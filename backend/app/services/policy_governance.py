"""
Canonical Rule Resolution, Shared Semantics/Contract Resolution, and
Runtime Policy Governance / Certification Helpers for Agent Intelligence Studio 2.1.

Separates:
  - Structural Approval (G1-G7 + manual/studio APPROVED state)
  - Empirical Validation (G8 PASSED via non-simulated OPENAI_COMPATIBLE run on exact active policy digest)
  - Autonomous Operation Eligibility (requires BOTH valid Structural Approval and matching Empirical Validation)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import re

from sqlalchemy import and_, desc, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident
from app.models.policy_quality import PolicyQualityAssessmentRecord
from app.models.prompt import PromptVersion
from app.models.rule import Rule
from app.models.rule_intelligence import RuleIntelligenceSnapshot
from app.models.verdict_intelligence import HistoricalEvaluationRunRecord
from app.schemas.evidence_contract import RuleEvidenceContract
from app.schemas.rule_intelligence import (
    DetectionSemantics,
    SemanticsDefinitionStatus,
    SourceProvenance,
)
from app.schemas.verdict_intelligence import EvaluationValidationState
from app.services.evidence_contract_service import EvidenceContractService
from app.services.policy_quality_validator import PolicyQualityValidator
from app.services.rule_intelligence_analyzer import RuleIntelligenceAnalyzer

MIN_EMPIRICAL_SAMPLES = 5
SIMULATED_PROVIDER_TOKENS = {
    "SIMULATED",
    "MOCK",
    "HEURISTIC",
    "SIMULATED_FALLBACK",
    "MOCK_LLM",
    "FALLBACK",
}
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


@dataclass
class RuleMatchContext:
    """Resolved rule match boundaries preventing cross-rule sibling contamination."""

    rule: Optional[Rule]
    matched_rule_ids: List[str] = field(default_factory=list)
    unambiguous_event_type: Optional[str] = None
    ambiguous_event_types: List[str] = field(default_factory=list)
    sibling_rules_with_same_event_type: List[str] = field(default_factory=list)

    @property
    def canonical_rule_identifier(self) -> Optional[str]:
        if self.rule:
            return self.rule.rule_id or self.rule.id
        return self.matched_rule_ids[0] if self.matched_rule_ids else None


@dataclass
class PolicyRuntimeCertification:
    """Runtime governance state derived from policy version, digest, and empirical simulation provenance."""

    rule_id: str
    prompt_version_id: Optional[str]
    prompt_version_status: str
    structural_approval_eligible: bool
    empirical_validation_eligible: bool
    autonomous_operation_eligible: bool
    empirical_validation_status: str
    policy_governance_mode: str
    active_policy_digest: Optional[str]
    certified_policy_digest: Optional[str] = None
    latest_run_id: Optional[str] = None
    latest_provider_type: Optional[str] = None
    latest_model_identifier: Optional[str] = None
    blocking_reasons: List[str] = field(default_factory=list)
    advisory_notice: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "prompt_version_id": self.prompt_version_id,
            "prompt_version_status": self.prompt_version_status,
            "structural_approval_eligible": self.structural_approval_eligible,
            "empirical_validation_eligible": self.empirical_validation_eligible,
            "autonomous_operation_eligible": self.autonomous_operation_eligible,
            "empirical_validation_status": self.empirical_validation_status,
            "policy_governance_mode": self.policy_governance_mode,
            "active_policy_digest": self.active_policy_digest,
            "certified_policy_digest": self.certified_policy_digest,
            "latest_run_id": self.latest_run_id,
            "latest_provider_type": self.latest_provider_type,
            "latest_model_identifier": self.latest_model_identifier,
            "blocking_reasons": list(self.blocking_reasons),
            "advisory_notice": self.advisory_notice,
        }


async def resolve_canonical_rule(db: AsyncSession, rule_identifier: Optional[str]) -> Optional[Rule]:
    """
    Resolve a rule deterministically by logical Rule.rule_id, Rule.id UUID, or
    (only when globally unique in `rules`) exact Rule.event_type.
    Never performs fuzzy/substring matching that could conflate similarly named rules.
    """
    ident = str(rule_identifier or "").strip()
    if not ident:
        return None

    res = await db.execute(
        select(Rule).where(or_(Rule.id == ident, Rule.rule_id == ident))
    )
    matches = res.scalars().all()
    if matches:
        # Prefer exact UUID match, then exact logical rule_id match
        for r in matches:
            if r.id == ident:
                return r
        for r in matches:
            if r.rule_id == ident:
                return r
        return matches[0]

    # Exact event_type fallback ONLY if unambiguous across the entire Rule catalog
    ev_res = await db.execute(select(Rule).where(Rule.event_type == ident))
    ev_matches = ev_res.scalars().all()
    if len(ev_matches) == 1:
        return ev_matches[0]
    return None


async def build_rule_incident_context(
    db: AsyncSession,
    rule: Optional[Rule],
    fallback_rule_id: Optional[str] = None,
) -> RuleMatchContext:
    """
    Build deterministic rule matching criteria:
    - Includes Rule.id and Rule.rule_id for explicit FK/string links.
    - Includes Rule.event_type ONLY for unlinked incidents AND ONLY when no sibling
      Rule shares the same event_type.
    """
    if rule is None:
        ids = [str(fallback_rule_id).strip()] if fallback_rule_id else []
        return RuleMatchContext(rule=None, matched_rule_ids=[x for x in ids if x])

    matched_ids = list(
        dict.fromkeys(x for x in (rule.id, rule.rule_id) if x and str(x).strip())
    )
    unambiguous_ev: Optional[str] = None
    ambiguous_evs: List[str] = []
    siblings: List[str] = []

    if rule.event_type and str(rule.event_type).strip():
        ev = str(rule.event_type).strip()
        sib_res = await db.execute(
            select(Rule.id, Rule.rule_id).where(Rule.event_type == ev)
        )
        rows = sib_res.all()
        if len(rows) <= 1:
            unambiguous_ev = ev
        else:
            ambiguous_evs.append(ev)
            siblings = [
                str(rid or uid)
                for uid, rid in rows
                if str(uid) != str(rule.id)
            ]

    return RuleMatchContext(
        rule=rule,
        matched_rule_ids=matched_ids,
        unambiguous_event_type=unambiguous_ev,
        ambiguous_event_types=ambiguous_evs,
        sibling_rules_with_same_event_type=siblings,
    )


def build_rule_incident_sql_filter(ctx: RuleMatchContext):
    """Build SQLAlchemy WHERE clause returning ONLY incidents belonging to `ctx.rule`."""
    clauses = []
    if ctx.matched_rule_ids:
        clauses.append(Incident.rule_id.in_(ctx.matched_rule_ids))
    if ctx.unambiguous_event_type:
        clauses.append(
            and_(
                or_(Incident.rule_id.is_(None), Incident.rule_id == ""),
                Incident.event_type == ctx.unambiguous_event_type,
            )
        )
    if not clauses:
        return literal(False)
    return or_(*clauses) if len(clauses) > 1 else clauses[0]


def verify_incident_matches_rule(
    inc: Incident, ctx: RuleMatchContext
) -> Tuple[bool, Optional[str]]:
    """
    Defensive row-level check confirming `inc` belongs strictly to `ctx.rule`.
    Prevents sibling rules or conflicting payload rule identifiers from leaking through.
    """
    inc_rule_id = str(getattr(inc, "rule_id", "") or "").strip()
    if inc_rule_id:
        if inc_rule_id in ctx.matched_rule_ids:
            return True, None
        return False, "RULE_MISMATCH"

    inc_event_type = str(getattr(inc, "event_type", "") or "").strip()
    if not ctx.unambiguous_event_type or inc_event_type != ctx.unambiguous_event_type:
        return False, "RULE_MISMATCH"

    raw_payload = getattr(inc, "raw_payload", None) or {}
    if isinstance(raw_payload, dict):
        payload_rule = str(
            raw_payload.get("ruleId")
            or raw_payload.get("rule_id")
            or raw_payload.get("eventRuleId")
            or ""
        ).strip()
        if payload_rule and (
            payload_rule.startswith("PH_RULE_") or _UUID_RE.match(payload_rule)
        ):
            allowed = set(ctx.matched_rule_ids)
            if ctx.unambiguous_event_type:
                allowed.add(ctx.unambiguous_event_type)
            if payload_rule not in allowed:
                return False, "RULE_MISMATCH"

    return True, None


def reconstruct_semantics_from_snapshot(
    snap: Optional[RuleIntelligenceSnapshot],
) -> Optional[DetectionSemantics]:
    """Reconstruct DetectionSemantics from a persisted RuleIntelligenceSnapshot safely."""
    if not snap or not getattr(snap, "semantics_payload", None):
        return None
    try:
        sem = DetectionSemantics.model_validate(snap.semantics_payload)
        if snap.threshold is not None:
            sem.threshold = snap.threshold
        if snap.threshold_unit:
            sem.threshold_unit = snap.threshold_unit
        if snap.aggregation_window:
            sem.aggregation_window = snap.aggregation_window
        if snap.definition_status:
            try:
                sem.definition_status = SemanticsDefinitionStatus(snap.definition_status)
            except Exception:
                pass
        if snap.source_provenance:
            try:
                sem.source_provenance = SourceProvenance(snap.source_provenance)
            except Exception:
                pass
        if snap.primary_archetype and snap.primary_archetype != "UNKNOWN":
            sem.primary_behavior = snap.primary_archetype
        return sem
    except Exception:
        return None


async def get_rule_semantics_and_contract(
    db: AsyncSession,
    rule: Rule,
    prompt_version: Optional[PromptVersion] = None,
    authoritative_siem_definition: Optional[Dict[str, Any]] = None,
    for_quality_validation: bool = False,
) -> Tuple[DetectionSemantics, RuleEvidenceContract, Optional[RuleIntelligenceSnapshot]]:
    """
    Single shared resolver for DetectionSemantics + RuleEvidenceContract used across
    Live Triage, Prompt Studio, and Historical Simulation to guarantee parity.
    """
    snap_res = await db.execute(
        select(RuleIntelligenceSnapshot).where(RuleIntelligenceSnapshot.rule_id == rule.id)
    )
    snap = snap_res.scalar_one_or_none()

    semantics: Optional[DetectionSemantics] = None
    rule_meta = getattr(rule, "parsed_metadata", None) or {}
    rule_has_authoritative_meta = (
        rule_meta.get("source") in ("FORTISIEM_LIVE_RULE_API", "AUTHORITATIVE_XML_IMPORT")
        or rule_meta.get("provenance") in ("AUTHORITATIVE_XML_IMPORT", "AUTHORITATIVE_SIEM_DEFINITION")
    )

    if authoritative_siem_definition:
        semantics = RuleIntelligenceAnalyzer.analyze_rule(
            rule, authoritative_siem_definition=authoritative_siem_definition
        )
    elif snap is not None and snap.semantics_payload and not (
        snap.source_provenance == SourceProvenance.HEURISTIC_PARSER.value
        and rule_has_authoritative_meta
    ):
        semantics = reconstruct_semantics_from_snapshot(snap)

    if semantics is None:
        # Preserve HEAD behavior: only apply threshold-only snapshots without a
        # populated semantics_payload during G1-G8 policy quality checks so synthetic
        # test fixtures with empty semantics_payload keep their runtime evidence contracts.
        snap_auth_def: Optional[Dict[str, Any]] = None
        if (
            for_quality_validation
            and snap is not None
            and snap.definition_status == SemanticsDefinitionStatus.VERIFIED.value
            and snap.threshold is not None
        ):
            snap_auth_def = {
                "threshold": snap.threshold,
                "threshold_unit": snap.threshold_unit,
                "aggregation_window": snap.aggregation_window,
            }
        semantics = RuleIntelligenceAnalyzer.analyze_rule(
            rule, authoritative_siem_definition=snap_auth_def
        )

    contract = EvidenceContractService.get_contract_for_rule(
        rule,
        prompt_version=prompt_version,
        semantics=semantics,
    )
    return semantics, contract, snap


def _is_simulated_run_config(cfg: Dict[str, Any], run: Optional[HistoricalEvaluationRunRecord] = None) -> bool:
    provider_raw = str(cfg.get("provider_type") or "").upper().strip()
    prov_raw = str(cfg.get("execution_provenance") or "").upper().strip()
    if cfg.get("is_simulated") is True:
        return True
    if not provider_raw or provider_raw in SIMULATED_PROVIDER_TOKENS:
        return True
    if prov_raw in SIMULATED_PROVIDER_TOKENS:
        return True
    model_id = str(cfg.get("model_identifier") or cfg.get("model_name") or "").upper()
    if "SIMULATED" in model_id:
        return True
    return False


async def assess_policy_runtime_certification(
    db: AsyncSession,
    rule: Optional[Rule],
    prompt_version: Optional[PromptVersion],
    min_samples: int = MIN_EMPIRICAL_SAMPLES,
) -> PolicyRuntimeCertification:
    """
    Evaluate whether an active policy version is authorized for:
      - Structural Approval (G1-G7 + APPROVED status)
      - Empirical Validation (G8 PASSED via non-simulated LLM run on exact digest)
      - Autonomous Operation (BOTH valid for exact active policy digest)
    Stale digests, simulated runs, insufficient data, or failed evaluations strictly
    deny autonomous authorization while permitting advisory analyst-assisted triage.
    """
    rule_ident = (getattr(rule, "rule_id", None) or getattr(rule, "id", None) or "UNKNOWN")

    if not prompt_version:
        return PolicyRuntimeCertification(
            rule_id=str(rule_ident),
            prompt_version_id=None,
            prompt_version_status="NONE",
            structural_approval_eligible=False,
            empirical_validation_eligible=False,
            autonomous_operation_eligible=False,
            empirical_validation_status="NOT_EVALUATED",
            policy_governance_mode="ADVISORY_ANALYST_REVIEW_REQUIRED",
            active_policy_digest=None,
            blocking_reasons=["NO_ACTIVE_POLICY_VERSION"],
            advisory_notice="No approved policy version active; human review is mandatory.",
        )

    active_digest = PolicyQualityValidator.compute_policy_digest(prompt_version)
    pv_status = str(getattr(prompt_version, "status", "DRAFT") or "DRAFT").upper()
    structural_ok = pv_status == "APPROVED"
    reasons: List[str] = []

    if not structural_ok:
        reasons.append(f"POLICY_NOT_APPROVED:{pv_status}")

    # Inspect latest quality assessment for this prompt version
    assessment: Optional[PolicyQualityAssessmentRecord] = None
    qa_id = getattr(prompt_version, "quality_assessment_id", None)
    if qa_id:
        qa_res = await db.execute(
            select(PolicyQualityAssessmentRecord).where(
                PolicyQualityAssessmentRecord.id == str(qa_id)
            )
        )
        assessment = qa_res.scalar_one_or_none()

    if not assessment:
        qa_res = await db.execute(
            select(PolicyQualityAssessmentRecord)
            .where(PolicyQualityAssessmentRecord.prompt_version_id == str(prompt_version.id))
            .order_by(desc(PolicyQualityAssessmentRecord.evaluated_at))
            .limit(1)
        )
        assessment = qa_res.scalar_one_or_none()

    if assessment:
        if assessment.policy_digest and assessment.policy_digest != active_digest:
            structural_ok = False
            reasons.append("STALE_ASSESSMENT_DIGEST")
        gate_results = getattr(assessment, "gate_results", None) or {}
        for gid in ("G1", "G2", "G3", "G4", "G5", "G6", "G7"):
            gate = gate_results.get(gid) or {}
            if str(gate.get("status") or "").upper() == "FAILED":
                structural_ok = False
                reasons.append(f"STRUCTURAL_GATE_FAILED:{gid}")

    # Inspect latest COMPLETED empirical run bound specifically to this prompt_version.id
    rule_scope_ids = [x for x in (getattr(rule, "id", None), getattr(rule, "rule_id", None)) if x]
    run_q = select(HistoricalEvaluationRunRecord).where(
        and_(
            HistoricalEvaluationRunRecord.policy_version_id == str(prompt_version.id),
            HistoricalEvaluationRunRecord.status == "COMPLETED",
        )
    )
    if rule_scope_ids:
        run_q = run_q.where(HistoricalEvaluationRunRecord.rule_id.in_(rule_scope_ids))
    run_q = run_q.order_by(desc(HistoricalEvaluationRunRecord.completed_at), desc(HistoricalEvaluationRunRecord.started_at)).limit(1)
    run_res = await db.execute(run_q)
    latest_run = run_res.scalar_one_or_none()

    empirical_ok = False
    empirical_status = "NOT_EVALUATED"
    certified_digest: Optional[str] = None
    latest_run_id: Optional[str] = None
    latest_provider: Optional[str] = None
    latest_model: Optional[str] = None

    if not latest_run:
        reasons.append("MISSING_EMPIRICAL_SIMULATION_RUN")
    else:
        latest_run_id = str(latest_run.id)
        cfg = getattr(latest_run, "config_snapshot", None) or {}
        metrics = getattr(latest_run, "metrics", None) or {}
        latest_provider = str(cfg.get("provider_type") or ("SIMULATED" if cfg.get("is_simulated") else "UNKNOWN")).upper()
        latest_model = str(cfg.get("model_identifier") or cfg.get("model_name") or "")
        run_digest = cfg.get("policy_digest")
        val_state = str(latest_run.validation_state or "NOT_EVALUATED").upper()
        eval_count = int(
            getattr(latest_run, "evaluated_cases", None)
            or metrics.get("total_evaluated_cases")
            or metrics.get("evaluated_cases")
            or 0
        )
        verified_count = int(
            getattr(latest_run, "verified_ground_truth_cases", None)
            or metrics.get("verified_ground_truth_cases")
            or metrics.get("independent_group_count")
            or metrics.get("eligible_cases")
            or eval_count
        )
        critical_regressions = int(
            metrics.get("critical_regressions")
            or metrics.get("critical_false_negatives")
            or 0
        )

        is_sim = _is_simulated_run_config(cfg, latest_run)
        if is_sim:
            empirical_status = "SIMULATED_ONLY"
            reasons.append("SIMULATED_RUN_CANNOT_CERTIFY")
        elif not run_digest:
            empirical_status = "STALE_DIGEST"
            reasons.append("MISSING_POLICY_DIGEST_IN_RUN")
        elif run_digest != active_digest:
            empirical_status = "STALE_DIGEST"
            reasons.append("STALE_POLICY_DIGEST")
        elif val_state not in ("VALIDATED", "PASS", "PASSED", "EVALUATED_PASSED"):
            empirical_status = val_state
            reasons.append(f"EMPIRICAL_VALIDATION_{val_state}")
        elif eval_count < min_samples or verified_count < min_samples:
            empirical_status = EvaluationValidationState.INSUFFICIENT_DATA.value
            reasons.append(
                f"INSUFFICIENT_VERIFIED_SAMPLES:{verified_count}<{min_samples}"
            )
        elif critical_regressions > 0:
            empirical_status = EvaluationValidationState.EVALUATION_FAILED.value
            reasons.append(f"CRITICAL_REGRESSIONS:{critical_regressions}")
        else:
            empirical_ok = True
            empirical_status = "EVALUATED_PASSED"
            certified_digest = str(run_digest)

    autonomous_ok = bool(structural_ok and empirical_ok and pv_status == "APPROVED")
    mode = (
        "EMPIRICALLY_CERTIFIED"
        if autonomous_ok
        else "ADVISORY_ANALYST_REVIEW_REQUIRED"
    )
    if autonomous_ok:
        notice = (
            f"Policy v{prompt_version.version_number} empirically certified on active digest "
            f"{active_digest[:12]} via real provider {latest_provider}."
        )
    else:
        notice = (
            f"Policy is operating in advisory/shadow mode only ({', '.join(reasons) or 'UNCERTIFIED'}): "
            "autonomous actions and closures are blocked until empirical Gate G8 passes with a real LLM on verified ground truth."
        )

    return PolicyRuntimeCertification(
        rule_id=str(rule_ident),
        prompt_version_id=str(prompt_version.id),
        prompt_version_status=pv_status,
        structural_approval_eligible=structural_ok,
        empirical_validation_eligible=empirical_ok,
        autonomous_operation_eligible=autonomous_ok,
        empirical_validation_status=empirical_status,
        policy_governance_mode=mode,
        active_policy_digest=active_digest,
        certified_policy_digest=certified_digest,
        latest_run_id=latest_run_id,
        latest_provider_type=latest_provider,
        latest_model_identifier=latest_model or None,
        blocking_reasons=reasons,
        advisory_notice=notice,
    )
