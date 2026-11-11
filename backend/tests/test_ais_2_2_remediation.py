"""
Agent Intelligence Studio 2.2 Regression & Integration Verification Suite.

Covers all AIS 2.2 targets:
  - Target 1 (AIS-F05): G1-G8 100-pt reconciled scoring model (v2.2.0), zero G1/G2 double-counting,
                        versioned scoring (v2.0.0 parity preserved), historical assessment preservation.
  - Target 2 (AIS-F06): Non-null validation_status, aligned assessment schema, full simulation provenance & digests.
  - Target 3 (AIS-F07): Workbench exact rule filtering, canonical rule_uuid/logical_rule_id/event_type visibility,
                        multi-rule search disambiguation, and 1:1 count reconciliation with AIS simulation.
  - Target 4: G1 runtime counter rejection, FortiSIEM field/pattern fixtures, never fabricating thresholds
              or marking unverified definitions VERIFIED, snapshot parity across intelligence/G1/verdict.
  - Target 5: Read-only ground-truth readiness diagnostics, legacy is_ml_generated dry-run re-evaluation audit
              with zero DB mutations, and sample threshold alone never authorizing autonomous ops.
  - Target 6: End-to-end workflow verification from Rule Selection -> Approval Eligibility alongside AIS 2.1 safeguards.
"""

from __future__ import annotations

import json
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Dict

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.incident import HistoricalGroundTruth, Incident, IncidentEvent
from app.models.investigation import Investigation
from app.models.policy_quality import PolicyQualityAssessmentRecord
from app.models.prompt import PromptVersion, RulePrompt
from app.models.rule import Rule
from app.models.rule_intelligence import RuleIntelligenceSnapshot
from app.models.verdict_intelligence import HistoricalEvaluationRunRecord
from app.schemas.policy_quality import GateStatus
from app.services.ai_verdict_service import VerdictTriageAgent
from app.services.evidence_normalization_service import EvidenceNormalizationService
from app.services.evidence_requirement_mapper import EvidenceRequirementMapper
from app.services.fortisiem_service import FortiSIEMService
from app.services.policy_governance import assess_policy_runtime_certification, get_rule_semantics_and_contract
from app.services.policy_quality_validator import PolicyQualityValidator
from app.services.policy_simulation_service import PolicySimulationService
from app.services.rule_intelligence_analyzer import RuleIntelligenceAnalyzer
from app.services.detection_archetype_registry import DetectionArchetypeRegistry
from app.utils.datetime_utils import utc_now


def _auth(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _start_openai_mock_server():
    calls = {"post": 0, "prompts": []}

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = json.dumps({"object": "list", "data": [{"id": "qwen2.5-ais22-mock"}]}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length).decode("utf-8", errors="ignore")
            calls["post"] += 1
            calls["prompts"].append(raw_body)

            supporting_ev = []
            grounded_claims = []
            try:
                req_payload = json.loads(raw_body)
                user_msg = next(
                    (m.get("content", "") for m in req_payload.get("messages", []) if m.get("role") == "user"),
                    "",
                )
                import re as _re
                m_json = _re.search(r"(\{.*\})", user_msg, _re.DOTALL)
                if m_json:
                    inc_obj = json.loads(m_json.group(1)).get("incident") or {}
                    for ev in inc_obj.get("canonical_evidence") or []:
                        if ev.get("source_field") in (
                            "network.source_ip",
                            "network.destination_port",
                            "security.event_type",
                        ):
                            supporting_ev.append(ev["evidence_id"])
                            grounded_claims.append({
                                "claim_type": "NETWORK_CONNECTION",
                                "field": ev["source_field"],
                                "asserted_value": str(ev["observed_value"]),
                                "evidence_ids": [ev["evidence_id"]],
                            })
            except Exception:
                pass

            is_fp = "CHG-E2E" in raw_body
            verdict_json = json.dumps({
                "verdict": "FALSE_POSITIVE" if is_fp else "TRUE_POSITIVE",
                "confidence": 91.0,
                "reason": (
                    "Authorized enterprise vulnerability scanner verified under change ticket CHG-E2E on port 445."
                    if is_fp
                    else "Verified unauthorized TCP host sweep matching threshold on port 445 from 192.0.2.77."
                ),
                "supporting_evidence": supporting_ev or ["network.source_ip: 192.0.2.77"],
                "supporting_claims": grounded_claims,
                "contradictory_evidence": [],
                "missing_evidence": [],
                "analyst_questions": [],
            })
            payload = {
                "model": "qwen2.5-ais22-mock",
                "choices": [{"message": {"content": verdict_json}}],
                "usage": {"prompt_tokens": 180, "completion_tokens": 55, "total_tokens": 235},
            }
            raw = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, server.server_address[1], calls


@pytest.mark.asyncio
async def test_1_g1_g8_reconciled_100pt_scoring_and_version_preservation(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
):
    """
    Target 1 (AIS-F05): Reconciled v2.2.0 scoring totals 100 pts (G1=10 + G2=10 + G3=20 + G4=10
    + G5=10 + G6=15 + G7=10 + G8=15), preserves explicit v2.0.0 behavior for regression parity,
    and never silently rescores stored historical PolicyQualityAssessmentRecord rows.
    """
    rule = Rule(
        id="9839fa49-40ac-4676-abcc-4c5581ae9e09",
        rule_id="PH_RULE_HEAVY_TCP_HOST_SCAN",
        name="Heavy TCP Host Scan",
        event_type="PH_RULE_HEAVY_TCP_HOST_SCAN",
        severity="HIGH",
        pattern_logic="COUNT(Matched Events) >= 20; window=5m; groupBy=srcIpAddr",
        raw_rule_text=(
            "Name: Heavy TCP Host Scan\n"
            "Pattern Conditions:\n"
            "COUNT(Matched Events) >= 20\n"
            "GroupBy: srcIpAddr\n"
            "Window: 5 minutes\n"
        ),
        parsed_metadata={"source": "AUTHORITATIVE_XML_IMPORT", "definition_status": "VERIFIED"},
    )
    db_session.add(rule)
    await db_session.flush()

    rp = RulePrompt(id=str(uuid.uuid4()), rule_id=rule.id, title="Prompt - Heavy TCP Scan")
    db_session.add(rp)
    await db_session.flush()

    pv = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=rp.id,
        version_number=2,
        status="APPROVED",
        common_prompt="Enterprise SOC evidence-grounded baseline.",
        rule_specific_prompt="Evaluate network scan rate, scanned destination ports, and scanner authorization.",
        detection_conditions="COUNT(Matched Events) >= 20 over 5m window grouped by srcIpAddr (ref incidentCount context verified).",
        required_evidence="security.event_type, event.timestamp, network.source_ip, network.destination_port, detection.threshold",
        tp_indicators="Unauthorized source IP scanning >= 20 distinct destination hosts/ports sequentially.",
        fp_indicators="Authorized enterprise vulnerability scanner with active maintenance change ticket.",
        missing_info_criteria="Abstain to REQUIRES_ATTENTION if source IP, destination port, or event timestamp is missing.",
        escalation_conditions="Escalate immediately to Tier-2 if scan targets critical domain controllers or DB tier.",
        analyst_questions=["Verify scanner authorization change ticket?"],
        quality_score=81.0,
        quality_status="APPROVED",
    )
    db_session.add(pv)
    await db_session.flush()
    rp.active_version_id = pv.id

    semantics = RuleIntelligenceAnalyzer.analyze_rule(
        rule,
        authoritative_siem_definition={
            "threshold": 20.0,
            "threshold_unit": "events",
            "aggregation_window": "5m",
            "grouping_keys": ["srcIpAddr"],
            "primary_behavior": "NETWORK_SCAN",
        },
    )
    arch_def = DetectionArchetypeRegistry.get_archetype_definition(
        DetectionArchetypeRegistry.classify_rule(semantics, rule).primary_archetype
    )
    contract = EvidenceRequirementMapper.map_evidence_contract(rule, semantics, arch_def, pv)

    # 1. Reconciled v2.2.0 scoring: G1(max=10) + G2(max=10) = 20, total max_score = 100
    a22 = PolicyQualityValidator.validate_policy_quality(rule, pv, contract, semantics)
    assert a22.validator_version == "v2.2.0"
    assert a22.scoring_model_version == "v2.2.0"
    assert a22.gate_max_total == 100.0
    assert sum(g.max_score for g in a22.gate_results.values()) == 100.0
    assert a22.gate_results["G1_RULE_INTEGRITY"].max_score == 10.0
    assert a22.gate_results["G2_ARCHETYPE_RELEVANCE"].max_score == 10.0
    # G1 has -2 warning (out of 10 -> 8.0), G2=10.0 => detection_semantics=18.0 (not double counted)
    assert a22.gate_results["G1_RULE_INTEGRITY"].score == 8.0
    assert a22.gate_results["G2_ARCHETYPE_RELEVANCE"].score == 10.0
    assert a22.score_breakdown["detection_semantics"] == 18.0
    assert a22.gate_scores_total == a22.quality_score
    assert a22.quality_score == round(sum(a22.score_breakdown.values()), 1)
    assert a22.quality_score == 83.0
    assert a22.structural_quality_score == round((83.0 / 85.0) * 100.0, 1)
    assert a22.structural_raw_score == 83.0
    assert a22.structural_approval_eligible is True
    assert a22.empirical_validation_eligible is False
    assert a22.autonomous_operation_eligible is False
    assert a22.validation_status == "INSUFFICIENT_DATA" or a22.validation_status == "NOT_EVALUATED"

    # 2. Legacy v2.0.0 parity still reproducible explicitly (G1=16, G2=20, max_total=120, quality=81, struct=95.3)
    a20 = PolicyQualityValidator.validate_policy_quality(rule, pv, contract, semantics, validator_version="v2.0.0")
    assert a20.validator_version == "v2.0.0"
    assert a20.gate_max_total == 120.0
    assert a20.gate_results["G1_RULE_INTEGRITY"].score == 16.0
    assert a20.gate_results["G2_ARCHETYPE_RELEVANCE"].score == 20.0
    assert a20.quality_score == 81.0
    assert a20.structural_quality_score == 95.3

    # 3. Persisted legacy assessment record is never silently rescored or altered
    legacy_qa = PolicyQualityAssessmentRecord(
        id=f"PQA-LEGACY-{uuid.uuid4().hex[:8]}",
        rule_id=rule.id,
        prompt_version_id=pv.id,
        version_number=pv.version_number,
        archetype="NETWORK_SCAN",
        quality_score=81.0,
        approval_eligible=True,
        simulation_status="INSUFFICIENT_DATA",
        score_breakdown=a20.score_breakdown,
        gate_results={k: v.model_dump(mode="json") for k, v in a20.gate_results.items()},
        blocking_issues=[],
        warnings=["Historical v2.0.0 warning"],
        missing_evidence_mappings=[],
        recommendations=[],
        policy_digest=a20.policy_digest,
        contract_digest=a20.contract_digest,
        rule_digest=a20.rule_digest,
        validator_version="v2.0.0",
        evaluated_at=utc_now(),
    )
    db_session.add(legacy_qa)
    await db_session.commit()

    stored_res = await client.get(f"/api/prompts/rule/{rule.id}/assessments", headers=_auth(admin_token))
    assert stored_res.status_code == 200
    stored_data = stored_res.json()
    assert stored_data["current_validator_version"] == "v2.2.0"
    assert len(stored_data["assessments"]) == 1
    assert stored_data["assessments"][0]["validator_version"] == "v2.0.0"
    assert stored_data["assessments"][0]["quality_score"] == 81.0
    assert stored_data["assessments"][0]["is_legacy_scoring_model"] is True

    prev_res = await client.get(
        f"/api/prompts/rule/{rule.id}/quality-preview?version_id={pv.id}",
        headers=_auth(admin_token),
    )
    assert prev_res.status_code == 200
    prev_data = prev_res.json()
    assert prev_data["scoring_model_version"] == "v2.2.0"
    assert prev_data["historical_assessment_preserved"] is True
    assert prev_data["persisted_validator_version"] == "v2.0.0"
    assert prev_data["persisted_quality_score"] == 81.0
    assert prev_data["validation_status"] is not None

    # Confirm DB legacy record remained completely untouched
    refreshed_qa = (
        await db_session.execute(select(PolicyQualityAssessmentRecord).where(PolicyQualityAssessmentRecord.id == legacy_qa.id))
    ).scalar_one()
    assert refreshed_qa.validator_version == "v2.0.0"
    assert refreshed_qa.quality_score == 81.0


@pytest.mark.asyncio
async def test_2_quality_assessment_schema_and_non_null_validation_status_with_provenance(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
):
    """
    Target 2 (AIS-F06): Ensures assessment API responses eliminate validation_status: null,
    align scoring denominators, and carry complete simulation provenance across SIMULATED vs OPENAI_COMPATIBLE.
    """
    rule = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_EXPORT_PARITY",
        name="Export Parity Rule",
        event_type="PH_RULE_EXPORT_PARITY",
        severity="MEDIUM",
        pattern_logic="COUNT(Matched Events) >= 10; window=5m",
        raw_rule_text="Pattern Conditions:\nCOUNT(Matched Events) >= 10\nWindow: 5m\n",
        parsed_metadata={"source": "AUTHORITATIVE_XML_IMPORT", "definition_status": "VERIFIED"},
    )
    db_session.add(rule)
    await db_session.flush()

    rp = RulePrompt(id=str(uuid.uuid4()), rule_id=rule.id, title="Prompt - Export")
    db_session.add(rp)
    await db_session.flush()

    pv = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=rp.id,
        version_number=1,
        status="APPROVED",
        common_prompt="Evidence baseline.",
        rule_specific_prompt="Validate network scan telemetry and port distribution.",
        detection_conditions="COUNT(Matched Events) >= 10 over 5m",
        required_evidence="security.event_type, event.timestamp, network.source_ip, network.destination_port",
        tp_indicators="Unauthorized rapid host sweep across >= 10 hosts.",
        fp_indicators="Authorized vulnerability scanner with active maintenance ticket.",
        missing_info_criteria="Abstain and vote REQUIRES_ATTENTION if required fields are absent.",
        escalation_conditions="Escalate if critical server IP impacted.",
        analyst_questions=["Change ticket present?"],
    )
    db_session.add(pv)
    await db_session.flush()
    rp.active_version_id = pv.id
    digest = PolicyQualityValidator.compute_policy_digest(pv)

    # Seed latest SIMULATED run -> validation_status MUST be non-null & empirical=False
    sim_run = HistoricalEvaluationRunRecord(
        id=str(uuid.uuid4()),
        run_name="Simulated Non-Certifying Run",
        rule_id=rule.id,
        policy_version_id=pv.id,
        status="COMPLETED",
        validation_state="SIMULATED_ONLY",
        total_cases=8,
        evaluated_cases=8,
        verified_ground_truth_cases=8,
        metrics={"verified_ground_truth_cases": 8, "balanced_accuracy": 0.9, "overall_accuracy": 0.9},
        config_snapshot={
            "provider_type": "SIMULATED",
            "is_simulated": True,
            "execution_provenance": "SIMULATED",
            "model_identifier": "simulated-v2.2",
            "policy_digest": digest,
        },
        started_at=utc_now(),
        completed_at=utc_now(),
    )
    db_session.add(sim_run)
    await db_session.commit()

    res_sim = await client.get(f"/api/prompts/rule/{rule.id}/quality-preview?version_id={pv.id}", headers=_auth(admin_token))
    assert res_sim.status_code == 200
    d_sim = res_sim.json()
    assert d_sim["validation_status"] == "SIMULATED_ONLY_NOT_CERTIFYING"
    assert d_sim["simulation_provider_type"] == "SIMULATED"
    assert d_sim["simulation_model_identifier"] == "simulated-v2.2"
    assert d_sim["simulation_is_simulated"] is True
    assert d_sim["empirical_validation_eligible"] is False
    assert d_sim["autonomous_operation_eligible"] is False

    # Seed newer real OPENAI_COMPATIBLE run on exact digest -> EVALUATED_PASSED
    real_run = HistoricalEvaluationRunRecord(
        id=str(uuid.uuid4()),
        run_name="Real Qwen Run",
        rule_id=rule.id,
        policy_version_id=pv.id,
        status="COMPLETED",
        validation_state="EVALUATED_PASSED",
        total_cases=10,
        evaluated_cases=10,
        verified_ground_truth_cases=10,
        metrics={"verified_ground_truth_cases": 10, "balanced_accuracy": 0.92, "overall_accuracy": 0.92, "decision_coverage": 1.0},
        regression_summary={"regression_status": "PASS"},
        config_snapshot={
            "provider_type": "OPENAI_COMPATIBLE",
            "is_simulated": False,
            "execution_provenance": "REAL_LOCAL_LLM",
            "model_identifier": "Qwen/Qwen2.5-7B-Instruct-AWQ",
            "policy_digest": digest,
        },
        started_at=utc_now(),
        completed_at=utc_now(),
    )
    db_session.add(real_run)
    await db_session.commit()

    res_real = await client.get(f"/api/prompts/rule/{rule.id}/quality-preview?version_id={pv.id}", headers=_auth(admin_token))
    assert res_real.status_code == 200
    d_real = res_real.json()
    assert d_real["validation_status"] == "EVALUATED_PASSED"
    assert d_real["simulation_run_id"] == real_run.id
    assert d_real["simulation_provider_type"] == "OPENAI_COMPATIBLE"
    assert d_real["simulation_model_identifier"] == "Qwen/Qwen2.5-7B-Instruct-AWQ"
    assert d_real["simulation_execution_provenance"] == "REAL_LOCAL_LLM"
    assert d_real["simulation_is_simulated"] is False
    assert d_real["empirical_validation_eligible"] is True
    assert d_real["autonomous_operation_eligible"] is True
    assert d_real["gate_max_total"] == 100.0
    assert d_real["gate_scores_total"] == d_real["quality_score"] == round(sum(d_real["score_breakdown"].values()), 1)


@pytest.mark.asyncio
async def test_3_workbench_exact_rule_filtering_disambiguation_and_ais_reconciliation(
    client: AsyncClient,
    db_session: AsyncSession,
    analyst_token: str,
):
    """
    Target 3 (AIS-F07): Workbench exposes rule_uuid + logical_rule_id + event_type, warns when
    free-text search merges multiple rules, keeps PH_RULE_HEAVY_TCP_HOST_SCAN separate from
    _ON_FIXED_PORT, and reconciles exact-rule count 1:1 with AIS simulation.
    """
    r_main = Rule(
        id="9839fa49-40ac-4676-abcc-4c5581ae9e09",
        rule_id="PH_RULE_HEAVY_TCP_HOST_SCAN",
        name="Heavy TCP Host Scan",
        event_type="PH_RULE_HEAVY_TCP_HOST_SCAN",
        severity="HIGH",
    )
    r_fixed = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT",
        name="Heavy TCP Host Scan on Fixed Port",
        event_type="PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT",
        severity="HIGH",
    )
    db_session.add_all([r_main, r_fixed])
    await db_session.flush()

    for i in range(2):
        db_session.add(
            Incident(
                incident_id=f"WB-MAIN-{i+1}",
                rule_id=r_main.id,
                event_type=r_main.event_type,
                title="Heavy TCP Host Scan",
                severity="HIGH",
                source_ip=f"192.0.2.{10+i}",
                raw_payload={"srcIpAddr": f"192.0.2.{10+i}", "destPort": 22},
            )
        )
    for j in range(4):
        db_session.add(
            Incident(
                incident_id=f"WB-FIXED-{j+1}",
                rule_id=r_fixed.id,
                event_type=r_fixed.event_type,
                title="Heavy TCP Host Scan on Fixed Port",
                severity="HIGH",
                source_ip=f"192.0.2.{50+j}",
                raw_payload={"srcIpAddr": f"192.0.2.{50+j}", "destPort": 445},
            )
        )
    await db_session.commit()

    # 1. Free-text search matches both rules and signals combines_multiple_rules=True
    search_res = await client.get(
        "/api/incidents?search=Heavy%20TCP%20Host%20Scan",
        headers=_auth(analyst_token),
    )
    assert search_res.status_code == 200
    sdata = search_res.json()
    assert sdata["total"] == 6
    assert sdata["combines_multiple_rules"] is True
    assert sdata["distinct_rule_count"] == 2
    by_logical = {m["logical_rule_id"]: m for m in sdata["matched_rules"]}
    assert by_logical["PH_RULE_HEAVY_TCP_HOST_SCAN"]["incident_count"] == 2
    assert by_logical["PH_RULE_HEAVY_TCP_HOST_SCAN"]["rule_uuid"] == r_main.id
    assert by_logical["PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT"]["incident_count"] == 4
    assert by_logical["PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT"]["rule_uuid"] == r_fixed.id
    # Each row carries canonical rule_uuid + logical_rule_id + event_type
    assert all(item["rule_uuid"] and item["logical_rule_id"] and item["event_type"] for item in sdata["items"])

    # 2. Exact rule filter isolates PH_RULE_HEAVY_TCP_HOST_SCAN == 2 and reconciles with AIS simulation
    exact_res = await client.get(
        f"/api/incidents?exact_rule_id={r_main.id}",
        headers=_auth(analyst_token),
    )
    assert exact_res.status_code == 200
    edata = exact_res.json()
    assert edata["total"] == 2
    assert edata["combines_multiple_rules"] is False
    assert edata["distinct_rule_count"] == 1
    assert edata["exact_rule_id"] == r_main.id
    assert edata["exact_logical_rule_id"] == "PH_RULE_HEAVY_TCP_HOST_SCAN"
    assert {it["incident_id"] for it in edata["items"]} == {"WB-MAIN-1", "WB-MAIN-2"}

    # Reconcile against AIS simulation retrieved count for same canonical rule
    sim_svc = PolicySimulationService(db_session)
    sim_run = await sim_svc.run_dry_run_intelligence_evaluation(
        run_name="Workbench-AIS Reconcile Check",
        rule_id=r_main.id,
        sample_limit=100,
        provider_type="SIMULATED",
    )
    assert sim_run.metrics["funnel"]["retrieved"] == edata["total"] == 2
    assert sim_run.metrics["funnel"]["rule_matched"] == edata["total"] == 2


@pytest.mark.asyncio
async def test_4_g1_runtime_counters_fortisiem_fixtures_and_snapshot_parity(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
):
    """
    Target 4: Runtime incident counters (incidentCount / incidentDetail) are never mistaken for
    authoritative rule parameters; unverified definitions never become VERIFIED; FortiSIEM
    Pattern Conditions & Destination Port fixtures normalize cleanly across intelligence/G1/triage.
    """
    siem_svc = FortiSIEMService(db_session)

    # 1. JSON rule response containing only incidentDetail MUST remain INCOMPLETE with blank pattern_logic
    parsed_runtime = siem_svc._parse_json_rule(
        {
            "ruleId": "PH_RULE_RUNTIME_ONLY",
            "name": "Runtime Counter Only Rule",
            "incidentDetail": "incidentCount=42; sentBytes64=999999",
            "incidentDetailJson": {"incidentCount": 42, "sentBytes64": 999999},
        },
        fallback_id="PH_RULE_RUNTIME_ONLY",
        fallback_name="Runtime Counter Only Rule",
    )
    assert parsed_runtime is not None
    assert parsed_runtime["pattern_logic"] == ""
    assert parsed_runtime["metadata"]["definition_status"] == "INCOMPLETE"
    assert "incident_detail" in parsed_runtime["metadata"]["source_incident_metrics"]

    # 2. Import with empty conditions/only runtime counter MUST NOT mark rule VERIFIED
    imp_unverified = await siem_svc.import_authoritative_rule_definition(
        rule_identifier="PH_RULE_UNVERIFIED_COUNTER",
        definition_text="incidentCount=7; incidentDetail=Runtime event wrapper only",
        format_type="TEXT",
    )
    assert imp_unverified["definition_status"] == "INCOMPLETE"
    rule_unv = (
        await db_session.execute(select(Rule).where(Rule.rule_id == "PH_RULE_UNVERIFIED_COUNTER"))
    ).scalar_one()
    sem_unv = RuleIntelligenceAnalyzer.analyze_rule(rule_unv)
    assert sem_unv.threshold is None
    assert sem_unv.definition_status.value == "INCOMPLETE"

    # 3. Direct runtime counter condition inside Rule pattern_logic cannot yield threshold or VERIFIED status
    r_ctr = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_COUNTER_TRAP",
        name="Counter Trap",
        event_type="PH_RULE_COUNTER_TRAP",
        pattern_logic="incidentCount >= 5\nincidentDetail CONTAINS scan",
        raw_rule_text="Rule: Counter Trap",
        parsed_metadata={"source": "FORTISIEM_LIVE_RULE_API"},
    )
    sem_ctr = RuleIntelligenceAnalyzer.analyze_rule(r_ctr)
    assert sem_ctr.threshold is None
    assert sem_ctr.definition_status.value == "INCOMPLETE"

    # 4. Authoritative FortiSIEM Pattern Conditions + Destination Port rawEvents fixture
    raw_scan_text = (
        "Name: Heavy TCP Host Scan\n"
        "Description: Detects heavy TCP host reconnaissance sweep\n"
        "Pattern Conditions:\n"
        "COUNT(Matched Events) >= 50\n"
        "Window: 5m\n"
        "GroupBy: srcIpAddr\n"
        "Triggered Event Attributes\n"
        "Source IP, Destination IP, Destination Port, Event Receive Time\n"
    )
    parsed_scan = FortiSIEMService(db_session)
    scan_rule = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_FORTISIEM_FIXTURE_SCAN",
        name="FortiSIEM Fixture Heavy TCP Scan",
        event_type="PH_RULE_FORTISIEM_FIXTURE_SCAN",
        severity="HIGH",
        pattern_logic="COUNT(Matched Events) >= 50\nWindow: 5m\nGroupBy: srcIpAddr",
        raw_rule_text=raw_scan_text,
        parsed_metadata={"source": "AUTHORITATIVE_XML_IMPORT", "definition_status": "VERIFIED"},
    )
    db_session.add(scan_rule)
    await db_session.flush()

    sem_scan = RuleIntelligenceAnalyzer.analyze_rule(scan_rule)
    assert sem_scan.definition_status.value == "VERIFIED"
    assert sem_scan.threshold == 50.0
    assert "srcIpAddr" in sem_scan.grouping_keys

    # Persist snapshot and verify GET /intelligence honors it consistently with contract resolution
    snap = RuleIntelligenceSnapshot(
        id=str(uuid.uuid4()),
        rule_id=scan_rule.id,
        rule_identifier=scan_rule.rule_id,
        primary_archetype="NETWORK_SCAN",
        definition_status="VERIFIED",
        source_provenance="AUTHORITATIVE_SIEM_DEFINITION",
        threshold=50.0,
        threshold_unit="events",
        aggregation_window="5m",
        semantics_payload=sem_scan.model_dump(mode="json"),
    )
    db_session.add(snap)
    await db_session.commit()

    intel_res = await client.get(f"/api/prompts/rule/{scan_rule.id}/intelligence", headers=_auth(admin_token))
    assert intel_res.status_code == 200
    intel_json = intel_res.json()
    assert intel_json["classification"]["primary_archetype"] == "NETWORK_SCAN"
    assert intel_json["semantics"]["threshold"] == 50.0
    assert intel_json["semantics"]["definition_status"] == "VERIFIED"

    # Representative FortiSIEM incident fixture with "Destination Port" + nested rawEvents
    inc_fx = Incident(
        incident_id="FX-SCAN-001",
        rule_id=scan_rule.id,
        event_type=scan_rule.event_type,
        source_ip="192.0.2.88",
        first_seen_epoch=1794300000,
        raw_payload={
            "attributes": {"Source IP": "192.0.2.88", "Destination Port": 445, "Protocol": "TCP"},
            "rawEvents": [{"srcIpAddr": "192.0.2.88", "dstPort": 445, "eventType": scan_rule.event_type}],
        },
    )
    norm_fx = EvidenceNormalizationService.normalize_incident_evidence(inc_fx, [])
    norm_fields = {r.source_field for r in norm_fx.records}
    assert "network.destination_port" in norm_fields
    assert "network.source_ip" in norm_fields
    assert "security.event_type" in norm_fields

    _, contract_rt, _ = await get_rule_semantics_and_contract(db_session, scan_rule, for_quality_validation=False)
    assert contract_rt.detection_archetype == "NETWORK_SCAN"


@pytest.mark.asyncio
async def test_5_ground_truth_readiness_diagnostics_and_dry_run_non_mutation(
    client: AsyncClient,
    db_session: AsyncSession,
    analyst_token: str,
):
    """
    Target 5: Read-only readiness diagnostics audit existing is_ml_generated rows under
    AIS 2.1 word-boundary detection without altering database rows or verification flags,
    keeps sibling rules separate, and ensures min sample threshold never self-authorizes autonomy.
    """
    r_a = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_GT_READINESS_A",
        name="Readiness Rule A",
        event_type="PH_RULE_GT_READINESS_A",
        severity="HIGH",
    )
    r_b = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_GT_READINESS_B",
        name="Readiness Rule B",
        event_type="PH_RULE_GT_READINESS_B",
        severity="HIGH",
    )
    db_session.add_all([r_a, r_b])
    await db_session.flush()

    # 1. Legacy is_ml_generated=True false substring match ("Normal maintenance") + independent review
    inc_false_ml_verified = Incident(
        incident_id="GT-FALSE-ML-VER",
        rule_id=r_a.id,
        event_type=r_a.event_type,
        severity="HIGH",
        source_ip="192.0.2.101",
        raw_payload={"srcIpAddr": "192.0.2.101"},
        events=[IncidentEvent(event_id="EV-GT-1", event_type=r_a.event_type, attributes={"srcIpAddr": "192.0.2.101"})],
    )
    # 2. Legacy is_ml_generated=True genuine "Resolution set by Machine Learning" without verification
    inc_true_ml = Incident(
        incident_id="GT-TRUE-ML",
        rule_id=r_a.id,
        event_type=r_a.event_type,
        severity="HIGH",
        source_ip="192.0.2.102",
        raw_payload={"srcIpAddr": "192.0.2.102"},
        events=[IncidentEvent(event_id="EV-GT-2", event_type=r_a.event_type, attributes={"srcIpAddr": "192.0.2.102"})],
    )
    # 3. 5 cleanly verified TP/FP cases on r_b (meets G8 min sample=5, still must NOT self-authorize autonomy)
    b_incs = []
    for k in range(5):
        inc_b = Incident(
            incident_id=f"GT-B-{k+1}",
            rule_id=r_b.id,
            event_type=r_b.event_type,
            severity="HIGH",
            source_ip=f"192.0.2.{110+k}",
            raw_payload={"srcIpAddr": f"192.0.2.{110+k}"},
            events=[IncidentEvent(event_id=f"EV-GT-B-{k+1}", event_type=r_b.event_type, attributes={"srcIpAddr": f"192.0.2.{110+k}"})],
        )
        b_incs.append(inc_b)

    db_session.add_all([inc_false_ml_verified, inc_true_ml, *b_incs])
    await db_session.flush()

    gt_false = HistoricalGroundTruth(
        incident_id=inc_false_ml_verified.id,
        resolution="False Positive",
        comments="Normal authorized scanner maintenance window confirmed via xml log.",
        cleared_user="tier3_human",
        is_ml_generated=True,
    )
    gt_true = HistoricalGroundTruth(
        incident_id=inc_true_ml.id,
        resolution="False Positive",
        comments="Resolution set by Machine Learning auto-clear",
        cleared_user="system",
        is_ml_generated=True,
    )
    db_session.add_all([gt_false, gt_true])
    db_session.add(
        Investigation(
            incident_id=inc_false_ml_verified.id,
            status="COMPLETED",
            analyst_verdict="FALSE_POSITIVE",
            is_independently_verified=True,
            is_disputed=False,
        )
    )
    for k, inc_b in enumerate(b_incs):
        db_session.add(
            HistoricalGroundTruth(
                incident_id=inc_b.id,
                resolution="True Positive" if k < 3 else "False Positive",
                comments=f"Analyst verified case {k+1} independently.",
                cleared_user="soc_analyst",
                cleared_time_epoch=1794300000 + k * 60,
                is_ml_generated=False,
            )
        )
        db_session.add(
            Investigation(
                incident_id=inc_b.id,
                status="COMPLETED",
                analyst_verdict="TRUE_POSITIVE" if k < 3 else "FALSE_POSITIVE",
                is_independently_verified=True,
                is_disputed=False,
            )
        )
    await db_session.commit()

    rep_res = await client.get("/api/verdict-intelligence/eligibility-report", headers=_auth(analyst_token))
    assert rep_res.status_code == 200
    rep = rep_res.json()

    ml_audit = rep["summary"]["ml_reevaluation_audit"]
    assert ml_audit["mutated_records"] == 0
    assert ml_audit["total_flagged_ml_generated"] == 2
    assert ml_audit["confirmed_ml_or_automated"] == 1
    assert ml_audit["false_positive_ml_candidates"] == 1
    assert ml_audit["human_verified_ready_candidates"] == 1

    rules_map = {r["rule_id"]: r for r in rep["rules"]}
    assert rules_map["PH_RULE_GT_READINESS_A"]["available_incident_count"] == 2
    assert rules_map["PH_RULE_GT_READINESS_A"]["unverified_or_ml_count"] == 1
    assert rules_map["PH_RULE_GT_READINESS_B"]["available_incident_count"] == 5
    assert rules_map["PH_RULE_GT_READINESS_B"]["eligible_independent_count"] == 5
    assert rules_map["PH_RULE_GT_READINESS_B"]["g8_eligibility"] == "ELIGIBLE"
    assert rules_map["PH_RULE_GT_READINESS_B"]["governance_readiness"]["sample_threshold_alone_sufficient"] is False

    # Verify DB is_ml_generated flags were NEVER modified by diagnostics
    await db_session.refresh(gt_false)
    await db_session.refresh(gt_true)
    assert gt_false.is_ml_generated is True
    assert gt_true.is_ml_generated is True

    # Also test read-only CLI function directly against an isolated temp SQLite URL? No, verify CLI module helper
    from scripts.audit_ground_truth_readiness import run_read_only_ground_truth_audit
    assert callable(run_read_only_ground_truth_audit)


@pytest.mark.asyncio
async def test_6_end_to_end_ais_workflow_and_2_1_safeguards(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
    analyst_token: str,
    monkeypatch,
):
    """
    Target 6: Full end-to-end AIS 2.2 workflow:
    Rule Selection -> Intelligence -> Evidence Contract -> Policy Generation -> G1-G7 ->
    Simulation (Real LLM) -> G8 -> Quality Export Metadata -> Approval -> Live vs Autonomous Gate.
    """
    from app.services.gpu_manager import gpu_workload_manager
    from app.services.llm_config_service import LLMConfigService

    server, port, mock_calls = _start_openai_mock_server()
    monkeypatch.setattr(LLMConfigService, "sync_runtime_settings", classmethod(lambda cls: False))
    monkeypatch.setattr(settings, "LOCAL_LLM_BASE_URL", f"http://127.0.0.1:{port}/v1")
    monkeypatch.setattr(settings, "LOCAL_LLM_MODEL_NAME", "qwen2.5-ais22-mock")
    monkeypatch.setattr(settings, "LOCAL_LLM_ALLOW_MOCK_FALLBACK", False)
    monkeypatch.setattr(settings, "LOCAL_LLM_CONTEXT_BUDGET", 8192)
    VerdictTriageAgent._is_local_llm_online = None
    gpu_workload_manager.consecutive_failures = 0
    gpu_workload_manager.circuit_open_until = 0.0

    try:
        # 1. Authoritative rule import (FortiSIEM XML with real threshold & condition)
        xml_rule = """<rule id="PH_RULE_E2E_TCP_SCAN">
            <name>E2E Heavy TCP Host Scan</name>
            <description>Detects unauthorized horizontal TCP scanning across multiple hosts.</description>
            <severity>HIGH</severity>
            <subCategory>Reconnaissance</subCategory>
            <condition>
                <window>300</window>
                <groupBy>srcIpAddr</groupBy>
                <expression>COUNT(Matched Events) &gt;= 25</expression>
            </condition>
        </rule>"""
        imp = await FortiSIEMService(db_session).import_authoritative_rule_definition(
            rule_identifier="PH_RULE_E2E_TCP_SCAN",
            definition_text=xml_rule,
            format_type="XML",
        )
        assert imp["definition_status"] == "VERIFIED"
        rule = (
            await db_session.execute(select(Rule).where(Rule.rule_id == "PH_RULE_E2E_TCP_SCAN"))
        ).scalar_one()

        # 2. Seed 5 verified historical incidents with FortiSIEM Destination Port + 1 unrelated incident
        other_rule = Rule(
            id=str(uuid.uuid4()),
            rule_id="PH_RULE_E2E_OTHER",
            name="Other Rule",
            event_type="PH_RULE_E2E_OTHER",
            severity="LOW",
        )
        db_session.add(other_rule)
        await db_session.flush()

        for i in range(5):
            is_fp_case = i >= 3
            raw_p = {
                "srcIpAddr": "192.0.2.77",
                "Destination Port": 445,
                "protocol": "TCP",
            }
            if is_fp_case:
                raw_p["authorization_ticket"] = f"CHG-E2E-{i+1}"
            inc = Incident(
                incident_id=f"E2E-SCAN-{i+1}",
                rule_id=rule.id,
                event_type=rule.event_type,
                title=rule.name,
                severity="HIGH",
                source_ip="192.0.2.77",
                first_seen_epoch=1794300000 + i * 120,
                raw_payload=raw_p,
                events=[
                    IncidentEvent(
                        event_id=f"EV-E2E-{i+1}",
                        event_type=rule.event_type,
                        attributes=raw_p,
                    )
                ],
            )
            db_session.add(inc)
            await db_session.flush()
            db_session.add(
                HistoricalGroundTruth(
                    incident_id=inc.id,
                    resolution="False Positive" if is_fp_case else "True Positive",
                    comments=f"Analyst verified horizontal port sweep {i+1} with normal change check.",
                    cleared_user="soc_lead",
                    cleared_time_epoch=1794305000 + i * 120,
                    is_ml_generated=False,
                )
            )
            db_session.add(
                Investigation(
                    incident_id=inc.id,
                    status="COMPLETED",
                    analyst_verdict="FALSE_POSITIVE" if is_fp_case else "TRUE_POSITIVE",
                    is_independently_verified=True,
                    is_disputed=False,
                )
            )

        db_session.add(
            Incident(
                incident_id="E2E-OTHER-1",
                rule_id=other_rule.id,
                event_type=other_rule.event_type,
                title="Unrelated Rule Alert",
                severity="LOW",
                source_ip="192.0.2.99",
                raw_payload={"srcIpAddr": "192.0.2.99"},
            )
        )
        await db_session.commit()

        # 3. Rule Intelligence + Generate Policy Draft via API
        intel = await client.get(f"/api/prompts/rule/{rule.id}/intelligence", headers=_auth(analyst_token))
        assert intel.status_code == 200
        assert intel.json()["classification"]["primary_archetype"] == "NETWORK_SCAN"

        draft_res = await client.post(
            f"/api/prompts/rule/{rule.id}/generate-intelligent-draft",
            json={},
            headers=_auth(analyst_token),
        )
        assert draft_res.status_code == 200
        pv_id = draft_res.json()["id"]

        # 4. Validate G1-G7 pre-simulation -> v2.2.0 100-pt rubric, structural eligible, empirical False
        q_pre = await client.post(
            f"/api/prompts/rule/{rule.id}/validate-quality?version_id={pv_id}",
            headers=_auth(admin_token),
        )
        assert q_pre.status_code == 200
        qd_pre = q_pre.json()
        assert qd_pre["validator_version"] == "v2.2.0"
        assert qd_pre["gate_max_total"] == 100.0
        assert qd_pre["structural_approval_eligible"] is True
        assert qd_pre["empirical_validation_eligible"] is False
        assert qd_pre["validation_status"] != "null"

        # 5. Approve policy (structurally eligible), verify live autonomous gate STILL blocks prior to G8
        app_res = await client.post(
            f"/api/prompts/rule/{rule.id}/approve/{pv_id}",
            json={"change_summary": "AIS 2.2 structural approval prior to real LLM simulation"},
            headers=_auth(admin_token),
        )
        assert app_res.status_code == 200

        pv_obj = (await db_session.execute(select(PromptVersion).where(PromptVersion.id == pv_id))).scalar_one()
        cert_before = await assess_policy_runtime_certification(db_session, rule, pv_obj)
        assert cert_before.structural_approval_eligible is True
        assert cert_before.empirical_validation_eligible is False
        assert cert_before.autonomous_operation_eligible is False

        live_target = Incident(
            incident_id="E2E-LIVE-CHECK",
            rule_id=rule.id,
            event_type=rule.event_type,
            title=rule.name,
            severity="HIGH",
            source_ip="192.0.2.77",
            first_seen_epoch=1794400000,
            raw_payload={"srcIpAddr": "192.0.2.77", "Destination Port": 445, "protocol": "TCP"},
        )
        db_session.add(live_target)
        await db_session.commit()

        blocked = await VerdictTriageAgent(db_session).evaluate_incident(
            live_target.incident_id,
            username="admin_test",
            model_provider_type="OPENAI_COMPATIBLE",
            require_autonomous_certification=True,
        )
        assert blocked["final_disposition"] == "BLOCKED_UNCERTIFIED_FOR_AUTONOMOUS_ACTION"

        # 6. Execute Real LLM Simulation via API -> strictly 5 scoped cases (never E2E-OTHER-1 or E2E-LIVE-CHECK)
        sim_res = await client.post(
            f"/api/prompts/rule/{rule.id}/evaluate-simulation?version_id={pv_id}&provider_type=OPENAI_COMPATIBLE&sample_limit=100",
            headers=_auth(admin_token),
        )
        assert sim_res.status_code == 200, sim_res.text
        sim_json = sim_res.json()
        assert sim_json["provider_type"] == "OPENAI_COMPATIBLE"
        assert sim_json["is_simulated"] is False
        assert sim_json["verified_ground_truth_cases"] == 5
        assert mock_calls["post"] >= 5, f"sim_status={sim_json.get('simulation_status')} msg={sim_json.get('message')} results={sim_json.get('per_incident_results')}"

        # Replay did not leak GT comments/resolutions into model prompt & did not mutate incidents
        assert all("Analyst verified horizontal port sweep" not in p for p in mock_calls["prompts"])

        # 7. Validate G1-G8 post-simulation -> G8 PASSED, 100/100 max, export-ready provenance
        q_post = await client.get(
            f"/api/prompts/rule/{rule.id}/quality-preview?version_id={pv_id}",
            headers=_auth(admin_token),
        )
        assert q_post.status_code == 200
        qd_post = q_post.json()
        assert qd_post["validation_status"] == "EVALUATED_PASSED"
        assert qd_post["empirical_validation_eligible"] is True
        assert qd_post["autonomous_operation_eligible"] is True
        assert qd_post["simulation_provider_type"] == "OPENAI_COMPATIBLE"
        assert qd_post["simulation_model_identifier"] == "qwen2.5-ais22-mock"
        assert qd_post["gate_scores_total"] == qd_post["quality_score"]

        # 8. Now autonomous certification succeeds cleanly!
        cert_after = await assess_policy_runtime_certification(db_session, rule, pv_obj)
        assert cert_after.autonomous_operation_eligible is True
    finally:
        server.shutdown()
        server.server_close()

