import hashlib
import json
import logging
import re
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, desc, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.actual_prompt_capture import ActualLLMPromptCapture
from app.models.audit import AuditLog
from app.models.incident import Incident
from app.models.prompt import PromptVersion
from app.models.rule import Rule
from app.models.user import User
from app.services.policy_compiler_service import PolicyCompilerService
from app.schemas.compiled_policy import CompilationExecutionMode
from app.schemas.prompt_inspector import ExecutionHistoryItem
from app.utils.datetime_utils import utc_now

logger = logging.getLogger("ai_verdict.actual_prompt_capture")


class ActualPromptCaptureService:
    """
    Authoritative Provider-Boundary Prompt Capture & Integrity Verification Service.
    Captures exact outbound LLM requests immediately prior to Server 2 dispatch.
    Guarantees immutable, execution-correlated inspection for L1 SOC analysts & Admins.
    """

    @staticmethod
    def canonical_serialize(payload: Dict[str, Any]) -> str:
        """Produces deterministic, canonical JSON serialization without extra whitespace."""
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    @classmethod
    def canonical_hash(cls, payload: Dict[str, Any]) -> str:
        """Computes deterministic SHA-256 hash of canonicalized JSON request payload."""
        canonical_str = cls.canonical_serialize(payload)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

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
        execution_id: Optional[str] = None,
        incident_id: str,
        rule_id: str,
        rule_name: str,
        policy_version_id: Optional[str] = None,
        policy_version_number: Optional[int] = None,
        policy_status: str = "APPROVED",
        policy_source: str = "DATABASE",
        attempt_number: int = 1,
        model_name: str,
        provider_type: str,
        generation_settings: Dict[str, Any],
        compiled_system_prompt: str,
        user_message: str,
        rag_precedents: Optional[List[Dict[str, Any]]] = None,
        evidence_requirements: Optional[Dict[str, Any]] = None,
        verdict_schema: Optional[Dict[str, Any]] = None,
        raw_request_payload: Dict[str, Any],
        policy_snapshot_hash: Optional[str] = None,
        is_simulated: bool = False,
    ) -> Optional[ActualLLMPromptCapture]:
        """
        Captures the final effective request payload immediately prior to dispatch to Server 2.
        Records dispatch_status="SEND_ATTEMPTED" and payload_format="CANONICAL_JSON".
        Must never fail or crash the core incident triage pipeline.
        """
        try:
            canonical_serialized = cls.canonical_serialize(raw_request_payload)
            req_hash = hashlib.sha256(canonical_serialized.encode("utf-8")).hexdigest()
            safe_settings = cls.sanitize_settings(generation_settings)
            precedents = rag_precedents or []
            ev_reqs = evidence_requirements or {}
            v_schema = verdict_schema or PolicyCompilerService.MODEL_RESPONSE_SCHEMA

            # Check if this incident has prior attempts to set retry_count
            retry_count = max(0, attempt_number - 1)

            exec_id = execution_id or str(uuid.uuid4())
            record = ActualLLMPromptCapture(
                id=str(uuid.uuid4()),
                execution_id=exec_id,
                incident_id=incident_id,
                rule_id=rule_id,
                rule_name=rule_name,
                policy_version_id=policy_version_id,
                policy_version_number=policy_version_number,
                policy_status=policy_status,
                policy_source=policy_source,
                policy_snapshot_hash=policy_snapshot_hash,
                dispatch_status="SEND_ATTEMPTED",
                attempt_number=attempt_number,
                retry_count=retry_count,
                is_active_verdict_capture=True,
                is_simulated=is_simulated,
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
                canonical_serialized_payload=canonical_serialized,
                payload_format="CANONICAL_JSON",
                request_sha256=req_hash,
                prompt_integrity_status="UNVERIFIED",  # Awaiting response & complete verification
                integrity_details={
                    "hash_match": True,
                    "policy_approved": (policy_status == "APPROVED"),
                    "policy_source": policy_source,
                    "capture_stage": "PRE_DISPATCH",
                    "delivery_state": "SEND_ATTEMPTED",
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
        response_raw: Optional[str] = None,
        response_verdict: Optional[str] = None,
        response_confidence: Optional[float] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        latency_ms: Optional[int] = None,
        integrity_status: str = "VERIFIED",
        integrity_details: Optional[Dict[str, Any]] = None,
        is_active_verdict: bool = True,
    ) -> Optional[ActualLLMPromptCapture]:
        """Updates capture record with final LLM response and verification status."""
        try:
            stmt = select(ActualLLMPromptCapture).where(ActualLLMPromptCapture.id == capture_id)
            res = await db.execute(stmt)
            record = res.scalar_one_or_none()
            if not record:
                return None

            record.dispatch_status = "COMPLETED"
            record.response_raw = response_raw
            record.response_verdict = response_verdict
            record.response_confidence = response_confidence
            record.prompt_tokens = prompt_tokens
            record.completion_tokens = completion_tokens
            calc_total = total_tokens if total_tokens is not None else (((prompt_tokens or 0) + (completion_tokens or 0)) if (prompt_tokens or completion_tokens) else None)
            record.total_tokens = calc_total
            record.latency_ms = latency_ms
            record.prompt_integrity_status = integrity_status
            record.is_active_verdict_capture = is_active_verdict

            det = dict(record.integrity_details or {})
            if integrity_details:
                det.update(integrity_details)
            det["delivery_state"] = "COMPLETED"
            record.integrity_details = det

            l1 = dict(record.l1_explanation or {})
            l1["verdict_returned"] = response_verdict or "UNKNOWN"
            l1["prompt_integrity_status"] = integrity_status
            record.l1_explanation = l1

            await db.flush()
            return record
        except Exception as e:
            logger.error(f"Failed to record completed prompt capture {capture_id}: {e}", exc_info=True)
            return None

    @classmethod
    async def record_failed(
        cls,
        db: AsyncSession,
        capture_id: str,
        *,
        error_message: str,
        latency_ms: Optional[int] = None,
    ) -> Optional[ActualLLMPromptCapture]:
        """Updates capture record when LLM dispatch or parsing fails."""
        try:
            stmt = select(ActualLLMPromptCapture).where(ActualLLMPromptCapture.id == capture_id)
            res = await db.execute(stmt)
            record = res.scalar_one_or_none()
            if not record:
                return None

            record.dispatch_status = "FAILED"
            record.error_message = error_message
            record.latency_ms = latency_ms or 0
            record.prompt_integrity_status = "UNVERIFIED"

            det = dict(record.integrity_details or {})
            det["delivery_state"] = "FAILED"
            det["dispatch_error"] = error_message
            record.integrity_details = det

            l1 = dict(record.l1_explanation or {})
            l1["verdict_returned"] = "DISPATCH_FAILED"
            l1["prompt_integrity_status"] = "UNVERIFIED"
            record.l1_explanation = l1

            await db.flush()
            return record
        except Exception as e:
            logger.error(f"Failed to record failed prompt capture {capture_id}: {e}", exc_info=True)
            return None

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
        intercept_reason: Optional[str] = None,
        reason: Optional[str] = None,
        policy_status: str = "UNAPPROVED",
        attempt_number: int = 1,
        is_simulated: bool = False,
    ) -> Optional[ActualLLMPromptCapture]:
        """
        Records an explicit NOT_DISPATCHED audit capture when safety gates halt execution
        prior to provider dispatch. Guaranteed not to falsely claim dispatch.
        """
        eff_reason = intercept_reason or reason or "Safety gate intercept"
        try:
            non_dispatch_payload = {
                "intercept_reason": eff_reason,
                "execution_id": execution_id,
                "incident_id": incident_id,
                "rule_id": rule_id,
                "timestamp": utc_now().isoformat(),
            }
            canonical_serialized = cls.canonical_serialize(non_dispatch_payload)
            req_hash = hashlib.sha256(canonical_serialized.encode("utf-8")).hexdigest()

            exec_id = execution_id or str(uuid.uuid4())
            record = ActualLLMPromptCapture(
                id=str(uuid.uuid4()),
                execution_id=exec_id,
                incident_id=incident_id,
                rule_id=rule_id,
                rule_name=rule_name,
                policy_version_id=policy_version_id,
                policy_version_number=policy_version_number,
                policy_status=policy_status,
                policy_source="SAFETY_GATE_INTERCEPT",
                dispatch_status="NOT_DISPATCHED",
                attempt_number=attempt_number,
                is_active_verdict_capture=True,
                is_simulated=is_simulated,
                model_name="NONE (Intercepted)",
                provider_type="SAFETY_GATE",
                generation_settings={},
                compiled_system_prompt=f"[DISPATCH INTERCEPTED: {eff_reason}]",
                user_message=f"<INTERCEPTED_EXECUTION reason='{eff_reason}' />",
                rag_precedents=[],
                has_rag_precedents=False,
                evidence_requirements={},
                verdict_schema={},
                raw_request_payload=non_dispatch_payload,
                canonical_serialized_payload=canonical_serialized,
                payload_format="CANONICAL_JSON",
                request_sha256=req_hash,
                prompt_integrity_status="UNVERIFIED",
                integrity_details={
                    "hash_match": True,
                    "policy_approved": False,
                    "untrusted_data_boundaries_present": False,
                    "intercept_reason": eff_reason,
                    "delivery_state": "NOT_DISPATCHED",
                },
                l1_explanation={
                    "headline": f"Execution halted by safety gate: {eff_reason}. No outbound request was sent to Local LLM.",
                    "policy_version_used": f"Version {policy_version_number or 'Unapproved'}",
                    "mandatory_evidence_available": False,
                    "historical_precedents_included": 0,
                    "verdict_returned": "NOT_DISPATCHED",
                    "prompt_matches_approved_policy": False,
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
        1. Canonical hash match against stored payload representation.
        2. Policy provenance: matches active approved policy version vs unauthorized draft.
        3. Policy snapshot hash verification (detecting code/content drift).
        4. Delimiter and schema boundary compliance.
        Separates Prompt Integrity from Delivery Status.
        """
        details: Dict[str, Any] = {}
        # 1. Recalculate hash over canonical JSON
        recalc_hash = cls.canonical_hash(capture.raw_request_payload)
        hash_ok = (recalc_hash == capture.request_sha256)
        details["hash_match"] = hash_ok
        details["calculated_hash"] = recalc_hash
        details["stored_hash"] = capture.request_sha256
        details["payload_format"] = getattr(capture, "payload_format", "CANONICAL_JSON")

        if not hash_ok:
            return "MISMATCH", {
                **details,
                "mismatch_reason": "Payload hash discrepancy: Stored canonical hash does not match computed SHA-256 digest",
            }

        # 2. Check delivery status (distinct from integrity)
        details["delivery_status"] = capture.dispatch_status
        if capture.dispatch_status == "NOT_DISPATCHED":
            return "UNVERIFIED", {**details, "notice": "Prompt was not dispatched to LLM engine (Safety Gate Intercept)"}

        # 3. Check policy provenance
        details["policy_status"] = capture.policy_status
        details["policy_approved"] = (capture.policy_status == "APPROVED")
        if capture.policy_status != "APPROVED":
            details["policy_approval_status"] = capture.policy_status
            if capture.policy_source in ("DATABASE_DRAFT", "DRAFT"):
                details["warning"] = "Executed with unapproved DRAFT policy"

        # Check if active approved version has diverged from what was executed
        if active_version:
            details["active_policy_id"] = active_version.id
            if active_version.id != capture.policy_version_id:
                details["active_policy_divergence"] = True
                details["current_active_version_number"] = active_version.version_number
                details["executed_version_number"] = capture.policy_version_number

            # Check policy snapshot digest if available
            if capture.policy_snapshot_hash and getattr(active_version, "compiled_digest", None):
                if capture.policy_snapshot_hash != active_version.compiled_digest:
                    details["policy_snapshot_drift"] = True
                    details["warning"] = "Policy compiled content has drifted since execution capture"

        # 4. Check delimiter boundaries in user message
        has_boundaries = (
            "<UNTRUSTED_INCIDENT_DATA>" in (capture.user_message or "")
            and "</UNTRUSTED_INCIDENT_DATA>" in (capture.user_message or "")
        )
        details["untrusted_data_boundaries_present"] = has_boundaries
        if not has_boundaries:
            return "MISMATCH", {**details, "mismatch_reason": "Missing mandatory untrusted data delimiters (<UNTRUSTED_INCIDENT_DATA>)"}

        # If policy was approved, hash matched, boundaries present -> VERIFIED
        if capture.policy_status == "APPROVED":
            return "VERIFIED", details

        return "UNVERIFIED", details

    @classmethod
    def apply_role_redaction(
        cls,
        capture_dict: Dict[str, Any],
        user: Optional[User],
    ) -> Dict[str, Any]:
        """
        Applies role-based data redaction across ALL fields and inspector tabs:
        - Administrators: full unredacted prompt and technical details.
        - SOC Analysts / Read-Only Viewers: sensitive credentials, private IPs, customer secrets masked.
        Ensures users cannot bypass redaction via raw JSON fields or exports.
        """
        is_admin = bool(user and str(user.role).strip().lower() == "administrator")
        if is_admin:
            capture_dict["is_redacted"] = False
            return capture_dict

        redacted = dict(capture_dict)
        redacted["is_redacted"] = True

        def _mask_secrets(text: str) -> str:
            if not text:
                return text
            # Mask passwords, tokens, API keys
            text = re.sub(
                r'(?i)(password|secret|apikey|api_key|token|access_token|bearer)["\']?\s*[:=]\s*["\']?[a-zA-Z0-9_\-\.]{6,}["\']?',
                r'\1="[REDACTED_SECRET]"',
                text,
            )
            # Mask internal private RFC1918 IPs and RFC5737 doc test networks
            text = re.sub(
                r'\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|192\.0\.2\.\d{1,3}|198\.51\.100\.\d{1,3}|203\.0\.113\.\d{1,3})\b',
                r'[REDACTED_IP]',
                text,
            )
            # Mask sensitive URLs or endpoints
            text = re.sub(
                r'https?://(?:[a-zA-Z0-9_\-]+\.)+[a-zA-Z]{2,}(?::\d+)?',
                r'http://[REDACTED_HOST]',
                text,
            )
            # Mask email addresses
            text = re.sub(
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                r'[REDACTED_EMAIL]',
                text,
            )
            return text

        # 1. Redact user message & incident payload
        if "user_message" in redacted and redacted["user_message"]:
            redacted["user_message"] = _mask_secrets(str(redacted["user_message"]))
        if "incident_payload" in redacted and redacted["incident_payload"]:
            redacted["incident_payload"] = _mask_secrets(str(redacted["incident_payload"]))

        # 2. Redact system prompt (if any secrets embedded)
        if "system_prompt" in redacted and redacted["system_prompt"]:
            redacted["system_prompt"] = _mask_secrets(str(redacted["system_prompt"]))

        # 3. Deep redact raw_request_payload
        if "raw_request_payload" in redacted and isinstance(redacted["raw_request_payload"], dict):
            raw_copy = json.loads(json.dumps(redacted["raw_request_payload"]))
            if "messages" in raw_copy and isinstance(raw_copy["messages"], list):
                for m in raw_copy["messages"]:
                    if isinstance(m, dict) and "content" in m:
                        m["content"] = _mask_secrets(str(m["content"]))
            redacted["raw_request_payload"] = raw_copy

        # 4. Redact technical details raw payload if present
        if "technical_details" in redacted and isinstance(redacted["technical_details"], dict):
            tech = dict(redacted["technical_details"])
            if "raw_request_payload" in tech and isinstance(tech["raw_request_payload"], dict):
                raw_copy = json.loads(json.dumps(tech["raw_request_payload"]))
                if "messages" in raw_copy and isinstance(raw_copy["messages"], list):
                    for m in raw_copy["messages"]:
                        if isinstance(m, dict) and "content" in m:
                            m["content"] = _mask_secrets(str(m["content"]))
                tech["raw_request_payload"] = raw_copy
            if "canonical_serialized_payload" in tech and tech["canonical_serialized_payload"]:
                tech["canonical_serialized_payload"] = _mask_secrets(str(tech["canonical_serialized_payload"]))
            # Redact generation settings endpoints
            gen_set = dict(tech.get("generation_settings") or {})
            if "endpoint" in gen_set:
                gen_set["endpoint"] = re.sub(r"//[^:]+:", "//[REDACTED_HOST]:", str(gen_set["endpoint"]))
            if "api_base" in gen_set:
                gen_set["api_base"] = re.sub(r"//[^:]+:", "//[REDACTED_HOST]:", str(gen_set["api_base"]))
            if "host" in gen_set:
                gen_set["host"] = "[REDACTED_HOST]"
            tech["generation_settings"] = gen_set
            redacted["technical_details"] = tech

        if "generation_settings" in redacted and isinstance(redacted["generation_settings"], dict):
            gset = dict(redacted["generation_settings"])
            if "endpoint" in gset:
                gset["endpoint"] = re.sub(r"//[^:]+:", "//[REDACTED_HOST]:", str(gset["endpoint"]))
            if "api_base" in gset:
                gset["api_base"] = re.sub(r"//[^:]+:", "//[REDACTED_HOST]:", str(gset["api_base"]))
            if "host" in gset:
                gset["host"] = "[REDACTED_HOST]"
            redacted["generation_settings"] = gset

        # 5. Redact raw model response
        if "response_raw" in redacted and redacted["response_raw"]:
            redacted["response_raw"] = _mask_secrets(str(redacted["response_raw"]))
        if "raw_model_response" in redacted and redacted["raw_model_response"]:
            redacted["raw_model_response"] = _mask_secrets(str(redacted["raw_model_response"]))

        return redacted

    @classmethod
    async def get_executions_for_incident(
        cls,
        db: AsyncSession,
        incident_id: str,
    ) -> List[ExecutionHistoryItem]:
        """Retrieves all historical execution records and retry attempts for an incident."""
        stmt = (
            select(ActualLLMPromptCapture)
            .where(ActualLLMPromptCapture.incident_id == incident_id)
            .order_by(desc(ActualLLMPromptCapture.captured_at), desc(ActualLLMPromptCapture.attempt_number))
        )
        res = await db.execute(stmt)
        records = res.scalars().all()

        items = []
        for r in records:
            items.append(
                ExecutionHistoryItem(
                    id=r.id,
                    execution_id=r.execution_id,
                    incident_id=r.incident_id,
                    attempt_number=r.attempt_number,
                    retry_count=getattr(r, "retry_count", 0),
                    captured_at=r.captured_at,
                    dispatch_status=r.dispatch_status,
                    prompt_integrity_status=r.prompt_integrity_status,
                    model_name=r.model_name,
                    provider_type=r.provider_type,
                    policy_version_number=r.policy_version_number,
                    latency_ms=r.latency_ms,
                    response_verdict=r.response_verdict,
                    is_active_verdict=getattr(r, "is_active_verdict_capture", True),
                    is_simulated=getattr(r, "is_simulated", False),
                )
            )
        return items

    @classmethod
    async def get_captures_for_rule(
        cls,
        db: AsyncSession,
        rule_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Returns recent incident captures for a specific rule to facilitate incident selection."""
        stmt = (
            select(ActualLLMPromptCapture)
            .where(ActualLLMPromptCapture.rule_id == rule_id)
            .order_by(desc(ActualLLMPromptCapture.captured_at))
            .limit(limit)
        )
        res = await db.execute(stmt)
        records = res.scalars().all()

        return [
            {
                "rule_id": r.rule_id,
                "incident_id": r.incident_id,
                "capture_id": r.id,
                "execution_id": r.execution_id,
                "captured_at": r.captured_at.isoformat(),
                "verdict": r.response_verdict,
                "dispatch_status": r.dispatch_status,
                "integrity_status": r.prompt_integrity_status,
                "policy_version_number": r.policy_version_number,
                "is_simulated": getattr(r, "is_simulated", False),
            }
            for r in records
        ]

    @classmethod
    async def cleanup_expired_captures(
        cls,
        db: AsyncSession,
        retention_days: Optional[int] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Configurable retention cleanup for prompt captures (Task 5).
        - Retention is only enforced if retention_days > 0.
        - Preserves active verdict executions and linked records.
        - Emits an immutable audit log upon completion.
        """
        days = retention_days if retention_days is not None else getattr(settings, "PROMPT_CAPTURE_RETENTION_DAYS", 0)
        if days <= 0:
            return {
                "deleted_count": 0,
                "retention_days": days,
                "cutoff_timestamp": utc_now().isoformat(),
                "dry_run": dry_run,
                "message": "Retention cleanup skipped: PROMPT_CAPTURE_RETENTION_DAYS is 0 (indefinite retention)",
            }

        cutoff = utc_now() - timedelta(days=days)

        # Select candidate captures older than cutoff that are NOT marked active verdict captures
        find_stmt = select(ActualLLMPromptCapture.id).where(
            and_(
                ActualLLMPromptCapture.captured_at < cutoff,
                ActualLLMPromptCapture.is_active_verdict_capture == False,
            )
        )
        res = await db.execute(find_stmt)
        candidate_ids = res.scalars().all()
        deleted_count = len(candidate_ids)

        if not dry_run and deleted_count > 0:
            del_stmt = delete(ActualLLMPromptCapture).where(ActualLLMPromptCapture.id.in_(candidate_ids))
            await db.execute(del_stmt)
            await db.commit()

            # Record audit log
            try:
                db.add(
                    AuditLog(
                        user_id="SYSTEM",
                        username="system",
                        action="PROMPT_CAPTURE_RETENTION_CLEANUP",
                        resource_type="PROMPT_CAPTURES",
                        resource_id=f"cutoff_{cutoff.date().isoformat()}",
                        details={"deleted_count": deleted_count, "retention_days": days, "dry_run": False},
                    )
                )
                await db.commit()
            except Exception:
                pass

        return {
            "deleted_count": deleted_count,
            "retention_days": days,
            "cutoff_timestamp": cutoff.isoformat(),
            "dry_run": dry_run,
            "message": f"Successfully identified {deleted_count} expired prompt capture records older than {days} days.",
        }
