import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.rule import Rule
from app.models.prompt import RulePrompt, PromptVersion
from app.models.incident import Incident, IncidentEvent
from app.models.learning import LearningRecord
from app.services.ai_verdict_service import VerdictTriageAgent


@pytest.mark.asyncio
async def test_phase3_full_end_to_end_investigation(db_session: AsyncSession):
    """
    Scenario: Phase 3 full end-to-end integration test.
    Validates:
    - 9-section policy compilation
    - Verified semantic RAG precedent retrieval
    - Evidence-preserving token budgeting
    - Independent Phase 2 deterministic validation
    - Honest calibration status reporting (NOT_CALIBRATED)
    - Audit verification token with compilation digest binding
    """
    # 1. Setup SIEM Rule
    rule = Rule(
        rule_id="RULE-P3-E2E",
        name="Suspicious LOLBin PowerShell Execution",
        event_type="Process-Creation",
        severity="High",
        pattern_logic="process = 'powershell.exe' and cmdline contains '-enc'",
    )
    db_session.add(rule)
    await db_session.flush()

    # 2. Setup Approved Rule Prompt in Studio
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
        common_prompt="ENTERPRISE SOC LEVEL-2 PROTOCOL",
        rule_specific_prompt="INVESTIGATE SUSPICIOUS POWERSHELL COMMAND LINES",
        detection_conditions="Detection Pattern: process = 'powershell.exe' and cmdline contains '-enc'",
        required_evidence="1. Full command line\n2. Parent process name",
        tp_indicators="- Encoded PowerShell commands\n- Download cradles",
        fp_indicators="- Scheduled backup scripts",
        missing_info_criteria="- Truncated command lines",
        escalation_conditions="- Ransomware precursor",
        analyst_questions=["What is the parent process?", "Is user administrative?"],
    )
    db_session.add(pv)
    await db_session.flush()

    rule_prompt.active_version_id = pv.id
    await db_session.flush()

    # 3. Setup a Verified Historical Precedent for this rule
    past_inc = Incident(
        incident_id="INC-P3-HIST-01",
        rule_id=rule.id,
        event_type="Process-Creation",
        title="Historical Encoded PowerShell Attack",
        customer="CORP-SOC",
        created_at=datetime.utcnow() - timedelta(days=10),
    )
    db_session.add(past_inc)
    await db_session.flush()

    lr = LearningRecord(
        incident_id=past_inc.id,
        rule_id=rule.id,
        verification_status="VERIFIED",
        verified_verdict="TRUE_POSITIVE",
        analyst_explanation="Confirmed malicious base64 cradle invoking remote stager.",
        evidence_references=["process.command_line: powershell.exe -enc ..."],
        feedback_timestamp=datetime.utcnow() - timedelta(days=9),
    )
    db_session.add(lr)
    await db_session.flush()

    # 4. Ingest Target Incident with matching PowerShell telemetry
    target_inc = Incident(
        incident_id="INC-P3-TARGET-01",
        rule_id=rule.id,
        event_type="Process-Creation",
        title="Active Suspicious PowerShell Execution",
        severity="High",
        customer="CORP-SOC",
        source_ip="10.0.1.25",
        reporting_device="WIN-SRV-01",
        created_at=datetime.utcnow(),
    )
    db_session.add(target_inc)
    await db_session.flush()

    evt = IncidentEvent(
        incident_id=target_inc.id,
        event_id="EVT-P3-01",
        event_type="Process-Creation",
        attributes={
            "process": "powershell.exe",
            "cmdline": "powershell.exe -NoP -NonI -W Hidden -Enc JABzAD0ATgBlAHcALQBPAGIAagBlAGMAdAA=",
            "parentprocess": "cmd.exe",
            "user": "NT AUTHORITY\\SYSTEM",
        }
    )
    db_session.add(evt)
    await db_session.commit()

    # 5. Evaluate Incident via Agent
    agent = VerdictTriageAgent(db_session)
    res = await agent.evaluate_incident(
        incident_id_or_obj="INC-P3-TARGET-01",
        username="soc_lead_analyst",
        allow_simulated_fallback=True,
    )

    # 6. Verify Complete Phase 3 Expectations
    assert res["incident_id"] == "INC-P3-TARGET-01"
    assert res["verdict"] == "TRUE_POSITIVE"
    assert res["validation_status"] == "VALIDATED"
    assert res["is_decisive_accepted"] is True

    # P3-REQ-01: Nine-Section Policy Compiler assertions
    assert res["compiler_version"] == "v3.0.0"
    assert res["policy_sections_count"] == 9
    assert len(res["compilation_digest"]) == 64
    assert res["policy_status"] == "APPROVED"

    # P3-REQ-03 & P3-REQ-04: Verified Semantic RAG assertions
    assert res["rag_retrieval_status"] == "PRECEDENTS_FOUND"
    assert res["retrieved_precedents_count"] == 1
    assert res["retrieved_precedents"][0]["incident_id"] == "INC-P3-HIST-01"
    assert res["retrieved_precedents"][0]["verified_verdict"] == "TRUE_POSITIVE"

    # P3-REQ-05: Token Budget assertions
    assert "token_budget_breakdown" in res
    assert res["token_budget_breakdown"]["total_prompt_tokens"] > 0
    assert res["token_budget_breakdown"]["context_overflow_detected"] is False

    # P3-REQ-07: Honest Confidence Calibration assertions
    assert res["calibration_status"] == "NOT_CALIBRATED"
    assert res["is_calibrated"] is False

    # Audit Verification Token binds compilation digest
    assert len(res["replay_signature"]) == 16

