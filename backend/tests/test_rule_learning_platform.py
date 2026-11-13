import pytest
import uuid
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.rule import Rule
from app.models.incident import Incident
from app.models.investigation import Investigation
from app.models.rule_learning import RuleLearningProfile, RuleLearningStateHistory
from app.models.analyst_feedback import AnalystVerdictReview, AnalystReviewAdjudication
from app.models.production_governance import (
    RulePromotionRequest,
    RulePromotionApproval,
    ProductionAutomationPolicy,
    IncidentAutomationAudit
)
from app.services.wilson_evaluator import WilsonScoreEvaluator
from app.services.rule_learning_service import RuleLearningService
from app.services.analyst_review_service import AnalystReviewService
from app.services.promotion_service import PromotionService
from app.services.automation_governor import AutomationGovernor


@pytest_asyncio.fixture
async def db_session():
    """Provides an isolated, in-memory SQLite session for testing."""
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


# ---------------------------------------------------------------------------
# 1. Wilson Score Confidence Interval Tests
# ---------------------------------------------------------------------------

def test_wilson_score_small_sample_protection():
    """
    Verifies that small sample sizes with 100% observed success are NOT
    treated as 100% certainty (protects against the zero-failure fallacy).
    """
    # 5 out of 5 correct (100% observed)
    lower_5, upper_5 = WilsonScoreEvaluator.calculate_wilson_interval(5, 5)
    assert lower_5 < 0.60, f"Expected Wilson lower bound < 60% for n=5, got {lower_5}"
    assert upper_5 == 1.0

    # 50 out of 50 correct
    lower_50, _ = WilsonScoreEvaluator.calculate_wilson_interval(50, 50)
    assert 0.90 < lower_50 < 0.95, f"Expected Wilson lower bound ~93% for n=50, got {lower_50}"

    # 200 out of 200 correct
    lower_200, _ = WilsonScoreEvaluator.calculate_wilson_interval(200, 200)
    assert lower_200 >= 0.98, f"Expected Wilson lower bound >= 98% for n=200, got {lower_200}"

    # Zero total cases handled safely
    lower_0, upper_0 = WilsonScoreEvaluator.calculate_wilson_interval(0, 0)
    assert lower_0 == 0.0 and upper_0 == 0.0


# ---------------------------------------------------------------------------
# 2. Rule Learning Profile & Lifecycle State Machine Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rule_learning_profile_lifecycle(db_session: AsyncSession):
    """
    Tests RuleLearningProfile creation, metric updates, and valid/invalid state transitions.
    """
    rule = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_WEB_POL_VIOLATION_TEST",
        name="Test Web Policy Violation",
        event_type="PH_RULE_WEB_POL_VIOLATION_TEST",
        severity="MEDIUM"
    )
    db_session.add(rule)
    await db_session.flush()

    # 1. Initial Profile Creation
    profile = await RuleLearningService.get_or_create_profile(
        db=db_session,
        rule_id=rule.id,
        customer="Tenant_Alpha"
    )
    assert profile.lifecycle_stage == RuleLearningService.STAGE_LEARNING
    assert profile.total_incidents_processed == 0

    # 2. Record Verdict Completion
    await RuleLearningService.record_verdict_completion(
        db=db_session,
        rule_id=rule.id,
        customer="Tenant_Alpha",
        effective_verdict="REQUIRES_ATTENTION",
        is_abstained=True
    )
    assert profile.total_incidents_processed == 1
    assert profile.abstention_count == 1

    # 3. Invalid Transition Rejection (Cannot jump straight to CONTROLLED_PRODUCTION)
    with pytest.raises(ValueError, match="Invalid lifecycle transition"):
        await RuleLearningService.transition_lifecycle_stage(
            db=db_session,
            profile=profile,
            new_stage=RuleLearningService.STAGE_CONTROLLED_PRODUCTION,
            reason="Premature promotion attempt",
            user_id="test_admin"
        )

    # 4. Valid Transition to VALIDATION
    updated = await RuleLearningService.transition_lifecycle_stage(
        db=db_session,
        profile=profile,
        new_stage=RuleLearningService.STAGE_VALIDATION,
        reason="Entering validation phase",
        user_id="test_admin"
    )
    assert updated.lifecycle_stage == RuleLearningService.STAGE_VALIDATION


# ---------------------------------------------------------------------------
# 3. Double-Blind Review Workflow & Agreement Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_double_blind_analyst_review_workflow(db_session: AsyncSession):
    """
    Tests independent review submission, post-submission reveal, agreement logging,
    and automatic RuleLearningProfile metric recalculation.
    """
    rule = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_TEST_SUSP_EXEC",
        name="Test Suspicious Execution",
        event_type="PH_RULE_TEST_SUSP_EXEC",
        severity="HIGH"
    )
    db_session.add(rule)
    await db_session.flush()

    incident = Incident(
        id=str(uuid.uuid4()),
        incident_id="INC-TEST-001",
        rule_id=rule.id,
        event_type=rule.event_type,
        title=rule.name,
        customer="DEFAULT",
        source_ip="192.0.2.100",
        ai_verdict={"verdict": "FALSE_POSITIVE", "effective_verdict": "FALSE_POSITIVE"}
    )
    db_session.add(incident)
    await db_session.flush()

    # 1. Analyst submits independent determination (matching AI FP -> AGREEMENT_FP)
    review_res = await AnalystReviewService.submit_analyst_review(
        db=db_session,
        incident_id=incident.incident_id,
        reviewer_id="analyst_jane",
        analyst_verdict="FALSE_POSITIVE",
        analyst_notes="Confirmed authorized scheduled maintenance script.",
        blind_mode_active=True
    )

    assert review_res["comparison_outcome"] == "AGREEMENT_FP"
    assert review_res["revealed_ai_verdict"] == "FALSE_POSITIVE"
    assert review_res["ground_truth_status"] == "VERIFIED"

    # Verify profile metrics updated
    profile = await RuleLearningService.get_or_create_profile(db_session, rule.id)
    assert profile.total_analyst_reviews == 1
    assert profile.verified_fp_count == 1
    assert profile.ai_correct_count == 1
    assert profile.empirical_accuracy == 1.0


# ---------------------------------------------------------------------------
# 4. Critical Missed TP Automatic Suspension Trigger
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_critical_missed_tp_triggers_suspension(db_session: AsyncSession):
    """
    Verifies that if an analyst identifies a confirmed True Positive on an incident
    where the AI proposed False Positive, a critical alarm is raised and an active
    production rule is immediately suspended.
    """
    rule = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_CRITICAL_TEST",
        name="Critical Attack Rule",
        event_type="PH_RULE_CRITICAL_TEST",
        severity="CRITICAL"
    )
    db_session.add(rule)
    await db_session.flush()

    profile = await RuleLearningService.get_or_create_profile(db_session, rule.id)
    profile.lifecycle_stage = RuleLearningService.STAGE_CONTROLLED_PRODUCTION
    db_session.add(profile)
    await db_session.flush()

    # Incident where AI proposed FALSE_POSITIVE
    incident = Incident(
        id=str(uuid.uuid4()),
        incident_id="INC-ATTACK-001",
        rule_id=rule.id,
        event_type=rule.event_type,
        title=rule.name,
        customer="DEFAULT",
        ai_verdict={"verdict": "FALSE_POSITIVE", "effective_verdict": "FALSE_POSITIVE"}
    )
    db_session.add(incident)
    await db_session.flush()

    # Analyst catches the attack -> TRUE_POSITIVE
    review_res = await AnalystReviewService.submit_analyst_review(
        db=db_session,
        incident_id=incident.incident_id,
        reviewer_id="analyst_bob",
        analyst_verdict="TRUE_POSITIVE",
        analyst_notes="Confirmed ransomware C2 beaconing. Definite True Positive!",
        blind_mode_active=True
    )

    assert review_res["comparison_outcome"] == "CRITICAL_MISSED_TP"
    assert "CRITICAL WARNING" in review_res["disagreement_reason"]

    # Verify Rule was AUTOMATICALLY SUSPENDED
    profile_updated = await RuleLearningService.get_or_create_profile(db_session, rule.id)
    assert profile_updated.lifecycle_stage == RuleLearningService.STAGE_SUSPENDED
    assert profile_updated.ai_incorrect_count == 1


# ---------------------------------------------------------------------------
# 5. Production Eligibility & 12-Barrier Automation Safety Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_automation_governor_safety_interlocks(db_session: AsyncSession):
    """
    Tests the 12-barrier safety check for automated FP closure.
    """
    # Case A: Rule in LEARNING stage -> Auto-closure BLOCKED
    is_eligible, results, failures = await AutomationGovernor.evaluate_auto_closure_eligibility(
        db=db_session,
        incident_id="INC-999",
        rule_identifier="RULE_UNAPPROVED",
        customer="DEFAULT",
        validated_verdict="FALSE_POSITIVE",
        trust_score=9,
        confidence=95.0,
        has_contradictions=False,
        global_kill_switch=False
    )
    assert is_eligible is False
    assert results["barrier_02_rule_in_controlled_production"] is False
    assert any("CONTROLLED_PRODUCTION" in f for f in failures)

    # Case B: Contradiction present (loopback on external traffic) -> BLOCKED
    is_eligible_b, results_b, failures_b = await AutomationGovernor.evaluate_auto_closure_eligibility(
        db=db_session,
        incident_id="INC-999",
        rule_identifier="RULE_UNAPPROVED",
        customer="DEFAULT",
        validated_verdict="FALSE_POSITIVE",
        trust_score=9,
        confidence=95.0,
        has_contradictions=True,
        global_kill_switch=False
    )
    assert is_eligible_b is False
    assert results_b["barrier_05_zero_contradictions"] is False

    # Case C: Global kill-switch active -> BLOCKED
    is_eligible_c, results_c, failures_c = await AutomationGovernor.evaluate_auto_closure_eligibility(
        db=db_session,
        incident_id="INC-999",
        rule_identifier="RULE_UNAPPROVED",
        customer="DEFAULT",
        validated_verdict="FALSE_POSITIVE",
        trust_score=9,
        confidence=95.0,
        has_contradictions=False,
        global_kill_switch=True
    )
    assert is_eligible_c is False
    assert results_c["barrier_01_global_killswitch"] is False


# ---------------------------------------------------------------------------
# 6. Multi-Tenant Scoping Isolation Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tenant_isolation_in_learning_profiles(db_session: AsyncSession):
    """
    Verifies that two tenants sharing the exact same FortiSIEM rule maintain
    completely isolated learning profiles and metrics.
    """
    rule = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_SHARED_EXFIL",
        name="Shared Exfiltration Rule",
        event_type="PH_RULE_SHARED_EXFIL",
        severity="HIGH"
    )
    db_session.add(rule)
    await db_session.flush()

    prof_tenant_a = await RuleLearningService.get_or_create_profile(db_session, rule.id, customer="Customer_A")
    prof_tenant_b = await RuleLearningService.get_or_create_profile(db_session, rule.id, customer="Customer_B")

    assert prof_tenant_a.id != prof_tenant_b.id
    assert prof_tenant_a.customer == "Customer_A"
    assert prof_tenant_b.customer == "Customer_B"

    # Tenant A receives review
    prof_tenant_a.total_analyst_reviews = 150
    prof_tenant_a.lifecycle_stage = RuleLearningService.STAGE_CONTROLLED_PRODUCTION
    db_session.add(prof_tenant_a)
    await db_session.flush()

    # Verify Tenant B remains completely unmutated in LEARNING stage
    prof_b_refreshed = await RuleLearningService.get_or_create_profile(db_session, rule.id, customer="Customer_B")
    assert prof_b_refreshed.total_analyst_reviews == 0
    assert prof_b_refreshed.lifecycle_stage == RuleLearningService.STAGE_LEARNING

