"""
Target Rule: Heavy TCP Host Scan On Fixed Port (UUID: 40498741-ee6b-4a71-9101-0d6d3f77154c)
AIS 2.0 Incident-Level AI Evaluation Tracking & Controlled Inference Management Tests
Covers all 20 required verification scenarios from Phase 8.
"""

import uuid
import datetime
from typing import Optional, Dict, Any
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, delete, or_

from app.main import app
from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.rule import Rule
from app.models.prompt import RulePrompt, PromptVersion
from app.models.incident import Incident
from app.models.actual_prompt_capture import ActualLLMPromptCapture
from app.models.verdict_intelligence import VerdictTrustAssessmentRecord
from app.models.analyst_feedback import AnalystVerdictReview
from app.services.ais_evaluation_service import (
    AisEvaluationService,
    STATUS_NOT_EVALUATED,
    STATUS_EVALUATED_DECISIVE,
    STATUS_ABSTAINED,
    STATUS_VALIDATION_REJECTED,
    STATUS_EVALUATION_FAILED,
)
from app.utils.security import get_password_hash, create_access_token

RULE_UUID = "40498741-ee6b-4a71-9101-0d6d3f77154c"
RULE_EVENT_TYPE = "PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT"
RULE_NAME = "Heavy TCP Host Scan On Fixed Port"

ADMIN_USER_ID = "u-admin-eval-test"
ANALYST_USER_ID = "u-analyst-eval-test"
OTHER_TENANT_USER_ID = "u-other-tenant-eval-test"

V7_VERSION_ID = "pv-eval-v7-" + uuid.uuid4().hex[:8]
V8_VERSION_ID = "pv-eval-v8-" + uuid.uuid4().hex[:8]


def create_token(user_id: str, username: str, role: str, customer: str = "DEFAULT") -> str:
    return create_access_token({"sub": user_id, "username": username, "role": role, "customer": customer})


def make_prompt_capture(
    incident_id: str,
    rule_id: str = RULE_UUID,
    policy_version_number: int = 7,
    policy_version_id: Optional[str] = V7_VERSION_ID,
    dispatch_status: str = "COMPLETED",
    is_simulated: bool = False,
    model_name: str = "Qwen/Qwen2.5-7B-Instruct-AWQ",
    response_verdict: Optional[str] = None,
    response_confidence: Optional[float] = None,
    error_message: Optional[str] = None,
    integrity_details: Optional[Dict[str, Any]] = None,
    captured_at: Optional[datetime.datetime] = None,
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
        dispatch_status=dispatch_status,
        is_simulated=is_simulated,
        model_name=model_name,
        compiled_system_prompt="System Prompt",
        user_message="User Prompt",
        request_sha256="sha-" + uuid.uuid4().hex,
        response_raw=f'{{"verdict": "{response_verdict}"}}' if response_verdict else None,
        response_verdict=response_verdict,
        response_confidence=response_confidence,
        error_message=error_message,
        prompt_integrity_status="VALID" if not error_message else "ERROR",
        integrity_details=integrity_details or {},
        latency_ms=450,
        captured_at=captured_at or datetime.datetime.now(datetime.timezone.utc),
    )


def make_trust_record(
    incident_id: str,
    suggested_verdict: str,
    effective_verdict: str,
    is_simulated: bool = False,
    evaluated_at: Optional[datetime.datetime] = None,
) -> VerdictTrustAssessmentRecord:
    return VerdictTrustAssessmentRecord(
        id=str(uuid.uuid4()),
        incident_id=incident_id,
        rule_id=RULE_UUID,
        suggested_verdict=suggested_verdict,
        effective_verdict=effective_verdict,
        trust_score=8,
        is_simulated=is_simulated,
        evaluated_at=evaluated_at or datetime.datetime.now(datetime.timezone.utc),
    )


# Global tracker to preserve original active version binding across tests
_SAVED_RULE_PROMPT_STATE: Dict[str, Any] = {}


@pytest_asyncio.fixture(autouse=True)
async def setup_test_environment():
    """Seed test rule, prompt versions v7 and v8, test users, and clean test records."""
    async with AsyncSessionLocal() as db:
        # Preserve existing active version binding if present
        rp_existing_res = await db.execute(select(RulePrompt).where(RulePrompt.rule_id == RULE_UUID))
        rp_existing = rp_existing_res.scalar_one_or_none()
        if rp_existing:
            _SAVED_RULE_PROMPT_STATE["active_version_id"] = rp_existing.active_version_id
            _SAVED_RULE_PROMPT_STATE["ai_execution_suspended"] = rp_existing.ai_execution_suspended

        await db.execute(delete(ActualLLMPromptCapture).where(
            or_(
                ActualLLMPromptCapture.incident_id.like("INC-%"),
                ActualLLMPromptCapture.incident_id.like("db-inc-%"),
            )
        ))
        await db.execute(delete(VerdictTrustAssessmentRecord).where(
            or_(
                VerdictTrustAssessmentRecord.incident_id.like("INC-%"),
                VerdictTrustAssessmentRecord.incident_id.like("db-inc-%"),
            )
        ))
        await db.execute(delete(AnalystVerdictReview).where(
            or_(
                AnalystVerdictReview.incident_id.like("INC-%"),
                AnalystVerdictReview.incident_id.like("db-inc-%"),
            )
        ))
        await db.execute(delete(Incident).where(Incident.id.like("db-inc-%")))
        await db.execute(delete(PromptVersion).where(PromptVersion.id.in_([V7_VERSION_ID, V8_VERSION_ID])))
        await db.commit()

        # Seed Users
        users = [
            (ADMIN_USER_ID, "eval_admin", "eval_admin@soc.local", "Administrator", "DEFAULT"),
            (ANALYST_USER_ID, "eval_analyst", "eval_analyst@soc.local", "SOC Analyst", "DEFAULT"),
            (OTHER_TENANT_USER_ID, "eval_other", "eval_other@soc.local", "SOC Analyst", "OTHER_TENANT"),
        ]
        for uid, uname, uemail, urole, ucustomer in users:
            res = await db.execute(select(User).where(User.id == uid))
            existing_user = res.scalar_one_or_none()
            if not existing_user:
                db.add(
                    User(
                        id=uid,
                        username=uname,
                        email=uemail,
                        hashed_password=get_password_hash("Password123!"),
                        role=urole,
                        customer=ucustomer,
                        is_active=True,
                    )
                )
            else:
                existing_user.role = urole
                existing_user.customer = ucustomer

        # Ensure Rule exists
        r_res = await db.execute(select(Rule).where(Rule.id == RULE_UUID))
        rule = r_res.scalar_one_or_none()
        if not rule:
            rule = Rule(
                id=RULE_UUID,
                rule_id=RULE_EVENT_TYPE,
                name=RULE_NAME,
                event_type=RULE_EVENT_TYPE,
                description="Detects fixed port TCP host scan attacks.",
                severity="HIGH",
                status="ACTIVE",
                data_source="FortiSIEM",
            )
            db.add(rule)
            await db.flush()

        # Ensure RulePrompt exists
        rp_res = await db.execute(select(RulePrompt).where(RulePrompt.rule_id == RULE_UUID))
        rp = rp_res.scalar_one_or_none()
        if not rp:
            rp = RulePrompt(
                id=str(uuid.uuid4()),
                rule_id=RULE_UUID,
                title=f"Prompt - {RULE_NAME}",
                ai_execution_suspended=False,
            )
            db.add(rp)
            await db.flush()

        pv7 = PromptVersion(
            id=V7_VERSION_ID,
            prompt_id=rp.id,
            version_number=7,
            status="APPROVED",
            quality_status="APPROVED",
            quality_score=95.0,
            common_prompt="Standard Common Prompt",
            rule_specific_prompt="V7 Rule Specific Prompt",
            change_summary="V7 Approved Baseline",
        )
        pv8 = PromptVersion(
            id=V8_VERSION_ID,
            prompt_id=rp.id,
            version_number=8,
            status="DRAFT",
            quality_status="DRAFT",
            quality_score=92.0,
            common_prompt="Standard Common Prompt",
            rule_specific_prompt="V8 Candidate Prompt with improved edge cases",
            change_summary="V8 Draft Candidate",
        )
        db.add(pv7)
        db.add(pv8)
        rp.active_version_id = pv7.id
        await db.commit()

    yield

    async with AsyncSessionLocal() as db:
        await db.execute(delete(ActualLLMPromptCapture).where(
            or_(
                ActualLLMPromptCapture.incident_id.like("INC-%"),
                ActualLLMPromptCapture.incident_id.like("db-inc-%"),
            )
        ))
        await db.execute(delete(VerdictTrustAssessmentRecord).where(
            or_(
                VerdictTrustAssessmentRecord.incident_id.like("INC-%"),
                VerdictTrustAssessmentRecord.incident_id.like("db-inc-%"),
            )
        ))
        await db.execute(delete(AnalystVerdictReview).where(
            or_(
                AnalystVerdictReview.incident_id.like("INC-%"),
                AnalystVerdictReview.incident_id.like("db-inc-%"),
            )
        ))
        await db.execute(delete(Incident).where(Incident.id.like("db-inc-%")))
        await db.execute(delete(PromptVersion).where(PromptVersion.id.in_([V7_VERSION_ID, V8_VERSION_ID])))

        # Restore original active version binding if it was recorded
        rp_res = await db.execute(select(RulePrompt).where(RulePrompt.rule_id == RULE_UUID))
        rp = rp_res.scalar_one_or_none()
        if rp and "active_version_id" in _SAVED_RULE_PROMPT_STATE:
            rp.active_version_id = _SAVED_RULE_PROMPT_STATE["active_version_id"]
            rp.ai_execution_suspended = _SAVED_RULE_PROMPT_STATE.get("ai_execution_suspended", False)

        await db.commit()


async def seed_incident(inc_id: str, title: str = "Test TCP Scan", customer: str = "DEFAULT") -> Incident:
    async with AsyncSessionLocal() as db:
        inc = Incident(
            id=f"db-inc-{inc_id}",
            incident_id=inc_id,
            rule_id=RULE_UUID,
            event_type=RULE_EVENT_TYPE,
            title=title,
            severity="MEDIUM",
            customer=customer,
            source_ip="172.25.24.150",
            raw_payload={"srcIpAddr": "172.25.24.150", "destPort": 443},
        )
        db.add(inc)
        await db.commit()
        return inc


# -----------------------------------------------------------------------------
# TEST 1: NOT EVALUATED status returned when no evaluation exists
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_01_not_evaluated_status_when_no_execution_exists():
    inc = await seed_incident("INC-001")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = create_token(ADMIN_USER_ID, "eval_admin", "Administrator")
        res = await ac.get(
            f"/api/ais/rules/{RULE_UUID}/evaluation-status?search=INC-001&policy_version_number=7",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["status"] == STATUS_NOT_EVALUATED
        assert item["is_real_inference"] is False
        assert item["badge_color"] == "neutral"
        assert item["effective_verdict"] is None


# -----------------------------------------------------------------------------
# TEST 2: EVALUATED — DECISIVE returned for valid TP/FP inference
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_02_evaluated_decisive_status_for_valid_tp_or_fp_inference():
    inc = await seed_incident("INC-002")
    async with AsyncSessionLocal() as db:
        cap = make_prompt_capture(
            incident_id=inc.incident_id,
            response_verdict="FALSE_POSITIVE",
            response_confidence=92.0,
            integrity_details={"validation_status": "VALIDATED", "is_decisive_accepted": True},
        )
        trust = make_trust_record(
            incident_id=inc.incident_id,
            suggested_verdict="FALSE_POSITIVE",
            effective_verdict="FALSE_POSITIVE",
        )
        db.add(cap)
        db.add(trust)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = create_token(ADMIN_USER_ID, "eval_admin", "Administrator")
        res = await ac.get(
            f"/api/ais/rules/{RULE_UUID}/evaluation-status?search=INC-002&policy_version_number=7",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        item = res.json()["items"][0]
        assert item["status"] == STATUS_EVALUATED_DECISIVE
        assert item["is_real_inference"] is True
        assert item["badge_color"] == "green"
        assert item["effective_verdict"] == "FALSE_POSITIVE"


# -----------------------------------------------------------------------------
# TEST 3: ABSTAINED returned for completed inference with non-decisive effective verdict
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_03_abstained_status_for_requires_attention():
    inc = await seed_incident("INC-003")
    async with AsyncSessionLocal() as db:
        cap = make_prompt_capture(
            incident_id=inc.incident_id,
            response_verdict="REQUIRES_ATTENTION",
            response_confidence=40.0,
            integrity_details={"validation_status": "VALIDATED", "is_decisive_accepted": False},
        )
        trust = make_trust_record(
            incident_id=inc.incident_id,
            suggested_verdict="REQUIRES_ATTENTION",
            effective_verdict="REQUIRES_ATTENTION",
        )
        db.add(cap)
        db.add(trust)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = create_token(ADMIN_USER_ID, "eval_admin", "Administrator")
        res = await ac.get(
            f"/api/ais/rules/{RULE_UUID}/evaluation-status?search=INC-003&policy_version_number=7",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        item = res.json()["items"][0]
        assert item["status"] == STATUS_ABSTAINED
        assert item["is_real_inference"] is True
        assert item["badge_color"] == "amber"
        assert item["effective_verdict"] == "REQUIRES_ATTENTION"


# -----------------------------------------------------------------------------
# TEST 4: VALIDATION REJECTED returned when validator rejects model output
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_04_validation_rejected_status_when_validator_rejects_output():
    inc = await seed_incident("INC-004")
    async with AsyncSessionLocal() as db:
        cap = make_prompt_capture(
            incident_id=inc.incident_id,
            response_verdict="FALSE_POSITIVE",
            response_confidence=90.0,
            integrity_details={
                "validation_status": "FAILED_EVIDENCE_GROUNDING",
                "is_decisive_accepted": False,
                "failure_reason": "Observed destination port 443 contradicted model reasoning.",
            },
        )
        trust = make_trust_record(
            incident_id=inc.incident_id,
            suggested_verdict="FALSE_POSITIVE",
            effective_verdict="REQUIRES_ATTENTION",  # Safely converted by governor
        )
        db.add(cap)
        db.add(trust)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = create_token(ADMIN_USER_ID, "eval_admin", "Administrator")
        res = await ac.get(
            f"/api/ais/rules/{RULE_UUID}/evaluation-status?search=INC-004&policy_version_number=7",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        item = res.json()["items"][0]
        # Preserves both facts: validation rejected and effective abstention
        assert item["status"] == STATUS_VALIDATION_REJECTED
        assert item["badge_color"] == "red"
        assert item["effective_verdict"] == "REQUIRES_ATTENTION"
        assert item["validation_status"] == "FAILED_EVIDENCE_GROUNDING"


# -----------------------------------------------------------------------------
# TEST 5: EVALUATION FAILED returned on timeout, exception, or failure
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_05_evaluation_failed_status_on_timeout_or_error():
    inc = await seed_incident("INC-005")
    async with AsyncSessionLocal() as db:
        cap = make_prompt_capture(
            incident_id=inc.incident_id,
            dispatch_status="FAILED",
            error_message="HTTPConnectionPool: Read timed out after 30.0 seconds.",
        )
        db.add(cap)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = create_token(ADMIN_USER_ID, "eval_admin", "Administrator")
        res = await ac.get(
            f"/api/ais/rules/{RULE_UUID}/evaluation-status?search=INC-005&policy_version_number=7",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        item = res.json()["items"][0]
        assert item["status"] == STATUS_EVALUATION_FAILED
        assert item["badge_color"] == "red"
        assert "Read timed out" in (item["validation_failure_reason"] or item["reason"])


# -----------------------------------------------------------------------------
# TEST 6: Mock/simulation output marked is_mock_only: true and excluded from real LLM
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_06_mock_or_simulation_output_marked_is_mock_only_and_excluded():
    inc = await seed_incident("INC-006")
    async with AsyncSessionLocal() as db:
        cap = make_prompt_capture(
            incident_id=inc.incident_id,
            is_simulated=True,
            model_name="MockSimulatedProvider-v1",
            response_verdict="FALSE_POSITIVE",
            response_confidence=99.0,
        )
        db.add(cap)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = create_token(ADMIN_USER_ID, "eval_admin", "Administrator")
        res = await ac.get(
            f"/api/ais/rules/{RULE_UUID}/evaluation-status?search=INC-006&policy_version_number=7",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        item = res.json()["items"][0]
        # Canonical status remains NOT_EVALUATED because mock doesn't satisfy real GPU evaluation
        assert item["status"] == STATUS_NOT_EVALUATED
        assert item["is_simulated"] is True
        assert item["is_real_inference"] is False
        summary = res.json()["summary"]
        assert summary["mock_only_count"] >= 1


# -----------------------------------------------------------------------------
# TEST 7: Policy version isolation: v7 evaluation does not satisfy v8 request
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_07_policy_version_isolation_v7_does_not_satisfy_v8():
    inc = await seed_incident("INC-007")
    async with AsyncSessionLocal() as db:
        cap_v7 = make_prompt_capture(
            incident_id=inc.incident_id,
            policy_version_id=V7_VERSION_ID,
            policy_version_number=7,
            response_verdict="TRUE_POSITIVE",
            response_confidence=94.0,
            integrity_details={"validation_status": "VALIDATED", "is_decisive_accepted": True},
        )
        trust_v7 = make_trust_record(
            incident_id=inc.incident_id,
            suggested_verdict="TRUE_POSITIVE",
            effective_verdict="TRUE_POSITIVE",
        )
        db.add(cap_v7)
        db.add(trust_v7)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = create_token(ADMIN_USER_ID, "eval_admin", "Administrator")
        # Query under v7 -> EVALUATED_DECISIVE
        res_v7 = await ac.get(
            f"/api/ais/rules/{RULE_UUID}/evaluation-status?search=INC-007&policy_version_number=7",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_v7.status_code == 200
        assert res_v7.json()["items"][0]["status"] == STATUS_EVALUATED_DECISIVE

        # Query under v8 -> NOT_EVALUATED (strict isolation)
        res_v8 = await ac.get(
            f"/api/ais/rules/{RULE_UUID}/evaluation-status?search=INC-007&policy_version_number=8",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_v8.status_code == 200
        assert res_v8.json()["items"][0]["status"] == STATUS_NOT_EVALUATED


# -----------------------------------------------------------------------------
# TEST 8: Status list filtering by status, policy version, and search
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_08_status_list_filtering_by_status_policy_version_and_search():
    inc = await seed_incident("INC-FILTER-01")
    async with AsyncSessionLocal() as db:
        cap = make_prompt_capture(
            incident_id=inc.incident_id,
            response_verdict="REQUIRES_ATTENTION",
            integrity_details={"validation_status": "VALIDATED", "is_decisive_accepted": False},
        )
        db.add(cap)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = create_token(ADMIN_USER_ID, "eval_admin", "Administrator")

        # Filter by status: ABSTAINED
        res_abstained = await ac.get(
            f"/api/ais/rules/{RULE_UUID}/evaluation-status?status=ABSTAINED&policy_version_number=7",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_abstained.status_code == 200
        for item in res_abstained.json()["items"]:
            assert item["status"] == STATUS_ABSTAINED

        # Filter by search query
        res_search = await ac.get(
            f"/api/ais/rules/{RULE_UUID}/evaluation-status?search=INC-FILTER-01&policy_version_number=7",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_search.status_code == 200
        items = res_search.json()["items"]
        assert len(items) == 1
        assert items[0]["incident_id"] == "INC-FILTER-01"


# -----------------------------------------------------------------------------
# TEST 9: Summary API count accuracy (no double counting across multiple attempts)
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_09_summary_api_count_accuracy_no_double_counting():
    inc = await seed_incident("INC-009")
    async with AsyncSessionLocal() as db:
        now = datetime.datetime.now(datetime.timezone.utc)
        t1 = now - datetime.timedelta(minutes=30)
        t2 = now - datetime.timedelta(minutes=15)
        t3 = now

        cap1 = make_prompt_capture(
            incident_id=inc.incident_id,
            dispatch_status="FAILED",
            error_message="Timeout",
            captured_at=t1,
        )
        cap2 = make_prompt_capture(
            incident_id=inc.incident_id,
            response_verdict="REQUIRES_ATTENTION",
            captured_at=t2,
        )
        cap3 = make_prompt_capture(
            incident_id=inc.incident_id,
            response_verdict="FALSE_POSITIVE",
            integrity_details={"validation_status": "VALIDATED", "is_decisive_accepted": True},
            captured_at=t3,
        )
        trust3 = make_trust_record(
            incident_id=inc.incident_id,
            suggested_verdict="FALSE_POSITIVE",
            effective_verdict="FALSE_POSITIVE",
            evaluated_at=t3,
        )
        db.add_all([cap1, cap2, cap3, trust3])
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = create_token(ADMIN_USER_ID, "eval_admin", "Administrator")
        res = await ac.get(
            f"/api/ais/rules/{RULE_UUID}/evaluation-status?search=INC-009&policy_version_number=7",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["status"] == STATUS_EVALUATED_DECISIVE
        assert item["evaluation_attempts_count"] >= 3


# -----------------------------------------------------------------------------
# TEST 10: Evaluation history preserves all attempts in chronological order
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_10_evaluation_history_preserves_all_attempts_in_chronological_order():
    inc = await seed_incident("INC-HIST-01")
    async with AsyncSessionLocal() as db:
        now = datetime.datetime.now(datetime.timezone.utc)
        cap1 = make_prompt_capture(
            incident_id=inc.incident_id,
            dispatch_status="FAILED",
            error_message="Timeout",
            captured_at=now - datetime.timedelta(minutes=30),
        )
        cap2 = make_prompt_capture(
            incident_id=inc.incident_id,
            response_verdict="REQUIRES_ATTENTION",
            captured_at=now - datetime.timedelta(minutes=15),
        )
        cap3 = make_prompt_capture(
            incident_id=inc.incident_id,
            response_verdict="FALSE_POSITIVE",
            captured_at=now,
        )
        db.add_all([cap1, cap2, cap3])
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = create_token(ADMIN_USER_ID, "eval_admin", "Administrator")
        res = await ac.get(
            f"/api/ais/incidents/INC-HIST-01/evaluation-history",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        hist = res.json()
        assert hist["incident_id"] == "INC-HIST-01"
        assert hist["history_count"] == 3
        timestamps = [item["captured_at"] for item in hist["history"] if item["captured_at"]]
        assert timestamps == sorted(timestamps, reverse=True)


# -----------------------------------------------------------------------------
# TEST 11: Controlled batch inference evaluates only eligible missing incidents
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_11_controlled_batch_inference_evaluates_only_eligible_missing_incidents():
    from unittest.mock import patch, AsyncMock
    inc_missing = await seed_incident("INC-MISSING-01")
    inc_existing = await seed_incident("INC-EXISTING-01")

    async with AsyncSessionLocal() as db:
        rev1 = AnalystVerdictReview(
            id=str(uuid.uuid4()),
            incident_id=inc_missing.incident_id,
            rule_id=RULE_UUID,
            reviewer_id="analyst_1",
            analyst_verdict="FALSE_POSITIVE",
            ground_truth_status="VERIFIED",
        )
        rev2 = AnalystVerdictReview(
            id=str(uuid.uuid4()),
            incident_id=inc_existing.incident_id,
            rule_id=RULE_UUID,
            reviewer_id="analyst_2",
            analyst_verdict="FALSE_POSITIVE",
            ground_truth_status="VERIFIED",
        )
        cap_ex = make_prompt_capture(
            incident_id=inc_existing.incident_id,
            response_verdict="FALSE_POSITIVE",
        )
        db.add_all([rev1, rev2, cap_ex])
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = create_token(ADMIN_USER_ID, "eval_admin", "Administrator")
        with patch("app.services.ai_verdict_service.AIVerdictService.is_local_llm_available", new=AsyncMock(return_value=True)):
            res = await ac.post(
                f"/api/ais/rules/{RULE_UUID}/evaluate-missing-batch",
                headers={"Authorization": f"Bearer {token}"},
                json={"version_number": 7, "confirm_execution": False},
            )
        assert res.status_code == 200
        data = res.json()
        assert data["action"] == "PREFLIGHT_SUMMARY"
        assert data["confirmed"] is False
        assert data["ready_for_execution"] is True
        candidate_ids = data["preflight"]["eligible_incident_ids"]
        assert "INC-MISSING-01" in candidate_ids
        assert "INC-EXISTING-01" not in candidate_ids


# -----------------------------------------------------------------------------
# TEST 12: Batch inference stops gracefully on cancellation
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_12_controlled_batch_inference_graceful_cancellation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = create_token(ADMIN_USER_ID, "eval_admin", "Administrator")
        res = await ac.post(
            f"/api/ais/rules/{RULE_UUID}/evaluate-missing-batch",
            headers={"Authorization": f"Bearer {token}"},
            json={"version_number": 7, "confirm_execution": False},
        )
        assert res.status_code == 200
        assert res.json()["confirmed"] is False
        assert res.json()["total_processed"] == 0


# -----------------------------------------------------------------------------
# TEST 13: Double-blind protection: unreviewed incidents mask raw/effective verdict
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_13_double_blind_protection_unreviewed_incident_masks_verdicts():
    inc = await seed_incident("INC-BLIND-01")
    async with AsyncSessionLocal() as db:
        cap = make_prompt_capture(
            incident_id=inc.incident_id,
            response_verdict="TRUE_POSITIVE",
            response_confidence=97.0,
            integrity_details={"validation_status": "VALIDATED", "is_decisive_accepted": True},
        )
        trust = make_trust_record(
            incident_id=inc.incident_id,
            suggested_verdict="TRUE_POSITIVE",
            effective_verdict="TRUE_POSITIVE",
        )
        db.add(cap)
        db.add(trust)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token_analyst = create_token(ANALYST_USER_ID, "eval_analyst", "SOC Analyst")
        res = await ac.get(
            f"/api/ais/rules/{RULE_UUID}/evaluation-status?search=INC-BLIND-01&policy_version_number=7",
            headers={"Authorization": f"Bearer {token_analyst}"},
        )
        assert res.status_code == 200
        item = res.json()["items"][0]
        # Mandatory server-side masking
        assert item["raw_model_verdict"] == "[Hidden - Blind Review]"
        assert item["effective_verdict"] == "[Hidden - Blind Review]"
        assert item["confidence"] is None
        assert item["reason"] == "[Hidden - Blind Review]"
        assert "TRUE_POSITIVE" not in str(item)


# -----------------------------------------------------------------------------
# TEST 14: Authorized admin/engineer can inspect full evaluation details
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_14_authorized_admin_can_inspect_full_evaluation_details():
    inc_admin = await seed_incident("INC-ADMIN-01")
    async with AsyncSessionLocal() as db:
        cap = make_prompt_capture(
            incident_id=inc_admin.incident_id,
            response_verdict="TRUE_POSITIVE",
            response_confidence=97.0,
            integrity_details={"validation_status": "VALIDATED", "is_decisive_accepted": True},
        )
        trust = make_trust_record(
            incident_id=inc_admin.incident_id,
            suggested_verdict="TRUE_POSITIVE",
            effective_verdict="TRUE_POSITIVE",
        )
        db.add(cap)
        db.add(trust)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token_admin = create_token(ADMIN_USER_ID, "eval_admin", "Administrator")
        res = await ac.get(
            f"/api/ais/rules/{RULE_UUID}/evaluation-status?search=INC-ADMIN-01&policy_version_number=7",
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert res.status_code == 200
        item = res.json()["items"][0]
        assert item["raw_model_verdict"] == "TRUE_POSITIVE"
        assert item["effective_verdict"] == "TRUE_POSITIVE"
        assert item["confidence"] == 97.0


# -----------------------------------------------------------------------------
# TEST 15: Non-admin cannot trigger batch inference
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_15_non_admin_cannot_trigger_batch_inference():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token_analyst = create_token(ANALYST_USER_ID, "eval_analyst", "SOC Analyst")
        res = await ac.post(
            f"/api/ais/rules/{RULE_UUID}/evaluate-missing-batch",
            headers={"Authorization": f"Bearer {token_analyst}"},
            json={"version_number": 7, "confirm_execution": True},
        )
        assert res.status_code == 403


# -----------------------------------------------------------------------------
# TEST 16: Tenant isolation enforced on evaluation status and history endpoints
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_16_tenant_isolation_enforced():
    inc_other = await seed_incident("INC-OTHER-01", customer="OTHER_TENANT")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token_default = create_token(ANALYST_USER_ID, "eval_analyst", "SOC Analyst", customer="DEFAULT")
        res = await ac.get(
            f"/api/ais/incidents/INC-OTHER-01/evaluation-history",
            headers={"Authorization": f"Bearer {token_default}"},
        )
        assert res.status_code in (403, 404)

        token_other = create_token(OTHER_TENANT_USER_ID, "eval_other", "SOC Analyst", customer="OTHER_TENANT")
        res_ok = await ac.get(
            f"/api/ais/incidents/INC-OTHER-01/evaluation-history",
            headers={"Authorization": f"Bearer {token_other}"},
        )
        assert res_ok.status_code == 200
        assert res_ok.json()["incident_id"] == "INC-OTHER-01"


# -----------------------------------------------------------------------------
# TEST 17: Invalid rule UUID returns 404
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_17_invalid_rule_uuid_returns_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = create_token(ADMIN_USER_ID, "eval_admin", "Administrator")
        res = await ac.get(
            f"/api/ais/rules/00000000-0000-0000-0000-000000000000/evaluation-status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 404


# -----------------------------------------------------------------------------
# TEST 18: Missing incident ID returns 404
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_18_missing_incident_id_returns_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = create_token(ADMIN_USER_ID, "eval_admin", "Administrator")
        res = await ac.get(
            f"/api/ais/incidents/INC-DOES-NOT-EXIST-9999/evaluation-history",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 404


# -----------------------------------------------------------------------------
# TEST 19: Re-evaluating an incident creates a new history entry while updating latest status
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_19_re_evaluating_incident_creates_new_history_and_updates_latest_status():
    inc = await seed_incident("INC-019")
    async with AsyncSessionLocal() as db:
        now = datetime.datetime.now(datetime.timezone.utc)
        cap1 = make_prompt_capture(
            incident_id=inc.incident_id,
            response_verdict="REQUIRES_ATTENTION",
            captured_at=now - datetime.timedelta(minutes=10),
        )
        cap2 = make_prompt_capture(
            incident_id=inc.incident_id,
            response_verdict="TRUE_POSITIVE",
            response_confidence=91.0,
            integrity_details={"validation_status": "VALIDATED", "is_decisive_accepted": True},
            captured_at=now,
        )
        trust2 = make_trust_record(
            incident_id=inc.incident_id,
            suggested_verdict="TRUE_POSITIVE",
            effective_verdict="TRUE_POSITIVE",
            evaluated_at=now,
        )
        db.add_all([cap1, cap2, trust2])
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = create_token(ADMIN_USER_ID, "eval_admin", "Administrator")

        res_hist = await ac.get(
            f"/api/ais/incidents/INC-019/evaluation-history",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_hist.status_code == 200
        assert res_hist.json()["history_count"] == 2

        res_status = await ac.get(
            f"/api/ais/rules/{RULE_UUID}/evaluation-status?search=INC-019&policy_version_number=7",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_status.status_code == 200
        item = res_status.json()["items"][0]
        assert item["status"] == STATUS_EVALUATED_DECISIVE
        assert item["effective_verdict"] == "TRUE_POSITIVE"


# -----------------------------------------------------------------------------
# TEST 20: Empirical accuracy summary reports NOT MEASURABLE when decisive comparisons equal 0
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_20_empirical_accuracy_summary_not_measurable_when_zero_decisive_comparisons():
    inc_a1 = await seed_incident("INC-ACC-01")
    inc_a2 = await seed_incident("INC-ACC-02")
    inc_a3 = await seed_incident("INC-ACC-03")

    async with AsyncSessionLocal() as db:
        r1 = AnalystVerdictReview(
            id=str(uuid.uuid4()),
            incident_id=inc_a1.incident_id,
            rule_id=RULE_UUID,
            reviewer_id="analyst_test",
            analyst_verdict="FALSE_POSITIVE",
            ground_truth_status="VERIFIED",
        )
        r2 = AnalystVerdictReview(
            id=str(uuid.uuid4()),
            incident_id=inc_a2.incident_id,
            rule_id=RULE_UUID,
            reviewer_id="analyst_test",
            analyst_verdict="FALSE_POSITIVE",
            ground_truth_status="VERIFIED",
        )
        r3 = AnalystVerdictReview(
            id=str(uuid.uuid4()),
            incident_id=inc_a3.incident_id,
            rule_id=RULE_UUID,
            reviewer_id="analyst_test",
            analyst_verdict="FALSE_POSITIVE",
            ground_truth_status="VERIFIED",
        )
        cap1 = make_prompt_capture(
            incident_id=inc_a1.incident_id,
            response_verdict="REQUIRES_ATTENTION",
        )
        cap2 = make_prompt_capture(
            incident_id=inc_a2.incident_id,
            response_verdict="REQUIRES_ATTENTION",
        )
        db.add_all([r1, r2, r3, cap1, cap2])
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        token = create_token(ADMIN_USER_ID, "eval_admin", "Administrator")
        res = await ac.get(
            f"/api/ais/rules/{RULE_UUID}/evaluation-status?policy_version_number=7",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        summary = res.json()["summary"]
        assert summary["accuracy_status"] == "NOT_MEASURABLE"
        assert summary["selective_accuracy"] is None
        assert summary["eligible_decisive_comparisons"] == 0
        assert "No eligible decisive AI predictions" in summary["accuracy_explanation"]
        assert "DEFICIT" in summary["class_balance_status"]
