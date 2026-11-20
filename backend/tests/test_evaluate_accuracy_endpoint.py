import pytest
import uuid
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.rule import Rule
from app.models.incident import Incident
from app.models.rule_learning import RuleLearningProfile
from app.models.analyst_feedback import AnalystVerdictReview
from app.services.rule_learning_service import RuleLearningService


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


@pytest.mark.asyncio
async def test_evaluate_accuracy_zero_decisive_predictions(db_session: AsyncSession):
    """
    Verifies that when all analyst reviews resolve AI abstentions or represent initial
    benchmarks, empirical accuracy evaluates strictly to None (N/A) rather than 0% or 100%.
    """
    rule_id = str(uuid.uuid4())
    rule = Rule(
        id=rule_id,
        rule_id="PH_RULE_TEST_ZERO_DECISIVE",
        name="Test Zero Decisive Rule",
        severity="MEDIUM",
    )
    db_session.add(rule)
    await db_session.flush()

    # Create 16 analyst-resolved abstentions and 15 initial benchmarks (total: 31 reviews, all FP)
    for i in range(16):
        inc = Incident(
            id=str(uuid.uuid4()),
            incident_id=f"INC-ABS-{i}",
            rule_id=rule.id,
            event_type="test",
            severity="MEDIUM",
        )
        db_session.add(inc)
        await db_session.flush()

        rev = AnalystVerdictReview(
            id=str(uuid.uuid4()),
            incident_id=inc.id,
            rule_id=rule.id,
            customer="DEFAULT",
            reviewer_id="analyst",
            analyst_verdict="FALSE_POSITIVE",
            revealed_ai_verdict="REQUIRES_ATTENTION",
            comparison_outcome="ANALYST_RESOLVED_ABSTENTION",
        )
        db_session.add(rev)

    for j in range(15):
        inc = Incident(
            id=str(uuid.uuid4()),
            incident_id=f"INC-INIT-{j}",
            rule_id=rule.id,
            event_type="test",
            severity="MEDIUM",
        )
        db_session.add(inc)
        await db_session.flush()

        rev = AnalystVerdictReview(
            id=str(uuid.uuid4()),
            incident_id=inc.id,
            rule_id=rule.id,
            customer="DEFAULT",
            reviewer_id="analyst",
            analyst_verdict="FALSE_POSITIVE",
            revealed_ai_verdict=None,
            comparison_outcome="ANALYST_ONLY_INITIAL_BENCHMARK",
        )
        db_session.add(rev)

    await db_session.commit()

    # Execute evaluation
    result = await RuleLearningService.evaluate_rule_accuracy(
        db=db_session,
        rule_id=rule.id,
        customer="DEFAULT",
    )

    assert result["success"] is True
    assert result["total_analyst_reviews"] == 31
    assert result["verified_fp_count"] == 31
    assert result["verified_tp_count"] == 0
    assert result["decisive_evaluations"] == 0
    assert result["empirical_accuracy"] is None, "Empirical accuracy must be None when decisive evaluations == 0"
    assert result["fp_precision"] is None
    assert result["tp_recall"] is None
    assert result["wilson_lower_bound"] is None

    # Check class balance
    assert result["class_balance"]["is_balanced"] is False
    assert result["class_balance"]["tp_deficit"] == 10
    assert result["class_balance"]["fp_deficit"] == 0

    # Check diagnostic breakdown
    assert result["breakdown"]["analyst_resolved_abstention"] == 16
    assert result["breakdown"]["analyst_only_initial_benchmark"] == 15
    assert result["breakdown"]["agreement_tp"] == 0
    assert result["breakdown"]["agreement_fp"] == 0

    # Ensure profile was updated in DB
    profile = await RuleLearningService.get_profile(db_session, rule.id, "DEFAULT")
    assert profile is not None
    assert profile.empirical_accuracy is None
    assert profile.total_analyst_reviews == 31
    assert profile.verified_fp_count == 31


@pytest.mark.asyncio
async def test_evaluate_accuracy_with_decisive_predictions(db_session: AsyncSession):
    """
    Verifies that when decisive model determinations (TP and FP) exist, Selective Accuracy,
    FP precision, TP recall, and Wilson confidence lower bound are computed accurately.
    """
    rule_id = str(uuid.uuid4())
    rule = Rule(
        id=rule_id,
        rule_id="PH_RULE_TEST_DECISIVE",
        name="Test Decisive Rule",
        severity="HIGH",
    )
    db_session.add(rule)
    await db_session.flush()

    # 15 Agreed TP
    for i in range(15):
        inc = Incident(id=str(uuid.uuid4()), incident_id=f"INC-TP-{i}", rule_id=rule.id, event_type="test", severity="HIGH")
        db_session.add(inc)
        await db_session.flush()
        rev = AnalystVerdictReview(
            id=str(uuid.uuid4()),
            incident_id=inc.id,
            rule_id=rule.id,
            customer="DEFAULT",
            reviewer_id="analyst",
            analyst_verdict="TRUE_POSITIVE",
            revealed_ai_verdict="TRUE_POSITIVE",
            comparison_outcome="AGREEMENT_TP",
        )
        db_session.add(rev)

    # 15 Agreed FP
    for j in range(15):
        inc = Incident(id=str(uuid.uuid4()), incident_id=f"INC-FP-{j}", rule_id=rule.id, event_type="test", severity="HIGH")
        db_session.add(inc)
        await db_session.flush()
        rev = AnalystVerdictReview(
            id=str(uuid.uuid4()),
            incident_id=inc.id,
            rule_id=rule.id,
            customer="DEFAULT",
            reviewer_id="analyst",
            analyst_verdict="FALSE_POSITIVE",
            revealed_ai_verdict="FALSE_POSITIVE",
            comparison_outcome="AGREEMENT_FP",
        )
        db_session.add(rev)

    # 2 AI False Alarms (AI said TP, Analyst said FP)
    for k in range(2):
        inc = Incident(id=str(uuid.uuid4()), incident_id=f"INC-FA-{k}", rule_id=rule.id, event_type="test", severity="HIGH")
        db_session.add(inc)
        await db_session.flush()
        rev = AnalystVerdictReview(
            id=str(uuid.uuid4()),
            incident_id=inc.id,
            rule_id=rule.id,
            customer="DEFAULT",
            reviewer_id="analyst",
            analyst_verdict="FALSE_POSITIVE",
            revealed_ai_verdict="TRUE_POSITIVE",
            comparison_outcome="AI_FALSE_ALARM",
        )
        db_session.add(rev)

    await db_session.commit()

    result = await RuleLearningService.evaluate_rule_accuracy(
        db=db_session,
        rule_id=rule.id,
        customer="DEFAULT",
    )

    assert result["success"] is True
    # Decisive evaluations = 15 + 15 + 2 = 32
    assert result["decisive_evaluations"] == 32
    assert result["ai_correct_count"] == 30
    assert result["ai_incorrect_count"] == 2
    # Accuracy = 30 / 32 = 0.9375
    assert result["empirical_accuracy"] == 0.9375
    # Class balance: TP=15 (>=10), FP=17 (>=10) -> True!
    assert result["class_balance"]["is_balanced"] is True
    assert result["class_balance"]["tp_deficit"] == 0
    assert result["class_balance"]["fp_deficit"] == 0
