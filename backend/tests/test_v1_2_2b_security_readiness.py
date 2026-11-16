import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, or_, text
from app.main import app
from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.incident import Incident, HistoricalGroundTruth
from app.models.analyst_feedback import AnalystVerdictReview
from app.models.prompt import RulePrompt
from app.models.production_governance import ProductionAutomationPolicy
from app.utils.security import get_password_hash, create_access_token
from app.services.incident_service import IncidentService

ADMIN_ID = "admin-user-001"
ANALYST_A_ID = "analyst-user-002"
ANALYST_B_ID = "analyst-user-b-004"
TENANT_A_ANALYST_ID = "analyst-tenant-a-005"
VIEWER_ID = "viewer-user-003"

HEAVY_TCP_RULE_ID = "40498741-ee6b-4a71-9101-0d6d3f77154c"
HEAVY_TCP_V1_ID = "8a460ab8-5f06-4a90-b2d4-db958199d644"
HEAVY_TCP_V3_ID = "ec0cc351-8dd1-4026-9dc3-586387bb324c"


@pytest_asyncio.fixture(autouse=True)
async def ensure_test_users():
    async with AsyncSessionLocal() as db:
        users_to_ensure = [
            (ADMIN_ID, "admin", "admin@verdictum.test", "Administrator", None),
            (ANALYST_A_ID, "analyst", "analyst@verdictum.test", "SOC Analyst", None),
            (ANALYST_B_ID, "analyst_b", "analyst_b@verdictum.test", "SOC Analyst", None),
            (TENANT_A_ANALYST_ID, "analyst_tenant_a", "analyst_a@tenant-a.test", "SOC Analyst", "TenantA"),
            (VIEWER_ID, "viewer", "viewer@verdictum.test", "Read-Only Viewer", None),
        ]
        for uid, uname, uemail, urole, ucustomer in users_to_ensure:
            res = await db.execute(select(User).where(User.username == uname))
            u = res.scalar_one_or_none()
            if not u:
                u = User(
                    id=uid,
                    username=uname,
                    email=uemail,
                    hashed_password=get_password_hash("AnalystPassword123!"),
                    role=urole,
                    customer=ucustomer,
                    is_active=True,
                )
                db.add(u)
            else:
                u.id = uid
                u.role = urole
                u.customer = ucustomer
                db.add(u)
        await db.commit()


def get_token(username: str, role: str, user_id: str, customer: str = None) -> str:
    payload = {"sub": user_id, "username": username, "role": role}
    if customer:
        payload["customer"] = customer
    return create_access_token(payload)


@pytest.mark.asyncio
async def test_01_canonical_readiness_endpoint_heavy_tcp_v1():
    """Verify canonical route GET /api/prompts/rule/{rule_id}/readiness returns 200 with accurate v1 readiness."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = get_token("admin", "Administrator", ADMIN_ID)
        url = f"/api/prompts/rule/{HEAVY_TCP_RULE_ID}/readiness?version_id={HEAVY_TCP_V1_ID}"
        res = await ac.get(url, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        assert data["readiness_status"] == "BLOCKED"
        assert data["quality_score"] == 54.0
        assert data["quality_gates_passed"] == 2
        assert data["ai_execution_status"] == "Suspended"
        assert data["version_status"] == "APPROVED"
        assert data["approval_eligible"] is False


@pytest.mark.asyncio
async def test_02_canonical_readiness_endpoint_heavy_tcp_v3_candidate():
    """Verify canonical route for candidate version v3 returns 200 with score 77.0 and fail-closed approval."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = get_token("admin", "Administrator", ADMIN_ID)
        url = f"/api/prompts/rule/{HEAVY_TCP_RULE_ID}/readiness?version_id={HEAVY_TCP_V3_ID}"
        res = await ac.get(url, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        assert data["readiness_status"] == "BLOCKED"
        assert data["quality_score"] == 77.0
        assert data["approval_eligible"] is False
        assert data["stages"][0]["status"] == "BLOCKED"  # Stage 1: Detection Semantics
        assert data["stages"][1]["status"] == "BLOCKED"  # Stage 2: Evidence Contract


@pytest.mark.asyncio
async def test_03_canonical_readiness_runtime_offline_status():
    """Verify authoritative status derivation distinguishes enabled automation from offline LLM runtime."""
    async with AsyncSessionLocal() as db:
        p_res = await db.execute(select(RulePrompt).where(RulePrompt.rule_id == HEAVY_TCP_RULE_ID))
        p = p_res.scalar_one_or_none()
        if p:
            p.ai_execution_suspended = False
        pols = (await db.execute(select(ProductionAutomationPolicy).where(
            ProductionAutomationPolicy.rule_id.in_(['PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT', HEAVY_TCP_RULE_ID])
        ))).scalars().all()
        for pol in pols:
            pol.is_enabled = True
        await db.commit()

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            token = get_token("admin", "Administrator", ADMIN_ID)
            url = f"/api/prompts/rule/{HEAVY_TCP_RULE_ID}/readiness?version_id={HEAVY_TCP_V1_ID}"
            res = await ac.get(url, headers={"Authorization": f"Bearer {token}"})
            assert res.status_code == 200
            data = res.json()
            assert data["automation_configured"] is True
            assert data["runtime_availability"] == "Offline"
            assert data["ai_execution_status"] == "Offline"
    finally:
        async with AsyncSessionLocal() as db:
            p_res = await db.execute(select(RulePrompt).where(RulePrompt.rule_id == HEAVY_TCP_RULE_ID))
            p = p_res.scalar_one_or_none()
            if p:
                p.ai_execution_suspended = True
            for pol in pols:
                pol.is_enabled = False
            await db.commit()


@pytest.mark.asyncio
async def test_04_blind_review_db_immutability_byte_for_byte():
    """
    P0 Test: Verify Blind Review masking CANNOT mutate database records.
    Persisted DB row must remain 100% byte-for-byte unchanged before and after masked fetches.
    """
    test_incident_id = "inc-test-immutability-101"
    async with AsyncSessionLocal() as db:
        # 1. Insert an incident with stored AI verdict and ground truth
        existing = (await db.execute(select(Incident).where(Incident.incident_id == test_incident_id))).scalar_one_or_none()
        if not existing:
            existing = Incident(
                incident_id=test_incident_id,
                event_type="TEST_IMMUTABILITY",
                title="Immutability Verification Alert",
                severity="HIGH",
                customer="DEFAULT",
                ai_verdict={
                    "verdict": "TRUE_POSITIVE",
                    "confidence": 98.5,
                    "reason": "Cryptographically verified malicious command execution pattern.",
                    "model_identifier": "simulated-test",
                }
            )
            db.add(existing)
            await db.flush()
            gt = HistoricalGroundTruth(
                incident_id=existing.id,
                resolution="True Positive",
                cleared_reason="Attacker activity confirmed by L3 forensic team",
            )
            db.add(gt)
            await db.commit()

        # 2. Record persisted DB row directly from raw SQL
        row_before = (await db.execute(text("SELECT ai_verdict, customer, title FROM incidents WHERE incident_id = :id"), {"id": test_incident_id})).fetchone()
        stored_verdict_before = row_before[0]

    # 3. Authenticate as unsubmitted reviewer and fetch masked incident
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = get_token("analyst_b", "SOC Analyst", ANALYST_B_ID)
        # Call both list and detail endpoints with ?blind_review=false attempt
        list_res = await ac.get(f"/api/incidents?search={test_incident_id}&blind_review=false", headers={"Authorization": f"Bearer {token}"})
        assert list_res.status_code == 200
        assert list_res.json()["items"][0]["ai_verdict"] is None
        assert list_res.json()["items"][0]["historical_resolution"] == "[Hidden - Blind Review]"

        detail_res = await ac.get(f"/api/incidents/{test_incident_id}?blind_review=false", headers={"Authorization": f"Bearer {token}"})
        assert detail_res.status_code == 200
        assert detail_res.json()["ai_verdict"] is None
        assert detail_res.json()["ground_truth"] is None

    # 4. Open a fresh database session, trigger commit, and reload incident from disk
    async with AsyncSessionLocal() as fresh_db:
        await fresh_db.commit()  # Ensure no pending dirty state
        row_after = (await fresh_db.execute(text("SELECT ai_verdict, customer, title FROM incidents WHERE incident_id = :id"), {"id": test_incident_id})).fetchone()
        stored_verdict_after = row_after[0]

        # 5. Assert byte-for-byte immutability
        assert stored_verdict_before == stored_verdict_after, "FATAL: Database record was mutated by masked GET request!"
        assert "TRUE_POSITIVE" in stored_verdict_after
        assert "Cryptographically verified" in stored_verdict_after


@pytest.mark.asyncio
async def test_05_cross_tenant_access_denial():
    """
    P1 Test: Verify Tenant A analyst cannot retrieve Tenant B incident, timeline, or submit reviews.
    """
    tenant_b_inc_id = "inc-tenant-b-isolated-202"
    async with AsyncSessionLocal() as db:
        inc_b = (await db.execute(select(Incident).where(Incident.incident_id == tenant_b_inc_id))).scalar_one_or_none()
        if not inc_b:
            inc_b = Incident(
                incident_id=tenant_b_inc_id,
                event_type="TENANT_B_ISOLATED_EVENT",
                title="Tenant B Sensitive Incident",
                severity="CRITICAL",
                customer="TenantB",
                ai_verdict={"verdict": "FALSE_POSITIVE", "reason": "Internal Tenant B test system"}
            )
            db.add(inc_b)
            await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Authenticate analyst belonging to TenantA
        token_a = get_token("analyst_tenant_a", "SOC Analyst", TENANT_A_ANALYST_ID, customer="TenantA")

        # 1. Detail endpoint -> 403 Forbidden
        det_res = await ac.get(f"/api/incidents/{tenant_b_inc_id}", headers={"Authorization": f"Bearer {token_a}"})
        assert det_res.status_code == 403, f"Expected 403, got {det_res.status_code}: {det_res.text}"
        assert "Access denied" in det_res.json()["detail"]

        # 2. Timeline endpoint -> 403 Forbidden
        tl_res = await ac.get(f"/api/incidents/{tenant_b_inc_id}/timeline", headers={"Authorization": f"Bearer {token_a}"})
        assert tl_res.status_code == 403, f"Expected 403, got {tl_res.status_code}: {tl_res.text}"
        assert "Access denied" in tl_res.json()["detail"]

        # 3. Review submission -> 403 Forbidden
        rev_res = await ac.post(
            f"/api/reviews/{tenant_b_inc_id}/submit",
            json={"analyst_verdict": "TRUE_POSITIVE", "analyst_notes": "Attempted cross-tenant review"},
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert rev_res.status_code == 403, f"Expected 403, got {rev_res.status_code}: {rev_res.text}"

        # 4. Actual prompt export -> 403 Forbidden
        exp_res = await ac.get(
            f"/api/prompts/actual-prompt/incident/{tenant_b_inc_id}/export",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert exp_res.status_code == 403, f"Expected 403, got {exp_res.status_code}: {exp_res.text}"

        # 5. Incident list -> excludes Tenant B incident
        list_res = await ac.get(f"/api/incidents?search={tenant_b_inc_id}", headers={"Authorization": f"Bearer {token_a}"})
        assert list_res.status_code == 200
        assert len(list_res.json()["items"]) == 0


@pytest.mark.asyncio
async def test_06_alternate_endpoint_and_export_redaction():
    """
    P1 Test: Verify alternate endpoints and actual-prompt export redact protected AI determinations.
    """
    target_inc_id = "132438483"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token_unreviewed = get_token("analyst_b", "SOC Analyst", ANALYST_B_ID)

        # 1. Investigation Queue -> AI validated verdict & trust score sanitized to None
        q_res = await ac.get("/api/investigations/queue?page=1&page_size=20", headers={"Authorization": f"Bearer {token_unreviewed}"})
        assert q_res.status_code == 200
        items = q_res.json()["items"]
        unreviewed_target = next((i for i in items if i["incident_id"] == target_inc_id), None)
        if unreviewed_target:
            assert unreviewed_target["ai_validated_verdict"] is None
            assert unreviewed_target["ai_trust_score"] is None

        # 2. Incident Timeline -> Milestone 6 masked as [Hidden - Blind Review]
        tl_res = await ac.get(f"/api/incidents/{target_inc_id}/timeline", headers={"Authorization": f"Bearer {token_unreviewed}"})
        assert tl_res.status_code == 200
        m_triage = next((m for m in tl_res.json()["milestones"] if m["type"] == "AGENT_EVALUATED"), None)
        assert m_triage is not None
        assert "[Hidden - Blind Review]" in m_triage["title"]

        # 3. Actual Prompt Export -> raw_model_response is masked and is_redacted is True
        exp_res = await ac.get(f"/api/prompts/actual-prompt/incident/{target_inc_id}/export?format=json", headers={"Authorization": f"Bearer {token_unreviewed}"})
        assert exp_res.status_code == 200
        exp_data = exp_res.json()
        assert exp_data["is_redacted"] is True
        assert exp_data["raw_model_response"] == "[Hidden - Blind Review]"
        if exp_data.get("l1_explanation"):
            assert exp_data["l1_explanation"]["verdict_returned"] == "[Hidden - Blind Review]"

        # 4. Direct On-Demand Inference Invocation -> Blocked with HTTP 403 Forbidden
        direct_post = await ac.post(f"/api/incidents/{target_inc_id}/ai-verdict", headers={"Authorization": f"Bearer {token_unreviewed}"})
        assert direct_post.status_code == 403, f"Expected 403, got {direct_post.status_code}"
        assert "Cannot invoke direct on-demand AI verdict for an unreviewed incident" in direct_post.json()["detail"]
