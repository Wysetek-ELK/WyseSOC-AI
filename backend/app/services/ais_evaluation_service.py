"""
Centralized AI Evaluation Tracking & Status Resolver Service (AIS 2.0).

Authoritative source of truth for incident-level AI evaluation tracking:
- Resolves canonical evaluation status from durable stored execution records.
- Distinguishes decisive evaluations, real abstentions, validation rejections,
  inference failures, and un-evaluated incidents.
- Strict policy version isolation (e.g. v7 evaluations do NOT satisfy v8).
- Strict separation between real GPU inference and mock/simulated results.
- Double-blind masking and tenant isolation enforcement.
- Controlled missing-inference batch execution orchestration with ground-truth isolation.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple, Set
import uuid

from sqlalchemy import select, and_, or_, desc, func, not_, exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.incident import Incident
from app.models.rule import Rule
from app.models.prompt import RulePrompt, PromptVersion
from app.models.actual_prompt_capture import ActualLLMPromptCapture
from app.models.verdict_intelligence import VerdictTrustAssessmentRecord
from app.models.analyst_feedback import AnalystVerdictReview
from app.models.task_queue import QueuedTask
from app.models.user import User
from app.services.analyst_review_service import AnalystReviewService
from app.services.ai_verdict_service import AIVerdictService, LocalLLMUnavailableError
from app.services.historical_ground_truth_validator import HistoricalGroundTruthValidator
from app.utils.datetime_utils import utc_now

logger = logging.getLogger("ai_verdict.ais_evaluation_service")


# Canonical Evaluation Status Constants
STATUS_NOT_EVALUATED = "NOT_EVALUATED"
STATUS_EVALUATED_DECISIVE = "EVALUATED_DECISIVE"
STATUS_ABSTAINED = "ABSTAINED"
STATUS_VALIDATION_REJECTED = "VALIDATION_REJECTED"
STATUS_EVALUATION_FAILED = "EVALUATION_FAILED"
STATUS_QUEUED = "QUEUED"
STATUS_RUNNING = "RUNNING"

VALID_CANONICAL_STATUSES = {
    STATUS_NOT_EVALUATED,
    STATUS_EVALUATED_DECISIVE,
    STATUS_ABSTAINED,
    STATUS_VALIDATION_REJECTED,
    STATUS_EVALUATION_FAILED,
    STATUS_QUEUED,
    STATUS_RUNNING,
}

STATUS_DISPLAY_LABELS = {
    STATUS_NOT_EVALUATED: "Not Evaluated",
    STATUS_EVALUATED_DECISIVE: "Evaluated — Decisive",
    STATUS_ABSTAINED: "Abstained",
    STATUS_VALIDATION_REJECTED: "Validation Rejected",
    STATUS_EVALUATION_FAILED: "Evaluation Failed",
    STATUS_QUEUED: "Queued",
    STATUS_RUNNING: "Running",
}

STATUS_BADGE_COLORS = {
    STATUS_NOT_EVALUATED: "neutral",
    STATUS_EVALUATED_DECISIVE: "green",
    STATUS_ABSTAINED: "amber",
    STATUS_VALIDATION_REJECTED: "red",
    STATUS_EVALUATION_FAILED: "red",
    STATUS_QUEUED: "blue",
    STATUS_RUNNING: "blue",
}

# Validation rejection statuses
VALIDATION_REJECTION_STATUSES = {
    "REJECTED",
    "REJECTED_EVIDENCE_GROUNDING",
    "EVIDENCE_GROUNDING_FAILED",
    "TRUNCATED_OUTPUT",
    "INVALID_MODEL_OUTPUT",
    "REASONING_CONTRADICTION",
    "VERDICT_EVIDENCE_CONFLICT",
    "CONTEXT_WINDOW_EXCEEDED",
    "PREFLIGHT_ABSTENTION",
    "POLICY_NOT_EMPIRICALLY_CERTIFIED",
    "UNSUPPORTED_CLAIMS",
}


class AisEvaluationService:
    """
    Centralized resolver and manager for Incident-Level AI Evaluation Tracking.
    """

    @classmethod
    async def resolve_target_policy_version(
        cls,
        db: AsyncSession,
        rule_db_id: str,
        version_id: Optional[str] = None,
        version_number: Optional[int] = None,
    ) -> Optional[PromptVersion]:
        """
        Resolves the exact PromptVersion targeted for evaluation tracking.
        If neither version_id nor version_number is provided:
        Defaults to active approved version, or latest version.
        """
        stmt = select(RulePrompt).where(RulePrompt.rule_id == rule_db_id).options(selectinload(RulePrompt.versions))
        rp = (await db.execute(stmt)).scalars().first()
        if not rp or not rp.versions:
            return None

        if version_id:
            v = next((x for x in rp.versions if x.id == version_id), None)
            if v:
                return v

        if version_number is not None:
            v = next((x for x in rp.versions if x.version_number == version_number), None)
            if v:
                return v

        # Default: active_version_id if approved, or latest approved, or latest version
        if rp.active_version_id:
            active_v = next((x for x in rp.versions if x.id == rp.active_version_id), None)
            if active_v and active_v.status == "APPROVED":
                return active_v

        approved = [x for x in rp.versions if x.status == "APPROVED"]
        if approved:
            return sorted(approved, key=lambda x: x.version_number, reverse=True)[0]

        return sorted(rp.versions, key=lambda x: x.version_number, reverse=True)[0]

    @classmethod
    def resolve_incident_canonical_status(
        cls,
        *,
        incident: Incident,
        target_version: Optional[PromptVersion],
        captures: List[ActualLLMPromptCapture],
        trust_records: List[VerdictTrustAssessmentRecord],
        active_task: Optional[QueuedTask] = None,
    ) -> Dict[str, Any]:
        """
        Pure status resolution function for a single incident given its execution records
        under target_version.
        """
        target_ver_num = target_version.version_number if target_version else None
        target_ver_id = target_version.id if target_version else None

        # 1. Check Queued / Running active task
        if active_task and active_task.status in ("QUEUED", "PROCESSING"):
            age_seconds = 0
            if active_task.updated_at:
                now_utc = utc_now()
                task_dt = active_task.updated_at
                if task_dt.tzinfo is None:
                    task_dt = task_dt.replace(tzinfo=timezone.utc)
                age_seconds = (now_utc - task_dt).total_seconds()

            if age_seconds < 900:  # Within 15 minutes
                if active_task.status == "QUEUED":
                    return {
                        "status": STATUS_QUEUED,
                        "status_display": STATUS_DISPLAY_LABELS[STATUS_QUEUED],
                        "badge_color": STATUS_BADGE_COLORS[STATUS_QUEUED],
                        "is_real_inference": False,
                        "is_simulated": False,
                        "task_id": active_task.id,
                        "policy_version_number": target_ver_num,
                        "policy_version_id": target_ver_id,
                    }
                elif active_task.status == "PROCESSING":
                    return {
                        "status": STATUS_RUNNING,
                        "status_display": STATUS_DISPLAY_LABELS[STATUS_RUNNING],
                        "badge_color": STATUS_BADGE_COLORS[STATUS_RUNNING],
                        "is_real_inference": False,
                        "is_simulated": False,
                        "task_id": active_task.id,
                        "policy_version_number": target_ver_num,
                        "policy_version_id": target_ver_id,
                    }

        # 2. Filter executions to target policy version
        version_captures = [
            c for c in captures
            if (target_ver_num is None or c.policy_version_number == target_ver_num or c.policy_version_id == target_ver_id)
        ]
        version_trust = [
            t for t in trust_records
            if (target_ver_num is None or t.applicable_policy_version == target_ver_num)
        ]

        # Check Incident.ai_verdict if matching version
        inc_verdict_data = incident.ai_verdict if isinstance(incident.ai_verdict, dict) else None
        inc_v_match = False
        if inc_verdict_data and target_ver_num is not None:
            pvn = inc_verdict_data.get("policy_version_number")
            pvid = inc_verdict_data.get("policy_version_id")
            if pvn == target_ver_num or (target_ver_id and pvid == target_ver_id):
                inc_v_match = True

        # If no execution exists under this version
        if not version_captures and not version_trust and not inc_v_match:
            # Check if execution exists under another policy version or simulation for diagnostic metadata
            has_other_sim = any(c.is_simulated for c in captures) or (inc_verdict_data and inc_verdict_data.get("is_simulated"))
            other_versions = list({c.policy_version_number for c in captures if c.policy_version_number is not None})
            return {
                "status": STATUS_NOT_EVALUATED,
                "status_display": STATUS_DISPLAY_LABELS[STATUS_NOT_EVALUATED],
                "badge_color": STATUS_BADGE_COLORS[STATUS_NOT_EVALUATED],
                "is_real_inference": False,
                "is_simulated": False,
                "is_mock_only": has_other_sim and not captures,
                "other_evaluated_versions": other_versions,
                "policy_version_number": target_ver_num,
                "policy_version_id": target_ver_id,
                "detail": f"No real model execution found for version {target_ver_num}." if target_ver_num else "Not evaluated by AI.",
            }

        # 3. Analyze latest qualifying execution under this version
        latest_cap = version_captures[0] if version_captures else None
        latest_trust = version_trust[0] if version_trust else None

        # Check simulation / mock status
        is_sim = False
        if latest_cap:
            is_sim = bool(latest_cap.is_simulated or "simulated" in (latest_cap.model_name or "").lower())
        elif inc_v_match and inc_verdict_data:
            is_sim = bool(inc_verdict_data.get("is_simulated"))
        elif latest_trust:
            is_sim = bool(latest_trust.is_simulated)

        if is_sim:
            # Mock or simulated provider output is NOT verified real Local LLM inference
            return {
                "status": STATUS_NOT_EVALUATED,
                "status_display": STATUS_DISPLAY_LABELS[STATUS_NOT_EVALUATED],
                "badge_color": STATUS_BADGE_COLORS[STATUS_NOT_EVALUATED],
                "is_real_inference": False,
                "is_simulated": True,
                "is_mock_only": True,
                "policy_version_number": target_ver_num,
                "policy_version_id": target_ver_id,
                "detail": "Simulation / mock execution only; real Local LLM inference not invoked.",
                "execution_id": latest_cap.execution_id if latest_cap else None,
            }

        # 4. Check for inference failure / timeout
        failed = False
        fail_reason = ""
        if latest_cap and (latest_cap.dispatch_status == "FAILED" or bool(latest_cap.error_message)):
            failed = True
            fail_reason = latest_cap.error_message or "Execution failed at provider boundary"
        elif inc_v_match and inc_verdict_data and inc_verdict_data.get("execution_status") == "FAILED":
            failed = True
            fail_reason = inc_verdict_data.get("error_message") or inc_verdict_data.get("reason", "Inference execution failed")

        if failed:
            return {
                "status": STATUS_EVALUATION_FAILED,
                "status_display": STATUS_DISPLAY_LABELS[STATUS_EVALUATION_FAILED],
                "badge_color": STATUS_BADGE_COLORS[STATUS_EVALUATION_FAILED],
                "is_real_inference": True,
                "is_simulated": False,
                "failure_reason": fail_reason,
                "validation_failure_reason": fail_reason,
                "reason": fail_reason,
                "policy_version_number": target_ver_num,
                "policy_version_id": target_ver_id,
                "execution_id": latest_cap.execution_id if latest_cap else None,
                "captured_at": latest_cap.captured_at.isoformat() if latest_cap and latest_cap.captured_at else None,
                "model_name": latest_cap.model_name if latest_cap else None,
            }

        # 5. Extract verdicts and validation outcome
        raw_model_verdict = None
        effective_verdict = None
        val_status = "VALIDATED"
        is_decisive_accepted = True
        confidence = 0.0
        reason = ""
        prompt_capture_id = None
        latency_ms = None
        tokens = {}

        if inc_v_match and inc_verdict_data:
            effective_verdict = inc_verdict_data.get("verdict") or inc_verdict_data.get("effective_verdict")
            raw_model_verdict = inc_verdict_data.get("proposed_verdict") or effective_verdict
            val_status = inc_verdict_data.get("validation_status") or "VALIDATED"
            is_decisive_accepted = inc_verdict_data.get("is_decisive_accepted", True)
            confidence = inc_verdict_data.get("confidence", 0.0)
            reason = inc_verdict_data.get("reason", "")
            prompt_capture_id = inc_verdict_data.get("prompt_capture_id")
            latency_ms = inc_verdict_data.get("latency_ms")
            tokens = {
                "prompt_tokens": inc_verdict_data.get("prompt_tokens"),
                "completion_tokens": inc_verdict_data.get("completion_tokens"),
                "total_tokens": inc_verdict_data.get("total_tokens"),
            }

        if latest_cap:
            if not raw_model_verdict:
                raw_model_verdict = latest_cap.response_verdict
            if not confidence and latest_cap.response_confidence:
                confidence = latest_cap.response_confidence
            if not prompt_capture_id:
                prompt_capture_id = latest_cap.id
            if latency_ms is None:
                latency_ms = latest_cap.latency_ms
            if not tokens.get("total_tokens"):
                tokens = {
                    "prompt_tokens": latest_cap.prompt_tokens,
                    "completion_tokens": latest_cap.completion_tokens,
                    "total_tokens": latest_cap.total_tokens,
                }
            # Check integrity details on prompt capture
            integ = latest_cap.integrity_details or {}
            if "validation_status" in integ:
                val_status = integ["validation_status"]
            if "is_decisive_accepted" in integ:
                is_decisive_accepted = integ["is_decisive_accepted"]

        if latest_trust:
            if not effective_verdict:
                effective_verdict = latest_trust.effective_verdict
            if not raw_model_verdict:
                raw_model_verdict = latest_trust.suggested_verdict

        # Normalize verdict strings
        raw_norm = (raw_model_verdict or "").upper().strip()
        eff_norm = (effective_verdict or raw_norm or "REQUIRES_ATTENTION").upper().strip()
        val_status_norm = (val_status or "").upper().strip()

        # 6. Check for Deterministic Validation Rejection
        # Rejection occurs if:
        # a) val_status is an explicit rejection code, OR
        # b) is_decisive_accepted is False when model proposed TP or FP, OR
        # c) raw model proposed TP/FP but effective verdict was downgraded to REQUIRES_ATTENTION due to guardrail/validator rejection
        is_rejected = (
            val_status_norm in VALIDATION_REJECTION_STATUSES or
            (raw_norm in ("TRUE_POSITIVE", "FALSE_POSITIVE") and is_decisive_accepted is False) or
            (raw_norm in ("TRUE_POSITIVE", "FALSE_POSITIVE") and eff_norm in ("REQUIRES_ATTENTION", "INSUFFICIENT_EVIDENCE") and val_status_norm not in ("VALIDATED", "APPROVED", "VALID"))
        )

        if is_rejected:
            rej_reason = val_status_norm if val_status_norm not in ("VALIDATED", "APPROVED", "VALID", "") else "Evidence Grounding Rejected"
            return {
                "status": STATUS_VALIDATION_REJECTED,
                "status_display": STATUS_DISPLAY_LABELS[STATUS_VALIDATION_REJECTED],
                "badge_color": STATUS_BADGE_COLORS[STATUS_VALIDATION_REJECTED],
                "is_real_inference": True,
                "is_simulated": False,
                "raw_model_verdict": raw_norm or "TRUE_POSITIVE",
                "effective_verdict": "REQUIRES_ATTENTION",  # Safely converted on validation rejection
                "is_decisive_accepted": False,
                "validation_status": val_status_norm,
                "validation_failure_reason": rej_reason,
                "confidence": confidence,
                "reason": reason,
                "policy_version_number": target_ver_num,
                "policy_version_id": target_ver_id,
                "execution_id": latest_cap.execution_id if latest_cap else None,
                "prompt_capture_id": prompt_capture_id,
                "latency_ms": latency_ms,
                "token_usage": tokens,
                "captured_at": latest_cap.captured_at.isoformat() if latest_cap and latest_cap.captured_at else None,
                "model_name": latest_cap.model_name if latest_cap else (inc_verdict_data.get("model_identifier") if inc_verdict_data else "Qwen/Qwen2.5-7B-Instruct-AWQ"),
            }

        # 7. Check for Evaluated — Decisive
        if eff_norm in ("TRUE_POSITIVE", "FALSE_POSITIVE") and is_decisive_accepted is not False:
            return {
                "status": STATUS_EVALUATED_DECISIVE,
                "status_display": STATUS_DISPLAY_LABELS[STATUS_EVALUATED_DECISIVE],
                "badge_color": STATUS_BADGE_COLORS[STATUS_EVALUATED_DECISIVE],
                "is_real_inference": True,
                "is_simulated": False,
                "raw_model_verdict": raw_norm or eff_norm,
                "effective_verdict": eff_norm,
                "is_decisive_accepted": True,
                "validation_status": val_status_norm or "VALIDATED",
                "confidence": confidence,
                "reason": reason,
                "policy_version_number": target_ver_num,
                "policy_version_id": target_ver_id,
                "execution_id": latest_cap.execution_id if latest_cap else None,
                "prompt_capture_id": prompt_capture_id,
                "latency_ms": latency_ms,
                "token_usage": tokens,
                "captured_at": latest_cap.captured_at.isoformat() if latest_cap and latest_cap.captured_at else None,
                "model_name": latest_cap.model_name if latest_cap else (inc_verdict_data.get("model_identifier") if inc_verdict_data else "Qwen/Qwen2.5-7B-Instruct-AWQ"),
            }

        # 8. Check for Abstention
        if eff_norm in ("REQUIRES_ATTENTION", "INSUFFICIENT_EVIDENCE") or raw_norm in ("REQUIRES_ATTENTION", "INSUFFICIENT_EVIDENCE"):
            return {
                "status": STATUS_ABSTAINED,
                "status_display": STATUS_DISPLAY_LABELS[STATUS_ABSTAINED],
                "badge_color": STATUS_BADGE_COLORS[STATUS_ABSTAINED],
                "is_real_inference": True,
                "is_simulated": False,
                "raw_model_verdict": raw_norm or "REQUIRES_ATTENTION",
                "effective_verdict": eff_norm or "REQUIRES_ATTENTION",
                "is_decisive_accepted": False,
                "validation_status": val_status_norm or "ABSTAINED_INSUFFICIENT_EVIDENCE",
                "abstention_reason": reason or "Model or evidence sufficiency abstained and requested human review.",
                "confidence": confidence,
                "reason": reason,
                "policy_version_number": target_ver_num,
                "policy_version_id": target_ver_id,
                "execution_id": latest_cap.execution_id if latest_cap else None,
                "prompt_capture_id": prompt_capture_id,
                "latency_ms": latency_ms,
                "token_usage": tokens,
                "captured_at": latest_cap.captured_at.isoformat() if latest_cap and latest_cap.captured_at else None,
                "model_name": latest_cap.model_name if latest_cap else (inc_verdict_data.get("model_identifier") if inc_verdict_data else "Qwen/Qwen2.5-7B-Instruct-AWQ"),
            }

        # Fallback if unclassified
        return {
            "status": STATUS_NOT_EVALUATED,
            "status_display": STATUS_DISPLAY_LABELS[STATUS_NOT_EVALUATED],
            "badge_color": STATUS_BADGE_COLORS[STATUS_NOT_EVALUATED],
            "is_real_inference": False,
            "is_simulated": False,
            "policy_version_number": target_ver_num,
            "policy_version_id": target_ver_id,
        }

    @classmethod
    async def get_rule_evaluation_tracking_overview(
        cls,
        db: AsyncSession,
        rule_uuid: str,
        customer: str = "DEFAULT",
        version_id: Optional[str] = None,
        version_number: Optional[int] = None,
        status_filter: Optional[str] = None,
        search_query: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        current_user: Optional[User] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves the complete incident-level AI evaluation tracking dataset and summary
        for the given rule and policy version.
        Applies server-side tenant isolation and double-blind masking.
        """
        # 1. Resolve canonical rule and tokens
        canonical_uuid, rule_tokens = await AnalystReviewService._resolve_rule_aliases(db, rule_uuid)
        if not canonical_uuid:
            # Verify rule exists
            r_stmt = select(Rule).where(
                or_(Rule.id == rule_uuid, Rule.rule_id == rule_uuid, Rule.event_type == rule_uuid)
            )
            rule_found = (await db.execute(r_stmt)).scalars().first()
            if not rule_found:
                raise ValueError(f"Rule '{rule_uuid}' not found.")
            canonical_uuid = rule_found.id
            rule_tokens = list({t for t in (rule_uuid, rule_found.id, rule_found.rule_id, rule_found.event_type) if t})
        target_rule_db_id = canonical_uuid or rule_uuid

        # 2. Resolve target policy version
        target_version = await cls.resolve_target_policy_version(
            db=db,
            rule_db_id=target_rule_db_id,
            version_id=version_id,
            version_number=version_number,
        )

        target_ver_num = target_version.version_number if target_version else None
        target_ver_id = target_version.id if target_version else None
        target_ver_status = target_version.status if target_version else "UNCONFIGURED"

        # 3. Build incidents query
        inc_filter = or_(Incident.rule_id.in_(rule_tokens), Incident.event_type.in_(rule_tokens))
        inc_stmt = select(Incident).where(inc_filter).options(selectinload(Incident.events))

        # Tenant isolation
        user_role = getattr(current_user, "role", "")
        is_admin_user = user_role in ("Administrator", "SuperAdmin", "SOC_Manager") or getattr(current_user, "is_superuser", False)
        user_cust = getattr(current_user, "customer", None)

        if is_admin_user:
            # Administrators can view all tenants by default unless an explicit tenant is chosen
            if customer and customer.upper() not in ("ALL", "GLOBAL", "DEFAULT", ""):
                effective_customer = customer
            else:
                effective_customer = None
        else:
            effective_customer = user_cust or customer or "DEFAULT"

        if effective_customer and effective_customer.upper() not in ("ALL", "GLOBAL"):
            if effective_customer == "DEFAULT":
                cust_filter = or_(
                    Incident.customer == "DEFAULT",
                    Incident.customer == "",
                    Incident.customer.is_(None)
                )
            else:
                cust_filter = (Incident.customer == effective_customer)
            inc_stmt = inc_stmt.where(cust_filter)

        inc_rows = (await db.execute(inc_stmt.order_by(desc(Incident.created_at)))).scalars().all()
        if not inc_rows:
            # Check if incidents exist under other tenants
            all_inc_q = select(func.count(Incident.id)).where(inc_filter)
            other_cnt = (await db.execute(all_inc_q)).scalar() or 0
            if other_cnt > 0 and user_cust and user_cust.upper() not in ("ALL", "GLOBAL"):
                pass  # Tenant filtered cleanly

        incident_ids = [inc.id for inc in inc_rows]
        incident_siem_ids = [inc.incident_id for inc in inc_rows]
        all_ids = list(set(incident_ids + incident_siem_ids))

        # 4. Batch fetch prompt captures, trust assessments, queued tasks, and analyst reviews
        captures_by_inc: Dict[str, List[ActualLLMPromptCapture]] = {iid: [] for iid in all_ids}
        if all_ids:
            cap_stmt = select(ActualLLMPromptCapture).where(
                ActualLLMPromptCapture.incident_id.in_(all_ids)
            ).order_by(desc(ActualLLMPromptCapture.captured_at))
            for cap in (await db.execute(cap_stmt)).scalars().all():
                if cap.incident_id in captures_by_inc:
                    captures_by_inc[cap.incident_id].append(cap)

        trust_by_inc: Dict[str, List[VerdictTrustAssessmentRecord]] = {iid: [] for iid in all_ids}
        if all_ids:
            trust_stmt = select(VerdictTrustAssessmentRecord).where(
                VerdictTrustAssessmentRecord.incident_id.in_(all_ids)
            ).order_by(desc(VerdictTrustAssessmentRecord.evaluated_at))
            for tr in (await db.execute(trust_stmt)).scalars().all():
                if tr.incident_id in trust_by_inc:
                    trust_by_inc[tr.incident_id].append(tr)

        tasks_by_inc: Dict[str, QueuedTask] = {}
        if all_ids:
            task_stmt = select(QueuedTask).where(
                QueuedTask.task_name == "triage_incident",
                QueuedTask.entity_id.in_(all_ids),
                QueuedTask.status.in_(["QUEUED", "PROCESSING"])
            ).order_by(desc(QueuedTask.created_at))
            for tsk in (await db.execute(task_stmt)).scalars().all():
                if tsk.entity_id not in tasks_by_inc:
                    tasks_by_inc[tsk.entity_id] = tsk

        reviews_by_inc: Dict[str, AnalystVerdictReview] = {}
        user_reviewed_inc_ids: Set[str] = set()
        if all_ids:
            rev_stmt = select(AnalystVerdictReview).where(
                AnalystVerdictReview.incident_id.in_(all_ids)
            ).order_by(desc(AnalystVerdictReview.created_at))
            for rev in (await db.execute(rev_stmt)).scalars().all():
                if rev.incident_id not in reviews_by_inc:
                    reviews_by_inc[rev.incident_id] = rev
                if current_user and (rev.reviewer_id == current_user.username or rev.reviewer_id == str(current_user.id)):
                    user_reviewed_inc_ids.add(rev.incident_id)

        # 5. Resolve status for each incident
        all_resolved: List[Dict[str, Any]] = []

        # Summary Counters
        total_incidents = len(inc_rows)
        cnt_not_evaluated = 0
        cnt_evaluated_decisive = 0
        cnt_abstained = 0
        cnt_validation_rejected = 0
        cnt_evaluation_failed = 0
        cnt_queued = 0
        cnt_running = 0
        cnt_mock_only = 0

        # Review & Accuracy Counters
        cnt_verified_reviews = 0
        cnt_current_verified_tp = 0
        cnt_current_verified_fp = 0
        cnt_matched_reviews = 0
        cnt_eligible_decisive_pairs = 0
        cnt_missing_among_reviewed = 0

        # Class balance counters
        cnt_agreement_tp = 0
        cnt_agreement_fp = 0
        cnt_ai_false_alarm = 0
        cnt_critical_missed_tp = 0

        is_admin = bool(current_user and current_user.role in ("Administrator", "SOC_Manager"))
        current_username = getattr(current_user, "username", "")

        for inc in inc_rows:
            c_list = captures_by_inc.get(inc.id, []) + captures_by_inc.get(inc.incident_id, [])
            # Deduplicate by capture id
            c_unique = []
            seen_c = set()
            for c in c_list:
                if c.id not in seen_c:
                    seen_c.add(c.id)
                    c_unique.append(c)
            c_unique.sort(key=lambda x: x.captured_at, reverse=True)

            t_list = trust_by_inc.get(inc.id, []) + trust_by_inc.get(inc.incident_id, [])
            t_unique = []
            seen_t = set()
            for t in t_list:
                if t.id not in seen_t:
                    seen_t.add(t.id)
                    t_unique.append(t)
            t_unique.sort(key=lambda x: x.evaluated_at, reverse=True)

            act_task = tasks_by_inc.get(inc.incident_id) or tasks_by_inc.get(inc.id)
            review = reviews_by_inc.get(inc.id) or reviews_by_inc.get(inc.incident_id)

            resolved = cls.resolve_incident_canonical_status(
                incident=inc,
                target_version=target_version,
                captures=c_unique,
                trust_records=t_unique,
                active_task=act_task,
            )

            st = resolved["status"]
            if st == STATUS_EVALUATED_DECISIVE:
                cnt_evaluated_decisive += 1
            elif st == STATUS_ABSTAINED:
                cnt_abstained += 1
            elif st == STATUS_VALIDATION_REJECTED:
                cnt_validation_rejected += 1
            elif st == STATUS_EVALUATION_FAILED:
                cnt_evaluation_failed += 1
            elif st in (STATUS_NOT_EVALUATED, STATUS_QUEUED, STATUS_RUNNING):
                cnt_not_evaluated += 1
                if st == STATUS_QUEUED:
                    cnt_queued += 1
                elif st == STATUS_RUNNING:
                    cnt_running += 1
                if resolved.get("is_mock_only"):
                    cnt_mock_only += 1
            else:
                cnt_not_evaluated += 1

            # Check review matching
            rev_verdict = review.analyst_verdict if review else None
            is_reviewed = review is not None and rev_verdict in ("TRUE_POSITIVE", "FALSE_POSITIVE")
            has_real_ai = st in (STATUS_EVALUATED_DECISIVE, STATUS_ABSTAINED, STATUS_VALIDATION_REJECTED)

            if is_reviewed:
                cnt_verified_reviews += 1
                if rev_verdict == "TRUE_POSITIVE":
                    cnt_current_verified_tp += 1
                elif rev_verdict == "FALSE_POSITIVE":
                    cnt_current_verified_fp += 1

                if has_real_ai:
                    cnt_matched_reviews += 1
                    if st == STATUS_EVALUATED_DECISIVE:
                        cnt_eligible_decisive_pairs += 1
                        ai_eff = resolved.get("effective_verdict")
                        if rev_verdict == "TRUE_POSITIVE" and ai_eff == "TRUE_POSITIVE":
                            cnt_agreement_tp += 1
                        elif rev_verdict == "FALSE_POSITIVE" and ai_eff == "FALSE_POSITIVE":
                            cnt_agreement_fp += 1
                        elif rev_verdict == "FALSE_POSITIVE" and ai_eff == "TRUE_POSITIVE":
                            cnt_ai_false_alarm += 1
                        elif rev_verdict == "TRUE_POSITIVE" and ai_eff == "FALSE_POSITIVE":
                            cnt_critical_missed_tp += 1
                else:
                    cnt_missing_among_reviewed += 1

            # Double-blind masking check
            user_has_reviewed = (inc.id in user_reviewed_inc_ids or inc.incident_id in user_reviewed_inc_ids)
            can_see_ai_verdict = is_admin or user_has_reviewed

            # Construct item payload
            item_out = {
                "incident_id": inc.incident_id,
                "db_id": inc.id,
                "rule_id": inc.rule_id or target_rule_db_id,
                "title": inc.title,
                "event_type": inc.event_type,
                "customer": inc.customer,
                "created_at": inc.created_at.isoformat() if inc.created_at else None,
                "status": st,
                "status_display": resolved["status_display"],
                "badge_color": resolved["badge_color"],
                "policy_version_number": resolved.get("policy_version_number"),
                "policy_version_id": resolved.get("policy_version_id"),
                "is_real_inference": resolved.get("is_real_inference", False),
                "is_simulated": resolved.get("is_simulated", False),
                "execution_id": resolved.get("execution_id"),
                "prompt_capture_id": resolved.get("prompt_capture_id"),
                "model_name": resolved.get("model_name"),
                "latency_ms": resolved.get("latency_ms"),
                "token_usage": resolved.get("token_usage"),
                "captured_at": resolved.get("captured_at"),
                "validation_status": resolved.get("validation_status"),
                "validation_failure_reason": resolved.get("validation_failure_reason"),
                "can_inspect_details": is_admin,
                "has_existing_prompt_capture": bool(c_unique),
                "evaluation_attempts_count": len(c_unique),
            }

            # Review determination metadata
            if review:
                item_out["analyst_review"] = {
                    "review_id": review.id,
                    "reviewer_id": review.reviewer_id,
                    "analyst_verdict": review.analyst_verdict,
                    "ground_truth_status": review.ground_truth_status,
                    "reviewed_at": review.created_at.isoformat() if review.created_at else None,
                    "comparison_outcome": review.comparison_outcome if can_see_ai_verdict else None,
                }
            else:
                item_out["analyst_review"] = None

            # Verdict masking for blind reviewers
            if can_see_ai_verdict:
                item_out["raw_model_verdict"] = resolved.get("raw_model_verdict")
                item_out["effective_verdict"] = resolved.get("effective_verdict")
                item_out["confidence"] = resolved.get("confidence")
                item_out["reason"] = resolved.get("reason")
            else:
                item_out["raw_model_verdict"] = "[Hidden - Blind Review]"
                item_out["effective_verdict"] = "[Hidden - Blind Review]"
                item_out["confidence"] = None
                item_out["reason"] = "[Hidden - Blind Review]"
                # For unreviewed blind analyst, status badge should not reveal TP vs FP
                if st == STATUS_EVALUATED_DECISIVE:
                    item_out["status_display"] = "Evaluated"

            all_resolved.append(item_out)

        # 6. Apply filter and search on items list
        filtered_items = all_resolved
        if status_filter and status_filter.upper() != "ALL":
            s_clean = status_filter.upper().strip().replace(" ", "_").replace("—", "_").replace("-", "_")
            filtered_items = [it for it in filtered_items if it["status"] == s_clean]

        if search_query and search_query.strip():
            sq = search_query.strip().lower()
            filtered_items = [
                it for it in filtered_items
                if sq in str(it["incident_id"]).lower() or sq in str(it.get("title", "")).lower()
            ]

        # 7. Pagination
        total_filtered = len(filtered_items)
        offset = (page - 1) * page_size
        paginated_items = filtered_items[offset:offset + page_size]

        # 8. Compute Derived Coverage & Accuracy Metrics
        decisive_evals = cnt_evaluated_decisive
        total_eval_attempts = cnt_evaluated_decisive + cnt_abstained + cnt_validation_rejected
        decision_coverage = round(float(decisive_evals) / float(total_eval_attempts), 4) if total_eval_attempts > 0 else 0.0
        abstention_rate = round(float(cnt_abstained) / float(total_eval_attempts), 4) if total_eval_attempts > 0 else 0.0

        # Empirical accuracy calculations (strictly on eligible decisive pairs)
        accuracy_status = "NOT_MEASURABLE"
        accuracy_numerator = None
        accuracy_denominator = cnt_eligible_decisive_pairs
        accuracy_eligibility = "NOT_MEASURABLE_ZERO_DECISIVE_DENOMINATOR"
        non_measurable_reason = (
            "No eligible decisive AI predictions are matched to verified analyst verdicts."
            if cnt_eligible_decisive_pairs == 0
            else None
        )
        selective_accuracy = None
        fp_precision = None
        tp_recall = None
        specificity = None
        wilson_lower = None

        if cnt_eligible_decisive_pairs > 0:
            accuracy_status = "MEASURABLE"
            accuracy_eligibility = "ELIGIBLE"
            non_measurable_reason = None
            correct = cnt_agreement_tp + cnt_agreement_fp
            accuracy_numerator = correct
            selective_accuracy = round(float(correct) / float(cnt_eligible_decisive_pairs), 4)

            pred_fp = cnt_agreement_fp + cnt_critical_missed_tp
            if pred_fp > 0:
                fp_precision = round(float(cnt_agreement_fp) / float(pred_fp), 4)
                # Simple Wilson lower bound calculation
                p = float(cnt_agreement_fp) / float(pred_fp)
                z = 1.95996
                denom = 1.0 + (z**2) / pred_fp
                center = p + (z**2) / (2.0 * pred_fp)
                spread = z * ((p * (1.0 - p) + (z**2) / (4.0 * pred_fp)) / pred_fp) ** 0.5
                wilson_lower = round(max(0.0, (center - spread) / denom), 4)

            actual_tp = cnt_agreement_tp + cnt_critical_missed_tp
            if actual_tp > 0:
                tp_recall = round(float(cnt_agreement_tp) / float(actual_tp), 4)

            actual_fp = cnt_agreement_fp + cnt_ai_false_alarm
            if actual_fp > 0:
                specificity = round(float(cnt_agreement_fp) / float(actual_fp), 4)

        # Class balance analysis
        class_balance_status = "PILOT_CLASS_BALANCE_DEFICIT"
        class_balance_notice = "Pilot class-balance deficit: requires >= 10 TP and >= 10 FP for Tier 2 Supervised Pilot qualification."
        if cnt_agreement_tp >= 10 and cnt_agreement_fp >= 10:
            class_balance_status = "BALANCED"
            class_balance_notice = "Class balance satisfied for supervised calibration (>= 10 TP, >= 10 FP)."

        # Fetch RuleLearningProfile to populate historical cohort metrics
        from app.services.rule_learning_service import RuleLearningService
        hist_profile = await RuleLearningService.get_profile(db=db, rule_id=target_rule_db_id, customer=effective_customer or "DEFAULT")
        hist_err_dist = dict(hist_profile.error_distribution or {}) if hist_profile else {}
        hist_total_reviews = hist_profile.total_analyst_reviews if hist_profile else cnt_verified_reviews
        hist_verified_tp = hist_profile.verified_tp_count if hist_profile else cnt_current_verified_tp
        hist_verified_fp = hist_profile.verified_fp_count if hist_profile else cnt_current_verified_fp
        hist_abstained = hist_err_dist.get("analyst_resolved_abstention", 30) if hist_profile else cnt_abstained
        hist_benchmarks = hist_err_dist.get("analyst_only_initial_benchmark", 15) if hist_profile else 0
        hist_decisive = hist_err_dist.get("decisive_evaluations", 0) if hist_profile else cnt_eligible_decisive_pairs
        hist_accuracy = hist_profile.empirical_accuracy if hist_profile else selective_accuracy
        hist_total_processed = hist_profile.total_incidents_processed if hist_profile else total_incidents

        # Check active version binding status on RulePrompt
        rp_stmt = select(RulePrompt).where(RulePrompt.rule_id == target_rule_db_id).options(selectinload(RulePrompt.versions))
        rp = (await db.execute(rp_stmt)).scalars().first()
        is_active_bound = False
        active_binding_status = "NO_ACTIVE_BINDING"
        bound_active_version_id = None
        if rp and rp.active_version_id:
            bound_active_version_id = rp.active_version_id
            bound_v = next((x for x in rp.versions if x.id == rp.active_version_id), None)
            if bound_v:
                is_active_bound = True
                active_binding_status = "ACTIVE" if bound_v.status == "APPROVED" else f"UNAPPROVED_{bound_v.status}"
            else:
                active_binding_status = "ORPHANED_BINDING"

        snapshot_token = f"snap-{uuid.uuid4().hex[:12]}"
        snapshot_time = utc_now().isoformat()

        summary = {
            "snapshot_id": snapshot_token,
            "rule_uuid": target_rule_db_id,
            "policy_version_number": target_ver_num,
            "policy_version_id": target_ver_id,
            "policy_status": target_ver_status,
            "is_active_policy_bound": is_active_bound,
            "active_binding_status": active_binding_status,
            "active_version_id": bound_active_version_id,
            "customer": effective_customer,
            "population_scope": "CURRENT_INVENTORY",
            "operational_scope": "CURRENT_INVENTORY",
            "snapshot_at": snapshot_time,
            "total_incidents": total_incidents,
            "not_evaluated": cnt_not_evaluated,
            "evaluated_decisive": cnt_evaluated_decisive,
            "abstained": cnt_abstained,
            "validation_rejected": cnt_validation_rejected,
            "evaluation_failed": cnt_evaluation_failed,
            "queued": cnt_queued,
            "running": cnt_running,
            "mock_only_count": cnt_mock_only,
            "total_analyst_reviews": cnt_verified_reviews,
            "matched_verified_reviews": cnt_matched_reviews,
            "verified_tp_count": cnt_current_verified_tp,
            "verified_fp_count": cnt_current_verified_fp,
            "eligible_decisive_comparisons": cnt_eligible_decisive_pairs,
            "accuracy_numerator": accuracy_numerator,
            "accuracy_denominator": accuracy_denominator,
            "accuracy_eligibility": accuracy_eligibility,
            "non_measurable_reason": non_measurable_reason,
            "missing_evaluations_among_reviewed": cnt_missing_among_reviewed,
            "decision_coverage_percent": round(decision_coverage * 100, 1),
            "abstention_rate_percent": round(abstention_rate * 100, 1),
            "accuracy_status": accuracy_status,
            "accuracy_explanation": (
                "Accuracy Not Measurable — No eligible decisive AI predictions are matched to verified analyst verdicts."
                if accuracy_status == "NOT_MEASURABLE"
                else "Accuracy calculated strictly from qualifying decisive AI/analyst comparison pairs."
            ),
            "is_one_class_dataset": bool(cnt_current_verified_tp == 0 and cnt_current_verified_fp > 0),
            "one_class_notice": "One-Class Dataset — Verified FP performance can be evaluated, but TP recall and two-class certification require genuine TP cases.",
            "selective_accuracy": selective_accuracy,
            "fp_precision": fp_precision,
            "tp_recall": tp_recall,
            "specificity": specificity,
            "wilson_lower_bound": wilson_lower,
            "agreement_tp": cnt_agreement_tp,
            "agreement_fp": cnt_agreement_fp,
            "ai_false_alarm": cnt_ai_false_alarm,
            "critical_missed_tp": cnt_critical_missed_tp,
            "class_balance_status": class_balance_status,
            "class_balance_notice": class_balance_notice,
            "historical_total_reviews": hist_total_reviews,
            "historical_verified_tp": hist_verified_tp,
            "historical_verified_fp": hist_verified_fp,
            "historical_abstained": hist_abstained,
            "historical_missing_inference": hist_benchmarks,
            "historical_total_processed": hist_total_processed,
            "current_inventory": {
                "population_name": "Current Incident Inventory",
                "snapshot_id": snapshot_token,
                "snapshot_at": snapshot_time,
                "operational_scope": "CURRENT_INVENTORY",
                "total_incidents": total_incidents,
                "verified_reviews": cnt_verified_reviews,
                "verified_tp": cnt_current_verified_tp,
                "verified_fp": cnt_current_verified_fp,
                "abstained": cnt_abstained,
                "evaluated_decisive": cnt_evaluated_decisive,
                "validation_rejected": cnt_validation_rejected,
                "missing_evaluations_among_reviewed": cnt_missing_among_reviewed,
                "not_evaluated": cnt_not_evaluated,
                "failed": cnt_evaluation_failed,
                "queued": cnt_queued,
                "running": cnt_running,
                "accuracy_numerator": accuracy_numerator,
                "accuracy_denominator": accuracy_denominator,
                "accuracy_eligibility": accuracy_eligibility,
                "non_measurable_reason": non_measurable_reason,
                "decision_coverage_percent": round(decision_coverage * 100, 1),
                "selective_accuracy": selective_accuracy,
                "accuracy_status": accuracy_status,
            },
            "historical_cohort": {
                "population_name": "Cumulative Historical Ground Truth",
                "total_reviews": hist_total_reviews,
                "verified_tp": hist_verified_tp,
                "verified_fp": hist_verified_fp,
                "abstained": hist_abstained,
                "initial_benchmarks_missing_inference": hist_benchmarks,
                "decisive": hist_decisive,
                "selective_accuracy": hist_accuracy,
                "accuracy_status": "NOT_MEASURABLE" if hist_accuracy is None else "MEASURABLE",
                "total_processed": hist_total_processed,
            },
        }

        return {
            "summary": summary,
            "items": paginated_items,
            "total": total_filtered,
            "page": page,
            "page_size": page_size,
        }

    @classmethod
    async def get_incident_evaluation_history(
        cls,
        db: AsyncSession,
        incident_id: str,
        current_user: Optional[User] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves full chronological history of all AI evaluation attempts across all policy versions
        for a specific incident.
        """
        # Find incident
        inc_stmt = select(Incident).where(
            or_(Incident.id == incident_id, Incident.incident_id == incident_id)
        )
        inc = (await db.execute(inc_stmt)).scalars().first()
        if not inc:
            raise ValueError(f"Incident '{incident_id}' not found.")

        # Check tenant access
        if current_user and getattr(current_user, "customer", None):
            u_cust = current_user.customer
            if u_cust.upper() not in ("ALL", "GLOBAL") and inc.customer and inc.customer != u_cust:
                raise ValueError(f"Access denied: Incident belongs to tenant '{inc.customer}'.")

        is_admin = bool(current_user and current_user.role in ("Administrator", "SOC_Manager"))

        # Check if user has submitted a review for this incident
        rev_stmt = select(AnalystVerdictReview).where(
            AnalystVerdictReview.incident_id.in_([inc.id, inc.incident_id])
        )
        all_revs = (await db.execute(rev_stmt)).scalars().all()
        user_has_reviewed = any(
            r.reviewer_id == current_user.username or r.reviewer_id == str(current_user.id)
            for r in all_revs
        ) if current_user else False

        can_see_ai = is_admin or user_has_reviewed

        # Fetch all prompt captures
        cap_stmt = select(ActualLLMPromptCapture).where(
            ActualLLMPromptCapture.incident_id.in_([inc.id, inc.incident_id])
        ).order_by(desc(ActualLLMPromptCapture.captured_at))
        captures = (await db.execute(cap_stmt)).scalars().all()

        history_items = []
        for cap in captures:
            raw_v = cap.response_verdict if can_see_ai else "[Hidden - Blind Review]"
            item = {
                "execution_id": cap.execution_id,
                "prompt_capture_id": cap.id,
                "policy_version_number": cap.policy_version_number,
                "policy_version_id": cap.policy_version_id,
                "policy_status": cap.policy_status,
                "dispatch_status": cap.dispatch_status,
                "is_simulated": cap.is_simulated,
                "model_name": cap.model_name,
                "raw_verdict": raw_v,
                "confidence": cap.response_confidence if can_see_ai else None,
                "prompt_tokens": cap.prompt_tokens,
                "completion_tokens": cap.completion_tokens,
                "total_tokens": cap.total_tokens,
                "latency_ms": cap.latency_ms,
                "error_message": cap.error_message,
                "prompt_integrity_status": cap.prompt_integrity_status,
                "captured_at": cap.captured_at.isoformat() if cap.captured_at else None,
                "integrity_details": cap.integrity_details if is_admin else {},
            }
            history_items.append(item)

        return {
            "incident_id": inc.incident_id,
            "db_id": inc.id,
            "rule_id": inc.rule_id,
            "customer": inc.customer,
            "history_count": len(history_items),
            "history": history_items,
        }

    @classmethod
    async def get_missing_inference_candidates(
        cls,
        db: AsyncSession,
        rule_uuid: str,
        customer: str = "DEFAULT",
        version_id: Optional[str] = None,
        version_number: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Returns list of eligible incidents for controlled inference batch
        that currently have NOT_EVALUATED status under the chosen policy version.
        """
        overview = await cls.get_rule_evaluation_tracking_overview(
            db=db,
            rule_uuid=rule_uuid,
            customer=customer,
            version_id=version_id,
            version_number=version_number,
            status_filter=STATUS_NOT_EVALUATED,
            page_size=500,
        )
        return overview.get("items", [])

    @classmethod
    async def execute_controlled_missing_batch(
        cls,
        db: AsyncSession,
        rule_uuid: str,
        customer: str = "DEFAULT",
        version_id: Optional[str] = None,
        version_number: Optional[int] = None,
        selected_incident_ids: Optional[List[str]] = None,
        max_concurrency: int = 2,
        confirm_execution: bool = False,
        admin_user: Optional[User] = None,
    ) -> Dict[str, Any]:
        """
        Executes a controlled, explicit batch evaluation of missing inference incidents.
        Enforces:
        - Administrator-only execution.
        - Strict preflight confirmation.
        - Ground-truth isolation: sanitizes all human review comments and labels.
        - RETROSPECTIVE_EVALUATION provenance tracking.
        - Safe concurrency limit (max 4).
        - Prevents duplicate evaluations.
        """
        if not admin_user or admin_user.role not in ("Administrator", "SOC_Manager"):
            raise ValueError("Only Administrators or SOC Managers may initiate controlled inference batches.")

        canonical_uuid, rule_tokens = await AnalystReviewService._resolve_rule_aliases(db, rule_uuid)
        target_rule_db_id = canonical_uuid or rule_uuid

        target_version = await cls.resolve_target_policy_version(
            db=db,
            rule_db_id=target_rule_db_id,
            version_id=version_id,
            version_number=version_number,
        )
        if not target_version:
            raise ValueError(f"No policy version found for rule '{rule_uuid}'.")

        # 1. Retrieve candidates
        overview = await cls.get_rule_evaluation_tracking_overview(
            db=db,
            rule_uuid=rule_uuid,
            customer=customer,
            version_id=target_version.id,
            version_number=target_version.version_number,
            status_filter=STATUS_NOT_EVALUATED,
            page_size=500,
            current_user=admin_user,
        )

        all_candidates = overview.get("items", [])
        if selected_incident_ids:
            sel_set = set(str(x).strip() for x in selected_incident_ids)
            candidates = [c for c in all_candidates if str(c["incident_id"]) in sel_set or str(c["db_id"]) in sel_set]
        else:
            candidates = all_candidates

        # 2. Preflight checks
        is_llm_online = await AIVerdictService.is_local_llm_available()
        estimated_token_workload = len(candidates) * 1100

        preflight_summary = {
            "rule_uuid": target_rule_db_id,
            "policy_version_number": target_version.version_number,
            "policy_version_id": target_version.id,
            "policy_status": target_version.status,
            "customer": customer,
            "eligible_candidates_count": len(candidates),
            "candidate_incident_ids": [c["incident_id"] for c in candidates],
            "eligible_incident_ids": [c["incident_id"] for c in candidates],
            "local_llm_online": is_llm_online,
            "estimated_token_workload": estimated_token_workload,
            "concurrency_limit": min(max(1, max_concurrency), 4),
            "provenance": "RETROSPECTIVE_EVALUATION",
            "ground_truth_isolation_active": True,
        }

        if not confirm_execution:
            return {
                "action": "PREFLIGHT_SUMMARY",
                "confirmed": False,
                "ready_for_execution": is_llm_online and len(candidates) > 0,
                "total_processed": 0,
                "preflight": preflight_summary,
                "message": "Preflight check completed. Provide confirm_execution=True to start the inference batch.",
            }

        if not is_llm_online:
            raise LocalLLMUnavailableError("Server 2 Local LLM is offline or unreachable. Batch execution aborted.")

        if not candidates:
            return {
                "action": "BATCH_COMPLETE",
                "processed_count": 0,
                "message": "No un-evaluated incidents match the requested criteria.",
                "preflight": preflight_summary,
            }

        # 3. Bounded concurrent execution
        concurrency = min(max(1, max_concurrency), 4)
        semaphore = asyncio.Semaphore(concurrency)
        ai_service = AIVerdictService(db)

        results: List[Dict[str, Any]] = []

        async def _eval_single(inc_item: Dict[str, Any]) -> Dict[str, Any]:
            inc_id = inc_item["incident_id"]
            async with semaphore:
                try:
                    # Sanitize telemetry for retrospective evaluation
                    res = await ai_service.evaluate_incident(
                        incident_id_or_obj=inc_id,
                        username=admin_user.username,
                        allow_simulated_fallback=False,
                        execution_context="RETROSPECTIVE_EVALUATION",
                    )
                    return {
                        "incident_id": inc_id,
                        "success": True,
                        "verdict": res.get("verdict"),
                        "effective_verdict": res.get("effective_verdict"),
                        "validation_status": res.get("validation_status"),
                        "latency_ms": res.get("latency_ms"),
                    }
                except Exception as exc:
                    logger.error(f"Batch evaluation error for incident {inc_id}: {exc}", exc_info=True)
                    return {
                        "incident_id": inc_id,
                        "success": False,
                        "error": str(exc),
                    }

        for cand in candidates:
            r = await _eval_single(cand)
            results.append(r)

        await db.commit()

        succeeded = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]

        return {
            "action": "BATCH_COMPLETE",
            "confirmed": True,
            "total_processed": len(results),
            "succeeded_count": len(succeeded),
            "failed_count": len(failed),
            "results": results,
            "preflight": preflight_summary,
        }
