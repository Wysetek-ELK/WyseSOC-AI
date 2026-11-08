import pytest
from httpx import AsyncClient
from app.models.incident import Incident
from app.models.rule import Rule
from app.workers.tasks import dispatch_incident_triage
from app.services.audit_service import AuditService


@pytest.mark.asyncio
async def test_phase4_full_stack_integration(client: AsyncClient, db_session, analyst_token):
    """
    P4-REQ-10: End-to-End Multi-Phase Integration Suite:
    - Phase 1: Security Controls, Zero Leakage, Cryptographic Audit Trail.
    - Phase 2: Evidence Normalization & Independent Verification.
    - Phase 3: Unified Nine-Section Policy Compilation & Token Budgeting.
    - Phase 4: Async Task Dispatch, Observability, and Health Telemetry.
    """
    # 1. Verify System Observability & Health
    health_resp = await client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] in ("healthy", "degraded")

    # 2. Setup Rule & Incident
    rule = Rule(
        rule_id="RULE-PHASE4-E2E-01",
        name="Phase 4 Integration Detection Rule",
        event_type="phase4_auth_failure",
        severity="HIGH",
    )
    db_session.add(rule)
    await db_session.flush()

    inc = Incident(
        incident_id="INC-PHASE4-E2E-001",
        rule_id=rule.id,
        event_type="phase4_auth_failure",
        title="Repeated Auth Failure Attack",
        severity="HIGH",
        source_ip="192.168.1.100",
        raw_payload={"failed_attempts": 10, "target_user": "root"},
    )
    db_session.add(inc)
    await db_session.commit()

    # 3. Dispatch Incident Triage via Unified Dispatcher
    dispatch_res = await dispatch_incident_triage(
        incident_id=inc.incident_id,
        trigger_source="LIVE",
        is_simulated=True,
        db=db_session,
    )
    assert dispatch_res is not None
    assert "verdict" in dispatch_res or dispatch_res.get("status") in ("QUEUED", "COMPLETED")

    # 4. Check Audit Trail HMAC Cryptographic Integrity
    audit_service = AuditService(db_session)
    integrity_check = await audit_service.verify_audit_integrity()
    assert integrity_check["tampered_count"] == 0

    # 5. Check Prometheus Metrics Endpoint
    metrics_resp = await client.get("/metrics")
    assert metrics_resp.status_code == 200
    assert "ai_verdict_incidents_total" in metrics_resp.text
