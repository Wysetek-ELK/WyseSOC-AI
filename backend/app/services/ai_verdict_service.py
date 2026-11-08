import time
import asyncio
from datetime import datetime
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

    def __init__(self, db: AsyncSession):
        self.db = db

    @classmethod
    async def is_local_llm_available(cls, force_refresh: bool = False) -> bool:
        """Checks if Server 2 LLM endpoint is reachable, caching result for 30s."""
        now = time.time()
        if not force_refresh and cls._is_local_llm_online is not None and (now - cls._last_probe_time) < 30.0:
            return cls._is_local_llm_online

        cls._last_probe_time = now
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
    ) -> Dict[str, Any]:
        """
        Evaluates a single incident with the LLM.
        Auto-provisions detection rules if unmapped, formats allowlisted model telemetry,
        and saves the structured verdict to the database.
        """
        # 1. Resolve incident object cleanly with eager-loaded relationships
        clean_target_id = incident_id_or_obj if isinstance(incident_id_or_obj, str) else str(getattr(incident_id_or_obj, "id", getattr(incident_id_or_obj, "incident_id", "")))
        stmt = (
            select(Incident)
            .where((Incident.id == clean_target_id) | (Incident.incident_id == clean_target_id))
            .options(selectinload(Incident.rule), selectinload(Incident.events))
        )
        res = await self.db.execute(stmt)
        incident = res.scalar_one_or_none()
        if not incident:
            raise ValueError(f"Incident '{clean_target_id}' not found.")

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
        if is_prod:
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

            # REQ-03 (AV-001 & AV-002): Refuse to evaluate with unapproved prompt drafts in live triage
            if not active_v:
                if not allow_simulated_fallback or is_prod:
                    verdict_data = {
                        "incident_id": incident.incident_id,
                        "proposed_verdict": "REQUIRES_ATTENTION",
                        "verdict": "REQUIRES_ATTENTION",
                        "confidence": 0.0,
                        "raw_model_confidence": 0.0,
                        "reason": "DETECTION_POLICY_PENDING_APPROVAL: No approved investigation policy exists for this detection rule. Triage deferred to human analyst.",
                        "supporting_evidence": [],
                        "missing_evidence": ["Approved detection rule investigation policy (Studio approval required)"],
                        "analyst_questions": ["Please review and approve the detection policy in Agent Intelligence Studio."],
                        "latency_ms": 0,
                        "model_identifier": "POLICY_GUARD",
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "is_simulated": False,
                        "validation_status": "POLICY_NOT_APPROVED",
                        "validation_reason_codes": ["POLICY_NOT_APPROVED", "EVIDENCE_CONTRACT_UNVERIFIED"],
                        "evidence_completeness": 0.0,
                        "grounding_ratio": 0.0,
                        "canonical_evidence_count": norm_result.total_evidence_count,
                        "rule_name": rule.name if rule else incident.title,
                        "severity": incident.severity,
                        "evaluated_at": datetime.utcnow().isoformat(),
                        "evaluated_by_user": username,
                    }
                    incident.ai_verdict = verdict_data
                    self.db.add(incident)

                    # Sync with Investigation record if present
                    inv_q = await self.db.execute(
                        select(Investigation).where(Investigation.incident_id == incident.id)
                    )
                    inv = inv_q.scalars().first()
                    if inv and not inv.analyst_verdict:
                        note_entry = f"[AI Verdict (REQUIRES_ATTENTION - 0%)]: {verdict_data['reason']}"
                        if inv.analyst_notes:
                            inv.analyst_notes = f"{inv.analyst_notes}\n\n{note_entry}"
                        else:
                            inv.analyst_notes = note_entry
                        inv.updated_at = datetime.utcnow()
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
                "validation_status": preflight.preflight_status,
                "validation_reason_codes": ["EVIDENCE_MISSING"] if preflight.critical_missing_fields else ["EVIDENCE_CONTRACT_UNVERIFIED"],
                "evidence_completeness": preflight.evidence_completeness,
                "grounding_ratio": 0.0,
                "canonical_evidence_count": norm_result.total_evidence_count,
                "contract_id": contract.contract_id,
                "contract_version": contract.version_number,
                "validator_version": IndependentVerdictValidator.VALIDATOR_VERSION,
                "rule_name": rule.name if rule else incident.title,
                "severity": incident.severity,
                "evaluated_at": datetime.utcnow().isoformat(),
                "evaluated_by_user": username,
            }
            incident.ai_verdict = verdict_data
            self.db.add(incident)

            inv_q = await self.db.execute(
                select(Investigation).where(Investigation.incident_id == incident.id)
            )
            inv = inv_q.scalars().first()
            if inv and not inv.analyst_verdict:
                note_entry = f"[AI Verdict (REQUIRES_ATTENTION - 0%)]: {verdict_data['reason']}"
                if inv.analyst_notes:
                    inv.analyst_notes = f"{inv.analyst_notes}\n\n{note_entry}"
                else:
                    inv.analyst_notes = note_entry
                inv.updated_at = datetime.utcnow()
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
                "validation_status": "CONTEXT_WINDOW_EXCEEDED",
                "validation_reason_codes": ["CONTEXT_WINDOW_EXCEEDED"],
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
                "rule_name": rule.name if rule else incident.title,
                "severity": incident.severity,
                "evaluated_at": datetime.utcnow().isoformat(),
                "evaluated_by_user": username,
            }
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

        try:
            verdict = await provider.analyze_incident(
                incident_payload=payload_dict,
                rule_spec=rule_spec,
                prompt_text=prompt_text,
                prompt_version_number=prompt_ver_num,
            )
            
            # Check if OPENAI_COMPATIBLE provider suffered an actual connection failure or HTTP error
            is_connection_error = (
                getattr(verdict, "validation_status", "") in ("CONNECTION_ERROR", "HTTP_ERROR")
                or (getattr(verdict, "confidence", 100.0) == 0.0 and getattr(verdict, "validation_status", "") != "VALID")
            )
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
        if t_tokens == 0:
            p_tokens = max(50, len(prompt_text) // 4)
            c_tokens = max(20, len(verdict.reason) // 4)
            t_tokens = p_tokens + c_tokens

        # P2-REQ-04: Structured Claim Extraction and Grounding
        raw_verdict_dict = verdict.model_dump() if hasattr(verdict, "model_dump") else (verdict.dict() if hasattr(verdict, "dict") else {
            "verdict": verdict.verdict,
            "confidence": verdict.confidence,
            "reason": verdict.reason,
            "supporting_evidence": verdict.supporting_evidence,
            "supporting_claims": getattr(verdict, "supporting_claims", []),
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
        )

        # 6. Format Structured Authoritative Verdict (P2-REQ-07, P3-REQ-01, P3-REQ-07)
        verdict_data = {
            "incident_id": incident.incident_id,
            "proposed_verdict": val_res.proposed_verdict,
            "verdict": val_res.final_verdict,
            "confidence": val_res.validated_confidence_display if val_res.validated_confidence_display is not None else verdict.confidence,
            "raw_model_confidence": verdict.confidence,
            "reason": verdict.reason if val_res.is_decisive_accepted else f"{val_res.analyst_action_directive} [Validation: {'; '.join(val_res.validation_reason_codes)}]. Model rationale: {verdict.reason}",
            "supporting_evidence": verdict.supporting_evidence,
            "supporting_claims": [c.model_dump() if hasattr(c, "model_dump") else c.dict() for c in claim_grounding.claims],
            "missing_evidence": val_res.missing_evidence_fields or verdict.missing_evidence,
            "analyst_questions": verdict.analyst_questions,
            "latency_ms": verdict.latency_ms,
            "model_identifier": verdict.model_identifier,
            "prompt_tokens": p_tokens,
            "completion_tokens": c_tokens,
            "total_tokens": t_tokens,
            "is_simulated": verdict.is_simulated,
            "validation_status": val_res.validation_status,
            "validation_reason_codes": val_res.validation_reason_codes,
            "is_decisive_accepted": val_res.is_decisive_accepted,
            "evidence_completeness": val_res.evidence_completeness,
            "grounding_ratio": val_res.grounding_ratio,
            "total_claims_count": val_res.total_claims_count,
            "grounded_claims_count": val_res.grounded_claims_count,
            "unsupported_claims_count": val_res.unsupported_claims_count,
            "unsupported_claims": val_res.unsupported_claims,
            "detected_contradictions": val_res.detected_contradictions,
            "analyst_action_directive": val_res.analyst_action_directive,
            "canonical_evidence_count": norm_result.total_evidence_count,
            "contract_id": val_res.contract_id,
            "contract_version": val_res.contract_version,
            "validator_version": val_res.validator_version,
            "compiler_version": compiled_policy.compiler_version,
            "compilation_digest": compiled_policy.compilation_digest,
            "policy_sections_count": len(compiled_policy.sections),
            "policy_version_number": compiled_policy.version_number,
            "policy_status": compiled_policy.policy_status,
            "calibration_status": "NOT_CALIBRATED",
            "is_calibrated": False,
            "rag_retrieval_status": rag_result.retrieval_status,
            "retrieved_precedents_count": len(rag_result.precedents),
            "retrieved_precedents": [p.model_dump() for p in rag_result.precedents],
            "token_budget_breakdown": budgeted.breakdown.model_dump(),
            "replay_signature": val_res.replay_signature,
            "rule_name": rule.name if rule else incident.title,
            "severity": incident.severity,
            "evaluated_at": datetime.utcnow().isoformat(),
            "evaluated_by_user": username,
        }

        # 7. Persist AI verdict to incident
        incident.ai_verdict = verdict_data
        self.db.add(incident)

        # 7b. Persist bifurcated TokenUsageRecord on Server 1 for analytics
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
            timestamp=datetime.utcnow(),
            details={
                "verdict": verdict.verdict,
                "confidence": verdict.confidence,
                "rule_name": rule.name if rule else incident.title,
                "severity": incident.severity,
            },
        )
        self.db.add(token_usage_entry)

        # 7c. Persist Historical Telemetry Timeline milestone on Server 1
        from app.models.telemetry_timeline import TelemetryTimelineRecord
        timeline_entry = TelemetryTimelineRecord(
            incident_id=incident.incident_id,
            event_type="AGENT_TRIAGE_EVALUATED",
            stage="TRIAGE",
            summary=f"Verdict Triage Agent evaluated incident: {verdict.verdict} ({int(verdict.confidence)}% confidence)",
            source="Verdict Triage Agent (Server 2 Inference)",
            severity=incident.severity,
            source_ip=incident.source_ip,
            reporting_device=incident.reporting_device,
            epoch_ms=int(time.time() * 1000),
            token_count=t_tokens,
            details={
                "verdict": verdict.verdict,
                "confidence": verdict.confidence,
                "model": verdict.model_identifier,
                "latency_ms": verdict.latency_ms,
                "prompt_tokens": p_tokens,
                "completion_tokens": c_tokens,
                "total_tokens": t_tokens,
            },
        )
        self.db.add(timeline_entry)

        # 8. Sync with Investigation queue
        inv_q = await self.db.execute(
            select(Investigation).where(Investigation.incident_id == incident.id)
        )
        inv = inv_q.scalars().first()
        if inv and not inv.analyst_verdict:
            note_entry = f"[AI Verdict ({verdict.verdict} - {int(verdict.confidence)}%)]: {verdict.reason}"
            if inv.analyst_notes:
                inv.analyst_notes = f"{inv.analyst_notes}\n\n{note_entry}"
            else:
                inv.analyst_notes = note_entry
            inv.updated_at = datetime.utcnow()
            self.db.add(inv)

        # 9. Audit log
        audit = AuditLog(
            user_id="SYSTEM" if username in ("system", "scheduler") else username,
            username=username,
            action="AI_VERDICT_EVALUATE",
            resource_type="INCIDENT",
            resource_id=incident.incident_id,
            details={
                "verdict": verdict.verdict,
                "confidence": verdict.confidence,
                "latency_ms": verdict.latency_ms,
                "model": verdict.model_identifier,
                "is_simulated": verdict.is_simulated,
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
                v = await self.evaluate_incident(iid, username=username, allow_simulated_fallback=allow_mock)
                await self.db.commit()
                results.append(v)
                successful += 1
                await asyncio.sleep(0.15)
            except Exception as e:
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
    ) -> Dict[str, Any]:
        """
        Reconciles pending triage incidents lacking an AI verdict. Once Local LLM is
        online, processes them one by one sequentially with the Verdict Triage Agent.
        If Local LLM is offline or goes offline mid-batch, halts immediately.
        """
        is_online = await self.is_local_llm_available(force_refresh=True)
        is_prod = getattr(settings, "APP_ENV", "development").lower() in ("production", "prod")
        allow_mock = False if is_prod else getattr(settings, "LOCAL_LLM_ALLOW_MOCK_FALLBACK", False)
        pending_total = await self.get_pending_incident_count()

        if not is_online and not allow_mock:
            return {
                "success": False,
                "is_llm_online": False,
                "message": f"Local LLM (Server 2) is currently offline. {pending_total} incidents pending in queue.",
                "processed": 0,
                "failed": 0,
                "pending_remaining": pending_total,
            }

        if pending_total == 0:
            return {
                "success": True,
                "is_llm_online": True,
                "message": "All incidents have AI verdicts. No pending incidents in queue.",
                "processed": 0,
                "failed": 0,
                "pending_remaining": 0,
            }

        # Query pending incident IDs chronologically
        stmt = (
            select(Incident.incident_id)
            .where(Incident.ai_verdict.is_(None))
            .order_by(Incident.created_at_epoch.asc().nulls_last(), Incident.created_at.asc())
            .limit(max_batch)
        )
        res = await self.db.execute(stmt)
        pending_ids = res.scalars().all()

        processed_count = 0
        failed_count = 0

        for iid in pending_ids:
            # If flagged offline from a failure, verify if recovered before processing incident
            if self.__class__._is_local_llm_online is False:
                if not await self.is_local_llm_available(force_refresh=True) and not allow_mock:
                    print(f"[LLM Backlog Processor] Local LLM is offline at incident {iid}. Halting processing.")
                    break

            try:
                await self.evaluate_incident(iid, username=username, allow_simulated_fallback=allow_mock)
                await self.db.commit()
                processed_count += 1
                if pause_between_s > 0:
                    await asyncio.sleep(pause_between_s)
            except Exception as exc:
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

