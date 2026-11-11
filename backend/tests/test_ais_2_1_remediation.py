"""
Comprehensive AIS 2.1 Remediation Regression Suite.
Covers all 11 backend acceptance criteria for P0/P1 remediations:
  1. Exact rule-scoped retrieval (2 matching incidents -> retrieves 2, never global 52)
  2. Strict sibling-rule isolation (PH_RULE_HEAVY_TCP_HOST_SCAN vs _ON_FIXED_PORT)
  3. Unlinked unambiguously matching event types included; ambiguous event types isolated
  4. Paginated retrieval beyond 50 incidents (e.g. 65 matching incidents)
  5. Word-boundary ML detection (no false 'normal'/'html'/'xml' loss) + no blind cleared_user trust
  6. Disputed, ambiguous, synthetic, or unverified labels excluded from G8 inference & scoring
  7. Real OPENAI_COMPATIBLE simulation via local HTTP server executes LLM & records provenance
  8. Mock SIMULATED execution cannot pass empirical G8
  9. Shared live/simulation verdict safeguards, Snapshot overrides & Destination Port normalization
 10. Historical replay never mutates live Incident.ai_verdict, Investigation, or GroundTruth
 11. Empirically unvalidated / stale / simulated / failed policies blocked from autonomous actions
"""

from datetime import datetime, timezone
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.incident import HistoricalGroundTruth, Incident, IncidentEvent
from app.models.investigation import Investigation
from app.models.pilot import PilotConfiguration
from app.models.prompt import PromptVersion, RulePrompt
from app.models.rule import Rule
from app.models.rule_intelligence import RuleIntelligenceSnapshot
from app.models.token_usage import TokenUsageRecord
from app.models.verdict_intelligence import (
    HistoricalEvaluationResultRecord,
    HistoricalEvaluationRunRecord,
)
from app.schemas.pilot import PilotMode
from app.schemas.policy_quality import GateStatus, SimulationStatus
from app.services.ai_verdict_service import VerdictTriageAgent
from app.services.detection_archetype_registry import DetectionArchetypeRegistry
from app.services.evidence_normalization_service import EvidenceNormalizationService
from app.services.evidence_sufficiency_engine import EvidenceSufficiencyEngine
from app.services.fortisiem_service import FortiSIEMService
from app.services.gpu_manager import gpu_workload_manager
from app.services.historical_ground_truth_validator import HistoricalGroundTruthValidator
from app.services.llm_config_service import LLMConfigService
from app.services.pilot_service import PilotService
from app.services.policy_governance import resolve_canonical_rule
from app.services.policy_quality_validator import PolicyQualityValidator
from app.services.policy_simulation_service import PolicySimulationService
from app.services.rule_parser import RuleParser


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _start_mock_openai_server(handler_cls):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


async def _seed_rule_with_approved_policy(
    db: AsyncSession,
    *,
    rule_id_str: str = "PH_RULE_HEAVY_TCP_HOST_SCAN",
    name: str = "Heavy TCP Host Scan",
    event_type: str = "PH_RULE_HEAVY_TCP_HOST_SCAN",
    pattern_logic: str = "COUNT(DISTINCT destIpAddr) >= 50 AND proto = TCP within 5m",
    with_snapshot: bool = True,
):
    rule = Rule(
        id=str(uuid.uuid4()),
        rule_id=rule_id_str,
        name=name,
        event_type=event_type,
        severity="HIGH",
        status="ACTIVE",
        data_source="Firewall",
        pattern_logic=pattern_logic,
        parsed_metadata={"source": "AUTHORITATIVE_XML_IMPORT", "definition_status": "VERIFIED"},
    )
    db.add(rule)
    await db.flush()

    rp = RulePrompt(id=str(uuid.uuid4()), rule_id=rule.id, title=f"Policy - {name}")
    db.add(rp)
    await db.flush()

    pv = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=rp.id,
        version_number=1,
        status="APPROVED",
        quality_status="APPROVED",
        quality_score=85.0,
        common_prompt="Enterprise SOC triage baseline: cite verified evidence.",
        rule_specific_prompt=f"Evaluate {name} telemetry for unauthorized horizontal TCP host scanning.",
        detection_conditions="Distinct destination hosts >= 50 on TCP over 5m.",
        required_evidence="source_ip, destination_ip, network.destination_port, network.protocol",
        tp_indicators="Unscheduled single source scanning dozens of distinct destination hosts on TCP ports.",
        fp_indicators="Verified change ticket approved enterprise vulnerability scanner during authorized window.",
        missing_info_criteria="Abstain to REQUIRES_ATTENTION if source_ip or network.destination_port is missing.",
        escalation_conditions="Escalate immediately if target includes critical domain controller.",
        analyst_questions=["Is source IP an authorized vulnerability scanner?"],
    )
    db.add(pv)
    await db.flush()
    rp.active_version_id = pv.id

    if with_snapshot:
        snap = RuleIntelligenceSnapshot(
            id=str(uuid.uuid4()),
            rule_id=rule.id,
            rule_identifier=rule_id_str,
            primary_archetype="NETWORK_SCAN",
            definition_status="VERIFIED",
            source_provenance="AUTHORITATIVE_SIEM_DEFINITION",
            threshold=50.0,
            threshold_unit="hosts",
            aggregation_window="5m",
            review_required=False,
            semantics_payload={
                "rule_identifier": rule_id_str,
                "rule_name": name,
                "primary_behavior": "NETWORK_SCAN",
                "definition_status": "VERIFIED",
                "source_provenance": "AUTHORITATIVE_SIEM_DEFINITION",
                "threshold": 50.0,
                "threshold_unit": "hosts",
                "aggregation_window": "5m",
                "grouping_keys": ["srcIpAddr"],
                "relevant_fields": ["srcIpAddr", "destIpAddr", "destPort", "proto"],
            },
        )
        db.add(snap)

    await db.flush()
    return rule, rp, pv


async def _add_historical_incident(
    db: AsyncSession,
    *,
    inc_code: str,
    rule_id: str | None,
    event_type: str,
    resolution: str | None = "True Positive",
    comments: str = "Verified malicious host scan against internal subnet.",
    cleared_reason: str = "",
    cleared_user: str = "tier2_analyst",
    is_ml_generated: bool = False,
    src_ip: str = "198.51.100.10",
    dest_ip: str = "192.0.2.50",
    dest_port: int = 445,
    extra_payload: dict | None = None,
    with_event: bool = True,
    with_investigation: Investigation | None = None,
):
    payload = {
        "source_ip": src_ip,
        "destIpAddr": dest_ip,
        "Destination Port": dest_port,
        "proto": "TCP",
        "rawEvents": [
            {
                "srcIpAddr": src_ip,
                "destIpAddr": dest_ip,
                "Destination Port": dest_port,
                "proto": "TCP",
            }
        ],
    }
    if extra_payload:
        payload.update(extra_payload)

    inc = Incident(
        id=str(uuid.uuid4()),
        incident_id=inc_code,
        rule_id=rule_id,
        event_type=event_type,
        title=f"Alert {inc_code}",
        severity="HIGH",
        status_code=2 if resolution else 1,
        status_name="Manually Cleared" if resolution else "Open",
        source_ip=src_ip,
        reporting_device="fw-core-01",
        raw_payload=payload,
        first_seen_epoch=1710000000000,
        created_at_epoch=1710000000000,
        created_at=datetime.now(timezone.utc),
    )
    db.add(inc)
    await db.flush()

    if with_event:
        ev = IncidentEvent(
            id=str(uuid.uuid4()),
            incident_id=inc.id,
            event_id=f"EV-{inc_code}",
            event_type=event_type,
            raw_log=f"TCP SYN {src_ip}:51234 -> {dest_ip}:{dest_port}",
            attributes={
                "srcIpAddr": src_ip,
                "destIpAddr": dest_ip,
                "Destination Port": dest_port,
                "proto": "TCP",
            },
        )
        db.add(ev)

    if resolution is not None:
        gt = HistoricalGroundTruth(
            id=str(uuid.uuid4()),
            incident_id=inc.id,
            resolution=resolution,
            comments=comments,
            cleared_reason=cleared_reason,
            cleared_user=cleared_user,
            is_ml_generated=is_ml_generated,
        )
        db.add(gt)

    if with_investigation is not None:
        with_investigation.incident_id = inc.id
        db.add(with_investigation)

    await db.flush()
    return inc


@pytest.mark.asyncio
async def test_1_rule_scoped_retrieval_returns_exact_two_not_52(db_session: AsyncSession):
    """AC-1: A rule with two matching incidents returns exactly 2, not unrelated global 52."""
    target_rule, _, pv = await _seed_rule_with_approved_policy(db_session)
    other_rule, _, _ = await _seed_rule_with_approved_policy(
        db_session,
        rule_id_str="PH_RULE_BRUTE_FORCE",
        name="Brute Force Login",
        event_type="PH_RULE_BRUTE_FORCE",
    )

    for i in range(2):
        await _add_historical_incident(
            db_session,
            inc_code=f"INC-SCAN-TWO-{i}",
            rule_id=target_rule.id,
            event_type=target_rule.event_type,
            src_ip=f"198.51.100.{20 + i}",
        )
    for i in range(52):
        await _add_historical_incident(
            db_session,
            inc_code=f"INC-OTHER-GLOBAL-{i}",
            rule_id=other_rule.id,
            event_type=other_rule.event_type,
            src_ip=f"203.0.113.{10 + (i % 100)}",
        )
    await db_session.commit()

    sim = PolicySimulationService(db_session)
    res = await sim.evaluate_candidate_policy(rule_id=target_rule.id, candidate_version=pv)
    funnel = res["funnel"]

    assert res["available_count"] == 2
    assert res["retrieved_count"] == 2
    assert funnel["total_scanned"] == 2
    assert funnel["rule_matched"] == 2
    assert funnel["exclusion_reasons"].get("RULE_MISMATCH", 0) == 0


@pytest.mark.asyncio
async def test_2_similar_rule_names_never_cause_cross_rule_contamination(db_session: AsyncSession):
    """AC-2: Sibling rules PH_RULE_HEAVY_TCP_HOST_SCAN and _ON_FIXED_PORT never contaminate."""
    scan_rule, _, pv_scan = await _seed_rule_with_approved_policy(
        db_session,
        rule_id_str="PH_RULE_HEAVY_TCP_HOST_SCAN",
        name="Heavy TCP Host Scan",
        event_type="PH_RULE_HEAVY_TCP_HOST_SCAN",
    )
    fixed_rule, _, _ = await _seed_rule_with_approved_policy(
        db_session,
        rule_id_str="PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT",
        name="Heavy TCP Host Scan on Fixed Port",
        event_type="PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT",
    )

    # Archetype classification handles exact _ON_FIXED_PORT spelling
    from app.services.rule_intelligence_analyzer import RuleIntelligenceAnalyzer

    fixed_sem = RuleIntelligenceAnalyzer.analyze_rule(fixed_rule)
    assert DetectionArchetypeRegistry.classify_rule(fixed_sem, fixed_rule).primary_archetype.value == "NETWORK_SCAN"

    # Seed 2 target incidents + 3 fixed-port sibling incidents + 1 ambiguous payload sibling collision
    for i in range(2):
        await _add_historical_incident(
            db_session,
            inc_code=f"INC-SCAN-SIB-{i}",
            rule_id=scan_rule.id,
            event_type=scan_rule.event_type,
        )
    for i in range(3):
        await _add_historical_incident(
            db_session,
            inc_code=f"INC-FIXED-SIB-{i}",
            rule_id=fixed_rule.id,
            event_type=fixed_rule.event_type,
        )
    # Unlinked row with target event_type string, but raw_payload specifies the fixed-port sibling ruleId
    await _add_historical_incident(
        db_session,
        inc_code="INC-FIXED-PAYLOAD-TAGGED",
        rule_id=None,
        event_type=scan_rule.event_type,
        extra_payload={"ruleId": "PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT"},
    )
    await db_session.commit()

    assert (await resolve_canonical_rule(db_session, "PH_RULE_HEAVY_TCP_HOST_SCAN")).id == scan_rule.id
    assert (await resolve_canonical_rule(db_session, "PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT")).id == fixed_rule.id

    sim = PolicySimulationService(db_session)
    res = await sim.evaluate_candidate_policy(
        rule_id="PH_RULE_HEAVY_TCP_HOST_SCAN", candidate_version=pv_scan
    )
    assert res["rule_matched"] == 2
    evaluated_ids = {item["incident_id"] for item in res["stage_details"]["evaluated"]}
    assert evaluated_ids == {"INC-SCAN-SIB-0", "INC-SCAN-SIB-1"}
    assert "INC-FIXED-PAYLOAD-TAGGED" not in evaluated_ids


@pytest.mark.asyncio
async def test_3_unlinked_unambiguous_event_type_included_ambiguous_isolated(db_session: AsyncSession):
    """AC-3: Unlinked incidents with globally unique event_type match cleanly; shared ambiguous event_types stay isolated."""
    unique_rule, _, pv_u = await _seed_rule_with_approved_policy(
        db_session,
        rule_id_str="PH_RULE_UNIQUE_EVT",
        name="Unique Event Scan",
        event_type="UNIQUE_SCAN_EVENT",
    )
    for i in range(2):
        await _add_historical_incident(
            db_session,
            inc_code=f"INC-UNLINKED-UNIQUE-{i}",
            rule_id=None,
            event_type="UNIQUE_SCAN_EVENT",
        )

    # Two distinct rules sharing an ambiguous event_type
    amb_rule_a, _, pv_a = await _seed_rule_with_approved_policy(
        db_session,
        rule_id_str="PH_RULE_AMBIG_A",
        name="Ambiguous Rule A",
        event_type="SHARED_EVENT_TYPE",
    )
    amb_rule_b, _, _ = await _seed_rule_with_approved_policy(
        db_session,
        rule_id_str="PH_RULE_AMBIG_B",
        name="Ambiguous Rule B",
        event_type="SHARED_EVENT_TYPE",
    )
    await _add_historical_incident(
        db_session,
        inc_code="INC-UNLINKED-AMBIGUOUS",
        rule_id=None,
        event_type="SHARED_EVENT_TYPE",
    )
    await db_session.commit()

    sim = PolicySimulationService(db_session)
    res_unique = await sim.evaluate_candidate_policy(rule_id=unique_rule.id, candidate_version=pv_u)
    assert res_unique["rule_matched"] == 2

    res_amb = await sim.evaluate_candidate_policy(rule_id=amb_rule_a.id, candidate_version=pv_a)
    assert res_amb["rule_matched"] == 0
    assert await resolve_canonical_rule(db_session, "SHARED_EVENT_TYPE") is None


@pytest.mark.asyncio
async def test_4_paginated_retrieval_over_50_incidents(db_session: AsyncSession):
    """AC-4: More than 50 matching incidents are completely retrieved via pagination."""
    rule, _, pv = await _seed_rule_with_approved_policy(
        db_session,
        rule_id_str="PH_RULE_PAGINATED_SCAN",
        name="Paginated Scan Rule",
        event_type="PH_RULE_PAGINATED_SCAN",
    )
    for i in range(65):
        await _add_historical_incident(
            db_session,
            inc_code=f"INC-PAGE-{i:03d}",
            rule_id=rule.id,
            event_type=rule.event_type,
            resolution="True Positive" if i % 2 == 0 else "False Positive",
            comments="Verified SOC investigation outcome",
            src_ip=f"198.51.101.{i + 1}",
        )
    await db_session.commit()

    sim = PolicySimulationService(db_session)
    res = await sim.evaluate_candidate_policy(
        rule_id=rule.id,
        candidate_version=pv,
        sample_limit=None,
    )
    assert res["available_count"] == 65
    assert res["retrieved_count"] == 65
    assert res["rule_matched"] == 65
    assert res["verified_count"] == 65
    assert res["scored_count"] == 65


@pytest.mark.asyncio
async def test_5_ml_word_boundary_and_human_provenance_safeguards(db_session: AsyncSession):
    """AC-5: Fixes 'ml' substring bug ('normal','html','xml','email') and never trusts cleared_user blindly."""
    for benign_word in (
        "Normal scheduled scanner traffic reviewed by analyst",
        "HTML dashboard artifact verified as benign administrative script",
        "XML export triggered during authorized maintenance window",
        "Email relay test verified legitimate",
    ):
        extracted = FortiSIEMService.extract_ground_truth_data(
            {"resolution": "False Positive", "comments": benign_word, "clearedUser": "soc_l2"}
        )
        assert extracted["is_ml_generated"] is False

    for actual_ml in (
        "Resolution set by Machine Learning",
        "Closed via ML auto-triage",
        "Automated closure applied",
    ):
        extracted = FortiSIEMService.extract_ground_truth_data(
            {"resolution": "False Positive", "comments": actual_ml, "clearedUser": "soc_l2"}
        )
        assert extracted["is_ml_generated"] is True

    # RuleParser preserves Pattern Conditions:
    parsed = RuleParser.parse_rule_text(
        "Name: Heavy TCP Host Scan\nEvent Type: PH_RULE_HEAVY_TCP_HOST_SCAN\nPattern Conditions:\ncount(destIpAddr) >= 50\n"
    )
    assert "50" in parsed["pattern_logic"]

    # DB verification: 'Normal' comment preserves human FP; ML with cleared_user stays excluded;
    # independent human Investigation provenance promotes verified outcome even if old ingestion had is_ml_generated=True
    rule, _, pv = await _seed_rule_with_approved_policy(db_session)
    await _add_historical_incident(
        db_session,
        inc_code="INC-ML-NORMAL-COMMENT",
        rule_id=rule.id,
        event_type=rule.event_type,
        resolution="False Positive",
        comments="Normal scheduled Nessus backup scan confirmed benign.",
        is_ml_generated=False,
    )
    await _add_historical_incident(
        db_session,
        inc_code="INC-ML-CLEARED-USER-NO-PROVENANCE",
        rule_id=rule.id,
        event_type=rule.event_type,
        resolution="False Positive",
        comments="Auto cleared by ML classifier",
        cleared_user="random_user",
        cleared_reason="Normal closure",
        is_ml_generated=True,
    )
    await _add_historical_incident(
        db_session,
        inc_code="INC-HUMAN-INV-OVERRIDE",
        rule_id=rule.id,
        event_type=rule.event_type,
        resolution="False Positive",
        comments="Legacy auto-tag later independently audited",
        is_ml_generated=True,
        with_investigation=Investigation(
            status="REVIEWED",
            analyst_verdict="FALSE_POSITIVE",
            verdict_reason="Independently verified change ticket CHG-8812.",
            is_disputed=False,
            is_independently_verified=True,
        ),
    )
    await db_session.commit()

    assert (
        HistoricalGroundTruthValidator.is_containment_only_fp_note(
            raw_resolution="False Positive",
            cleared_reason="kill process executed",
            cleared_user="ops_script",
        )
        is True
    )

    sim = PolicySimulationService(db_session)
    res = await sim.evaluate_candidate_policy(rule_id=rule.id, candidate_version=pv)
    eligible_ids = {item["incident_id"] for item in res["stage_details"]["eligible"]}
    assert "INC-ML-NORMAL-COMMENT" in eligible_ids
    assert "INC-HUMAN-INV-OVERRIDE" in eligible_ids
    assert "INC-ML-CLEARED-USER-NO-PROVENANCE" not in eligible_ids
    assert res["exclusion_reasons"]["HEURISTIC_OR_ML_LABEL"] == 1


@pytest.mark.asyncio
async def test_6_disputed_ambiguous_synthetic_excluded_from_g8_and_unlabeled_isolated(
    db_session: AsyncSession,
):
    """AC-6: Disputed/ambiguous/synthetic/unverified excluded from G8 scoring; exploratory unlabeled replay isolated."""
    rule, _, pv = await _seed_rule_with_approved_policy(db_session)

    # 5 verified cases
    for i in range(5):
        await _add_historical_incident(
            db_session,
            inc_code=f"INC-VALID-{i}",
            rule_id=rule.id,
            event_type=rule.event_type,
            resolution="True Positive" if i < 3 else "False Positive",
            comments="Verified Tier-2 investigation with packet capture." if i < 3 else "Authorized scheduled backup maintenance task.",
        )

    # 1 Disputed investigation (even with SIEM resolution)
    await _add_historical_incident(
        db_session,
        inc_code="INC-DISPUTED-1",
        rule_id=rule.id,
        event_type=rule.event_type,
        resolution="True Positive",
        comments="Initial escalation",
        with_investigation=Investigation(
            status="REVIEWED",
            analyst_verdict="FALSE_POSITIVE",
            verdict_reason="Analyst disagrees on intent",
            is_disputed=True,
            is_independently_verified=False,
        ),
    )
    # 1 Ambiguous closure
    await _add_historical_incident(
        db_session,
        inc_code="INC-AMBIGUOUS-1",
        rule_id=rule.id,
        event_type=rule.event_type,
        resolution="Manually Cleared",
        comments="Cleared in console",
    )
    # 1 Synthetic fixture
    await _add_historical_incident(
        db_session,
        inc_code="INC-DEBUG-SYNTHETIC-1",
        rule_id=rule.id,
        event_type=rule.event_type,
        resolution="True Positive",
        extra_payload={"is_synthetic": True},
        with_event=False,
    )
    # 2 Unlabeled open incidents
    for i in range(2):
        await _add_historical_incident(
            db_session,
            inc_code=f"INC-UNLABELED-{i}",
            rule_id=rule.id,
            event_type=rule.event_type,
            resolution=None,
        )
    await db_session.commit()

    sim = PolicySimulationService(db_session)
    strict_res = await sim.evaluate_candidate_policy(rule_id=rule.id, candidate_version=pv)
    assert strict_res["retrieved_count"] == 10
    assert strict_res["verified_count"] == 5
    assert strict_res["excluded_count"] == 5
    assert strict_res["inferred_count"] == 5
    assert strict_res["scored_count"] == 5
    assert strict_res["exclusion_reasons"]["DISPUTED_LABEL"] == 1
    assert strict_res["exclusion_reasons"]["AMBIGUOUS_LABEL"] == 1
    assert strict_res["exclusion_reasons"]["SYNTHETIC_FIXTURE_EXCLUDED"] == 1
    assert strict_res["exclusion_reasons"]["MISSING_ANALYST_LABEL"] == 2

    # With exploratory replay enabled, unlabeled rows execute but remain strictly isolated from G8 scored metrics
    exp_res = await sim.evaluate_candidate_policy(
        rule_id=rule.id,
        candidate_version=pv,
        include_unlabeled_replay=True,
    )
    assert exp_res["exploratory_replay_count"] == 2
    assert exp_res["inferred_count"] == 7
    assert exp_res["scored_count"] == 5
    assert exp_res["verified_count"] == 5


@pytest.mark.asyncio
async def test_7_and_8_real_llm_simulation_provenance_vs_simulated_blocked_from_g8(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
    analyst_token: str,
    monkeypatch: pytest.MonkeyPatch,
):
    """AC-7 & AC-8: OPENAI_COMPATIBLE simulation invokes real HTTP LLM and passes G8; SIMULATED never passes G8."""
    captured_requests = []

    class _MockLLMHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if "/models" in self.path or "/health" in self.path:
                body = json.dumps({"data": [{"id": "qwen3-local-audit"}]}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(404)
            self.end_headers()

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode("utf-8")
            req_json = json.loads(raw)
            captured_requests.append(req_json)
            user_content = str((req_json.get("messages") or [{}])[-1].get("content", ""))
            # Ensure zero ground-truth leakage keys are present in model prompt
            assert "historical_ground_truth" not in user_content.lower()
            assert "verified tier-2 human proof" not in user_content.lower()

            grounded_claims = []
            try:
                req_obj = json.loads(user_content)
                for ev in (req_obj.get("incident") or {}).get("canonical_evidence") or []:
                    if ev.get("source_field") in ("network.source_ip", "network.destination_ip", "network.destination_port"):
                        grounded_claims.append({
                            "claim_type": "NETWORK_CONNECTION",
                            "field": ev["source_field"],
                            "asserted_value": str(ev["observed_value"]),
                            "evidence_ids": [ev["evidence_id"]],
                        })
            except Exception:
                pass

            if "198.51.100.31" in user_content:
                verdict_json = {
                    "verdict": "FALSE_POSITIVE",
                    "confidence": 91,
                    "reason": "Authorized backup scanner activity verified on 198.51.100.31 targeting 192.0.2.50:445 under change ticket CHG-4001.",
                    "supporting_evidence": ["198.51.100.31", "192.0.2.50", "445", "CHG-4001"],
                    "supporting_claims": grounded_claims,
                }
            else:
                verdict_json = {
                    "verdict": "TRUE_POSITIVE",
                    "confidence": 93,
                    "reason": "Observed horizontal TCP scan from 198.51.100.11 probing port 445 across subnet against 192.0.2.50.",
                    "supporting_evidence": ["198.51.100.11", "192.0.2.50", "445"],
                    "supporting_claims": grounded_claims,
                }

            payload = {
                "id": "chatcmpl-ais21",
                "model": "qwen3-local-audit",
                "choices": [{"message": {"role": "assistant", "content": json.dumps(verdict_json)}}],
                "usage": {"prompt_tokens": 220, "completion_tokens": 55, "total_tokens": 275},
            }
            out = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(out)

        def log_message(self, format, *args):
            return

    server, _ = _start_mock_openai_server(_MockLLMHandler)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}/v1"
        monkeypatch.setattr(LLMConfigService, "sync_runtime_settings", classmethod(lambda cls: False))
        monkeypatch.setattr(settings, "LOCAL_LLM_BASE_URL", base_url)
        monkeypatch.setattr(settings, "LOCAL_LLM_MODEL_NAME", "qwen3-local-audit")
        monkeypatch.setattr(settings, "LOCAL_LLM_ALLOW_MOCK_FALLBACK", False)
        VerdictTriageAgent._is_local_llm_online = None
        gpu_workload_manager.consecutive_failures = 0
        gpu_workload_manager.circuit_open_until = 0.0

        rule, _, pv = await _seed_rule_with_approved_policy(db_session)
        for i in range(4):
            await _add_historical_incident(
                db_session,
                inc_code=f"INC-REAL-TP-{i}",
                rule_id=rule.id,
                event_type=rule.event_type,
                resolution="True Positive",
                comments="Verified Tier-2 human proof of unauthorized scan.",
                src_ip="198.51.100.11",
            )
        for i in range(2):
            await _add_historical_incident(
                db_session,
                inc_code=f"INC-REAL-FP-{i}",
                rule_id=rule.id,
                event_type=rule.event_type,
                resolution="False Positive",
                comments="Verified Tier-2 human proof: authorized backup activity.",
                src_ip="198.51.100.31",
                extra_payload={"authorization_ticket": "CHG-4001", "note": "authorized scheduled backup"},
            )
        await db_session.commit()

        # AC-8: SIMULATED run NEVER passes G8
        sim_http_res = await client.post(
            f"/api/prompts/rule/{rule.id}/evaluate-simulation?version_id={pv.id}&provider_type=SIMULATED",
            headers=_auth(analyst_token),
        )
        assert sim_http_res.status_code == 200
        sim_body = sim_http_res.json()
        assert sim_body["status"] == "SIMULATED_ONLY"
        assert sim_body["simulation_status"] == SimulationStatus.NOT_EVALUATED.value
        assert sim_body["certifying_empirical_eligible"] is False
        assert sim_body["is_simulated"] is True
        assert len(captured_requests) == 0

        q_sim_res = await client.get(
            f"/api/prompts/rule/{rule.id}/quality-preview?version_id={pv.id}",
            headers=_auth(analyst_token),
        )
        assert q_sim_res.status_code == 200
        q_sim = q_sim_res.json()
        assert q_sim["gate_results"]["G8_SIMULATION_REGRESSION"]["score"] == 0.0
        assert q_sim["empirical_validation_eligible"] is False
        assert q_sim["autonomous_operation_eligible"] is False

        # AC-7: OPENAI_COMPATIBLE executes real HTTP endpoint and certifies G8
        real_http_res = await client.post(
            f"/api/prompts/rule/{rule.id}/evaluate-simulation?version_id={pv.id}&provider_type=OPENAI_COMPATIBLE",
            headers=_auth(analyst_token),
        )
        assert real_http_res.status_code == 200
        real_body = real_http_res.json()
        assert len(captured_requests) == 6
        assert real_body["provider_type"] == "OPENAI_COMPATIBLE"
        assert real_body["is_simulated"] is False
        assert real_body["execution_provenance"] != "SIMULATED"
        assert real_body["model_identifier"] == "qwen3-local-audit"
        assert real_body["token_usage"]["total_tokens"] > 0
        assert real_body["certifying_empirical_eligible"] is True
        assert real_body["simulation_status"] == SimulationStatus.EVALUATED_PASSED.value

        # Check TokenUsageRecord & HistoricalEvaluationResultRecord provenance
        tu_rows = (
            await db_session.execute(
                select(TokenUsageRecord).where(TokenUsageRecord.process_id == real_body["run_id"])
            )
        ).scalars().all()
        assert len(tu_rows) == 6
        assert all(t.process_type == "POLICY_SIMULATION" and not t.is_simulated for t in tu_rows)

        res_rows = (
            await db_session.execute(
                select(HistoricalEvaluationResultRecord).where(
                    HistoricalEvaluationResultRecord.run_id == real_body["run_id"]
                )
            )
        ).scalars().all()
        assert len(res_rows) == 6
        assert all(
            (r.claims_summary or {}).get("evidence_trace", {}).get("provider_type") == "OPENAI_COMPATIBLE"
            and (r.claims_summary or {}).get("policy_digest") == real_body["policy_digest"]
            for r in res_rows
        )

        # Quality preview now grants G8 empirical pass & autonomous eligibility
        q_real_res = await client.get(
            f"/api/prompts/rule/{rule.id}/quality-preview?version_id={pv.id}",
            headers=_auth(analyst_token),
        )
        assert q_real_res.status_code == 200
        q_real = q_real_res.json()
        assert q_real["simulation_status"] == SimulationStatus.EVALUATED_PASSED.value
        assert q_real["gate_results"]["G8_SIMULATION_REGRESSION"]["status"] == GateStatus.PASSED.value
        assert q_real["empirical_validation_eligible"] is True
        assert q_real["autonomous_operation_eligible"] is True
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.asyncio
async def test_9_simulation_and_live_share_verdict_safeguards_and_port_normalization(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    """AC-9: Normalization of 'Destination Port' in rawEvents, invalid model output abstention, & preflight parity."""
    rule, _, pv = await _seed_rule_with_approved_policy(db_session)
    inc_valid = Incident(
        id=str(uuid.uuid4()),
        incident_id="INC-PORT-NORM-01",
        rule_id=rule.id,
        event_type=rule.event_type,
        title="Heavy scan port 22",
        severity="HIGH",
        source_ip="198.51.100.77",
        raw_payload={
            "attributes": {"vendor": "FortiGate"},
            "rawEvents": [{"srcIpAddr": "198.51.100.77", "destIpAddr": "192.0.2.88", "Destination Port": 22}],
        },
        first_seen_epoch=1710000000000,
        created_at_epoch=1710000000000,
    )
    db_session.add(inc_valid)
    await db_session.flush()
    db_session.add(
        HistoricalGroundTruth(
            incident_id=inc_valid.id,
            resolution="True Positive",
            comments="Verified SSH host scan from unauthorized external IP.",
            cleared_user="tier2_analyst",
            is_ml_generated=False,
        )
    )
    inc_empty = Incident(
        id=str(uuid.uuid4()),
        incident_id="INC-PREFLIGHT-EMPTY-01",
        rule_id=rule.id,
        event_type=rule.event_type,
        title="Incomplete scan",
        severity="HIGH",
        source_ip="",
        raw_payload={"rawEvents": [{"note": "incomplete telemetry without ips or ports"}]},
    )
    db_session.add(inc_empty)
    await db_session.flush()
    db_session.add(
        HistoricalGroundTruth(
            incident_id=inc_empty.id,
            resolution="True Positive",
            comments="Verified scan",
            is_ml_generated=False,
        )
    )
    await db_session.commit()

    # Check Destination Port extraction from rawEvents & EvidenceSufficiencyEngine match
    norm = EvidenceNormalizationService.normalize_incident_evidence(inc_valid, [])
    fields = {r.source_field: r.observed_value for r in norm.records}
    assert str(fields.get("network.destination_port")) == "22"
    suff = EvidenceSufficiencyEngine.evaluate_incident_sufficiency(
        {"canonical_evidence": [r.model_dump() for r in norm.records]},
        archetype_id="NETWORK_SCAN",
    )
    assert suff.overall_sufficiency_score > 0

    # Malformed model response server -> BOTH Simulation and Live abstain safely with REQUIRES_ATTENTION & trust <= 2
    class _MalformedHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"data": [{"id": "bad-json-model"}]}).encode("utf-8"))

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            _ = self.rfile.read(length)
            body = json.dumps({
                "model": "bad-json-model",
                "choices": [{"message": {"role": "assistant", "content": "NOT_JSON_AT_ALL"}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110},
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    server, _ = _start_mock_openai_server(_MalformedHandler)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}/v1"
        monkeypatch.setattr(LLMConfigService, "sync_runtime_settings", classmethod(lambda cls: False))
        monkeypatch.setattr(settings, "LOCAL_LLM_BASE_URL", base_url)
        monkeypatch.setattr(settings, "LOCAL_LLM_MODEL_NAME", "bad-json-model")
        monkeypatch.setattr(settings, "LOCAL_LLM_ALLOW_MOCK_FALLBACK", False)
        VerdictTriageAgent._is_local_llm_online = None
        gpu_workload_manager.consecutive_failures = 0
        gpu_workload_manager.circuit_open_until = 0.0

        # Simulation through OPENAI_COMPATIBLE: inc_valid abstains on invalid model output; inc_empty abstains on preflight!
        sim = PolicySimulationService(db_session)
        sim_res = await sim.evaluate_candidate_policy(
            rule_id=rule.id,
            candidate_version=pv,
            provider_type="OPENAI_COMPATIBLE",
        )
        per_inc = {r["incident_id"]: r for r in sim_res["per_incident_results"]}
        assert per_inc["INC-PORT-NORM-01"]["effective_verdict"] == "REQUIRES_ATTENTION"
        assert per_inc["INC-PORT-NORM-01"]["trust_score"] <= 2
        assert per_inc["INC-PREFLIGHT-EMPTY-01"]["effective_verdict"] == "REQUIRES_ATTENTION"

        # Live VerdictTriageAgent shares identical abstention behavior
        agent = VerdictTriageAgent(db_session)
        live_valid = await agent.evaluate_incident(
            inc_valid.id,
            model_provider_type="OPENAI_COMPATIBLE",
            allow_simulated_fallback=False,
        )
        live_empty = await agent.evaluate_incident(
            inc_empty.id,
            model_provider_type="OPENAI_COMPATIBLE",
            allow_simulated_fallback=False,
        )
        assert live_valid["verdict"] == "REQUIRES_ATTENTION"
        assert live_valid["trust_score"] <= 2
        assert live_valid["validation_status"] == "INVALID_MODEL_OUTPUT"
        assert live_empty["verdict"] == "REQUIRES_ATTENTION"
        assert live_empty["model_identifier"] == "PREFLIGHT_GUARD"
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.asyncio
async def test_10_historical_replay_does_not_mutate_live_incident_state(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    """AC-10: Replay (verified and exploratory unlabeled) leaves Incident.ai_verdict, status, Investigation & GT untouched."""
    rule, _, pv = await _seed_rule_with_approved_policy(db_session)
    inc_labeled = await _add_historical_incident(
        db_session,
        inc_code="INC-NOMUTATE-01",
        rule_id=rule.id,
        event_type=rule.event_type,
        resolution="True Positive",
        comments="Original human verification comment.",
        with_investigation=Investigation(
            status="REVIEWED",
            analyst_verdict="TRUE_POSITIVE",
            verdict_reason="Confirmed malicious host scan",
            analyst_notes="Original analyst triage note.",
            is_independently_verified=True,
        ),
    )
    inc_unlabeled = await _add_historical_incident(
        db_session,
        inc_code="INC-NOMUTATE-UNLABELED",
        rule_id=rule.id,
        event_type=rule.event_type,
        resolution=None,
    )
    await db_session.commit()

    sim = PolicySimulationService(db_session)
    await sim.evaluate_candidate_policy(
        rule_id=rule.id,
        candidate_version=pv,
        provider_type="SIMULATED",
        include_unlabeled_replay=True,
    )

    refreshed_1 = (await db_session.execute(select(Incident).where(Incident.id == inc_labeled.id))).scalar_one()
    refreshed_2 = (await db_session.execute(select(Incident).where(Incident.id == inc_unlabeled.id))).scalar_one()
    inv_1 = (await db_session.execute(select(Investigation).where(Investigation.incident_id == inc_labeled.id))).scalar_one()
    gt_1 = (await db_session.execute(select(HistoricalGroundTruth).where(HistoricalGroundTruth.incident_id == inc_labeled.id))).scalar_one()

    assert refreshed_1.ai_verdict is None
    assert refreshed_1.status_code == 2
    assert refreshed_2.ai_verdict is None
    assert refreshed_2.status_code == 1
    assert inv_1.analyst_notes == "Original analyst triage note."
    assert gt_1.resolution == "True Positive"
    assert gt_1.comments == "Original human verification comment."


@pytest.mark.asyncio
async def test_11_uncertified_policy_blocked_from_autonomous_actions_advisory_allowed(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    """AC-11: Uncertified, simulated, failed, or stale-digest policies cannot run autonomously; analyst-assisted stays advisory."""
    rule, rp, pv = await _seed_rule_with_approved_policy(db_session)
    inc = await _add_historical_incident(
        db_session,
        inc_code="INC-GOV-LIVE-01",
        rule_id=rule.id,
        event_type=rule.event_type,
        resolution=None,
    )
    await db_session.commit()

    # Deterministic mock OpenAI response for Analyst-Assisted & Certified checks
    class _CleanHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"data": [{"id": "qwen3-gov"}]}).encode("utf-8"))

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            req_json = json.loads(self.rfile.read(length).decode("utf-8"))
            user_content = str((req_json.get("messages") or [{}])[-1].get("content", ""))
            grounded_claims = []
            try:
                req_obj = json.loads(user_content)
                for ev in (req_obj.get("incident") or {}).get("canonical_evidence") or []:
                    if ev.get("source_field") in ("network.source_ip", "network.destination_ip", "network.destination_port"):
                        grounded_claims.append({
                            "claim_type": "NETWORK_CONNECTION",
                            "field": ev["source_field"],
                            "asserted_value": str(ev["observed_value"]),
                            "evidence_ids": [ev["evidence_id"]],
                        })
            except Exception:
                pass
            v = {
                "verdict": "TRUE_POSITIVE",
                "confidence": 92,
                "reason": "Confirmed scan telemetry from 198.51.100.10 to 192.0.2.50:445.",
                "supporting_evidence": ["198.51.100.10", "192.0.2.50", "445"],
                "supporting_claims": grounded_claims,
            }
            out = json.dumps({
                "model": "qwen3-gov",
                "choices": [{"message": {"role": "assistant", "content": json.dumps(v)}}],
                "usage": {"prompt_tokens": 150, "completion_tokens": 40, "total_tokens": 190},
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(out)

        def log_message(self, format, *args):
            return

    server, _ = _start_mock_openai_server(_CleanHandler)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}/v1"
        monkeypatch.setattr(LLMConfigService, "sync_runtime_settings", classmethod(lambda cls: False))
        monkeypatch.setattr(settings, "LOCAL_LLM_BASE_URL", base_url)
        monkeypatch.setattr(settings, "LOCAL_LLM_MODEL_NAME", "qwen3-gov")
        monkeypatch.setattr(settings, "LOCAL_LLM_ALLOW_MOCK_FALLBACK", False)
        VerdictTriageAgent._is_local_llm_online = None
        gpu_workload_manager.consecutive_failures = 0
        gpu_workload_manager.circuit_open_until = 0.0

        agent = VerdictTriageAgent(db_session)

        # Case A: Approved policy WITHOUT empirical validation -> AUTONOMOUS blocked, ANALYST_ASSISTED stays advisory
        auto_blocked = await agent.evaluate_incident(
            inc.id,
            model_provider_type="OPENAI_COMPATIBLE",
            execution_context="AUTONOMOUS",
        )
        assert auto_blocked["verdict"] == "REQUIRES_ATTENTION"
        assert auto_blocked["final_disposition"] == "BLOCKED_UNCERTIFIED_FOR_AUTONOMOUS_ACTION"
        assert auto_blocked["autonomous_operation_eligible"] is False
        assert auto_blocked["autonomous_action_blocked"] is True

        advisory = await agent.evaluate_incident(
            inc.id,
            model_provider_type="OPENAI_COMPATIBLE",
            execution_context="ANALYST_ASSISTED",
        )
        assert advisory["verdict"] == "TRUE_POSITIVE"
        assert advisory["policy_governance_mode"] == "ADVISORY_ANALYST_REVIEW_REQUIRED"
        assert advisory["autonomous_operation_eligible"] is False
        assert advisory["autonomous_action_blocked"] is True
        assert advisory["auto_incident_closure_allowed"] is False
        assert advisory["external_writeback_allowed"] is False
        assert advisory["requires_human_review"] is True

        # Pilot with autonomous closure enabled MUST also block uncertified policy!
        pilot_cfg = PilotConfiguration(
            pilot_name="Autonomous Block Test",
            version_number=1,
            is_active_config=True,
            mode=PilotMode.SHADOW.value,
            allow_auto_incident_closure=True,
            allow_external_writeback=False,
            require_analyst_review=False,
        )
        db_session.add(pilot_cfg)
        await db_session.flush()
        pilot_res = await PilotService(db_session).evaluate_incident_for_pilot(inc.incident_id, actor="test_admin")
        assert pilot_res["validated_verdict"] == "REQUIRES_ATTENTION"
        assert pilot_res["autonomous_action_blocked"] is True

        # Case B: Seed ONLY a SIMULATED run -> STILL blocked from autonomous!
        active_digest = PolicyQualityValidator.compute_policy_digest(pv)
        sim_only_run = HistoricalEvaluationRunRecord(
            id=str(uuid.uuid4()),
            run_name="Simulated Non-Certifying",
            rule_id=rule.id,
            policy_version_id=pv.id,
            status="COMPLETED",
            validation_state="PASSED",
            total_cases=10,
            evaluated_cases=10,
            verified_ground_truth_cases=10,
            metrics={"evaluated_cases": 10, "eligible_cases": 10, "critical_regressions": 0},
            config_snapshot={"provider_type": "SIMULATED", "is_simulated": True, "policy_digest": active_digest},
        )
        db_session.add(sim_only_run)
        await db_session.commit()
        res_b = await agent.evaluate_incident(inc.id, execution_context="AUTONOMOUS")
        assert res_b["final_disposition"] == "BLOCKED_UNCERTIFIED_FOR_AUTONOMOUS_ACTION"

        # Case C: Seed REAL OPENAI_COMPATIBLE run, then mutate policy -> STALE digest blocked!
        real_run = HistoricalEvaluationRunRecord(
            id=str(uuid.uuid4()),
            run_name="Real Empirical Run",
            rule_id=rule.id,
            policy_version_id=pv.id,
            status="COMPLETED",
            validation_state="PASSED",
            total_cases=8,
            evaluated_cases=8,
            verified_ground_truth_cases=8,
            metrics={"evaluated_cases": 8, "eligible_cases": 8, "critical_regressions": 0},
            config_snapshot={"provider_type": "OPENAI_COMPATIBLE", "is_simulated": False, "policy_digest": active_digest},
        )
        db_session.add(real_run)
        await db_session.flush()
        pv.rule_specific_prompt = "Edited prompt text after empirical simulation ran!"
        await db_session.commit()

        res_c = await agent.evaluate_incident(inc.id, execution_context="AUTONOMOUS")
        assert res_c["final_disposition"] == "BLOCKED_UNCERTIFIED_FOR_AUTONOMOUS_ACTION"
        assert "STALE_POLICY_DIGEST" in res_c["validation_reason_codes"]

        # Case D: Update real run digest to match exact active policy -> autonomous becomes ELIGIBLE!
        new_digest = PolicyQualityValidator.compute_policy_digest(pv)
        real_run.config_snapshot = {
            "provider_type": "OPENAI_COMPATIBLE",
            "is_simulated": False,
            "policy_digest": new_digest,
        }
        await db_session.commit()

        res_d = await agent.evaluate_incident(
            inc.id,
            model_provider_type="OPENAI_COMPATIBLE",
            execution_context="AUTONOMOUS",
        )
        assert res_d["verdict"] == "TRUE_POSITIVE"
        assert res_d["autonomous_operation_eligible"] is True
        assert res_d["autonomous_action_blocked"] is False
        assert res_d["policy_governance_mode"] == "EMPIRICALLY_CERTIFIED"
    finally:
        server.shutdown()
        server.server_close()
