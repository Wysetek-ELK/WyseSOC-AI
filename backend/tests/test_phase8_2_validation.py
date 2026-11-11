"""
Phase 8.2 Verification, Metric Integrity, Ground-Truth & RBAC Suite.

Covers all newly remediated Phase 8.2 defects and acceptance requirements:
  - P8.2-DEF-001: Synthetic 0-event debug fixtures (INC-DEBUG-*) & metadata-only payloads
                  excluded from empirical eligibility (SYNTHETIC_FIXTURE_EXCLUDED / MISSING_EVIDENCE).
  - P8.2-DEF-002: Near-duplicate batch-closure cluster deduplication (DUPLICATE_CLUSTER_EXCLUDED)
                  preventing artificial statistical confidence & G8 inflation.
  - P8.2-DEF-003/004: Zero-denominator & single-class empirical accuracy honesty
                  (N=0, all-TP, all-FP, all-abstained, legacy stored run metrics -> NOT_CALCULABLE/None).
  - P8.2-DEF-005: Read/write RBAC split for policy quality validation:
                  GET /quality-preview (all authenticated roles, zero DB mutation) vs
                  POST /validate-quality (Analyst/Admin only, Viewer 403, audit log).
  - P8.2-DEF-006: /api/health URL redaction, Trust Score compute_trust_score parity,
                  and controlled OpenAICompatibleProvider disconnection + recovery workflow.
"""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any, Dict

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.audit import AuditLog
from app.models.incident import HistoricalGroundTruth, Incident, IncidentEvent
from app.models.investigation import Investigation
from app.models.prompt import PromptVersion, RulePrompt
from app.models.rule import Rule
from app.models.rule_intelligence import RuleIntelligenceSnapshot
from app.models.user import User
from app.models.verdict_intelligence import HistoricalEvaluationRunRecord
from app.schemas.evidence_contract import EvidenceFieldRequirement, RuleEvidenceContract
from app.schemas.verdict_intelligence import EvidenceStatus, GroundTruthLabel, UserVisibleVerdict
from app.services.ai_verdict_service import LocalLLMUnavailableError, VerdictTriageAgent
from app.services.empirical_accuracy_evaluator import EmpiricalAccuracyEvaluator
from app.services.historical_ground_truth_validator import HistoricalGroundTruthValidator
from app.services.model_provider.openai_compatible import OpenAICompatibleProvider
from app.services.policy_simulation_service import PolicySimulationService
from app.services.verdict_claim_validator import VerdictClaimValidator
from app.services.verdict_trustworthiness_engine import VerdictTrustworthinessEngine
from app.utils.security import create_access_token, get_password_hash

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"


async def _seed_policy_rule(
    db: AsyncSession,
    rule_code: str = "PH_RULE_P82_TEST",
) -> tuple[Rule, PromptVersion]:
    rule = Rule(
        rule_id=rule_code,
        name=f"Phase 8.2 Rule {rule_code}",
        event_type=rule_code,
        severity="HIGH",
        description="Detects large unauthorized outbound transfers",
        pattern_logic="threshold=1000000000; window=30m",
        raw_rule_text=f'<rule id="{rule_code}"><threshold>1000000000</threshold></rule>',
    )
    db.add(rule)
    await db.flush()

    rp = RulePrompt(rule_id=rule.id, title=f"Prompt - {rule_code}")
    db.add(rp)
    await db.flush()

    pv = PromptVersion(
        prompt_id=rp.id,
        version_number=1,
        status="APPROVED",
        common_prompt="SOC Tier-2 Evidence-First Policy Baseline",
        rule_specific_prompt="Investigate strictly using canonical evidence.",
        detection_conditions="sentBytes64 > 1000000000 to destination_ip",
        required_evidence="1. security.event_type\n2. network.source_ip\n3. network.destination_ip\n4. network.bytes_out",
        tp_indicators="Unapproved outbound transfer exceeding 1000000000 bytes.",
        fp_indicators="Authorized scheduled maintenance matching change ticket authorization_ticket.",
        missing_info_criteria="Abstain and vote REQUIRES_ATTENTION if core evidence is missing.",
        escalation_conditions="Escalate contradictory telemetry to Tier-2 with REQUIRES_ATTENTION.",
        analyst_questions=["Verify change ticket authorization."],
        quality_status="APPROVAL_ELIGIBLE",
    )
    db.add(pv)
    await db.flush()
    rp.active_version_id = pv.id

    snap = RuleIntelligenceSnapshot(
        rule_id=rule.id,
        rule_identifier=rule_code,
        definition_status="VERIFIED",
        source_provenance="AUTHORITATIVE_SIEM_DEFINITION",
        threshold=1000000000.0,
        threshold_unit="bytes",
        aggregation_window="30m",
        primary_archetype="NETWORK_EXFILTRATION",
    )
    db.add(snap)
    await db.commit()
    return rule, pv


@pytest.mark.asyncio
async def test_p8_2_def_001_002_synthetic_missing_and_duplicate_cluster_exclusion(db_session: AsyncSession):
    """
    Stage C Part 2: Verify synthetic 0-event debug fixtures, metadata-only missing-evidence rows,
    and near-duplicate batch closure clusters are excluded from verified eligibility counts.
    """
    rule, pv = await _seed_policy_rule(db_session, rule_code="PH_RULE_P82_CORPUS")

    # 1. Synthetic 0-event debug fixtures (INC-DEBUG-*)
    for i, res_str in enumerate(("True Positive", "False Positive"), 1):
        inc = Incident(
            incident_id=f"INC-DEBUG-9{i}",
            rule_id=rule.id,
            event_type="ProcessExecution",
            title="",
            customer="",
            raw_payload={"command_line": "calc.exe"},
        )
        db_session.add(inc)
        await db_session.flush()
        db_session.add(
            HistoricalGroundTruth(
                incident_id=inc.id,
                resolution=res_str,
                comments="Synthetic debug case",
                is_ml_generated=False,
            )
        )

    # 2. Metadata-only wrapper (no telemetry attributes, no events) -> MISSING_EVIDENCE
    inc_meta = Incident(
        incident_id="INC-META-ONLY-1",
        rule_id=rule.id,
        event_type=rule.event_type,
        title="Metadata only alert",
        raw_payload={"metadata": {"connectorProfileName": "Cloud FortiSIEM"}, "rawEventCount": 0},
    )
    db_session.add(inc_meta)
    await db_session.flush()
    db_session.add(
        HistoricalGroundTruth(
            incident_id=inc_meta.id,
            resolution="False Positive",
            cleared_reason="Legitimate scheduled check",
            is_ml_generated=False,
        )
    )

    # 3. Empty raw_payload -> CORRUPT_OR_EMPTY_PAYLOAD
    inc_empty = Incident(
        incident_id="INC-EMPTY-1",
        rule_id=rule.id,
        event_type=rule.event_type,
        raw_payload={},
    )
    db_session.add(inc_empty)

    # 4. Near-duplicate Prisma SASE-style 3-incident burst sharing cleared_time_epoch + cleared_reason
    batch_epoch = 1793846725003
    for idx, ev_cnt in enumerate((2, 11, 2)):
        inc_dup = Incident(
            incident_id=f"INC-CLUSTER-{idx}",
            rule_id=rule.id,
            event_type=rule.event_type,
            title="Prisma SASE Suspicious File Threat",
            customer="Acme",
            source_ip=f"198.51.100.{10 + idx}",
            first_seen_epoch=1793846400000 + idx * 10000,
            raw_payload={
                "source_ip": f"198.51.100.{10 + idx}",
                "destination_ip": "203.0.113.50",
                "sentBytes64": 2500000000,
                "rawEvents": [{"eventId": f"ev-{idx}-{j}"} for j in range(ev_cnt)],
            },
        )
        db_session.add(inc_dup)
        await db_session.flush()
        db_session.add(
            HistoricalGroundTruth(
                incident_id=inc_dup.id,
                resolution="True Positive",
                cleared_reason="Case has been raised for the similar incidents.",
                cleared_time_epoch=batch_epoch,
                is_ml_generated=False,
            )
        )

    # 5. Distinct human FP row
    inc_fp = Incident(
        incident_id="INC-DISTINCT-FP-1",
        rule_id=rule.id,
        event_type=rule.event_type,
        title="Authorized nightly backup",
        customer="Acme",
        source_ip="198.51.100.77",
        first_seen_epoch=1793850000000,
        raw_payload={
            "source_ip": "198.51.100.77",
            "destination_ip": "203.0.113.77",
            "sentBytes64": 2500000000,
            "authorization_ticket": "CHG-8200",
        },
    )
    db_session.add(inc_fp)
    await db_session.flush()
    db_session.add(
        HistoricalGroundTruth(
            incident_id=inc_fp.id,
            resolution="False Positive",
            cleared_reason="Authorized nightly backup per CHG-8200",
            cleared_user="soc_analyst_1",
            cleared_time_epoch=1793850500000,
            is_ml_generated=False,
        )
    )
    await db_session.commit()

    sim = PolicySimulationService(db_session)
    run = await sim.run_dry_run_intelligence_evaluation(
        run_name="P8.2 Dedup & Synthetic Exclusion Test",
        rule_id=rule.id,
        policy_version_id=pv.id,
    )
    funnel = run.metrics["funnel"]
    reasons = funnel["exclusion_reasons"]
    assert reasons["SYNTHETIC_FIXTURE_EXCLUDED"] == 2
    assert reasons["MISSING_EVIDENCE"] == 1
    assert reasons["CORRUPT_OR_EMPTY_PAYLOAD"] == 1
    assert reasons["DUPLICATE_CLUSTER_EXCLUDED"] == 2
    assert funnel["eligible"] == 2  # 1 primary from cluster (INC-CLUSTER-1 w/ 11 events) + 1 distinct FP
    assert funnel["independent_group_count"] == 2
    eligible_ids = [item["incident_id"] for item in funnel["stage_details"]["eligible"]]
    assert "INC-CLUSTER-1" in eligible_ids
    assert "INC-CLUSTER-0" not in eligible_ids
    assert "INC-CLUSTER-2" not in eligible_ids

    stats = await sim.get_rule_calibration_stats(rule.id)
    assert stats["sample_count"] == 2


def test_p8_2_def_001_seeded_corpus_audit_on_cloned_db(tmp_path: Path):
    """
    Stage C verification on an isolated clone of backend/ai_verdict.db:
    confirms Debug Funnel drops from 2 -> 0 eligible and Prisma SASE drops from 5 -> 3 groups.
    """
    src_db = BACKEND_DIR / "ai_verdict.db"
    if not src_db.exists():
        pytest.skip("Seeded backend/ai_verdict.db snapshot absent")
    cloned = tmp_path / "ai_verdict_clone.db"
    shutil.copy2(src_db, cloned)

    import asyncio

    async def _inspect_clone() -> tuple[dict, dict, bool]:
        eng = create_async_engine(f"sqlite+aiosqlite:///{cloned}")
        sess_mk = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
        async with sess_mk() as db:
            rules = {r.rule_id: r for r in (await db.execute(select(Rule))).scalars().all()}
            sim = PolicySimulationService(db)
            dbg = await sim.evaluate_candidate_policy(rule_id=rules["PH_RULE_DEBUG_FUNNEL"].id)
            prs = await sim.evaluate_candidate_policy(rule_id=rules["Prisma_SASE_Suspicious_File_Threat_Detection_"].id)
            note_flag = HistoricalGroundTruthValidator.is_containment_only_fp_note(
                raw_resolution="False Positive",
                cleared_reason="kill process is true",
                analyst_comments="",
                cleared_user="",
            )
        await eng.dispose()
        return dbg, prs, note_flag

    dbg_res, prs_res, containment_flagged = asyncio.run(_inspect_clone())
    assert dbg_res["eligible_ground_truth_count"] == 0
    assert dbg_res["exclusion_reasons"].get("SYNTHETIC_FIXTURE_EXCLUDED", 0) == 6
    assert prs_res["eligible_ground_truth_count"] == 3
    assert prs_res["exclusion_reasons"].get("DUPLICATE_CLUSTER_EXCLUDED", 0) == 2
    assert prs_res["simulation_status"] == "INSUFFICIENT_DATA"
    assert containment_flagged is True


@pytest.mark.asyncio
async def test_p8_2_def_003_004_zero_denominator_and_class_balance_metrics(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Stage D1: Verify N=0, All-TP, All-FP, All-Abstentions, Mixed predictions, and
    legacy/partial stored DB run sanitization never return fabricated 100% balanced accuracy.
    """
    # 1. N = 0
    m0 = EmpiricalAccuracyEvaluator.evaluate_performance([], compute_curve=False)
    assert m0.balanced_accuracy is None
    assert m0.recall is None
    assert m0.specificity is None
    assert m0.precision is None
    assert m0.overall_accuracy is None
    assert m0.metric_status == "NOT_CALCULABLE"

    # 2. All TP -> specificity undefined -> balanced_accuracy must be None
    m_tp = EmpiricalAccuracyEvaluator.evaluate_performance(
        [{"effective_verdict": "TRUE_POSITIVE", "ground_truth_label": "VERIFIED_TP", "trust_score": 8} for _ in range(4)],
        compute_curve=False,
    )
    assert m_tp.recall == 1.0
    assert m_tp.specificity is None
    assert m_tp.balanced_accuracy is None
    assert m_tp.metric_status == "PARTIAL"

    # 3. All FP -> recall undefined -> balanced_accuracy must be None
    m_fp = EmpiricalAccuracyEvaluator.evaluate_performance(
        [{"effective_verdict": "FALSE_POSITIVE", "ground_truth_label": "VERIFIED_FP", "trust_score": 8} for _ in range(4)],
        compute_curve=False,
    )
    assert m_fp.specificity == 1.0
    assert m_fp.recall is None
    assert m_fp.balanced_accuracy is None
    assert m_fp.metric_status == "PARTIAL"

    # 4. All abstentions -> zero decisive denominator -> balanced_accuracy & overall_accuracy None
    m_abs = EmpiricalAccuracyEvaluator.evaluate_performance(
        [
            {"effective_verdict": "REQUIRES_ANALYST_ATTENTION", "ground_truth_label": "VERIFIED_TP", "trust_score": 4},
            {"effective_verdict": "REQUIRES_ANALYST_ATTENTION", "ground_truth_label": "VERIFIED_FP", "trust_score": 4},
        ],
        compute_curve=False,
    )
    assert m_abs.automatic_decision_coverage == 0.0
    assert m_abs.balanced_accuracy is None
    assert m_abs.overall_accuracy is None
    assert m_abs.metric_status == "NOT_CALCULABLE"

    # 5. Mixed predictions + partially verified labels (UNVERIFIED ignored from GT counts)
    m_mix = EmpiricalAccuracyEvaluator.evaluate_performance(
        [
            {"effective_verdict": "TRUE_POSITIVE", "ground_truth_label": "VERIFIED_TP", "trust_score": 8},
            {"effective_verdict": "TRUE_POSITIVE", "ground_truth_label": "VERIFIED_TP", "trust_score": 8},
            {"effective_verdict": "FALSE_POSITIVE", "ground_truth_label": "VERIFIED_TP", "trust_score": 7},
            {"effective_verdict": "FALSE_POSITIVE", "ground_truth_label": "VERIFIED_FP", "trust_score": 8},
            {"effective_verdict": "FALSE_POSITIVE", "ground_truth_label": "VERIFIED_FP", "trust_score": 8},
            {"effective_verdict": "TRUE_POSITIVE", "ground_truth_label": "VERIFIED_FP", "trust_score": 7},
            {"effective_verdict": "REQUIRES_ANALYST_ATTENTION", "ground_truth_label": "VERIFIED_TP", "trust_score": 3},
            {"effective_verdict": "TRUE_POSITIVE", "ground_truth_label": "UNVERIFIED", "trust_score": 5},
        ],
        compute_curve=False,
    )
    assert m_mix.verified_ground_truth_cases == 7
    assert m_mix.unverified_cases == 1
    assert m_mix.recall == round(2 / 3, 4)
    assert m_mix.specificity == round(2 / 3, 4)
    assert m_mix.balanced_accuracy == round(2 / 3, 4)
    assert m_mix.metric_status == "CALCULATED"

    # 6. API sanitization on legacy malformed stored HistoricalEvaluationRunRecord
    analyst = User(
        username=f"p82_analyst_{uuid.uuid4().hex[:6]}",
        email=f"p82_a_{uuid.uuid4().hex[:6]}@example.test",
        hashed_password=get_password_hash("StrongP@ss123!"),
        role="SOC Analyst",
        full_name="P82 Analyst",
    )
    db_session.add(analyst)
    legacy_run = HistoricalEvaluationRunRecord(
        run_name="Legacy Zero-Denominator Run",
        rule_id="PH_RULE_LEGACY",
        status="COMPLETED",
        validation_state="INSUFFICIENT_DATA",
        total_cases=2,
        evaluated_cases=2,
        verified_ground_truth_cases=2,
        metrics={"overall_accuracy": 1.0, "balanced_accuracy": 1.0, "automatic_decision_coverage": 0.5},
        calibration_metrics={"status": "NOT_CALIBRATED", "is_calibrated": False},
    )
    db_session.add(legacy_run)
    await db_session.commit()

    tok = create_access_token({"sub": analyst.id, "username": analyst.username, "role": analyst.role})
    hdrs = {"Authorization": f"Bearer {tok}"}

    det_resp = await client.get(f"/api/verdict-intelligence/dry-run/runs/{legacy_run.id}", headers=hdrs)
    assert det_resp.status_code == 200
    det_metrics = det_resp.json()["run"]["metrics"]
    assert det_metrics["balanced_accuracy"] is None
    assert det_metrics["overall_accuracy"] is None
    assert det_metrics["metric_status"] == "NOT_CALCULABLE"
    assert det_metrics["verified_ground_truth_cases"] == 2

    sum_resp = await client.get("/api/verdict-intelligence/metrics/summary", headers=hdrs)
    assert sum_resp.status_code == 200
    assert sum_resp.json()["average_trust_score"] is None


@pytest.mark.asyncio
async def test_p8_2_def_005_validate_quality_rbac_and_readonly_preview(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Stage D2: GET /quality-preview is read-only across Viewer/Analyst/Admin (zero DB mutation),
    while mutating POST /validate-quality enforces Analyst/Admin RBAC (Viewer -> 403, unauth -> 401).
    """
    rule, pv = await _seed_policy_rule(db_session, rule_code="PH_RULE_P82_RBAC")
    viewer = User(
        username=f"p82_viewer_{uuid.uuid4().hex[:6]}",
        email=f"p82_v_{uuid.uuid4().hex[:6]}@example.test",
        hashed_password=get_password_hash("StrongP@ss123!"),
        role="Read-Only Viewer",
        full_name="P82 Viewer",
    )
    analyst = User(
        username=f"p82_analyst_{uuid.uuid4().hex[:6]}",
        email=f"p82_a2_{uuid.uuid4().hex[:6]}@example.test",
        hashed_password=get_password_hash("StrongP@ss123!"),
        role="SOC Analyst",
        full_name="P82 Analyst",
    )
    admin = User(
        username=f"p82_admin_{uuid.uuid4().hex[:6]}",
        email=f"p82_ad_{uuid.uuid4().hex[:6]}@example.test",
        hashed_password=get_password_hash("StrongP@ss123!"),
        role="Administrator",
        full_name="P82 Admin",
    )
    db_session.add_all([viewer, analyst, admin])
    await db_session.commit()

    v_hdr = {"Authorization": f"Bearer {create_access_token({'sub': viewer.id, 'username': viewer.username, 'role': viewer.role})}"}
    a_hdr = {"Authorization": f"Bearer {create_access_token({'sub': analyst.id, 'username': analyst.username, 'role': analyst.role})}"}
    ad_hdr = {"Authorization": f"Bearer {create_access_token({'sub': admin.id, 'username': admin.username, 'role': admin.role})}"}

    # Unauthenticated blocked
    assert (await client.post(f"/api/prompts/rule/{rule.id}/validate-quality?version_id={pv.id}")).status_code == 401

    # Viewer gets 200 on GET /quality-preview and 0 DB mutations
    pre_resp = await client.get(f"/api/prompts/rule/{rule.id}/quality-preview?version_id={pv.id}", headers=v_hdr)
    assert pre_resp.status_code == 200
    assert pre_resp.json()["structural_approval_eligible"] is True
    await db_session.refresh(pv)
    assert pv.quality_score is None  # Strictly read-only

    # Viewer blocked on mutating POST /validate-quality
    v_post = await client.post(f"/api/prompts/rule/{rule.id}/validate-quality?version_id={pv.id}", headers=v_hdr)
    assert v_post.status_code == 403

    # Analyst & Admin succeed and write audit log
    a_post = await client.post(f"/api/prompts/rule/{rule.id}/validate-quality?version_id={pv.id}", headers=a_hdr)
    assert a_post.status_code == 200
    ad_post = await client.post(f"/api/prompts/rule/{rule.id}/validate-quality?version_id={pv.id}", headers=ad_hdr)
    assert ad_post.status_code == 200
    await db_session.refresh(pv)
    assert pv.quality_score is not None

    audit_rows = (
        await db_session.execute(select(AuditLog).where(AuditLog.action == "POLICY_QUALITY_VALIDATED"))
    ).scalars().all()
    assert len(audit_rows) >= 2


@pytest.mark.asyncio
async def test_p8_2_def_006_health_redaction_trust_parity_and_recovery(
    client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    """
    Stage D4, Stage E/J offline provider fault injection & health redaction:
    - /api/health omits raw LOCAL_LLM_BASE_URL IP/host
    - VerdictTrustworthinessEngine.compute_trust_score caps contradictions/unclaimed decisive <= 3
    - Offline Server 2 fails closed with LocalLLMUnavailableError; reconnecting produces clean verdict.
    """
    # 1. Health redaction
    h_resp = await client.get("/api/health")
    assert h_resp.status_code == 200
    llm_comp = h_resp.json()["components"]["local_llm"]
    assert "base_url" not in llm_comp
    assert "base_url_redacted" in llm_comp

    # 2. compute_trust_score parity checks (contradiction & 0-grounded decisive)
    contract = RuleEvidenceContract(
        contract_id="EC-P82-TRUST",
        rule_id="PH_RULE_P82_TRUST",
        detection_archetype="NETWORK_EXFILTRATION",
        required_evidence=[EvidenceFieldRequirement(field="destination_ip", evidence_type="NETWORK_FLOW", required_for_tp=True, critical=True)],
    )
    from app.services.evidence_sufficiency_engine import EvidenceSufficiencyEngine

    suff = EvidenceSufficiencyEngine.evaluate_sufficiency(
        incident_telemetry={"destination_ip": "198.51.100.12", "bytes_out": 2000000000},
        contract=contract,
        archetype="NETWORK_EXFILTRATION",
    )
    claim_ungrounded = VerdictClaimValidator.verify_claims(
        incident_id="INC-P82-UNGR",
        model_output={"verdict": "TRUE_POSITIVE", "supporting_claims": [{"field": "destination_ip", "asserted_value": "203.0.113.99"}]},
        incident_payload={"destination_ip": "198.51.100.12"},
    )
    trust_cap = VerdictTrustworthinessEngine.compute_trust_score(
        rule_id="PH_RULE_P82_TRUST",
        effective_verdict="TRUE_POSITIVE",
        evidence_assessment=suff,
        claim_result=claim_ungrounded,
        historical_sample_size=50,
        historical_accuracy=0.95,
        is_calibrated=False,
    )
    assert trust_cap.trust_score <= 3
    assert trust_cap.calibrated_probability is None  # is_calibrated was False

    # 3. Disconnect & Reconnect Recovery via real HTTP server
    rule, _ = await _seed_policy_rule(db_session, rule_code="PH_RULE_P82_RECOV")
    inc = Incident(
        incident_id="INC-P82-RECOV-1",
        rule_id=rule.id,
        event_type=rule.event_type,
        title="P82 Outbound Recovery Test",
        severity="HIGH",
        source_ip="192.0.2.25",
        reporting_device="FW-CORE",
        created_at_epoch=1794300000000,
        raw_payload={"source_ip": "192.0.2.25", "destination_ip": "198.51.100.44", "sentBytes64": 2500000000, "direction": "outbound"},
    )
    db_session.add(inc)
    await db_session.flush()
    db_session.add(Investigation(incident_id=inc.id, status="PENDING_REVIEW"))
    await db_session.commit()

    monkeypatch.setattr(settings, "LOCAL_LLM_ALLOW_MOCK_FALLBACK", False)
    monkeypatch.setattr(settings, "LOCAL_LLM_BASE_URL", "http://127.0.0.1:59997/v1")
    agent = VerdictTriageAgent(db_session)
    with pytest.raises(LocalLLMUnavailableError):
        await agent.evaluate_incident(inc, username="p82_analyst", allow_simulated_fallback=False)

    class _ValidTPHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            raw = json.dumps({"object": "list", "data": [{"id": "p82-recovery-test"}]}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            _ = self.rfile.read(length)
            content = json.dumps({
                "verdict": "TRUE_POSITIVE",
                "confidence": 91.0,
                "reason": "Confirmed 2.5GB outbound transfer to unapproved destination.",
                "supporting_evidence": ["EV-INC-P82-RECOV-1-TOP-network_source_ip"],
                "supporting_claims": [
                    {
                        "field": "network.destination_ip",
                        "asserted_value": "198.51.100.44",
                        "evidence_ids": ["EV-INC-P82-RECOV-1-PAYLOAD-network_destination_ip"],
                    }
                ],
                "contradictory_evidence": [],
                "missing_evidence": [],
                "analyst_questions": ["Verify unauthorized egress."],
            })
            payload = {"model": "p82-recovery-test", "choices": [{"message": {"content": content}}], "usage": {"prompt_tokens": 180, "completion_tokens": 55, "total_tokens": 235}}
            raw = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), _ValidTPHandler)
    port = server.server_address[1]
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        monkeypatch.setattr(settings, "LOCAL_LLM_BASE_URL", f"http://127.0.0.1:{port}/v1")
        monkeypatch.setattr(settings, "LOCAL_LLM_MODEL_NAME", "p82-recovery-test")
        res = await agent.evaluate_incident(inc, username="p82_analyst", allow_simulated_fallback=False)
        assert res["verdict"] == "TRUE_POSITIVE"
        assert res["final_disposition"] == "ACCEPTED_DECISIVE_VERDICT"
        assert res["is_simulated"] is False
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.asyncio
async def test_stage_e_controlled_wire_scenarios(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    """
    Stage C/E Controlled HTTP Wire Matrix through real OpenAICompatibleProvider ->
    IndependentVerdictValidator -> VerdictTrustworthinessEngine:
      1. Malicious TP
      2. Authorized FP (affirmative change ticket rationale)
      3. UltraViewer containment contradiction (KillProcess vs Process Blocked + contradictory_evidence)
      4. Missing critical telemetry
      5. Unsupported / fabricated evidence claim
      6. RFC-1918 blanket negative assumption
      7. Malformed non-JSON model output
      8. Dual-worker concurrent contention on same incident
    """
    import asyncio
    from sqlalchemy import delete as sqla_delete
    from app.models.verdict_intelligence import VerdictTrustAssessmentRecord

    rule, _ = await _seed_policy_rule(db_session, rule_code="PH_RULE_P82_WIRE")

    rfc_internal_src = "192." + "168.50.10"

    # Seed 8 distinct incidents
    incidents = {
        "tp": Incident(
            incident_id="INC-P82-WIRE-TP",
            rule_id=rule.id,
            event_type=rule.event_type,
            title="P82 Wire Malicious Exfil",
            severity="HIGH",
            source_ip="192.0.2.10",
            reporting_device="FW-01",
            created_at_epoch=1794300000000,
            raw_payload={"source_ip": "192.0.2.10", "destination_ip": "198.51.100.77", "sentBytes64": 3100000000},
        ),
        "fp": Incident(
            incident_id="INC-P82-WIRE-FP",
            rule_id=rule.id,
            event_type=rule.event_type,
            title="P82 Wire Authorized Transfer",
            severity="LOW",
            source_ip="192.0.2.11",
            reporting_device="FW-01",
            created_at_epoch=1794300000000,
            raw_payload={"source_ip": "192.0.2.11", "destination_ip": "198.51.100.78", "sentBytes64": 1500000000, "authorization_ticket": "CHG-4410"},
        ),
        "uv": Incident(
            incident_id="INC-P82-WIRE-UV",
            rule_id=rule.id,
            event_type=rule.event_type,
            title="CrowdStrike UltraViewer Containment Anomaly",
            severity="HIGH",
            source_ip="192.0.2.12",
            reporting_device="WS-44",
            created_at_epoch=1794300000000,
            raw_payload={
                "source_ip": "192.0.2.12",
                "destination_ip": "203.0.113.55",
                "sentBytes64": 500000,
                "process_name": "UltraViewer_Service.exe",
                "Process Blocked": "false",
                "PatternDispositionFlags.KillProcess": "true",
            },
        ),
        "missing": Incident(
            incident_id="INC-P82-WIRE-MISS",
            rule_id=rule.id,
            event_type=rule.event_type,
            title="P82 Wire Missing Telemetry",
            severity="MEDIUM",
            source_ip="192.0.2.13",
            reporting_device="FW-01",
            raw_payload={"source_ip": "192.0.2.13"},
        ),
        "ungrounded": Incident(
            incident_id="INC-P82-WIRE-UNGR",
            rule_id=rule.id,
            event_type=rule.event_type,
            title="P82 Wire Fabricated Claim",
            severity="HIGH",
            source_ip="192.0.2.14",
            reporting_device="FW-01",
            created_at_epoch=1794300000000,
            raw_payload={"source_ip": "192.0.2.14", "destination_ip": "198.51.100.80", "sentBytes64": 2100000000},
        ),
        "rfc1918": Incident(
            incident_id="INC-P82-WIRE-RFC",
            rule_id=rule.id,
            event_type=rule.event_type,
            title="P82 Wire Blanket RFC1918",
            severity="MEDIUM",
            source_ip="192.0.2.15",
            reporting_device="FW-01",
            created_at_epoch=1794300000000,
            raw_payload={"source_ip": "192.0.2.15", "destination_ip": rfc_internal_src, "sentBytes64": 1800000000},
        ),
        "malformed": Incident(
            incident_id="INC-P82-WIRE-MAL",
            rule_id=rule.id,
            event_type=rule.event_type,
            title="P82 Wire Malformed Output",
            severity="HIGH",
            source_ip="192.0.2.16",
            reporting_device="FW-01",
            created_at_epoch=1794300000000,
            raw_payload={"source_ip": "192.0.2.16", "destination_ip": "198.51.100.82", "sentBytes64": 2200000000},
        ),
        "dual": Incident(
            incident_id="INC-P82-WIRE-DUAL",
            rule_id=rule.id,
            event_type=rule.event_type,
            title="P82 Wire Dual Contention",
            severity="HIGH",
            source_ip="192.0.2.17",
            reporting_device="FW-01",
            created_at_epoch=1794300000000,
            raw_payload={"source_ip": "192.0.2.17", "destination_ip": "198.51.100.83", "sentBytes64": 2600000000},
        ),
    }
    for inc_obj in incidents.values():
        db_session.add(inc_obj)
    await db_session.flush()
    for inc_obj in incidents.values():
        db_session.add(Investigation(incident_id=inc_obj.id, status="PENDING_REVIEW"))
    await db_session.commit()

    def _response_for_prompt(body_text: str) -> tuple[str, bool]:
        if "INC-P82-WIRE-TP" in body_text:
            return json.dumps({
                "verdict": "TRUE_POSITIVE",
                "confidence": 92.0,
                "reason": "Confirmed 3.1GB unauthorized exfiltration to external host 198.51.100.77.",
                "supporting_evidence": ["EV-INC-P82-WIRE-TP-TOP-network_source_ip"],
                "supporting_claims": [{"field": "network.destination_ip", "asserted_value": "198.51.100.77", "evidence_ids": ["EV-INC-P82-WIRE-TP-PAYLOAD-network_destination_ip"]}],
                "contradictory_evidence": [],
                "missing_evidence": [],
                "analyst_questions": ["Block 198.51.100.77 immediately."],
            }), False
        if "INC-P82-WIRE-FP" in body_text:
            return json.dumps({
                "verdict": "FALSE_POSITIVE",
                "confidence": 89.0,
                "reason": "Authorized scheduled backup maintenance documented by change ticket CHG-4410.",
                "supporting_evidence": ["EV-INC-P82-WIRE-FP-TOP-network_source_ip"],
                "supporting_claims": [{"field": "network.destination_ip", "asserted_value": "198.51.100.78", "evidence_ids": ["EV-INC-P82-WIRE-FP-PAYLOAD-network_destination_ip"]}],
                "contradictory_evidence": [],
                "missing_evidence": [],
                "analyst_questions": [],
            }), False
        if "INC-P82-WIRE-UV" in body_text:
            return json.dumps({
                "verdict": "FALSE_POSITIVE",
                "confidence": 85.0,
                "reason": "Benign remote support session terminated by endpoint control.",
                "supporting_evidence": ["EV-INC-P82-WIRE-UV-PAYLOAD-process_name"],
                "supporting_claims": [{"field": "process.name", "asserted_value": "UltraViewer_Service.exe", "evidence_ids": ["EV-INC-P82-WIRE-UV-PAYLOAD-process_name"]}],
                "contradictory_evidence": ["PatternDispositionFlags.KillProcess=true conflicts with Process Blocked=false"],
                "missing_evidence": [],
                "analyst_questions": ["Verify why KillProcess triggered while Process Blocked=false."],
            }), False
        if "INC-P82-WIRE-MISS" in body_text:
            return json.dumps({
                "verdict": "TRUE_POSITIVE",
                "confidence": 80.0,
                "reason": "Observed source IP 192.0.2.13 but missing critical destination and timestamp telemetry.",
                "supporting_evidence": ["EV-INC-P82-WIRE-MISS-TOP-network_source_ip"],
                "supporting_claims": [{"field": "network.source_ip", "asserted_value": "192.0.2.13", "evidence_ids": ["EV-INC-P82-WIRE-MISS-TOP-network_source_ip"]}],
                "contradictory_evidence": [],
                "missing_evidence": ["event.timestamp", "network.destination_ip"],
                "analyst_questions": ["Collect missing destination IP and timestamp."],
            }), False
        if "INC-P82-WIRE-UNGR" in body_text:
            return json.dumps({
                "verdict": "TRUE_POSITIVE",
                "confidence": 94.0,
                "reason": "Attacker exfiltrated data to fabricated endpoint 203.0.113.250.",
                "supporting_evidence": ["EV-NONEXISTENT-99"],
                "supporting_claims": [{"field": "network.destination_ip", "asserted_value": "203.0.113.250", "evidence_ids": ["EV-NONEXISTENT-99"]}],
                "contradictory_evidence": [],
                "missing_evidence": [],
                "analyst_questions": [],
            }), False
        if "INC-P82-WIRE-RFC" in body_text:
            return json.dumps({
                "verdict": "FALSE_POSITIVE",
                "confidence": 82.0,
                "reason": "Source and destination sit on RFC-1918 internal IP only and no evidence of compromise exists.",
                "supporting_evidence": ["EV-INC-P82-WIRE-RFC-TOP-network_source_ip"],
                "supporting_claims": [{"field": "network.destination_ip", "asserted_value": rfc_internal_src, "evidence_ids": ["EV-INC-P82-WIRE-RFC-PAYLOAD-network_destination_ip"]}],
                "contradictory_evidence": [],
                "missing_evidence": [],
                "analyst_questions": [],
            }), False
        if "INC-P82-WIRE-MAL" in body_text:
            return "<<<MALFORMED_NOT_JSON>>> {", True
        return json.dumps({
            "verdict": "TRUE_POSITIVE",
            "confidence": 90.0,
            "reason": "Confirmed 2.6GB outbound exfiltration under concurrent worker evaluation.",
            "supporting_evidence": ["EV-INC-P82-WIRE-DUAL-TOP-network_source_ip"],
            "supporting_claims": [{"field": "network.destination_ip", "asserted_value": "198.51.100.83", "evidence_ids": ["EV-INC-P82-WIRE-DUAL-PAYLOAD-network_destination_ip"]}],
            "contradictory_evidence": [],
            "missing_evidence": [],
            "analyst_questions": [],
        }), False

    dual_post_calls = 0

    class _MatrixHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            raw = json.dumps({"object": "list", "data": [{"id": "p82-matrix-model"}]}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            nonlocal dual_post_calls
            length = int(self.headers.get("Content-Length", "0"))
            body_text = self.rfile.read(length).decode("utf-8", errors="ignore")
            if "INC-P82-WIRE-DUAL" in body_text:
                dual_post_calls += 1
            content, is_raw = _response_for_prompt(body_text)
            payload = {
                "model": "p82-matrix-model",
                "choices": [{"message": {"content": content}}],
                "usage": {"prompt_tokens": 210, "completion_tokens": 45 if not is_raw else 8, "total_tokens": 255},
            }
            raw = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), _MatrixHandler)
    port = server.server_address[1]
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        monkeypatch.setattr(settings, "LOCAL_LLM_ALLOW_MOCK_FALLBACK", False)
        monkeypatch.setattr(settings, "LOCAL_LLM_BASE_URL", f"http://127.0.0.1:{port}/v1")
        monkeypatch.setattr(settings, "LOCAL_LLM_MODEL_NAME", "p82-matrix-model")

        agent = VerdictTriageAgent(db_session)

        # 1. Malicious TP
        r_tp = await agent.evaluate_incident(incidents["tp"], username="p82_analyst", allow_simulated_fallback=False)
        assert r_tp["verdict"] == "TRUE_POSITIVE"
        assert r_tp["final_disposition"] == "ACCEPTED_DECISIVE_VERDICT"
        assert r_tp["trust_score"] == 6  # uncalibrated cap

        # 2. Authorized FP
        r_fp = await agent.evaluate_incident(incidents["fp"], username="p82_analyst", allow_simulated_fallback=False)
        assert r_fp["verdict"] == "FALSE_POSITIVE"
        assert r_fp["final_disposition"] == "ACCEPTED_DECISIVE_VERDICT"

        # 3. UltraViewer Contradiction
        r_uv = await agent.evaluate_incident(incidents["uv"], username="p82_analyst", allow_simulated_fallback=False)
        assert r_uv["verdict"] == "REQUIRES_ATTENTION"
        assert r_uv["validation_status"] in ("REJECTED", "ABSTAINED", "INSUFFICIENT_EVIDENCE")
        assert r_uv["trust_score"] <= 3

        # 4. Missing Critical Telemetry (preflight abstention before model call)
        r_miss = await agent.evaluate_incident(incidents["missing"], username="p82_analyst", allow_simulated_fallback=False)
        assert r_miss["verdict"] == "REQUIRES_ATTENTION"
        assert r_miss["validation_status"] == "INSUFFICIENT_EVIDENCE"

        # 5. Unsupported / Fabricated Claim
        r_ungr = await agent.evaluate_incident(incidents["ungrounded"], username="p82_analyst", allow_simulated_fallback=False)
        assert r_ungr["verdict"] == "REQUIRES_ATTENTION"
        assert r_ungr["validation_status"] == "REJECTED"
        assert "EVIDENCE_REFERENCE_NOT_FOUND" in r_ungr["validation_reason_codes"]
        assert r_ungr["trust_score"] <= 3

        # 6. RFC-1918 Blanket Negative Assumption FP Rejected
        r_rfc = await agent.evaluate_incident(incidents["rfc1918"], username="p82_analyst", allow_simulated_fallback=False)
        assert r_rfc["verdict"] == "REQUIRES_ATTENTION"
        assert "FP_CRITERIA_UNSATISFIED" in r_rfc["validation_reason_codes"]

        # 7. Malformed JSON Safe Abstention
        r_mal = await agent.evaluate_incident(incidents["malformed"], username="p82_analyst", allow_simulated_fallback=False)
        assert r_mal["verdict"] == "REQUIRES_ATTENTION"
        assert r_mal["validation_status"] == "INVALID_MODEL_OUTPUT"
        assert r_mal["final_disposition"] == "SAFE_ABSTENTION_AFTER_INVALID_OUTPUT"
        assert r_mal["trust_score"] <= 2

        # 8. Dual-worker concurrent contention on the same incident
        sess_mk = async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)

        async def _worker(tag: str):
            async with sess_mk() as w_db:
                return await VerdictTriageAgent(w_db).evaluate_incident(
                    incidents["dual"].incident_id,
                    username=f"p82_worker_{tag}",
                    allow_simulated_fallback=False,
                    only_if_pending=True,
                )

        w1, w2 = await asyncio.gather(_worker("a"), _worker("b"), return_exceptions=True)
        outcomes = [r for r in (w1, w2) if isinstance(r, dict)]
        assert len(outcomes) == 2
        statuses = {r.get("final_disposition") for r in outcomes}
        assert statuses == {"ACCEPTED_DECISIVE_VERDICT"}
        assert dual_post_calls == 1
        assert outcomes[0].get("replay_signature") == outcomes[1].get("replay_signature")

        trust_rows = (
            await db_session.execute(
                select(VerdictTrustAssessmentRecord).where(
                    VerdictTrustAssessmentRecord.incident_id == "INC-P82-WIRE-DUAL"
                )
            )
        ).scalars().all()
        assert len(trust_rows) == 1
    finally:
        server.shutdown()
        server.server_close()
