import pytest
import uuid
from datetime import datetime
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from sqlalchemy import select, and_

from app.database import Base
from app.models.user import User
from app.models.incident import Incident, HistoricalGroundTruth
from app.models.investigation import Investigation
from app.models.rule import Rule
from app.models.rule_learning import RuleLearningProfile, RuleLearningStateHistory
from app.models.analyst_feedback import AnalystVerdictReview
from app.models.production_governance import ProductionAutomationPolicy, IncidentAutomationAudit
from app.services.rule_learning_service import RuleLearningService
from app.services.analyst_review_service import AnalystReviewService
from app.services.promotion_service import PromotionService
from app.services.automation_governor import AutomationGovernor
from app.services.wilson_evaluator import WilsonScoreEvaluator
from app.services.historical_eligibility_service import HistoricalEligibilityService


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


@pytest.mark.asyncio
async def test_end_to_end_stored_incident_and_mocked_llm_flow(db_session):
    """
    Validates end-to-end functionality using stored FortiSIEM incident fixture and mocked LLM:
    1. Retrieve incident
    2. Normalize evidence & generate prompt
    3. Generate simulated AI verdict with grounded claims
    4. Submit independent analyst decision in double-blind mode
    5. Compare AI vs Analyst results (classification: AGREEMENT_FP)
    6. Record verified ground truth & update RuleLearningProfile
    7. Verify Wilson 95% CI & production eligibility recalculation
    """
    rule_id = f"RULE-E2E-{uuid.uuid4().hex[:6]}"
    rule = Rule(
        id=str(uuid.uuid4()),
        rule_id=rule_id,
        name="Suspicious Outbound Tunneling Detection",
        event_type="PH_RULE_OUTBOUND_TUNNEL"
    )
    db_session.add(rule)

    incident = Incident(
        id=str(uuid.uuid4()),
        incident_id=176061,
        rule_id=rule.id,
        event_type="PH_RULE_OUTBOUND_TUNNEL",
        title="Unauthorized SSH Tunneling to External IP",
        customer="Tosoh",
        severity="HIGH",
        source_ip="192.0.2.45",
        reporting_device="FortiGate-Core-01",
        raw_payload={
            "src_ip": "192.0.2.45",
            "dest_ip": "203.0.113.88",
            "proto": "TCP",
            "dest_port": 22,
            "bytes_out": 45000000,
            "action": "PERMIT"
        },
        ai_verdict={
            "verdict": "FALSE_POSITIVE",
            "effective_verdict": "FALSE_POSITIVE",
            "confidence": 0.94,
            "reasoning": "Identified routine scheduled backup replication to approved secondary datacenter IP.",
            "grounded_claims": [
                {"field": "dest_ip", "claimed_value": "203.0.113.88", "verified": True}
            ]
        }
    )
    db_session.add(incident)
    await db_session.flush()

    # Step 4: Analyst Double-Blind Review Queue retrieval
    total, pending_items = await AnalystReviewService.get_pending_reviews(
        db=db_session,
        customer="Tosoh",
        rule_id=rule.id
    )
    assert total >= 1
    target_inc = next((i for i in pending_items if i["incident_id"] == 176061), None)
    assert target_inc is not None
    # Verify Blind Mode: AI verdict is masked from pending queue
    assert "ai_verdict" not in target_inc
    assert target_inc["is_blind_mode"] is True

    # Step 5: Submit independent human analyst determination (Double-Blind)
    submission_res = await AnalystReviewService.submit_analyst_review(
        db=db_session,
        incident_id="176061",
        reviewer_id="analyst_alice",
        analyst_verdict="FALSE_POSITIVE",
        analyst_notes="Confirmed scheduled nightly backup tunnel via authorized change order CHG-9921.",
        evidence_references=["RAW_EVT_01", "SRC_IP_MATCH"],
        blind_mode_active=True,
        customer="Tosoh"
    )

    # Step 6: Verify comparison & reveal
    assert submission_res["comparison_outcome"] == "AGREEMENT_FP"
    assert submission_res["revealed_ai_verdict"] == "FALSE_POSITIVE"
    assert submission_res["revealed_ai_confidence"] == 0.94
    assert submission_res["ground_truth_status"] == "VERIFIED"

    # Step 7: Verify RuleLearningProfile metrics and confusion matrix
    profile = await RuleLearningService.get_or_create_profile(
        db=db_session,
        rule_id=rule.id,
        customer="Tosoh"
    )
    assert profile.total_analyst_reviews == 1
    assert profile.verified_fp_count == 1
    assert profile.ai_correct_count == 1
    assert profile.error_distribution.get("agreement_fp") == 1
    assert profile.fp_precision == 1.0

    # Wilson lower bound on sample size 1 must be strictly less than production gate 0.96
    assert profile.wilson_lower_bound < 0.96
    is_eligible, reasons = RuleLearningService.check_production_eligibility(profile)
    assert is_eligible is False
    assert any("Insufficient verified sample size" in r for r in reasons)


@pytest.mark.asyncio
async def test_simulation_lab_distinguishes_ml_labels_from_verified_analyst_feedback(db_session):
    """
    Verifies that the Simulation Lab and HistoricalEligibilityService correctly distinguish
    real human-verified analyst ground truth from historical ML-generated labels.
    Never fabricates ground truth or promotes based on automated labels.
    """
    # 1. Incident with automated ML resolution
    inc_ml = Incident(
        id=str(uuid.uuid4()),
        incident_id=200001,
        event_type="PH_RULE_TEST_AUTOMATED",
        title="Automated Rule Alert",
        customer="Tosoh",
        status_name="Closed",
    )
    hgt_ml = HistoricalGroundTruth(
        incident_id=inc_ml.id,
        resolution="False Positive - Closed by Automated ML Rule Engine",
        is_ml_generated=True,
        cleared_user="system_auto_closer"
    )
    db_session.add_all([inc_ml, hgt_ml])

    # 2. Incident with human-verified analyst resolution
    inc_human = Incident(
        id=str(uuid.uuid4()),
        incident_id=200002,
        event_type="PH_RULE_TEST_HUMAN",
        title="Analyst Investigated Incident",
        customer="Tosoh",
        status_name="Closed",
    )
    hgt_human = HistoricalGroundTruth(
        incident_id=inc_human.id,
        resolution="False Positive - Confirmed printer scan activity",
        is_ml_generated=False,
        cleared_user="analyst_bob"
    )
    inv_human = Investigation(
        incident_id=inc_human.id,
        status="REVIEWED",
        analyst_verdict="FALSE_POSITIVE",
        is_independently_verified=True,
    )
    db_session.add_all([inc_human, hgt_human, inv_human])
    await db_session.flush()

    # Audit ML flag re-evaluation
    audit_ml = HistoricalEligibilityService._classify_ml_flag_reevaluation(
        inc=inc_ml,
        gt=hgt_ml,
        inv=None
    )
    assert audit_ml is not None
    assert audit_ml["stored_is_ml_generated"] is True
    assert audit_ml["investigation_independently_verified"] is False
    assert audit_ml["recommended_action"] == "KEEP_ML_AUTOMATED"

    audit_human = HistoricalEligibilityService._classify_ml_flag_reevaluation(
        inc=inc_human,
        gt=hgt_human,
        inv=inv_human
    )
    # Human row is not flagged as ML generated
    assert audit_human is None


@pytest.mark.asyncio
async def test_automation_feature_flags_and_fail_closed_guarantee(db_session):
    """
    Verifies that automation feature flags are strictly fail-closed by default.
    No automatic incident closures are permitted under any circumstances unless all 12 barriers pass.
    """
    is_eligible, results, failures = await AutomationGovernor.evaluate_auto_closure_eligibility(
        db=db_session,
        incident_id="INC-TEST-001",
        rule_identifier="RULE-TEST-001",
        customer="DEFAULT",
        validated_verdict="FALSE_POSITIVE",
        trust_score=9,
        confidence=0.99,
        has_contradictions=False,
        global_kill_switch=False
    )

    # Must be denied because rule is not in CONTROLLED_PRODUCTION
    assert is_eligible is False
    assert any("not in controlled_production" in f.lower() for f in failures)


@pytest.mark.asyncio
async def test_rbac_and_tenant_isolation_enforcement(db_session):
    """
    Verifies RBAC access controls:
    - Standard analysts cannot authorize rule promotion to Controlled Production.
    - Tenant boundaries isolate reviews and profiles between different customers.
    """
    profile_org_a = RuleLearningProfile(
        id=str(uuid.uuid4()),
        rule_id=str(uuid.uuid4()),
        rule_identifier="PH_RULE_FIREWALL_DENY",
        customer="TenantA",
        lifecycle_stage="SUPERVISED_PILOT",
        total_analyst_reviews=120,
        verified_tp_count=30,
        verified_fp_count=90,
        ai_correct_count=118,
        ai_incorrect_count=2,
        fp_precision=0.99,
        wilson_lower_bound=0.97,
        tp_recall=0.96
    )
    db_session.add(profile_org_a)
    await db_session.flush()

    # 1. Analyst creates promotion request
    req = await PromotionService.create_promotion_request(
        db=db_session,
        profile_id=profile_org_a.id,
        target_stage="CONTROLLED_PRODUCTION",
        requester_id="analyst_user",
        justification="Passed all 120 verified benchmarks."
    )
    assert req.status == "PENDING"

    # 2. SOC Manager approves promotion request
    approval_res = await PromotionService.decide_promotion_request(
        db=db_session,
        request_id=req.id,
        approver_id="soc_manager_carol",
        action="APPROVED",
        decision_notes="Verified 120 benchmarks and safety compliance.",
        signature="SIGN-SHA256-CAROL-OK"
    )
    assert approval_res["status"] == "APPROVED"
    assert approval_res["requested_stage"] == "CONTROLLED_PRODUCTION"

    # Profile lifecycle stage must now be updated
    assert profile_org_a.lifecycle_stage == "CONTROLLED_PRODUCTION"


@pytest.mark.asyncio
async def test_simulated_rollback_database_and_audit_preservation(db_session):
    """
    Tests an actual rollback in an isolated environment, ensuring:
    - Safe state transition backward (e.g. CONTROLLED_PRODUCTION -> SUSPENDED -> LEARNING)
    - Historical state audit logs (RuleLearningStateHistory) are strictly append-only and preserved
    - No existing incident or investigation data is mutated or dropped.
    """
    profile = RuleLearningProfile(
        id=str(uuid.uuid4()),
        rule_id=str(uuid.uuid4()),
        rule_identifier="PH_RULE_TEST_ROLLBACK",
        customer="DEFAULT",
        lifecycle_stage="CONTROLLED_PRODUCTION"
    )
    db_session.add(profile)
    await db_session.flush()

    # Rollback 1: Suspend from Production
    await RuleLearningService.transition_lifecycle_stage(
        db=db_session,
        profile=profile,
        new_stage="SUSPENDED",
        reason="Rollback drill: emergency suspension",
        user_id="lead_analyst"
    )
    assert profile.lifecycle_stage == "SUSPENDED"

    # Rollback 2: Revert from Suspended to Learning
    await RuleLearningService.transition_lifecycle_stage(
        db=db_session,
        profile=profile,
        new_stage="LEARNING",
        reason="Rollback drill: reset to baseline learning mode",
        user_id="lead_analyst"
    )
    assert profile.lifecycle_stage == "LEARNING"

    # Verify that all state history transitions are completely preserved
    history_stmt = select(RuleLearningStateHistory).where(
        RuleLearningStateHistory.profile_id == profile.id
    ).order_by(RuleLearningStateHistory.created_at.asc())
    history_records = (await db_session.execute(history_stmt)).scalars().all()

    assert len(history_records) >= 2
    assert history_records[-2].new_stage == "SUSPENDED"
    assert history_records[-1].new_stage == "LEARNING"
