"""
Verdict Trustworthiness Engine (AIS 2.1).
Computes deterministic, evidence-grounded Trust Scores (1–10 ordinal scale)
from five explicit scoring dimensions (0–100 raw points).

Scoring Rubric:
1. Direct Claim-to-Evidence Support: Max 35 pts
2. Evidence Source Reliability: Max 20 pts
3. Contradiction & Counterevidence Handling: Max 15 pts
4. Independent Corroboration: Max 15 pts
5. Historical Empirical Validation Support: Max 15 pts
Total: 100 pts

Trust Score Mapping (Ordinal 1–10):
- 1–2: Very Weak (< 30 pts) -> Analyst Attention
- 3–4: Weak / Substantially Uncertain (30–49 pts) -> Analyst Attention
- 5–6: Partial Support (50–69 pts) -> Analyst Attention by Default
- 7–8: Strong Support (70–89 pts) -> Eligible for Automatic Verdict if safety gates pass
- 9: Very Strong Corroborated Support (90–97 pts) -> Eligible for Automatic Verdict
- 10: Exceptional Independently Validated Support (98–100 pts) -> Rare, requires verified ground truth
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from app.schemas.verdict_intelligence import (
    EvidenceStatus,
    UserVisibleVerdict,
    TrustScoreDimensionBreakdown,
    VerdictTrustAssessmentResult,
    EvidenceSufficiencyAssessmentResult,
    ClaimVerificationResult,
)
from app.services.evidence_sufficiency_engine import EvidenceSufficiencyEngine
from app.services.verdict_claim_validator import VerdictClaimValidator
from app.services.verdict_guardrails_engine import VerdictGuardrailsEngine

logger = logging.getLogger("ai_verdict.trustworthiness")


class VerdictTrustworthinessEngine:
    """
    Evaluates incident evidence, model assertions, and historical validation support
    to produce an explainable, auditable Trust Score and guardrailed verdict.
    """
    CALCULATION_VERSION = "v2.2.0"

    @classmethod
    def score_to_ordinal(cls, raw_total: float, is_calibrated: bool = False, sample_count: int = 0) -> int:
        """Maps raw 0-100 score to 1-10 ordinal scale with uncalibrated capping."""
        if raw_total >= 98.0 and is_calibrated and sample_count >= 30:
            ordinal = 10
        elif raw_total >= 90.0:
            ordinal = 9
        elif raw_total >= 80.0:
            ordinal = 8
        elif raw_total >= 70.0:
            ordinal = 7
        elif raw_total >= 60.0:
            ordinal = 6
        elif raw_total >= 50.0:
            ordinal = 5
        elif raw_total >= 40.0:
            ordinal = 4
        elif raw_total >= 30.0:
            ordinal = 3
        elif raw_total >= 20.0:
            ordinal = 2
        else:
            ordinal = 1

        if not is_calibrated or sample_count < 30:
            ordinal = min(6, ordinal)

        return ordinal

    @classmethod
    def evaluate_verdict_trust(
        cls,
        incident_payload: Dict[str, Any],
        model_output: Dict[str, Any],
        contract: Optional[Any] = None,
        archetype_id: Optional[str] = None,
        authoritative_threshold: Optional[float] = None,
        definition_status: str = "VERIFIED",
        historical_sample_count: int = 0,
        historical_accuracy: Optional[float] = None,
        is_calibrated: bool = False,
        calibrated_prob: Optional[float] = None,
    ) -> VerdictTrustAssessmentResult:
        """
        Executes complete multi-dimensional trust assessment and applies verdict guardrails.
        """
        incident_id = str(incident_payload.get("incident_id") or incident_payload.get("id") or "INC-UNKNOWN")
        rule_id = str(incident_payload.get("rule_id") or "RULE-UNKNOWN")
        suggested_verdict = str(
            model_output.get("verdict")
            or model_output.get("suggested_verdict")
            or model_output.get("proposed_verdict")
            or "REQUIRES_ATTENTION"
        ).upper().strip()
        raw_confidence = float(model_output.get("confidence") or model_output.get("llm_confidence") or 100.0)

        # 1. Evaluate Evidence Sufficiency
        sufficiency = EvidenceSufficiencyEngine.evaluate_incident_sufficiency(
            incident_payload=incident_payload,
            contract=contract,
            archetype_id=archetype_id,
            authoritative_threshold=authoritative_threshold,
        )

        # 2. Verify Model Claims
        claim_verification = VerdictClaimValidator.verify_claims(
            incident_id=incident_id,
            model_output=model_output,
            incident_payload=incident_payload,
            authoritative_threshold=authoritative_threshold,
            authoritative_definition_status=definition_status,
        )

        # -------------------------------------------------------------
        # DIMENSION 1: Direct Claim-to-Evidence Support (Max 35 pts)
        # -------------------------------------------------------------
        if claim_verification.total_claims > 0:
            claim_support = claim_verification.grounding_ratio * 35.0
            if claim_verification.has_unsupported_assertions:
                claim_support = max(0.0, claim_support - 10.0)
        elif suggested_verdict in ("TRUE_POSITIVE", "FALSE_POSITIVE"):
            # Decisive proposals with zero claims cannot earn high direct-claim credit
            claim_support = 0.0
        else:
            # Explicit abstention may receive modest sufficiency credit
            claim_support = 15.0 if sufficiency.evidence_status == EvidenceStatus.SUFFICIENT else 5.0

        dim1 = round(min(35.0, max(0.0, claim_support)), 2)

        # -------------------------------------------------------------
        # DIMENSION 2: Evidence Source Reliability (Max 20 pts)
        # -------------------------------------------------------------
        # Derived from sufficiency.integrity_provenance_score (which is out of 25)
        dim2 = round(min(20.0, (sufficiency.integrity_provenance_score / 25.0) * 20.0), 2)

        # -------------------------------------------------------------
        # DIMENSION 3: Contradiction & Counterevidence Handling (Max 15 pts)
        # -------------------------------------------------------------
        contra_points = 15.0
        if sufficiency.contradictions_detected:
            contra_points -= 10.0
        if claim_verification.has_contradictions:
            contra_points -= 10.0

        # Check if model acknowledged contradictory evidence honestly
        model_contradictions = model_output.get("contradictory_evidence") or []
        if model_contradictions and contra_points < 15.0:
            contra_points = min(15.0, contra_points + 5.0)  # Honest acknowledgement bonus

        dim3 = round(max(0.0, min(15.0, contra_points)), 2)

        # -------------------------------------------------------------
        # DIMENSION 4: Independent Corroboration (Max 15 pts)
        # -------------------------------------------------------------
        # Derived from sufficiency.consistency_corroboration_score (out of 20)
        dim4 = round(min(15.0, (sufficiency.consistency_corroboration_score / 20.0) * 15.0), 2)

        # -------------------------------------------------------------
        # DIMENSION 5: Historical Empirical Validation Support (Max 15 pts)
        # -------------------------------------------------------------
        acc_pct = (historical_accuracy * 100.0) if (historical_accuracy is not None and historical_accuracy <= 1.0) else historical_accuracy
        acc_ratio = (acc_pct / 100.0) if acc_pct is not None else 0.90

        if is_calibrated or (historical_sample_count >= 30 and (acc_pct is None or acc_pct >= 70.0)):
            hist_pts = acc_ratio * 15.0
            hist_status = "CALIBRATED"
        elif historical_sample_count >= 5:
            hist_pts = min(10.0, acc_ratio * 10.0)
            hist_status = "PARTIALLY_VALIDATED"
        else:
            hist_pts = 5.0  # Conservative baseline points
            hist_status = "UNCALIBRATED"

        dim5 = round(max(0.0, min(15.0, hist_pts)), 2)

        # -------------------------------------------------------------
        # Total Raw Score & Ordinal 1–10 Normalization
        # -------------------------------------------------------------
        effective_calibrated = bool(is_calibrated or hist_status == "CALIBRATED")
        raw_total = round(dim1 + dim2 + dim3 + dim4 + dim5, 2)
        ordinal_score = cls.score_to_ordinal(
            raw_total=raw_total,
            is_calibrated=effective_calibrated,
            sample_count=historical_sample_count if historical_sample_count > 0 else (50 if effective_calibrated else 0),
        )

        # If mandatory evidence is absent or material contradictions exist, score cannot exceed 3/10
        _claim_contradiction = bool(
            getattr(claim_verification, "has_contradictions", False)
            or getattr(claim_verification, "contradiction_detected", False)
            or (model_output or {}).get("contradictory_evidence")
        )
        _zero_grounded_decisive = bool(
            str((model_output or {}).get("verdict") or (model_output or {}).get("proposed_verdict") or "").upper().strip() in ("TRUE_POSITIVE", "FALSE_POSITIVE")
            and (getattr(claim_verification, "has_unsupported_assertions", False) or getattr(claim_verification, "grounded_claims", 0) == 0)
        )
        _model_val_status = str((model_output or {}).get("validation_status", "VALID")).upper().strip()
        _raw_prop_label = str((model_output or {}).get("verdict") or (model_output or {}).get("proposed_verdict") or "").upper().strip()
        _is_malformed_output = (
            _model_val_status in ("INVALID_SCHEMA", "UNEXPECTED_VERDICT", "INVALID_MODEL_OUTPUT", "PARSE_ERROR", "HTTP_ERROR")
            or (_raw_prop_label != "" and _raw_prop_label not in ("TRUE_POSITIVE", "FALSE_POSITIVE", "REQUIRES_ATTENTION"))
        )

        if sufficiency.mandatory_fields_missing or sufficiency.evidence_status == EvidenceStatus.CONFLICTING or _claim_contradiction or _zero_grounded_decisive:
            ordinal_score = min(3, ordinal_score)
        if _is_malformed_output:
            ordinal_score = min(2, ordinal_score)

        breakdown = TrustScoreDimensionBreakdown(
            direct_claim_support=dim1,
            source_reliability=dim2,
            contradiction_handling=dim3,
            independent_corroboration=dim4,
            historical_validation_support=dim5,
            total_raw_score=raw_total,
        )

        # -------------------------------------------------------------
        # Apply Deterministic Guardrails
        # -------------------------------------------------------------
        effective_verdict, escalation_reason, confidence_limitations = VerdictGuardrailsEngine.apply_guardrails(
            proposed_verdict=suggested_verdict,
            raw_confidence=raw_confidence,
            sufficiency=sufficiency,
            claim_verification=claim_verification,
            raw_trust_score=raw_total,
            trust_score_ordinal=ordinal_score,
            is_calibrated=effective_calibrated,
            definition_status=definition_status,
            authoritative_threshold=authoritative_threshold,
            incident_context=incident_payload,
        )

        # Check if supporting evidence is completely unavailable
        has_telemetry = any(
            k not in ("id", "incident_id", "rule_id", "severity", "category", "created_at") and bool(v)
            for k, v in incident_payload.items()
        )
        is_empty_telemetry = not has_telemetry
        is_totally_insufficient = sufficiency.overall_sufficiency_score <= 0.0 and len(sufficiency.mandatory_fields_missing) >= 3

        if is_empty_telemetry or is_totally_insufficient:
            trust_status = "NOT_CALCULABLE"
            ordinal_score = None
            confidence_limitations.append("NOT_CALCULABLE: Sufficient supporting telemetry is unavailable to calculate a trustworthy verdict score.")
        else:
            trust_status = "CALCULATED"

        # Build human-readable explanation
        explanation_lines = [
            f"Suggested Verdict: {suggested_verdict} | Guardrail-Adjusted Effective Verdict: {effective_verdict.value}.",
            f"Verdict Trust Score: {f'{ordinal_score}/10' if ordinal_score is not None else 'NOT_CALCULABLE'} (Raw: {raw_total:.1f}/100) | Evidence Sufficiency: {sufficiency.overall_sufficiency_score:.1f}/100.",
        ]
        if escalation_reason:
            explanation_lines.append(f"Escalation Reason: {escalation_reason}")
        if sufficiency.mandatory_fields_missing:
            explanation_lines.append(f"Missing Telemetry: {', '.join(sufficiency.mandatory_fields_missing)}.")
        if sufficiency.contradictions_detected:
            explanation_lines.append(f"Contradictions: {'; '.join(sufficiency.contradictions_detected)}.")

        supporting_evidence = [
            f"{c.claim_text} ({c.grounding_status})" for c in claim_verification.claims if c.is_grounded
        ]

        return VerdictTrustAssessmentResult(
            incident_id=incident_id,
            rule_id=rule_id,
            archetype=sufficiency.archetype,
            suggested_verdict=suggested_verdict,
            effective_verdict=effective_verdict,
            trust_score=ordinal_score,
            trust_status=trust_status,
            calculation_version=cls.CALCULATION_VERSION,
            raw_trust_score=raw_total,
            evidence_sufficiency_score=sufficiency.overall_sufficiency_score,
            evidence_status=sufficiency.evidence_status,
            score_dimensions=breakdown,
            supporting_evidence=supporting_evidence,
            contradictory_evidence=sufficiency.contradictions_detected,
            missing_evidence=sufficiency.mandatory_fields_missing,
            confidence_limitations=confidence_limitations,
            historical_validation_status=hist_status,
            is_calibrated=effective_calibrated,
            calibrated_probability=calibrated_prob,
            applicable_policy_version=incident_payload.get("prompt_version_number"),
            applicable_contract_version=incident_payload.get("contract_version"),
            escalation_reason=escalation_reason,
            human_readable_explanation=" ".join(explanation_lines),
            model_identifier=str(model_output.get("model_identifier", "default-model")),
            is_simulated=bool(model_output.get("is_simulated", False)),
            evaluated_at=datetime.utcnow(),
            evidence_sufficiency=sufficiency,
            claim_verification=claim_verification,
        )

    @classmethod
    def compute_trust_score(
        cls,
        rule_id: str,
        effective_verdict: Optional[str] = None,
        proposed_verdict: Optional[str] = None,
        evidence_assessment: Optional[Any] = None,
        sufficiency: Optional[Any] = None,
        claim_result: Optional[Any] = None,
        claim_verification: Optional[Any] = None,
        historical_sample_size: int = 0,
        historical_accuracy: Optional[float] = None,
        is_calibrated: bool = False,
        **kwargs
    ) -> VerdictTrustAssessmentResult:
        verdict = effective_verdict or proposed_verdict or "REQUIRES_ATTENTION"
        suff = evidence_assessment or sufficiency
        claim_res = claim_result or claim_verification

        # 1. Direct Claim Support (Max 35)
        if claim_res and getattr(claim_res, "total_claims", 0) > 0:
            claim_support = claim_res.grounding_ratio * 35.0
            if getattr(claim_res, "has_unsupported_assertions", False):
                claim_support = max(0.0, claim_support - 10.0)
        else:
            claim_support = 25.0 if suff and getattr(suff, "is_sufficient", False) else 5.0
        dim1 = round(min(35.0, max(0.0, claim_support)), 2)

        # 2. Source Reliability (Max 20)
        dim2 = round(min(20.0, (getattr(suff, "integrity_provenance_score", 20.0) / 25.0) * 20.0), 2)

        # 3. Contradiction Handling (Max 15)
        contra_pts = 15.0
        if getattr(suff, "contradictions_detected", None):
            contra_pts -= 10.0
        if getattr(claim_res, "has_contradictions", False) or getattr(claim_res, "contradicted_claims", 0) > 0:
            contra_pts -= 10.0
        dim3 = round(max(0.0, min(15.0, contra_pts)), 2)

        # 4. Independent Corroboration (Max 15)
        dim4 = round(min(15.0, (getattr(suff, "consistency_corroboration_score", 15.0) / 20.0) * 15.0), 2)

        # 5. Historical Empirical Validation (Max 15)
        acc_pct = (historical_accuracy * 100.0) if (historical_accuracy is not None and historical_accuracy <= 1.0) else historical_accuracy
        acc_ratio = (acc_pct / 100.0) if acc_pct is not None else 0.90
        calibrated = is_calibrated or (historical_sample_size >= 30 and (acc_pct is None or acc_pct >= 70.0))

        if calibrated:
            dim5 = round(acc_ratio * 15.0, 2)
            hist_status = "CALIBRATED"
        elif historical_sample_size >= 5:
            dim5 = round(min(10.0, acc_ratio * 10.0), 2)
            hist_status = "PARTIALLY_VALIDATED"
        else:
            dim5 = 5.0
            hist_status = "UNCALIBRATED"

        raw_total = round(dim1 + dim2 + dim3 + dim4 + dim5, 2)
        ordinal = cls.score_to_ordinal(raw_total, is_calibrated=calibrated, sample_count=historical_sample_size)
        if suff and (getattr(suff, "mandatory_fields_missing", None) or getattr(suff, "evidence_status", None) == EvidenceStatus.CONFLICTING):
            ordinal = min(3, ordinal)

        breakdown = TrustScoreDimensionBreakdown(
            direct_claim_support=dim1,
            source_reliability=dim2,
            contradiction_handling=dim3,
            independent_corroboration=dim4,
            historical_validation_support=dim5,
            total_raw_score=raw_total,
        )

        eff_v = UserVisibleVerdict(verdict) if verdict in [v.value for v in UserVisibleVerdict] else UserVisibleVerdict.REQUIRES_ANALYST_ATTENTION

        return VerdictTrustAssessmentResult(
            incident_id="INC-COMPUTED",
            rule_id=rule_id,
            archetype=getattr(suff, "archetype", "UNKNOWN"),
            suggested_verdict=verdict,
            effective_verdict=eff_v,
            trust_score=ordinal,
            trust_status="CALCULATED",
            calculation_version=cls.CALCULATION_VERSION,
            raw_trust_score=raw_total,
            evidence_sufficiency_score=getattr(suff, "overall_sufficiency_score", 80.0),
            evidence_status=getattr(suff, "evidence_status", EvidenceStatus.SUFFICIENT),
            score_dimensions=breakdown,
            supporting_evidence=[f"{c.claim_text} ({c.grounding_status})" for c in getattr(claim_res, "claims", []) if c.is_grounded],
            contradictory_evidence=getattr(suff, "contradictions_detected", []),
            missing_evidence=getattr(suff, "mandatory_fields_missing", []),
            confidence_limitations=[],
            historical_validation_status=hist_status,
            is_calibrated=calibrated,
            human_readable_explanation=f"Direct computation for {rule_id}. Trust Score: {ordinal}/10.",
            model_identifier="direct-evaluator",
            evaluated_at=datetime.utcnow(),
            evidence_sufficiency=suff,
            claim_verification=claim_res,
        )

    calculate_trust_score = compute_trust_score
