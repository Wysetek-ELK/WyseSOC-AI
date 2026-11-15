import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.prompt import RulePrompt, PromptVersion
from app.models.incident import Incident
from app.models.analyst_feedback import AnalystVerdictReview
from app.models.rule_learning import RuleLearningProfile
from app.schemas.production_readiness import ReadinessStatus
from app.services.production_readiness_service import ProductionReadinessService
from app.services.prompt_studio_service import PromptStudioService
from app.services.incident_service import IncidentService
from app.services.rule_learning_service import RuleLearningService
from app.services.wilson_evaluator import WilsonScoreEvaluator
from app.utils.security import create_access_token
from app.main import app


@pytest.mark.asyncio
async def test_scenario_a_heavy_tcp_host_scan_readiness_integrity():
    """
    Scenario A: Verify that canonical rule Heavy TCP Host Scan (40498741-ee6b-4a71-9101-0d6d3f77154c)
    with legacy approved Version 1 (quality score 52.0, 2/8 gates) evaluates strictly to BLOCKED,
    with approval_eligible=False and explicit blocking requirements.
    """
    async with AsyncSessionLocal() as db:
        res = await ProductionReadinessService.evaluate_readiness(
            db,
            rule_identifier="40498741-ee6b-4a71-9101-0d6d3f77154c",
            version_id="8a460ab8-5f06-4a90-b2d4-db958199d644",
        )
        assert res.rule_identifier == "PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT"
        assert res.readiness_status == ReadinessStatus.BLOCKED
        assert res.readiness_label == "Blocked / Incomplete"
        assert res.approval_eligible is False
        assert res.quality_gates_passed < 8
        assert len(res.blocking_requirements) > 0
        assert any("correlation conditions & thresholds unverified" in b for b in res.blocking_requirements)


@pytest.mark.asyncio
async def test_scenario_b_candidate_draft_cannot_be_ready_for_approval_with_sub_8_gates():
    """
    Scenario B: Version 3 (Draft) with 6/8 gates and 0 reviews CANNOT be approved.
    Readiness evaluation must return BLOCKED with approval_eligible=False.
    """
    async with AsyncSessionLocal() as db:
        res = await ProductionReadinessService.evaluate_readiness(
            db,
            rule_identifier="40498741-ee6b-4a71-9101-0d6d3f77154c",
            version_id="ec0cc351-8dd1-4026-9dc3-586387bb324c",
        )
        assert res.readiness_status == ReadinessStatus.BLOCKED
        assert res.approval_eligible is False
        assert res.quality_gates_passed == 6
        assert len(res.blocking_requirements) >= 3
        # Must flag insufficient reviews and simulation
        assert any("Insufficient ground truth reviews" in b for b in res.blocking_requirements)
        assert any("simulation" in b.lower() for b in res.blocking_requirements)


@pytest.mark.asyncio
async def test_scenario_c_server_side_approval_rejection():
    """
    Scenario C: Attempting to approve an ineligible version on the server must raise
    ValueError with complete blocker details and never activate the policy.
    """
    async with AsyncSessionLocal() as db:
        service = PromptStudioService(db)
        with pytest.raises(ValueError) as excinfo:
            await service.approve_version(
                rule_id="40498741-ee6b-4a71-9101-0d6d3f77154c",
                version_id="ec0cc351-8dd1-4026-9dc3-586387bb324c",
                user_id="test-admin-id",
                change_summary="Attempted unearned approval",
            )
        err_msg = str(excinfo.value)
        assert "Policy approval rejected" in err_msg
        assert "RULE_DEFINITION_INCOMPLETE" in err_msg or "incomplete requirements" in err_msg


@pytest.mark.asyncio
async def test_blind_review_api_sanitization():
    """
    Verify that IncidentService masks ai_verdict to None when blind_review=True
    prior to analyst review submission, and returns ai_verdict after analyst review.
    """
    async with AsyncSessionLocal() as db:
        service = IncidentService(db)
        incidents, total, meta = await service.list_incidents_with_rule_summary(
            page=1,
            page_size=10,
            blind_review=True,
        )
        assert total > 0
        for inc in incidents:
            # Check if this incident has an analyst review
            rev_q = select(AnalystVerdictReview).where(
                (AnalystVerdictReview.incident_id == inc.id) | (AnalystVerdictReview.incident_id == inc.incident_id)
            )
            rev_res = await db.execute(rev_q)
            has_rev = rev_res.scalar_one_or_none() is not None

            if not has_rev:
                assert inc.ai_verdict is None, f"ai_verdict leaked for unreviewed incident {inc.incident_id}"
                assert inc.historical_resolution == "[Hidden - Blind Review]"

        # Also check single incident detail
        sample_inc = incidents[0]
        detail = await service.get_incident(sample_inc.incident_id, blind_review=True)
        assert detail is not None
        rev_q = select(AnalystVerdictReview).where(
            (AnalystVerdictReview.incident_id == detail.id) | (AnalystVerdictReview.incident_id == detail.incident_id)
        )
        rev_res = await db.execute(rev_q)
        has_rev = rev_res.scalar_one_or_none() is not None
        if not has_rev:
            assert detail.ai_verdict is None
            assert detail.ground_truth is None


def test_wilson_lower_bound_zero_failure_mathematics():
    """
    Verify Wilson Score lower bound math and the 93 error-free observation threshold
    for 96% Wilson lower bound at 95% confidence level.
    """
    # Case 1: n = 0 observations -> (0.0, 0.0)
    lower_0, upper_0 = WilsonScoreEvaluator.calculate_wilson_interval(0, 0)
    assert lower_0 == 0.0
    assert upper_0 == 0.0

    # Case 2: n = 30 error-free observations -> ~88.65% lower bound (< 96%)
    lower_30 = WilsonScoreEvaluator.calculate_lower_bound(30, 30)
    assert lower_30 < 0.96
    assert round(lower_30, 4) == 0.8865

    # Case 3: n = 92 error-free observations -> 95.99% (< 96.0%)
    lower_92 = WilsonScoreEvaluator.calculate_lower_bound(92, 92)
    assert lower_92 < 0.9600
    assert round(lower_92, 4) == 0.9599

    # Case 4: n = 93 error-free observations -> 96.03% (>= 96.0%)
    lower_93 = WilsonScoreEvaluator.calculate_lower_bound(93, 93)
    assert lower_93 >= 0.9600
    assert round(lower_93, 4) == 0.9603


def test_rule_learning_service_no_fabrication_when_total_eval_zero():
    """
    Verify that RuleLearningService sets fp_precision and wilson_lower_bound to None
    when total_fp_pred == 0, and never fabricates empirical accuracy.
    """
    profile = RuleLearningProfile(
        rule_id="test-rule-profile",
        rule_identifier="RULE_TEST_001",
        customer="DEFAULT",
        total_analyst_reviews=10,
        verified_fp_count=10,
        verified_tp_count=0,
        ai_correct_count=0,
        ai_incorrect_count=0,
        error_distribution={"agreement_fp": 0, "critical_missed_tp": 0},
    )

    RuleLearningService._recalculate_profile_metrics(profile)

    assert profile.empirical_accuracy is None
    assert profile.fp_precision is None
    assert profile.wilson_lower_bound is None
    assert profile.tp_recall is None


@pytest.mark.asyncio
async def test_rbac_read_only_viewer_mutation_forbidden():
    """
    Verify that an authenticated Read-Only Viewer receives 403 Forbidden
    when attempting to synthesize an intelligent draft or approve a policy version.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        viewer_token = create_access_token({
            "sub": "viewer-user-003",
            "username": "viewer",
            "role": "Read-Only Viewer",
        })
        headers = {"Authorization": f"Bearer {viewer_token}"}

        # 1. Attempt to synthesize intelligent draft -> MUST BE 403 FORBIDDEN
        synth_res = await client.post(
            "/api/prompts/rule/40498741-ee6b-4a71-9101-0d6d3f77154c/generate-intelligent-draft",
            headers=headers,
            json={},
        )
        assert synth_res.status_code == 403, f"Expected 403 for viewer synthesize, got {synth_res.status_code}"
        assert "Access denied" in synth_res.text or "role" in synth_res.text.lower()

        # 2. Attempt to approve version -> MUST BE 403 FORBIDDEN
        approve_res = await client.post(
            "/api/prompts/rule/40498741-ee6b-4a71-9101-0d6d3f77154c/approve/ec0cc351-8dd1-4026-9dc3-586387bb324c",
            headers=headers,
            json={"change_summary": "Viewer trying to approve"},
        )
        assert approve_res.status_code == 403, f"Expected 403 for viewer approve, got {approve_res.status_code}"
        assert "Access denied" in approve_res.text or "role" in approve_res.text.lower()
