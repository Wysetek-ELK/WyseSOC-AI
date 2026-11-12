"""
Unified Verdict Execution Pipeline shared between Live VerdictTriageAgent and
Historical PolicySimulationService to enforce identical safeguards:
  - Allowlisted & sanitized model inputs (zero ground-truth leakage)
  - Canonical Evidence Normalization & RuleIntelligenceSnapshot-backed Contracts
  - Evidence Preflight Validation
  - Unified 9-Section Policy Compilation
  - Rule-Scoped Verified Semantic RAG (temporal & self-exclusion safe)
  - Evidence-Preserving Token Budgeting
  - GPU-managed OPENAI_COMPATIBLE or explicit SIMULATED model invocation
  - Claim Extraction/Grounding + Independent Verdict Validation + Trustworthiness Scoring
  - Runtime Policy Governance (structural vs empirical vs autonomous authorization)
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.incident import Incident
from app.models.prompt import PromptVersion
from app.models.rule import Rule
from app.schemas.compiled_policy import CompilationExecutionMode
from app.schemas.canonical_evidence import CanonicalEvidenceRecord
from app.schemas.verdict_intelligence import UserVisibleVerdict
from app.services.evidence_contract_service import EvidenceContractService
from app.services.evidence_normalization_service import EvidenceNormalizationService
from app.services.evidence_preflight_validator import EvidencePreflightValidator
from app.services.historical_ground_truth_validator import HistoricalGroundTruthValidator
from app.services.independent_verdict_validator import IndependentVerdictValidator
from app.services.model_claim_extractor import ModelClaimExtractor
from app.services.model_payload_allowlist import build_model_facing_payload
from app.services.model_provider.base import StructuredModelVerdict
from app.services.model_provider.factory import get_model_provider
from app.services.policy_compiler_service import PolicyCompilerService
from app.services.policy_governance import (
    PolicyRuntimeCertification,
    assess_policy_runtime_certification,
    get_rule_semantics_and_contract,
)
from app.services.provenance import classify_execution_provenance
from app.services.llm_config_service import LLMConfigService
from app.services.token_budget_service import TokenBudgetService
from app.services.verified_semantic_retrieval_service import VerifiedSemanticRetrievalService
from app.services.verdict_trustworthiness_engine import VerdictTrustworthinessEngine
from app.utils.datetime_utils import utc_now


class PipelineLLMUnavailableError(Exception):
    """Raised when the configured OPENAI_COMPATIBLE endpoint is offline or unreachable."""


@dataclass
class VerdictPipelineResult:
    """Complete output of the shared verdict evaluation & validation pipeline."""

    verdict_data: Dict[str, Any]
    early_exit: bool = False
    early_exit_kind: Optional[str] = None
    verdict_obj: Optional[Any] = None
    trust_res: Optional[Any] = None
    val_res: Optional[Any] = None
    claim_grounding: Optional[Any] = None
    norm_result: Optional[Any] = None
    contract: Optional[Any] = None
    compiled_policy: Optional[Any] = None
    certification: Optional[PolicyRuntimeCertification] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    token_usage_source: str = "UNAVAILABLE"
    provider_type_used: str = "SIMULATED"
    verdict_prov: Dict[str, Any] = field(default_factory=dict)
    is_abstained: bool = False
    effective_verdict: str = "REQUIRES_ATTENTION"
    proposed_verdict: str = "REQUIRES_ATTENTION"
    trust_score: int = 0
    raw_trust_score: int = 0
    evidence_status: str = "INSUFFICIENT"
    escalation_reason: Optional[str] = None
    evidence_trace: Dict[str, Any] = field(default_factory=dict)


def build_sanitized_model_payload(
    incident: Incident,
    rule: Optional[Rule],
) -> Tuple[Any, Dict[str, Any]]:
    """Normalize incident telemetry and construct a leakage-sanitized model payload."""
    norm_result = EvidenceNormalizationService.normalize_incident_evidence(
        incident=incident,
        events=getattr(incident, "events", None) or [],
    )
    payload_dict = build_model_facing_payload(
        incident=incident,
        rule=rule,
        events=getattr(incident, "events", None) or [],
    )
    payload_dict = HistoricalGroundTruthValidator.sanitize_incident_for_inference(payload_dict)
    payload_dict["canonical_evidence"] = [r.model_dump() for r in norm_result.records]
    return norm_result, payload_dict


def _governance_fields(certification: Optional[PolicyRuntimeCertification]) -> Dict[str, Any]:
    if not certification:
        return {
            "policy_governance_mode": "ADVISORY_ANALYST_REVIEW_REQUIRED",
            "structural_approval_eligible": False,
            "empirical_validation_eligible": False,
            "autonomous_operation_eligible": False,
            "autonomous_action_blocked": True,
            "auto_incident_closure_allowed": False,
            "external_writeback_allowed": False,
            "requires_human_review": True,
            "empirical_validation_status": "NOT_EVALUATED",
            "active_policy_digest": None,
            "governance_reasons": ["NO_CERTIFICATION_CONTEXT"],
        }
    return {
        "policy_governance_mode": certification.policy_governance_mode,
        "structural_approval_eligible": certification.structural_approval_eligible,
        "empirical_validation_eligible": certification.empirical_validation_eligible,
        "autonomous_operation_eligible": certification.autonomous_operation_eligible,
        "autonomous_action_blocked": not certification.autonomous_operation_eligible,
        "auto_incident_closure_allowed": bool(certification.autonomous_operation_eligible),
        "external_writeback_allowed": bool(certification.autonomous_operation_eligible),
        "requires_human_review": not certification.autonomous_operation_eligible,
        "empirical_validation_status": certification.empirical_validation_status,
        "active_policy_digest": certification.active_policy_digest,
        "governance_reasons": list(certification.blocking_reasons),
    }


async def _invoke_provider_with_guards(
    *,
    chosen_provider_type: str,
    payload_dict: Dict[str, Any],
    rule_spec: Dict[str, Any],
    prompt_text: str,
    prompt_ver_num: int,
    allow_mock_fallback: bool,
    provider_factory: Callable[..., Any],
    set_llm_online: Optional[Callable[[bool], None]] = None,
    simulated_output_fn: Optional[Callable[..., Dict[str, Any]]] = None,
    contract: Optional[Any] = None,
    prompt_version: Optional[PromptVersion] = None,
) -> Tuple[Any, str]:
    """Invoke OPENAI_COMPATIBLE (with GPU slot protection) or SIMULATED provider safely."""
    ptype = str(chosen_provider_type or "SIMULATED").upper().strip()

    if ptype == "SIMULATED":
        if simulated_output_fn is not None:
            raw = simulated_output_fn(payload_dict, contract, prompt_version)
            verdict_obj = StructuredModelVerdict(
                incident_id=str(payload_dict.get("incident_id") or "INC-SIM"),
                rule_id=str(rule_spec.get("rule_id") or rule_spec.get("id") or "RULE-SIM"),
                verdict=str(raw.get("verdict") or "REQUIRES_ATTENTION"),
                confidence=float(raw.get("confidence") or 50.0),
                reason=str(raw.get("reason") or ""),
                supporting_evidence=list(raw.get("supporting_evidence") or []),
                supporting_claims=list(raw.get("claims") or raw.get("supporting_claims") or []),
                contradictory_evidence=list(raw.get("contradictory_evidence") or []),
                missing_evidence=list(raw.get("missing_evidence") or []),
                analyst_questions=list(raw.get("analyst_questions") or []),
                model_identifier=str(raw.get("model_identifier") or "simulated-v2.2-policy-aware"),
                prompt_version_number=int(prompt_ver_num or 1),
                is_simulated=True,
                validation_status="SIMULATED",
                latency_ms=int(raw.get("latency_ms") or 5),
                prompt_tokens=int(raw.get("prompt_tokens") or 0),
                completion_tokens=int(raw.get("completion_tokens") or 0),
                total_tokens=int(raw.get("total_tokens") or 0),
            )
            return verdict_obj, "SIMULATED"

        provider = provider_factory("SIMULATED")
        verdict_obj = await provider.analyze_incident(
            incident_payload=payload_dict,
            rule_spec=rule_spec,
            prompt_text=prompt_text,
            prompt_version_number=prompt_ver_num,
        )
        return verdict_obj, "SIMULATED"

    provider = provider_factory(ptype)
    use_gpu_manager = ptype == "OPENAI_COMPATIBLE"
    if use_gpu_manager:
        from app.services.gpu_manager import gpu_workload_manager, CircuitBreakerOpenException

        try:
            await gpu_workload_manager.acquire_inference_slot()
        except CircuitBreakerOpenException as cb_exc:
            if not allow_mock_fallback:
                raise PipelineLLMUnavailableError(str(cb_exc)) from cb_exc
            sim_provider = provider_factory("SIMULATED")
            verdict_obj = await sim_provider.analyze_incident(
                incident_payload=payload_dict,
                rule_spec=rule_spec,
                prompt_text=prompt_text,
                prompt_version_number=prompt_ver_num,
            )
            return verdict_obj, "SIMULATED"

    try:
        verdict_obj = await provider.analyze_incident(
            incident_payload=payload_dict,
            rule_spec=rule_spec,
            prompt_text=prompt_text,
            prompt_version_number=prompt_ver_num,
        )
        raw_status = str(getattr(verdict_obj, "validation_status", "") or "").upper().strip()
        is_connection_error = raw_status in ("CONNECTION_ERROR", "HTTP_ERROR")
        if use_gpu_manager:
            await gpu_workload_manager.release_inference_slot(
                success=not is_connection_error,
                error_message=getattr(verdict_obj, "reason", "connection failure")
                if is_connection_error
                else None,
            )
            use_gpu_manager = False

        if is_connection_error:
            if set_llm_online:
                set_llm_online(False)
            if allow_mock_fallback:
                sim_provider = provider_factory("SIMULATED")
                verdict_obj = await sim_provider.analyze_incident(
                    incident_payload=payload_dict,
                    rule_spec=rule_spec,
                    prompt_text=prompt_text,
                    prompt_version_number=prompt_ver_num,
                )
                return verdict_obj, "SIMULATED"
            raise PipelineLLMUnavailableError(
                f"Local LLM connection error: {getattr(verdict_obj, 'reason', 'connection failed')}"
            )

        if set_llm_online:
            set_llm_online(True)
        return verdict_obj, ptype
    except Exception as exc:
        if use_gpu_manager:
            await gpu_workload_manager.release_inference_slot(
                success=False, error_message=str(exc)
            )
        if set_llm_online:
            set_llm_online(False)
        if allow_mock_fallback and not isinstance(exc, PipelineLLMUnavailableError):
            sim_provider = provider_factory("SIMULATED")
            verdict_obj = await sim_provider.analyze_incident(
                incident_payload=payload_dict,
                rule_spec=rule_spec,
                prompt_text=prompt_text,
                prompt_version_number=prompt_ver_num,
            )
            return verdict_obj, "SIMULATED"
        if isinstance(exc, PipelineLLMUnavailableError):
            raise
        raise PipelineLLMUnavailableError(f"Local LLM inference failed: {exc}") from exc


async def run_shared_verdict_pipeline(
    *,
    db: AsyncSession,
    incident: Incident,
    rule: Optional[Rule],
    prompt_version: Optional[PromptVersion],
    active_approved_version: Optional[PromptVersion],
    model_provider_type: Optional[str] = None,
    allow_simulated_fallback: bool = False,
    is_simulation: bool = False,
    is_prod: bool = False,
    execution_context: str = "ANALYST_ASSISTED",
    require_autonomous_certification: bool = False,
    username: str = "system",
    pilot_context: Optional[Dict[str, Any]] = None,
    historical_stats: Optional[Dict[str, Any]] = None,
    prev_attempts: int = 0,
    check_llm_available: Optional[Callable[[], Any]] = None,
    set_llm_online: Optional[Callable[[bool], None]] = None,
    provider_factory: Optional[Callable[..., Any]] = None,
    simulated_output_fn: Optional[Callable[..., Dict[str, Any]]] = None,
) -> VerdictPipelineResult:
    """
    Execute the complete AIS 2.1 policy compilation, evidence validation, inference,
    claim grounding, and trustworthiness pipeline identically for Live Triage and Simulation.
    """
    prov_factory = provider_factory or get_model_provider
    norm_result, payload_dict = build_sanitized_model_payload(incident, rule)

    if is_prod or (pilot_context and str(pilot_context.get("source_type", "")).upper() == "LIVE"):
        allow_mock = False
    elif is_simulation:
        allow_mock = False
    else:
        allow_mock = bool(
            allow_simulated_fallback or getattr(settings, "LOCAL_LLM_ALLOW_MOCK_FALLBACK", False)
        )

    # Check LLM availability upfront only for live non-mock calls without explicit provider
    if not is_simulation and not allow_mock and not model_provider_type and check_llm_available:
        is_online = await check_llm_available()
        if not is_online:
            raise PipelineLLMUnavailableError(
                "Local LLM (Server 2) is currently offline. AI verdict generation is deferred until Local LLM comes online."
            )

    active_v = active_approved_version
    if is_simulation:
        active_v = prompt_version or active_approved_version

    # 1. Policy Approval Gate (Live triage requires APPROVED unless mock fallback in dev/test)
    if not active_v and not is_simulation:
        if not allow_simulated_fallback or is_prod:
            deferral_detail = (
                "DETECTION_POLICY_PENDING_APPROVAL: No approved investigation policy exists for this detection rule. Triage deferred to human analyst."
                if rule
                else "DETECTION_POLICY_PENDING_APPROVAL: Incident has no matched approved detection rule policy. Triage deferred to human analyst."
            )
            cert_empty = await assess_policy_runtime_certification(db, rule, None)
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
                **_governance_fields(cert_empty),
            }
            return VerdictPipelineResult(
                verdict_data=verdict_data,
                early_exit=True,
                early_exit_kind="POLICY_NOT_APPROVED",
                norm_result=norm_result,
                certification=cert_empty,
                is_abstained=True,
                effective_verdict="REQUIRES_ATTENTION",
                escalation_reason=deferral_detail,
            )
        active_v = prompt_version

    # 2. Runtime Governance / Autonomous Authorization Gate (AIS-F03)
    certification = await assess_policy_runtime_certification(db, rule, active_v)
    enforce_autonomous = (
        not is_simulation
        and (
            str(execution_context or "").upper() == "AUTONOMOUS"
            or bool(require_autonomous_certification)
        )
    )
    if enforce_autonomous and not certification.autonomous_operation_eligible:
        block_detail = (
            f"POLICY_NOT_EMPIRICALLY_CERTIFIED: Autonomous execution blocked. {certification.advisory_notice}"
        )
        verdict_data = {
            "incident_id": incident.incident_id,
            "proposed_verdict": "REQUIRES_ATTENTION",
            "verdict": "REQUIRES_ATTENTION",
            "confidence": 0.0,
            "raw_model_confidence": 0.0,
            "reason": block_detail,
            "supporting_evidence": [],
            "missing_evidence": ["Empirical Gate G8 certification with real LLM on exact active policy digest"],
            "analyst_questions": ["Complete real-provider empirical simulation (G8) or process in analyst-assisted review mode."],
            "latency_ms": 0,
            "model_identifier": "GOVERNANCE_GUARD",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "is_simulated": False,
            "execution_provenance": "GOVERNANCE_GUARD",
            "configured_provider": "GOVERNANCE_GUARD",
            "test_environment": classify_execution_provenance(model_identifier="GOVERNANCE_GUARD")["test_environment"],
            "validation_status": "POLICY_NOT_EMPIRICALLY_CERTIFIED",
            "validation_reason_codes": [
                "POLICY_NOT_EMPIRICALLY_CERTIFIED",
                *certification.blocking_reasons,
            ],
            "is_decisive_accepted": False,
            "proposal_validation_outcome": "BLOCKED_UNCERTIFIED_AUTONOMOUS_ACTION",
            "final_disposition": "BLOCKED_UNCERTIFIED_FOR_AUTONOMOUS_ACTION",
            "abstention_reason": block_detail,
            "evidence_completeness": 0.0,
            "grounding_ratio": 0.0,
            "canonical_evidence_count": norm_result.total_evidence_count,
            "policy_version_id": getattr(active_v, "id", None),
            "policy_version_number": getattr(active_v, "version_number", 1),
            "reevaluation_eligible": True,
            "deferral_reason": "POLICY_NOT_EMPIRICALLY_CERTIFIED",
            "reevaluation_attempts": prev_attempts + 1,
            "rule_name": rule.name if rule else incident.title,
            "severity": incident.severity,
            "evaluated_at": utc_now().isoformat(),
            "evaluated_by_user": username,
            **_governance_fields(certification),
        }
        return VerdictPipelineResult(
            verdict_data=verdict_data,
            early_exit=True,
            early_exit_kind="BLOCKED_UNCERTIFIED_FOR_AUTONOMOUS_ACTION",
            norm_result=norm_result,
            certification=certification,
            is_abstained=True,
            effective_verdict="REQUIRES_ATTENTION",
            escalation_reason=block_detail,
        )

    # 3. Resolve Shared Detection Semantics & Evidence Contract (honors RuleIntelligenceSnapshot)
    if rule:
        semantics, contract, snap = await get_rule_semantics_and_contract(
            db, rule, prompt_version=active_v
        )
    else:
        semantics, snap = None, None
        contract = EvidenceContractService.get_contract_for_rule(None, active_v)

    # Determine explicit provider early so preflight simulation allowance matches mode
    if is_simulation:
        chosen_provider_type = str(model_provider_type or "SIMULATED").upper().strip()
        preflight_allow_sim = chosen_provider_type == "SIMULATED"
    elif model_provider_type:
        if is_prod and str(model_provider_type).upper() == "SIMULATED":
            raise ValueError("Simulated model provider is strictly forbidden in production mode.")
        chosen_provider_type = str(model_provider_type).upper().strip()
        preflight_allow_sim = allow_mock
    elif allow_mock:
        is_online = await check_llm_available() if check_llm_available else False
        chosen_provider_type = "OPENAI_COMPATIBLE" if is_online else "SIMULATED"
        preflight_allow_sim = True
    else:
        chosen_provider_type = "OPENAI_COMPATIBLE"
        preflight_allow_sim = False

    # 4. Preflight Evidence Validation
    preflight = EvidencePreflightValidator.validate_preflight(
        incident_id=incident.incident_id,
        contract=contract,
        normalization_result=norm_result,
        allow_simulation=preflight_allow_sim,
    )
    if preflight.must_abstain_immediately and (
        (is_simulation and chosen_provider_type == "OPENAI_COMPATIBLE")
        or (not is_simulation and (not allow_simulated_fallback or is_prod))
    ):
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
            "is_simulated": (chosen_provider_type == "SIMULATED"),
            "execution_provenance": "PREFLIGHT_GUARD",
            "configured_provider": chosen_provider_type,
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
            "calibration_status": "NOT_CALIBRATED",
            "is_calibrated": False,
            "reevaluation_eligible": True,
            "deferral_reason": "EVIDENCE_MISSING" if preflight.critical_missing_fields else "EVIDENCE_CONTRACT_UNVERIFIED",
            "reevaluation_attempts": prev_attempts + 1,
            "rule_name": rule.name if rule else incident.title,
            "severity": incident.severity,
            "evaluated_at": utc_now().isoformat(),
            "evaluated_by_user": username,
            **_governance_fields(certification),
        }
        return VerdictPipelineResult(
            verdict_data=verdict_data,
            early_exit=True,
            early_exit_kind="PREFLIGHT_ABSTENTION",
            norm_result=norm_result,
            contract=contract,
            certification=certification,
            provider_type_used=chosen_provider_type,
            is_abstained=True,
            effective_verdict="REQUIRES_ATTENTION",
            trust_score=0,
            raw_trust_score=0,
            evidence_status="INSUFFICIENT",
            escalation_reason=preflight.reason,
            evidence_trace={
                "stage": "PREFLIGHT_GUARD",
                "preflight_status": preflight.preflight_status,
                "evidence_completeness": preflight.evidence_completeness,
                "missing_fields": list(preflight.missing_evidence_fields),
                "canonical_evidence_count": norm_result.total_evidence_count,
                "contract_id": contract.contract_id,
            },
        )

    # 5. Compile Unified Nine-Section Policy
    exec_mode = (
        CompilationExecutionMode.SIMULATION
        if (is_simulation or (not is_prod and allow_mock))
        else CompilationExecutionMode.LIVE
    )
    compiled_policy = PolicyCompilerService.compile_policy(
        rule=rule,
        prompt_version=active_v,
        execution_mode=exec_mode,
        raise_on_unapproved=False,
    )
    prompt_ver_num = compiled_policy.version_number or 1

    # 6. Verified Semantic RAG (rule-scoped, self-excluding, temporal cutoff protected)
    rag_result = await VerifiedSemanticRetrievalService.retrieve_verified_precedents(
        db=db,
        incident=incident,
        rule_id=rule.id if rule else "UNKNOWN_RULE",
        max_precedents=2,
    )

    # 7. Evidence-Preserving Token Budgeting
    payload_dict["evidence_contract"] = {
        "contract_id": contract.contract_id,
        "version": contract.version_number,
        "required_fields": [r.field for r in contract.required_evidence],
    }
    # Resolve per-model profile and capacity limits
    active_model = getattr(settings, "LOCAL_LLM_MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct-AWQ")
    model_profile = LLMConfigService.get_model_profile(active_model)
    configured_ctx = int(model_profile.get("max_context_tokens") or getattr(settings, "LOCAL_LLM_CONTEXT_BUDGET", 16384) or 16384)
    verified_model_len = getattr(settings, "LOCAL_LLM_VERIFIED_MAX_MODEL_LEN", None)
    effective_max_ctx = (
        min(configured_ctx, int(verified_model_len))
        if verified_model_len is not None and int(verified_model_len) > 0
        else configured_ctx
    )
    reserved_comp_tokens = int(model_profile.get("reserved_output_tokens") or getattr(settings, "LOCAL_LLM_MAX_TOKENS", 1024) or 1024)
    target_input = int(model_profile.get("target_input_budget") or getattr(settings, "LOCAL_LLM_TARGET_INPUT_BUDGET", 8192) or 8192)

    rule_spec = {
        "id": rule.id if rule else (incident.rule_id or "UNKNOWN"),
        "rule_id": getattr(rule, "rule_id", None) if rule else None,
        "name": rule.name if rule else incident.title,
        "severity": rule.severity if rule else incident.severity,
        "description": rule.description if rule else "",
    }
    rule_overhead_tokens = TokenBudgetService.estimate_tokens(rule_spec)
    budgeted = TokenBudgetService.budget_prompt(
        compiled_policy=compiled_policy,
        incident_payload=payload_dict,
        rag_block=rag_result.formatted_rag_block,
        max_context_tokens=effective_max_ctx,
        max_completion_tokens=reserved_comp_tokens,
        reserved_overhead_tokens=rule_overhead_tokens,
        model_name=active_model,
        target_input_budget=target_input,
    )

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
            "is_simulated": (chosen_provider_type == "SIMULATED"),
            "execution_provenance": "TOKEN_BUDGET_GUARD",
            "configured_provider": chosen_provider_type,
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
            **_governance_fields(certification),
        }
        return VerdictPipelineResult(
            verdict_data=verdict_data,
            early_exit=True,
            early_exit_kind="CONTEXT_OVERFLOW",
            norm_result=norm_result,
            contract=contract,
            compiled_policy=compiled_policy,
            certification=certification,
            prompt_tokens=budgeted.breakdown.total_prompt_tokens,
            completion_tokens=0,
            total_tokens=budgeted.breakdown.total_prompt_tokens,
            token_usage_source="ESTIMATED",
            provider_type_used=chosen_provider_type,
            is_abstained=True,
            effective_verdict="REQUIRES_ATTENTION",
            escalation_reason=budgeted.abstention_reason or "CONTEXT_WINDOW_EXCEEDED",
            evidence_trace={
                "stage": "TOKEN_BUDGET_GUARD",
                "token_budget_breakdown": budgeted.breakdown.model_dump(),
                "compilation_digest": compiled_policy.compilation_digest,
            },
        )

    prompt_text = budgeted.budgeted_system_prompt
    if budgeted.budgeted_rag_block:
        prompt_text += f"\n\n{budgeted.budgeted_rag_block}"
    budgeted_payload = budgeted.budgeted_incident_payload

    # Synchronize any newly created compacted/deduplicated canonical records into norm_result
    # so that independent claim grounding can verify model citations without reference errors
    existing_rec_ids = {r.evidence_id for r in norm_result.records}
    for item in budgeted_payload.get("canonical_evidence", []):
        eid = item.get("evidence_id")
        if eid and eid not in existing_rec_ids:
            norm_result.records.append(
                CanonicalEvidenceRecord(
                    evidence_id=eid,
                    incident_id=str(incident.incident_id),
                    source_system="FortiSIEM",
                    source_field=str(item.get("source_field", "unknown")),
                    observed_value=item.get("observed_value", ""),
                    evidence_type=str(item.get("evidence_type", "SECURITY_EVENT")),
                    integrity_digest="compacted",
                )
            )
            existing_rec_ids.add(eid)

    # 8. Invoke Provider
    verdict_obj, actual_provider_type = await _invoke_provider_with_guards(
        chosen_provider_type=chosen_provider_type,
        payload_dict=budgeted_payload,
        rule_spec=rule_spec,
        prompt_text=prompt_text,
        prompt_ver_num=prompt_ver_num,
        allow_mock_fallback=(not is_simulation and allow_mock),
        provider_factory=prov_factory,
        set_llm_online=set_llm_online,
        simulated_output_fn=simulated_output_fn,
        contract=contract,
        prompt_version=active_v,
    )

    # 9. Token Usage Accounting
    p_tokens = getattr(verdict_obj, "prompt_tokens", 0) or 0
    c_tokens = getattr(verdict_obj, "completion_tokens", 0) or 0
    t_tokens = getattr(verdict_obj, "total_tokens", 0) or (p_tokens + c_tokens)
    token_usage_source = "API_USAGE"
    if t_tokens == 0 and (
        getattr(verdict_obj, "validation_status", "VALID") in ("VALID", "SIMULATED", None)
        or getattr(verdict_obj, "is_simulated", False)
    ):
        p_tokens = max(50, len(prompt_text) // 4)
        c_tokens = max(20, len(str(getattr(verdict_obj, "reason", "") or "")) // 4)
        t_tokens = p_tokens + c_tokens
        token_usage_source = "ESTIMATED"
    elif t_tokens == 0:
        token_usage_source = "UNAVAILABLE"

    # 10. Claim Extraction, Independent Validator, and Verdict Trustworthiness
    raw_verdict_dict = (
        verdict_obj.model_dump()
        if hasattr(verdict_obj, "model_dump")
        else (
            verdict_obj.dict()
            if hasattr(verdict_obj, "dict")
            else {
                "verdict": verdict_obj.verdict,
                "confidence": verdict_obj.confidence,
                "reason": verdict_obj.reason,
                "supporting_evidence": verdict_obj.supporting_evidence,
                "supporting_claims": getattr(verdict_obj, "supporting_claims", []),
                "contradictory_evidence": getattr(verdict_obj, "contradictory_evidence", []),
                "validation_status": getattr(verdict_obj, "validation_status", "VALID"),
            }
        )
    )
    claim_grounding = ModelClaimExtractor.extract_and_ground_claims(
        incident_id=incident.incident_id,
        raw_verdict_output=raw_verdict_dict,
        normalization_result=norm_result,
    )

    val_res = IndependentVerdictValidator.validate_verdict(
        incident_id=incident.incident_id,
        proposed_verdict=verdict_obj.verdict,
        raw_model_confidence=verdict_obj.confidence,
        preflight=preflight,
        claim_grounding=claim_grounding,
        normalization_result=norm_result,
        contract=contract,
        allow_simulation=(actual_provider_type == "SIMULATED" or allow_mock),
        compilation_digest=compiled_policy.compilation_digest,
        model_reason=verdict_obj.reason,
        contradictory_evidence=getattr(verdict_obj, "contradictory_evidence", None),
    )

    hist_stats = historical_stats or {"sample_count": 0, "accuracy": None, "is_calibrated": False}
    auth_threshold = snap.threshold if snap else None
    def_status = (
        snap.definition_status
        if snap
        else ((rule.parsed_metadata or {}).get("definition_status", "VERIFIED") if rule else "INCOMPLETE")
    )

    trust_payload = dict(budgeted_payload)
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

    # 11. Reconcile Authoritative Verdict & Hard Safety Guardrails
    final_auth_verdict = val_res.final_verdict
    final_is_decisive = val_res.is_decisive_accepted
    final_validation_status = val_res.validation_status
    final_reason_codes = list(val_res.validation_reason_codes)
    final_confidence_display = (
        val_res.validated_confidence_display
        if val_res.validated_confidence_display is not None
        else verdict_obj.confidence
    )
    final_action_directive = val_res.analyst_action_directive

    raw_provider_status = str(getattr(verdict_obj, "validation_status", "VALID") or "VALID").upper().strip()
    if (
        raw_provider_status in ("INVALID_SCHEMA", "UNEXPECTED_VERDICT", "INVALID_MODEL_OUTPUT", "PARSE_ERROR")
        or "MODEL_OUTPUT_INVALID" in final_reason_codes
    ):
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
    elif val_res.proposed_verdict != final_auth_verdict or final_validation_status in (
        "REJECTED",
        "INSUFFICIENT_EVIDENCE",
        "GUARDRAIL_ABSTAINED",
    ):
        proposal_validation_outcome = "REJECTED_BY_VALIDATOR"
        final_disposition = "OVERRULED_TO_ANALYST_ATTENTION"
        abstention_reason = final_action_directive or "; ".join(final_reason_codes)
    else:
        proposal_validation_outcome = "MODEL_ABSTENTION"
        final_disposition = "SAFE_ANALYST_ESCALATION"
        abstention_reason = final_action_directive or "Model recommended cautious analyst escalation."

    if (
        final_auth_verdict in ("TRUE_POSITIVE", "FALSE_POSITIVE")
        and trust_res.effective_verdict == UserVisibleVerdict.REQUIRES_ANALYST_ATTENTION
    ):
        esc_lower = (trust_res.escalation_reason or "").lower()
        is_hard_guardrail_block = bool(
            trust_res.missing_evidence
            or trust_res.contradictory_evidence
            or (
                trust_res.claim_verification
                and (
                    trust_res.claim_verification.has_unsupported_assertions
                    or trust_res.claim_verification.has_contradictions
                    or trust_res.claim_verification.grounded_claims == 0
                )
            )
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
    elif (
        val_res.detected_contradictions
        or final_validation_status == "REJECTED"
        or "EVIDENCE_CONTRADICTION" in final_reason_codes
    ):
        if trust_res.trust_score is not None:
            trust_res.trust_score = min(3, trust_res.trust_score)

    if certification and not certification.autonomous_operation_eligible:
        gov_note = f"ADVISORY_ONLY_NOT_EMPIRICALLY_CERTIFIED: {certification.advisory_notice}"
        if gov_note not in trust_res.confidence_limitations:
            trust_res.confidence_limitations.append(gov_note)

    verdict_prov = classify_execution_provenance(
        is_simulated=bool(getattr(verdict_obj, "is_simulated", actual_provider_type == "SIMULATED")),
        model_identifier=str(getattr(verdict_obj, "model_identifier", actual_provider_type) or ""),
        validation_status=final_validation_status,
        eligibility_status="ABSTAINED" if final_auth_verdict == "REQUIRES_ATTENTION" else "EVALUATED",
        source_type=(pilot_context.get("source_type") if pilot_context else ("SIMULATION" if is_simulation else "LIVE")),
        base_url=settings.LOCAL_LLM_BASE_URL,
    )

    gov_meta = _governance_fields(certification)
    verdict_data = {
        "incident_id": incident.incident_id,
        "proposed_verdict": val_res.proposed_verdict,
        "verdict": final_auth_verdict,
        "confidence": final_confidence_display,
        "raw_model_confidence": verdict_obj.confidence,
        "reason": (
            verdict_obj.reason
            if final_is_decisive
            else f"{final_action_directive} [Validation: {'; '.join(final_reason_codes)}]. Model rationale: {verdict_obj.reason}"
        ),
        "supporting_evidence": verdict_obj.supporting_evidence,
        "supporting_claims": [
            c.model_dump() if hasattr(c, "model_dump") else c.dict()
            for c in claim_grounding.claims
        ],
        "missing_evidence": val_res.missing_evidence_fields or verdict_obj.missing_evidence,
        "analyst_questions": verdict_obj.analyst_questions,
        "latency_ms": verdict_obj.latency_ms,
        "model_identifier": verdict_obj.model_identifier,
        "prompt_tokens": p_tokens,
        "completion_tokens": c_tokens,
        "total_tokens": t_tokens,
        "token_usage_source": token_usage_source,
        "is_simulated": bool(verdict_obj.is_simulated),
        "execution_provenance": verdict_prov["execution_provenance"],
        "configured_provider": verdict_prov["configured_provider"],
        "provider_type": actual_provider_type,
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
        "reevaluation_eligible": bool(
            not final_is_decisive
            and ("EVIDENCE_MISSING" in final_reason_codes or "EVIDENCE_CONTRACT_UNVERIFIED" in final_reason_codes)
        ),
        "deferral_reason": (
            "EVIDENCE_MISSING"
            if not final_is_decisive and "EVIDENCE_MISSING" in final_reason_codes
            else None
        ),
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
        "pilot_id": pilot_context.get("pilot_id") if pilot_context else None,
        "pilot_mode": pilot_context.get("mode") if pilot_context else None,
        "pilot_version": pilot_context.get("pilot_version") if pilot_context else None,
        **gov_meta,
    }

    evidence_trace = {
        "contract_id": val_res.contract_id,
        "contract_version": val_res.contract_version,
        "compilation_digest": compiled_policy.compilation_digest,
        "policy_digest": gov_meta.get("active_policy_digest"),
        "preflight_status": preflight.preflight_status,
        "evidence_completeness": val_res.evidence_completeness,
        "grounding_ratio": val_res.grounding_ratio,
        "total_claims_count": val_res.total_claims_count,
        "grounded_claims_count": val_res.grounded_claims_count,
        "unsupported_claims_count": val_res.unsupported_claims_count,
        "detected_contradictions": val_res.detected_contradictions,
        "rag_retrieval_status": rag_result.retrieval_status,
        "retrieved_precedents_count": len(rag_result.precedents),
        "canonical_evidence_count": norm_result.total_evidence_count,
        "validation_status": final_validation_status,
        "validation_reason_codes": final_reason_codes,
        "token_usage_source": token_usage_source,
        "prompt_tokens": p_tokens,
        "completion_tokens": c_tokens,
        "total_tokens": t_tokens,
        "provider_type": actual_provider_type,
        "execution_provenance": verdict_prov["execution_provenance"],
        "model_identifier": verdict_obj.model_identifier,
    }

    return VerdictPipelineResult(
        verdict_data=verdict_data,
        early_exit=False,
        verdict_obj=verdict_obj,
        trust_res=trust_res,
        val_res=val_res,
        claim_grounding=claim_grounding,
        norm_result=norm_result,
        contract=contract,
        compiled_policy=compiled_policy,
        certification=certification,
        prompt_tokens=p_tokens,
        completion_tokens=c_tokens,
        total_tokens=t_tokens,
        token_usage_source=token_usage_source,
        provider_type_used=actual_provider_type,
        verdict_prov=verdict_prov,
        is_abstained=(final_auth_verdict == "REQUIRES_ATTENTION"),
        effective_verdict=final_auth_verdict,
        proposed_verdict=val_res.proposed_verdict,
        trust_score=int(trust_res.trust_score),
        raw_trust_score=int(trust_res.raw_trust_score),
        evidence_status=trust_res.evidence_status.value,
        escalation_reason=trust_res.escalation_reason or abstention_reason,
        evidence_trace=evidence_trace,
    )

