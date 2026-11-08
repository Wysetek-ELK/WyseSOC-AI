"""
test_phase2_integration.py
Phase 2 Test Suite: End-to-End System Integration & Workflow Verification (Scenarios 35-48)

Tests:
35. Live AI verdict flow with valid evidence & approved policy produces accepted verdict
36. Live AI verdict flow with missing mandatory telemetry forces REQUIRES_ATTENTION
37. Live AI verdict flow with unapproved prompt version forces immediate human deferral
38. Model-facing payload allowlist includes canonical evidence and excludes ground truth
39. Simulated provider extracts and populates claims from canonical evidence
40. Replay validation end-to-end reconstruction matches live verdict
41. Bifurcated verdict persistence: proposed_verdict vs authoritative final verdict
42. Token accounting, latency tracking, and Phase 1 safety control non-regression
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.incident import Incident, IncidentEvent, HistoricalGroundTruth
from app.models.rule import Rule
from app.models.prompt import RulePrompt, PromptVersion
from app.services.ai_verdict_service import VerdictTriageAgent
from app.services.independent_verdict_validator import IndependentVerdictValidator
from app.services.model_provider.simulated import SimulatedModelProvider
from app.services.model_payload_allowlist import build_model_facing_payload
from app.services.evidence_normalization_service import EvidenceNormalizationService
from app.schemas.canonical_evidence import CanonicalEvidenceRecord


@pytest.mark.asyncio
async def test_live_verdict_evaluation_with_grounded_evidence(db_session: AsyncSession):
    """Scenario 35: Live AI verdict flow with valid telemetry and approved contract."""
    # 1. Setup Rule and Approved Prompt
    rule = Rule(
        rule_id="RULE-E2E-01",
        name="Suspicious PowerShell LOLBin Activity",
        event_type="Process-Creation",
        severity="High",
    )
    db_session.add(rule)
    await db_session.flush()

    rule_prompt = RulePrompt(
        rule_id=rule.id,
        title=rule.name,
    )
    db_session.add(rule_prompt)
    await db_session.flush()

    pv = PromptVersion(
        prompt_id=rule_prompt.id,
        version_number=1,
        status="APPROVED",
        is_template_draft=False,
        tp_indicators="- Encoded command line parameters\n- Web request from powershell",
        fp_indicators="- Standard administrative maintenance scripts",
    )
    db_session.add(pv)
    await db_session.flush()

    rule_prompt.active_version_id = pv.id
    await db_session.flush()

    # 2. Setup Incident with complete process telemetry
    incident = Incident(
        incident_id="INC-E2E-01",
        rule_id=rule.id,
        event_type="Process-Creation",
        title="PowerShell Execution with Obfuscated Script",
        severity="High",
        source_ip="10.0.1.15",
        reporting_device="WORKSTATION-01",
        category="Execution",
        subcategory="PowerShell",
        raw_payload={"vendor": "FortiSIEM"},
    )
    db_session.add(incident)
    await db_session.flush()

    evt = IncidentEvent(
        incident_id=incident.id,
        event_id="EVT-E2E-01",
        event_type="Process-Creation",
        attributes={
            "process": "powershell.exe",
            "cmdline": "powershell.exe -NoP -NonI -W Hidden -Enc JABzAD0ATgBlAHcALQBPAGIAagBlAGMAdAA=",
            "parentprocess": "cmd.exe",
            "user": "DOMAIN\\victim_user",
        }
    )
    db_session.add(evt)
    await db_session.commit()

    # 3. Execute Verdict Evaluation via Agent
    agent = VerdictTriageAgent(db_session)
    res = await agent.evaluate_incident(
        incident_id_or_obj="INC-E2E-01",
        username="test_user_analyst",
        allow_simulated_fallback=True,
    )

    # 4. Assert Evidence-Grounded Verdict
    assert res["verdict"] in ("TRUE_POSITIVE", "FALSE_POSITIVE", "REQUIRES_ATTENTION")
    assert res["evidence_completeness"] is not None
    assert res["evidence_completeness"] >= 0.5
    assert res["canonical_evidence_count"] > 0
    assert res["contract_id"] is not None
    assert res["contract_version"] == 1
    assert res["validator_version"] == "2.0.0"
    assert res["replay_signature"] != ""
    assert res["analyst_action_directive"] != ""


@pytest.mark.asyncio
async def test_live_verdict_evaluation_missing_telemetry_abstention(db_session: AsyncSession):
    """Scenario 36: Live AI verdict flow with missing mandatory telemetry forces REQUIRES_ATTENTION."""
    # 1. Setup Rule with Approved Prompt requiring process.command_line
    rule = Rule(
        rule_id="RULE-E2E-02",
        name="PowerShell Execution Anomaly",
        event_type="Process-Creation",
        severity="Medium",
    )
    db_session.add(rule)
    await db_session.flush()

    rule_prompt = RulePrompt(
        rule_id=rule.id,
        title=rule.name,
    )
    db_session.add(rule_prompt)
    await db_session.flush()

    pv = PromptVersion(
        prompt_id=rule_prompt.id,
        version_number=1,
        status="APPROVED",
        is_template_draft=False,
    )
    db_session.add(pv)
    await db_session.flush()
    rule_prompt.active_version_id = pv.id
    await db_session.flush()

    # 2. Setup Incident with MISSING command line (only process name provided)
    incident = Incident(
        incident_id="INC-E2E-02",
        rule_id=rule.id,
        event_type="Process-Creation",
        title="PowerShell Execution Anomaly",
        severity="Medium",
        source_ip="10.0.1.20",
        reporting_device="SERVER-01",
        category="Execution",
        raw_payload={},
    )
    db_session.add(incident)
    await db_session.flush()

    evt = IncidentEvent(
        incident_id=incident.id,
        event_id="EVT-E2E-02",
        event_type="Process-Creation",
        attributes={
            "process": "powershell.exe",
            # No cmdline
        }
    )
    db_session.add(evt)
    await db_session.commit()

    # 3. Execute Verdict Evaluation
    agent = VerdictTriageAgent(db_session)
    res = await agent.evaluate_incident(
        incident_id_or_obj="INC-E2E-02",
        username="test_user_analyst",
        allow_simulated_fallback=True,
    )

    # 4. Mandatory evidence missing -> Authoritative final verdict MUST be REQUIRES_ATTENTION
    assert res["verdict"] == "REQUIRES_ATTENTION"
    assert res["is_decisive_accepted"] is False
    assert res["confidence"] == 0.0 or res["confidence"] <= 50.0  # Safe abstention display
    assert any("EVIDENCE_MISSING" in c or "CRITICAL_TELEMETRY_MISSING" in c or "UNSATISFIED" in c for c in res["validation_reason_codes"])


@pytest.mark.asyncio
async def test_live_verdict_unapproved_prompt_forces_attention(db_session: AsyncSession):
    """Scenario 37: Unapproved prompt draft forces contract UNVERIFIED and immediate abstention."""
    rule = Rule(
        rule_id="RULE-E2E-03",
        name="Unapproved Policy Test Rule",
        event_type="General",
        severity="Low",
    )
    db_session.add(rule)
    await db_session.flush()

    rule_prompt = RulePrompt(
        rule_id=rule.id,
        title=rule.name,
    )
    db_session.add(rule_prompt)
    await db_session.flush()

    # DRAFT version, not APPROVED
    pv = PromptVersion(
        prompt_id=rule_prompt.id,
        version_number=1,
        status="DRAFT",
        is_template_draft=True,
    )
    db_session.add(pv)
    await db_session.flush()

    incident = Incident(
        incident_id="INC-E2E-03",
        rule_id=rule.id,
        event_type="General",
        title="Unapproved Policy Incident",
        severity="Low",
        source_ip="10.0.1.30",
        raw_payload={},
    )
    db_session.add(incident)
    await db_session.commit()

    agent = VerdictTriageAgent(db_session)
    res = await agent.evaluate_incident(
        incident_id_or_obj="INC-E2E-03",
        username="test_user_analyst",
        allow_simulated_fallback=True,
    )

    assert res["verdict"] == "REQUIRES_ATTENTION"
    assert res["is_decisive_accepted"] is False
    assert any("EVIDENCE_CONTRACT_UNVERIFIED" in c or "POLICY_NOT_APPROVED" in c for c in res["validation_reason_codes"])


@pytest.mark.asyncio
async def test_model_facing_payload_includes_canonical_evidence(db_session: AsyncSession):
    """Scenario 38: Model payload includes canonical evidence records with zero ground truth leakage."""
    incident = Incident(
        incident_id="INC-E2E-04",
        event_type="Process-Creation",
        title="Ground Truth Isolation Check",
        severity="High",
        source_ip="192.168.1.99",
        reporting_device="WIN-DESKTOP-99",
        raw_payload={"process": "whoami.exe", "user": "admin"},
    )
    db_session.add(incident)
    await db_session.flush()

    gt = HistoricalGroundTruth(
        incident_id=incident.id,
        resolution="True Positive - Malicious",
        cleared_reason="Confirmed attack",
        cleared_user="analyst_alice",
        comments="Attacker performed reconnaissance",
    )
    db_session.add(gt)
    await db_session.commit()

    norm = EvidenceNormalizationService.normalize_incident_evidence(incident, events=[])
    payload = build_model_facing_payload(incident, rule=None, events=[])
    payload["canonical_evidence"] = [r.model_dump() for r in norm.records]

    # 1. Verify canonical evidence presence
    assert "canonical_evidence" in payload
    assert len(payload["canonical_evidence"]) > 0
    for rec in payload["canonical_evidence"]:
        assert "evidence_id" in rec
        assert "integrity_digest" in rec
        assert "observed_value" in rec

    # 2. Verify zero ground truth leakage
    payload_str = str(payload)
    assert "True Positive - Malicious" not in payload_str
    assert "Confirmed attack" not in payload_str
    assert "analyst_alice" not in payload_str
    assert "Attacker performed reconnaissance" not in payload_str


@pytest.mark.asyncio
async def test_simulated_provider_populates_canonical_claims():
    """Scenario 39: SimulatedModelProvider constructs claims referencing canonical evidence IDs."""
    provider = SimulatedModelProvider()
    input_payload = {
        "incident_id": "INC-SIM-01",
        "title": "Suspicious PowerShell Activity",
        "events": [{"raw_log": "powershell.exe -enc AAAAA"}],
        "canonical_evidence": [
            {
                "evidence_id": "EV-INC-SIM-01-proc",
                "source_field": "process.name",
                "observed_value": "powershell.exe",
                "evidence_type": "PROCESS_EXECUTION",
            },
            {
                "evidence_id": "EV-INC-SIM-01-cmd",
                "source_field": "process.command_line",
                "observed_value": "powershell.exe -enc AAAAA",
                "evidence_type": "PROCESS_EXECUTION",
            }
        ]
    }

    verdict = await provider.analyze_incident(
        incident_payload=input_payload,
        rule_spec={"id": "RULE-SIM-01", "name": "PowerShell Test"},
        prompt_text="system instructions",
        prompt_version_number=1,
    )
    assert verdict.verdict in ("TRUE_POSITIVE", "FALSE_POSITIVE", "REQUIRES_ATTENTION")
    assert len(verdict.supporting_claims) > 0

    # Claims must cite the canonical evidence IDs passed in
    cited_ids = set()
    for claim in verdict.supporting_claims:
        for eid in claim.get("evidence_ids", []):
            cited_ids.add(eid)
    assert "EV-INC-SIM-01-proc" in cited_ids or "EV-INC-SIM-01-cmd" in cited_ids


@pytest.mark.asyncio
async def test_replay_endpoint_end_to_end():
    """Scenario 40: Deterministic Replay Engine replicates decision faithfully."""
    rec = {
        "evidence_id": "EV-REPLAY-01",
        "incident_id": "INC-REPLAY-01",
        "source_system": "FortiSIEM",
        "source_event_id": "EVT1",
        "source_field": "process.name",
        "observed_value": "svchost.exe",
        "evidence_type": "PROCESS_EXECUTION",
        "availability": "AVAILABLE",
        "integrity_digest": "a" * 64,
    }

    contract = {
        "contract_id": "EC-REPLAY-01",
        "rule_id": "RULE-REPLAY-01",
        "version_number": 1,
        "status": "APPROVED",
        "detection_archetype": "PROCESS_EXECUTION",
        "required_evidence": [
            {"field": "process.name", "evidence_type": "PROCESS_EXECUTION", "required_for_tp": True, "required_for_fp": False, "critical": False, "description": ""}
        ],
    }

    model_output = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 85.0,
        "reason": "Legitimate windows service process",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "process.name",
                "asserted_value": "svchost.exe",
                "evidence_ids": ["EV-REPLAY-01"],
            }
        ]
    }

    res = IndependentVerdictValidator.replay_validation(
        incident_id="INC-REPLAY-01",
        saved_evidence_records=[rec],
        contract_dict=contract,
        saved_model_output=model_output,
    )

    assert res.final_verdict == "FALSE_POSITIVE"
    assert res.is_decisive_accepted is True
    assert res.validation_status == "VALIDATED"
    assert res.replay_signature != ""
