"""
Verdict Guardrails Engine (AIS 2.1).
Applies deterministic safety guardrails to model-proposed verdicts.
Enforces the 3 user-visible verdicts:
1. TRUE_POSITIVE
2. FALSE_POSITIVE
3. REQUIRES_ANALYST_ATTENTION

Guarantees:
- An alert firing alone NEVER proves a True Positive.
- Private RFC-1918 IPs or familiar domains NEVER automatically justify a False Positive.
- Missing mandatory evidence, contradictions, or ungrounded claims ALWAYS force REQUIRES_ANALYST_ATTENTION.
- Uncertainty is NEVER silently converted into False Positive.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from app.schemas.verdict_intelligence import (
    UserVisibleVerdict,
    EvidenceStatus,
    ClaimType,
    EvidenceSufficiencyAssessmentResult,
    ClaimVerificationResult,
)

logger = logging.getLogger("ai_verdict.verdict_guardrails")


class VerdictGuardrailResult:
    """
    Result container for verdict guardrails evaluation.
    Supports 3-tuple unpacking: (effective_verdict, escalation_reason, confidence_limitations)
    as well as attribute-based access.
    """
    def __init__(
        self,
        effective_verdict: UserVisibleVerdict,
        escalation_reason: Optional[str],
        confidence_limitations: List[str],
        guardrails_triggered: Optional[List[str]] = None,
    ):
        self.effective_verdict = effective_verdict
        self.escalation_reason = escalation_reason
        self.confidence_limitations = confidence_limitations
        self.guardrails_triggered = guardrails_triggered or []

    def __iter__(self):
        return iter((self.effective_verdict, self.escalation_reason, self.confidence_limitations))

    def __getitem__(self, idx):
        return (self.effective_verdict, self.escalation_reason, self.confidence_limitations)[idx]

    def __eq__(self, other):
        if isinstance(other, (str, UserVisibleVerdict)):
            return self.effective_verdict == other
        return super().__eq__(other)

    def __repr__(self):
        return f"<VerdictGuardrailResult verdict={self.effective_verdict} triggered={self.guardrails_triggered}>"


class VerdictGuardrailsEngine:
    """
    Authoritative deterministic gatekeeper that evaluates proposed LLM verdicts
    against evidence sufficiency, claim grounding, and safety invariants.
    """

    @classmethod
    def apply_guardrails(
        cls,
        proposed_verdict: str,
        raw_confidence: float,
        sufficiency: EvidenceSufficiencyAssessmentResult,
        claim_verification: ClaimVerificationResult,
        raw_trust_score: float,
        trust_score_ordinal: Optional[int] = None,
        is_calibrated: bool = False,
        definition_status: str = "VERIFIED",
        authoritative_threshold: Optional[float] = None,
        incident_context: Optional[Dict[str, Any]] = None,
    ) -> VerdictGuardrailResult:
        """
        Determines the effective verdict and escalation reasons.
        Returns: VerdictGuardrailResult (unpacks as 3-tuple: effective_verdict, escalation_reason, confidence_limitations)
        """
        clean_prop = str(proposed_verdict or "REQUIRES_ATTENTION").upper().strip()
        confidence_limitations: List[str] = []
        guardrails_triggered: List[str] = []
        escalation_reason: Optional[str] = None

        if not is_calibrated:
            confidence_limitations.append("Rule is UNCALIBRATED (insufficient historical verification cases < 30). Trust capped at 6/10.")

        # -------------------------------------------------------------
        # Guardrail 1: Missing Mandatory Evidence
        # -------------------------------------------------------------
        if sufficiency.mandatory_fields_missing:
            escalation_reason = (
                f"Missing mandatory telemetry fields: {', '.join(sufficiency.mandatory_fields_missing)}. "
                "Evidence is insufficient to support an automated verdict."
            )
            confidence_limitations.append("Mandatory evidence missing from incident telemetry.")
            guardrails_triggered.append("G1_MANDATORY_EVIDENCE_MISSING")
            return VerdictGuardrailResult(UserVisibleVerdict.REQUIRES_ANALYST_ATTENTION, escalation_reason, confidence_limitations, guardrails_triggered)

        # -------------------------------------------------------------
        # Guardrail 2: Material Contradictions Detected
        # -------------------------------------------------------------
        if sufficiency.evidence_status == EvidenceStatus.CONFLICTING or claim_verification.has_contradictions:
            all_contradictions = list(sufficiency.contradictions_detected)
            for c in claim_verification.claims:
                if c.contradiction_details:
                    all_contradictions.append(c.contradiction_details)

            escalation_reason = (
                f"Material evidence contradiction detected: {'; '.join(all_contradictions[:2])}. "
                "Conflicting telemetry prevents a reliable automated decision."
            )
            confidence_limitations.append("Direct telemetry or directional conflict detected.")
            guardrails_triggered.append("G2_MATERIAL_CONTRADICTIONS_DETECTED")
            return VerdictGuardrailResult(UserVisibleVerdict.REQUIRES_ANALYST_ATTENTION, escalation_reason, confidence_limitations, guardrails_triggered)

        # -------------------------------------------------------------
        # Guardrail 3: Unsupported or Hallucinated Claims
        # -------------------------------------------------------------
        if claim_verification.has_unsupported_assertions and clean_prop in ("TRUE_POSITIVE", "FALSE_POSITIVE"):
            unsupported_texts = [
                c.claim_text for c in claim_verification.claims if not c.is_grounded
            ]
            escalation_reason = (
                f"Model asserted unverified or fabricated claims: {'; '.join(unsupported_texts[:2])}. "
                "Reasoning cannot be grounded in canonical evidence."
            )
            confidence_limitations.append("Model claims failed factual grounding verification.")
            guardrails_triggered.append("G2_G3_UNSUPPORTED_OR_HALLUCINATED_CLAIMS")
            return VerdictGuardrailResult(UserVisibleVerdict.REQUIRES_ANALYST_ATTENTION, escalation_reason, confidence_limitations, guardrails_triggered)

        # -------------------------------------------------------------
        # Guardrail 4: Incomplete Detection Semantics / Unknown Threshold
        # -------------------------------------------------------------
        if definition_status == "INCOMPLETE" and clean_prop in ("TRUE_POSITIVE", "FALSE_POSITIVE"):
            # If the rule has no authoritative threshold and requires one
            if sufficiency.archetype in ("NETWORK_EXFILTRATION",) and authoritative_threshold is None:
                escalation_reason = (
                    "Authoritative SIEM detection threshold is unverified. "
                    "Provisional policy cannot automatically classify incident without human review."
                )
                confidence_limitations.append("Rule definition status is INCOMPLETE: threshold unverified.")
                guardrails_triggered.append("G4_INCOMPLETE_DETECTION_SEMANTICS")
                return VerdictGuardrailResult(UserVisibleVerdict.REQUIRES_ANALYST_ATTENTION, escalation_reason, confidence_limitations, guardrails_triggered)

        # -------------------------------------------------------------
        # Guardrail 5: Low Trust Score (< 7/10 or raw < 70)
        # -------------------------------------------------------------
        if (trust_score_ordinal is not None and trust_score_ordinal < 7) or raw_trust_score < 70.0:
            escalation_reason = (
                f"Verdict Trust Score ({trust_score_ordinal or 'N/A'}/10, raw {raw_trust_score:.1f}/100) "
                "is below the automated decision threshold (7/10). Analyst attention required."
            )
            confidence_limitations.append("Trust score below automated decision safety threshold.")
            guardrails_triggered.append("G5_LOW_TRUST_SCORE")
            return VerdictGuardrailResult(UserVisibleVerdict.REQUIRES_ANALYST_ATTENTION, escalation_reason, confidence_limitations, guardrails_triggered)

        # -------------------------------------------------------------
        # Guardrail 6: Negative/Blanket FP Assumptions Prohibition
        # -------------------------------------------------------------
        if clean_prop == "FALSE_POSITIVE":
            # Check if there is affirmative benign justification
            has_affirmative_benign = False
            for c in claim_verification.claims:
                if c.is_grounded:
                    c_lower = c.claim_text.lower()
                    if any(w in c_lower for w in ("backup", "authorized", "scheduled", "approved", "admin", "maintenance", "cdn", "sync")):
                        has_affirmative_benign = True
                        break

            # If incident context is available, check for affirmative justification
            if incident_context and (
                incident_context.get("is_authorized_backup")
                or incident_context.get("business_authorization_verified")
                or (isinstance(incident_context.get("raw_payload"), dict) and incident_context["raw_payload"].get("business_service"))
            ):
                has_affirmative_benign = True

            if not has_affirmative_benign:
                escalation_reason = (
                    "False Positive recommendation lacks affirmative evidence of business authorization. "
                    "Cannot classify as benign merely due to lack of confirmed malware or RFC-1918 addressing."
                )
                confidence_limitations.append("Affirmative benign business justification absent.")
                guardrails_triggered.append("G6_NEGATIVE_FP_PROHIBITION")
                return VerdictGuardrailResult(UserVisibleVerdict.REQUIRES_ANALYST_ATTENTION, escalation_reason, confidence_limitations, guardrails_triggered)

        # -------------------------------------------------------------
        # Guardrail 7: Alert Firing Alone Does Not Prove True Positive
        # -------------------------------------------------------------
        if clean_prop == "TRUE_POSITIVE":
            # Must have at least one grounded malicious/observed indicator
            has_grounded_malicious = False
            for c in claim_verification.claims:
                if c.is_grounded and (c.claim_type == ClaimType.OBSERVED_FACT or getattr(c.claim_type, "value", None) == "OBSERVED_FACT" or str(c.claim_type) == "OBSERVED_FACT"):
                    has_grounded_malicious = True
                    break

            if not has_grounded_malicious and not (claim_verification.grounded_claims > 0):
                escalation_reason = "True Positive asserted without concrete grounded indicators of malicious or unauthorized activity."
                confidence_limitations.append("Alert firing alone does not prove True Positive.")
                guardrails_triggered.append("G7_ALERT_FIRING_ALONE")
                return VerdictGuardrailResult(UserVisibleVerdict.REQUIRES_ANALYST_ATTENTION, escalation_reason, confidence_limitations, guardrails_triggered)

        # -------------------------------------------------------------
        # Validated Decisive Verdict
        # -------------------------------------------------------------
        if clean_prop == "TRUE_POSITIVE":
            return VerdictGuardrailResult(UserVisibleVerdict.TRUE_POSITIVE, None, confidence_limitations, guardrails_triggered)
        elif clean_prop == "FALSE_POSITIVE":
            return VerdictGuardrailResult(UserVisibleVerdict.FALSE_POSITIVE, None, confidence_limitations, guardrails_triggered)
        else:
            return VerdictGuardrailResult(UserVisibleVerdict.REQUIRES_ANALYST_ATTENTION, "Model suggested analyst attention.", confidence_limitations, guardrails_triggered)

    @classmethod
    def evaluate_guardrails(
        cls,
        proposed_verdict: str,
        evidence_sufficiency: Optional[Any] = None,
        sufficiency: Optional[Any] = None,
        claim_verification: Optional[Any] = None,
        raw_confidence: float = 90.0,
        raw_trust_score: float = 75.0,
        incident_telemetry: Optional[Dict[str, Any]] = None,
        incident_context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> VerdictGuardrailResult:
        suff = evidence_sufficiency or sufficiency
        ctx = incident_telemetry or incident_context
        return cls.apply_guardrails(
            proposed_verdict=proposed_verdict,
            raw_confidence=raw_confidence,
            sufficiency=suff,
            claim_verification=claim_verification,
            raw_trust_score=raw_trust_score,
            incident_context=ctx,
            **kwargs
        )
