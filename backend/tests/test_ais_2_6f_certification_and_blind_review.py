"""
AIS 2.6f Regression & Security Certification Suite:
Covers queue population separation, server-side blind review enforcement across all
endpoints, handover note sanitization, GT-0/GT-1/GT-2/GT-3/Conflict/Adjudication/Revision
state machine, self-approval/duplicate lock blocks, RAG/LearningRecord isolation, and
benchmark harness consumption of certified GT.
"""

import json
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from app.models.analyst_feedback import (
    AnalystVerdictReview,
    BenchmarkCohortItem,
    BenchmarkReviewRevision,
)
from app.models.incident import HistoricalGroundTruth, Incident, IncidentEvent
from app.models.investigation import Investigation
from app.models.learning import LearningRecord
from app.models.rule import Rule
from app.models.user import User
from app.services.blind_review_guard import (
    FROZEN_AIS_2_6E_COHORT_ID,
    PRIORITY_5_INCIDENT_IDS,
    has_ai_notes_contamination,
    strip_ai_notes_from_handover,
)
from app.services.empirical_benchmark_harness import EmpiricalBenchmarkHarness
from app.services.ground_truth_certification_service import GroundTruthCertificationService
from app.services.learning_service import AgentMemoryEngine
from app.services.verified_semantic_retrieval_service import VerifiedSemanticRetrievalService
from app.utils.security import create_access_token, get_password_hash


async def _make_user(
    db: AsyncSession,
    username: str,
    role: str,
    customer: str = "DEFAULT",
) -> tuple[User, str]:
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password=get_password_hash("TestPass123!"),
        full_name=username,
        role=role,
        is_active=True,
        customer=customer,
    )
    db.add(user)
    await db.flush()
    token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role, "customer": user.customer}
    )
    return user, token


def test_strip_ai_notes_preserves_human_handover_notes():
    contaminated = (
        "Checked ticket CHG-4410 for IT maintenance.\n\n"
        "[AI Verdict (REQUIRES_ATTENTION - 0%)]: Evidence completeness failed for UltraViewer.\n\n"
        "Verified endpoint hostname PC-TSI-DC."
    )
    assert has_ai_notes_contamination(contaminated) is True
    cleaned = strip_ai_notes_from_handover(contaminated)
    assert "[AI Verdict" not in cleaned
    assert "REQUIRES_ATTENTION" not in cleaned
    assert "CHG-4410" in cleaned
    assert "PC-TSI-DC" in cleaned
    assert has_ai_notes_contamination(cleaned) is False


@pytest.mark.asyncio
async def test_frozen_cohort_registration_and_operational_queue_separation(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
):
    # Create an unrelated operational rule/incident (like PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST)
    op_rule = Rule(
        rule_id="PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST",
        name="Website access policy violation: Same Source and Destination",
        event_type="PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST",
        severity="LOW",
        description="Operational web policy rule",
    )
    db_session.add(op_rule)
    await db_session.flush()

    op_inc = Incident(
        incident_id="13031",
        rule_id=op_rule.id,
        title="Website access policy violation: Same Source and Destination",
        event_type="PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST",
        severity="LOW",
        customer="DEFAULT",
    )
    db_session.add(op_inc)
    await db_session.commit()

    # Register AIS 2.6e frozen 20 cohort (loads from fixtures/Incident json.zip if missing in DB)
    cohort = await GroundTruthCertificationService.ensure_ais_2_6e_cohort_registered(db_session)
    assert cohort.cohort_key == FROZEN_AIS_2_6E_COHORT_ID
    assert cohort.excluded_from_learning is True

    # Operational queue has operational + ingested incidents + DB-wide aggregates
    op_res = await client.get(
        "/api/investigations/queue?blind_review=true&page_size=20",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert op_res.status_code == 200
    op_data = op_res.json()
    assert op_data["status_counts"] is not None
    assert op_data["status_counts"]["pending_review"] >= 1
    assert op_data["status_counts"]["total"] == op_data["total"]

    # Ground Truth Certification queue contains strictly the 20 frozen benchmark incidents
    gt_res = await client.get(
        f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/queue",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert gt_res.status_code == 200
    gt_data = gt_res.json()
    assert gt_data["total"] == 20
    returned_fids = [x["fortisiem_incident_id"] for x in gt_data["items"]]
    assert "13031" not in returned_fids
    for pid in PRIORITY_5_INCIDENT_IDS:
        assert pid in returned_fids

    # Priority filter shows strictly the 5 Priority Pilot items
    p_res = await client.get(
        f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/queue?priority_only=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert p_res.status_code == 200
    p_data = p_res.json()
    assert p_data["total"] == 5
    assert [x["fortisiem_incident_id"] for x in p_data["items"]] == PRIORITY_5_INCIDENT_IDS


@pytest.mark.asyncio
async def test_blind_review_masking_across_admin_and_analyst_endpoints(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
):
    _, analyst_token = await _make_user(db_session, "blind_analyst_a", "SOC Analyst", customer="Tosoh")
    await GroundTruthCertificationService.ensure_ais_2_6e_cohort_registered(db_session)

    inc = (
        await db_session.execute(select(Incident).where(Incident.incident_id == "132474210"))
    ).scalars().first()
    assert inc is not None

    # Inject simulated legacy AI verdict, contaminated handover notes, and historical FortiSIEM label
    inc.ai_verdict = {
        "verdict": "TRUE_POSITIVE",
        "proposed_verdict": "TRUE_POSITIVE",
        "validated_verdict": "REQUIRES_ATTENTION",
        "confidence": 82,
        "trust_score": 4,
        "reason": "SECRET_AI_REASON_MUST_NOT_LEAK",
        "pilot_mode": "ANALYST_ASSISTED",
    }
    db_session.add(inc)
    gt_existing = (
        await db_session.execute(
            select(HistoricalGroundTruth).where(HistoricalGroundTruth.incident_id == inc.id)
        )
    ).scalars().first()
    if not gt_existing:
        db_session.add(
            HistoricalGroundTruth(
                incident_id=inc.id,
                resolution="False Positive",
                cleared_reason="SECRET_HISTORICAL_RESOLUTION_MUST_NOT_LEAK",
                is_ml_generated=True,
            )
        )
    else:
        gt_existing.resolution = "False Positive"
        gt_existing.cleared_reason = "SECRET_HISTORICAL_RESOLUTION_MUST_NOT_LEAK"
        gt_existing.is_ml_generated = True
        db_session.add(gt_existing)
    inv = (
        await db_session.execute(select(Investigation).where(Investigation.incident_id == inc.id))
    ).scalars().first()
    if not inv:
        inv = Investigation(
            incident_id=inc.id,
            status="PENDING_REVIEW",
            analyst_notes="Real analyst observation.\n\n[AI Verdict (REQUIRES_ATTENTION - 0%)]: SECRET_AI_REASON_MUST_NOT_LEAK",
        )
        db_session.add(inv)
    else:
        inv.analyst_notes = "Real analyst observation.\n\n[AI Verdict (REQUIRES_ATTENTION - 0%)]: SECRET_AI_REASON_MUST_NOT_LEAK"
    await db_session.commit()

    # 1. Operational queue & detail with blind_review=true MUST mask EVEN for Administrator!
    q_admin = await client.get(
        "/api/investigations/queue?blind_review=true&search=132474210",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert q_admin.status_code == 200
    q_item = q_admin.json()["items"][0]
    assert q_item["ai_validated_verdict"] is None
    assert q_item["ai_trust_score"] is None
    assert q_item["pilot_mode"] is None

    det_admin = await client.get(
        f"/api/investigations/{inv.id}?blind_review=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert det_admin.status_code == 200
    det_json = det_admin.json()
    assert det_json["ai_assurance"]["validated_verdict"] is None
    assert det_json["ai_assurance"]["proposed_verdict"] is None
    assert "SECRET_AI_REASON_MUST_NOT_LEAK" not in det_json["analyst_notes"]
    assert "[AI Verdict" not in det_json["analyst_notes"]
    assert "Real analyst observation." in det_json["analyst_notes"]

    # 2. Timeline endpoint with blind_review=true masks Milestone 6 & 7 for Admin
    tl_admin = await client.get(
        f"/api/incidents/132474210/timeline?blind_review=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert tl_admin.status_code == 200
    tl_text = json.dumps(tl_admin.json())
    assert "SECRET_AI_REASON_MUST_NOT_LEAK" not in tl_text
    assert "SECRET_HISTORICAL_RESOLUTION_MUST_NOT_LEAK" not in tl_text

    # 3. Ground Truth Certification detail endpoint NEVER reveals AI or Historical labels even to Admin
    gt_det = await client.get(
        f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/incidents/132474210",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert gt_det.status_code == 200
    gt_payload_str = json.dumps(gt_det.json())
    assert "SECRET_AI_REASON_MUST_NOT_LEAK" not in gt_payload_str
    assert "SECRET_HISTORICAL_RESOLUTION_MUST_NOT_LEAK" not in gt_payload_str
    assert gt_det.json()["blind_review_guarantees"]["ai_verdict_hidden"] is True
    assert gt_det.json()["blind_review_guarantees"]["historical_fortisiem_label_hidden"] is True
    assert len(gt_det.json()["raw_logs"]) >= 1

    # 4. Analyst cannot bypass via blind_review=false on incidents timeline or AIS history
    ais_hist = await client.get(
        "/api/ais/incidents/132474210/evaluation-history?blind_review=true",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert ais_hist.status_code == 200

    # 5. Post-certification comparison endpoint fails closed (403) before GT-3 completion
    comp_res = await client.get(
        f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/incidents/132474210/post-certification-comparison",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert comp_res.status_code == 403


@pytest.mark.asyncio
async def test_certification_state_machine_and_learning_isolation(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
):
    _, rev1_token = await _make_user(db_session, "reviewer_one", "SOC Analyst")
    _, rev2_token = await _make_user(db_session, "reviewer_two", "SOC Analyst")
    await db_session.commit()

    await GroundTruthCertificationService.ensure_ais_2_6e_cohort_registered(db_session)

    base_payload = {
        "human_verdict": "FALSE_POSITIVE",
        "detection_correctness": "NOT_MATCHED",
        "authorization_context": "AUTHORIZED",
        "confidence_level": "HIGH",
        "evidence_sufficiency_status": "SUFFICIENT",
        "rationale": "Confirmed authorized UltraViewer IT support session verified via host telemetry.",
        "evidence_references": ["proc: UltraViewer_Service.exe", "host: PC-TSI-DC"],
        "attestation_flags": {
            "evidence_reviewed": True,
            "no_ai_or_historical_influence": True,
            "independent_judgment": True,
        },
    }

    # 1. Draft save keeps IN_PROGRESS and does not advance GT-2
    draft_res = await client.post(
        f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/incidents/132474210/review",
        json={**base_payload, "mode": "DRAFT"},
        headers={"Authorization": f"Bearer {rev1_token}"},
    )
    assert draft_res.status_code == 200
    assert draft_res.json()["certification_status"] == "IN_PROGRESS"

    # 2. Missing attestation rejected on LOCK
    bad_lock = await client.post(
        f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/incidents/132474210/review",
        json={
            **base_payload,
            "mode": "LOCK",
            "attestation_flags": {
                "evidence_reviewed": True,
                "no_ai_or_historical_influence": False,
                "independent_judgment": True,
            },
        },
        headers={"Authorization": f"Bearer {rev1_token}"},
    )
    assert bad_lock.status_code == 400

    # 3. Reviewer 1 Locks -> GT2_SINGLE_REVIEW (certified_verdict stays None)
    lock1 = await client.post(
        f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/incidents/132474210/review",
        json={**base_payload, "mode": "LOCK"},
        headers={"Authorization": f"Bearer {rev1_token}"},
    )
    assert lock1.status_code == 200
    assert lock1.json()["certification_status"] == "GT2_SINGLE_REVIEW"
    assert lock1.json()["certified_verdict"] is None
    assert lock1.json()["excluded_from_learning"] is True

    # 4. Self-approval blocked cleanly (409)
    self_dup = await client.post(
        f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/incidents/132474210/review",
        json={**base_payload, "mode": "LOCK"},
        headers={"Authorization": f"Bearer {rev1_token}"},
    )
    assert self_dup.status_code == 409

    # 5. Reviewer 2 viewing detail does NOT see Reviewer 1's verdict while uncertified
    det_rev2 = await client.get(
        f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/incidents/132474210",
        headers={"Authorization": f"Bearer {rev2_token}"},
    )
    assert det_rev2.status_code == 200
    assert det_rev2.json()["other_reviewer_submitted"] is True
    assert det_rev2.json()["conflict_reviews"] == []

    # 6. Reviewer 2 agrees & locks FALSE_POSITIVE -> GT3_CERTIFIED!
    lock2 = await client.post(
        f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/incidents/132474210/review",
        json={**base_payload, "mode": "LOCK"},
        headers={"Authorization": f"Bearer {rev2_token}"},
    )
    assert lock2.status_code == 200
    assert lock2.json()["certification_status"] == "GT3_CERTIFIED"
    assert lock2.json()["certified_verdict"] == "FALSE_POSITIVE"

    # 7. Conflict workflow on 132596403: Rev1=TP, Rev2=FP -> CONFLICT_PENDING_ADJUDICATION -> Admin adjudicates TP
    await client.post(
        f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/incidents/132596403/review",
        json={**base_payload, "human_verdict": "TRUE_POSITIVE", "mode": "LOCK"},
        headers={"Authorization": f"Bearer {rev1_token}"},
    )
    c_res = await client.post(
        f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/incidents/132596403/review",
        json={**base_payload, "human_verdict": "FALSE_POSITIVE", "mode": "LOCK"},
        headers={"Authorization": f"Bearer {rev2_token}"},
    )
    assert c_res.json()["certification_status"] == "CONFLICT_PENDING_ADJUDICATION"

    adj_res = await client.post(
        f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/incidents/132596403/adjudicate",
        json={
            "final_verdict": "TRUE_POSITIVE",
            "rationale": "Senior adjudication confirmed unauthorized payload transfer in gateway logs.",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert adj_res.status_code == 200
    assert adj_res.json()["certification_status"] == "GT3_CERTIFIED"
    assert adj_res.json()["certified_verdict"] == "TRUE_POSITIVE"

    # 8. Inconclusive dual agreement on 132599145 -> CERTIFIED_INCONCLUSIVE
    await client.post(
        f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/incidents/132599145/review",
        json={**base_payload, "human_verdict": "INCONCLUSIVE", "mode": "LOCK"},
        headers={"Authorization": f"Bearer {rev1_token}"},
    )
    inc_res = await client.post(
        f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/incidents/132599145/review",
        json={**base_payload, "human_verdict": "INCONCLUSIVE", "mode": "LOCK"},
        headers={"Authorization": f"Bearer {rev2_token}"},
    )
    assert inc_res.json()["certification_status"] == "CERTIFIED_INCONCLUSIVE"
    assert inc_res.json()["certified_verdict"] == "INCONCLUSIVE"

    # 9. Reopen Revision by Admin creates immutable BenchmarkReviewRevision record
    rev1_row_id = lock1.json()["review_id"]
    reopen_res = await client.post(
        f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/reviews/reopen",
        json={
            "review_id": rev1_row_id,
            "new_verdict": "FALSE_POSITIVE",
            "new_rationale": "Admin verified IT change ticket reference updated cleanly in revision.",
            "revision_reason": "Append verified change request identifier without altering verdict.",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert reopen_res.status_code == 200
    revs_q = await db_session.execute(
        select(BenchmarkReviewRevision).where(BenchmarkReviewRevision.review_id == rev1_row_id)
    )
    assert revs_q.scalar_one_or_none() is not None

    # 10. Strict Learning / RAG Isolation: ZERO LearningRecord entries for ANY frozen cohort incident!
    lr_rows = (await db_session.execute(select(LearningRecord))).scalars().all()
    assert len(lr_rows) == 0

    # Even seeding from historical incidents must NEVER ingest frozen benchmark cohort items!
    cohort_items = (await db_session.execute(select(BenchmarkCohortItem))).scalars().all()
    first_inc = (
        await db_session.execute(select(Incident).where(Incident.incident_id == "132474210"))
    ).scalars().first()
    existing_gt = (
        await db_session.execute(
            select(HistoricalGroundTruth).where(HistoricalGroundTruth.incident_id == first_inc.id)
        )
    ).scalars().first()
    if not existing_gt:
        db_session.add(
            HistoricalGroundTruth(
                incident_id=first_inc.id,
                resolution="False Positive",
                cleared_reason="Legacy SIEM label",
                is_ml_generated=False,
            )
        )
    else:
        existing_gt.resolution = "False Positive"
        existing_gt.cleared_reason = "Legacy SIEM label"
        existing_gt.is_ml_generated = False
        db_session.add(existing_gt)
    await db_session.commit()

    seeded_cnt = await AgentMemoryEngine(db_session).seed_verified_cases_from_historical_incidents()
    assert seeded_cnt == 0

    rag_res = await VerifiedSemanticRetrievalService.retrieve_verified_precedents(
        db_session, first_inc, first_inc.rule_id or "PH_RULE_CS_SUSPICIOUS_ACTIVITY"
    )
    assert len(rag_res.precedents) == 0

    # 11. Empirical Benchmark Harness consumes ONLY GT3_CERTIFIED TP/FP (keeps CERTIFIED_INCONCLUSIVE separate)
    gt2_only_item = (
        await client.post(
            f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/incidents/132438483/review",
            json={**base_payload, "human_verdict": "TRUE_POSITIVE", "mode": "LOCK"},
            headers={"Authorization": f"Bearer {rev1_token}"},
        )
    )
    assert gt2_only_item.json()["certification_status"] == "GT2_SINGLE_REVIEW"

    recs_strict, summary_strict = await EmpiricalBenchmarkHarness.load_certified_ground_truth_cohort(
        db_session, FROZEN_AIS_2_6E_COHORT_ID, include_gt2_exploratory=False
    )
    assert summary_strict["gt3_certified"] == 2
    assert summary_strict["certified_inconclusive"] == 1
    assert summary_strict["gt2_single_review"] == 1
    strict_map = {r.incident_id: r.ground_truth_label for r in recs_strict}
    assert strict_map["132474210"] == "VERIFIED_FP"
    assert strict_map["132596403"] == "VERIFIED_TP"
    assert strict_map["132599145"] == "CERTIFIED_INCONCLUSIVE"
    assert strict_map["132438483"] == "UNVERIFIED"  # GT-2 excluded from authoritative GT-3 metrics!

    # Exploratory flag allows GT-2 inclusion when explicitly requested
    recs_exp, _ = await EmpiricalBenchmarkHarness.load_certified_ground_truth_cohort(
        db_session, FROZEN_AIS_2_6E_COHORT_ID, include_gt2_exploratory=True
    )
    exp_map = {r.incident_id: r.ground_truth_label for r in recs_exp}
    assert exp_map["132438483"] == "VERIFIED_TP"

    # Harness policy lookup returns reconciled AIS 2.6e approved v1 IDs
    cs_pv = EmpiricalBenchmarkHarness._lookup_approved_prompt_version("PH_RULE_CS_SUSPICIOUS_ACTIVITY", db_path="__nonexistent__.db")
    ps_pv = EmpiricalBenchmarkHarness._lookup_approved_prompt_version("PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE", db_path="__nonexistent__.db")
    assert cs_pv.id == "bd751fac-9bfb-4994-b150-8850bb94dd6c"
    assert cs_pv.prompt_id == "08c59656-c002-4a76-b100-3c8d6d645eb2"
    assert ps_pv.id == "8ae7beaa-626a-4061-a0c4-8500f7e6a69d"
    assert ps_pv.prompt_id == "1fe4e834-bd52-4571-95ca-ee329e40e1b2"


@pytest.mark.asyncio
async def test_unlock_review_option_1_policy(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
):
    _, rev1_token = await _make_user(db_session, "unlock_rev1", "SOC Analyst")
    _, rev2_token = await _make_user(db_session, "unlock_rev2", "SOC Analyst")
    await db_session.commit()

    await GroundTruthCertificationService.ensure_ais_2_6e_cohort_registered(db_session)

    base_payload = {
        "human_verdict": "TRUE_POSITIVE",
        "detection_correctness": "MATCHED",
        "authorization_context": "UNAUTHORIZED",
        "confidence_level": "HIGH",
        "evidence_sufficiency_status": "SUFFICIENT",
        "rationale": "Initial classification before realizing evidence mismatch.",
        "evidence_references": ["host: PC-TSI-DC"],
        "attestation_flags": {
            "evidence_reviewed": True,
            "no_ai_or_historical_influence": True,
            "independent_judgment": True,
        },
    }

    # 1. Reviewer 1 locks -> GT2_SINGLE_REVIEW, can_unlock_my_review=True
    lock1 = await client.post(
        f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/incidents/132438483/review",
        json={**base_payload, "mode": "LOCK"},
        headers={"Authorization": f"Bearer {rev1_token}"},
    )
    assert lock1.status_code == 200
    assert lock1.json()["certification_status"] == "GT2_SINGLE_REVIEW"
    rev1_id = lock1.json()["review_id"]

    det1 = await client.get(
        f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/incidents/132438483",
        headers={"Authorization": f"Bearer {rev1_token}"},
    )
    assert det1.status_code == 200
    assert det1.json()["can_unlock_my_review"] is True
    assert det1.json()["can_submit_lock"] is False

    # 2. Reviewer 1 unlocks their own review while still GT2_SINGLE_REVIEW -> reverts to DRAFT
    unlock1 = await client.post(
        f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/incidents/132438483/review/unlock",
        json={"reason": "Marked wrong verdict by mistake"},
        headers={"Authorization": f"Bearer {rev1_token}"},
    )
    assert unlock1.status_code == 200
    u_data = unlock1.json()
    assert u_data["is_locked"] is False
    assert u_data["is_draft"] is True
    assert u_data["certification_status"] == "IN_PROGRESS"
    assert u_data["locked_reviewers_count"] == 0

    # 3. Reviewer 1 updates verdict to FALSE_POSITIVE and re-locks
    relock1 = await client.post(
        f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/incidents/132438483/review",
        json={**base_payload, "human_verdict": "FALSE_POSITIVE", "mode": "LOCK"},
        headers={"Authorization": f"Bearer {rev1_token}"},
    )
    assert relock1.status_code == 200
    assert relock1.json()["certification_status"] == "GT2_SINGLE_REVIEW"

    # 4. Reviewer 2 locks FALSE_POSITIVE -> GT3_CERTIFIED
    lock2 = await client.post(
        f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/incidents/132438483/review",
        json={**base_payload, "human_verdict": "FALSE_POSITIVE", "mode": "LOCK"},
        headers={"Authorization": f"Bearer {rev2_token}"},
    )
    assert lock2.status_code == 200
    assert lock2.json()["certification_status"] == "GT3_CERTIFIED"
    rev2_id = lock2.json()["review_id"]

    # 5. Non-admin Reviewer 1 cannot unlock once GT3_CERTIFIED (403) or unlock Reviewer 2 (403)
    det_after_gt3 = await client.get(
        f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/incidents/132438483",
        headers={"Authorization": f"Bearer {rev1_token}"},
    )
    assert det_after_gt3.json()["can_unlock_my_review"] is False
    assert det_after_gt3.json()["unlock_blocked_reason"] is not None

    blocked_unlock = await client.post(
        f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/incidents/132438483/review/unlock",
        json={"reason": "Want to change after GT3"},
        headers={"Authorization": f"Bearer {rev1_token}"},
    )
    assert blocked_unlock.status_code == 403

    other_unlock = await client.post(
        f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/incidents/132438483/review/unlock",
        json={"reason": "Try unlocking peer", "review_id": rev2_id},
        headers={"Authorization": f"Bearer {rev1_token}"},
    )
    assert other_unlock.status_code == 403

    # 6. Admin can unlock even after GT3_CERTIFIED -> reverts to GT2_SINGLE_REVIEW & clears certified_verdict
    admin_unlock = await client.post(
        f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/incidents/132438483/review/unlock",
        json={"reason": "Admin approved correction", "review_id": rev1_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_unlock.status_code == 200
    assert admin_unlock.json()["certification_status"] == "GT2_SINGLE_REVIEW"
    assert admin_unlock.json()["locked_reviewers_count"] == 1

    det_after_admin = await client.get(
        f"/api/ground-truth/cohorts/{FROZEN_AIS_2_6E_COHORT_ID}/incidents/132438483",
        headers={"Authorization": f"Bearer {rev1_token}"},
    )
    assert det_after_admin.json()["cohort_item"]["certified_verdict"] is None
    assert det_after_admin.json()["can_submit_lock"] is True
    assert any(r["new_verdict"] == "UNLOCKED_TO_DRAFT" for r in det_after_admin.json()["revisions"])
