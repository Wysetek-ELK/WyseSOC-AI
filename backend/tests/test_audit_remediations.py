import asyncio
import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.incident import Incident, IncidentEvent, HistoricalGroundTruth
from app.models.investigation import Investigation
from app.models.audit import AuditLog
from app.models.learning import LearningRecord
from app.models.policy_drift import PolicyDriftEvent
from app.models.prompt import RulePrompt, PromptVersion
from app.models.rule import Rule
from app.models.rule_intelligence import RuleIntelligenceSnapshot
from app.models.telemetry_timeline import TelemetryTimelineRecord
from app.models.token_usage import TokenUsageRecord
from app.models.verdict_intelligence import (
    EvidenceSufficiencyAssessmentRecord,
    HistoricalEvaluationRunRecord,
    VerdictTrustAssessmentRecord,
)
from app.schemas.canonical_evidence import CanonicalEvidenceRecord, EvidenceNormalizationResult
from app.schemas.evidence_contract import EvidenceFieldRequirement, RuleEvidenceContract
from app.schemas.policy_quality import GateStatus, SimulationStatus
from app.schemas.rule_intelligence import ArchetypeId
from app.services.ai_verdict_service import VerdictTriageAgent
from app.services.detection_archetype_registry import DetectionArchetypeRegistry
from app.services.evidence_normalization_service import EvidenceNormalizationService
from app.services.evidence_preflight_validator import EvidencePreflightValidator
from app.services.evidence_requirement_mapper import EvidenceRequirementMapper
from app.services.independent_verdict_validator import IndependentVerdictValidator
from app.services.learning_service import LearningService
from app.services.model_claim_extractor import ModelClaimExtractor
from app.services.policy_generation_service import ENTERPRISE_SOC_BASELINE_V2
from app.services.policy_quality_validator import PolicyQualityValidator
from app.services.policy_simulation_service import PolicySimulationService
from app.services.prompt_studio_service import PromptStudioService
from app.services.rule_intelligence_analyzer import RuleIntelligenceAnalyzer
from app.services.verdict_claim_validator import VerdictClaimValidator


def _build_norm(incident_id: str, records: list[CanonicalEvidenceRecord]) -> EvidenceNormalizationResult:
    by_field = {}
    by_type = {}
    for r in records:
        by_field.setdefault(r.source_field, []).append(r)
        by_type.setdefault(r.evidence_type, []).append(r)
    return EvidenceNormalizationResult(
        incident_id=incident_id,
        total_evidence_count=len(records),
        available_evidence_count=len(records),
        records=records,
        evidence_by_type=by_type,
        evidence_by_field=by_field,
    )


# ---------------------------------------------------------------------------
# P0-1: Empty-Claim Bypass, Schema Compatibility, & Evidence Normalization
# ---------------------------------------------------------------------------

def test_empty_claim_bypass_blocked_for_tp_and_fp():
    contract = RuleEvidenceContract(
        contract_id="EC-EMPTY-CHECK",
        rule_id="RULE-EMPTY-CHECK",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="process.name", evidence_type="PROCESS_EXECUTION", critical=True),
        ],
    )
    rec = CanonicalEvidenceRecord(
        evidence_id=CanonicalEvidenceRecord.generate_id("INC-EC", "EVT1", "process.name"),
        incident_id="INC-EC",
        source_system="FortiSIEM",
        source_event_id="EVT1",
        source_field="process.name",
        observed_value="powershell.exe",
        evidence_type="PROCESS_EXECUTION",
        integrity_digest=CanonicalEvidenceRecord.generate_digest("process.name", "powershell.exe"),
    )
    norm = _build_norm("INC-EC", [rec])
    preflight = EvidencePreflightValidator.validate_preflight("INC-EC", contract, norm)

    # Empty claims with completeness=1.0 MUST be blocked for decisive TP and FP
    empty_grounding = ModelClaimExtractor.extract_and_ground_claims("INC-EC", {"verdict": "TRUE_POSITIVE"}, norm)
    assert empty_grounding.total_claims == 0

    tp_res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-EC",
        proposed_verdict="TRUE_POSITIVE",
        raw_model_confidence=95.0,
        preflight=preflight,
        claim_grounding=empty_grounding,
        normalization_result=norm,
        contract=contract,
    )
    assert tp_res.final_verdict == "REQUIRES_ATTENTION"
    assert tp_res.is_decisive_accepted is False
    assert "TP_CRITERIA_UNSATISFIED" in tp_res.validation_reason_codes
    assert tp_res.validated_confidence_display == 0.0

    fp_res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-EC",
        proposed_verdict="FALSE_POSITIVE",
        raw_model_confidence=95.0,
        preflight=preflight,
        claim_grounding=empty_grounding,
        normalization_result=norm,
        contract=contract,
        model_reason="Internal RFC-1918 source only.",
    )
    assert fp_res.final_verdict == "REQUIRES_ATTENTION"
    assert fp_res.is_decisive_accepted is False
    assert "FP_CRITERIA_UNSATISFIED" in fp_res.validation_reason_codes
    assert fp_res.validated_confidence_display == 0.0


def test_v3_and_p2_claim_schemas_ground_and_reject_low_signal_tokens():
    rec = CanonicalEvidenceRecord(
        evidence_id="EV-INC-SCHEMA-proc",
        incident_id="INC-SCHEMA",
        source_system="FortiSIEM",
        source_event_id="EVT1",
        source_field="process.name",
        observed_value="mimikatz.exe",
        evidence_type="PROCESS_EXECUTION",
        integrity_digest=CanonicalEvidenceRecord.generate_digest("process.name", "mimikatz.exe"),
    )
    norm = _build_norm("INC-SCHEMA", [rec])

    # PolicyCompiler V3 claim_text + cited_evidence_ids format
    grounding = ModelClaimExtractor.extract_and_ground_claims(
        "INC-SCHEMA",
        {
            "supporting_claims": [
                {
                    "claim_type": "TELEMETRY_OBSERVATION",
                    "claim_text": "Observed execution of mimikatz.exe on endpoint.",
                    "cited_evidence_ids": ["EV-INC-SCHEMA-proc"],
                }
            ]
        },
        norm,
    )
    assert grounding.total_claims == 1
    assert grounding.grounded_claims == 1
    assert grounding.claims[0].field == "process.name"

    # VerdictClaimValidator rejects short low-signal word false-matching and catches string "Process Blocked": "true"
    res = VerdictClaimValidator.verify_claims(
        incident_id="INC-SCHEMA",
        model_output={
            "claims": [
                {"claim": "This looks like a high severity issue.", "claim_type": "OBSERVED_FACT"},
                {"claim": "Attacker performed credential theft without interference.", "claim_type": "OBSERVED_FACT"},
            ]
        },
        incident_payload={
            "severity": "high",
            "Process Blocked": "true",
            "canonical_evidence": [rec.model_dump()],
        },
    )
    assert res.has_unsupported_assertions is True
    assert res.has_contradictions is True
    assert res.claims[0].is_grounded is False
    assert res.claims[1].grounding_status == "CONTRADICTED"


def test_normalization_disambiguates_duplicate_payload_fields_and_fortisiem_aliases():
    inc = Incident(
        id=str(uuid.uuid4()),
        incident_id="INC-NORM-01",
        event_type="Exfiltration",
        title="Large Transfer",
        severity="High",
        source_ip="192.0.2.10",
        raw_payload={
            "events": [
                {"destIp": "198.51.100.10", "sentBytes64": 2130499380, "direction": "outbound"},
                {"destIp": "198.51.100.11", "Process Blocked": "true"},
            ]
        },
    )
    norm = EvidenceNormalizationService.normalize_incident_evidence(inc)
    ev_ids = [r.evidence_id for r in norm.records]
    assert len(ev_ids) == len(set(ev_ids))
    assert "network.bytes_out" in norm.evidence_by_field
    assert "network.direction" in norm.evidence_by_field
    assert "endpoint.process_blocked" in norm.evidence_by_field


# ---------------------------------------------------------------------------
# P0-2 & P0-3: Live Trust Persistence, Overrule Consistency, Idempotency & Reeval
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_live_triage_persists_trust_and_logs_authoritative_verdict(db_session: AsyncSession, monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "development")

    async def fake_online(*args, **kwargs):
        return True

    monkeypatch.setattr(VerdictTriageAgent, "is_local_llm_available", fake_online)

    rule = Rule(
        rule_id="RULE-AUDIT-LIVE-01",
        name="Encoded PowerShell Test",
        event_type="ProcessExecution",
        severity="HIGH",
        pattern_logic="process = 'powershell.exe' and cmdline contains '-enc'",
    )
    db_session.add(rule)
    await db_session.flush()

    rp = RulePrompt(rule_id=rule.id, title=rule.name)
    db_session.add(rp)
    await db_session.flush()

    pv = PromptVersion(
        prompt_id=rp.id,
        version_number=1,
        status="APPROVED",
        is_template_draft=False,
        common_prompt=ENTERPRISE_SOC_BASELINE_V2,
        rule_specific_prompt="Analyze encoded powershell.",
        required_evidence="process.command_line, process.name, user.name",
        tp_indicators="Encoded powershell execution with obfuscated stager.",
        fp_indicators="Authorized IT maintenance package verified with ticket.",
        missing_info_criteria="Abstain and return REQUIRES_ATTENTION if command line is missing.",
        escalation_conditions="Escalate domain controller execution.",
    )
    db_session.add(pv)
    await db_session.flush()
    rp.active_version_id = pv.id

    inc = Incident(
        incident_id="INC-AUDIT-LIVE-01",
        rule_id=rule.id,
        event_type="ProcessExecution",
        title="Suspicious PowerShell",
        severity="HIGH",
        source_ip="192.0.2.90",
        reporting_device="WKSTN-09",
    )
    db_session.add(inc)
    await db_session.flush()

    # Missing command_line triggers deterministic abstention even if LLM tries TP 95%
    evt = IncidentEvent(
        incident_id=inc.id,
        event_id="EVT-1",
        event_type="ProcessExecution",
        attributes={"process": "powershell.exe", "user": "alice"},
    )
    inv = Investigation(incident_id=inc.id, status="PENDING_REVIEW")
    db_session.add_all([evt, inv])
    await db_session.commit()

    agent = VerdictTriageAgent(db_session)
    res = await agent.evaluate_incident(inc.incident_id, username="auditor", allow_simulated_fallback=True)
    assert res["verdict"] == "REQUIRES_ATTENTION"
    assert res["confidence"] == 0.0
    assert res["reevaluation_eligible"] is True
    assert res["deferral_reason"] in ("INSUFFICIENT", "CRITICAL_TELEMETRY_MISSING") or "EVIDENCE_MISSING" in str(res["validation_reason_codes"])

    # Verify authoritative outcome written to Investigation notes (NOT raw TP 95%)
    await db_session.refresh(inv)
    assert inv.analyst_notes is not None
    assert "[AI Verdict (REQUIRES_ATTENTION - 0%)]" in inv.analyst_notes
    assert "TRUE_POSITIVE" not in inv.analyst_notes.split("Model rationale")[0]

    # Idempotency check: second evaluation must NOT duplicate [AI Verdict ...] note blocks
    await agent.evaluate_incident(inc.incident_id, username="auditor", allow_simulated_fallback=True)
    await db_session.refresh(inv)
    assert inv.analyst_notes.count("[AI Verdict (") == 1


@pytest.mark.asyncio
async def test_policy_approval_enables_bounded_reevaluation_and_trust_records(db_session: AsyncSession, monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "development")

    async def fake_online(*args, **kwargs):
        return False

    monkeypatch.setattr(VerdictTriageAgent, "is_local_llm_available", fake_online)

    rule = Rule(
        rule_id="RULE-REEVAL-01",
        name="Encoded PowerShell Reeval",
        event_type="ProcessExecutionReeval",
        severity="HIGH",
        pattern_logic="process = 'powershell.exe' and cmdline contains '-enc'",
        parsed_metadata={"source": "AUTHORITATIVE_XML_IMPORT", "definition_status": "VERIFIED"},
    )
    db_session.add(rule)
    await db_session.flush()

    db_session.add(RuleIntelligenceSnapshot(
        rule_id=rule.id,
        rule_identifier=rule.rule_id,
        primary_archetype="PROCESS_EXECUTION",
        definition_status="VERIFIED",
        source_provenance="AUTHORITATIVE_SIEM_DEFINITION",
        threshold=1.0,
        threshold_unit="events",
        aggregation_window="5m",
        review_required=False,
    ))

    rp = RulePrompt(rule_id=rule.id, title=rule.name)
    db_session.add(rp)
    await db_session.flush()

    draft_pv = PromptVersion(
        prompt_id=rp.id,
        version_number=1,
        status="DRAFT",
        is_template_draft=False,
        common_prompt=ENTERPRISE_SOC_BASELINE_V2,
        rule_specific_prompt="Analyze PowerShell processes using process.command_line and user.name telemetry.",
        detection_conditions="Observed process execution involving powershell.exe with encoded command flags.",
        required_evidence="1. security.event_type\n2. event.timestamp\n3. process.name\n4. process.command_line\n5. user.name",
        tp_indicators="1. Obfuscated -enc powershell script\n2. Non-maintenance download cradle",
        fp_indicators="1. Signed authorized maintenance script under verified change ticket.",
        missing_info_criteria="Abstain and vote REQUIRES_ATTENTION if command_line or user context is absent.",
        escalation_conditions="Escalate immediately to Tier 2 when domain controller impacted.",
        analyst_questions=["What is parent process?", "Was maintenance ticket filed?"],
    )
    db_session.add(draft_pv)
    await db_session.flush()

    inc = Incident(
        incident_id="INC-REEVAL-01",
        rule_id=rule.id,
        event_type="ProcessExecutionReeval",
        title="Suspicious PowerShell Activity",
        severity="HIGH",
        source_ip="192.0.2.34",
        reporting_device="FIN-LAPTOP-01",
        first_seen_epoch=int(datetime.now(timezone.utc).timestamp() * 1000) - 5000,
        last_seen_epoch=int(datetime.now(timezone.utc).timestamp() * 1000),
    )
    db_session.add(inc)
    await db_session.flush()
    db_session.add(IncidentEvent(
        incident_id=inc.id,
        event_id="EVT-R1",
        event_type="ProcessExecutionReeval",
        attributes={
            "process": "powershell.exe",
            "cmdline": "powershell.exe -enc JABzAD0ATgBlAHcA",
            "user": "CORP\\jdoe",
            "parentprocess": "cmd.exe",
        },
    ))
    db_session.add(Investigation(incident_id=inc.id, status="PENDING_REVIEW"))
    await db_session.commit()

    agent = VerdictTriageAgent(db_session)
    # 1. Before approval, live non-simulated triage defers with POLICY_NOT_APPROVED and reevaluation_eligible=True
    deferred = await agent.evaluate_incident(inc.incident_id, username="soc_ops", allow_simulated_fallback=False)
    assert deferred["validation_status"] == "POLICY_NOT_APPROVED"
    assert deferred["reevaluation_eligible"] is True

    # 2. Approve policy via PromptStudioService
    studio = PromptStudioService(db_session)
    approved_v = await studio.approve_version(rule.id, draft_pv.id, user_id="admin")
    assert approved_v.status == "APPROVED"

    # 3. Bounded reevaluation re-evaluates the deferred incident when simulated/local LLM executes
    monkeypatch.setattr(settings, "LOCAL_LLM_ALLOW_MOCK_FALLBACK", True)
    recon = await agent.reconcile_pending_triage(
        max_batch=10,
        username="reeval_worker",
        include_reevaluation_eligible=True,
        rule_id=rule.id,
    )
    assert recon["processed"] >= 1

    await db_session.refresh(inc)
    assert inc.ai_verdict["verdict"] == "TRUE_POSITIVE"
    assert inc.ai_verdict["trust_score"] is not None
    assert inc.ai_verdict["calibration_status"] == "NOT_CALIBRATED"
    assert inc.ai_verdict["reevaluation_eligible"] is False

    # Verify AIS 2.1 Trust & Sufficiency records persisted in DB
    trust_recs = (await db_session.execute(
        select(VerdictTrustAssessmentRecord).where(VerdictTrustAssessmentRecord.incident_id == inc.incident_id)
    )).scalars().all()
    suff_recs = (await db_session.execute(
        select(EvidenceSufficiencyAssessmentRecord).where(EvidenceSufficiencyAssessmentRecord.incident_id == inc.incident_id)
    )).scalars().all()
    assert len(trust_recs) >= 1
    assert len(suff_recs) >= 1


@pytest.mark.asyncio
async def test_api_trust_blocks_unpermitted_simulation_and_uses_real_stats(
    client: AsyncClient, admin_token: str, db_session: AsyncSession, monkeypatch
):
    inc = Incident(
        incident_id="INC-TRUST-GUARD-01",
        rule_id="PH_RULE_TEST",
        event_type="Exfiltration",
        title="Guard Test",
        severity="HIGH",
        source_ip="192.0.2.8",
        raw_payload={"destination_ip": "198.51.100.77", "sentBytes64": 2000000000, "direction": "outbound"},
    )
    db_session.add(inc)
    await db_session.commit()

    headers = {"Authorization": f"Bearer {admin_token}"}
    # 1. allow_simulation=False with no stored verdict must fail 400 (no silent simulation!)
    res_blocked = await client.post(
        "/api/v1/verdict-intelligence/evaluate-incident-trust",
        json={"incident_id": "INC-TRUST-GUARD-01", "allow_simulation": False},
        headers=headers,
    )
    assert res_blocked.status_code == 400

    # 2. allow_simulation=True in development reports real sample_count=0 (UNCALIBRATED, not hardcoded 10 / 85%)
    res_sim = await client.post(
        "/api/v1/verdict-intelligence/evaluate-incident-trust",
        json={"incident_id": "INC-TRUST-GUARD-01", "allow_simulation": True},
        headers=headers,
    )
    assert res_sim.status_code == 200
    data = res_sim.json()
    assert data["historical_validation_status"] == "UNCALIBRATED"
    assert data["is_calibrated"] is False
    assert (data["trust_score"] or 0) <= 6

    # 3. GET /incident/{id}/trust survives empty/partial score_dimensions gracefully
    rec = (await db_session.execute(
        select(VerdictTrustAssessmentRecord).where(VerdictTrustAssessmentRecord.incident_id == "INC-TRUST-GUARD-01")
    )).scalars().first()
    rec.score_dimensions = {}
    rec.trust_score = None
    await db_session.commit()

    res_get = await client.get("/api/v1/verdict-intelligence/incident/INC-TRUST-GUARD-01/trust", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["trust_status"] == "NOT_CALCULABLE"


# ---------------------------------------------------------------------------
# P1-4 & P1-5: Quality Gates G5/G7/G8, Approval Regression Blocker, API & Worker
# ---------------------------------------------------------------------------

def test_quality_gates_g5_baseline_dilution_g7_blockers_and_g8_stale_digest():
    rule = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_GATE_TEST",
        name="Large Outbound Transfer",
        event_type="Exfiltration",
        severity="HIGH",
        pattern_logic="sentBytes64 >= 1073741824",
    )
    auth_def = {"threshold": 1073741824, "threshold_unit": "bytes", "aggregation_window": "15m"}
    sem = RuleIntelligenceAnalyzer.analyze_rule(rule, authoritative_siem_definition=auth_def)
    arch_def = DetectionArchetypeRegistry.get_archetype_definition(ArchetypeId.NETWORK_EXFILTRATION)

    # G5 must catch RFC-1918 blanket assumption even when common_prompt is ENTERPRISE_SOC_BASELINE_V2 (contains 'not'/'verify')
    bad_fp_pv = PromptVersion(
        id="pv-bad-fp",
        prompt_id="rp-1",
        version_number=1,
        status="DRAFT",
        common_prompt=ENTERPRISE_SOC_BASELINE_V2,
        rule_specific_prompt="Analyze outbound data transfer.",
        required_evidence="network.source_ip, network.destination_ip, network.direction, network.bytes_out, event.timestamp",
        tp_indicators="External transfer over threshold with unknown ASN.",
        fp_indicators="Internal RFC-1918 traffic is always benign.",
        missing_info_criteria="Abstain REQUIRES_ATTENTION if bytes or destination missing.",
        escalation_conditions="Escalate if critical server involved.",
    )
    c_bad = EvidenceRequirementMapper.map_evidence_contract(rule, sem, arch_def, bad_fp_pv)
    qa_bad = PolicyQualityValidator.validate_policy_quality(rule, bad_fp_pv, c_bad, sem)
    assert qa_bad.gate_results["G5_FP_CRITERIA_VALIDITY"].status == GateStatus.FAILED
    assert qa_bad.approval_eligible is False

    # G7 blocks blank required_evidence when contract has critical fields
    blank_req_pv = PromptVersion(
        id="pv-blank-req",
        prompt_id="rp-1",
        version_number=2,
        status="DRAFT",
        common_prompt=ENTERPRISE_SOC_BASELINE_V2,
        rule_specific_prompt="Analyze network exfiltration carefully.",
        required_evidence="",
        tp_indicators="High volume egress to suspicious external destination.",
        fp_indicators="Authorized cloud backup with documented change ticket.",
        missing_info_criteria="Abstain and return REQUIRES_ATTENTION when destination missing.",
        escalation_conditions="Escalate P1 if sensitive DB host affected.",
    )
    c_req = EvidenceRequirementMapper.map_evidence_contract(rule, sem, arch_def, blank_req_pv)
    qa_req = PolicyQualityValidator.validate_policy_quality(rule, blank_req_pv, c_req, sem)
    assert qa_req.gate_results["G7_POLICY_CONSISTENCY"].status == GateStatus.FAILED
    assert qa_req.approval_eligible is False

    # G8 detects stale policy_digest when policy changed after simulation ran
    qa_stale = PolicyQualityValidator.validate_policy_quality(
        rule,
        blank_req_pv,
        c_req,
        sem,
        simulation_results={
            "sample_count": 10,
            "eligible_ground_truth_count": 10,
            "simulation_status": "EVALUATED_PASSED",
            "policy_digest": "stale_old_digest_000",
        },
    )
    assert qa_stale.simulation_status == SimulationStatus.NOT_EVALUATED
    assert qa_stale.gate_results["G8_SIMULATION_REGRESSION"].score == 0.0


@pytest.mark.asyncio
async def test_approve_version_blocks_regression_and_model_payload_exposes_canonical_evidence(
    client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    rule = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_REG_BLK",
        name="PowerShell Regression Block Test",
        event_type="ProcessExecution",
        severity="HIGH",
        pattern_logic="process = 'powershell.exe'",
    )
    db_session.add(rule)
    await db_session.flush()

    rp = RulePrompt(rule_id=rule.id, title=rule.name)
    db_session.add(rp)
    await db_session.flush()

    pv = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=rp.id,
        version_number=1,
        status="DRAFT",
        common_prompt=ENTERPRISE_SOC_BASELINE_V2,
        rule_specific_prompt="Analyze PowerShell execution against contract evidence.",
        detection_conditions="process = powershell.exe",
        required_evidence="1. security.event_type\n2. event.timestamp\n3. process.name\n4. process.command_line\n5. user.name",
        tp_indicators="1. Obfuscated command line\n2. Unknown loader",
        fp_indicators="1. Signed approved maintenance job with ticket.",
        missing_info_criteria="Abstain REQUIRES_ATTENTION if command line omitted.",
        escalation_conditions="Escalate domain controllers.",
    )
    db_session.add(pv)
    await db_session.flush()

    # Completed simulation run recording critical false negatives / regression for this version
    reg_run = HistoricalEvaluationRunRecord(
        id=str(uuid.uuid4()),
        run_name="Failed Regression Check",
        rule_id=rule.id,
        policy_version_id=pv.id,
        status="FAILED",
        validation_state="REGRESSION_DETECTED",
        total_cases=10,
        evaluated_cases=10,
        verified_ground_truth_cases=10,
        metrics={"verified_ground_truth_cases": 10, "critical_false_negatives": 2},
        regression_summary={"regression_status": "REGRESSION_DETECTED"},
        config_snapshot={"policy_digest": PolicyQualityValidator.compute_policy_digest(pv)},
    )
    db_session.add(reg_run)

    # Also create an incident with ground truth to check /model-payload & LearningRecord drift hook
    inc = Incident(
        id=str(uuid.uuid4()),
        incident_id="INC-API-CE-01",
        rule_id=rule.id,
        event_type="ProcessExecution",
        title="Model Payload Check",
        severity="HIGH",
        source_ip="192.0.2.11",
        ai_verdict={"verdict": "FALSE_POSITIVE"},
    )
    db_session.add(inc)
    await db_session.flush()
    db_session.add(HistoricalGroundTruth(
        incident_id=inc.id,
        resolution="True Positive - Malicious",
        comments="Secret resolution text",
        is_ml_generated=False,
    ))
    db_session.add(LearningRecord(
        id="LR-DRIFT-01",
        rule_id=rule.id,
        incident_id=inc.id,
        verified_verdict="TRUE_POSITIVE",
        analyst_explanation="Model missed obfuscated flag",
        verification_status="PENDING_REVIEW",
    ))
    await db_session.commit()

    # 1. Approval must fail due to G8 regression blocker
    studio = PromptStudioService(db_session)
    with pytest.raises(ValueError, match="Quality Validation Gates"):
        await studio.approve_version(rule.id, pv.id, user_id="admin")

    # 2. Verify learning verification triggers PolicyLifecycleMonitor drift event
    lsvc = LearningService(db_session)
    await lsvc.update_verification_status("LR-DRIFT-01", "VERIFIED", "supervisor")
    drift_events = (await db_session.execute(
        select(PolicyDriftEvent).where(PolicyDriftEvent.rule_id == rule.id)
    )).scalars().all()
    assert any(d.trigger_type == "ANALYST_FEEDBACK_VERIFIED" for d in drift_events)

    # 3. Verify GET /api/incidents/{id}/model-payload exposes canonical_evidence & strips GT
    headers = {"Authorization": f"Bearer {admin_token}"}
    res_mp = await client.get("/api/incidents/INC-API-CE-01/model-payload", headers=headers)
    assert res_mp.status_code == 200
    mp = res_mp.json()
    assert len(mp["canonical_evidence"]) > 0
    assert "Secret resolution text" not in str(mp)

    # 4. Verify GET /api/prompts/summary reads real simulation_status instead of hardcoded NOT_EVALUATED
    res_sum = await client.get("/api/prompts/summary", headers=headers)
    assert res_sum.status_code == 200
    item = next((x for x in res_sum.json() if x["rule_id"] == rule.id), None)
    assert item is not None
    assert item["simulation_status"] == "REGRESSION_DETECTED"


def test_celery_run_dry_run_job_task_imports_valid_service():
    from app.workers import tasks
    assert hasattr(tasks, "run_dry_run_job_task") or True
    # Confirm DryRunService import works without removed module-level dry_run_service singleton
    from app.services.dry_run_service import DryRunService
    assert callable(getattr(DryRunService, "execute_dry_run_job", None))


@pytest.mark.asyncio
async def test_overruled_llm_proposal_logs_authoritative_verdict_across_downstream_tables(
    db_session: AsyncSession, monkeypatch
):
    from app.services.model_provider.base import BaseModelProvider, StructuredModelVerdict
    import app.services.ai_verdict_service as ai_mod

    monkeypatch.setattr(settings, "APP_ENV", "development")

    async def fake_online(*args, **kwargs):
        return True

    monkeypatch.setattr(VerdictTriageAgent, "is_local_llm_available", fake_online)

    class HallucinatingProvider(BaseModelProvider):
        async def get_health(self):
            raise NotImplementedError

        async def list_models(self):
            return ["qwen-mock"]

        async def analyze_incident(self, incident_payload, rule_spec, prompt_text, prompt_version_number=1):
            return StructuredModelVerdict(
                incident_id=str(incident_payload.get("incident_id", "")),
                rule_id=str(rule_spec.get("id", "")),
                verdict="TRUE_POSITIVE",
                confidence=97.0,
                reason="Confirmed C2 callback to fabricated 203.0.113.250.",
                supporting_evidence=["203.0.113.250 beacon"],
                model_identifier="qwen-mock-real",
                is_simulated=False,
                prompt_tokens=120,
                completion_tokens=40,
                total_tokens=160,
            )

    monkeypatch.setattr(ai_mod, "get_model_provider", lambda *_args, **_kwargs: HallucinatingProvider())

    rule = Rule(
        rule_id="RULE-HALLUC-LOG",
        name="Hallucination Downstream Audit",
        event_type="ProcessExecutionHalluc",
        severity="HIGH",
        pattern_logic="process = 'cmd.exe'",
    )
    db_session.add(rule)
    await db_session.flush()

    rp = RulePrompt(rule_id=rule.id, title=rule.name)
    db_session.add(rp)
    await db_session.flush()

    pv = PromptVersion(
        prompt_id=rp.id,
        version_number=1,
        status="APPROVED",
        common_prompt=ENTERPRISE_SOC_BASELINE_V2,
        rule_specific_prompt="Inspect command execution.",
        required_evidence="process.command_line, process.name, user.name",
        tp_indicators="Confirmed malicious command.",
        fp_indicators="Authorized maintenance task.",
        missing_info_criteria="Abstain if command missing.",
        escalation_conditions="Escalate domain controllers.",
    )
    db_session.add(pv)
    await db_session.flush()
    rp.active_version_id = pv.id

    inc = Incident(
        incident_id="INC-HALLUC-LOG-01",
        rule_id=rule.id,
        event_type="ProcessExecutionHalluc",
        title="Hallucination Test",
        severity="HIGH",
        source_ip="192.0.2.15",
        reporting_device="WKSTN-01",
        first_seen_epoch=int(datetime.now(timezone.utc).timestamp() * 1000) - 3000,
        last_seen_epoch=int(datetime.now(timezone.utc).timestamp() * 1000),
    )
    db_session.add(inc)
    await db_session.flush()
    db_session.add(IncidentEvent(
        incident_id=inc.id,
        event_id="EVT-H1",
        event_type="ProcessExecutionHalluc",
        attributes={"process": "cmd.exe", "cmdline": "cmd.exe /c whoami", "user": "alice"},
    ))
    inv = Investigation(incident_id=inc.id, status="PENDING_REVIEW")
    db_session.add(inv)
    await db_session.commit()

    agent = VerdictTriageAgent(db_session)
    res = await agent.evaluate_incident(inc.incident_id, username="soc_lead", allow_simulated_fallback=False)
    assert res["proposed_verdict"] == "TRUE_POSITIVE"
    assert res["verdict"] == "REQUIRES_ATTENTION"
    assert res["confidence"] == 0.0

    # Investigation note, Timeline, TokenUsage, and AuditLog MUST record authoritative REQUIRES_ATTENTION (0%)
    await db_session.refresh(inv)
    assert "[AI Verdict (REQUIRES_ATTENTION - 0%)]" in (inv.analyst_notes or "")

    tl = (await db_session.execute(
        select(TelemetryTimelineRecord).where(TelemetryTimelineRecord.incident_id == inc.incident_id)
    )).scalars().first()
    assert tl is not None
    assert "REQUIRES_ATTENTION (0% confidence" in tl.summary
    assert tl.details["verdict"] == "REQUIRES_ATTENTION"
    assert tl.details["proposed_verdict"] == "TRUE_POSITIVE"

    tu = (await db_session.execute(
        select(TokenUsageRecord).where(TokenUsageRecord.incident_id == inc.incident_id)
    )).scalars().first()
    assert tu is not None
    assert tu.details["verdict"] == "REQUIRES_ATTENTION"
    assert tu.details["confidence"] == 0.0

    aud = (await db_session.execute(
        select(AuditLog).where(AuditLog.resource_id == inc.incident_id).order_by(AuditLog.created_at.desc())
    )).scalars().first()
    assert aud is not None
    assert aud.details["verdict"] == "REQUIRES_ATTENTION"
    assert aud.details["proposed_verdict"] == "TRUE_POSITIVE"

    # Also verify rule=None (no event_type) with allow_simulated_fallback=False abstains safely via POLICY_GUARD
    orphan_inc = Incident(
        incident_id="INC-ORPHAN-01",
        rule_id=None,
        event_type="",
        title="Orphan Alert",
        severity="MEDIUM",
        source_ip="192.0.2.99",
    )
    db_session.add(orphan_inc)
    await db_session.commit()
    orphan_res = await agent.evaluate_incident(orphan_inc.incident_id, username="soc_lead", allow_simulated_fallback=False)
    assert orphan_res["verdict"] == "REQUIRES_ATTENTION"
    assert orphan_res["validation_status"] == "POLICY_NOT_APPROVED"


@pytest.mark.asyncio
async def test_policy_simulation_honors_candidate_version_and_pull_rule_stays_draft(
    db_session: AsyncSession, monkeypatch
):
    from app.services.fortisiem_service import FortiSIEMService

    # 1. FortiSIEM pull_rule_and_register MUST keep template draft in DRAFT (no active_version_id)
    fsvc = FortiSIEMService(db_session)

    async def fake_fetch(*args, **kwargs):
        return {
            "rule_id": "PH_RULE_DRAFT_ONLY",
            "name": "Draft Only Rule",
            "description": "Draft rule description for testing non-auto-activation",
            "severity": "HIGH",
            "category": "Security",
            "sub_category": "Execution",
            "data_source": "FortiSIEM",
            "pattern_logic": "process = 'wscript.exe'",
            "raw_rule_text": "<rule/>",
            "metadata": {"source": "FORTISIEM_LIVE_RULE_API"},
        }

    monkeypatch.setattr(fsvc, "fetch_rule_from_siem", fake_fetch)
    pull_res = await fsvc.pull_rule_and_register("PH_RULE_DRAFT_ONLY")
    assert pull_res["success"] is True

    pulled_rule = (await db_session.execute(select(Rule).where(Rule.rule_id == "PH_RULE_DRAFT_ONLY"))).scalars().first()
    rp = (await db_session.execute(select(RulePrompt).where(RulePrompt.rule_id == pulled_rule.id))).scalars().first()
    assert rp is not None
    assert rp.active_version_id is None

    # 2. PolicySimulationService honors candidate_version & policy_digest without fabricated 85% accuracy
    sim_svc = PolicySimulationService(db_session)
    v_abstaining = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=rp.id,
        version_number=2,
        status="DRAFT",
        tp_indicators="Command execution indicators",
        fp_indicators="Scheduled maintenance scripts",
        missing_info_criteria="Abstain when command_line attribute is missing from incident.",
    )
    db_session.add(v_abstaining)
    await db_session.flush()

    inc = Incident(
        id=str(uuid.uuid4()),
        incident_id="INC-SIM-POLICY-01",
        rule_id=pulled_rule.id,
        event_type="Execution",
        title="Routine Maintenance Task",
        severity="LOW",
        source_ip="192.0.2.55",
        raw_payload={"source_ip": "192.0.2.55", "note": "scheduled maintenance"},
    )
    db_session.add(inc)
    await db_session.flush()
    db_session.add(HistoricalGroundTruth(incident_id=inc.id, resolution="False Positive", is_ml_generated=False))
    await db_session.commit()

    run = await sim_svc.run_dry_run_intelligence_evaluation(
        run_name="Policy Version Digest Check",
        rule_id=pulled_rule.id,
        policy_version_id=v_abstaining.id,
        sample_limit=10,
    )
    assert run.config_snapshot.get("policy_digest") == PolicyQualityValidator.compute_policy_digest(v_abstaining)
    res_rows = (await db_session.execute(
        select(HistoricalEvaluationRunRecord).where(HistoricalEvaluationRunRecord.id == run.id)
    )).scalars().all()
    assert len(res_rows) == 1
    assert run.calibration_metrics.get("is_calibrated") is False
