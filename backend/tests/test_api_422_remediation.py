import pytest
import uuid
import pytest_asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from sqlalchemy import select
from httpx import AsyncClient, ASGITransport

from app.database import Base, get_db
from app.main import app
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.rule import Rule
from app.models.incident import Incident
from app.models.investigation import Investigation
from app.models.learning import LearningRecord
from app.models.rule_learning import RuleLearningProfile
from app.models.analyst_feedback import AnalystVerdictReview
from app.models.production_governance import RulePromotionRequest
from app.services.rule_learning_service import RuleLearningService


# Mock users for testing
MOCK_ANALYST = User(
    id="user-analyst-1",
    username="soc_analyst_test",
    email="analyst@wyse.local",
    role="SOC Analyst",
    is_active=True
)

MOCK_TENANT_A_USER = User(
    id="user-tenant-a",
    username="tenant_a_analyst",
    email="userA@tenantA.local",
    role="SOC Analyst",
    is_active=True
)
# Attach customer attribute for tenant scoping
setattr(MOCK_TENANT_A_USER, "customer", "CUSTOMER_ALPHA")

MOCK_MANAGER = User(
    id="user-manager-1",
    username="soc_manager_test",
    email="manager@wyse.local",
    role="SOC_Manager",
    is_active=True
)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Isolated, in-memory SQLite database session."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provides an authenticated httpx AsyncClient tied to the test database session."""
    async def override_get_db():
        yield db_session

    async def override_get_user():
        return MOCK_ANALYST

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_get_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_submit_review_true_positive(db_session: AsyncSession, async_client: AsyncClient):
    """
    Test 1: Submit independent True Positive review.
    Verifies that double-blind AI verdict is revealed post-submission,
    verified_tp_count is incremented, and empirical accuracy is recalibrated.
    """
    rule_id = "PH_RULE_TEST_PORT_SCAN"
    # Seed incident with stored AI verdict proposing TRUE_POSITIVE
    incident = Incident(
        id=str(uuid.uuid4()),
        incident_id=101,
        title="Suspicious Inbound Port Scan",
        rule_id=rule_id,
        event_type=rule_id,
        severity="HIGH",
        customer="DEFAULT",
        source_ip="198.51.100.5",
        reporting_device="firewall-01",
        ai_verdict={
            "verdict": "TRUE_POSITIVE",
            "confidence": 0.94,
            "reasoning": "Observed rapid sequential connection attempts across 100 ports."
        }
    )
    db_session.add(incident)
    await db_session.commit()

    # Submit analyst review with alias format 'TP'
    response = await async_client.post(
        f"/api/reviews/{incident.incident_id}/submit",
        json={
            "analyst_verdict": "TP",
            "analyst_notes": "Confirmed malicious port sweep by analyst.",
            "evidence_references": ["ev-conn-101", "ev-conn-102"],
            "blind_mode_active": True
        }
    )

    assert response.status_code == 200, f"Submit failed: {response.text}"
    body = response.json()
    assert body["analyst_verdict"] == "TRUE_POSITIVE"
    assert body["revealed_ai_verdict"] == "TRUE_POSITIVE"
    assert body["comparison_outcome"] == "AGREEMENT_TP"
    assert body["ground_truth_status"] == "VERIFIED"

    # Verify RuleLearningProfile metrics
    profile = await RuleLearningService.get_profile(db_session, rule_id=rule_id, customer="DEFAULT")
    assert profile is not None
    assert profile.total_analyst_reviews == 1
    assert profile.verified_tp_count == 1
    assert profile.verified_fp_count == 0
    assert profile.ai_correct_count == 1
    assert profile.empirical_accuracy == 1.0


@pytest.mark.asyncio
async def test_submit_review_false_positive(db_session: AsyncSession, async_client: AsyncClient):
    """
    Test 2: Submit independent False Positive review.
    Verifies that overturning AI True Positive records AI_FALSE_ALARM,
    increments verified_fp_count, and flags AI incorrect.
    """
    rule_id = "PH_RULE_TEST_BRUTE_FORCE"
    incident = Incident(
        id=str(uuid.uuid4()),
        incident_id=102,
        title="Possible SSH Brute Force",
        rule_id=rule_id,
        event_type=rule_id,
        severity="MEDIUM",
        customer="DEFAULT",
        source_ip="192.168.1.50",
        reporting_device="bastion-01",
        ai_verdict={
            "verdict": "TRUE_POSITIVE",
            "confidence": 0.88,
            "reasoning": "Repeated SSH auth failures."
        }
    )
    db_session.add(incident)
    await db_session.commit()

    response = await async_client.post(
        f"/api/reviews/{incident.id}/submit",
        json={
            "analyst_verdict": "FALSE_POSITIVE",
            "analyst_notes": "Scheduled vulnerability scanner authenticated test run.",
            "evidence_references": "ev-qualys-scan-1, ev-cron-run",  # Pass as comma-delimited string
            "blind_mode_active": True
        }
    )

    assert response.status_code == 200, f"Submit failed: {response.text}"
    body = response.json()
    assert body["analyst_verdict"] == "FALSE_POSITIVE"
    assert body["revealed_ai_verdict"] == "TRUE_POSITIVE"
    assert body["comparison_outcome"] == "AI_FALSE_ALARM"
    assert body["ground_truth_status"] == "VERIFIED"

    profile = await RuleLearningService.get_profile(db_session, rule_id=rule_id, customer="DEFAULT")
    assert profile is not None
    assert profile.total_analyst_reviews == 1
    assert profile.verified_fp_count == 1
    assert profile.verified_tp_count == 0
    assert profile.ai_incorrect_count == 1


@pytest.mark.asyncio
async def test_submit_review_insufficient_evidence_safeguard(db_session: AsyncSession, async_client: AsyncClient):
    """
    Test 3: Submit 'Insufficient Evidence' review.
    CRITICAL SAFETY REQUIREMENT: Submitting 'Insufficient Evidence' must NEVER
    create false verified TP or FP ground truth!
    """
    rule_id = "PH_RULE_TEST_ANOMALY"
    incident = Incident(
        id=str(uuid.uuid4()),
        incident_id=103,
        title="Unusual Outbound UDP Packet",
        rule_id=rule_id,
        event_type=rule_id,
        severity="LOW",
        customer="DEFAULT",
        source_ip="10.0.0.42",
        reporting_device="core-sw-01",
        ai_verdict={
            "verdict": "REQUIRES_ATTENTION",
            "confidence": 0.40,
            "reasoning": "Payload truncated; inconclusive."
        }
    )
    db_session.add(incident)
    await db_session.commit()

    response = await async_client.post(
        f"/api/reviews/{incident.id}/submit",
        json={
            "analyst_verdict": "Insufficient Evidence",
            "analyst_notes": "Packet capture missing payload bytes; cannot verify malicious intent.",
            "blind_mode_active": True
        }
    )

    assert response.status_code == 200, f"Submit failed: {response.text}"
    body = response.json()
    assert body["analyst_verdict"] == "INSUFFICIENT_EVIDENCE"
    assert body["ground_truth_status"] == "INSUFFICIENT_EVIDENCE"
    assert body["comparison_outcome"] == "ANALYST_INSUFFICIENT_EVIDENCE"

    profile = await RuleLearningService.get_profile(db_session, rule_id=rule_id, customer="DEFAULT")
    assert profile is not None
    # Crucial assertion: TP and FP counts must remain ZERO
    assert profile.verified_tp_count == 0
    assert profile.verified_fp_count == 0
    assert profile.abstention_count == 1
    assert profile.total_analyst_reviews == 1


@pytest.mark.asyncio
async def test_double_blind_isolation(db_session: AsyncSession, async_client: AsyncClient):
    """
    Test 4: Double-blind review queue isolation.
    Pending reviews queue must NEVER expose AI verdict or rationale to the analyst.
    """
    incident = Incident(
        id=str(uuid.uuid4()),
        incident_id=104,
        title="Blinded Audit Incident",
        rule_id="PH_RULE_BLIND_TEST",
        event_type="PH_RULE_BLIND_TEST",
        severity="HIGH",
        customer="DEFAULT",
        ai_verdict={
            "verdict": "TRUE_POSITIVE",
            "confidence": 0.99,
            "reasoning": "Secret AI analysis that must remain hidden."
        }
    )
    db_session.add(incident)
    await db_session.commit()

    response = await async_client.get("/api/reviews/pending")
    assert response.status_code == 200
    items = response.json().get("items", [])
    matching = [i for i in items if i["incident_id"] == 104]
    assert len(matching) == 1
    # Ensure AI verdict is not exposed in the pending queue
    assert "ai_verdict" not in matching[0]
    assert "revealed_ai_verdict" not in matching[0]
    assert matching[0]["is_blind_mode"] is True


@pytest.mark.asyncio
async def test_metric_update_exact_once_guarantee(db_session: AsyncSession, async_client: AsyncClient):
    """
    Test 5: Metric update idempotency and update semantics.
    Duplicate submissions must not inflate metrics; corrections must adjust counts accurately.
    """
    rule_id = "PH_RULE_EXACT_ONCE"
    incident = Incident(
        id=str(uuid.uuid4()),
        incident_id=105,
        title="Idempotency Test Incident",
        rule_id=rule_id,
        event_type=rule_id,
        severity="MEDIUM",
        customer="DEFAULT",
        ai_verdict={"verdict": "FALSE_POSITIVE", "confidence": 0.90}
    )
    db_session.add(incident)
    await db_session.commit()

    # 1. First submission: FP
    res1 = await async_client.post(
        f"/api/reviews/{incident.id}/submit",
        json={"analyst_verdict": "FALSE_POSITIVE", "analyst_notes": "Benign"}
    )
    assert res1.status_code == 200

    profile = await RuleLearningService.get_profile(db_session, rule_id=rule_id)
    assert profile.total_analyst_reviews == 1
    assert profile.verified_fp_count == 1
    assert profile.verified_tp_count == 0

    # 2. Duplicate submission (same verdict)
    res2 = await async_client.post(
        f"/api/reviews/{incident.id}/submit",
        json={"analyst_verdict": "FALSE_POSITIVE", "analyst_notes": "Benign duplicate"}
    )
    assert res2.status_code == 200
    assert res2.json().get("is_duplicate") is True

    # Total count must NOT be 2!
    await db_session.refresh(profile)
    assert profile.total_analyst_reviews == 1
    assert profile.verified_fp_count == 1

    # 3. Updated verdict: correction to True Positive
    res3 = await async_client.post(
        f"/api/reviews/{incident.id}/submit",
        json={"analyst_verdict": "TRUE_POSITIVE", "analyst_notes": "Overturning previous assessment to TP"}
    )
    assert res3.status_code == 200
    assert res3.json().get("is_updated") is True

    await db_session.refresh(profile)
    # Total reviews stays 1, verified_fp decreases to 0, verified_tp becomes 1
    assert profile.total_analyst_reviews == 1
    assert profile.verified_fp_count == 0
    assert profile.verified_tp_count == 1


@pytest.mark.asyncio
async def test_cross_tenant_review_isolation(db_session: AsyncSession):
    """
    Test 6: Cross-tenant review authorization rejection.
    An analyst restricted to Customer Alpha cannot review Customer Beta's incident (HTTP 403).
    """
    incident = Incident(
        id=str(uuid.uuid4()),
        incident_id=106,
        title="Tenant Beta Restricted Incident",
        rule_id="PH_RULE_TENANT_TEST",
        event_type="PH_RULE_TENANT_TEST",
        severity="HIGH",
        customer="CUSTOMER_BETA",
        ai_verdict={"verdict": "TRUE_POSITIVE"}
    )
    db_session.add(incident)
    await db_session.commit()

    async def override_get_db():
        yield db_session

    async def override_get_user():
        return MOCK_TENANT_A_USER

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_get_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.post(
            f"/api/reviews/{incident.id}/submit",
            json={"analyst_verdict": "TRUE_POSITIVE"}
        )
        assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"
        assert "access denied" in res.json().get("detail", "").lower()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_lifecycle_transition_and_promotion_eligibility_enforcement(
    db_session: AsyncSession,
    async_client: AsyncClient
):
    """
    Test 7: Enforce eligibility requirements for lifecycle transitions and promotions.
    Advancing to SUPERVISED_PILOT without 30 verified reviews or CONTROLLED_PRODUCTION
    without 100 samples must be blocked with HTTP 400.
    """
    rule_id = "PH_RULE_GOVERNANCE_TEST"
    profile = await RuleLearningService.get_or_create_profile(db_session, rule_id=rule_id)
    profile.lifecycle_stage = "VALIDATION"
    profile.total_analyst_reviews = 5  # Below 30 requirement
    db_session.add(profile)
    await db_session.commit()

    # 1. Attempt premature transition to SUPERVISED_PILOT
    res_trans = await async_client.post(
        f"/api/learning/rules/{rule_id}/transition",
        json={"target_stage": "SUPERVISED_PILOT", "reason": "Attempting jump without samples"}
    )
    assert res_trans.status_code == 400
    assert "requires at least 30 reviews" in res_trans.json()["detail"].lower()

    # 2. Attempt premature promotion request for SUPERVISED_PILOT via body
    res_prom_pilot = await async_client.post(
        "/api/governance/promotion/request",
        json={
            "profile_id": profile.id,
            "target_stage": "SUPERVISED_PILOT",
            "justification": "Testing promotion validation"
        }
    )
    assert res_prom_pilot.status_code == 400
    assert "requires at least 30 verified reviews" in res_prom_pilot.json()["detail"].lower()

    # 3. Attempt premature promotion request for CONTROLLED_PRODUCTION via query param
    res_prom_prod = await async_client.post(
        f"/api/governance/promotion/request?profile_id={profile.id}",
        json={
            "target_stage": "CONTROLLED_PRODUCTION",
            "justification": "Testing production criteria gating"
        }
    )
    assert res_prom_prod.status_code == 400
    assert "cannot submit promotion request" in res_prom_prod.json()["detail"].lower()

    # 4. Now simulate rule meeting production criteria
    profile.total_analyst_reviews = 120
    profile.verified_tp_count = 35
    profile.verified_fp_count = 85
    profile.fp_precision = 0.99
    profile.wilson_lower_bound = 0.97
    profile.tp_recall = 0.98
    profile.lifecycle_stage = "SUPERVISED_PILOT"
    db_session.add(profile)
    await db_session.commit()

    # Valid promotion request should succeed
    res_valid = await async_client.post(
        f"/api/governance/promotion/request?profile_id={profile.id}",
        json={
            "target_stage": "CONTROLLED_PRODUCTION",
            "justification": "Passed all statistical benchmarks with Wilson LB > 96%"
        }
    )
    assert res_valid.status_code == 200, f"Valid promotion failed: {res_valid.text}"
    valid_data = res_valid.json()
    assert valid_data["status"] == "PENDING"
    assert valid_data["requested_stage"] == "CONTROLLED_PRODUCTION"

    # Duplicate promotion request must be blocked
    res_dup = await async_client.post(
        "/api/governance/promotion/request",
        json={
            "profile_id": profile.id,
            "target_stage": "CONTROLLED_PRODUCTION",
            "justification": "Duplicate attempt"
        }
    )
    assert res_dup.status_code == 400
    assert "already pending" in res_dup.json()["detail"].lower()
