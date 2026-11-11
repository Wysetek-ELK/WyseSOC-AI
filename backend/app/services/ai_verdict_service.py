import time
import asyncio
from datetime import datetime
from app.utils.datetime_utils import utc_now
from typing import Optional, List, Dict, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc, or_, func
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.incident import Incident
from app.models.rule import Rule
from app.models.learning import LearningRecord
from app.models.investigation import Investigation
from app.models.audit import AuditLog
from app.services.model_payload_allowlist import build_model_facing_payload
from app.services.model_provider.factory import get_model_provider
from app.services.prompt_studio_service import PromptStudioService, COMMON_SOC_BASELINE
from app.services.evidence_normalization_service import EvidenceNormalizationService
from app.services.evidence_contract_service import EvidenceContractService
from app.services.evidence_preflight_validator import EvidencePreflightValidator
from app.services.model_claim_extractor import ModelClaimExtractor
from app.services.independent_verdict_validator import IndependentVerdictValidator
from app.schemas.compiled_policy import CompilationExecutionMode
from app.services.policy_compiler_service import PolicyCompilerService
from app.services.verified_semantic_retrieval_service import VerifiedSemanticRetrievalService
from app.services.token_budget_service import TokenBudgetService
from app.services.provenance import classify_execution_provenance


class LocalLLMUnavailableError(Exception):
    """Raised when Server 2 Local LLM is offline or unreachable."""
    pass


class VerdictTriageAgent:
    """
    Agentic SOC Verdict Triage Agent.
    Executes zero-bias incident evaluations with strict ground-truth isolation,
    dynamic prompt synthesis (Level-2 SOC criteria + few-shot RAG),
    and resilient model provider fallback.
    """

    _last_probe_time: float = 0.0
    _is_local_llm_online: Optional[bool] = None
    _last_probed_base_url: Optional[str] = None
    _incident_locks: Dict[str, asyncio.Lock] = {}

    def __init__(self, db: AsyncSession):
        self.db = db

    @classmethod
    def _get_incident_lock(cls, incident_key: str) -> asyncio.Lock:
        try:
            loop_id = id(asyncio.get_running_loop())
        except RuntimeError:
            loop_id = 0
        scoped_key = f"{loop_id}:{incident_key}"
        lock = cls._incident_locks.get(scoped_key)
        if lock is None:
            lock = asyncio.Lock()
            cls._incident_locks[scoped_key] = lock
        return lock

    @staticmethod
    def _upsert_ai_verdict_note(inv: Investigation, note_entry: str) -> None:
        """Idempotently inserts or updates automated AI Verdict note without duplicating on reevaluation."""
        if not inv or inv.analyst_verdict:
            return
        existing = inv.analyst_notes or ""
        if note_entry in existing:
            return
        lines = [line for line in existing.split("\n\n") if line.strip() and not line.strip().startswith("[AI Verdict (")]
        lines.append(note_entry)
        inv.analyst_notes = "\n\n".join(lines)
        inv.updated_at = utc_now()

    @staticmethod
    async def _assert_lock_held(db: AsyncSession, lock_key: Optional[str], lock_owner_id: Optional[str]) -> None:
        if lock_key and lock_owner_id:
            from app.services.distributed_lock import DistributedLockManager, DistributedLockLostError
            held = await DistributedLockManager.verify_or_renew(
                db, lock_key=lock_key, owner_id=lock_owner_id, ttl_seconds=120
            )
            if not held:
                await db.rollback()
                raise DistributedLockLostError(
                    f"Distributed lease lost or expired before commit for '{lock_key}' (owner={lock_owner_id})."
                )

    @classmethod
    async def is_local_llm_available(cls, force_refresh: bool = False) -> bool:
        """Checks if Server 2 LLM endpoint is reachable, caching positive status for 30s and offline status for 8s."""
        from app.services.llm_config_service import LLMConfigService
        if LLMConfigService.sync_runtime_settings():
            force_refresh = True

        current_base_url = str(getattr(settings, "LOCAL_LLM_BASE_URL", "") or "").rstrip("/")
        if cls._last_probed_base_url != current_base_url:
            force_refresh = True

        now = time.time()
        cache_ttl = 30.0 if cls._is_local_llm_online else 8.0
        if not force_refresh and cls._is_local_llm_online is not None and (now - cls._last_probe_time) < cache_ttl:
            return cls._is_local_llm_online

        cls._last_probe_time = now
        cls._last_probed_base_url = current_base_url
        provider = get_model_provider("OPENAI_COMPATIBLE")
        try:
            health = await provider.get_health()
            cls._is_local_llm_online = (health.status == "HEALTHY")
        except Exception:
            cls._is_local_llm_online = False
        return cls._is_local_llm_online

    async def get_pending_incident_count(self) -> int:
        """Returns the number of incidents currently awaiting an AI verdict."""
        res = await self.db.execute(
            select(func.count(Incident.id)).where(Incident.ai_verdict.is_(None))
        )
        return res.scalar() or 0

    async def evaluate_incident(
        self,
        incident_id_or_obj: Union[str, Incident],
        username: str = "system",
        model_provider_type: Optional[str] = None,
        allow_simulated_fallback: bool = False,
        only_if_pending: bool = False,
        pilot_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates a single incident with the LLM.
        Coordinates across intra-process coroutines and cross-process DB/Redis locks,
        auto-provisions detection rules if unmapped, formats allowlisted model telemetry,
        and saves the structured verdict to the database.
        """
        from app.services.distributed_lock import DistributedLockManager

        clean_target_id = incident_id_or_obj if isinstance(incident_id_or_obj, str) else str(getattr(incident_id_or_obj, "incident_id", None) or getattr(incident_id_or_obj, "id", ""))
        canonical_key = clean_target_id
        if not isinstance(incident_id_or_obj, str) and getattr(incident_id_or_obj, "incident_id", None):
            canonical_key = str(incident_id_or_obj.incident_id)

        pre_stmt = select(Incident.incident_id, Incident.id).where(
            (Incident.id == clean_target_id) | (Incident.incident_id == clean_target_id)
        )
        pre_res = await self.db.execute(pre_stmt)
        pre_row = pre_res.first()
        if not pre_row:
            raise ValueError(f"Incident '{clean_target_id}' not found.")
        canonical_key = str(pre_row[0] or pre_row[1] or clean_target_id)

        inc_lock = self._get_incident_lock(canonical_key)
        async with inc_lock:
            lock_key = f"incident_triage:{canonical_key}"
            async with DistributedLockManager.acquire(
                self.db,
                lock_key=lock_key,
                ttl_seconds=120,
                acquire_timeout_seconds=30.0,
            ) as lock_owner_id:
                # Reload authoritative DB state inside locks to prevent stale snapshots or duplicate triage
                stmt = (
                    select(Incident)
                    .where((Incident.id == clean_target_id) | (Incident.incident_id == clean_target_id))
                    .options(selectinload(Incident.rule), selectinload(Incident.events))
                    .execution_options(populate_existing=True)
                )
                res = await self.db.execute(stmt)
                incident = res.scalar_one_or_none()
                if not incident:
                    raise ValueError(f"Incident '{clean_target_id}' not found.")

                if only_if_pending and not pilot_context and isinstance(incident.ai_verdict, dict):
                    return incident.ai_verdict

                return await self._evaluate_incident_locked(
                    incident=incident,
                    username=username,
                    model_provider_type=model_provider_type,
                    allow_simulated_fallback=allow_simulated_fallback,
                    lock_key=lock_key,
                    lock_owner_id=lock_owner_id,
                    pilot_context=pilot_context,
                )

    async def _evaluate_incident_locked(
        self,
        incident: Incident,
        username: str = "system",
        model_provider_type: Optional[str] = None,
        allow_simulated_fallback: bool = False,
        lock_key: Optional[str] = None,
        lock_owner_id: Optional[str] = None,
        pilot_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Protected single-incident evaluation execution under per-incident concurrency lock."""
        is_shadow_pilot = bool(pilot_context and str(pilot_context.get("mode", "")).upper() == "SHADOW")
        if pilot_context and str(pilot_context.get("source_type", "")).upper() == "LIVE":
            allow_simulated_fallback = False
        prev_attempts = 0
        if isinstance(incident.ai_verdict, dict):
            prev_attempts = int(incident.ai_verdict.get("reevaluation_attempts", 0) or 0)

        # 2. Auto-resolve Rule if incident is unmapped
        rule = incident.rule
        if not rule and incident.event_type:
            r_q = await self.db.execute(
                select(Rule).where((Rule.event_type == incident.event_type) | (Rule.rule_id == incident.event_type))
            )
            rule = r_q.scalars().first()

            if not rule:
                rule = Rule(
                    rule_id=incident.event_type,
                    name=incident.title if incident.title and incident.title != "No description provided by SIEM." else incident.event_type,
                    event_type=incident.event_type,
                    severity=incident.severity or "MEDIUM",
                    description=f"Auto-mapped SIEM detection rule for {incident.event_type}",
                    status="ACTIVE",
                )
                self.db.add(rule)
                await self.db.flush()

            incident.rule_id = rule.id
            incident.rule = rule
            self.db.add(incident)
            await self.db.flush()

            # Link any sibling unmapped incidents sharing this event_type
            await self.db.execute(
                update(Incident)
                .where(Incident.event_type == incident.event_type, Incident.rule_id.is_(None))
                .values(rule_id=rule.id)
            )

        # 3. Canonical Evidence Normalization (P2-REQ-01)
        norm_result = EvidenceNormalizationService.normalize_incident_evidence(
            incident=incident,
            events=incident.events or [],
        )

        # 3b. Build model-facing payload (strict allowlist - zero ground-truth leakage)
        payload_dict = build_model_facing_payload(
            incident=incident,
            rule=rule,
            events=incident.events or [],
        )
        payload_dict["canonical_evidence"] = [r.model_dump() for r in norm_result.records]

        # 4. Resolve evaluation mode & Model Availability Guard (REQ-02 / AV-004)
        is_prod = getattr(settings, "APP_ENV", "development").lower() in ("production", "prod")
        if is_prod or (pilot_context and str(pilot_context.get("source_type", "")).upper() == "LIVE"):
            allow_mock = False
        else:
            allow_mock = allow_simulated_fallback or getattr(settings, "LOCAL_LLM_ALLOW_MOCK_FALLBACK", False)

        if not allow_mock and not model_provider_type:
            is_online = await self.is_local_llm_available()
            if not is_online:
                raise LocalLLMUnavailableError(
                    "Local LLM (Server 2) is currently offline. AI verdict generation is deferred until Local LLM comes online."
                )

        # 4b. Resolve prompt text with Level-2 SOC criteria
        prompt_service = PromptStudioService(self.db)
        prompt_text = COMMON_SOC_BASELINE
        prompt_ver_num = 1

        active_v = None
        if rule:
            rp = await prompt_service.get_or_create_rule_prompt(rule.id)
            if rp and rp.active_version_id and rp.versions:
                candidate = next((v for v in rp.versions if v.id == rp.active_version_id), None)
                if candidate and candidate.status == "APPROVED":
                    active_v = candidate
        else:
            rp = None

        # REQ-03 (AV-001 & AV-002): Refuse to evaluate with unapproved prompt drafts or unmapped rule policy in live triage
        if not active_v:
            if not allow_simulated_fallback or is_prod:
                deferral_detail = (
                    "DETECTION_POLICY_PENDING_APPROVAL: No approved investigation policy exists for this detection rule. Triage deferred to human analyst."
                    if rule
                    else "DETECTION_POLICY_PENDING_APPROVAL: Incident has no matched approved detection rule policy. Triage deferred to human analyst."
                )
                verdict_data = {
                    "incident_id": incident.incident_id,
                    "proposed_verdict": "REQUIRES_ATTENTION",
                    "verdict": "REQUIRES_ATTENTION",
                    "confidence": 0.0,
                    "raw_model_confidence": 0.0,
                    "reason": deferral_detail,
                    "supporting_evidence": [],
                    "missing_evidence": ["Approved detection rule investigation policy (Studio approval required)"],
                    "analyst_questions": ["Please review and approve the detection policy in Agent Intelligence Studio."],
                    "latency_ms": 0,
                    "model_identifier": "POLICY_GUARD",
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "is_simulated": False,
                    "execution_provenance": "POLICY_GUARD",
                    "configured_provider": "POLICY_GUARD",
                    "test_environment": classify_execution_provenance(model_identifier="POLICY_GUARD")["test_environment"],
                    "validation_status": "POLICY_NOT_APPROVED",
                    "validation_reason_codes": ["POLICY_NOT_APPROVED", "EVIDENCE_CONTRACT_UNVERIFIED"],
                    "is_decisive_accepted": False,
                    "proposal_validation_outcome": "POLICY_NOT_APPROVED",
                    "final_disposition": "DEFERRED_PENDING_POLICY_APPROVAL",
                    "abstention_reason": deferral_detail,
                    "evidence_completeness": 0.0,
                    "grounding_ratio": 0.0,
                    "canonical_evidence_count": norm_result.total_evidence_count,
                    "reevaluation_eligible": True,
                    "deferral_reason": "POLICY_NOT_APPROVED",
                    "reevaluation_attempts": prev_attempts + 1,
                    "rule_name": rule.name if rule else incident.title,
                    "severity": incident.severity,
                    "evaluated_at": utc_now().isoformat(),
                    "evaluated_by_user": username,
                }
                await self._assert_lock_held(self.db, lock_key, lock_owner_id)
                if not is_shadow_pilot:
                    incident.ai_verdict = verdict_data
                    self.db.add(incident)

                    # Sync with Investigation record if present (idempotent upsert)
                    inv_q = await self.db.execute(
                        select(Investigation).where(Investigation.incident_id == incident.id)
                    )
                    inv = inv_q.scalars().first()
                    if inv and not inv.analyst_verdict:
                        note_entry = f"[AI Verdict (REQUIRES_ATTENTION - 0%)]: {verdict_data['reason']}"
                        self._upsert_ai_verdict_note(inv, note_entry)
                        self.db.add(inv)

                audit = AuditLog(
                    user_id="SYSTEM" if username in ("system", "scheduler") else username,
                    username=username,
                    action="AI_VERDICT_EVALUATE",
                    resource_type="INCIDENT",
                    resource_id=incident.incident_id,
                    details={
                        "verdict": "REQUIRES_ATTENTION",
                        "confidence": 0.0,
                        "validation_status": "POLICY_NOT_APPROVED",
                        "reason": verdict_data["reason"],
                    },
                )
                self.db.add(audit)
                await self.db.commit()
                return verdict_data
            else:
                # In simulation / test mode, allow testing with draft version if available
                if rp and rp.versions:
                    active_v = rp.versions[0]

        # P2-REQ-02: Resolve Evidence Contract for the rule and active policy
        contract = EvidenceContractService.get_contract_for_rule(rule, active_v)

        # P2-REQ-03: Preflight Evidence Validation
        preflight = EvidencePreflightValidator.validate_preflight(
            incident_id=incident.incident_id,
            contract=contract,
            normalization_result=norm_result,
            allow_simulation=allow_mock,
        )

        # Preflight Gate: If critical required telemetry is missing in live triage, abstain immediately
        if preflight.must_abstain_immediately and (not allow_simulated_fallback or is_prod):
            verdict_data = {
                "incident_id": incident.incident_id,
                "proposed_verdict": "REQUIRES_ATTENTION",
                "verdict": "REQUIRES_ATTENTION",
                "confidence": 0.0,
                "raw_model_confidence": 0.0,
                "reason": f"CRITICAL_TELEMETRY_MISSING: {preflight.reason}",
                "supporting_evidence": [],
                "missing_evidence": preflight.missing_evidence_fields,
                "analyst_questions": [f"Review missing critical telemetry: {', '.join(preflight.critical_missing_fields)}"],
                "latency_ms": 0,
                "model_identifier": "PREFLIGHT_GUARD",
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "is_simulated": False,
                "execution_provenance": "PREFLIGHT_GUARD",
                "configured_provider": "POLICY_GUARD",
                "test_environment": classify_execution_provenance(model_identifier="PREFLIGHT_GUARD")["test_environment"],
                "validation_status": preflight.preflight_status,
                "validation_reason_codes": ["EVIDENCE_MISSING"] if preflight.critical_missing_fields else ["EVIDENCE_CONTRACT_UNVERIFIED"],
                "is_decisive_accepted": False,
                "proposal_validation_outcome": "PREFLIGHT_EVIDENCE_INSUFFICIENT",
                "final_disposition": "SAFE_ANALYST_ESCALATION",
                "abstention_reason": preflight.reason,
                "evidence_completeness": preflight.evidence_completeness,
                "grounding_ratio": 0.0,
                "canonical_evidence_count": norm_result.total_evidence_count,
                "contract_id": contract.contract_id,
                "contract_version": contract.version_number,
                "validator_version": IndependentVerdictValidator.VALIDATOR_VERSION,
                "reevaluation_eligible": True,
                "deferral_reason": preflight.preflight_status,
                "reevaluation_attempts": prev_attempts + 1,
                "rule_name": rule.name if rule else incident.title,
                "severity": incident.severity,
                "evaluated_at": utc_now().isoformat(),
                "evaluated_by_user": username,
            }
            await self._assert_lock_held(self.db, lock_key, lock_owner_id)
            if not is_shadow_pilot:
                incident.ai_verdict = verdict_data
                self.db.add(incident)

                inv_q = await self.db.execute(
                    select(Investigation).where(Investigation.incident_id == incident.id)
                )
                inv = inv_q.scalars().first()
                if inv and not inv.analyst_verdict:
                    note_entry = f"[AI Verdict (REQUIRES_ATTENTION - 0%)]: {verdict_data['reason']}"
                    self._upsert_ai_verdict_note(inv, note_entry)
                    self.db.add(inv)

            audit = AuditLog(
                user_id="SYSTEM" if username in ("system", "scheduler") else username,
                username=username,
                action="AI_VERDICT_EVALUATE",
                resource_type="INCIDENT",
                resource_id=incident.incident_id,
                details={
                    "verdict": "REQUIRES_ATTENTION",
                    "confidence": 0.0,
                    "validation_status": preflight.preflight_status,
                    "reason": verdict_data["reason"],
                },
            )
            self.db.add(audit)
            await self.db.commit()
            return verdict_data

        # P3-REQ-01: Compile Unified Nine-Section Policy
        exec_mode = CompilationExecutionMode.LIVE if (is_prod or not allow_mock) else CompilationExecutionMode.SIMULATION
        compiled_policy = PolicyCompilerService.compile_policy(
            rule=rule,
            prompt_version=active_v,
            execution_mode=exec_mode,
            raise_on_unapproved=False,
        )
        prompt_ver_num = compiled_policy.version_number or 1

        # P3-REQ-03 & P3-REQ-04: Rule-Specific Verified Semantic RAG
        rag_result = await VerifiedSemanticRetrievalService.retrieve_verified_precedents(
            db=self.db,
            incident=incident,
            rule_id=rule.id if rule else "UNKNOWN_RULE",
            max_precedents=2,
        )

        # P3-REQ-05: Evidence-Preserving Token Budgeting
        payload_dict["evidence_contract"] = {
            "contract_id": contract.contract_id,
            "version": contract.version_number,
            "required_fields": [r.field for r in contract.required_evidence],
        }
        budgeted = TokenBudgetService.budget_prompt(
            compiled_policy=compiled_policy,
            incident_payload=payload_dict,
            rag_block=rag_result.formatted_rag_block,
            max_context_tokens=int(getattr(settings, "LOCAL_LLM_CONTEXT_BUDGET", 4096) or 4096),
            max_completion_tokens=int(getattr(settings, "LOCAL_LLM_MAX_TOKENS", 512) or 512),
        )

        # Context Overflow Gate: If mandatory core exceeds context window, abstain safely
        if not budgeted.can_proceed_to_inference:
            verdict_data = {
                "incident_id": incident.incident_id,
                "proposed_verdict": "REQUIRES_ATTENTION",
                "verdict": "REQUIRES_ATTENTION",
                "confidence": 0.0,
                "raw_model_confidence": 0.0,
                "reason": budgeted.abstention_reason or "CONTEXT_WINDOW_EXCEEDED",
                "supporting_evidence": [],
                "missing_evidence": ["Reduced telemetry size (exceeds model context limit)"],
                "analyst_questions": ["Please inspect raw incident logs directly in SIEM."],
                "latency_ms": 0,
                "model_identifier": "TOKEN_BUDGET_GUARD",
                "prompt_tokens": budgeted.breakdown.total_prompt_tokens,
                "completion_tokens": 0,
                "total_tokens": budgeted.breakdown.total_prompt_tokens,
                "is_simulated": False,
                "execution_provenance": "TOKEN_BUDGET_GUARD",
                "configured_provider": "POLICY_GUARD",
                "test_environment": classify_execution_provenance(model_identifier="TOKEN_BUDGET_GUARD")["test_environment"],
                "validation_status": "CONTEXT_WINDOW_EXCEEDED",
                "validation_reason_codes": ["CONTEXT_WINDOW_EXCEEDED"],
                "is_decisive_accepted": False,
                "proposal_validation_outcome": "CONTEXT_BUDGET_EXCEEDED",
                "final_disposition": "SAFE_ANALYST_ESCALATION",
                "abstention_reason": budgeted.abstention_reason or "CONTEXT_WINDOW_EXCEEDED",
                "evidence_completeness": preflight.evidence_completeness,
                "grounding_ratio": 0.0,
                "canonical_evidence_count": norm_result.total_evidence_count,
                "contract_id": contract.contract_id,
                "contract_version": contract.version_number,
                "validator_version": IndependentVerdictValidator.VALIDATOR_VERSION,
                "compiler_version": compiled_policy.compiler_version,
                "compilation_digest": compiled_policy.compilation_digest,
                "policy_sections_count": len(compiled_policy.sections),
                "calibration_status": "NOT_CALIBRATED",
                "is_calibrated": False,
                "reevaluation_eligible": True,
                "deferral_reason": "CONTEXT_WINDOW_EXCEEDED",
                "reevaluation_attempts": prev_attempts + 1,
                "rule_name": rule.name if rule else incident.title,
                "severity": incident.severity,
                "evaluated_at": utc_now().isoformat(),
                "evaluated_by_user": username,
            }
            await self._assert_lock_held(self.db, lock_key, lock_owner_id)
            if not is_shadow_pilot:
                incident.ai_verdict = verdict_data
                self.db.add(incident)
            await self.db.commit()
            return verdict_data

        prompt_text = budgeted.budgeted_system_prompt
        if budgeted.budgeted_rag_block:
            prompt_text += f"\n\n{budgeted.budgeted_rag_block}"
        payload_dict = budgeted.budgeted_incident_payload

        rule_spec = {
            "id": rule.id if rule else (incident.rule_id or "UNKNOWN"),
            "name": rule.name if rule else incident.title,
            "severity": rule.severity if rule else incident.severity,
            "description": rule.description if rule else "",
        }

        # 5. Invoke Model Provider with strict offline enforcement (REQ-02 / AV-004)
        if model_provider_type:
            if is_prod and model_provider_type == "SIMULATED":
                raise ValueError("Simulated model provider is strictly forbidden in production mode.")
            chosen_provider_type = model_provider_type
        else:
            if allow_mock:
                is_online = await self.is_local_llm_available()
                chosen_provider_type = "OPENAI_COMPATIBLE" if is_online else "SIMULATED"
            else:
                chosen_provider_type = "OPENAI_COMPATIBLE"

        provider = get_model_provider(chosen_provider_type)

        use_gpu_manager = (chosen_provider_type == "OPENAI_COMPATIBLE")
        if use_gpu_manager:
            from app.services.gpu_manager import gpu_workload_manager, CircuitBreakerOpenException
            try:
                await gpu_workload_manager.acquire_inference_slot()
            except CircuitBreakerOpenException as cb_exc:
                if not allow_mock:
                    raise LocalLLMUnavailableError(str(cb_exc))
                chosen_provider_type = "SIMULATED"
                provider = get_model_provider("SIMULATED")
                use_gpu_manager = False

        try:
            verdict = await provider.analyze_incident(
                incident_payload=payload_dict,
                rule_spec=rule_spec,
                prompt_text=prompt_text,
                prompt_version_number=prompt_ver_num,
            )
            
            # Check if OPENAI_COMPATIBLE provider suffered an actual connection failure or HTTP error
            # NOTE: INVALID_SCHEMA / UNEXPECTED_VERDICT mean the LLM responded over HTTP 200 with malformed output
            # and must NOT trip the circuit breaker or silently swap to mock simulation.
            is_connection_error = getattr(verdict, "validation_status", "") in ("CONNECTION_ERROR", "HTTP_ERROR")
            if use_gpu_manager:
                if is_connection_error:
                    await gpu_workload_manager.release_inference_slot(success=False, error_message=getattr(verdict, "reason", "connection failure"))
                else:
                    await gpu_workload_manager.release_inference_slot(success=True)
                use_gpu_manager = False  # Released

            if is_connection_error:
                self.__class__._is_local_llm_online = False
                if allow_mock:
                    sim_provider = get_model_provider("SIMULATED")
                    verdict = await sim_provider.analyze_incident(
                        incident_payload=payload_dict,
                        rule_spec=rule_spec,
                        prompt_text=prompt_text,
                        prompt_version_number=prompt_ver_num,
                    )
                else:
                    raise LocalLLMUnavailableError(f"Local LLM connection error: {verdict.reason}")
            else:
                # Successfully received response from Server 2
                self.__class__._is_local_llm_online = True
        except Exception as exc:
            if use_gpu_manager:
                await gpu_workload_manager.release_inference_slot(success=False, error_message=str(exc))
                use_gpu_manager = False
            self.__class__._is_local_llm_online = False
            if allow_mock and not isinstance(exc, LocalLLMUnavailableError):
                sim_provider = get_model_provider("SIMULATED")
                verdict = await sim_provider.analyze_incident(
                    incident_payload=payload_dict,
                    rule_spec=rule_spec,
                    prompt_text=prompt_text,
                    prompt_version_number=prompt_ver_num,
                )
            else:
                if isinstance(exc, LocalLLMUnavailableError):
                    raise exc
                raise LocalLLMUnavailableError(f"Local LLM inference failed: {str(exc)}") from exc

        p_tokens = getattr(verdict, "prompt_tokens", 0) or 0
        c_tokens = getattr(verdict, "completion_tokens", 0) or 0
        t_tokens = getattr(verdict, "total_tokens", 0) or (p_tokens + c_tokens)
        token_usage_source = "API_USAGE"
        if t_tokens == 0 and getattr(verdict, "validation_status", "VALID") in ("VALID", None) or getattr(verdict, "is_simulated", False):
            if t_tokens == 0:
                p_tokens = max(50, len(prompt_text) // 4)
                c_tokens = max(20, len(verdict.reason) // 4)
                t_tokens = p_tokens + c_tokens
                token_usage_source = "ESTIMATED"
        elif t_tokens == 0:
            token_usage_source = "UNAVAILABLE"

        # P2-REQ-04: Structured Claim Extraction and Grounding
        raw_verdict_dict = verdict.model_dump() if hasattr(verdict, "model_dump") else (verdict.dict() if hasattr(verdict, "dict") else {
            "verdict": verdict.verdict,
            "confidence": verdict.confidence,
            "reason": verdict.reason,
            "supporting_evidence": verdict.supporting_evidence,
            "supporting_claims": getattr(verdict, "supporting_claims", []),
            "contradictory_evidence": getattr(verdict, "contradictory_evidence", []),
            "validation_status": getattr(verdict, "validation_status", "VALID"),
        })
        claim_grounding = ModelClaimExtractor.extract_and_ground_claims(
            incident_id=incident.incident_id,
            raw_verdict_output=raw_verdict_dict,
            normalization_result=norm_result,
        )

        # P2-REQ-05 & P2-REQ-06: Independent Deterministic Verdict Validation
        val_res = IndependentVerdictValidator.validate_verdict(
            incident_id=incident.incident_id,
            proposed_verdict=verdict.verdict,
            raw_model_confidence=verdict.confidence,
            preflight=preflight,
            claim_grounding=claim_grounding,
            normalization_result=norm_result,
            contract=contract,
            allow_simulation=allow_mock,
            compilation_digest=compiled_policy.compilation_digest,
            model_reason=verdict.reason,
            contradictory_evidence=getattr(verdict, "contradictory_evidence", None),
        )

        # AIS 2.1: Unified Verdict Trustworthiness & Real Empirical Calibration Lookup
        from app.services.policy_simulation_service import PolicySimulationService
        from app.services.verdict_trustworthiness_engine import VerdictTrustworthinessEngine
        from app.models.verdict_intelligence import VerdictTrustAssessmentRecord, EvidenceSufficiencyAssessmentRecord
        from app.models.rule_intelligence import RuleIntelligenceSnapshot
        from app.schemas.verdict_intelligence import UserVisibleVerdict

        hist_stats = await PolicySimulationService(self.db).get_rule_calibration_stats(rule.id if rule else None)
        snap = None
        if rule:
            snap_res = await self.db.execute(select(RuleIntelligenceSnapshot).where(RuleIntelligenceSnapshot.rule_id == rule.id))
            snap = snap_res.scalars().first()

        auth_threshold = snap.threshold if snap else None
        def_status = snap.definition_status if snap else (
            (rule.parsed_metadata or {}).get("definition_status", "VERIFIED") if rule else "INCOMPLETE"
        )

        trust_payload = dict(payload_dict)
        trust_payload["rule_id"] = rule.rule_id if rule else incident.event_type
        trust_payload["prompt_version_number"] = compiled_policy.version_number
        trust_payload["contract_version"] = contract.status
        trust_res = VerdictTrustworthinessEngine.evaluate_verdict_trust(
            incident_payload=trust_payload,
            model_output=raw_verdict_dict,
            contract=contract,
            archetype_id=getattr(contract, "detection_archetype", None) or (snap.primary_archetype if snap else None),
            authoritative_threshold=auth_threshold,
            definition_status=def_status,
            historical_sample_count=int(hist_stats.get("sample_count", 0)),
            historical_accuracy=hist_stats.get("accuracy"),
            is_calibrated=bool(hist_stats.get("is_calibrated", False)),
        )

        # Reconcile authoritative live verdict with AIS 2.1 hard safety guardrails
        # (cold-start uncalibrated score <= 6 alone does not block contract-approved valid triage,
        #  whereas missing mandatory telemetry, contradictions, ungrounded/empty claims, incomplete threshold,
        #  or unsupported FP assumptions strictly enforce REQUIRES_ATTENTION).
        final_auth_verdict = val_res.final_verdict
        final_is_decisive = val_res.is_decisive_accepted
        final_validation_status = val_res.validation_status
        final_reason_codes = list(val_res.validation_reason_codes)
        final_confidence_display = val_res.validated_confidence_display if val_res.validated_confidence_display is not None else verdict.confidence
        final_action_directive = val_res.analyst_action_directive

        raw_provider_status = str(getattr(verdict, "validation_status", "VALID") or "VALID").upper().strip()
        if raw_provider_status in ("INVALID_SCHEMA", "UNEXPECTED_VERDICT", "INVALID_MODEL_OUTPUT", "PARSE_ERROR") or "MODEL_OUTPUT_INVALID" in final_reason_codes:
            final_auth_verdict = "REQUIRES_ATTENTION"
            final_is_decisive = False
            final_validation_status = "INVALID_MODEL_OUTPUT"
            final_confidence_display = 0.0
            if "MODEL_OUTPUT_INVALID" not in final_reason_codes:
                final_reason_codes.append("MODEL_OUTPUT_INVALID")
            final_action_directive = (
                "Model returned malformed or invalid structured output; safely abstained and routed to analyst review."
            )

        if final_validation_status == "INVALID_MODEL_OUTPUT":
            proposal_validation_outcome = "INVALID_MODEL_OUTPUT"
            final_disposition = "SAFE_ABSTENTION_AFTER_INVALID_OUTPUT"
            abstention_reason = final_action_directive
        elif final_is_decisive and final_auth_verdict in ("TRUE_POSITIVE", "FALSE_POSITIVE"):
            proposal_validation_outcome = "VALID_DECISIVE_PROPOSAL"
            final_disposition = "ACCEPTED_DECISIVE_VERDICT"
            abstention_reason = None
        elif val_res.proposed_verdict != final_auth_verdict or final_validation_status in ("REJECTED", "INSUFFICIENT_EVIDENCE", "GUARDRAIL_ABSTAINED"):
            proposal_validation_outcome = "REJECTED_BY_VALIDATOR"
            final_disposition = "OVERRULED_TO_ANALYST_ATTENTION"
            abstention_reason = final_action_directive or "; ".join(final_reason_codes)
        else:
            proposal_validation_outcome = "MODEL_ABSTENTION"
            final_disposition = "SAFE_ANALYST_ESCALATION"
            abstention_reason = final_action_directive or "Model recommended cautious analyst escalation."

        if final_auth_verdict in ("TRUE_POSITIVE", "FALSE_POSITIVE") and trust_res.effective_verdict == UserVisibleVerdict.REQUIRES_ANALYST_ATTENTION:
            esc_lower = (trust_res.escalation_reason or "").lower()
            is_hard_guardrail_block = bool(
                trust_res.missing_evidence
                or trust_res.contradictory_evidence
                or (trust_res.claim_verification and (trust_res.claim_verification.has_unsupported_assertions or trust_res.claim_verification.has_contradictions or trust_res.claim_verification.grounded_claims == 0))
                or "siem detection threshold" in esc_lower
                or "threshold is unverified" in esc_lower
                or "incomplete" in esc_lower
                or "business authorization" in esc_lower
                or "alert firing alone" in esc_lower
            )
            if is_hard_guardrail_block:
                final_auth_verdict = "REQUIRES_ATTENTION"
                final_is_decisive = False
                final_validation_status = "GUARDRAIL_ABSTAINED"
                final_confidence_display = 0.0
                if "TRUST_GUARDRAIL_BLOCK" not in final_reason_codes:
                    final_reason_codes.append("TRUST_GUARDRAIL_BLOCK")
                if trust_res.escalation_reason:
                    final_action_directive = trust_res.escalation_reason

        if final_validation_status == "INVALID_MODEL_OUTPUT":
            note_invalid = (
                "INVALID_MODEL_OUTPUT: Malformed or unparseable model verdict forced safe abstention and minimal trust (<= 2/10)."
            )
            if note_invalid not in trust_res.confidence_limitations:
                trust_res.confidence_limitations.append(note_invalid)
            if trust_res.trust_score is not None:
                trust_res.trust_score = min(2, trust_res.trust_score)
        elif val_res.detected_contradictions or final_validation_status == "REJECTED" or "EVIDENCE_CONTRADICTION" in final_reason_codes:
            if trust_res.trust_score is not None:
                trust_res.trust_score = min(3, trust_res.trust_score)

        # Verify distributed lock lease is still owned by this worker before staging any DB writes
        await self._assert_lock_held(self.db, lock_key, lock_owner_id)

        # Persist AIS 2.1 assessment records alongside live verdict
        if trust_res.evidence_sufficiency is not None:
            suff = trust_res.evidence_sufficiency
            self.db.add(EvidenceSufficiencyAssessmentRecord(
                incident_id=incident.incident_id,
                rule_id=rule.id if rule else incident.event_type,
                archetype=suff.archetype,
                overall_sufficiency_score=suff.overall_sufficiency_score,
                required_coverage_score=suff.required_coverage_score,
                integrity_provenance_score=suff.integrity_provenance_score,
                consistency_corroboration_score=suff.consistency_corroboration_score,
                freshness_relevance_score=suff.freshness_relevance_score,
                evidence_status=suff.evidence_status.value,
                mandatory_fields_present=suff.mandatory_fields_present,
                mandatory_fields_missing=suff.mandatory_fields_missing,
                conditional_fields_evaluated=suff.conditional_fields_evaluated,
                optional_enrichment_present=suff.optional_enrichment_present,
                unsupported_fields_requested=suff.unsupported_fields_requested,
                contradictions_detected=suff.contradictions_detected,
                evaluated_at=utc_now(),
            ))

        self.db.add(VerdictTrustAssessmentRecord(
            incident_id=incident.incident_id,
            rule_id=rule.id if rule else incident.event_type,
            archetype=trust_res.archetype,
            suggested_verdict=trust_res.suggested_verdict,
            effective_verdict=trust_res.effective_verdict.value,
            trust_score=trust_res.trust_score,
            raw_trust_score=trust_res.raw_trust_score,
            evidence_sufficiency_score=trust_res.evidence_sufficiency_score,
            evidence_status=trust_res.evidence_status.value,
            score_dimensions=trust_res.score_dimensions.model_dump(),
            supporting_evidence=trust_res.supporting_evidence,
            contradictory_evidence=trust_res.contradictory_evidence,
            missing_evidence=trust_res.missing_evidence,
            confidence_limitations=trust_res.confidence_limitations,
            historical_validation_status=trust_res.historical_validation_status,
            is_calibrated=trust_res.is_calibrated,
            applicable_policy_version=compiled_policy.version_number,
            applicable_contract_version=contract.status,
            escalation_reason=str(trust_res.escalation_reason)[:256] if trust_res.escalation_reason else None,
            human_readable_explanation=trust_res.human_readable_explanation,
            model_identifier=verdict.model_identifier,
            is_simulated=verdict.is_simulated,
            evaluated_at=utc_now(),
        ))

        # 6. Format Structured Authoritative Verdict (P2-REQ-07, P3-REQ-01, P3-REQ-07)
        verdict_prov = classify_execution_provenance(
            is_simulated=bool(verdict.is_simulated),
            model_identifier=verdict.model_identifier,
            validation_status=final_validation_status,
            source_type=(pilot_context.get("source_type") if pilot_context else "LIVE"),
            base_url=settings.LOCAL_LLM_BASE_URL,
        )
        verdict_data = {
            "incident_id": incident.incident_id,
            "proposed_verdict": val_res.proposed_verdict,
            "verdict": final_auth_verdict,
            "confidence": final_confidence_display,
            "raw_model_confidence": verdict.confidence,
            "reason": verdict.reason if final_is_decisive else f"{final_action_directive} [Validation: {'; '.join(final_reason_codes)}]. Model rationale: {verdict.reason}",
            "supporting_evidence": verdict.supporting_evidence,
            "supporting_claims": [c.model_dump() if hasattr(c, "model_dump") else c.dict() for c in claim_grounding.claims],
            "missing_evidence": val_res.missing_evidence_fields or verdict.missing_evidence,
            "analyst_questions": verdict.analyst_questions,
            "latency_ms": verdict.latency_ms,
            "model_identifier": verdict.model_identifier,
            "prompt_tokens": p_tokens,
            "completion_tokens": c_tokens,
            "total_tokens": t_tokens,
            "token_usage_source": token_usage_source,
            "is_simulated": verdict.is_simulated,
            "execution_provenance": verdict_prov["execution_provenance"],
            "configured_provider": verdict_prov["configured_provider"],
            "test_environment": verdict_prov["test_environment"],
            "validation_status": final_validation_status,
            "validation_reason_codes": final_reason_codes,
            "is_decisive_accepted": final_is_decisive,
            "proposal_validation_outcome": proposal_validation_outcome,
            "final_disposition": final_disposition,
            "abstention_reason": abstention_reason,
            "evidence_completeness": val_res.evidence_completeness,
            "grounding_ratio": val_res.grounding_ratio,
            "total_claims_count": val_res.total_claims_count,
            "grounded_claims_count": val_res.grounded_claims_count,
            "unsupported_claims_count": val_res.unsupported_claims_count,
            "unsupported_claims": val_res.unsupported_claims,
            "detected_contradictions": val_res.detected_contradictions,
            "analyst_action_directive": final_action_directive,
            "canonical_evidence_count": norm_result.total_evidence_count,
            "contract_id": val_res.contract_id,
            "contract_version": val_res.contract_version,
            "validator_version": val_res.validator_version,
            "compiler_version": compiled_policy.compiler_version,
            "compilation_digest": compiled_policy.compilation_digest,
            "policy_sections_count": len(compiled_policy.sections),
            "policy_version_id": getattr(active_v, "id", None),
            "policy_version_number": compiled_policy.version_number,
            "policy_status": compiled_policy.policy_status,
            "trust_score": trust_res.trust_score,
            "trust_status": trust_res.trust_status,
            "raw_trust_score": trust_res.raw_trust_score,
            "evidence_sufficiency_score": trust_res.evidence_sufficiency_score,
            "evidence_status": trust_res.evidence_status.value,
            "score_dimensions": trust_res.score_dimensions.model_dump(),
            "confidence_limitations": trust_res.confidence_limitations,
            "calibration_status": "CALIBRATED" if trust_res.is_calibrated else "NOT_CALIBRATED",
            "historical_validation_status": trust_res.historical_validation_status,
            "is_calibrated": trust_res.is_calibrated,
            "historical_sample_count": int(hist_stats.get("sample_count", 0)),
            "reevaluation_eligible": bool(not final_is_decisive and ("EVIDENCE_MISSING" in final_reason_codes or "EVIDENCE_CONTRACT_UNVERIFIED" in final_reason_codes)),
            "deferral_reason": ("EVIDENCE_MISSING" if not final_is_decisive and "EVIDENCE_MISSING" in final_reason_codes else None),
            "reevaluation_attempts": prev_attempts + 1,
            "rag_retrieval_status": rag_result.retrieval_status,
            "retrieved_precedents_count": len(rag_result.precedents),
            "retrieved_precedents": [p.model_dump() for p in rag_result.precedents],
            "token_budget_breakdown": budgeted.breakdown.model_dump(),
            "replay_signature": val_res.replay_signature,
            "rule_name": rule.name if rule else incident.title,
            "severity": incident.severity,
            "evaluated_at": utc_now().isoformat(),
            "evaluated_by_user": username,
            "pilot_mode": pilot_context.get("mode") if pilot_context else None,
            "pilot_id": pilot_context.get("pilot_id") if pilot_context else None,
            "pilot_version": pilot_context.get("pilot_version") if pilot_context else None,
        }

        # 7. Persist AI verdict to incident (unless SHADOW pilot mode keeps authoritative incident clean)
        if not is_shadow_pilot:
            incident.ai_verdict = verdict_data
            self.db.add(incident)

        # 7b. Persist bifurcated TokenUsageRecord on Server 1 for analytics (records authoritative outcome)
        from app.models.token_usage import TokenUsageRecord
        token_usage_entry = TokenUsageRecord(
            process_type="INCIDENT_TRIAGE",
            process_id=incident.incident_id,
            incident_id=incident.incident_id,
            rule_id=rule.rule_id if rule else incident.event_type,
            model_identifier=verdict.model_identifier,
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
            total_tokens=t_tokens,
            latency_ms=verdict.latency_ms,
            is_simulated=verdict.is_simulated,
            executed_by_user=username,
            timestamp=utc_now(),
            details={
                "verdict": final_auth_verdict,
                "proposed_verdict": val_res.proposed_verdict,
                "confidence": final_confidence_display,
                "raw_model_confidence": verdict.confidence,
                "trust_score": trust_res.trust_score,
                "token_usage_source": token_usage_source,
                "rule_name": rule.name if rule else incident.title,
                "severity": incident.severity,
            },
        )
        self.db.add(token_usage_entry)

        # 7c. Persist Historical Telemetry Timeline milestone on Server 1 with authoritative verdict
        from app.models.telemetry_timeline import TelemetryTimelineRecord
        timeline_entry = TelemetryTimelineRecord(
            incident_id=incident.incident_id,
            event_type="AGENT_TRIAGE_EVALUATED",
            stage="TRIAGE",
            summary=f"Verdict Triage Agent evaluated incident: {final_auth_verdict} ({int(final_confidence_display)}% confidence, trust={trust_res.trust_score}/10)",
            source="Verdict Triage Agent (Server 2 Inference)",
            severity=incident.severity,
            source_ip=incident.source_ip,
            reporting_device=incident.reporting_device,
            epoch_ms=int(time.time() * 1000),
            token_count=t_tokens,
            details={
                "verdict": final_auth_verdict,
                "proposed_verdict": val_res.proposed_verdict,
                "confidence": final_confidence_display,
                "raw_model_confidence": verdict.confidence,
                "trust_score": trust_res.trust_score,
                "validation_status": final_validation_status,
                "model": verdict.model_identifier,
                "latency_ms": verdict.latency_ms,
                "prompt_tokens": p_tokens,
                "completion_tokens": c_tokens,
                "total_tokens": t_tokens,
            },
        )
        self.db.add(timeline_entry)

        # 8. Sync with Investigation queue using authoritative validated verdict (idempotent; skipped in SHADOW pilot mode)
        if not is_shadow_pilot:
            inv_q = await self.db.execute(
                select(Investigation).where(Investigation.incident_id == incident.id)
            )
            inv = inv_q.scalars().first()
            if inv and not inv.analyst_verdict:
                note_entry = f"[AI Verdict ({final_auth_verdict} - {int(final_confidence_display)}%)]: {verdict_data['reason']}"
                self._upsert_ai_verdict_note(inv, note_entry)
                self.db.add(inv)

        # 9. Audit log with authoritative outcome and model proposal provenance
        audit = AuditLog(
            user_id="SYSTEM" if username in ("system", "scheduler") else username,
            username=username,
            action="AI_VERDICT_EVALUATE",
            resource_type="INCIDENT",
            resource_id=incident.incident_id,
            details={
                "verdict": final_auth_verdict,
                "proposed_verdict": val_res.proposed_verdict,
                "confidence": final_confidence_display,
                "raw_model_confidence": verdict.confidence,
                "trust_score": trust_res.trust_score,
                "validation_status": final_validation_status,
                "latency_ms": verdict.latency_ms,
                "model": verdict.model_identifier,
                "is_simulated": verdict.is_simulated,
                "execution_provenance": verdict_prov["execution_provenance"],
                "configured_provider": verdict_prov["configured_provider"],
                "test_environment": verdict_prov["test_environment"],
            },
        )
        self.db.add(audit)
        await self.db.commit()

        return verdict_data

    async def evaluate_batch(
        self,
        incident_ids: Optional[List[str]] = None,
        only_pending: bool = True,
        max_batch: int = 50,
        username: str = "batch_evaluator",
        allow_simulated_fallback: bool = False,
    ) -> Dict[str, Any]:
        """
        Evaluates a batch of incidents in sequence.
        Halts immediately if the Local LLM is offline, leaving incidents pending.
        """
        is_online = await self.is_local_llm_available()
        is_prod = getattr(settings, "APP_ENV", "development").lower() in ("production", "prod")
        allow_mock = False if is_prod else (allow_simulated_fallback or getattr(settings, "LOCAL_LLM_ALLOW_MOCK_FALLBACK", False))
        if not is_online and not allow_mock:
            pending_count = await self.get_pending_incident_count()
            return {
                "success": False,
                "total_requested": 0,
                "processed": 0,
                "successful": 0,
                "failed": 0,
                "results": [],
                "message": f"Local LLM (Server 2) is currently offline. {pending_count} incidents remain queued.",
            }

        stmt = select(Incident).options(
            selectinload(Incident.rule),
            selectinload(Incident.events),
        )

        if incident_ids and len(incident_ids) > 0:
            stmt = stmt.where(Incident.incident_id.in_(incident_ids))
        elif only_pending:
            stmt = stmt.where(Incident.ai_verdict.is_(None))

        stmt = stmt.order_by(Incident.created_at_epoch.asc().nulls_last(), Incident.created_at.asc()).limit(max_batch)
        res = await self.db.execute(stmt)
        incidents = res.scalars().all()
        target_ids = [str(inc.incident_id or inc.id) for inc in incidents]

        results = []
        successful = 0
        failed = 0

        for iid in target_ids:
            # If flagged offline from a failure, verify if recovered before continuing batch
            if self.__class__._is_local_llm_online is False:
                if not await self.is_local_llm_available(force_refresh=True) and not allow_mock:
                    print(f"[Batch AI Verdict] Local LLM is offline at incident {iid}. Stopping batch.")
                    break

            try:
                v = await self.evaluate_incident(
                    iid,
                    username=username,
                    allow_simulated_fallback=allow_mock,
                    only_if_pending=only_pending,
                )
                await self.db.commit()
                results.append(v)
                successful += 1
                await asyncio.sleep(0.15)
            except Exception as e:
                try:
                    await self.db.rollback()
                except Exception:
                    pass
                failed += 1
                results.append({
                    "incident_id": iid,
                    "error": str(e),
                    "verdict": "ERROR",
                })

        return {
            "success": True,
            "total_requested": len(incidents),
            "processed": len(results),
            "successful": successful,
            "failed": failed,
            "results": results,
            "message": f"Evaluated {successful} incidents with AI Verdict ({failed} failures).",
        }

    async def reconcile_pending_triage(
        self,
        max_batch: int = 100,
        username: str = "llm_backlog_worker",
        pause_between_s: float = 0.15,
        include_reevaluation_eligible: bool = False,
        rule_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Reconciles pending triage incidents lacking an AI verdict, plus bounded
        reevaluation of recoverable abstentions (e.g., POLICY_NOT_APPROVED once
        a rule policy is approved) when include_reevaluation_eligible=True.
        If Local LLM is offline or goes offline mid-batch, halts immediately.
        """
        from app.services.llm_config_service import LLMConfigService
        LLMConfigService.sync_runtime_settings()
        is_online = await self.is_local_llm_available(force_refresh=True)
        is_prod = getattr(settings, "APP_ENV", "development").lower() in ("production", "prod")
        allow_mock = False if is_prod else getattr(settings, "LOCAL_LLM_ALLOW_MOCK_FALLBACK", False)
        pending_total = await self.get_pending_incident_count()

        # Query pending incident IDs chronologically
        stmt = (
            select(Incident.incident_id)
            .where(Incident.ai_verdict.is_(None))
            .order_by(Incident.created_at_epoch.asc().nulls_last(), Incident.created_at.asc())
            .limit(max_batch)
        )
        if rule_id:
            stmt = stmt.where(Incident.rule_id == rule_id)
        res = await self.db.execute(stmt)
        pending_ids = list(res.scalars().all())

        # Bounded discovery of reevaluation-eligible deferred incidents
        if include_reevaluation_eligible and len(pending_ids) < max_batch:
            rem_cap = max_batch - len(pending_ids)
            re_q = select(Incident).where(Incident.ai_verdict.isnot(None))
            if rule_id:
                re_q = re_q.where(Incident.rule_id == rule_id)
            re_q = re_q.order_by(Incident.created_at_epoch.asc().nulls_last(), Incident.created_at.asc()).limit(rem_cap * 3)
            re_res = await self.db.execute(re_q)
            for inc_obj in re_res.scalars().all():
                if len(pending_ids) >= max_batch:
                    break
                av = inc_obj.ai_verdict
                if isinstance(av, dict) and av.get("reevaluation_eligible") is True and int(av.get("reevaluation_attempts", 0) or 0) < 3:
                    iid = str(inc_obj.incident_id)
                    if iid not in pending_ids:
                        pending_ids.append(iid)

        if not is_online and not allow_mock:
            return {
                "success": False,
                "is_llm_online": False,
                "message": f"Local LLM (Server 2) is currently offline. {pending_total} incidents pending in queue.",
                "processed": 0,
                "failed": 0,
                "pending_remaining": pending_total,
            }

        if not pending_ids:
            return {
                "success": True,
                "is_llm_online": True,
                "message": "All incidents have AI verdicts. No pending incidents in queue.",
                "processed": 0,
                "failed": 0,
                "pending_remaining": 0,
            }

        processed_count = 0
        failed_count = 0

        for iid in pending_ids:
            # If flagged offline from a failure, verify if recovered before processing incident
            if self.__class__._is_local_llm_online is False:
                if not await self.is_local_llm_available(force_refresh=True) and not allow_mock:
                    print(f"[LLM Backlog Processor] Local LLM is offline at incident {iid}. Halting processing.")
                    break

            try:
                await self.evaluate_incident(
                    iid,
                    username=username,
                    allow_simulated_fallback=allow_mock,
                    only_if_pending=not include_reevaluation_eligible,
                )
                await self.db.commit()
                processed_count += 1
                if pause_between_s > 0:
                    await asyncio.sleep(pause_between_s)
            except Exception as exc:
                try:
                    await self.db.rollback()
                except Exception:
                    pass
                failed_count += 1
                print(f"[LLM Backlog Processor] Error evaluating incident {iid}: {exc}")

        remaining = await self.get_pending_incident_count()
        return {
            "success": True,
            "is_llm_online": True,
            "processed": processed_count,
            "failed": failed_count,
            "pending_remaining": remaining,
            "message": f"Processed {processed_count} pending incidents one by one ({remaining} remaining).",
        }

    # Backward compatibility alias
    process_pending_incidents = reconcile_pending_triage


# Backward compatibility alias
AIVerdictService = VerdictTriageAgent

