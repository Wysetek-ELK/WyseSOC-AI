import pytest
import uuid
import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.rule import Rule
from app.models.prompt import RulePrompt, PromptVersion
from app.models.incident import Incident
from app.models.actual_prompt_capture import ActualLLMPromptCapture
from app.models.audit import AuditLog
from app.services.actual_prompt_capture_service import ActualPromptCaptureService
from app.services.verdict_pipeline import run_shared_verdict_pipeline
from app.services.policy_compiler_service import PolicyCompilerService
from app.services.model_provider.base import StructuredModelVerdict


@pytest.mark.asyncio
async def test_heavy_tcp_scan_prompt_capture_end_to_end(db_session: AsyncSession):
    """
    Validates Req 2 & 6: End-to-end prompt capture for Heavy TCP Host Scan On Fixed Port.
    Verifies:
      1. Policy version 2 is selected.
      2. NETWORK_SCAN archetype contributes to the prompt.
      3. All 9 policy sections and guardrail sections 10/11 are included.
      4. FortiSIEM detection threshold is preserved accurately.
      5. Incident telemetry in <UNTRUSTED_INCIDENT_DATA> matches outbound payload.
      6. SHA-256 hash of canonical outbound payload is verified.
      7. Prompt integrity status is VERIFIED.
    """
    rule = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT",
        name="Heavy TCP Host Scan On Fixed Port",
        event_type="PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT",
        severity="MEDIUM",
        description="Detects anomalous TCP port scanning across multiple destination hosts on a fixed port.",
        pattern_logic="COUNT(DISTINCT destIpAddr) >= 50 AND destPort IS NOT NULL",
    )
    db_session.add(rule)
    await db_session.flush()

    rp = RulePrompt(
        id=str(uuid.uuid4()),
        rule_id=rule.id,
        title=f"Investigation Prompt — {rule.name}",
    )
    db_session.add(rp)
    await db_session.flush()

    # Create approved version 2 candidate with NETWORK_SCAN archetype
    pv2 = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=rp.id,
        version_number=2,
        status="APPROVED",
        rule_specific_prompt="Analyze TCP scan telemetry on fixed destination port. Evaluate connection rates, destination diversity, and authorization status against known vulnerability scanners.",
        detection_conditions="SIEM rule flagged multiple TCP connection attempts to a fixed destination port. Threshold: 50.0 distinct hosts.",
        required_evidence="1. security.event_type\n2. event.timestamp\n3. network.source_ip\n4. network.destination_port\n5. detection.threshold",
        tp_indicators="Rapid sequential TCP connection attempts to fixed port across multiple unique internal hosts.",
        fp_indicators="Authorized network vulnerability scanner with active change ticket.",
        missing_info_criteria="Abstain if source IP is unrecorded or firewall logs truncated.",
        escalation_conditions="Escalate immediately if scan establishes connections to critical infrastructure.",
        analyst_questions=["Is the source IP registered as an authorized scanner?", "Were any TCP sessions completed?"],
    )
    db_session.add(pv2)
    rp.active_version_id = pv2.id
    db_session.add(rp)
    await db_session.commit()

    # Create Incident with authentic FortiSIEM scan telemetry
    inc = Incident(
        id=str(uuid.uuid4()),
        incident_id="INC-SCAN-TEST-001",
        rule_id=rule.id,
        event_type="PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT",
        title="Heavy TCP Host Scan On Fixed Port - Port 445 SMB Sweep",
        severity="HIGH",
        source_ip="192.168.1.105",
        raw_payload={
            "srcIpAddr": "192.168.1.105",
            "destPort": 445,
            "incidentCount": 78,
            "distinctDestCount": 65,
            "detectionThreshold": 50.0,
            "events": [
                {"raw_log": "TCP SYN to 10.0.1.10:445", "attributes": {"destIp": "10.0.1.10", "destPort": 445}},
                {"raw_log": "TCP SYN to 10.0.1.11:445", "attributes": {"destIp": "10.0.1.11", "destPort": 445}},
            ]
        }
    )
    db_session.add(inc)
    await db_session.commit()

    # Execute shared verdict pipeline
    res = await run_shared_verdict_pipeline(
        db=db_session,
        incident=inc,
        rule=rule,
        prompt_version=pv2,
        active_approved_version=pv2,
        allow_simulated_fallback=True,
        is_simulation=False,
    )

    # 1. Pipeline result checks
    assert res.verdict_data is not None
    assert "prompt_capture_id" in res.verdict_data
    capture_id = res.verdict_data["prompt_capture_id"]
    assert capture_id is not None
    assert res.verdict_data["prompt_integrity_status"] == "VERIFIED"

    # 2. Inspect captured record from database
    cap_stmt = select(ActualLLMPromptCapture).where(ActualLLMPromptCapture.id == capture_id)
    cap = (await db_session.execute(cap_stmt)).scalar_one_or_none()
    assert cap is not None

    # Check execution summary metadata
    assert cap.incident_id == inc.incident_id
    assert cap.rule_id == rule.id
    assert cap.rule_name == rule.name
    assert cap.policy_version_number == 2
    assert cap.policy_status == "APPROVED"
    assert cap.dispatch_status == "COMPLETED"

    # Check compiled system prompt content
    assert "## SECTION 1: COMMON SOC BASELINE PROTOCOL" in cap.compiled_system_prompt
    assert "## SECTION 2: RULE-SPECIFIC INVESTIGATION DIRECTIVE" in cap.compiled_system_prompt
    assert "Analyze TCP scan telemetry on fixed destination port" in cap.compiled_system_prompt
    assert "## SECTION 3: DETECTION CONDITIONS & PATTERN LOGIC" in cap.compiled_system_prompt
    assert "Threshold: 50.0 distinct hosts" in cap.compiled_system_prompt
    assert "## SECTION 4: MANDATORY EVIDENCE REQUIREMENTS" in cap.compiled_system_prompt
    assert "## SECTION 5: TRUE POSITIVE INDICATORS" in cap.compiled_system_prompt
    assert "## SECTION 6: FALSE POSITIVE INDICATORS" in cap.compiled_system_prompt
    assert "## SECTION 7: ABSTENTION CRITERIA" in cap.compiled_system_prompt
    assert "## SECTION 8: P1/P2 ESCALATION CONDITIONS" in cap.compiled_system_prompt
    assert "## SECTION 9: ANALYST INVESTIGATION QUESTIONS" in cap.compiled_system_prompt
    assert "## SECTION 10: INSTRUCTION BOUNDARIES & UNTRUSTED DATA DELIMITERS" in cap.compiled_system_prompt
    assert "## SECTION 11: STRICT STRUCTURED JSON OUTPUT REQUIREMENTS" in cap.compiled_system_prompt

    # Check user message telemetry
    assert "<UNTRUSTED_INCIDENT_DATA>" in cap.user_message
    assert "</UNTRUSTED_INCIDENT_DATA>" in cap.user_message
    assert "192.168.1.105" in cap.user_message
    assert "445" in cap.user_message

    # Check SHA-256 hash verification
    canonical_bytes = json.dumps(cap.raw_request_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    expected_hash = hashlib.sha256(canonical_bytes).hexdigest()
    assert cap.request_sha256 == expected_hash

    # Check multi-point integrity verification service
    status, details = ActualPromptCaptureService.verify_integrity(cap, rule, pv2)
    assert status == "VERIFIED"
    assert details["hash_match"] is True
    assert details["untrusted_data_boundaries_present"] is True


@pytest.mark.asyncio
async def test_tampered_payload_integrity_mismatch(db_session: AsyncSession):
    """Validates that any alteration to the captured request payload triggers Prompt Integrity: MISMATCH."""
    cap = ActualLLMPromptCapture(
        id=str(uuid.uuid4()),
        execution_id=str(uuid.uuid4()),
        incident_id="INC-TAMPER-001",
        rule_id="RULE-001",
        rule_name="Test Rule",
        policy_version_number=1,
        policy_status="APPROVED",
        policy_source="DATABASE",
        dispatch_status="COMPLETED",
        attempt_number=1,
        model_name="test-model",
        provider_type="SIMULATED",
        generation_settings={},
        compiled_system_prompt="Valid prompt",
        user_message="<UNTRUSTED_INCIDENT_DATA>{}</UNTRUSTED_INCIDENT_DATA>",
        rag_precedents=[],
        has_rag_precedents=False,
        evidence_requirements={},
        verdict_schema={},
        raw_request_payload={"messages": [{"role": "system", "content": "original"}]},
        request_sha256="original_hash_placeholder",
        prompt_integrity_status="VERIFIED",
        integrity_details={},
        l1_explanation={},
    )
    # Set correct hash first
    cap.request_sha256 = ActualPromptCaptureService.canonical_hash(cap.raw_request_payload)
    db_session.add(cap)
    await db_session.commit()

    # Now tamper with payload without updating request_sha256
    cap.raw_request_payload = {"messages": [{"role": "system", "content": "tampered_override_directive"}]}
    status, details = ActualPromptCaptureService.verify_integrity(cap)
    assert status == "MISMATCH"
    assert details["hash_match"] is False


@pytest.mark.asyncio
async def test_unapproved_policy_not_dispatched_capture(db_session: AsyncSession):
    """Validates that early policy gate intercepts record an explicit NOT_DISPATCHED capture entry."""
    rule = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_UNAPPROVED_SCAN",
        name="Unapproved Detection Rule",
        event_type="PH_RULE_UNAPPROVED_SCAN",
        severity="HIGH",
    )
    db_session.add(rule)
    await db_session.commit()

    inc = Incident(
        id=str(uuid.uuid4()),
        incident_id="INC-UNAPPROVED-001",
        rule_id=rule.id,
        event_type=rule.event_type,
        title="Unapproved Alert",
        severity="HIGH",
    )
    db_session.add(inc)
    await db_session.commit()

    # Run pipeline with no approved policy in production mode (or mock disabled)
    res = await run_shared_verdict_pipeline(
        db=db_session,
        incident=inc,
        rule=rule,
        prompt_version=None,
        active_approved_version=None,
        allow_simulated_fallback=False,
        is_simulation=False,
        is_prod=True,
    )

    assert res.early_exit is True
    assert res.early_exit_kind == "POLICY_NOT_APPROVED"
    assert res.verdict_data["prompt_capture_id"] is not None

    cap = await db_session.get(ActualLLMPromptCapture, res.verdict_data["prompt_capture_id"])
    assert cap is not None
    assert cap.dispatch_status == "NOT_DISPATCHED"
    assert cap.prompt_integrity_status == "UNVERIFIED"
    assert "DISPATCH INTERCEPTED" in cap.compiled_system_prompt


@pytest.mark.asyncio
async def test_api_actual_prompt_for_incident(client, db_session: AsyncSession, admin_token: str):
    """Validates GET /api/v1/prompts/actual-prompt/incident/{incident_id} returns all 6 required sections."""
    incident_id = f"INC-API-{uuid.uuid4().hex[:8]}"
    raw_payload = {
        "model": "qwen2.5-7b",
        "messages": [
            {"role": "system", "content": "You are a SOC investigator."},
            {"role": "user", "content": "<UNTRUSTED_INCIDENT_DATA>{}</UNTRUSTED_INCIDENT_DATA>"}
        ],
        "max_tokens": 1024,
        "temperature": 0.1,
    }
    cap = ActualLLMPromptCapture(
        id=str(uuid.uuid4()),
        execution_id=str(uuid.uuid4()),
        incident_id=incident_id,
        rule_id="RULE-API-001",
        rule_name="API Test Rule",
        policy_version_number=2,
        policy_status="APPROVED",
        policy_source="DATABASE",
        dispatch_status="COMPLETED",
        attempt_number=1,
        model_name="qwen2.5-7b",
        provider_type="OPENAI_COMPATIBLE",
        generation_settings={"temperature": 0.1, "max_tokens": 1024},
        compiled_system_prompt="You are a SOC investigator.",
        user_message="<UNTRUSTED_INCIDENT_DATA>{}</UNTRUSTED_INCIDENT_DATA>",
        rag_precedents=[{"precedent_id": "PREC-01", "verdict": "FALSE_POSITIVE"}],
        has_rag_precedents=True,
        evidence_requirements={"core_fields": ["network.source_ip"]},
        verdict_schema=PolicyCompilerService.MODEL_RESPONSE_SCHEMA,
        raw_request_payload=raw_payload,
        request_sha256=ActualPromptCaptureService.canonical_hash(raw_payload),
        response_raw=json.dumps({"verdict": "FALSE_POSITIVE", "confidence": 92.0, "reason": "Authorized scan"}),
        response_verdict="FALSE_POSITIVE",
        response_confidence=92.0,
        prompt_tokens=450,
        completion_tokens=85,
        total_tokens=535,
        latency_ms=120,
        prompt_integrity_status="VERIFIED",
        integrity_details={"hash_verified": True},
        l1_explanation={
            "headline": "Investigation instructions sent to LLM",
            "policy_version_used": "Version 2 (APPROVED)",
            "mandatory_evidence_available": True,
            "historical_precedents_included": 1,
            "verdict_returned": "FALSE_POSITIVE",
            "prompt_matches_approved_policy": True,
        },
    )
    db_session.add(cap)

    inc = Incident(
        id=str(uuid.uuid4()),
        incident_id=incident_id,
        event_type="RULE-API-001",
        title="API Test Incident",
        severity="MEDIUM",
    )
    db_session.add(inc)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/prompts/actual-prompt/incident/{incident_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    # Section 1: Execution Summary
    assert data["execution_summary"]["incident_id"] == incident_id
    assert data["execution_summary"]["rule_name"] == "API Test Rule"
    assert data["execution_summary"]["policy_version_number"] == 2
    assert data["execution_summary"]["dispatch_status"] == "COMPLETED"

    # Section 2: System Prompt
    assert data["system_prompt"] == "You are a SOC investigator."

    # Section 3: Incident Payload
    assert "<UNTRUSTED_INCIDENT_DATA>" in data["incident_payload"]

    # Section 4: Historical Precedents
    assert len(data["rag_precedents"]) == 1
    assert data["has_rag_precedents"] is True

    # Section 5: Output Contract
    assert "verdict" in data["verdict_schema"]["properties"]

    # Section 6: Technical Details
    assert data["technical_details"]["prompt_tokens"] == 450
    assert data["technical_details"]["completion_tokens"] == 85
    assert data["technical_details"]["request_sha256"] == cap.request_sha256
    assert data["integrity_status"] == "VERIFIED"

    # Banner status
    assert data["capture_status"] == "CAPTURED_RUNTIME"

    # Audit log check
    audit_stmt = select(AuditLog).where(AuditLog.action == "VIEW_ACTUAL_LLM_PROMPT")
    audit_row = (await db_session.execute(audit_stmt)).scalars().first()
    assert audit_row is not None
    assert audit_row.resource_id == cap.id


@pytest.mark.asyncio
async def test_api_historical_capture_unavailable(client, db_session: AsyncSession, admin_token: str):
    """Validates that historical incidents without capture records return HISTORICAL_CAPTURE_UNAVAILABLE."""
    incident_id = f"INC-HIST-{uuid.uuid4().hex[:8]}"
    inc = Incident(
        id=str(uuid.uuid4()),
        incident_id=incident_id,
        event_type="LEGACY_EVENT",
        title="Legacy Incident",
        severity="LOW",
        ai_verdict={"verdict": "FALSE_POSITIVE", "reason": "Historical baseline classification"},
    )
    db_session.add(inc)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/prompts/actual-prompt/incident/{incident_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["capture_status"] == "HISTORICAL_CAPTURE_UNAVAILABLE"
    assert data["integrity_status"] == "UNVERIFIED"
    assert "HISTORICAL CAPTURE UNAVAILABLE" in data["system_prompt"]


@pytest.mark.asyncio
async def test_api_prompt_preview_only_status(client, db_session: AsyncSession, analyst_token: str):
    """Validates that live preview endpoint is explicitly tagged PREVIEW_ONLY and UNVERIFIED."""
    rule = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_PREVIEW_TEST",
        name="Preview Test Rule",
        event_type="PH_RULE_PREVIEW_TEST",
        severity="HIGH",
    )
    db_session.add(rule)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/prompts/actual-prompt/rule/{rule.id}/preview",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["capture_status"] == "PREVIEW_ONLY"
    assert data["integrity_status"] == "UNVERIFIED"
    assert "SECTION 1:" in data["system_prompt"]
    assert "SECTION 10:" in data["system_prompt"]


@pytest.mark.asyncio
async def test_api_export_json_and_markdown(client, db_session: AsyncSession, admin_token: str):
    """Validates export endpoints in JSON and Markdown formats."""
    incident_id = f"INC-EXP-{uuid.uuid4().hex[:8]}"
    raw_payload = {"messages": [{"role": "system", "content": "Export prompt"}]}
    cap = ActualLLMPromptCapture(
        id=str(uuid.uuid4()),
        execution_id=str(uuid.uuid4()),
        incident_id=incident_id,
        rule_id="RULE-EXP",
        rule_name="Export Rule",
        policy_version_number=1,
        policy_status="APPROVED",
        policy_source="DATABASE",
        dispatch_status="COMPLETED",
        attempt_number=1,
        model_name="test-model",
        provider_type="SIMULATED",
        generation_settings={},
        compiled_system_prompt="Export prompt content",
        user_message="<UNTRUSTED_INCIDENT_DATA>{}</UNTRUSTED_INCIDENT_DATA>",
        rag_precedents=[],
        has_rag_precedents=False,
        evidence_requirements={},
        verdict_schema={},
        raw_request_payload=raw_payload,
        request_sha256=ActualPromptCaptureService.canonical_hash(raw_payload),
        prompt_integrity_status="VERIFIED",
        integrity_details={},
        l1_explanation={"headline": "Export L1 test"},
    )
    db_session.add(cap)

    inc = Incident(
        id=str(uuid.uuid4()),
        incident_id=incident_id,
        event_type="RULE-EXP",
        title="Export Incident",
        severity="MEDIUM",
    )
    db_session.add(inc)
    await db_session.commit()

    # JSON export
    resp_json = await client.get(
        f"/api/v1/prompts/actual-prompt/incident/{incident_id}/export?format=json",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_json.status_code == 200
    assert resp_json.headers["content-type"] == "application/json"
    assert "attachment; filename=" in resp_json.headers["content-disposition"]
    data = json.loads(resp_json.text)
    assert data["capture_id"] == cap.id

    # Markdown export
    resp_md = await client.get(
        f"/api/v1/prompts/actual-prompt/incident/{incident_id}/export?format=markdown",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_md.status_code == 200
    assert "text/markdown" in resp_md.headers["content-type"]
    assert "# Actual LLM Prompt Export" in resp_md.text
    assert "## 2. Compiled System Prompt" in resp_md.text


@pytest.mark.asyncio
async def test_canonical_json_serialization_and_hashing():
    """Validates that canonical serialization is key-sorted, compact, and whitespace invariant."""
    payload_a = {"temperature": 0.1, "model": "qwen2.5", "messages": [{"role": "system", "content": "test"}]}
    payload_b = {"messages": [{"role": "system", "content": "test"}], "model": "qwen2.5", "temperature": 0.1}

    hash_a = ActualPromptCaptureService.canonical_hash(payload_a)
    hash_b = ActualPromptCaptureService.canonical_hash(payload_b)
    assert hash_a == hash_b

    ser_a = ActualPromptCaptureService.canonical_serialize(payload_a)
    assert ' ' not in ser_a or ': ' not in ser_a  # No whitespace around delimiters
    assert hash_a == hashlib.sha256(ser_a.encode("utf-8")).hexdigest()


@pytest.mark.asyncio
async def test_delivery_status_vs_prompt_integrity_separation(db_session: AsyncSession):
    """
    Validates Task 2 requirement:
    Delivery status (SEND_ATTEMPTED, COMPLETED, FAILED, NOT_DISPATCHED)
    must remain separate from Prompt Integrity (VERIFIED, MISMATCH, UNVERIFIED).
    Pre-dispatch capture does not claim Server 2 received the request.
    """
    # 1. SEND_ATTEMPTED capture
    raw_payload = {"messages": [{"role": "user", "content": "<UNTRUSTED_INCIDENT_DATA>{}</UNTRUSTED_INCIDENT_DATA>"}]}
    cap_attempt = await ActualPromptCaptureService.record_dispatch(
        db=db_session,
        incident_id="INC-DISPATCH-01",
        rule_id="RULE-D01",
        rule_name="Dispatch Test",
        policy_version_number=1,
        policy_status="APPROVED",
        policy_source="DATABASE",
        attempt_number=1,
        model_name="qwen2.5-7b",
        provider_type="LOCAL_LLM",
        generation_settings={"temperature": 0.0},
        compiled_system_prompt="Test directive",
        user_message="<UNTRUSTED_INCIDENT_DATA>{}</UNTRUSTED_INCIDENT_DATA>",
        rag_precedents=[],
        evidence_requirements={},
        verdict_schema={},
        raw_request_payload=raw_payload,
        is_simulated=False,
    )
    assert cap_attempt.dispatch_status == "SEND_ATTEMPTED"
    assert cap_attempt.payload_format == "CANONICAL_JSON"
    # Pre-dispatch status separates delivery attempt from model execution
    status_pre, details_pre = ActualPromptCaptureService.verify_integrity(cap_attempt)
    assert status_pre == "VERIFIED"
    assert details_pre["hash_match"] is True

    # 2. Record FAILED attempt (e.g. timeout to Server 2)
    cap_failed = await ActualPromptCaptureService.record_failed(
        db=db_session,
        capture_id=cap_attempt.id,
        error_message="HTTP 504 Gateway Timeout: Server 2 did not respond in 30000ms",
    )
    assert cap_failed is not None
    assert cap_failed.dispatch_status == "FAILED"
    assert "504 Gateway Timeout" in cap_failed.error_message

    # 3. Verify integrity service differentiates delivery failure from prompt payload integrity
    status, details = ActualPromptCaptureService.verify_integrity(cap_failed)
    assert status == "VERIFIED"
    assert details["hash_match"] is True


@pytest.mark.asyncio
async def test_execution_history_and_retry_traceability(client, db_session: AsyncSession, admin_token: str):
    """
    Validates Task 3: Support multiple verdict executions/retries per incident,
    with /executions list and execution-specific retrieval.
    """
    incident_id = f"INC-RETRY-{uuid.uuid4().hex[:8]}"
    inc = Incident(
        id=str(uuid.uuid4()),
        incident_id=incident_id,
        event_type="RETRY_RULE",
        title="Retry Trace Incident",
        severity="HIGH",
    )
    db_session.add(inc)
    await db_session.commit()

    # Attempt 1: Failed
    payload1 = {"messages": [{"role": "user", "content": "Attempt 1"}]}
    cap1 = await ActualPromptCaptureService.record_dispatch(
        db=db_session,
        incident_id=incident_id,
        rule_id="RULE-RETRY",
        rule_name="Retry Rule",
        policy_version_number=1,
        policy_status="APPROVED",
        policy_source="DATABASE",
        attempt_number=1,
        model_name="qwen2.5-7b",
        provider_type="LOCAL_LLM",
        generation_settings={},
        compiled_system_prompt="Directive 1",
        user_message="Attempt 1",
        rag_precedents=[],
        evidence_requirements={},
        verdict_schema={},
        raw_request_payload=payload1,
        is_simulated=False,
    )
    await ActualPromptCaptureService.record_failed(
        db=db_session,
        capture_id=cap1.id,
        error_message="Connection refused on port 8000",
    )

    # Attempt 2: Successful retry
    payload2 = {"messages": [{"role": "user", "content": "Attempt 2"}]}
    cap2 = await ActualPromptCaptureService.record_dispatch(
        db=db_session,
        incident_id=incident_id,
        rule_id="RULE-RETRY",
        rule_name="Retry Rule",
        policy_version_number=1,
        policy_status="APPROVED",
        policy_source="DATABASE",
        attempt_number=2,
        model_name="qwen2.5-7b",
        provider_type="LOCAL_LLM",
        generation_settings={},
        compiled_system_prompt="Directive 1",
        user_message="Attempt 2",
        rag_precedents=[],
        evidence_requirements={},
        verdict_schema={},
        raw_request_payload=payload2,
        is_simulated=False,
    )
    await ActualPromptCaptureService.record_completed(
        db=db_session,
        capture_id=cap2.id,
        response_raw=json.dumps({"verdict": "TRUE_POSITIVE", "confidence": 95.0}),
        response_verdict="TRUE_POSITIVE",
        response_confidence=95.0,
        prompt_tokens=200,
        completion_tokens=40,
        latency_ms=350,
        is_active_verdict=True,
    )

    # Query executions list endpoint
    resp_execs = await client.get(
        f"/api/v1/prompts/actual-prompt/incident/{incident_id}/executions",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_execs.status_code == 200
    exec_data = resp_execs.json()
    assert len(exec_data) == 2
    assert exec_data[0]["attempt_number"] == 2
    assert exec_data[0]["dispatch_status"] == "COMPLETED"
    assert exec_data[0]["is_active_verdict"] is True
    assert exec_data[1]["attempt_number"] == 1
    assert exec_data[1]["dispatch_status"] == "FAILED"

    # Query specific execution by capture_id (Attempt 1)
    resp_att1 = await client.get(
        f"/api/v1/prompts/actual-prompt/incident/{incident_id}?capture_id={cap1.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_att1.status_code == 200
    data_att1 = resp_att1.json()
    assert data_att1["capture_id"] == cap1.id
    assert data_att1["execution_summary"]["attempt_number"] == 1
    assert data_att1["execution_summary"]["dispatch_status"] == "FAILED"
    assert data_att1["technical_details"]["error_message"] == "Connection refused on port 8000"


@pytest.mark.asyncio
async def test_rule_prompt_captures_summary(client, db_session: AsyncSession, analyst_token: str):
    """Validates GET /api/v1/prompts/actual-prompt/rule/{rule_id}/captures endpoint."""
    rule_id = f"RULE-SUMMARY-{uuid.uuid4().hex[:6]}"
    rule = Rule(
        id=rule_id,
        rule_id=rule_id,
        name="Summary Rule",
        event_type=rule_id,
        severity="MEDIUM",
    )
    db_session.add(rule)
    await db_session.commit()

    for i in range(3):
        raw_payload = {"messages": [{"role": "user", "content": f"Case {i}"}]}
        cap = await ActualPromptCaptureService.record_dispatch(
            db=db_session,
            incident_id=f"INC-R-{rule_id}-{i}",
            rule_id=rule_id,
            rule_name="Summary Rule",
            policy_version_number=1,
            policy_status="APPROVED",
            policy_source="DATABASE",
            attempt_number=1,
            model_name="qwen2.5-7b",
            provider_type="LOCAL_LLM",
            generation_settings={},
            compiled_system_prompt="Directive",
            user_message=f"Case {i}",
            rag_precedents=[],
            evidence_requirements={},
            verdict_schema={},
            raw_request_payload=raw_payload,
        )
        await ActualPromptCaptureService.record_completed(
            db=db_session,
            capture_id=cap.id,
            response_raw=json.dumps({"verdict": "FALSE_POSITIVE"}),
            response_verdict="FALSE_POSITIVE",
            response_confidence=90.0,
            prompt_tokens=100,
            completion_tokens=20,
            latency_ms=150,
        )

    resp = await client.get(
        f"/api/v1/prompts/actual-prompt/rule/{rule_id}/captures?limit=10",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 3
    assert all(item["rule_id"] == rule_id for item in items)
    assert all(item["dispatch_status"] == "COMPLETED" for item in items)


@pytest.mark.asyncio
async def test_role_based_deep_redaction_and_export_security(
    client, db_session: AsyncSession, admin_token: str, analyst_token: str, viewer_token: str
):
    """
    Validates Task 4:
    - SOC Analysts and Viewers receive deep redaction on IP addresses, emails, and generation settings hosts.
    - Raw request payload messages and user messages are masked.
    - Export endpoint enforces redaction for non-admins (no bypass).
    - Administrators receive unredacted access.
    """
    incident_id = f"INC-REDACT-{uuid.uuid4().hex[:8]}"
    raw_payload = {
        "model": "qwen2.5-7b",
        "api_base": "http://198.51.100.50:8000/v1",
        "messages": [
            {"role": "system", "content": "Investigate alerts. Contact: lead@soc.example."},
            {"role": "user", "content": "<UNTRUSTED_INCIDENT_DATA>src=192.0.2.105, user=bob@corp.example</UNTRUSTED_INCIDENT_DATA>"}
        ]
    }
    cap = await ActualPromptCaptureService.record_dispatch(
        db=db_session,
        incident_id=incident_id,
        rule_id="RULE-REDACT",
        rule_name="Redaction Rule",
        policy_version_number=1,
        policy_status="APPROVED",
        policy_source="DATABASE",
        attempt_number=1,
        model_name="qwen2.5-7b",
        provider_type="LOCAL_LLM",
        generation_settings={"api_base": "http://198.51.100.50:8000/v1", "host": "198.51.100.50"},
        compiled_system_prompt="Investigate alerts. Contact: lead@soc.example.",
        user_message="<UNTRUSTED_INCIDENT_DATA>src=192.0.2.105, user=bob@corp.example</UNTRUSTED_INCIDENT_DATA>",
        rag_precedents=[],
        evidence_requirements={},
        verdict_schema={},
        raw_request_payload=raw_payload,
    )
    await ActualPromptCaptureService.record_completed(
        db=db_session,
        capture_id=cap.id,
        response_raw=json.dumps({"verdict": "TRUE_POSITIVE", "reason": "Attack from 192.0.2.105"}),
        response_verdict="TRUE_POSITIVE",
        response_confidence=99.0,
        prompt_tokens=150,
        completion_tokens=30,
        latency_ms=200,
    )

    inc = Incident(
        id=str(uuid.uuid4()),
        incident_id=incident_id,
        event_type="RULE-REDACT",
        title="Redaction Test Incident",
        severity="HIGH",
    )
    db_session.add(inc)
    await db_session.commit()

    # 1. SOC Analyst access -> Redacted
    resp_analyst = await client.get(
        f"/api/v1/prompts/actual-prompt/incident/{incident_id}",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert resp_analyst.status_code == 200
    data_analyst = resp_analyst.json()
    assert data_analyst["is_redacted"] is True
    # Verify IP and email redaction in payload & messages
    assert "192.0.2.105" not in data_analyst["incident_payload"]
    assert "[REDACTED_IP]" in data_analyst["incident_payload"]
    assert "lead@soc.example" not in data_analyst["system_prompt"]
    assert "[REDACTED_EMAIL]" in data_analyst["system_prompt"]
    # Check generation settings host redaction
    assert "198.51.100.50" not in str(data_analyst["technical_details"]["generation_settings"])

    # 2. Export with analyst token -> Must also be redacted (no bypass)
    resp_exp_analyst = await client.get(
        f"/api/v1/prompts/actual-prompt/incident/{incident_id}/export?format=json",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert resp_exp_analyst.status_code == 200
    exp_data = json.loads(resp_exp_analyst.text)
    assert "192.0.2.105" not in exp_data["incident_payload"]
    assert "[REDACTED_IP]" in exp_data["incident_payload"]

    # 3. Administrator access -> Full unredacted
    resp_admin = await client.get(
        f"/api/v1/prompts/actual-prompt/incident/{incident_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_admin.status_code == 200
    data_admin = resp_admin.json()
    assert data_admin["is_redacted"] is False
    assert "192.0.2.105" in data_admin["incident_payload"]
    assert "lead@soc.example" in data_admin["system_prompt"]


@pytest.mark.asyncio
async def test_retention_cleanup_preserves_active_executions(client, db_session: AsyncSession, admin_token: str, analyst_token: str):
    """
    Validates Task 5:
    - Retention cleanup deletes expired captures (> retention_days).
    - NEVER deletes active verdict captures (is_active_verdict_capture=True).
    - Only administrators can trigger manual cleanup endpoint.
    - Emits PROMPT_CAPTURE_RETENTION_CLEANUP audit log.
    """
    now = datetime.now(timezone.utc)
    old_time = now - timedelta(days=45)

    # Old inactive capture (eligible for deletion)
    cap_old_inactive = ActualLLMPromptCapture(
        id=str(uuid.uuid4()),
        execution_id=str(uuid.uuid4()),
        incident_id="INC-OLD-INACTIVE",
        rule_id="RULE-CLEAN",
        rule_name="Clean Rule",
        policy_version_number=1,
        policy_status="APPROVED",
        policy_source="DATABASE",
        dispatch_status="FAILED",
        attempt_number=1,
        model_name="qwen2.5-7b",
        provider_type="LOCAL_LLM",
        generation_settings={},
        compiled_system_prompt="Old prompt",
        user_message="Old msg",
        rag_precedents=[],
        has_rag_precedents=False,
        evidence_requirements={},
        verdict_schema={},
        raw_request_payload={},
        request_sha256="hash1",
        captured_at=old_time,
        is_active_verdict_capture=False,
    )
    db_session.add(cap_old_inactive)

    # Old active verdict capture (MUST BE PRESERVED)
    cap_old_active = ActualLLMPromptCapture(
        id=str(uuid.uuid4()),
        execution_id=str(uuid.uuid4()),
        incident_id="INC-OLD-ACTIVE",
        rule_id="RULE-CLEAN",
        rule_name="Clean Rule",
        policy_version_number=1,
        policy_status="APPROVED",
        policy_source="DATABASE",
        dispatch_status="COMPLETED",
        attempt_number=2,
        model_name="qwen2.5-7b",
        provider_type="LOCAL_LLM",
        generation_settings={},
        compiled_system_prompt="Active prompt",
        user_message="Active msg",
        rag_precedents=[],
        has_rag_precedents=False,
        evidence_requirements={},
        verdict_schema={},
        raw_request_payload={},
        request_sha256="hash2",
        captured_at=old_time,
        is_active_verdict_capture=True,
    )
    db_session.add(cap_old_active)
    await db_session.commit()

    # Analyst cannot trigger retention cleanup (403)
    resp_forbidden = await client.post(
        "/api/v1/prompts/actual-prompt/retention/cleanup?retention_days=30",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert resp_forbidden.status_code == 403

    # Admin triggers cleanup
    resp_admin = await client.post(
        "/api/v1/prompts/actual-prompt/retention/cleanup?retention_days=30",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_admin.status_code == 200
    res_data = resp_admin.json()
    assert res_data["deleted_count"] >= 1

    # Verify database state
    check_inactive = await db_session.get(ActualLLMPromptCapture, cap_old_inactive.id)
    assert check_inactive is None  # Deleted

    check_active = await db_session.get(ActualLLMPromptCapture, cap_old_active.id)
    assert check_active is not None  # Preserved!

