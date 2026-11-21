"""
Target Rule: Heavy TCP Host Scan On Fixed Port (UUID: 40498741-ee6b-4a71-9101-0d6d3f77154c)
AIS 2.1a Unified Evaluation Population & Accuracy Display Integrity Tests
Validates:
- Population A (Incident Inventory) vs Population B (Analyst Reviews) vs Population C (Verified Ground Truth)
- Strict mathematical invariants: Total Verified = Verified TP + Verified FP (never 13 reviews with 45 FP)
- Synthetic fixture exclusion: Patterned UUIDs (10000000-... and 20000000-...) are filtered out
- Zero decisive comparisons = NOT MEASURABLE (never 0.00%)
- Dual scope payload (current_inventory & historical_cohort)
"""

import uuid
import datetime
from typing import Optional, Dict, Any
import pytest
import pytest_asyncio
from sqlalchemy import select, delete, or_

from app.database import AsyncSessionLocal
from app.models.rule import Rule
from app.models.prompt import RulePrompt, PromptVersion
from app.models.incident import Incident
from app.models.actual_prompt_capture import ActualLLMPromptCapture
from app.models.verdict_intelligence import VerdictTrustAssessmentRecord
from app.models.analyst_feedback import AnalystVerdictReview
from app.services.rule_learning_service import RuleLearningService
from app.services.ais_evaluation_service import AisEvaluationService

RULE_UUID = "40498741-ee6b-4a71-9101-0d6d3f77154c"
RULE_EVENT_TYPE = "PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT"
RULE_NAME = "Heavy TCP Host Scan On Fixed Port"
V7_VERSION_ID = "pv-eval-contract-v7"


def make_prompt_capture(
    incident_id: str,
    rule_id: str = RULE_UUID,
    policy_version_number: int = 7,
    policy_version_id: Optional[str] = V7_VERSION_ID,
    response_verdict: Optional[str] = None,
) -> ActualLLMPromptCapture:
    return ActualLLMPromptCapture(
        id=str(uuid.uuid4()),
        execution_id=str(uuid.uuid4()),
        incident_id=incident_id,
        rule_id=rule_id,
        rule_name=RULE_NAME,
        policy_version_id=policy_version_id,
        policy_version_number=policy_version_number,
        policy_status="APPROVED",
        dispatch_status="COMPLETED",
        is_simulated=False,
        model_name="Qwen/Qwen2.5-7B-Instruct-AWQ",
        compiled_system_prompt="System Prompt",
        user_message="User Prompt",
        request_sha256="sha-" + uuid.uuid4().hex,
        response_raw=f'{{"verdict": "{response_verdict}"}}' if response_verdict else None,
        response_verdict=response_verdict,
        response_confidence=0.85,
        prompt_integrity_status="VALID",
        integrity_details={},
        latency_ms=450,
        captured_at=datetime.datetime.now(datetime.timezone.utc),
    )


def make_trust_record(
    incident_id: str,
    suggested_verdict: str,
    effective_verdict: str,
) -> VerdictTrustAssessmentRecord:
    return VerdictTrustAssessmentRecord(
        id=str(uuid.uuid4()),
        incident_id=incident_id,
        rule_id=RULE_UUID,
        suggested_verdict=suggested_verdict,
        effective_verdict=effective_verdict,
        trust_score=8,
        is_simulated=False,
        evaluated_at=datetime.datetime.now(datetime.timezone.utc),
    )


@pytest_asyncio.fixture(autouse=True)
async def setup_test_data():
    """Ensure rule and policy version exist and clean up test records."""
    async with AsyncSessionLocal() as db:
        # Clean previous test records
        await db.execute(delete(ActualLLMPromptCapture).where(
            or_(
                ActualLLMPromptCapture.incident_id.like("test-pop-%"),
                ActualLLMPromptCapture.incident_id.like("10000000-%"),
            )
        ))
        await db.execute(delete(VerdictTrustAssessmentRecord).where(
            or_(
                VerdictTrustAssessmentRecord.incident_id.like("test-pop-%"),
                VerdictTrustAssessmentRecord.incident_id.like("10000000-%"),
            )
        ))
        await db.execute(delete(AnalystVerdictReview).where(
            or_(
                AnalystVerdictReview.incident_id.like("test-pop-%"),
                AnalystVerdictReview.incident_id.like("10000000-%"),
            )
        ))
        await db.execute(delete(Incident).where(
            or_(
                Incident.id.like("test-pop-%"),
                Incident.id.like("10000000-%"),
            )
        ))

        # Ensure Rule
        r_res = await db.execute(select(Rule).where(Rule.id == RULE_UUID))
        rule = r_res.scalar_one_or_none()
        if not rule:
            db.add(Rule(
                id=RULE_UUID,
                rule_id=RULE_EVENT_TYPE,
                name=RULE_NAME,
                event_type=RULE_EVENT_TYPE,
                description="Detects fixed port TCP host scan attacks.",
                severity="HIGH",
                status="ACTIVE",
                data_source="FortiSIEM",
            ))

        # Ensure RulePrompt
        rp_res = await db.execute(select(RulePrompt).where(RulePrompt.rule_id == RULE_UUID))
        rp = rp_res.scalar_one_or_none()
        if not rp:
            rp = RulePrompt(
                id=str(uuid.uuid4()),
                rule_id=RULE_UUID,
                title=f"Prompt - {RULE_NAME}",
                ai_execution_suspended=False,
                active_version_id=V7_VERSION_ID,
            )
            db.add(rp)
        else:
            rp.active_version_id = V7_VERSION_ID
            rp.ai_execution_suspended = False

        # Ensure PromptVersion v7
        pv_res = await db.execute(select(PromptVersion).where(PromptVersion.id == V7_VERSION_ID))
        pv = pv_res.scalar_one_or_none()
        if not pv:
            pv = PromptVersion(
                id=V7_VERSION_ID,
                prompt_id=rp.id,
                version_number=7,
                status="APPROVED",
                quality_status="APPROVED",
                was_ever_approved=True,
                approved_at=datetime.datetime.now(datetime.timezone.utc),
                common_prompt="Standard Common Prompt",
                rule_specific_prompt="V7 Rule Specific Prompt",
                change_summary="V7 Approved Baseline",
            )
            db.add(pv)

        await db.commit()

    yield

    async with AsyncSessionLocal() as db:
        await db.execute(delete(ActualLLMPromptCapture).where(
            or_(
                ActualLLMPromptCapture.incident_id.like("test-pop-%"),
                ActualLLMPromptCapture.incident_id.like("10000000-%"),
            )
        ))
        await db.execute(delete(VerdictTrustAssessmentRecord).where(
            or_(
                VerdictTrustAssessmentRecord.incident_id.like("test-pop-%"),
                VerdictTrustAssessmentRecord.incident_id.like("10000000-%"),
            )
        ))
        await db.execute(delete(AnalystVerdictReview).where(
            or_(
                AnalystVerdictReview.incident_id.like("test-pop-%"),
                AnalystVerdictReview.incident_id.like("10000000-%"),
            )
        ))
        await db.execute(delete(Incident).where(
            or_(
                Incident.id.like("test-pop-%"),
                Incident.id.like("10000000-%"),
            )
        ))
        await db.commit()


@pytest.mark.asyncio
async def test_dual_scope_mathematical_invariants():
    """
    Verify that in both current_inventory and historical_cohort:
    Verified Total = Verified TP + Verified FP
    And that they never report inconsistent counts (e.g., 13 Reviews with 45 FP).
    """
    async with AsyncSessionLocal() as db:
        # Seed 3 current incidents
        for i in range(1, 4):
            inc_id = f"test-pop-curr-{i}"
            db.add(Incident(
                id=inc_id,
                incident_id=inc_id,
                rule_id=RULE_UUID,
                event_type=RULE_EVENT_TYPE,
                customer="DEFAULT",
                severity="HIGH",
                title=f"Test Incident {i}",
                status_name="Closed",
                created_at=datetime.datetime.now(datetime.timezone.utc),
            ))
            # Analyst marked all 3 as FALSE_POSITIVE
            db.add(AnalystVerdictReview(
                id=f"rev-curr-{i}",
                incident_id=inc_id,
                rule_id=RULE_UUID,
                customer="DEFAULT",
                reviewer_id="u-admin",
                analyst_verdict="FALSE_POSITIVE",
                ground_truth_status="VERIFIED",
                created_at=datetime.datetime.now(datetime.timezone.utc),
            ))
            # AI evaluated all 3 as REQUIRES_ATTENTION (Abstained under v7)
            db.add(make_prompt_capture(incident_id=inc_id, response_verdict="REQUIRES_ATTENTION"))
            db.add(make_trust_record(
                incident_id=inc_id,
                suggested_verdict="REQUIRES_ATTENTION",
                effective_verdict="REQUIRES_ATTENTION",
            ))

        # Seed 2 historical incidents (without current Incident row, but reviews recorded)
        for j in range(4, 6):
            inc_id = f"test-pop-hist-{j}"
            db.add(AnalystVerdictReview(
                id=f"rev-hist-{j}",
                incident_id=inc_id,
                rule_id=RULE_UUID,
                customer="DEFAULT",
                reviewer_id="u-admin",
                analyst_verdict="FALSE_POSITIVE",
                ground_truth_status="VERIFIED",
                created_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=10),
            ))
        await db.commit()

        # Evaluate via RuleLearningService
        rl_res = await RuleLearningService.evaluate_rule_accuracy(
            db=db,
            rule_id=RULE_UUID,
            customer="DEFAULT",
            version_id=V7_VERSION_ID,
        )

        assert rl_res is not None
        assert "current_inventory" in rl_res
        assert "historical_cohort" in rl_res

        curr = rl_res["current_inventory"]
        hist = rl_res["historical_cohort"]

        # Current Inventory Invariant:
        assert curr["verified_tp"] + curr["verified_fp"] == curr["verified_reviews"]
        assert curr["verified_tp"] == 0
        assert curr["verified_fp"] >= 3
        assert curr["verified_reviews"] >= 3

        # Historical Invariant:
        assert hist["verified_tp"] + hist["verified_fp"] == hist["total_reviews"]
        assert hist["verified_tp"] == 0
        assert hist["total_reviews"] >= curr["verified_reviews"]

        # Mathematical consistency: current verified reviews cannot exceed historical reviews
        assert curr["verified_reviews"] <= hist["total_reviews"]
        assert curr["verified_fp"] <= hist["verified_fp"]


@pytest.mark.asyncio
async def test_synthetic_patterned_fixture_exclusion():
    """
    Ensure synthetic patterned fixtures (e.g. 10000000-0000-0000-0000-000000000001)
    are strictly excluded from accuracy calculations and learning profiles.
    """
    async with AsyncSessionLocal() as db:
        synthetic_id = "10000000-0000-0000-0000-000000000001"
        db.add(Incident(
            id=synthetic_id,
            incident_id=synthetic_id,
            rule_id=RULE_UUID,
            event_type=RULE_EVENT_TYPE,
            customer="DEFAULT",
            severity="HIGH",
            title="Synthetic Fixture Incident",
            status_name="Closed",
            created_at=datetime.datetime.now(datetime.timezone.utc),
        ))
        db.add(AnalystVerdictReview(
            id="10000000-0000-0000-0000-000000000002",
            incident_id=synthetic_id,
            rule_id=RULE_UUID,
            customer="DEFAULT",
            reviewer_id="u-admin",
            analyst_verdict="TRUE_POSITIVE",  # Attempt to inject a synthetic TP
            ground_truth_status="VERIFIED",
            created_at=datetime.datetime.now(datetime.timezone.utc),
        ))
        db.add(make_prompt_capture(incident_id=synthetic_id, response_verdict="TRUE_POSITIVE"))
        await db.commit()

        # Run accuracy evaluation
        res = await RuleLearningService.evaluate_rule_accuracy(
            db=db,
            rule_id=RULE_UUID,
            customer="DEFAULT",
            version_id=V7_VERSION_ID,
        )

        # The synthetic TRUE_POSITIVE review must be excluded by the regex pattern!
        assert res["current_inventory"]["verified_tp"] == 0
        assert res["historical_cohort"]["verified_tp"] == 0


@pytest.mark.asyncio
async def test_zero_decisive_comparisons_returns_not_measurable():
    """
    When decisive comparisons = 0 (e.g. all predictions abstained),
    empirical accuracy must be NOT MEASURABLE (None / not a false 0.00%).
    """
    async with AsyncSessionLocal() as db:
        res = await AisEvaluationService.get_rule_evaluation_tracking_overview(
            db=db,
            rule_uuid=RULE_UUID,
            version_number=7,
            customer="DEFAULT",
        )

        summary = res["summary"]
        assert summary["eligible_decisive_comparisons"] == 0
        assert summary["selective_accuracy"] is None
        assert summary["accuracy_status"] == "NOT_MEASURABLE"
        assert "No eligible decisive" in summary["accuracy_explanation"]
        assert "current_inventory" in summary
        assert "historical_cohort" in summary
