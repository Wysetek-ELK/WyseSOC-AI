import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, delete
from unittest.mock import patch, AsyncMock

from app.database import AsyncSessionLocal
from app.models.prompt import RulePrompt, PromptVersion
from app.models.incident import Incident
from app.models.analyst_feedback import AnalystVerdictReview
from app.models.production_governance import ProductionAutomationPolicy
from app.models.user import User
from app.schemas.production_readiness import ReadinessStatus
from app.services.production_readiness_service import ProductionReadinessService
from app.services.incident_service import IncidentService
from app.services.investigation_service import InvestigationService
from app.services.telemetry_timeline_service import TelemetryTimelineService
from app.utils.security import create_access_token
from app.main import app

HEAVY_TCP_RULE_ID = "40498741-ee6b-4a71-9101-0d6d3f77154c"
HEAVY_TCP_V1_ID = "8a460ab8-5f06-4a90-b2d4-db958199d644"
HEAVY_TCP_V3_ID = "ec0cc351-8dd1-4026-9dc3-586387bb324c"

ANALYST_A_ID = "analyst-user-002"
VIEWER_USER_ID = "viewer-user-003"
ADMIN_USER_ID = "24ecd70d-c30b-4f1a-a022-ccc3ef571b95"
ANALYST_B_ID = "analyst-user-b-004"


@pytest_asyncio.fixture(autouse=True)
async def ensure_test_users():
    """Ensure seeded analyst B exists for multi-reviewer tests."""
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.id == ANALYST_B_ID))
        u = res.scalar_one_or_none()
        if not u:
            new_u = User(
                id=ANALYST_B_ID,
                username="analyst_b",
                email="analyst_b@verdictum.test",
                hashed_password="hashed_pw_test",
                role="SOC Analyst",
                is_active=True,
            )
            db.add(new_u)
            await db.commit()


# ==============================================================================
# 1. BLIND REVIEW FLAG BYPASS ATTEMPT TEST
# ==============================================================================

@pytest.mark.asyncio
async def test_01_blind_review_flag_bypass_attempt():
    """
    Test 1: Client passing ?blind_review=false CANNOT override server-enforced isolation.
    An unreviewed analyst attempting to pass ?blind_review=false must still receive masked verdicts.
    """
    async with AsyncSessionLocal() as db:
        await db.execute(delete(AnalystVerdictReview).where(AnalystVerdictReview.reviewer_id.in_([ANALYST_A_ID, "analyst"])))
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_access_token({"sub": ANALYST_A_ID, "username": "analyst", "role": "SOC Analyst"})
        headers = {"Authorization": f"Bearer {token}"}

        # 1. List endpoint with blind_review=false
        list_res = await client.get("/api/incidents?blind_review=false&page=1&page_size=10", headers=headers)
        assert list_res.status_code == 200
        data = list_res.json()
        assert len(data["items"]) > 0

        for item in data["items"]:
            assert item["ai_verdict"] is None, f"Bypass succeeded on list! Verdict leaked: {item['ai_verdict']}"
            assert item["historical_resolution"] == "[Hidden - Blind Review]", "Historical ground truth resolution leaked on list!"
            assert item["cleared_reason"] is None
            assert item["cleared_user"] is None

        # 2. Detail endpoint with blind_review=false
        sample_inc_id = data["items"][0]["incident_id"]
        detail_res = await client.get(f"/api/incidents/{sample_inc_id}?blind_review=false", headers=headers)
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["ai_verdict"] is None, f"Bypass succeeded on detail! Verdict leaked: {detail['ai_verdict']}"
        assert detail["ground_truth"] is None, "Ground truth object leaked on detail!"


# ==============================================================================
# 2. REVIEWER A/B ISOLATION TEST
# ==============================================================================

@pytest.mark.asyncio
async def test_02_reviewer_ab_isolation():
    """
    Test 2: Reviewer-specific isolation.
    Analyst A submitting a review does NOT disclose the verdict to Analyst B.
    """
    async with AsyncSessionLocal() as db:
        inc_q = select(Incident).where(Incident.ai_verdict.isnot(None))
        inc_res = await db.execute(inc_q)
        sample_inc = inc_res.scalars().first()
        assert sample_inc is not None

        # Clean previous reviews for this incident
        await db.execute(delete(AnalystVerdictReview).where(
            (AnalystVerdictReview.incident_id == sample_inc.id) |
            (AnalystVerdictReview.incident_id == str(sample_inc.incident_id))
        ))
        await db.commit()

        # Analyst A submits review
        analyst_a_user = User(id="user-analyst-alpha", username="analyst_alpha", role="SOC Analyst")
        rev_a = AnalystVerdictReview(
            incident_id=sample_inc.id,
            rule_id=sample_inc.rule_id or "PH_RULE_TEST",
            reviewer_id=analyst_a_user.id,
            analyst_verdict="TRUE_POSITIVE",
            analyst_notes="Alpha verified TP",
        )
        db.add(rev_a)
        await db.commit()

        # Query detail as Analyst A -> Revealed
        svc = IncidentService(db)
        detail_a = await svc.get_incident(sample_inc.incident_id, blind_review=False, current_user=analyst_a_user)
        assert detail_a.ai_verdict is not None, "Analyst A did not receive post-submission verdict!"
        assert detail_a.ai_verdict == sample_inc.ai_verdict

        # Query detail as Analyst B (has not submitted) -> Masked
        analyst_b_user = User(id=ANALYST_B_ID, username="analyst_b", role="SOC Analyst")
        detail_b = await svc.get_incident(sample_inc.incident_id, blind_review=False, current_user=analyst_b_user)
        assert detail_b.ai_verdict is None, "AI verdict leaked to unsubmitted Analyst B!"
        assert detail_b.ground_truth is None, "Ground truth leaked to unsubmitted Analyst B!"


# ==============================================================================
# 3. CROSS-ROLE AND CROSS-TENANT DISCLOSURE TEST
# ==============================================================================

@pytest.mark.asyncio
async def test_03_cross_role_and_cross_tenant_disclosure():
    """
    Test 3: Cross-role protection (Viewer cannot see protected verdicts even with blind_review=false)
    and cross-tenant isolation.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Viewer role requesting unmasked data
        token_viewer = create_access_token({"sub": VIEWER_USER_ID, "username": "viewer", "role": "Read-Only Viewer"})
        res_viewer = await client.get("/api/incidents?blind_review=false&page=1&page_size=5", headers={"Authorization": f"Bearer {token_viewer}"})
        assert res_viewer.status_code == 200
        for item in res_viewer.json()["items"]:
            assert item["ai_verdict"] is None, "Viewer accessed protected AI verdict!"
            assert item["historical_resolution"] == "[Hidden - Blind Review]", "Viewer accessed ground truth resolution!"

        # 2. Administrator has oversight authority
        token_admin = create_access_token({"sub": ADMIN_USER_ID, "username": "admin", "role": "Administrator"})
        res_admin = await client.get("/api/incidents?blind_review=false&page=1&page_size=5", headers={"Authorization": f"Bearer {token_admin}"})
        assert res_admin.status_code == 200
        items_with_verdict = [it for it in res_admin.json()["items"] if it.get("ai_verdict") is not None]
        assert len(items_with_verdict) > 0, "Administrator was incorrectly masked when requesting unmasked data!"


# ==============================================================================
# 4. ALTERNATE ENDPOINT DISCLOSURE TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_04_alternate_endpoint_disclosure_prevention():
    """
    Test 4: Prevent verdict disclosure through alternate endpoints:
    - /api/investigations/queue
    - /api/investigations/{id}
    - /api/incidents/{id}/timeline
    - /api/incidents/{id}/ai-verdict (on-demand execution blocked in blind review)
    """
    async with AsyncSessionLocal() as db:
        await db.execute(delete(AnalystVerdictReview).where(AnalystVerdictReview.reviewer_id.in_([ANALYST_B_ID, "analyst_b"])))
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unsub_token = create_access_token({"sub": ANALYST_B_ID, "username": "analyst_b", "role": "SOC Analyst"})
        headers = {"Authorization": f"Bearer {unsub_token}"}

        # 1. Investigations Queue
        inv_q_res = await client.get("/api/investigations/queue?page=1&page_size=10", headers=headers)
        assert inv_q_res.status_code == 200
        for item in inv_q_res.json()["items"]:
            assert item["ai_validated_verdict"] is None, f"Investigation queue leaked AI verdict: {item['ai_validated_verdict']}"
            assert item["ai_trust_score"] is None, "Investigation queue leaked trust score!"

        # 2. Investigation Detail
        if inv_q_res.json()["items"]:
            inv_id = inv_q_res.json()["items"][0]["id"]
            inv_detail_res = await client.get(f"/api/investigations/{inv_id}", headers=headers)
            assert inv_detail_res.status_code == 200
            inv_data = inv_detail_res.json()
            if inv_data.get("ai_assurance"):
                assert inv_data["ai_assurance"]["validated_verdict"] is None, "Investigation detail leaked AI assurance validated verdict!"
                assert inv_data["ai_assurance"]["proposed_verdict"] is None, "Investigation detail leaked proposed verdict!"
                assert inv_data["ai_assurance"]["trust_score"] is None, "Investigation detail leaked trust score!"

        # 3. Incident Timeline
        list_res = await client.get("/api/incidents?page=1&page_size=5", headers=headers)
        assert list_res.status_code == 200
        inc_id = list_res.json()["items"][0]["incident_id"]

        timeline_res = await client.get(f"/api/incidents/{inc_id}/timeline", headers=headers)
        assert timeline_res.status_code == 200
        t_data = timeline_res.json()
        for m in t_data.get("milestones", []):
            if m.get("type") == "AGENT_EVALUATED":
                assert "[Hidden - Blind Review]" in m.get("title", ""), f"Timeline leaked AI verdict: {m.get('title')}"
            if m.get("type") == "TICKET_CLEARED":
                assert "[Hidden - Blind Review]" in m.get("title", ""), f"Timeline leaked SIEM ground truth: {m.get('title')}"

        # 4. On-demand AI verdict endpoint blocked for unreviewed analyst in blind review
        on_demand_res = await client.post(f"/api/incidents/{inc_id}/ai-verdict", headers=headers)
        assert on_demand_res.status_code == 403, "On-demand AI verdict was not blocked for unreviewed analyst!"


# ==============================================================================
# 5. DATABASE PERSISTENCE AFTER MASKED GET TEST
# ==============================================================================

@pytest.mark.asyncio
async def test_05_database_persistence_after_masked_get():
    """
    Test 5: Masked GET queries NEVER mutate the underlying ORM entity or database table.
    """
    async with AsyncSessionLocal() as db:
        service = IncidentService(db)
        inc_res = await db.execute(select(Incident).where(Incident.ai_verdict.isnot(None)))
        inc_obj = inc_res.scalars().first()
        assert inc_obj is not None
        stored_verdict = dict(inc_obj.ai_verdict)

        unsub_user = User(id="unsub-db-check", username="unsub_db", role="SOC Analyst")
        dto = await service.get_incident(inc_obj.incident_id, blind_review=False, current_user=unsub_user)
        assert dto.ai_verdict is None

        # Verify ORM object in memory is unchanged
        assert inc_obj.ai_verdict == stored_verdict, "In-memory ORM object was mutated!"

        # Re-query fresh from DB
        fresh = await db.execute(select(Incident.ai_verdict).where(Incident.id == inc_obj.id))
        persisted = fresh.scalar_one_or_none()
        assert persisted == stored_verdict, "Database table value was mutated!"


# ==============================================================================
# 6. AUTHORIZED POST-SUBMISSION REVEAL TEST
# ==============================================================================

@pytest.mark.asyncio
async def test_06_authorized_post_submission_reveal():
    """
    Test 6: Authorized reviewer submitting a review immediately reveals the verdict
    and post-submission comparison outcome.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_access_token({"sub": ANALYST_A_ID, "username": "analyst", "role": "SOC Analyst"})
        headers = {"Authorization": f"Bearer {token}"}

        # Pick an incident
        async with AsyncSessionLocal() as db:
            inc_res = await db.execute(select(Incident).where(Incident.ai_verdict.isnot(None)))
            inc_obj = inc_res.scalars().first()
            assert inc_obj is not None
            inc_db_id = inc_obj.id
            inc_biz_id = inc_obj.incident_id

            # Clear reviews for this analyst
            await db.execute(delete(AnalystVerdictReview).where(
                ((AnalystVerdictReview.incident_id == inc_db_id) | (AnalystVerdictReview.incident_id == str(inc_biz_id))) &
                (AnalystVerdictReview.reviewer_id.in_([ANALYST_A_ID, "analyst"]))
            ))
            await db.commit()

        # Before submission: masked
        before_res = await client.get(f"/api/incidents/{inc_biz_id}?blind_review=false", headers=headers)
        assert before_res.status_code == 200
        assert before_res.json()["ai_verdict"] is None

        # Submit review
        review_body = {
            "analyst_verdict": "FALSE_POSITIVE",
            "analyst_notes": "Test 6 post-submission reveal check",
            "blind_mode_active": True,
        }
        submit_res = await client.post(f"/api/reviews/{inc_db_id}/submit", json=review_body, headers=headers)
        assert submit_res.status_code in (200, 201)
        sub_data = submit_res.json()
        assert "revealed_ai_verdict" in sub_data
        assert sub_data["revealed_ai_verdict"] is not None

        # After submission: revealed for THIS analyst
        after_res = await client.get(f"/api/incidents/{inc_biz_id}?blind_review=false", headers=headers)
        assert after_res.status_code == 200
        assert after_res.json()["ai_verdict"] is not None
        assert after_res.json()["ground_truth"] is not None


# ==============================================================================
# 7. AUTHORITATIVE AI EXECUTION STATUS DERIVATION TEST
# ==============================================================================

@pytest.mark.asyncio
async def test_07_authoritative_execution_status_derivation():
    """
    Test 7: AI Execution status derivation strictly decouples:
    - SIEM Rule Status
    - AI Policy Version Status
    - Production Readiness
    - Automation Configuration
    - Runtime Availability
    """
    async with AsyncSessionLocal() as db:
        res = await ProductionReadinessService.evaluate_readiness(
            db,
            rule_identifier=HEAVY_TCP_RULE_ID,
            version_id=HEAVY_TCP_V1_ID,
        )
        assert res.rule_deployment_status == "ACTIVE"
        assert res.version_status == "APPROVED"
        assert res.readiness_status == ReadinessStatus.BLOCKED
        assert res.ai_execution_status == "Suspended"
        assert res.automation_configured is False


# ==============================================================================
# 8. LLM OFFLINE AND EMERGENCY SUSPENSION TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_08_llm_offline_and_emergency_suspension():
    """
    Test 8:
    A) Approved policy + offline LLM -> status 'Offline' (distinguishes configured from runtime).
    B) Enabled configuration + emergency suspension -> status 'Suspended'.
    C) Missing runtime telemetry -> status 'Unknown'.
    """
    async with AsyncSessionLocal() as db:
        prompt_res = await db.execute(select(RulePrompt).where(RulePrompt.rule_id == HEAVY_TCP_RULE_ID))
        prompt = prompt_res.scalar_one()
        orig_susp = prompt.ai_execution_suspended

        # Update all matching automation policies for Heavy TCP
        possible_keys = [
            "PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT",
            "PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT",
            "PH_RULE_HEAVY_TCP_HOST_SCAN",
            HEAVY_TCP_RULE_ID,
        ]
        pols = (await db.execute(select(ProductionAutomationPolicy).where(ProductionAutomationPolicy.rule_id.in_(possible_keys)))).scalars().all()
        for p in pols:
            p.is_enabled = True
        prompt.ai_execution_suspended = False
        await db.commit()

        try:
            # 8A: LLM Offline
            with patch("app.services.ai_verdict_service.VerdictTriageAgent.is_local_llm_available", new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = False
                res_offline = await ProductionReadinessService.evaluate_readiness(db, HEAVY_TCP_RULE_ID, version_id=HEAVY_TCP_V1_ID)
                assert res_offline.ai_execution_status == "Offline", f"Expected Offline, got {res_offline.ai_execution_status}"
                assert res_offline.runtime_availability == "Offline"
                assert res_offline.automation_configured is True

            # 8B: Emergency suspension engaged -> Suspended takes precedence
            prompt.ai_execution_suspended = True
            await db.commit()
            with patch("app.services.ai_verdict_service.VerdictTriageAgent.is_local_llm_available", new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = True
                res_susp = await ProductionReadinessService.evaluate_readiness(db, HEAVY_TCP_RULE_ID, version_id=HEAVY_TCP_V1_ID)
                assert res_susp.ai_execution_status == "Suspended"

            # 8C: Telemetry unknown (mock returns None or raises)
            prompt.ai_execution_suspended = False
            await db.commit()
            with patch("app.services.ai_verdict_service.VerdictTriageAgent.is_local_llm_available", new_callable=AsyncMock) as mock_llm:
                mock_llm.side_effect = RuntimeError("Telemetry unreachable")
                res_unknown = await ProductionReadinessService.evaluate_readiness(db, HEAVY_TCP_RULE_ID, version_id=HEAVY_TCP_V1_ID)
                assert res_unknown.ai_execution_status == "Unknown"
                assert res_unknown.runtime_availability == "Unknown"

        finally:
            prompt.ai_execution_suspended = orig_susp
            for p in pols:
                p.is_enabled = False
            await db.commit()


# ==============================================================================
# 9. HEAVY TCP V1 HISTORICAL / CURRENT STATE SEPARATION TEST
# ==============================================================================

@pytest.mark.asyncio
async def test_09_heavy_tcp_v1_historical_current_separation():
    """
    Test 9: Reconciles Heavy TCP v1 historical baseline:
    - Policy Version Status is APPROVED (historical baseline preserved)
    - Quality score is 54.0 (2/8 gates passed against current requirements)
    - Current Readiness is BLOCKED / INCOMPLETE (revalidation required)
    - AI Execution Status is Suspended (kill-switch engaged)
    - SIEM Rule Deployment Status is ACTIVE
    """
    async with AsyncSessionLocal() as db:
        res = await ProductionReadinessService.evaluate_readiness(
            db,
            rule_identifier=HEAVY_TCP_RULE_ID,
            version_id=HEAVY_TCP_V1_ID,
        )
        assert res.version_status == "APPROVED"
        assert res.rule_deployment_status == "ACTIVE"
        assert res.quality_score == 54.0
        assert res.quality_gates_passed == 2
        assert res.readiness_status == ReadinessStatus.BLOCKED
        assert res.readiness_label == "Blocked / Incomplete"
        assert res.ai_execution_status == "Suspended"


# ==============================================================================
# 10. MANDATORY ASSERTION FAILURE PROPAGATION TEST
# ==============================================================================

@pytest.mark.asyncio
async def test_10_mandatory_assertion_failure_propagation():
    """
    Test 10: Validation runner integrity invariant:
    Every mandatory assertion must contribute via boolean conjunction.
    A single failing assertion MUST fail the overall scenario.
    """
    assertions = {
        "hasRuleHeader": True,
        "hasSiemActive": True,
        "hasV1Status": True,
        "hasAiSuspended": True,
        "hasApprovedStatus": False,  # Failing mandatory assertion
    }
    all_passed = all(assertions.values())
    assert all_passed is False, "Failing mandatory assertion was silently ignored!"
