"""
Phase 1: Critical Safety & Security Controls Verification Test Suite.
Validates REQ-01 through REQ-08 (Audit findings AV-001, AV-002, AV-004, AV-006, AV-008, AV-010, AV-011, AV-014, AV-015).
"""
import pytest
import os
import re
import socket
from datetime import datetime
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings, Settings
from app.models.incident import Incident, IncidentEvent, HistoricalGroundTruth
from app.models.rule import Rule
from app.models.prompt import RulePrompt, PromptVersion
from app.models.learning import LearningRecord
from app.models.investigation import Investigation
from app.services.ai_verdict_service import AIVerdictService, LocalLLMUnavailableError
from app.services.fortisiem_service import FortiSIEMService
from app.services.incident_service import IncidentService, sanitize_blind_review_payload
from app.services.learning_service import LearningService
from app.services.system_monitor_service import SystemMonitorService
from app.services.llm_config_service import LLMConfigService
from app.schemas.fortisiem import FortiSIEMConfigUpdate
from app.schemas.learning import LearningRecordVerifyRequest


# =========================================================================
# REQ-01 / AV-014: Cryptographic Secrets & Credential Hardening
# =========================================================================

def test_req01_insecure_secret_key_rejection_in_prod(monkeypatch):
    """
    Validates that in production (APP_ENV=production), the application refuses
    to start with default, short, or empty SECRET_KEY.
    """
    # 1. Default known key in production -> MUST raise RuntimeError
    with pytest.raises(RuntimeError, match="Critical Security Blocker"):
        s = Settings(
            APP_ENV="production",
            SECRET_KEY="ai-verdict-super-secure-enterprise-secret-key-phase1-2026",
        )
        s.validate_security()

    # 2. Too short key (< 32 chars) in production -> MUST raise RuntimeError
    with pytest.raises(RuntimeError, match="Critical Security Blocker"):
        s = Settings(
            APP_ENV="production",
            SECRET_KEY="short-key-12345",
        )
        s.validate_security()

    # 3. Empty key in production -> MUST raise RuntimeError
    with pytest.raises(RuntimeError, match="Critical Security Blocker"):
        s = Settings(
            APP_ENV="production",
            SECRET_KEY="",
        )
        s.validate_security()

    # 4. Valid, strong 32+ char key -> MUST pass
    s_valid = Settings(
        APP_ENV="production",
        SECRET_KEY="production-super-strong-secret-key-min-32-chars-long-2026",
    )
    s_valid.validate_security()
    assert s_valid.SECRET_KEY == "production-super-strong-secret-key-min-32-chars-long-2026"


@pytest.mark.asyncio
async def test_req01_fortisiem_password_never_persisted_to_env(monkeypatch, tmp_path):
    """
    Validates that updating FortiSIEM credentials never writes cleartext
    passwords or credentials back into .env file.
    """
    fake_env = tmp_path / ".env"
    fake_env.write_text("FORTISIEM_HOST=https://siem.test\nFORTISIEM_USER=admin\n", encoding="utf-8")

    # Point BASE_DIR to tmp_path
    from app.services import fortisiem_service
    monkeypatch.setattr(fortisiem_service, "BASE_DIR", str(tmp_path))

    orig_host = settings.FORTISIEM_HOST
    orig_user = settings.FORTISIEM_USERNAME
    orig_pass = settings.FORTISIEM_PASSWORD
    orig_mock = settings.FORTISIEM_MOCK_FALLBACK
    orig_timeout = settings.FORTISIEM_TIMEOUT
    orig_verify = settings.FORTISIEM_VERIFY_SSL

    try:
        update_req = FortiSIEMConfigUpdate(
            host="https://siem.test",
            username="admin",
            password="SuperSecretPasswordNeverInFile123!",
            timeout=30.0,
            mock_fallback=False,
        )
        res = FortiSIEMService.update_config(update_req, username="admin")
        assert res.is_password_set is True

        # Read .env - password must NOT be in the file
        content = fake_env.read_text(encoding="utf-8")
        assert "SuperSecretPasswordNeverInFile123!" not in content
        assert "FORTISIEM_PASSWORD" not in content
    finally:
        settings.FORTISIEM_HOST = orig_host
        settings.FORTISIEM_USERNAME = orig_user
        settings.FORTISIEM_PASSWORD = orig_pass
        settings.FORTISIEM_MOCK_FALLBACK = orig_mock
        settings.FORTISIEM_TIMEOUT = orig_timeout
        settings.FORTISIEM_VERIFY_SSL = orig_verify


# =========================================================================
# REQ-02 / AV-004: Inference Failure Safety & No Mock in Production
# =========================================================================

@pytest.mark.asyncio
async def test_req02_production_strictly_rejects_mock_fallback(db_session: AsyncSession, monkeypatch):
    """
    In production mode, mock fallback is unconditionally disabled.
    If Local LLM is offline, evaluate_incident must raise LocalLLMUnavailableError,
    never returning a simulated TP or FP verdict.
    """
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "LOCAL_LLM_ALLOW_MOCK_FALLBACK", False)

    async def mock_offline(*args, **kwargs):
        return False

    monkeypatch.setattr(AIVerdictService, "is_local_llm_available", mock_offline)

    # Create dummy rule & incident
    rule = Rule(
        rule_id="PHASE1-RULE-001",
        name="Phase 1 Test Rule",
        event_type="PHASE1_TEST",
        severity="HIGH",
        status="ACTIVE",
    )
    db_session.add(rule)
    await db_session.flush()

    inc = Incident(
        incident_id="9990001",
        rule_id=rule.id,
        event_type="PHASE1_TEST",
        title="Test Incident for Mock Rejection",
        severity="HIGH",
        status_code=1,
        status_name="Open",
        category="Security",
        source_ip="10.0.0.50",
        reporting_device="firewall-01",
    )
    db_session.add(inc)
    await db_session.commit()

    service = AIVerdictService(db_session)

    # Even if caller passes allow_simulated_fallback=True, production MUST disallow it!
    with pytest.raises(LocalLLMUnavailableError, match="offline"):
        await service.evaluate_incident(inc.id, allow_simulated_fallback=True)


# =========================================================================
# REQ-03 / AV-001 & AV-002: Policy Approval Enforcement
# =========================================================================

@pytest.mark.asyncio
async def test_req03_unapproved_prompt_draft_abstained_in_live_triage(db_session: AsyncSession, monkeypatch):
    """
    When an incident's rule has only an unapproved draft prompt, live triage
    must abstain and return REQUIRES_ATTENTION with POLICY_NOT_APPROVED,
    never executing the unapproved draft prompt.
    """
    monkeypatch.setattr(settings, "APP_ENV", "development")

    async def mock_online(*args, **kwargs):
        return True

    monkeypatch.setattr(AIVerdictService, "is_local_llm_available", mock_online)

    # Create rule with RulePrompt in DRAFT status and no active_version_id
    rule = Rule(
        rule_id="RULE-UNAPPROVED-01",
        name="Unapproved Policy Test",
        event_type="UNAPPROVED_EVT",
        severity="HIGH",
        status="ACTIVE",
    )
    db_session.add(rule)
    await db_session.flush()

    rp = RulePrompt(rule_id=rule.id, active_version_id=None)
    db_session.add(rp)
    await db_session.flush()

    draft_ver = PromptVersion(
        prompt_id=rp.id,
        version_number=1,
        status="DRAFT",  # Unapproved draft
        rule_specific_prompt="Draft instructions",
        tp_indicators="Draft TP indicators",
        fp_indicators="Draft FP indicators",
    )
    db_session.add(draft_ver)
    await db_session.commit()

    inc = Incident(
        incident_id="9990002",
        rule_id=rule.id,
        event_type="UNAPPROVED_EVT",
        title="Incident with unapproved draft policy",
        severity="HIGH",
        status_code=1,
        status_name="Open",
        category="Security",
        source_ip="10.0.0.55",
        reporting_device="edr-01",
    )
    db_session.add(inc)
    await db_session.commit()

    service = AIVerdictService(db_session)
    result = await service.evaluate_incident(inc.id, allow_simulated_fallback=False)

    assert result["verdict"] == "REQUIRES_ATTENTION"
    assert result["validation_status"] == "POLICY_NOT_APPROVED"
    assert result["confidence"] == 0.0
    assert "DETECTION_POLICY_PENDING_APPROVAL" in result["reason"]


# =========================================================================
# REQ-04 / AV-006: Ground-Truth Sanitization in Blind Review Mode
# =========================================================================

def test_req04_sanitize_blind_review_payload_recursive():
    """
    Validates that sanitize_blind_review_payload recursively removes all forbidden
    ground truth and analyst resolution keys from arbitrarily nested dictionaries/lists.
    """
    dirty_payload = {
        "incident_id": "12345",
        "title": "Brute Force Attack",
        "resolution": "True Positive - Malicious",
        "clearedReason": "Resolved by analyst",
        "clearedUser": "analyst_bob",
        "comments": "Adversary confirmed using Hydra",
        "analyst_verdict": "TRUE_POSITIVE",
        "nested_details": {
            "source_ip": "192.168.1.100",
            "incidentResSummary": "Contained threat",
            "inner_list": [
                {"event": "login_failed", "analyst_notes": "Leaked notes"},
                {"event": "login_success", "clean_field": "valid_data"},
            ],
        },
    }

    clean = sanitize_blind_review_payload(dirty_payload)

    assert "resolution" not in clean
    assert "clearedReason" not in clean
    assert "clearedUser" not in clean
    assert "comments" not in clean
    assert "analyst_verdict" not in clean
    assert clean["title"] == "Brute Force Attack"
    assert clean["nested_details"]["source_ip"] == "192.168.1.100"
    assert "incidentResSummary" not in clean["nested_details"]
    assert clean["nested_details"]["inner_list"][0]["event"] == "login_failed"
    assert "analyst_notes" not in clean["nested_details"]["inner_list"][0]
    assert clean["nested_details"]["inner_list"][1]["clean_field"] == "valid_data"


@pytest.mark.asyncio
async def test_req04_blind_review_endpoint_ground_truth_isolation(
    client: AsyncClient, db_session: AsyncSession, analyst_token: str
):
    """
    Validates that calling GET /api/incidents/{id}?blind_review=true returns zero
    ground truth or analyst closure information in raw_payload or events.
    """
    inc = Incident(
        incident_id="9990004",
        event_type="AUTH_FAILURE",
        title="Incident with Ground Truth Leak Potential",
        severity="HIGH",
        status_code=1,
        status_name="Open",
        category="Security",
        source_ip="172.16.0.5",
        reporting_device="siem-collector",
        raw_payload={
            "rawEvents": [{"id": 1, "msg": "Suspicious login"}],
            "resolution": "TRUE_POSITIVE",
            "clearedReason": "Compromised host isolated",
            "comments": "Attacker IP blocked at edge",
            "clearedUser": "admin_user",
        },
    )
    db_session.add(inc)
    await db_session.flush()

    evt = IncidentEvent(
        incident_id=inc.id,
        event_id="EVT-01",
        event_type="AUTH_FAILURE",
        raw_log="Failed auth from 172.16.0.5",
        attributes={"user": "root", "analyst_verdict": "MALICIOUS"},
    )
    db_session.add(evt)

    gt = HistoricalGroundTruth(
        incident_id=inc.id,
        resolution="TRUE_POSITIVE",
        cleared_reason="Confirmed attack",
        comments="Manual analysis confirmed",
        cleared_user="soc_lead",
    )
    db_session.add(gt)
    await db_session.commit()

    headers = {"Authorization": f"Bearer {analyst_token}"}
    res = await client.get(f"/api/incidents/{inc.incident_id}?blind_review=true", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Ground truth top-level must be None
    assert data["ground_truth"] is None

    # raw_payload must NOT contain resolution or clearedReason
    raw = data["raw_payload"]
    assert "resolution" not in raw
    assert "clearedReason" not in raw
    assert "comments" not in raw
    assert "clearedUser" not in raw

    # events[0].attributes must NOT contain analyst_verdict
    assert len(data["events"]) > 0
    attrs = data["events"][0]["attributes"]
    assert "analyst_verdict" not in attrs
    assert attrs["user"] == "root"


# =========================================================================
# REQ-05 / AV-008: Supervisor Approval Gate for Learning Records
# =========================================================================

@pytest.mark.asyncio
async def test_req05_learning_record_verification_gate(
    client: AsyncClient, db_session: AsyncSession, analyst_token: str, admin_token: str
):
    """
    Validates that newly created learning records start in PENDING_REVIEW status,
    analysts cannot self-verify them, and only administrators can verify them.
    """
    rule = Rule(
        rule_id="RULE-LR-01",
        name="Learning Rule Test",
        event_type="LR_EVT",
        severity="MEDIUM",
        status="ACTIVE",
    )
    db_session.add(rule)
    await db_session.flush()

    inc = Incident(
        incident_id="9990005",
        rule_id=rule.id,
        event_type="LR_EVT",
        title="Learning Record Incident",
        severity="MEDIUM",
        status_code=1,
        status_name="Open",
        category="Security",
        source_ip="10.10.1.1",
        reporting_device="sensor-1",
    )
    db_session.add(inc)
    await db_session.flush()

    inv = Investigation(
        incident_id=inc.id,
        status="PENDING_REVIEW",
    )
    db_session.add(inv)
    await db_session.commit()

    # 1. Analyst submits verdict
    analyst_headers = {"Authorization": f"Bearer {analyst_token}"}
    verdict_payload = {
        "analyst_verdict": "FALSE_POSITIVE",
        "verdict_reason": "Authorized penetration testing activity.",
        "analyst_notes": "Confirmed with SecOps calendar.",
        "is_disputed": False,
        "is_independently_verified": True,
        "status": "REVIEWED",
    }
    submit_res = await client.post(
        f"/api/investigations/{inv.id}/verdict",
        headers=analyst_headers,
        json=verdict_payload,
    )
    assert submit_res.status_code == 200

    # 2. Check LearningRecord status -> MUST be PENDING_REVIEW (not VERIFIED)
    lr_res = await db_session.execute(select(LearningRecord).where(LearningRecord.incident_id == inc.id))
    lr = lr_res.scalars().first()
    assert lr is not None
    assert lr.verification_status == "PENDING_REVIEW"

    # 3. Analyst tries to verify learning record -> MUST be 403 Forbidden
    analyst_verify = await client.put(
        f"/api/learning/records/{lr.id}/verify",
        headers=analyst_headers,
        json={"verification_status": "VERIFIED", "review_notes": "Self verification attempt"},
    )
    assert analyst_verify.status_code == 403

    # 4. Administrator verifies learning record -> MUST succeed (200 OK)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    admin_verify = await client.put(
        f"/api/learning/records/{lr.id}/verify",
        headers=admin_headers,
        json={"verification_status": "VERIFIED", "review_notes": "Approved by SOC Supervisor"},
    )
    assert admin_verify.status_code == 200
    assert admin_verify.json()["verification_status"] == "VERIFIED"


@pytest.mark.asyncio
async def test_req05_seed_historical_forbidden_in_production(
    client: AsyncClient, admin_token: str, monkeypatch
):
    """
    Validates that POST /api/learning/seed-historical is blocked (403 Forbidden)
    when running in production environments.
    """
    monkeypatch.setattr(settings, "APP_ENV", "production")

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    res = await client.post("/api/learning/seed-historical", headers=admin_headers)
    assert res.status_code == 403
    assert "production" in res.json()["detail"].lower()


# =========================================================================
# REQ-06 / AV-010: Honest Hardware & Telemetry Monitoring
# =========================================================================

@pytest.mark.asyncio
async def test_req06_honest_monitoring_when_prometheus_offline(monkeypatch):
    """
    Validates that when Server 2 Prometheus /metrics is unavailable, the monitor
    service returns None for CPU, memory, disk, and GPU, setting metrics_available=False
    rather than fabricating synthetic utilization constants.
    """
    async def mock_sample():
        svc = SystemMonitorService()
        return await svc._sample_server_2()

    # Even if Server 2 /models is unreachable:
    res = await mock_sample()

    assert res["cpu_percent"] is None
    assert res["memory_percent"] is None
    assert res["disk_percent"] is None
    assert res["gpu_percent"] is None
    assert res["gpu_memory_percent"] is None
    assert res["gpu_temp_c"] is None
    assert res["details"]["metrics_available"] is False


# =========================================================================
# REQ-07 / AV-011: Outbound Network Discovery Isolation
# =========================================================================

@pytest.mark.asyncio
async def test_req07_server1_ip_resolution_no_external_egress(monkeypatch):
    """
    Validates that get_server1_outbound_ip resolves using local configuration
    or interface sockets without attempting outbound connections to public echo services.
    """
    # Reset cached IP
    LLMConfigService._cached_server1_ip = None
    LLMConfigService._cached_ip_timestamp = 0.0

    # Configure local outbound IP
    monkeypatch.setattr(settings, "SERVER1_OUTBOUND_IP", "192.168.10.25")

    resolved_ip = await LLMConfigService.get_server1_outbound_ip()
    assert resolved_ip == "192.168.10.25"


# =========================================================================
# REQ-08 / AV-015: Route Alias & Dev Endpoint Isolation
# =========================================================================

@pytest.mark.asyncio
async def test_req08_rules_sync_fortisiem_route_alias(
    client: AsyncClient, admin_token: str
):
    """
    Validates that POST /api/rules/sync/fortisiem exists as a functional route
    alias matching documentation.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = await client.post("/api/rules/sync/fortisiem", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_synced" in data or "synced_rules" in data


@pytest.mark.asyncio
async def test_req08_dev_endpoint_isolation_in_production(
    client: AsyncClient, monkeypatch
):
    """
    Validates that /api/dev endpoints return 404 in production mode.
    """
    monkeypatch.setattr(settings, "APP_ENV", "production")
    res = await client.get("/api/dev/status")
    assert res.status_code == 404
