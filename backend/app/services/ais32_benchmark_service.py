"""
AIS 3.2 — Development Dataset Isolation, Mode A / Mode B Live GPU Runner,
Comprehensive Empirical Evaluation Engine, and AIS 3.3 Fresh Holdout Planner.

Key Invariants:
- NEVER modifies or unlocks `AIS_2_6E_FROZEN_20` or `AIS_3_0_INDEPENDENT_HOLDOUT_100`.
- `AIS_3_2_DEVELOPMENT` strictly excludes all protected benchmark incident IDs,
  raw evidence SHA-256 duplicates, and LearningRecord-exposed incidents.
- Development labels NEVER enter model inference payloads or dynamic rule contracts.
- Reports Raw LLM, Validated Application, and Effective Operational Verdicts separately
  with exact denominators, Wilson 95% CIs, and baselines (Always-TP, Always-FP, Always-Abstain).
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import uuid
from collections import Counter, defaultdict
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.ais32_intelligence import IntelligenceExecutionRecord
from app.models.analyst_feedback import AnalystVerdictReview, BenchmarkCohort, BenchmarkCohortItem
from app.models.incident import HistoricalGroundTruth, Incident
from app.models.learning import LearningRecord
from app.models.rule import Rule
from app.services.ais27_benchmark_runner import AIS27BenchmarkRunner
from app.services.blind_review_guard import AIS_3_0_HOLDOUT_COHORT_ID, FROZEN_AIS_2_6E_COHORT_ID
from app.services.empirical_accuracy_evaluator import EmpiricalAccuracyEvaluator
from app.services.evidence_preflight_validator import EvidencePreflightValidator
from app.services.model_claim_extractor import ModelClaimExtractor
from app.services.modular_verdict_validator import ModularVerdictValidator
from app.services.organizational_context_service import OrganizationalContextService
from app.services.rule_intelligence_engine import RuleIntelligenceEngine
from app.services.universal_prompt_engine import UniversalPromptEngine
from app.services.verdict_trustworthiness_engine import VerdictTrustworthinessEngine
from app.utils.datetime_utils import utc_now

AIS_3_2_DEVELOPMENT_COHORT_ID = "AIS_3_2_DEVELOPMENT"
AIS_3_3_FUTURE_COHORT_ID = "AIS_3_3_INDEPENDENT_HOLDOUT"
PROTECTED_COHORTS = (FROZEN_AIS_2_6E_COHORT_ID, AIS_3_0_HOLDOUT_COHORT_ID)


def _sha256_canonical(obj: Any) -> str:
    if isinstance(obj, str):
        return hashlib.sha256(obj.encode("utf-8")).hexdigest()
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str, ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _pct(num: int, den: int) -> Optional[float]:
    if den <= 0:
        return None
    return round((num / den) * 100.0, 2)


def _wilson_pct(successes: int, trials: int) -> Optional[Dict[str, float]]:
    if trials <= 0:
        return None
    ci = EmpiricalAccuracyEvaluator.calculate_wilson_ci(successes, trials)
    return {
        "point": round((ci.point_estimate or 0.0) * 100.0, 2),
        "lower_95": round((ci.lower_bound or 0.0) * 100.0, 2),
        "upper_95": round((ci.upper_bound or 0.0) * 100.0, 2),
    }


def _normalize_gt_label(raw_val: Optional[str]) -> str:
    s = str(raw_val or "").upper().strip()
    if s in ("TRUE_POSITIVE", "TRUE POSITIVE", "VERIFIED_TP", "TP"):
        return "TRUE_POSITIVE"
    if s in ("FALSE_POSITIVE", "FALSE POSITIVE", "VERIFIED_FP", "FP"):
        return "FALSE_POSITIVE"
    if s in ("INCONCLUSIVE", "INSUFFICIENT_EVIDENCE", "UNVERIFIED"):
        return "INCONCLUSIVE"
    return "UNREVIEWED"


class AIS32BenchmarkService:
    """Authoritative AIS 3.2 cohort isolation, paired Mode A/B execution, and empirical evaluator."""

    @classmethod
    async def verify_protected_cohorts_intact(cls, db: AsyncSession) -> Dict[str, Any]:
        """Verifies protected historical benchmark cohorts remain unaltered and isolated."""
        report: Dict[str, Any] = {}
        for ckey in PROTECTED_COHORTS:
            cohort = (
                await db.execute(select(BenchmarkCohort).where(BenchmarkCohort.cohort_key == ckey))
            ).scalar_one_or_none()
            if not cohort:
                report[ckey] = {"present": False, "item_count": 0, "locked_reviews": 0}
                continue
            items = (
                await db.execute(select(BenchmarkCohortItem).where(BenchmarkCohortItem.cohort_id == cohort.id))
            ).scalars().all()
            inc_ids = [it.incident_db_id for it in items if it.incident_db_id]
            locked_cnt = 0
            if inc_ids:
                locked_cnt = len(
                    (
                        await db.execute(
                            select(AnalystVerdictReview.id).where(
                                AnalystVerdictReview.incident_id.in_(inc_ids),
                                AnalystVerdictReview.is_locked.is_(True),
                            )
                        )
                    ).all()
                )
            report[ckey] = {
                "present": True,
                "is_frozen": cohort.is_frozen,
                "excluded_from_learning": cohort.excluded_from_learning,
                "item_count": len(items),
                "locked_reviews": locked_cnt,
                "gt2_count": sum(1 for it in items if it.certification_status == "GT2_SINGLE_REVIEW"),
                "gt3_count": sum(1 for it in items if it.certification_status in ("GT3_CERTIFIED", "CERTIFIED_INCONCLUSIVE")),
            }
        return report

    @classmethod
    async def build_development_cohort(
        cls,
        db: AsyncSession,
        *,
        cohort_key: str = AIS_3_2_DEVELOPMENT_COHORT_ID,
        target_min: int = 60,
        target_max: int = 100,
    ) -> Dict[str, Any]:
        """
        Selects an isolated development cohort (`AIS_3_2_DEVELOPMENT`) completely disjoint from
        `AIS_2_6E_FROZEN_20` and `AIS_3_0_INDEPENDENT_HOLDOUT_100` (zero ID, DB UUID, or raw-event-hash overlap).
        Does NOT fabricate labels; records real analyst/GT availability cleanly.
        """
        existing = (
            await db.execute(select(BenchmarkCohort).where(BenchmarkCohort.cohort_key == cohort_key))
        ).scalar_one_or_none()

        # Collect protected IDs and protected raw evidence hashes
        protected_fids: Set[str] = set()
        protected_db_ids: Set[str] = set()
        protected_hashes: Set[str] = set()
        for pkey in PROTECTED_COHORTS:
            p_coh = (
                await db.execute(select(BenchmarkCohort).where(BenchmarkCohort.cohort_key == pkey))
            ).scalar_one_or_none()
            if p_coh:
                p_items = (
                    await db.execute(
                        select(BenchmarkCohortItem)
                        .where(BenchmarkCohortItem.cohort_id == p_coh.id)
                        .options(selectinload(BenchmarkCohortItem.incident).selectinload(Incident.events))
                    )
                ).scalars().all()
                for pit in p_items:
                    protected_fids.add(pit.fortisiem_incident_id)
                    if pit.incident_db_id:
                        protected_db_ids.add(pit.incident_db_id)
                    if pit.raw_evidence_sha256:
                        protected_hashes.add(pit.raw_evidence_sha256)
                    if pit.incident:
                        ev, _ = UniversalPromptEngine.extract_sanitized_events_and_summary(pit.incident)
                        protected_hashes.add(_sha256_canonical(ev))

        if existing:
            items = (
                await db.execute(
                    select(BenchmarkCohortItem)
                    .where(BenchmarkCohortItem.cohort_id == existing.id)
                    .order_by(BenchmarkCohortItem.priority_rank.asc())
                )
            ).scalars().all()
            return {
                "cohort_key": cohort_key,
                "already_exists": True,
                "count": len(items),
                "id_overlap_with_protected": len({it.fortisiem_incident_id for it in items} & protected_fids),
                "hash_overlap_with_protected": len({it.raw_evidence_sha256 for it in items if it.raw_evidence_sha256} & protected_hashes),
            }

        # Exclude LearningRecord incidents as well
        learned_ids = {row[0] for row in (await db.execute(select(LearningRecord.incident_id))).all()}

        # Fetch candidate incidents outside protected cohorts
        all_incs = (
            await db.execute(
                select(Incident)
                .options(
                    selectinload(Incident.events),
                    selectinload(Incident.rule),
                    selectinload(Incident.ground_truth),
                )
                .order_by(Incident.created_at.desc())
            )
        ).scalars().all()

        # Also check any non-benchmark AnalystVerdictReview labels
        rev_rows = (
            await db.execute(select(AnalystVerdictReview).order_by(desc(AnalystVerdictReview.created_at)))
        ).scalars().all()
        rev_by_inc: Dict[str, AnalystVerdictReview] = {}
        for rr in rev_rows:
            if rr.incident_id not in rev_by_inc:
                rev_by_inc[rr.incident_id] = rr

        # Stratified selection across rules & archetypes, deduplicated by raw hash
        seen_hashes: Set[str] = set()
        candidates_by_rule: Dict[str, List[Tuple[Incident, str, str, str]]] = defaultdict(list)

        for inc in all_incs:
            if inc.id in protected_db_ids or inc.incident_id in protected_fids or inc.id in learned_ids:
                continue
            ev, _ = UniversalPromptEngine.extract_sanitized_events_and_summary(inc)
            if not ev and not inc.raw_payload:
                continue
            r_hash = _sha256_canonical(ev)
            if r_hash in protected_hashes or r_hash in seen_hashes:
                continue
            seen_hashes.add(r_hash)

            # Determine honest label availability (never fabricated)
            gt_label = "UNREVIEWED"
            if inc.id in rev_by_inc:
                gt_label = _normalize_gt_label(rev_by_inc[inc.id].analyst_verdict)
            elif inc.ground_truth and inc.ground_truth.resolution:
                gt_label = _normalize_gt_label(inc.ground_truth.resolution)

            rule_key = (inc.rule.rule_id if inc.rule else None) or inc.event_type or "UNKNOWN"
            candidates_by_rule[rule_key].append((inc, r_hash, gt_label, rule_key))

        # Round-robin stratified selection across rules (preferring labeled items first for empirical eval)
        for rk in candidates_by_rule:
            candidates_by_rule[rk].sort(key=lambda tup: (0 if tup[2] in ("TRUE_POSITIVE", "FALSE_POSITIVE") else 1, tup[0].incident_id))

        selected: List[Tuple[Incident, str, str, str]] = []
        rule_keys = sorted(candidates_by_rule.keys())
        while len(selected) < target_max:
            progressed = False
            for rk in rule_keys:
                if candidates_by_rule[rk]:
                    selected.append(candidates_by_rule[rk].pop(0))
                    progressed = True
                    if len(selected) >= target_max:
                        break
            if not progressed:
                break

        cohort = BenchmarkCohort(
            cohort_key=cohort_key,
            name="AIS 3.2 Development Cohort (Rule-Diverse, Holdout-Disjoint)",
            description="Strictly disjoint development evaluation cohort for AIS 3.2 universal rule intelligence.",
            version="3.2",
            is_frozen=False,
            required_reviewers=1,
            excluded_from_learning=True,
        )
        db.add(cohort)
        await db.flush()

        for rank, (inc, r_hash, gt_label, rule_key) in enumerate(selected, start=1):
            db.add(
                BenchmarkCohortItem(
                    cohort_id=cohort.id,
                    incident_db_id=inc.id,
                    fortisiem_incident_id=inc.incident_id,
                    rule_id=rule_key,
                    rule_name=(inc.rule.name if inc.rule else inc.title) or rule_key,
                    customer=inc.customer or "DEFAULT",
                    is_priority=(rank <= 10),
                    priority_rank=rank,
                    raw_evidence_sha256=r_hash,
                    eligibility_status="ELIGIBLE",
                    certification_status="DEV_LABELED" if gt_label in ("TRUE_POSITIVE", "FALSE_POSITIVE", "INCONCLUSIVE") else "DEV_UNLABELED",
                    certified_verdict=gt_label if gt_label != "UNREVIEWED" else None,
                    exposure_risk_flag=False,
                )
            )
        await db.commit()

        return {
            "cohort_key": cohort_key,
            "already_exists": False,
            "count": len(selected),
            "labeled_count": sum(1 for _, _, lbl, _ in selected if lbl in ("TRUE_POSITIVE", "FALSE_POSITIVE")),
            "inconclusive_label_count": sum(1 for _, _, lbl, _ in selected if lbl == "INCONCLUSIVE"),
            "unlabeled_count": sum(1 for _, _, lbl, _ in selected if lbl == "UNREVIEWED"),
            "distinct_rules": len({rk for _, _, _, rk in selected}),
            "id_overlap_with_protected": 0,
            "hash_overlap_with_protected": 0,
        }

    @classmethod
    async def execute_mode_run(
        cls,
        db: AsyncSession,
        *,
        cohort_key: str = AIS_3_2_DEVELOPMENT_COHORT_ID,
        mode: str = "MODE_B",
        run_key: Optional[str] = None,
        target_fids: Optional[List[str]] = None,
        max_incidents: Optional[int] = None,
        max_context_tokens: int = 8192,
        max_completion_tokens: int = 1024,
        timeout_seconds: float = 180.0,
        transport_override: Optional[Callable[..., Any]] = None,
        allow_repair_retry: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes real GPU (or explicit test transport) evaluation for MODE_A or MODE_B
        across the specified development cohort with per-incident checkpointing.
        """
        mode_u = "MODE_A" if str(mode).upper().strip() in ("A", "MODE_A", "NEUTRAL") else "MODE_B"
        cohort = (
            await db.execute(select(BenchmarkCohort).where(BenchmarkCohort.cohort_key == cohort_key))
        ).scalar_one_or_none()
        if not cohort:
            raise ValueError(f"Cohort '{cohort_key}' not found.")

        # Preflight Server 2 check when live
        if transport_override is None:
            rt = await AIS27BenchmarkRunner.verify_gpu_runtime()
            avail = [str(m.get("id")) for m in ((rt.get("models_payload") or {}).get("data") or []) if m.get("id")]
            if rt.get("models_http_status") != 200 or "Qwen/Qwen3-14B-AWQ" not in avail:
                raise RuntimeError(f"Server 2 target model Qwen/Qwen3-14B-AWQ unavailable: {avail}")

        items = (
            await db.execute(
                select(BenchmarkCohortItem)
                .where(BenchmarkCohortItem.cohort_id == cohort.id)
                .options(
                    selectinload(BenchmarkCohortItem.incident).selectinload(Incident.events),
                    selectinload(BenchmarkCohortItem.incident).selectinload(Incident.rule),
                )
                .order_by(BenchmarkCohortItem.priority_rank.asc(), BenchmarkCohortItem.fortisiem_incident_id.asc())
            )
        ).scalars().all()
        if target_fids:
            fid_set = {str(x).strip() for x in target_fids}
            items = [it for it in items if it.fortisiem_incident_id in fid_set]
        if max_incidents and max_incidents > 0:
            items = items[:max_incidents]

        actual_run_key = run_key or f"AIS32-{mode_u}-{utc_now().strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:6]}"
        existing_rows = (
            await db.execute(
                select(IntelligenceExecutionRecord).where(
                    IntelligenceExecutionRecord.run_key == actual_run_key,
                    IntelligenceExecutionRecord.mode == mode_u,
                )
            )
        ).scalars().all()
        run_id = existing_rows[0].run_id if existing_rows else str(uuid.uuid4())
        done_fids = {r.fortisiem_incident_id for r in existing_rows if r.execution_status == "COMPLETED"}

        base_url = str(getattr(settings, "LOCAL_LLM_BASE_URL", "") or "").rstrip("/")
        api_key = str(getattr(settings, "LOCAL_LLM_API_KEY", "EMPTY") or "EMPTY")
        model_name = str(getattr(settings, "LOCAL_LLM_MODEL_NAME", "Qwen/Qwen3-14B-AWQ") or "Qwen/Qwen3-14B-AWQ")
        executed_now = 0

        for it in items:
            if it.fortisiem_incident_id in done_fids or not it.incident:
                continue
            inc = it.incident
            rule = inc.rule
            if not rule:
                rule = (
                    await db.execute(
                        select(Rule).where(or_(Rule.event_type == it.rule_id, Rule.rule_id == it.rule_id))
                    )
                ).scalars().first()
            if not rule:
                continue

            dyn_contract, _ = await RuleIntelligenceEngine.get_or_build_contract_for_rule(db, rule)
            legacy_contract = RuleIntelligenceEngine.to_legacy_evidence_contract(
                dyn_contract, force_approved_for_eval=True
            )
            norm_tmp, _, _ = UniversalPromptEngine.prepare_canonical_incident(
                incident=inc, rule=rule, fortisiem_incident_id=it.fortisiem_incident_id
            )
            org_ctx = (
                await OrganizationalContextService.resolve_relevant_context(
                    db,
                    customer=inc.customer or it.customer or "DEFAULT",
                    allowed_context_types=dyn_contract.approved_organizational_context_types,
                    observed_entities=UniversalPromptEngine.extract_observed_entities(norm_tmp, rule),
                )
                if mode_u == "MODE_B"
                else {"context_status": "DISABLED_IN_MODE_A", "matched_records": [], "authorizes_activity": False}
            )

            composed = await UniversalPromptEngine.compose_prompt(
                mode=mode_u,
                incident=inc,
                rule=rule,
                contract=dyn_contract,
                org_context=org_ctx,
                fortisiem_incident_id=it.fortisiem_incident_id,
                max_context_tokens=max_context_tokens,
                max_completion_tokens=max_completion_tokens,
                verify_remote_tokenize=(transport_override is None),
                timeout_seconds=timeout_seconds,
            )

            if composed["overflow_error"]:
                rec = IntelligenceExecutionRecord(
                    run_id=run_id,
                    run_key=actual_run_key,
                    cohort_key=cohort_key,
                    mode=mode_u,
                    fortisiem_incident_id=it.fortisiem_incident_id,
                    incident_db_id=inc.id,
                    rule_id=dyn_contract.fortisiem_rule_id,
                    archetype=dyn_contract.rule_archetype,
                    contract_id=dyn_contract.contract_id,
                    contract_hash=dyn_contract.contract_hash,
                    policy_hash=composed["policy_hash"],
                    wire_prompt_sha256=composed["wire_prompt_sha256"],
                    model_identifier=model_name,
                    gpu_provenance="TEST_TRANSPORT" if transport_override else "LIVE_SERVER2_VLLM",
                    execution_status="CONTEXT_OVERFLOW",
                    validator_status="CONTEXT_WINDOW_EXCEEDED",
                    validator_module="TokenBudgetGuard",
                    token_audit_json=composed["wire_token_audit"],
                    evidence_audit_json=composed["evidence_audit"],
                    org_context_json=org_ctx,
                    wire_system_prompt=composed["sys_prompt"],
                    wire_user_content=composed["user_content"],
                )
                db.add(rec)
                await db.commit()
                continue

            # Dispatch inference (+ at most 1 bounded repair attempt if malformed/truncated)
            attempts = 0
            retry_count = 0
            total_latency = 0.0
            total_p_tok = 0
            total_c_tok = 0
            raw_env: Dict[str, Any] = {}
            valid_ev_ids = {r.evidence_id for r in composed["norm_result"].records}
            struct_chk: Dict[str, Any] = {}

            for attempt in (1, 2):
                attempts = attempt
                sys_msg = composed["sys_prompt"]
                usr_msg = composed["user_content"]
                if attempt == 2:
                    retry_count = 1
                    usr_msg = (
                        f"{usr_msg}\n\n[REPAIR_INSTRUCTION: Previous response was truncated or invalid JSON "
                        f"({'; '.join(struct_chk.get('issues') or [])[:180]}). "
                        "Return ONE complete, compact valid JSON object matching the exact schema, citing valid EV-* IDs.]"
                    )
                if transport_override is not None:
                    raw_env = await transport_override(
                        system_instruction=sys_msg,
                        user_content=usr_msg,
                        model_name=model_name,
                        max_tokens=max_completion_tokens,
                        temperature=0.0,
                    )
                else:
                    raw_env = await AIS27BenchmarkRunner._dispatch_vllm(
                        system_instruction=sys_msg,
                        user_content=usr_msg,
                        model_name=model_name,
                        max_tokens=max_completion_tokens,
                        temperature=0.0,
                        timeout_seconds=timeout_seconds,
                        base_url=base_url,
                        api_key=api_key,
                        top_p=1.0,
                        enable_thinking=False,
                    )
                total_latency += float(raw_env.get("latency_ms") or 0.0)
                total_p_tok += int(raw_env.get("prompt_tokens") or 0)
                total_c_tok += int(raw_env.get("completion_tokens") or 0)
                if not raw_env.get("ok"):
                    break
                struct_chk = UniversalPromptEngine.validate_structured_output(
                    raw_response_text=str(raw_env.get("raw_response_text") or ""),
                    finish_reason=raw_env.get("finish_reason"),
                    valid_evidence_ids=valid_ev_ids,
                    mode=mode_u,
                )
                if struct_chk["schema_valid"] or not allow_repair_retry:
                    break

            if not raw_env.get("ok"):
                rec = IntelligenceExecutionRecord(
                    run_id=run_id,
                    run_key=actual_run_key,
                    cohort_key=cohort_key,
                    mode=mode_u,
                    fortisiem_incident_id=it.fortisiem_incident_id,
                    incident_db_id=inc.id,
                    rule_id=dyn_contract.fortisiem_rule_id,
                    archetype=dyn_contract.rule_archetype,
                    contract_id=dyn_contract.contract_id,
                    contract_hash=dyn_contract.contract_hash,
                    policy_hash=composed["policy_hash"],
                    wire_prompt_sha256=composed["wire_prompt_sha256"],
                    model_identifier=model_name,
                    gpu_provenance="TEST_TRANSPORT" if transport_override else "LIVE_SERVER2_VLLM",
                    execution_status="FAILED",
                    attempts=attempts,
                    retry_count=retry_count,
                    latency_ms=total_latency,
                    validator_status="PROVIDER_FAILURE",
                    validator_module="InferenceTransport",
                    token_audit_json=composed["wire_token_audit"],
                    evidence_audit_json=composed["evidence_audit"],
                    org_context_json=org_ctx,
                    validator_detail_json={"error": raw_env.get("error_message")},
                )
                db.add(rec)
                await db.commit()
                continue

            parsed_obj = struct_chk.get("parsed") or {}
            raw_verdict = struct_chk.get("norm_verdict") or "REQUIRES_ATTENTION"
            preflight = EvidencePreflightValidator.validate_preflight(
                incident_id=it.fortisiem_incident_id,
                contract=legacy_contract,
                normalization_result=composed["norm_result"],
                allow_simulation=True,
            )
            grounding = ModelClaimExtractor.extract_and_ground_claims(
                incident_id=it.fortisiem_incident_id,
                raw_verdict_output=parsed_obj,
                normalization_result=composed["norm_result"],
            )
            val_res = ModularVerdictValidator.validate(
                incident_id=it.fortisiem_incident_id,
                proposed_verdict=raw_verdict,
                raw_model_confidence=float(parsed_obj.get("confidence") or 0.0),
                preflight=preflight,
                claim_grounding=grounding,
                normalization_result=composed["norm_result"],
                legacy_contract=legacy_contract,
                dynamic_contract=dyn_contract,
                org_context=org_ctx,
                model_output=parsed_obj,
                structured_check=struct_chk,
                allow_provisional_contracts=True,
            )
            trust_res = VerdictTrustworthinessEngine.evaluate_verdict_trust(
                incident_payload=composed["budgeted_payload"],
                model_output=parsed_obj,
                contract=legacy_contract,
                archetype_id=dyn_contract.rule_archetype,
                historical_sample_count=0,
                is_calibrated=False,
            )
            reconciled = VerdictTrustworthinessEngine.reconcile_verdict_layers(
                raw_llm_verdict=raw_verdict,
                validated_verdict=val_res.final_verdict,
                validation_result=val_res,
                trust_result=trust_res,
                allow_advisory_uncalibrated=True,
            )

            executed_now += 1
            rec = IntelligenceExecutionRecord(
                run_id=run_id,
                run_key=actual_run_key,
                cohort_key=cohort_key,
                mode=mode_u,
                fortisiem_incident_id=it.fortisiem_incident_id,
                incident_db_id=inc.id,
                rule_id=dyn_contract.fortisiem_rule_id,
                archetype=dyn_contract.rule_archetype,
                contract_id=dyn_contract.contract_id,
                contract_hash=dyn_contract.contract_hash,
                policy_hash=composed["policy_hash"],
                wire_prompt_sha256=composed["wire_prompt_sha256"],
                model_identifier=model_name,
                actual_model_returned=raw_env.get("model_returned"),
                inference_request_id=raw_env.get("vllm_response_id"),
                gpu_provenance="TEST_TRANSPORT" if transport_override else "LIVE_SERVER2_VLLM",
                execution_status="COMPLETED",
                attempts=attempts,
                retry_count=retry_count,
                latency_ms=total_latency,
                prompt_tokens=total_p_tok,
                completion_tokens=total_c_tok,
                finish_reason=raw_env.get("finish_reason"),
                raw_llm_verdict=raw_verdict,
                validated_verdict=val_res.final_verdict,
                effective_operational_verdict=reconciled["effective_operational_verdict"],
                validator_status=val_res.validation_status,
                validator_module=val_res.validator_module or "",
                grounding_ratio=float(val_res.grounding_ratio),
                trust_score=trust_res.trust_score,
                semantic_dimensions_json=val_res.semantic_evaluation or {},
                token_audit_json=composed["wire_token_audit"],
                evidence_audit_json=composed["evidence_audit"],
                org_context_json=org_ctx,
                validator_detail_json={
                    "reason_codes": val_res.validation_reason_codes,
                    "failed_check": val_res.failed_check,
                    "failure_severity": val_res.failure_severity,
                    "failure_classification": val_res.failure_classification,
                    "evidence_reference": val_res.evidence_reference,
                    "directive": val_res.analyst_action_directive,
                    "trust_reconciliation": reconciled,
                },
                parsed_output_json=parsed_obj,
                wire_system_prompt=composed["sys_prompt"],
                wire_user_content=composed["user_content"],
                raw_response_text=str(raw_env.get("raw_response_text") or ""),
            )
            db.add(rec)
            await db.commit()

        return {
            "run_id": run_id,
            "run_key": actual_run_key,
            "cohort_key": cohort_key,
            "mode": mode_u,
            "executed_in_call": executed_now,
        }

    @classmethod
    def compute_full_metrics(
        cls,
        rows: List[Dict[str, Any]],
        verdict_key: str,
    ) -> Dict[str, Any]:
        """Computes all 30+ mandatory AIS 3.2 empirical metrics with explicit denominators."""
        total = len(rows)
        completed = [r for r in rows if r.get("execution_status") == "COMPLETED"]
        failed = total - len(completed)
        valid_struct = sum(
            1 for r in completed
            if r.get("validator_status") not in ("TRUNCATED_OUTPUT", "INVALID_MODEL_OUTPUT", "INVALID_SCHEMA")
        )

        # Confusion counts on binary GT vs 3-class GT
        tp = fp = tn = fn = abst = 0
        three_class_agree = 0
        inc_gt_n = 0
        inc_agree = 0

        for r in completed:
            gt = r.get("human_gt_verdict", "UNREVIEWED")
            pred = str(r.get(verdict_key) or "REQUIRES_ATTENTION").upper().strip()
            is_inc_pred = pred not in ("TRUE_POSITIVE", "FALSE_POSITIVE")

            if gt == "INCONCLUSIVE":
                inc_gt_n += 1
                if is_inc_pred:
                    inc_agree += 1
                    three_class_agree += 1
                continue
            if gt not in ("TRUE_POSITIVE", "FALSE_POSITIVE"):
                continue

            if is_inc_pred:
                abst += 1
            elif gt == "TRUE_POSITIVE" and pred == "TRUE_POSITIVE":
                tp += 1
                three_class_agree += 1
            elif gt == "FALSE_POSITIVE" and pred == "TRUE_POSITIVE":
                fp += 1
            elif gt == "FALSE_POSITIVE" and pred == "FALSE_POSITIVE":
                tn += 1
                three_class_agree += 1
            elif gt == "TRUE_POSITIVE" and pred == "FALSE_POSITIVE":
                fn += 1

        bin_gt_n = sum(1 for r in rows if r.get("human_gt_verdict") in ("TRUE_POSITIVE", "FALSE_POSITIVE"))
        all_gt_tp = sum(1 for r in rows if r.get("human_gt_verdict") == "TRUE_POSITIVE")
        all_gt_fp = sum(1 for r in rows if r.get("human_gt_verdict") == "FALSE_POSITIVE")
        conclusive = tp + fp + tn + fn
        correct_bin = tp + tn

        tp_precision = _pct(tp, tp + fp)
        # End-to-end TP recall across ALL human-labelled TPs (returns 0.0 when abstained on all TPs!)
        e2e_tp_recall = _pct(tp, all_gt_tp)
        e2e_fp_recall = _pct(tn, all_gt_fp)
        cond_tp_recall = _pct(tp, tp + fn)
        cond_fp_recall = _pct(tn, tn + fp)
        f1 = (
            round((2 * tp_precision * e2e_tp_recall) / (tp_precision + e2e_tp_recall), 2)
            if (tp_precision is not None and e2e_tp_recall is not None and (tp_precision + e2e_tp_recall) > 0)
            else 0.0 if all_gt_tp > 0 else None
        )
        e2e_bal_acc = (
            round((e2e_tp_recall + e2e_fp_recall) / 2.0, 2)
            if (e2e_tp_recall is not None and e2e_fp_recall is not None)
            else None
        )
        fnr_e2e = _pct(fn, all_gt_tp)
        tp_to_fp_rate = _pct(fn, all_gt_tp)

        latencies = [float(r.get("latency_ms") or 0.0) for r in completed if r.get("latency_ms") is not None]
        sorted_lat = sorted(latencies)
        p95 = round(sorted_lat[min(len(sorted_lat) - 1, int(0.95 * len(sorted_lat)))], 2) if sorted_lat else None
        grounding_vals = [float(r.get("grounding_ratio") or 0.0) for r in completed]
        retries = sum(int(r.get("retry_count") or 0) for r in completed)

        return {
            "total_eligible_incidents": total,
            "binary_gt_incidents": bin_gt_n,
            "human_tp_support": all_gt_tp,
            "human_fp_support": all_gt_fp,
            "human_inconclusive_support": inc_gt_n,
            "successful_inference_requests": len(completed),
            "valid_structured_outputs": valid_struct,
            "failed_inference_requests": failed,
            "tp": tp,
            "tn": tn,
            "fp": fp,
            "fn": fn,
            "abstentions": abst,
            "conclusive_decisions": conclusive,
            "decision_coverage_pct": _pct(conclusive, bin_gt_n),
            "conclusive_accuracy_pct": _pct(correct_bin, conclusive),
            "conclusive_accuracy_ci95": _wilson_pct(correct_bin, conclusive),
            "end_to_end_correct_binary_rate_pct": _pct(correct_bin, bin_gt_n),
            "end_to_end_correct_binary_ci95": _wilson_pct(correct_bin, bin_gt_n),
            "three_class_agreement_pct": _pct(three_class_agree, bin_gt_n + inc_gt_n),
            "tp_precision_pct": tp_precision,
            "tp_recall_all_tps_pct": e2e_tp_recall,
            "fp_recall_all_fps_pct": e2e_fp_recall,
            "conditional_tp_recall_pct": cond_tp_recall,
            "conditional_fp_recall_pct": cond_fp_recall,
            "f1_score_pct": f1,
            "balanced_accuracy_pct": e2e_bal_acc,
            "false_negative_rate_pct": fnr_e2e,
            "tp_to_fp_misclassification_rate_pct": tp_to_fp_rate,
            "inconclusive_agreement_pct": _pct(inc_agree, inc_gt_n),
            "claim_grounding_ratio_avg": round(statistics.mean(grounding_vals), 4) if grounding_vals else None,
            "validator_rejection_rate_pct": _pct(
                sum(1 for r in completed if r.get("raw_llm_verdict") in ("TRUE_POSITIVE", "FALSE_POSITIVE") and r.get("validated_verdict") not in ("TRUE_POSITIVE", "FALSE_POSITIVE")),
                len(completed),
            ),
            "mean_latency_ms": round(statistics.mean(latencies), 2) if latencies else None,
            "median_latency_ms": round(statistics.median(latencies), 2) if latencies else None,
            "p95_latency_ms": p95,
            "retry_rate_pct": _pct(retries, len(completed)),
            "total_prompt_tokens": sum(int(r.get("prompt_tokens") or 0) for r in completed),
            "total_completion_tokens": sum(int(r.get("completion_tokens") or 0) for r in completed),
        }

    @classmethod
    async def evaluate_run(cls, db: AsyncSession, *, run_key: str, mode: Optional[str] = None) -> Dict[str, Any]:
        """Evaluates an AIS 3.2 execution run against real cohort labels with baseline comparisons."""
        stmt = select(IntelligenceExecutionRecord).where(IntelligenceExecutionRecord.run_key == run_key)
        if mode:
            stmt = stmt.where(IntelligenceExecutionRecord.mode == mode.upper().strip())
        rows = (await db.execute(stmt)).scalars().all()
        if not rows:
            raise ValueError(f"No AIS 3.2 execution records found for run_key='{run_key}'.")

        cohort_key = rows[0].cohort_key
        cohort = (await db.execute(select(BenchmarkCohort).where(BenchmarkCohort.cohort_key == cohort_key))).scalar_one()
        c_items = (
            await db.execute(select(BenchmarkCohortItem).where(BenchmarkCohortItem.cohort_id == cohort.id))
        ).scalars().all()
        gt_by_fid = {it.fortisiem_incident_id: _normalize_gt_label(it.certified_verdict) for it in c_items}

        joined: List[Dict[str, Any]] = []
        for r in rows:
            joined.append({
                "fortisiem_incident_id": r.fortisiem_incident_id,
                "rule_id": r.rule_id,
                "archetype": r.archetype,
                "execution_status": r.execution_status,
                "human_gt_verdict": gt_by_fid.get(r.fortisiem_incident_id, "UNREVIEWED"),
                "raw_llm_verdict": r.raw_llm_verdict,
                "validated_verdict": r.validated_verdict,
                "effective_operational_verdict": r.effective_operational_verdict,
                "validator_status": r.validator_status,
                "validator_module": r.validator_module,
                "grounding_ratio": r.grounding_ratio,
                "latency_ms": r.latency_ms,
                "retry_count": r.retry_count,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "evidence_audit": r.evidence_audit_json,
                "validator_detail": r.validator_detail_json,
            })

        raw_m = cls.compute_full_metrics(joined, "raw_llm_verdict")
        val_m = cls.compute_full_metrics(joined, "validated_verdict")
        eff_m = cls.compute_full_metrics(joined, "effective_operational_verdict")

        bin_n = raw_m["binary_gt_incidents"]
        gt_tp = raw_m["human_tp_support"]
        gt_fp = raw_m["human_fp_support"]
        baselines = {
            "always_tp_end_to_end_pct": _pct(gt_tp, bin_n),
            "always_fp_end_to_end_pct": _pct(gt_fp, bin_n),
            "always_abstain_end_to_end_pct": 0.0 if bin_n > 0 else None,
        }

        by_arch: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        by_rule: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for j in joined:
            by_arch[j["archetype"]].append(j)
            by_rule[j["rule_id"]].append(j)

        return {
            "run_key": run_key,
            "cohort_key": cohort_key,
            "mode": rows[0].mode,
            "raw_llm_metrics": raw_m,
            "validated_app_metrics": val_m,
            "effective_operational_metrics": eff_m,
            "baselines": baselines,
            "by_archetype": {k: cls.compute_full_metrics(v, "validated_verdict") for k, v in sorted(by_arch.items())},
            "by_rule": {k: cls.compute_full_metrics(v, "validated_verdict") for k, v in sorted(by_rule.items())},
            "incident_results": joined,
        }

    @classmethod
    def compute_ais33_holdout_plan(
        cls,
        *,
        target_accuracy: float = 0.90,
        min_tp_recall: float = 0.95,
        desired_ci_half_width: float = 0.04,
        expected_tp_prevalence: float = 0.25,
    ) -> Dict[str, Any]:
        """
        Statistically derives the required AIS 3.3 untouched holdout cohort size
        and class representation (not assuming N=100 is automatically sufficient).
        """
        z = 1.96
        # Minimum total N for overall accuracy CI half-width <= desired_ci_half_width
        n_overall = math.ceil((z ** 2 * target_accuracy * (1.0 - target_accuracy)) / (desired_ci_half_width ** 2))
        # Minimum TP count for Wilson CI lower bound >= 0.85 when observed recall >= 0.95 (approx >= 60 TPs)
        n_tp_min = 60
        n_for_tp = math.ceil(n_tp_min / max(0.05, expected_tp_prevalence))
        recommended_total = max(200, n_overall, n_for_tp)

        return {
            "cohort_key": AIS_3_3_FUTURE_COHORT_ID,
            "status": "ISOLATION_PLAN_PREPARED_NOT_EVALUATED",
            "recommended_minimum_total": recommended_total,
            "recommended_min_tp_incidents": n_tp_min,
            "recommended_min_fp_incidents": recommended_total - n_tp_min,
            "n_overall_for_ci_halfwidth": n_overall,
            "statistical_rationale": (
                f"N=100 at ~18% TP prevalence yields only 18 TPs (95% Wilson CI width >20% on recall). "
                f"To bound TP recall >=95% and overall accuracy >=90% within +/-{desired_ci_half_width*100:.1f}% "
                f"with dual-reviewer GT-3 certification, >= {recommended_total} untouched incidents "
                f"(including >= {n_tp_min} TPs across all 11 archetypes) is required."
            ),
            "contamination_guards": [
                f"Exclude all {FROZEN_AIS_2_6E_COHORT_ID} IDs & raw evidence hashes",
                f"Exclude all {AIS_3_0_HOLDOUT_COHORT_ID} IDs & raw evidence hashes",
                f"Exclude all {AIS_3_2_DEVELOPMENT_COHORT_ID} IDs & raw evidence hashes",
                "Exclude all LearningRecord & PromptCapture-exposed incidents",
                "Require dual independent blind human review (GT-3) before evaluation",
                "Freeze AIS 3.2 candidate policy & validator versions prior to AIS 3.3 execution",
            ],
        }
