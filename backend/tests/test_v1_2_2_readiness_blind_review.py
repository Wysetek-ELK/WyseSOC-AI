import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.prompt import RulePrompt, PromptVersion
from app.models.incident import Incident
from app.models.analyst_feedback import AnalystVerdictReview
from app.models.rule_learning import RuleLearningProfile
from app.models.user import User
from app.schemas.production_readiness import ReadinessStatus
from app.services.production_readiness_service import ProductionReadinessService
from app.services.prompt_studio_service import PromptStudioService
from app.services.incident_service import IncidentService
from app.services.rule_learning_service import RuleLearningService
from app.services.wilson_evaluator import WilsonScoreEvaluator
from app.utils.security import create_access_token
from app.main import app

HEAVY_TCP_RULE_ID = "40498741-ee6b-4a71-9101-0d6d3f77154c"
HEAVY_TCP_V1_ID = "8a460ab8-5f06-4a90-b2d4-db958199d644"
HEAVY_TCP_V3_ID = "ec0cc351-8dd1-4026-9dc3-586387bb324c"

ANALYST_USER_ID = "analyst-user-002"
VIEWER_USER_ID = "viewer-user-003"
ADMIN_USER_ID = "24ecd70d-c30b-4f1a-a022-ccc3ef571b95"


# ==============================================================================
# READINESS INTEGRITY & CONSISTENCY SCENARIOS (1–10)
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_01_authoritative_readiness_state_consistency():
    """
    Scenario 1: Authoritative Production Readiness State across APIs and models.
    Invariant: READY_FOR_APPROVAL requires approval_eligible == True.
    A candidate version that fails mandatory gates or requirements is BLOCKED.
    """
    async with AsyncSessionLocal() as db:
        res = await ProductionReadinessService.evaluate_readiness(
            db,
            rule_identifier=HEAVY_TCP_RULE_ID,
            version_id=HEAVY_TCP_V3_ID,
        )
        assert res.readiness_status == ReadinessStatus.BLOCKED
        assert res.approval_eligible is False
        assert len(res.blocking_requirements) > 0


@pytest.mark.asyncio
async def test_scenario_02_candidate_draft_sub8_gates_ineligible():
    """
    Scenario 2: Candidate Draft sub-8 gates strictly ineligible (approval_eligible = False).
    Candidate v3 has 6/8 gates passed and 0 reviews, so it cannot be approved.
    """
    async with AsyncSessionLocal() as db:
        res = await ProductionReadinessService.evaluate_readiness(
            db,
            rule_identifier=HEAVY_TCP_RULE_ID,
            version_id=HEAVY_TCP_V3_ID,
        )
        assert res.quality_gates_passed == 6
        assert res.approval_eligible is False
        assert res.readiness_status == ReadinessStatus.BLOCKED


@pytest.mark.asyncio
async def test_scenario_03_server_side_approval_rejection_for_ineligible_version():
    """
    Scenario 3: Server-side approval rejection for ineligible version.
    Attempting to approve an ineligible draft version must raise ValueError.
    """
    async with AsyncSessionLocal() as db:
        service = PromptStudioService(db)
        with pytest.raises(ValueError) as excinfo:
            await service.approve_version(
                rule_id=HEAVY_TCP_RULE_ID,
                version_id=HEAVY_TCP_V3_ID,
                user_id=ADMIN_USER_ID,
                change_summary="Illegal attempt to approve incomplete candidate",
            )
        err = str(excinfo.value)
        assert "Policy approval rejected" in err
        assert "incomplete requirements" in err or "RULE_DEFINITION_INCOMPLETE" in err


@pytest.mark.asyncio
async def test_scenario_04_heavy_tcp_v3_checklist_consistency():
    """
    Scenario 4: Heavy TCP candidate v3 checklist consistency:
    - Stage 1 (define_detection): BLOCKED due to unverified thresholds.
    - Stage 2 (verify_evidence): BLOCKED because Stage 1 is unverified and contract is UNVERIFIED.
    - Stage 3 (validate_policy): Quality score 77.0 meets standard (>= 70), text does NOT say "below 70 requirement".
    - Stage 6 (production_approval): BLOCKED with action button disabled.
    - Smart Next Action prioritizes root dependency: Verify FortiSIEM Detection Semantics.
    """
    async with AsyncSessionLocal() as db:
        res = await ProductionReadinessService.evaluate_readiness(
            db,
            rule_identifier=HEAVY_TCP_RULE_ID,
            version_id=HEAVY_TCP_V3_ID,
        )

        stage_map = {s.stage_id: s for s in res.stages}

        # Stage 1: Define Detection
        st1 = stage_map["define_detection"]
        assert st1.status.value == "BLOCKED"
        assert "detection condition" in st1.missing_requirement.lower() or "threshold" in st1.missing_requirement.lower()

        # Stage 2: Verify Evidence
        st2 = stage_map["verify_evidence"]
        assert st2.status.value == "BLOCKED"
        assert "upstream" in st2.missing_requirement.lower() or "stage 1" in st2.missing_requirement.lower()

        # Stage 3: Validate AI Policy
        st3 = stage_map["validate_policy"]
        assert res.quality_score == 77.0
        # Contradiction check: String must NOT say "below 70 requirement" when score is 77.0
        if st3.missing_requirement:
            assert "below 70 requirement" not in st3.missing_requirement
            assert "meets score threshold" in st3.missing_requirement

        # Stage 6: Production Approval
        st6 = stage_map["production_approval"]
        assert st6.status.value == "BLOCKED"

        # Smart Action
        assert res.recommended_action is not None
        assert "Semantics" in res.recommended_action.title or "Define" in res.recommended_action.title


@pytest.mark.asyncio
async def test_scenario_05_heavy_tcp_v1_historical_approved_baseline_preserved():
    """
    Scenario 5: Heavy TCP v1 historical approved baseline preserved.
    V1 was approved previously but passes 2/8 gates under modern VCDS criteria.
    Its historical status 'APPROVED' in DB is preserved, but readiness flags revalidation required
    and ai_execution_status is 'Suspended'.
    """
    async with AsyncSessionLocal() as db:
        v1_q = select(PromptVersion).where(PromptVersion.id == HEAVY_TCP_V1_ID)
        v1_res = await db.execute(v1_q)
        v1_model = v1_res.scalar_one_or_none()
        assert v1_model is not None
        assert v1_model.status == "APPROVED"

        res = await ProductionReadinessService.evaluate_readiness(
            db,
            rule_identifier=HEAVY_TCP_RULE_ID,
            version_id=HEAVY_TCP_V1_ID,
        )
        assert res.ai_execution_status == "Suspended"
        assert res.quality_gates_passed == 2
        assert res.approval_eligible is False


@pytest.mark.asyncio
async def test_scenario_06_score_consistency_and_raw_vs_semantic_coverage():
    """
    Scenario 6: Authoritative score consistency:
    Authoritative assessment score is 77.0, not conflated with raw field presence.
    Raw fields present (8) != semantic verification.
    """
    async with AsyncSessionLocal() as db:
        res = await ProductionReadinessService.evaluate_readiness(
            db,
            rule_identifier=HEAVY_TCP_RULE_ID,
            version_id=HEAVY_TCP_V3_ID,
        )
        assert res.quality_score == 77.0
        st2 = next(s for s in res.stages if s.stage_id == "verify_evidence")
        assert st2.status.value == "BLOCKED"


def test_scenario_07_statistical_eligibility_pilot_vs_production():
    """
    Scenario 7: Statistical eligibility consistency:
    - Pilot threshold: 30 reviews -> Wilson lower bound ~88.65% (< 96%).
    - Production threshold: 100 reviews -> n >= 93 error-free reviews for 96% Wilson lower bound.
    A rule with 30 reviews cannot be treated as ready for full production approval.
    """
    lb_30 = WilsonScoreEvaluator.calculate_lower_bound(30, 30)
    assert lb_30 < 0.96
    assert round(lb_30, 4) == 0.8865

    lb_92 = WilsonScoreEvaluator.calculate_lower_bound(92, 92)
    assert lb_92 < 0.96

    lb_93 = WilsonScoreEvaluator.calculate_lower_bound(93, 93)
    assert lb_93 >= 0.96


def test_scenario_08_zero_denominator_no_fabrication():
    """
    Scenario 8: Zero-denominator / Zero-evaluation math:
    When total evaluated reviews or FP predictions are zero, empirical accuracy
    and Wilson lower bounds must be None, never fabricated.
    """
    profile = RuleLearningProfile(
        rule_id="test-zero-eval-rule",
        rule_identifier="RULE_TEST_ZERO",
        customer="DEFAULT",
        total_analyst_reviews=0,
        verified_fp_count=0,
        verified_tp_count=0,
        ai_correct_count=0,
        ai_incorrect_count=0,
    )
    RuleLearningService._recalculate_profile_metrics(profile)
    assert profile.empirical_accuracy is None
    assert profile.fp_precision is None
    assert profile.tp_recall is None
    assert profile.wilson_lower_bound is None


@pytest.mark.asyncio
async def test_scenario_09_decoupled_lifecycle_statuses():
    """
    Scenario 9: Decoupled 4-part lifecycle separation:
    SIEM deployment status 'ACTIVE' does not automatically mean AI Execution is 'Enabled'.
    When candidate version is DRAFT or baseline requires revalidation, AI Execution is 'Suspended'.
    """
    async with AsyncSessionLocal() as db:
        res = await ProductionReadinessService.evaluate_readiness(
            db,
            rule_identifier=HEAVY_TCP_RULE_ID,
            version_id=HEAVY_TCP_V3_ID,
        )
        assert res.rule_deployment_status == "ACTIVE"
        assert res.ai_execution_status == "Suspended"
        assert res.readiness_status == ReadinessStatus.BLOCKED


@pytest.mark.asyncio
async def test_scenario_10_smart_next_action_root_dependency():
    """
    Scenario 10: Smart Next Action prioritizes root blocking dependency.
    When detection definition is incomplete (Stage 1), Smart Action points to
    FortiSIEM detection semantics, not downstream stages.
    """
    async with AsyncSessionLocal() as db:
        res = await ProductionReadinessService.evaluate_readiness(
            db,
            rule_identifier=HEAVY_TCP_RULE_ID,
            version_id=HEAVY_TCP_V3_ID,
        )
        assert res.recommended_action is not None
        assert "Semantics" in res.recommended_action.title or "Define" in res.recommended_action.title
        assert res.recommended_action.target_tab == "advanced"


# ==============================================================================
# BLIND REVIEW SECURITY SCENARIOS (11–17)
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_11_unsubmitted_analyst_blind_review_masking():
    """
    Scenario 11: Unsubmitted Analyst GET /api/incidents?blind_review=true:
    ai_verdict is None, historical_resolution is masked.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_access_token({"sub": ANALYST_USER_ID, "username": "analyst", "role": "SOC Analyst"})
        res = await client.get("/api/incidents?blind_review=true&page=1&page_size=5", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert len(data["items"]) > 0
        for item in data["items"]:
            # Check if this incident has an analyst review for THIS user
            async with AsyncSessionLocal() as db:
                rev_q = select(AnalystVerdictReview).where(
                    (AnalystVerdictReview.incident_id == item["id"]) &
                    (AnalystVerdictReview.reviewer_id.in_([ANALYST_USER_ID, "analyst"]))
                )
                rev_res = await db.execute(rev_q)
                has_rev = rev_res.scalar_one_or_none() is not None

            if not has_rev:
                assert item["ai_verdict"] is None
                assert item["historical_resolution"] == "[Hidden - Blind Review]"


@pytest.mark.asyncio
async def test_scenario_12_submitted_analyst_disclosure():
    """
    Scenario 12: Submitted Analyst GET /api/incidents?blind_review=true:
    When an analyst has submitted a review for an incident, the ai_verdict is revealed to THEM.
    """
    async with AsyncSessionLocal() as db:
        service = IncidentService(db)
        # Find an incident that has an actual AI verdict in DB
        inc_q = select(Incident).where(Incident.ai_verdict.isnot(None))
        inc_res = await db.execute(inc_q)
        sample_inc = inc_res.scalars().first()
        assert sample_inc is not None

        analyst_user = User(id="analyst-user-submitted-12", username="analyst12", role="SOC Analyst")

        # Submit analyst review for this analyst
        rev = AnalystVerdictReview(
            incident_id=sample_inc.id,
            rule_id=sample_inc.rule_id or "PH_RULE_TEST",
            reviewer_id=analyst_user.id,
            analyst_verdict="TRUE_POSITIVE",
            analyst_notes="Verified malicious TCP sequence",
        )
        db.add(rev)
        await db.commit()

        # Fetch incident with current_user = analyst_user
        detail = await service.get_incident(sample_inc.incident_id, blind_review=True, current_user=analyst_user)
        assert detail is not None
        assert detail.ai_verdict is not None
        assert detail.ai_verdict == sample_inc.ai_verdict


@pytest.mark.asyncio
async def test_scenario_13_second_analyst_isolation():
    """
    Scenario 13: Second Analyst (unsubmitted on that incident) GET /api/incidents?blind_review=true:
    Reviewer-specific disclosure: One analyst submitting a review does NOT disclose
    the verdict to a second analyst who has not yet submitted.
    """
    async with AsyncSessionLocal() as db:
        service = IncidentService(db)
        # Find an incident with an AI verdict
        inc_q = select(Incident).where(Incident.ai_verdict.isnot(None))
        inc_res = await db.execute(inc_q)
        sample_inc = inc_res.scalars().first()
        assert sample_inc is not None

        # Analyst A submitted
        analyst_a = User(id="analyst-submitted-A", username="analyst_A", role="SOC Analyst")
        rev = AnalystVerdictReview(
            incident_id=sample_inc.id,
            rule_id=sample_inc.rule_id or "PH_RULE_TEST",
            reviewer_id=analyst_a.id,
            analyst_verdict="FALSE_POSITIVE",
            analyst_notes="Benign internal scanner",
        )
        db.add(rev)
        await db.commit()

        # Analyst B has NOT submitted
        analyst_b = User(id="analyst-unsubmitted-B", username="analyst_B", role="SOC Analyst")
        detail_for_b = await service.get_incident(sample_inc.incident_id, blind_review=True, current_user=analyst_b)
        assert detail_for_b is not None
        assert detail_for_b.ai_verdict is None, "AI verdict leaked to unsubmitted Analyst B!"


@pytest.mark.asyncio
async def test_scenario_14_read_only_viewer_masking():
    """
    Scenario 14: Read-Only Viewer GET /api/incidents?blind_review=true:
    Read-Only Viewers do not submit blind reviews; verdicts remain masked.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_access_token({"sub": VIEWER_USER_ID, "username": "viewer", "role": "Read-Only Viewer"})
        res = await client.get("/api/incidents?blind_review=true&page=1&page_size=5", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        for item in res.json()["items"]:
            assert item["ai_verdict"] is None


@pytest.mark.asyncio
async def test_scenario_15_no_orm_mutation_guarantee():
    """
    Scenario 15: Blind Review requests NEVER mutate SQLAlchemy ORM entities.
    Verify that querying with blind_review=True does not overwrite the persisted
    ai_verdict attribute in the database session.
    """
    async with AsyncSessionLocal() as db:
        service = IncidentService(db)
        # Get an incident with an AI verdict
        inc_q = select(Incident).where(Incident.ai_verdict.isnot(None))
        inc_res = await db.execute(inc_q)
        db_inc = inc_res.scalars().first()
        assert db_inc is not None
        original_verdict = db_inc.ai_verdict

        # Call get_incident with blind_review=True and unsubmitted user
        unsub_user = User(id="temp-user-no-review", username="temp", role="SOC Analyst")
        dto = await service.get_incident(db_inc.incident_id, blind_review=True, current_user=unsub_user)
        assert dto.ai_verdict is None

        # Check the ORM entity in the session
        assert db_inc.ai_verdict == original_verdict, "ORM entity ai_verdict was mutated in memory!"

        # Query database again in fresh transaction
        fresh_res = await db.execute(select(Incident.ai_verdict).where(Incident.incident_id == db_inc.incident_id))
        persisted_verdict = fresh_res.scalar_one_or_none()
        assert persisted_verdict == original_verdict, "Database persisted ai_verdict was overwritten!"


@pytest.mark.asyncio
async def test_scenario_16_incident_detail_blind_review_masking():
    """
    Scenario 16: Masked incident detail endpoint GET /api/incidents/{id}?blind_review=true
    returns masked fields for unsubmitted user.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_access_token({"sub": ANALYST_USER_ID, "username": "analyst", "role": "SOC Analyst"})
        list_res = await client.get("/api/incidents?page=1&page_size=5", headers={"Authorization": f"Bearer {token}"})
        assert list_res.status_code == 200
        inc_id = list_res.json()["items"][0]["incident_id"]

        detail_res = await client.get(f"/api/incidents/{inc_id}?blind_review=true", headers={"Authorization": f"Bearer {token}"})
        assert detail_res.status_code == 200
        detail_data = detail_res.json()
        # If unreviewed by analyst-user-002:
        async with AsyncSessionLocal() as db:
            rev_q = select(AnalystVerdictReview).where(
                (AnalystVerdictReview.incident_id == detail_data["id"]) &
                (AnalystVerdictReview.reviewer_id.in_([ANALYST_USER_ID, "analyst"]))
            )
            rev_res = await db.execute(rev_q)
            has_rev = rev_res.scalar_one_or_none() is not None

        if not has_rev:
            assert detail_data["ai_verdict"] is None
            assert detail_data["ground_truth"] is None


@pytest.mark.asyncio
async def test_scenario_17_review_submission_immediate_unmasking():
    """
    Scenario 17: Submitting an analyst review stores the review and immediately
    unmasks the AI verdict for that submitting analyst on subsequent queries.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_access_token({"sub": ANALYST_USER_ID, "username": "analyst", "role": "SOC Analyst"})
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Fetch an incident with an AI verdict and clear existing reviews for this specific test
        async with AsyncSessionLocal() as db:
            from sqlalchemy import delete
            inc_q = select(Incident).where(Incident.ai_verdict.isnot(None))
            inc_res = await db.execute(inc_q)
            sample_inc = inc_res.scalars().first()
            assert sample_inc is not None
            inc_db_id = sample_inc.id
            inc_business_id = sample_inc.incident_id

            # Clear reviews on this incident so we test pristine unmasking
            await db.execute(delete(AnalystVerdictReview).where(
                (AnalystVerdictReview.incident_id == inc_db_id) |
                (AnalystVerdictReview.incident_id == str(inc_business_id))
            ))
            await db.commit()

        # 2. Submit analyst review via /api/reviews/{incident_id}/submit
        review_payload = {
            "analyst_verdict": "TRUE_POSITIVE",
            "analyst_notes": "Immediate unmasking verification test",
            "blind_mode_active": True,
        }
        submit_res = await client.post(f"/api/reviews/{inc_db_id}/submit", json=review_payload, headers=headers)
        assert submit_res.status_code in (200, 201)

        # 3. Query detail again for this analyst -> AI verdict must now be revealed
        post_res = await client.get(f"/api/incidents/{inc_business_id}?blind_review=true", headers=headers)
        assert post_res.status_code == 200
        post_data = post_res.json()
        assert post_data["ai_verdict"] is not None
