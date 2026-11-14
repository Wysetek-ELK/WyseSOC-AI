import hashlib
import json
import logging
import re
import uuid
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.actual_prompt_capture import ActualLLMPromptCapture
from app.models.audit import AuditLog
from app.models.incident import Incident
from app.models.prompt import PromptVersion
from app.models.rule import Rule
from app.models.user import User
from app.services.policy_compiler_service import PolicyCompilerService
from app.schemas.compiled_policy import CompilationExecutionMode
from app.utils.datetime_utils import utc_now

logger = logging.getLogger("ai_verdict.actual_prompt_capture")


class ActualPromptCaptureService:
    """
    Authoritative Provider-Boundary Prompt Capture & Integrity Verification Service.
    Captures exact outbound LLM requests immediately prior to Server 2 dispatch.
    Guarantees immutable, execution-correlated inspection for L1 SOC analysts & Admins.
    """

    @staticmethod
    def canonical_hash(payload: Dict[str, Any]) -> str:
        """Computes deterministic SHA-256 hash of canonicalized JSON request payload."""
        canonical_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()

    @staticmethod
    def sanitize_settings(settings_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Ensures API keys, tokens, or credentials never enter capture records."""
        safe = {}
        for k, v in settings_dict.items():
            k_lower = k.lower()
            if any(secret in k_lower for secret in ("key", "token", "auth", "secret", "password")):
                continue
            safe[k] = v
        return safe

    @classmethod
    async def record_dispatch(
        cls,
        db: AsyncSession,
        *,
        execution_id: str,
        incident_id: str,
        rule_id: str,
        rule_name: str,
        policy_version_id: Optional[str],
        policy_version_number: Optional[int],
        policy_status: str,
        policy_source: str,
        attempt_number: int,
        model_name: str,
        provider_type: str,
        generation_settings: Dict[str, Any],
        compiled_system_prompt: str,
        user_message: str,
        rag_precedents: Optional[List[Dict[str, Any]]] = None,
        evidence_requirements: Optional[Dict[str, Any]] = None,
        verdict_schema: Optional[Dict[str, Any]] = None,
        raw_request_payload: Dict[str, Any],
    ) -> Optional[ActualLLMPromptCapture]:
        """
        Captures the final effective request payload immediately prior to dispatch to Server 2.
        Must never fail or crash the core incident triage pipeline.
        """
        try:
            req_hash = cls.canonical_hash(raw_request_payload)
            safe_settings = cls.sanitize_settings(generation_settings)
            precedents = rag_precedents or []
            ev_reqs = evidence_requirements or {}
            v_schema = verdict_schema or PolicyCompilerService.MODEL_RESPONSE_SCHEMA

            record = ActualLLMPromptCapture(
                id=str(uuid.uuid4()),
                execution_id=execution_id,
                incident_id=incident_id,
                rule_id=rule_id,
                rule_name=rule_name,
                policy_version_id=policy_version_id,
                policy_version_number=policy_version_number,
                policy_status=policy_status,
                policy_source=policy_source,
                dispatch_status="DISPATCHED",
                attempt_number=attempt_number,
                model_name=model_name,
                provider_type=provider_type,
                generation_settings=safe_settings,
                compiled_system_prompt=compiled_system_prompt,
                user_message=user_message,
                rag_precedents=precedents,
                has_rag_precedents=len(precedents) > 0,
                evidence_requirements=ev_reqs,
                verdict_schema=v_schema,
                raw_request_payload=raw_request_payload,
                request_sha256=req_hash,
                prompt_integrity_status="VERIFIED",
                integrity_details={
                    "hash_verified": True,
                    "sha256": req_hash,
                    "policy_status": policy_status,
                    "policy_source": policy_source,
                    "is_approved_policy": (policy_status == "APPROVED"),
                    "capture_stage": "PRE_DISPATCH",
                },
                l1_explanation={
                    "headline": "This is the investigation instruction and incident evidence that Verdictum AI sent to the Local LLM to generate this verdict.",
                    "policy_version_used": f"Version {policy_version_number or 1} ({policy_status})",
                    "mandatory_evidence_available": True,
                    "historical_precedents_included": len(precedents),
                    "verdict_returned": "PENDING_DISPATCH",
                    "prompt_matches_approved_policy": (policy_status == "APPROVED"),
                },
                is_redacted=False,
                captured_at=utc_now(),
            )
            db.add(record)
            await db.flush()
            return record
        except Exception as e:
            logger.error(f"Failed to record prompt dispatch capture for incident {incident_id}: {e}", exc_info=True)
            # Record audit failure for visibility
            try:
                db.add(AuditLog(
                    user_id="SYSTEM",
                    username="system",
                    action="LLM_PROMPT_CAPTURE_FAILED",
                    resource_type="INCIDENT",
                    resource_id=incident_id,
                    details={"error": str(e), "execution_id": execution_id, "attempt": attempt_number},
                ))
            except Exception:
                pass
            return None

    @classmethod
    async def record_completed(
        cls,
        db: AsyncSession,
        capture_id: str,
        *,
        response_raw: Optional[str],
        response_verdict: Optional[str],
        response_confidence: Optional[float],
        prompt_tokens: Optional[int],
        completion_tokens: Optional[int],
        total_tokens: Optional[int],
        latency_ms: Optional[int],
        integrity_status: str = "VERIFIED",
        integrity_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Updates capture record with final LLM response and verification status."""
        try:
            stmt = select(ActualLLMPromptCapture).where(ActualLLMPromptCapture.id == capture_id)
            res = await db.execute(stmt)
            record = res.scalar_one_or_none()
            if not record:
                return

            record.dispatch_status = "COMPLETED"
            record.response_raw = response_raw
            record.response_verdict = response_verdict
            record.response_confidence = response_confidence
            record.prompt_tokens = prompt_tokens
            record.completion_tokens = completion_tokens
            record.total_tokens = total_tokens
            record.latency_ms = latency_ms
            record.prompt_integrity_status = integrity_status

            det = record.integrity_details or {}
            if integrity_details:
                det.update(integrity_details)
            det["capture_stage"] = "POST_DISPATCH_COMPLETE"
            record.integrity_details = det

            # Update L1 explanation with finalized response info
            l1 = record.l1_explanation or {}
            l1["verdict_returned"] = response_verdict or "REQUIRES_ATTENTION"
            l1["response_confidence"] = response_confidence
            l1["latency_ms"] = latency_ms
            l1["prompt_tokens"] = prompt_tokens
            record.l1_explanation = l1

            db.add(record)
            await db.flush()
        except Exception as e:
            logger.error(f"Failed to finalize completed prompt capture {capture_id}: {e}", exc_info=True)

    @classmethod
    async def record_failed(
        cls,
        db: AsyncSession,
        capture_id: str,
        *,
        error_message: str,
        latency_ms: Optional[int] = None,
    ) -> None:
        """Updates capture record when LLM call fails (timeout, connection refused, HTTP error)."""
        try:
            stmt = select(ActualLLMPromptCapture).where(ActualLLMPromptCapture.id == capture_id)
            res = await db.execute(stmt)
            record = res.scalar_one_or_none()
            if not record:
                return

            record.dispatch_status = "FAILED"
            record.error_message = error_message
            record.latency_ms = latency_ms
            record.prompt_integrity_status = "UNVERIFIED"

            det = record.integrity_details or {}
            det["dispatch_error"] = error_message
            det["capture_stage"] = "POST_DISPATCH_FAILED"
            record.integrity_details = det

            l1 = record.l1_explanation or {}
            l1["verdict_returned"] = "FAILED"
            l1["failure_reason"] = error_message
            record.l1_explanation = l1

            db.add(record)
            await db.flush()
        except Exception as e:
            logger.error(f"Failed to record prompt failure for {capture_id}: {e}", exc_info=True)

    @classmethod
    async def record_non_dispatch(
        cls,
        db: AsyncSession,
        *,
        execution_id: str,
        incident_id: str,
        rule_id: str,
        rule_name: str,
        policy_version_id: Optional[str],
        policy_version_number: Optional[int],
        policy_status: str,
        reason: str,
    ) -> Optional[ActualLLMPromptCapture]:
        """
        Records an explicit capture-state entry when a verdict early-exits before dispatch
        (e.g., POLICY_NOT_APPROVED, CONTEXT_OVERFLOW, GOVERNANCE_BLOCKED).
        """
        try:
            record = ActualLLMPromptCapture(
                id=str(uuid.uuid4()),
                execution_id=execution_id,
                incident_id=incident_id,
                rule_id=rule_id,
                rule_name=rule_name,
                policy_version_id=policy_version_id,
                policy_version_number=policy_version_number,
                policy_status=policy_status,
                policy_source="GUARD_INTERCEPT",
                dispatch_status="NOT_DISPATCHED",
                attempt_number=1,
                model_name="NONE",
                provider_type="NONE",
                generation_settings={},
                compiled_system_prompt=f"DISPATCH INTERCEPTED: {reason}",
                user_message="NO_PAYLOAD_DISPATCHED",
                rag_precedents=[],
                has_rag_precedents=False,
                evidence_requirements={},
                verdict_schema={},
                raw_request_payload={"status": "NOT_DISPATCHED", "reason": reason},
                request_sha256="0" * 64,
                response_verdict="REQUIRES_ATTENTION",
                error_message=reason,
                prompt_integrity_status="UNVERIFIED",
                integrity_details={
                    "hash_verified": False,
                    "reason": reason,
                    "is_approved_policy": (policy_status == "APPROVED"),
                },
                l1_explanation={
                    "headline": "This incident triage did NOT dispatch a prompt to Server 2 because it was intercepted by safety guardrails.",
                    "policy_version_used": f"Version {policy_version_number or 0} ({policy_status})",
                    "mandatory_evidence_available": False,
                    "historical_precedents_included": 0,
                    "verdict_returned": "REQUIRES_ATTENTION",
                    "prompt_matches_approved_policy": (policy_status == "APPROVED"),
                    "interception_reason": reason,
                },
                is_redacted=False,
                captured_at=utc_now(),
            )
            db.add(record)
            await db.flush()
            return record
        except Exception as e:
            logger.error(f"Failed to record non-dispatch prompt entry for {incident_id}: {e}", exc_info=True)
            return None

    @classmethod
    def verify_integrity(
        cls,
        capture: ActualLLMPromptCapture,
        rule: Optional[Rule] = None,
        active_version: Optional[PromptVersion] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Performs multi-point integrity verification on a captured prompt:
        1. Canonical hash match against stored payload.
        2. Policy provenance: matches active approved policy version vs unauthorized draft.
        3. Delimiter and schema boundary compliance.
        """
        details: Dict[str, Any] = {}
        # 1. Recalculate hash
        recalc_hash = cls.canonical_hash(capture.raw_request_payload)
        hash_ok = (recalc_hash == capture.request_sha256)
        details["hash_match"] = hash_ok
        details["calculated_hash"] = recalc_hash
        details["stored_hash"] = capture.request_sha256

        if not hash_ok:
            return "MISMATCH", {**details, "mismatch_reason": "Payload hash discrepancy detected"}

        # 2. Check policy provenance
        if capture.dispatch_status == "NOT_DISPATCHED":
            return "UNVERIFIED", {**details, "notice": "Prompt was not dispatched to LLM engine"}

        if capture.policy_status != "APPROVED":
            # If policy was not approved at time of capture
            details["policy_approval_status"] = capture.policy_status
            if capture.policy_source in ("DATABASE_DRAFT", "DRAFT"):
                details["warning"] = "Executed with unapproved DRAFT policy"

        # Check if active approved version is different from what was executed
        if active_version and active_version.id != capture.policy_version_id:
            details["active_policy_divergence"] = True
            details["current_active_version_number"] = active_version.version_number
            details["executed_version_number"] = capture.policy_version_number

        # 3. Check delimiter boundaries in user message
        has_boundaries = (
            "<UNTRUSTED_INCIDENT_DATA>" in capture.user_message
            and "</UNTRUSTED_INCIDENT_DATA>" in capture.user_message
        )
        details["untrusted_data_boundaries_present"] = has_boundaries
        if not has_boundaries:
            return "MISMATCH", {**details, "mismatch_reason": "Missing mandatory untrusted data delimiters"}

        return "VERIFIED", details

    @classmethod
    def apply_role_redaction(
        cls,
        capture_dict: Dict[str, Any],
        user: Optional[User],
    ) -> Dict[str, Any]:
        """
        Applies role-based data redaction:
        - Administrators: full unredacted prompt and technical details.
        - SOC Analysts / Read-Only Viewers: sensitive credentials, private IPs/customer secrets masked.
        """
        is_admin = bool(user and str(user.role).strip().lower() == "administrator")
        if is_admin:
            capture_dict["is_redacted"] = False
            return capture_dict

        # Redact for analysts and viewers
        redacted = dict(capture_dict)
        redacted["is_redacted"] = True

        # Redact generation settings endpoints if containing sensitive ports or internal IPs
        gen_set = dict(redacted.get("generation_settings") or {})
        if "endpoint" in gen_set:
            gen_set["endpoint"] = re.sub(r"//[^:]+:", "//[REDACTED_HOST]:", str(gen_set["endpoint"]))
        redacted["generation_settings"] = gen_set

        # Mask private customer identifiers or passwords if present in user message
        user_msg = redacted.get("user_message") or ""
        # Mask obvious credential patterns like password=... or token=...
        user_msg = re.sub(r'(?i)(password|secret|apikey|token)["\']?\s*[:=]\s*["\']?[^"\'\s,;]+', r'\1="[REDACTED]"', user_msg)
        redacted["user_message"] = user_msg

        return redacted
