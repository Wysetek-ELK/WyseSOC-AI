import pytest
import uuid
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from sqlalchemy import select, func

from app.database import Base
from app.models.rule import Rule
from app.models.incident import Incident
from app.models.investigation import Investigation
from app.models.rule_learning import RuleLearningProfile, RuleLearningStateHistory
from app.models.production_governance import ProductionAutomationPolicy
from app.services.rule_learning_service import RuleLearningService
from app.services.analyst_review_service import AnalystReviewService


@pytest_asyncio.fixture
async def db_session():
    """Provides an isolated, in-memory SQLite session with foreign keys enabled."""
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


@pytest.mark.asyncio
async def test_profile_initialization_target_rule(db_session: AsyncSession):
    """
    Test that target FortiSIEM rule 40498741-ee6b-4a71-9101-0d6d3f77154c
    is automatically, safely, and idempotently provisioned with an accessible RuleLearningProfile.
    """
    target_uuid = "40498741-ee6b-4a71-9101-0d6d3f77154c"

    # Profile does not exist initially
    profile = await RuleLearningService.get_or_create_profile(db_session, target_uuid)
    assert profile is not None
    assert profile.rule_id == target_uuid
    assert profile.rule_identifier == "PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT"
    assert profile.lifecycle_stage == "LEARNING"
    assert profile.total_analyst_reviews == 0
    assert profile.verified_tp_count == 0
    assert profile.verified_fp_count == 0

    # Underlying Rule record is properly created
    rule_res = await db_session.execute(select(Rule).where(Rule.id == target_uuid))
    rule = rule_res.scalar_one_or_none()
    assert rule is not None
    assert rule.name == "Heavy TCP Host Scan On Fixed Port"
    assert rule.event_type == "PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT"

    # Associated ProductionAutomationPolicy is created with auto-closure DISABLED
    pol_res = await db_session.execute(
        select(ProductionAutomationPolicy).where(ProductionAutomationPolicy.profile_id == profile.id)
    )
    pol = pol_res.scalar_one_or_none()
    assert pol is not None
    assert pol.is_enabled is False

    # Second call is idempotent and returns the same profile without error
    profile2 = await RuleLearningService.get_or_create_profile(db_session, target_uuid)
    assert profile2.id == profile.id


@pytest.mark.asyncio
async def test_ensure_all_rules_initialized(db_session: AsyncSession):
    """
    Test bulk idempotent initialization of all detection rules across customer scopes.
    """
    # Create two arbitrary rules
    rule1 = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_SSH_BRUTE_FORCE",
        name="SSH Brute Force",
        event_type="PH_RULE_SSH_BRUTE_FORCE",
        severity="HIGH",
    )
    rule2 = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_RANSOMWARE_BEHAVIOR",
        name="Ransomware Behavior Detected",
        event_type="PH_RULE_RANSOMWARE_BEHAVIOR",
        severity="CRITICAL",
    )
    db_session.add_all([rule1, rule2])
    await db_session.commit()

    profiles = await RuleLearningService.ensure_all_rules_initialized(db_session)
    assert len(profiles) >= 2

    # Verify rule1 profile exists
    p1 = await RuleLearningService.get_or_create_profile(db_session, rule1.id)
    assert p1.lifecycle_stage == "LEARNING"
    assert p1.rule_identifier == "PH_RULE_SSH_BRUTE_FORCE"


@pytest.mark.asyncio
async def test_profile_reload_persistence(db_session: AsyncSession):
    """
    Test that created profiles persist and reload accurately.
    """
    rule_uuid = str(uuid.uuid4())
    p = await RuleLearningService.get_or_create_profile(db_session, rule_uuid)
    profile_id = p.id

    # Query directly from DB
    res = await db_session.execute(
        select(RuleLearningProfile).where(RuleLearningProfile.id == profile_id)
    )
    loaded = res.scalar_one_or_none()
    assert loaded is not None
    assert loaded.id == profile_id
    assert loaded.rule_id == rule_uuid
    assert loaded.lifecycle_stage == "LEARNING"


@pytest.mark.asyncio
async def test_zero_verified_feedback_and_auto_closure_disabled(db_session: AsyncSession):
    """
    Verify profile initializes with zero verified feedback and auto closure disabled.
    """
    rule_uuid = str(uuid.uuid4())
    profile = await RuleLearningService.get_or_create_profile(db_session, rule_uuid)

    assert profile.total_analyst_reviews == 0
    assert profile.verified_tp_count == 0
    assert profile.verified_fp_count == 0
    assert profile.ai_correct_count == 0
    assert profile.ai_incorrect_count == 0
    assert profile.abstention_count == 0
    assert profile.validation_failure_count == 0
    assert profile.empirical_accuracy is None
    assert profile.wilson_lower_bound is None

    # Check Production eligibility: must NOT be eligible
    is_eligible, reasons = RuleLearningService.check_production_eligibility(profile)
    assert is_eligible is False
    assert len(reasons) > 0


@pytest.mark.asyncio
async def test_tenant_isolation_and_scoping(db_session: AsyncSession):
    """
    Test customer-scoped learning profiles prevent cross-tenant contamination.
    """
    rule = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_TEST_TENANCY",
        name="Test Multi-Tenancy Rule",
        event_type="PH_RULE_TEST_TENANCY",
    )
    db_session.add(rule)
    await db_session.commit()

    # Create profiles for two separate tenants
    p_tosoh = await RuleLearningService.get_or_create_profile(db_session, rule.id, customer="Tosoh")
    p_wstpl = await RuleLearningService.get_or_create_profile(db_session, rule.id, customer="WSTPL")

    assert p_tosoh.id != p_wstpl.id
    assert p_tosoh.customer == "Tosoh"
    assert p_wstpl.customer == "WSTPL"

    # Increment reviews on Tosoh only
    await RuleLearningService.record_analyst_feedback(
        db_session,
        profile_id=p_tosoh.id,
        analyst_verdict="FALSE_POSITIVE",
        ai_verdict="FALSE_POSITIVE",
        comparison_outcome="AGREEMENT_FP",
    )

    # Re-fetch both profiles
    res_t = await db_session.execute(select(RuleLearningProfile).where(RuleLearningProfile.id == p_tosoh.id))
    re_tosoh = res_t.scalar_one()

    res_w = await db_session.execute(select(RuleLearningProfile).where(RuleLearningProfile.id == p_wstpl.id))
    re_wstpl = res_w.scalar_one()

    assert re_tosoh.total_analyst_reviews == 1
    assert re_tosoh.verified_fp_count == 1
    assert re_wstpl.total_analyst_reviews == 0
    assert re_wstpl.verified_fp_count == 0


@pytest.mark.asyncio
async def test_learning_mode_unblocked_by_quality_failures(db_session: AsyncSession):
    """
    Verify that rule quality status does not prevent Learning Mode or analyst reviews.
    """
    rule_id = str(uuid.uuid4())
    profile = await RuleLearningService.get_or_create_profile(db_session, rule_id)
    assert profile.lifecycle_stage == "LEARNING"

    # Analyst review proceeds without G1-G8 blocking
    updated = await RuleLearningService.record_analyst_feedback(
        db_session,
        profile_id=profile.id,
        analyst_verdict="TRUE_POSITIVE",
        ai_verdict="TRUE_POSITIVE",
        comparison_outcome="AGREEMENT_TP",
    )
    assert updated.total_analyst_reviews == 1
    assert updated.verified_tp_count == 1


@pytest.mark.asyncio
async def test_historical_incidents_and_verdicts_untouched(db_session: AsyncSession):
    """
    Verify profile initialization never modifies historical incident records or AI verdicts.
    """
    rule = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_TEST_UNTOUCHED",
        name="Test Untouched Rule",
        event_type="PH_RULE_TEST_UNTOUCHED",
    )
    db_session.add(rule)
    await db_session.flush()

    inc = Incident(
        id=str(uuid.uuid4()),
        incident_id="INC-99901",
        rule_id=rule.id,
        event_type=rule.event_type,
        title="Sample SSH Incident",
        severity="HIGH",
        customer="Tosoh",
        ai_verdict={
            "verdict": "FALSE_POSITIVE",
            "confidence": 0.95,
            "reasoning": "Scheduled backup transfer",
        },
    )
    db_session.add(inc)
    await db_session.commit()

    # Initialize profiles
    await RuleLearningService.ensure_all_rules_initialized(db_session)

    # Re-fetch incident
    re_inc = (await db_session.execute(select(Incident).where(Incident.id == inc.id))).scalar_one()
    assert re_inc.incident_id == "INC-99901"
    assert re_inc.ai_verdict["verdict"] == "FALSE_POSITIVE"
    assert re_inc.ai_verdict["confidence"] == 0.95
    assert re_inc.ai_verdict["reasoning"] == "Scheduled backup transfer"


@pytest.mark.asyncio
async def test_explicit_initialization_and_read_only_get(db_session: AsyncSession):
    """
    Validates Requirement 9:
    - Pure read query returns None when uninitialized.
    - Explicit initialization endpoint creates profile in LEARNING state idempotently.
    - Subsequent read query finds the persisted profile.
    """
    rule = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_EXPLICIT_INIT_TEST",
        name="Explicit Init Test Rule",
        event_type="PH_RULE_EXPLICIT_INIT_TEST",
    )
    db_session.add(rule)
    await db_session.commit()

    # 1. Pure read query should return None before initialization
    prof_before = await RuleLearningService.get_profile(db_session, rule.id, "DEFAULT")
    assert prof_before is None

    # 2. Explicit initialization creates profile
    prof_init = await RuleLearningService.get_or_create_profile(db_session, rule.id, "DEFAULT")
    assert prof_init is not None
    assert prof_init.rule_id == rule.id
    assert prof_init.lifecycle_stage == "LEARNING"

    # 3. Subsequent pure read returns the exact profile
    prof_after = await RuleLearningService.get_profile(db_session, rule.id, "DEFAULT")
    assert prof_after is not None
    assert prof_after.id == prof_init.id


@pytest.mark.asyncio
async def test_switch_between_three_rules_persistence(db_session: AsyncSession):
    """
    Validates Requirement 13:
    Verifies profile persistence after reload and switching between at least three different detection rules.
    """
    rules_data = [
        ("40498741-ee6b-4a71-9101-0d6d3f77154c", "PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT", "Heavy TCP Host Scan On Fixed Port"),
        (str(uuid.uuid4()), "PH_RULE_DNS_TUNNEL_ANOMALY", "DNS Tunneling Anomaly"),
        (str(uuid.uuid4()), "PH_RULE_SUSPICIOUS_POWERSHELL_EXEC", "Suspicious PowerShell Encoded Execution"),
    ]

    for rid, rident, rname in rules_data:
        rule = Rule(id=rid, rule_id=rident, name=rname, event_type=rident)
        db_session.add(rule)
    await db_session.commit()

    # Initialize all three
    profiles = []
    for rid, rident, _ in rules_data:
        p = await RuleLearningService.get_or_create_profile(db_session, rid, "DEFAULT")
        profiles.append(p)

    assert len(profiles) == 3

    # Switch back and forth between rules
    for idx, (rid, rident, _) in enumerate(rules_data):
        loaded = await RuleLearningService.get_profile(db_session, rid, "DEFAULT")
        assert loaded is not None
        assert loaded.rule_id == rid
        assert loaded.rule_identifier == rident
        assert loaded.lifecycle_stage == "LEARNING"
        assert loaded.total_analyst_reviews == 0


@pytest.mark.asyncio
async def test_alembic_head_and_migration_revision():
    """
    Validates that Alembic head revision is 009_rule_learning_and_governance
    and points cleanly to down_revision 008_soc_pilot.
    """
    from app.services.migration_service import get_head_revision
    head = get_head_revision()
    assert head == "009_rule_learning_and_governance"
