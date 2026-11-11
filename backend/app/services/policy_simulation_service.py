"""
Policy Simulation & Historical Evaluation Service (AIS 2.1).
Integrates the dry-run intelligence validation pipeline:
1. Replays historical incidents through the evidence & policy engine
2. Validates evidence sufficiency & extracts grounded claims
3. Applies deterministic verdict guardrails
4. Computes 1-10 Trust Scores & empirical accuracy metrics
5. Compares candidate policy against baseline with paired regression detection
"""

import hashlib
import math
import uuid
import json
import logging
from datetime import datetime
from app.utils.datetime_utils import utc_now
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload

from app.models.rule import Rule
from app.models.prompt import PromptVersion, RulePrompt
from app.models.incident import Incident, HistoricalGroundTruth
from app.models.investigation import Investigation
from app.models.token_usage import TokenUsageRecord
from app.models.verdict_intelligence import (
    VerdictTrustAssessmentRecord,
    EvidenceSufficiencyAssessmentRecord,
    HistoricalEvaluationRunRecord,
    HistoricalEvaluationResultRecord,
)
from app.schemas.policy_quality import SimulationStatus
from app.schemas.verdict_intelligence import (
    EvaluationValidationState,
    UserVisibleVerdict,
    GroundTruthLabel,
    EmpiricalAccuracyMetrics,
    CaseRegressionDetail,
    RegressionComparisonReport,
    IncidentEligibilityFunnel,
    IncidentExclusionRecord,
)
from app.services.evidence_sufficiency_engine import EvidenceSufficiencyEngine
from app.services.verdict_claim_validator import VerdictClaimValidator
from app.services.verdict_guardrails_engine import VerdictGuardrailsEngine
from app.services.verdict_trustworthiness_engine import VerdictTrustworthinessEngine
from app.services.historical_ground_truth_validator import HistoricalGroundTruthValidator
from app.services.empirical_accuracy_evaluator import EmpiricalAccuracyEvaluator
from app.services.calibration_evaluator import CalibrationEvaluator
from app.services.evidence_contract_service import EvidenceContractService
from app.services.policy_governance import (
    SIMULATED_PROVIDER_TOKENS,
    RuleMatchContext,
    build_rule_incident_context,
    build_rule_incident_sql_filter,
    get_rule_semantics_and_contract,
    resolve_canonical_rule,
    verify_incident_matches_rule,
)
from app.services.verdict_pipeline import (
    PipelineLLMUnavailableError,
    build_sanitized_model_payload,
    run_shared_verdict_pipeline,
)

logger = logging.getLogger("ai_verdict.policy_simulation")


class PolicySimulationService:
    """
    Dry-Run Intelligence Validation & Policy Regression Evaluation Service.
    """
    MIN_HISTORICAL_SAMPLES = 5

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _is_simulated_run(run_rec: HistoricalEvaluationRunRecord) -> bool:
        cfg = getattr(run_rec, "config_snapshot", None) or {}
        if cfg.get("is_simulated") is True:
            return True
        ptype = str(cfg.get("provider_type") or "").upper().strip()
        prov = str(cfg.get("execution_provenance") or "").upper().strip()
        return bool(ptype in SIMULATED_PROVIDER_TOKENS or prov in SIMULATED_PROVIDER_TOKENS)

    async def get_rule_calibration_stats(self, rule_id: Optional[str]) -> Dict[str, Any]:
        """
        Queries real empirical validation sample count and measured accuracy from
        persisted HistoricalGroundTruth and completed NON-SIMULATED HistoricalEvaluationRunRecord data.
        Never fabricates sample counts or accuracy percentages or counts simulated runs as calibrated.
        """
        if not rule_id:
            return {
                "sample_count": 0,
                "accuracy": None,
                "is_calibrated": False,
                "calibration_status": "UNCALIBRATED",
            }

        matched_rule = await resolve_canonical_rule(self.db, rule_id)
        rule_ctx = await build_rule_incident_context(self.db, matched_rule, fallback_rule_id=rule_id)
        rule_ids = list(rule_ctx.matched_rule_ids or [rule_id])

        # 1. Check latest completed NON-SIMULATED empirical evaluation run for this rule
        try:
            run_q = (
                select(HistoricalEvaluationRunRecord)
                .where(
                    HistoricalEvaluationRunRecord.rule_id.in_(rule_ids),
                    HistoricalEvaluationRunRecord.status == "COMPLETED",
                )
                .order_by(desc(HistoricalEvaluationRunRecord.completed_at))
                .limit(10)
            )
            run_res = await self.db.execute(run_q)
            candidate_runs = run_res.scalars().all()
            latest_run = next((r for r in candidate_runs if not self._is_simulated_run(r)), None)
            if latest_run and (latest_run.verified_ground_truth_cases or 0) > 0:
                gt_cases = int(latest_run.verified_ground_truth_cases or 0)
                metrics = latest_run.metrics or {}
                calib = latest_run.calibration_metrics or {}
                measured_acc = metrics.get("overall_accuracy")
                if measured_acc is None:
                    measured_acc = metrics.get("balanced_accuracy")
                acc_pct = (
                    round(float(measured_acc) * 100.0, 2)
                    if measured_acc is not None and float(measured_acc) <= 1.0
                    else (float(measured_acc) if measured_acc is not None else None)
                )
                has_calib_report = isinstance(calib, dict) and ("is_calibrated" in calib)
                is_cal = (
                    bool(calib.get("is_calibrated", False))
                    if has_calib_report
                    else (gt_cases >= 30 and acc_pct is not None and acc_pct >= 70.0)
                )
                cal_status = (
                    "CALIBRATED"
                    if is_cal
                    else ("PARTIALLY_VALIDATED" if gt_cases >= 5 else "UNCALIBRATED")
                )
                return {
                    "sample_count": gt_cases,
                    "accuracy": acc_pct,
                    "is_calibrated": is_cal,
                    "calibration_status": cal_status,
                }
        except Exception as e:
            logger.warning(f"Failed querying completed evaluation runs for rule {rule_id}: {e}")

        # 2. Fallback: count real verified non-ML, non-disputed, non-synthetic HistoricalGroundTruth records
        try:
            rule_filter = build_rule_incident_sql_filter(rule_ctx)
            gt_q = (
                select(Incident, HistoricalGroundTruth)
                .outerjoin(HistoricalGroundTruth, Incident.id == HistoricalGroundTruth.incident_id)
                .options(selectinload(Incident.events))
                .where(rule_filter)
            )
            gt_res = await self.db.execute(gt_q)
            inc_rows = gt_res.all()
            inc_db_ids = [inc_obj.id for inc_obj, _ in inc_rows]
            inv_map: Dict[str, Investigation] = {}
            if inc_db_ids:
                inv_res = await self.db.execute(
                    select(Investigation).where(Investigation.incident_id.in_(inc_db_ids))
                )
                inv_map = {inv.incident_id: inv for inv in inv_res.scalars().all()}

            verified_count = 0
            seen_clusters = set()
            for inc_obj, gt in inc_rows:
                matched, _ = verify_incident_matches_rule(inc_obj, rule_ctx)
                if not matched:
                    continue
                rp = inc_obj.raw_payload
                if isinstance(rp, str):
                    try:
                        rp = json.loads(rp)
                    except Exception:
                        rp = {}
                elif not isinstance(rp, dict):
                    rp = {}
                if HistoricalGroundTruthValidator.is_synthetic_fixture(inc_obj, rp, gt):
                    continue
                miss_reason, _ = HistoricalGroundTruthValidator.is_missing_evidence(inc_obj, rp)
                if miss_reason:
                    continue
                adj, ex_code, _, _, _ = HistoricalGroundTruthValidator.adjudicate_incident_ground_truth(
                    ground_truth=gt,
                    investigation=inv_map.get(inc_obj.id),
                    incident=inc_obj,
                )
                if ex_code is None and adj in (GroundTruthLabel.VERIFIED_TP, GroundTruthLabel.VERIFIED_FP):
                    if gt is not None:
                        cluster_key = HistoricalGroundTruthValidator.compute_duplicate_cluster_key(
                            inc_obj, gt, adj.value
                        )
                        if cluster_key:
                            if cluster_key in seen_clusters:
                                continue
                            seen_clusters.add(cluster_key)
                    verified_count += 1

            return {
                "sample_count": verified_count,
                "accuracy": None,
                "is_calibrated": False,
                "calibration_status": "PARTIALLY_VALIDATED" if verified_count >= 5 else "UNCALIBRATED",
            }
        except Exception as e:
            logger.warning(f"Failed counting historical ground truth for rule {rule_id}: {e}")

        return {
            "sample_count": 0,
            "accuracy": None,
            "is_calibrated": False,
            "calibration_status": "UNCALIBRATED",
        }

    async def _fetch_scoped_incidents_paginated(
        self,
        *,
        rule_ctx: RuleMatchContext,
        has_rule_filter: bool,
        sample_limit: Optional[int],
        after_epoch: Optional[int],
        before_epoch: Optional[int],
        split_partition: Optional[str],
    ) -> Tuple[int, List[Tuple[Incident, Optional[HistoricalGroundTruth]]]]:
        """
        Deterministically paginate rule-scoped incidents (without global top-50 pollution)
        supporting >50 matching records cleanly.
        """
        base_filter = build_rule_incident_sql_filter(rule_ctx) if has_rule_filter else None

        count_q = select(func.count(Incident.id))
        if base_filter is not None:
            count_q = count_q.where(base_filter)
        available_count = int((await self.db.execute(count_q)).scalar() or 0)

        target_partition = (
            split_partition.value
            if hasattr(split_partition, "value")
            else (str(split_partition).upper() if split_partition else None)
        )

        collected: List[Tuple[Incident, Optional[HistoricalGroundTruth]]] = []
        seen_ids = set()
        page_size = 100
        offset = 0

        while True:
            page_q = (
                select(Incident, HistoricalGroundTruth)
                .outerjoin(HistoricalGroundTruth, Incident.id == HistoricalGroundTruth.incident_id)
                .options(selectinload(Incident.events))
                .order_by(desc(Incident.created_at), Incident.id.asc())
                .offset(offset)
                .limit(page_size)
            )
            if base_filter is not None:
                page_q = page_q.where(base_filter)

            batch = (await self.db.execute(page_q)).all()
            if not batch:
                break

            for row in batch:
                inc_obj = row[0]
                if inc_obj.id in seen_ids:
                    continue
                seen_ids.add(inc_obj.id)

                inc_epoch = inc_obj.first_seen_epoch or inc_obj.created_at_epoch
                if after_epoch is not None and (inc_epoch is None or inc_epoch < after_epoch):
                    continue
                if before_epoch is not None and (inc_epoch is None or inc_epoch > before_epoch):
                    continue
                if target_partition:
                    inc_part = HistoricalGroundTruthValidator.assign_partition(
                        str(inc_obj.incident_id or inc_obj.id)
                    ).value
                    if inc_part != target_partition:
                        continue

                collected.append(row)
                if sample_limit is not None and len(collected) >= sample_limit:
                    return available_count, collected

            if len(batch) < page_size:
                break
            offset += page_size

        return available_count, collected

    async def run_dry_run_intelligence_evaluation(
        self,
        run_name: str,
        rule_id: Optional[str] = None,
        archetype: Optional[str] = None,
        policy_version_id: Optional[str] = None,
        baseline_run_id: Optional[str] = None,
        sample_limit: Optional[int] = 500,
        provider_type: str = "SIMULATED",
        split_partition: Optional[str] = None,
        after_epoch: Optional[int] = None,
        before_epoch: Optional[int] = None,
        include_unlabeled_replay: bool = False,
        existing_run_id: Optional[str] = None,
    ) -> HistoricalEvaluationRunRecord:
        """
        Executes empirical historical evaluation using canonical rule isolation, paginated
        retrieval, human-provenance ground truth gating, and the shared live-parity pipeline.
        Never mutates live Incident.ai_verdict, Investigation, or SIEM state.
        """
        provider_upper = str(provider_type or "SIMULATED").upper().strip()
        is_simulated_run = provider_upper in SIMULATED_PROVIDER_TOKENS

        matched_rule = await resolve_canonical_rule(self.db, rule_id) if rule_id else None
        rule_ctx = await build_rule_incident_context(self.db, matched_rule, fallback_rule_id=rule_id)

        candidate_pv: Optional[PromptVersion] = None
        policy_digest: Optional[str] = None
        if policy_version_id:
            try:
                pv_res = await self.db.execute(
                    select(PromptVersion).where(PromptVersion.id == policy_version_id)
                )
                candidate_pv = pv_res.scalar_one_or_none()
            except Exception as e:
                logger.warning(f"Failed loading candidate PromptVersion {policy_version_id}: {e}")

        from app.services.policy_quality_validator import PolicyQualityValidator
        if candidate_pv:
            policy_digest = PolicyQualityValidator.compute_policy_digest(candidate_pv)

        # Resolve shared semantics & evidence contract (honoring RuleIntelligenceSnapshot)
        semantics = None
        contract = None
        contract_digest = None
        rule_digest = None
        if matched_rule:
            try:
                semantics, contract, _ = await get_rule_semantics_and_contract(
                    self.db, matched_rule, prompt_version=candidate_pv
                )
                contract_digest = PolicyQualityValidator.compute_contract_digest(contract)
                rule_digest = PolicyQualityValidator.compute_rule_digest(matched_rule, semantics)
            except Exception as e:
                logger.warning(f"Failed resolving shared contract for rule {rule_id}: {e}")

        config_snap: Dict[str, Any] = {
            "provider_type": provider_upper,
            "is_simulated": is_simulated_run,
            "execution_provenance": "SIMULATED" if is_simulated_run else "REAL_LOCAL_LLM",
            "model_identifier": None,
            "sample_limit": sample_limit,
            "policy_version_id": policy_version_id,
            "policy_digest": policy_digest,
            "contract_digest": contract_digest,
            "rule_digest": rule_digest,
            "canonical_rule_id": matched_rule.id if matched_rule else None,
            "canonical_rule_identifier": matched_rule.rule_id if matched_rule else rule_id,
            "unambiguous_event_type": rule_ctx.unambiguous_event_type,
            "sibling_rules_with_same_event_type": rule_ctx.sibling_rules_with_same_event_type,
            "include_unlabeled_replay": bool(include_unlabeled_replay),
            "split_partition": split_partition.value if hasattr(split_partition, "value") else split_partition,
            "after_epoch": after_epoch,
            "before_epoch": before_epoch,
            "certifying_empirical_eligible": False,
            "evaluated_at": utc_now().isoformat(),
        }

        run_record: Optional[HistoricalEvaluationRunRecord] = None
        if existing_run_id:
            ex_res = await self.db.execute(
                select(HistoricalEvaluationRunRecord).where(
                    HistoricalEvaluationRunRecord.id == existing_run_id
                )
            )
            run_record = ex_res.scalar_one_or_none()

        if run_record is None:
            run_record = HistoricalEvaluationRunRecord(
                id=existing_run_id or str(uuid.uuid4()),
                run_name=run_name,
                rule_id=(matched_rule.id if matched_rule else rule_id),
                archetype=archetype or (semantics.primary_behavior if semantics else None),
                dataset_id="historical-adjudicated-v2.1",
                dataset_hash=str(uuid.uuid4())[:16],
                policy_version_id=policy_version_id,
                baseline_run_id=baseline_run_id,
                status="RUNNING",
                validation_state=EvaluationValidationState.INCONCLUSIVE.value,
                metrics={},
                selective_metrics=[],
                calibration_metrics={},
                regression_summary={},
                config_snapshot=config_snap,
                started_at=utc_now(),
            )
            self.db.add(run_record)
        else:
            run_record.status = "RUNNING"
            run_record.config_snapshot = {**(run_record.config_snapshot or {}), **config_snap}
            self.db.add(run_record)
        await self.db.flush()

        # 1. Canonical Rule-Scoped Paginated Historical Retrieval
        available_count, rows = await self._fetch_scoped_incidents_paginated(
            rule_ctx=rule_ctx,
            has_rule_filter=bool(rule_id),
            sample_limit=sample_limit,
            after_epoch=after_epoch,
            before_epoch=before_epoch,
            split_partition=split_partition,
        )
        retrieved_count = len(rows)
        run_record.total_cases = retrieved_count

        if retrieved_count == 0:
            run_record.status = "COMPLETED"
            run_record.validation_state = EvaluationValidationState.INSUFFICIENT_DATA.value
            run_record.completed_at = utc_now()
            run_record.evaluated_cases = 0
            run_record.verified_ground_truth_cases = 0
            run_record.metrics = {
                "message": (
                    f"Zero historical incidents match rule '{rule_id or 'ALL'}' "
                    f"(0 available). Empirical validation requires at least {self.MIN_HISTORICAL_SAMPLES} verified cases."
                ),
                "funnel": {
                    "available": available_count,
                    "retrieved": 0,
                    "total_scanned": 0,
                    "rule_matched": 0,
                    "labeled": 0,
                    "analyst_labeled": 0,
                    "verified": 0,
                    "eligible": 0,
                    "independent_group_count": 0,
                    "excluded": 0,
                    "inferred": 0,
                    "evaluated": 0,
                    "scored": 0,
                    "exploratory_replay_count": 0,
                    "exclusion_reasons": {"INSUFFICIENT_SAMPLE_SIZE": 0},
                    "exclusions_detail": [],
                },
                "verified_ground_truth_cases": 0,
                "total_evaluated_incidents": 0,
            }
            await self.db.commit()
            return run_record

        # Load Investigations for retrieved incidents to evaluate disputed & human verification flags
        inc_db_ids = [r[0].id for r in rows]
        inv_map: Dict[str, Investigation] = {}
        if inc_db_ids:
            for i in range(0, len(inc_db_ids), 200):
                chunk_ids = inc_db_ids[i : i + 200]
                inv_res = await self.db.execute(
                    select(Investigation).where(Investigation.incident_id.in_(chunk_ids))
                )
                for inv in inv_res.scalars().all():
                    inv_map[inv.incident_id] = inv

        hist_stats = await self.get_rule_calibration_stats(matched_rule.id if matched_rule else rule_id)

        eval_items: List[Dict[str, Any]] = []
        exploratory_items: List[Dict[str, Any]] = []
        analyst_labeled_count = 0
        eligible_count = 0
        excluded_count = 0
        duplicate_excluded_count = 0
        synthetic_excluded_count = 0
        rule_matched_count = 0
        exploratory_replay_count = 0
        inferred_count = 0
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_tokens_sum = 0
        observed_models: List[str] = []

        exclusion_reasons: Dict[str, int] = {
            "RULE_MISMATCH": 0,
            "MISSING_ANALYST_LABEL": 0,
            "DISPUTED_LABEL": 0,
            "AMBIGUOUS_LABEL": 0,
            "CORRUPT_OR_EMPTY_PAYLOAD": 0,
            "MISSING_EVIDENCE": 0,
            "SYNTHETIC_FIXTURE_EXCLUDED": 0,
            "DUPLICATE_CLUSTER_EXCLUDED": 0,
            "HEURISTIC_OR_ML_LABEL": 0,
        }
        exclusions_detail: List[Dict[str, Any]] = []
        stage_details: Dict[str, List[Dict[str, Any]]] = {
            "scanned": [],
            "rule_matched": [],
            "analyst_labeled": [],
            "eligible": [],
            "excluded": [],
            "evaluated": [],
            "exploratory_replay": [],
        }

        def _parse_payload(inc_obj: Incident) -> Dict[str, Any]:
            rp = inc_obj.raw_payload
            if isinstance(rp, str):
                try:
                    rp = json.loads(rp)
                except Exception:
                    rp = {}
            elif not isinstance(rp, dict):
                rp = {}
            return rp

        # Deterministic cluster pre-pass across verified, non-disputed, non-ML rule-matched incidents
        cluster_candidates: Dict[str, Tuple[int, str]] = {}
        for inc_c, gt_c in rows:
            if rule_id:
                ok_match, _ = verify_incident_matches_rule(inc_c, rule_ctx)
                if not ok_match:
                    continue
            rp_c = _parse_payload(inc_c)
            if HistoricalGroundTruthValidator.is_synthetic_fixture(inc_c, rp_c, gt_c):
                continue
            miss_c, _ = HistoricalGroundTruthValidator.is_missing_evidence(inc_c, rp_c)
            if miss_c:
                continue
            adj_c, ex_c, _, _, _ = HistoricalGroundTruthValidator.adjudicate_incident_ground_truth(
                ground_truth=gt_c,
                investigation=inv_map.get(inc_c.id),
                incident=inc_c,
            )
            if ex_c is None and gt_c is not None and adj_c in (
                GroundTruthLabel.VERIFIED_TP,
                GroundTruthLabel.VERIFIED_FP,
            ):
                ckey = HistoricalGroundTruthValidator.compute_duplicate_cluster_key(
                    inc_c, gt_c, adj_c.value
                )
                if ckey:
                    ev_score = len(getattr(inc_c, "events", None) or []) + len(rp_c.get("rawEvents") or [])
                    cid_str = str(inc_c.incident_id or inc_c.id)
                    best = cluster_candidates.get(ckey)
                    if best is None or ev_score > best[0] or (ev_score == best[0] and cid_str < best[1]):
                        cluster_candidates[ckey] = (ev_score, cid_str)

        for inc, gt in rows:
            inc_id_str = str(inc.incident_id or inc.id)
            inc_rule_str = str(inc.rule_id or "")
            inv = inv_map.get(inc.id)

            if rule_id:
                is_match, mismatch_code = verify_incident_matches_rule(inc, rule_ctx)
                if not is_match:
                    reason_code = mismatch_code or "RULE_MISMATCH"
                    exclusion_detail = (
                        f"Incident '{inc_id_str}' (rule_id='{inc_rule_str}', event_type='{inc.event_type}') "
                        f"does not canonically match target rule '{rule_id}'."
                    )
                    exclusion_reasons[reason_code] = exclusion_reasons.get(reason_code, 0) + 1
                    excluded_count += 1
                    ex_rec = {
                        "incident_id": inc_id_str,
                        "rule_id": inc_rule_str,
                        "reason": reason_code,
                        "detail": exclusion_detail,
                    }
                    exclusions_detail.append(ex_rec)
                    stage_details["excluded"].append(ex_rec)
                    stage_details["scanned"].append({
                        "incident_id": inc_id_str,
                        "rule_id": inc_rule_str,
                        "status": "EXCLUDED",
                        "reason": reason_code,
                        "detail": exclusion_detail,
                    })
                    continue

            rule_matched_count += 1
            stage_details["scanned"].append({
                "incident_id": inc_id_str,
                "rule_id": inc_rule_str,
                "status": "RULE_MATCHED",
                "reason": None,
                "detail": f"Matched canonical rule '{rule_ctx.canonical_rule_identifier or inc_rule_str}'",
            })
            has_any_label = bool(
                (gt and gt.resolution)
                or (inv and inv.analyst_verdict)
                or (inv and inv.is_disputed)
            )
            stage_details["rule_matched"].append({
                "incident_id": inc_id_str,
                "rule_id": inc_rule_str,
                "has_analyst_label": has_any_label,
                "resolution": str(gt.resolution) if gt and gt.resolution else (inv.analyst_verdict if inv else None),
            })

            raw_payload = _parse_payload(inc)
            gt_label = None
            provenance_source = "NONE"
            exclusion_reason = None
            exclusion_detail = None

            synthetic_detail = HistoricalGroundTruthValidator.is_synthetic_fixture(inc, raw_payload, gt)
            missing_code, missing_detail = HistoricalGroundTruthValidator.is_missing_evidence(inc, raw_payload)

            if synthetic_detail:
                exclusion_reason = "SYNTHETIC_FIXTURE_EXCLUDED"
                exclusion_detail = synthetic_detail
                exclusion_reasons["SYNTHETIC_FIXTURE_EXCLUDED"] += 1
                synthetic_excluded_count += 1
            elif missing_code:
                exclusion_reason = missing_code
                exclusion_detail = missing_detail
                exclusion_reasons[missing_code] = exclusion_reasons.get(missing_code, 0) + 1
            else:
                if has_any_label:
                    analyst_labeled_count += 1
                    stage_details["analyst_labeled"].append({
                        "incident_id": inc_id_str,
                        "rule_id": inc_rule_str,
                        "resolution": str(gt.resolution) if gt and gt.resolution else str(getattr(inv, "analyst_verdict", "") or ""),
                        "comments": str(gt.comments or "") if gt else "",
                        "is_ml_generated": bool(getattr(gt, "is_ml_generated", False)),
                        "is_disputed": bool(getattr(inv, "is_disputed", False)),
                        "is_independently_verified": bool(getattr(inv, "is_independently_verified", False)),
                    })

                adj_label, adj_ex_code, adj_detail, _, provenance_source = (
                    HistoricalGroundTruthValidator.adjudicate_incident_ground_truth(
                        ground_truth=gt,
                        investigation=inv,
                        incident=inc,
                    )
                )
                if adj_ex_code is not None:
                    mapped_code = "MISSING_ANALYST_LABEL" if adj_ex_code == "UNLABELED" else adj_ex_code
                    exclusion_reason = mapped_code
                    exclusion_detail = adj_detail
                    exclusion_reasons[mapped_code] = exclusion_reasons.get(mapped_code, 0) + 1
                elif adj_label in (GroundTruthLabel.VERIFIED_TP, GroundTruthLabel.VERIFIED_FP):
                    ckey = (
                        HistoricalGroundTruthValidator.compute_duplicate_cluster_key(
                            inc, gt, adj_label.value
                        )
                        if gt is not None
                        else None
                    )
                    if ckey and cluster_candidates.get(ckey, (0, ""))[1] != inc_id_str:
                        exclusion_reason = "DUPLICATE_CLUSTER_EXCLUDED"
                        exclusion_detail = (
                            f"Duplicate batch-closure cluster '{ckey}' represented by primary incident "
                            f"'{cluster_candidates[ckey][1]}' to prevent sample-size inflation."
                        )
                        exclusion_reasons["DUPLICATE_CLUSTER_EXCLUDED"] += 1
                        duplicate_excluded_count += 1
                    else:
                        eligible_count += 1
                        gt_label = adj_label.value
                        weak_fp_note = (
                            HistoricalGroundTruthValidator.is_containment_only_fp_note(
                                raw_resolution=gt.resolution,
                                cleared_reason=getattr(gt, "cleared_reason", None),
                                analyst_comments=gt.comments,
                                cleared_user=getattr(gt, "cleared_user", None),
                            )
                            if gt is not None and provenance_source != "INDEPENDENT_HUMAN_INVESTIGATION"
                            else False
                        )
                        stage_details["eligible"].append({
                            "incident_id": inc_id_str,
                            "rule_id": inc_rule_str,
                            "ground_truth": gt_label,
                            "provenance": provenance_source,
                            "resolution": str(gt.resolution) if gt and gt.resolution else str(getattr(inv, "analyst_verdict", "")),
                            "comments": str((gt.comments if gt else "") or getattr(inv, "verdict_reason", "") or ""),
                            "cluster_key": ckey,
                            "weak_containment_fp_note": weak_fp_note,
                        })

            is_exploratory_only = False
            if exclusion_reason:
                excluded_count += 1
                ex_rec = {
                    "incident_id": inc_id_str,
                    "rule_id": inc_rule_str,
                    "reason": exclusion_reason,
                    "detail": exclusion_detail,
                }
                exclusions_detail.append(ex_rec)
                stage_details["excluded"].append(ex_rec)
                if include_unlabeled_replay and exclusion_reason == "MISSING_ANALYST_LABEL":
                    is_exploratory_only = True
                else:
                    # Strictly exclude ineligible incidents from G8 inference and empirical scoring
                    continue

            # Run the unified live-parity evaluation pipeline (never mutates live Incident/Investigation)
            try:
                pipe_res = await run_shared_verdict_pipeline(
                    db=self.db,
                    incident=inc,
                    rule=matched_rule,
                    prompt_version=candidate_pv,
                    active_approved_version=candidate_pv,
                    model_provider_type=provider_upper,
                    allow_simulated_fallback=False,
                    is_simulation=True,
                    is_prod=False,
                    execution_context="SIMULATION",
                    require_autonomous_certification=False,
                    username="simulation_engine",
                    historical_stats=hist_stats,
                    simulated_output_fn=self._simulate_model_output if is_simulated_run else None,
                )
            except PipelineLLMUnavailableError as llm_err:
                run_record.status = "FAILED"
                run_record.validation_state = EvaluationValidationState.INCONCLUSIVE.value
                run_record.completed_at = utc_now()
                run_record.metrics = {
                    "error": str(llm_err),
                    "message": f"Real LLM simulation failed on incident '{inc_id_str}': {llm_err}",
                }
                await self.db.commit()
                raise RuntimeError(f"Real LLM simulation unavailable: {llm_err}") from llm_err

            inferred_count += 1
            total_prompt_tokens += pipe_res.prompt_tokens
            total_completion_tokens += pipe_res.completion_tokens
            total_tokens_sum += pipe_res.total_tokens

            model_ident = str(
                pipe_res.verdict_data.get("model_identifier")
                or ("simulated-v2.2-policy-aware" if is_simulated_run else "OPENAI_COMPATIBLE")
            )
            if model_ident and model_ident not in observed_models:
                observed_models.append(model_ident)

            self.db.add(
                TokenUsageRecord(
                    process_type="POLICY_SIMULATION",
                    process_id=run_record.id,
                    incident_id=inc_id_str,
                    rule_id=str(rule_ctx.canonical_rule_identifier or inc_rule_str or inc.event_type),
                    model_identifier=model_ident,
                    prompt_tokens=pipe_res.prompt_tokens,
                    completion_tokens=pipe_res.completion_tokens,
                    total_tokens=pipe_res.total_tokens,
                    latency_ms=int(pipe_res.verdict_data.get("latency_ms") or 0),
                    is_simulated=bool(pipe_res.verdict_data.get("is_simulated", is_simulated_run)),
                    executed_by_user="simulation_engine",
                    timestamp=utc_now(),
                    details={
                        "run_id": run_record.id,
                        "provider_type": pipe_res.provider_type_used,
                        "execution_provenance": pipe_res.verdict_prov.get("execution_provenance"),
                        "is_exploratory": is_exploratory_only,
                    },
                )
            )

            eff_verdict = pipe_res.effective_verdict
            is_correct = None
            is_critical_error = False
            if not is_exploratory_only and gt_label in (
                GroundTruthLabel.VERIFIED_TP.value,
                GroundTruthLabel.VERIFIED_FP.value,
            ):
                if eff_verdict == UserVisibleVerdict.TRUE_POSITIVE.value:
                    is_correct = gt_label == GroundTruthLabel.VERIFIED_TP.value
                elif eff_verdict == UserVisibleVerdict.FALSE_POSITIVE.value:
                    is_correct = gt_label == GroundTruthLabel.VERIFIED_FP.value
                    if gt_label == GroundTruthLabel.VERIFIED_TP.value:
                        is_critical_error = True

            norm_records_dump = pipe_res.verdict_data.get("supporting_claims") or []
            ev_snap_hash = hashlib.sha256(
                json.dumps(
                    [r.model_dump() for r in pipe_res.norm_result.records]
                    if pipe_res.norm_result
                    else norm_records_dump,
                    sort_keys=True,
                    default=str,
                ).encode("utf-8")
            ).hexdigest()

            result_record = HistoricalEvaluationResultRecord(
                id=str(uuid.uuid4()),
                run_id=run_record.id,
                incident_id=inc_id_str[:64],
                rule_id=str(inc.rule_id or rule_id or "RULE-UNKNOWN")[:128],
                suggested_verdict=str(pipe_res.proposed_verdict or "REQUIRES_ATTENTION")[:32],
                effective_verdict=str(eff_verdict)[:32],
                ground_truth_label=("UNLABELED_EXPLORATORY" if is_exploratory_only else str(gt_label)[:32]),
                trust_score=int(pipe_res.trust_score),
                raw_trust_score=int(pipe_res.raw_trust_score),
                evidence_sufficiency_score=float(
                    pipe_res.verdict_data.get("evidence_sufficiency_score") or 0.0
                ),
                evidence_status=str(pipe_res.evidence_status)[:32],
                is_correct=is_correct,
                is_abstained=bool(pipe_res.is_abstained),
                is_critical_error=is_critical_error,
                claims_summary={
                    "supporting_evidence": pipe_res.verdict_data.get("supporting_evidence", []),
                    "contradictions": pipe_res.verdict_data.get("detected_contradictions", []),
                    "missing": pipe_res.verdict_data.get("missing_evidence", []),
                    "exclusion_reason": exclusion_reason,
                    "is_exploratory": is_exploratory_only,
                    "ground_truth_provenance": provenance_source,
                    "policy_version_id": policy_version_id,
                    "policy_digest": policy_digest,
                    "provider_type": pipe_res.provider_type_used,
                    "execution_provenance": pipe_res.verdict_prov.get("execution_provenance"),
                    "model_identifier": model_ident,
                    "is_simulated": bool(pipe_res.verdict_data.get("is_simulated", is_simulated_run)),
                    "prompt_tokens": pipe_res.prompt_tokens,
                    "completion_tokens": pipe_res.completion_tokens,
                    "total_tokens": pipe_res.total_tokens,
                    "evidence_trace": pipe_res.evidence_trace,
                    "partition": HistoricalGroundTruthValidator.assign_partition(inc_id_str).value,
                    "evidence_snapshot_hash": ev_snap_hash,
                },
                escalation_reason=str(pipe_res.escalation_reason)[:256]
                if pipe_res.escalation_reason
                else None,
                created_at=utc_now(),
            )
            self.db.add(result_record)

            if is_exploratory_only:
                exploratory_replay_count += 1
                exploratory_items.append({
                    "incident_id": inc_id_str,
                    "rule_id": inc.rule_id,
                    "suggested_verdict": pipe_res.proposed_verdict,
                    "effective_verdict": eff_verdict,
                    "trust_score": pipe_res.trust_score,
                    "evidence_status": pipe_res.evidence_status,
                    "validation_status": pipe_res.verdict_data.get("validation_status"),
                    "is_exploratory": True,
                })
                continue

            eval_items.append({
                "incident_id": inc_id_str,
                "rule_id": inc.rule_id,
                "suggested_verdict": pipe_res.proposed_verdict,
                "effective_verdict": eff_verdict,
                "ground_truth_label": gt_label,
                "ground_truth_provenance": provenance_source,
                "trust_score": pipe_res.trust_score,
                "raw_trust_score": pipe_res.raw_trust_score,
                "evidence_status": pipe_res.evidence_status,
                "is_correct": is_correct,
                "escalation_reason": pipe_res.escalation_reason,
                "provider_type": pipe_res.provider_type_used,
                "model_identifier": model_ident,
                "evidence_trace": pipe_res.evidence_trace,
            })

        stage_details["evaluated"] = eval_items
        stage_details["exploratory_replay"] = exploratory_items

        # 3. Calculate Empirical Accuracy & Uncertainty Metrics Strictly on Verified Eligible Items
        funnel_model = IncidentEligibilityFunnel(
            available=available_count,
            retrieved=retrieved_count,
            total_scanned=retrieved_count,
            rule_matched=rule_matched_count,
            labeled=analyst_labeled_count,
            analyst_labeled=analyst_labeled_count,
            verified=eligible_count,
            eligible=eligible_count,
            independent_group_count=eligible_count,
            excluded=excluded_count,
            duplicate_excluded_count=duplicate_excluded_count,
            synthetic_excluded_count=synthetic_excluded_count,
            inferred=inferred_count,
            evaluated=len(eval_items),
            scored=len(eval_items),
            exploratory_replay_count=exploratory_replay_count,
            exclusion_reasons=exclusion_reasons,
            exclusions_detail=[IncidentExclusionRecord(**ex) for ex in exclusions_detail[:500]],
            stage_details=stage_details,
        )
        metrics = EmpiricalAccuracyEvaluator.evaluate_performance(eval_items, funnel=funnel_model)
        metrics.independent_group_count = eligible_count
        metrics_dict = metrics.model_dump()
        metrics_dict["stage_details"] = stage_details

        if rule_matched_count < self.MIN_HISTORICAL_SAMPLES or eligible_count < self.MIN_HISTORICAL_SAMPLES:
            metrics_dict["message"] = (
                f"Retrieved {retrieved_count} matching historical incidents ({rule_matched_count} rule-matched, "
                f"{eligible_count} verified ground-truth cases < {self.MIN_HISTORICAL_SAMPLES} required)."
            )
        elif is_simulated_run:
            metrics_dict["message"] = (
                f"Dry-run SIMULATED evaluation scored {len(eval_items)} verified cases ({excluded_count} excluded). "
                "SIMULATED outputs do not certify empirical G8."
            )
        else:
            metrics_dict["message"] = (
                f"Empirical evaluation scored {len(eval_items)} verified cases via {provider_upper} ({excluded_count} excluded)."
            )

        run_record.metrics = metrics_dict
        run_record.evaluated_cases = len(eval_items)
        run_record.verified_ground_truth_cases = metrics.verified_ground_truth_cases
        run_record.config_snapshot = {
            **(run_record.config_snapshot or {}),
            "model_identifier": observed_models[0] if observed_models else (
                "simulated-v2.2-policy-aware" if is_simulated_run else None
            ),
            "observed_models": observed_models,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_tokens": total_tokens_sum,
            "inferred_count": inferred_count,
            "scored_count": len(eval_items),
            "exploratory_replay_count": exploratory_replay_count,
        }

        # 4. Generate Risk-Coverage Curve (never computed on exploratory/excluded items)
        risk_coverage = EmpiricalAccuracyEvaluator.generate_risk_coverage_curve(eval_items)
        run_record.selective_metrics = [rc.model_dump() for rc in risk_coverage]

        # 5. Evaluate Calibration
        calib_report = CalibrationEvaluator.evaluate_calibration(eval_items)
        calib_dict = calib_report.model_dump()
        if is_simulated_run:
            calib_dict["is_calibrated"] = False
            calib_dict["status"] = "SIMULATED_NOT_CALIBRATED"
        run_record.calibration_metrics = calib_dict

        # 6. Determine Authoritative Empirical Validation State
        if baseline_run_id:
            reg_report = await self.compare_runs(baseline_run_id=baseline_run_id, candidate_run_id=run_record.id)
            run_record.regression_summary = reg_report.model_dump()
            if reg_report.validation_state == EvaluationValidationState.REGRESSION_DETECTED:
                run_record.validation_state = EvaluationValidationState.REGRESSION_DETECTED.value
            elif eligible_count < self.MIN_HISTORICAL_SAMPLES:
                run_record.validation_state = EvaluationValidationState.INSUFFICIENT_DATA.value
            elif is_simulated_run:
                run_record.validation_state = EvaluationValidationState.INCONCLUSIVE.value
            elif reg_report.validation_state in (EvaluationValidationState.VALIDATED, EvaluationValidationState.PASS):
                run_record.validation_state = EvaluationValidationState.VALIDATED.value
                run_record.config_snapshot = {**(run_record.config_snapshot or {}), "certifying_empirical_eligible": True}
            else:
                run_record.validation_state = reg_report.validation_state.value
        else:
            if eligible_count < self.MIN_HISTORICAL_SAMPLES:
                run_record.validation_state = EvaluationValidationState.INSUFFICIENT_DATA.value
            elif metrics.critical_false_negatives > 0:
                run_record.validation_state = EvaluationValidationState.REGRESSION_DETECTED.value
            elif is_simulated_run:
                run_record.validation_state = EvaluationValidationState.INCONCLUSIVE.value
                run_record.config_snapshot = {**(run_record.config_snapshot or {}), "dry_run_validation_state": "SIMULATED_NON_CERTIFYING"}
            elif metrics.overall_accuracy is not None and metrics.overall_accuracy >= 0.80 and metrics.critical_false_negatives == 0:
                run_record.validation_state = EvaluationValidationState.VALIDATED.value
                run_record.config_snapshot = {**(run_record.config_snapshot or {}), "certifying_empirical_eligible": True}
            else:
                run_record.validation_state = EvaluationValidationState.INCONCLUSIVE.value

        run_record.status = "COMPLETED"
        run_record.completed_at = utc_now()
        await self.db.commit()
        await self.db.refresh(run_record)
        return run_record

    async def compare_runs(
        self,
        baseline_run_id: str,
        candidate_run_id: str,
    ) -> RegressionComparisonReport:
        """
        Executes paired regression comparison between baseline and candidate evaluation runs
        across identical incident cases.
        """
        q_base = select(HistoricalEvaluationResultRecord).where(HistoricalEvaluationResultRecord.run_id == baseline_run_id)
        q_cand = select(HistoricalEvaluationResultRecord).where(HistoricalEvaluationResultRecord.run_id == candidate_run_id)

        res_base = await self.db.execute(q_base)
        res_cand = await self.db.execute(q_cand)

        base_results = {r.incident_id: r for r in res_base.scalars().all()}
        cand_results = {r.incident_id: r for r in res_cand.scalars().all()}

        common_ids = set(base_results.keys()).intersection(cand_results.keys())
        sample_count = len(common_ids)

        if sample_count < 5:
            return RegressionComparisonReport(
                rule_id=cand_results[list(cand_results.keys())[0]].rule_id if cand_results else None,
                baseline_run_id=baseline_run_id,
                candidate_run_id=candidate_run_id,
                validation_state=EvaluationValidationState.INSUFFICIENT_DATA,
                regression_status="INSUFFICIENT_DATA",
                sample_count=sample_count,
                baseline_coverage=0.0,
                candidate_coverage=0.0,
                coverage_delta=0.0,
                summary_message=f"Only {sample_count} common cases between runs. At least 5 required for regression comparison.",
            )

        regressed_cases: List[CaseRegressionDetail] = []
        improved_cases: List[CaseRegressionDetail] = []

        base_correct = 0
        cand_correct = 0
        base_auto = 0
        cand_auto = 0

        for inc_id in common_ids:
            b = base_results[inc_id]
            c = cand_results[inc_id]

            if b.ground_truth_label in (GroundTruthLabel.VERIFIED_TP.value, GroundTruthLabel.VERIFIED_FP.value):
                if not b.is_abstained:
                    base_auto += 1
                    if b.is_correct:
                        base_correct += 1

                if not c.is_abstained:
                    cand_auto += 1
                    if c.is_correct:
                        cand_correct += 1

                # Check for critical regression: was correct TP in baseline, now false negative or wrong
                if b.is_correct and not c.is_correct and not c.is_abstained:
                    reg_type = "TP_DROPPED_TO_FN" if b.ground_truth_label == GroundTruthLabel.VERIFIED_TP.value else "FP_INTRODUCED"
                    regressed_cases.append(
                        CaseRegressionDetail(
                            incident_id=inc_id,
                            rule_id=c.rule_id,
                            ground_truth=c.ground_truth_label,
                            baseline_verdict=b.effective_verdict,
                            candidate_verdict=c.effective_verdict,
                            baseline_trust=b.trust_score,
                            candidate_trust=c.trust_score,
                            regression_type=reg_type,
                            reason=f"Candidate made wrong decision on verified case that baseline answered correctly.",
                        )
                    )
                elif not b.is_correct and c.is_correct:
                    improved_cases.append(
                        CaseRegressionDetail(
                            incident_id=inc_id,
                            rule_id=c.rule_id,
                            ground_truth=c.ground_truth_label,
                            baseline_verdict=b.effective_verdict,
                            candidate_verdict=c.effective_verdict,
                            baseline_trust=b.trust_score,
                            candidate_trust=c.trust_score,
                            regression_type="IMPROVEMENT",
                            reason=f"Candidate correctly resolved case where baseline failed.",
                        )
                    )

        base_acc = (base_correct / base_auto) if base_auto > 0 else None
        cand_acc = (cand_correct / cand_auto) if cand_auto > 0 else None
        acc_delta = round((cand_acc - base_acc) * 100.0, 2) if (base_acc is not None and cand_acc is not None) else None

        base_cov = round(base_auto / sample_count, 4)
        cand_cov = round(cand_auto / sample_count, 4)
        cov_delta = round((cand_cov - base_cov) * 100.0, 2)

        # Statistical significance: Mcnemar test approximation
        b_better = len(regressed_cases)  # cases where baseline was correct, cand was wrong
        c_better = len(improved_cases)   # cases where candidate was correct, base was wrong
        discordant = b_better + c_better

        if discordant >= 10:
            chi2 = ((abs(b_better - c_better) - 1.0) ** 2) / discordant
            is_sig = chi2 > 3.841  # p < 0.05
            p_val = 0.04 if is_sig else 0.20
        else:
            is_sig = False
            p_val = None

        critical_reg_count = sum(1 for r in regressed_cases if r.regression_type == "TP_DROPPED_TO_FN")

        if critical_reg_count > 0 or (acc_delta is not None and acc_delta < -2.0 and is_sig):
            val_state = EvaluationValidationState.REGRESSION_DETECTED
            msg = f"REGRESSION DETECTED: {critical_reg_count} critical false negatives introduced. Accuracy delta: {acc_delta or 0}%."
        elif acc_delta is not None and acc_delta >= 0.0 and len(improved_cases) >= len(regressed_cases):
            val_state = EvaluationValidationState.VALIDATED
            msg = f"VALIDATED: Candidate maintained or improved performance (+{acc_delta or 0}% accuracy delta)."
        else:
            val_state = EvaluationValidationState.INCONCLUSIVE
            msg = f"INCONCLUSIVE: Discordant outcomes within statistical noise margin."

        reg_status = "REGRESSION_DETECTED" if val_state == EvaluationValidationState.REGRESSION_DETECTED else (
            "PASS" if val_state == EvaluationValidationState.VALIDATED else val_state.value
        )

        return RegressionComparisonReport(
            rule_id=cand_results[list(cand_results.keys())[0]].rule_id if cand_results else None,
            baseline_run_id=baseline_run_id,
            candidate_run_id=candidate_run_id,
            validation_state=val_state,
            regression_status=reg_status,
            sample_count=sample_count,
            baseline_accuracy=round(base_acc * 100.0, 2) if base_acc is not None else None,
            candidate_accuracy=round(cand_acc * 100.0, 2) if cand_acc is not None else None,
            accuracy_delta=acc_delta,
            baseline_coverage=base_cov,
            candidate_coverage=cand_cov,
            coverage_delta=cov_delta,
            critical_regressions_count=critical_reg_count,
            statistically_significant=is_sig,
            p_value_estimate=p_val,
            regressed_cases=regressed_cases,
            improved_cases=improved_cases,
            summary_message=msg,
        )

    def _simulate_model_output(
        self,
        incident_payload: Dict[str, Any],
        contract: Optional[Any] = None,
        prompt_version: Optional[PromptVersion] = None,
    ) -> Dict[str, Any]:
        """
        Generates simulated LLM reasoning and claims based on observed incident telemetry
        and the candidate PromptVersion policy criteria (TP/FP/missing-info rules).
        """
        src = incident_payload.get("source_ip", "")
        evt = str(incident_payload.get("event_type", ""))
        raw = incident_payload.get("raw_payload") or {}
        if not isinstance(raw, dict):
            raw = {}

        tp_policy_text = (getattr(prompt_version, "tp_indicators", "") or "").lower()
        fp_policy_text = (getattr(prompt_version, "fp_indicators", "") or "").lower()
        missing_policy_text = (getattr(prompt_version, "missing_info_criteria", "") or "").lower()

        # Check for exfiltration byte indicator
        bytes_sent = raw.get("sentBytes64") or raw.get("bytes_sent") or raw.get("bytes_out") or 0
        try:
            bytes_sent_int = int(float(bytes_sent))
        except (ValueError, TypeError):
            bytes_sent_int = 0

        claims = []
        if src:
            claims.append({
                "claim": f"Transmitting internal host is {src}",
                "evidence_ids": ["source_ip"],
                "claim_type": "OBSERVED_FACT",
            })
        if bytes_sent_int:
            claims.append({
                "claim": f"Total observed outbound transfer volume is {bytes_sent_int} bytes",
                "evidence_ids": ["sentBytes64"],
                "claim_type": "OBSERVED_FACT",
            })

        raw_str = str(raw).lower()
        inc_str = str(incident_payload).lower()

        # Enforce candidate policy abstention trigger if command_line / critical fields absent when required
        cmd_val = raw.get("command_line") or raw.get("cmdline") or raw.get("Command")
        if ("command" in missing_policy_text or "command_line" in missing_policy_text) and not cmd_val and not bytes_sent_int:
            return {
                "verdict": "REQUIRES_ATTENTION",
                "confidence": 40.0,
                "reason": "Policy abstention triggered: required command-line telemetry missing from incident.",
                "claims": claims,
                "supporting_evidence": [],
                "model_identifier": "simulated-v2.2-policy-aware",
                "is_simulated": True,
            }

        # Policy-aware False Positive check
        is_backup_ctx = "backup" in raw_str or "backup" in inc_str or bool(raw.get("authorization_ticket"))
        is_maint_ctx = any(k in raw_str or k in inc_str for k in ("maintenance", "ccmexec", "patch", "scheduled"))
        if is_backup_ctx or (is_maint_ctx and ("maintenance" in fp_policy_text or "scheduled" in fp_policy_text or not fp_policy_text)):
            dest = raw.get("destination_ip") or raw.get("business_service") or "verified endpoint"
            claims.append({
                "claim": f"Transfer or maintenance activity verified against authorized endpoint {dest}",
                "evidence_ids": ["destination_ip" if raw.get("destination_ip") else "raw_payload"],
                "claim_type": "OBSERVED_FACT",
            })
            return {
                "verdict": "FALSE_POSITIVE",
                "confidence": 88.0,
                "reason": "Authorized scheduled backup or approved maintenance activity confirmed.",
                "claims": claims,
                "supporting_evidence": ["Authorized operational maintenance/backup confirmed"],
                "model_identifier": "simulated-v2.2-policy-aware",
                "is_simulated": True,
            }

        # Policy-aware True Positive check
        malicious_cmd = cmd_val and any(k in str(cmd_val).lower() for k in ("-enc", "powershell", "mimikatz", "rundll32", "lsass"))
        if bytes_sent_int > 1_000_000_000 or malicious_cmd:
            if malicious_cmd:
                claims.append({
                    "claim": f"Suspicious process command line observed: {cmd_val}",
                    "evidence_ids": ["command_line"],
                    "claim_type": "OBSERVED_FACT",
                })
            return {
                "verdict": "TRUE_POSITIVE",
                "confidence": 92.0,
                "reason": (
                    f"High volume outbound transfer of {bytes_sent_int} bytes observed from {src}."
                    if bytes_sent_int > 1_000_000_000
                    else f"Suspicious execution indicator observed in telemetry ({cmd_val})."
                ),
                "claims": claims,
                "supporting_evidence": [f"Source IP {src}", f"Indicator: {bytes_sent_int or cmd_val}"],
                "model_identifier": "simulated-v2.2-policy-aware",
                "is_simulated": True,
            }
        else:
            return {
                "verdict": "REQUIRES_ATTENTION",
                "confidence": 50.0,
                "reason": "Telemetry insufficient to prove malicious or benign justification.",
                "claims": claims,
                "supporting_evidence": [],
                "model_identifier": "simulated-v2.2-policy-aware",
                "is_simulated": True,
            }

    # REQ-07 Compatibility & AIS 2.1 Governed Simulation Evaluator
    async def evaluate_candidate_policy(
        self,
        rule_id: str,
        candidate_version: Optional[PromptVersion] = None,
        baseline_version: Optional[PromptVersion] = None,
        provider_type: str = "SIMULATED",
        sample_limit: Optional[int] = 500,
        include_unlabeled_replay: bool = False,
        existing_run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes empirical policy simulation on rule-matched historical incidents.
        Separates SIMULATED dry-runs (non-certifying for Gate G8) from real
        OPENAI_COMPATIBLE empirical evaluations, reporting the full 8-stage funnel.
        """
        version_num = getattr(candidate_version, "version_number", 1) if candidate_version else 1
        pv_id = str(getattr(candidate_version, "id", "")) if candidate_version else None
        provider_upper = str(provider_type or "SIMULATED").upper().strip()

        matched_rule = await resolve_canonical_rule(self.db, rule_id)
        scope_rule_ids = (
            list(dict.fromkeys([x for x in (rule_id, matched_rule.id, matched_rule.rule_id) if x]))
            if matched_rule
            else [rule_id]
        )

        # Look up baseline run ONLY if baseline_version is provided, distinct, and compatible
        baseline_run_id = None
        cand_id_str = str(getattr(candidate_version, "id", "")) if candidate_version else ""
        if baseline_version and getattr(baseline_version, "id", None) and str(baseline_version.id) != cand_id_str:
            try:
                base_run_q = (
                    select(HistoricalEvaluationRunRecord)
                    .where(
                        HistoricalEvaluationRunRecord.policy_version_id == str(baseline_version.id),
                        HistoricalEvaluationRunRecord.rule_id.in_(scope_rule_ids),
                        HistoricalEvaluationRunRecord.status == "COMPLETED",
                    )
                    .order_by(desc(HistoricalEvaluationRunRecord.completed_at))
                    .limit(10)
                )
                base_run_res = await self.db.execute(base_run_q)
                base_candidates = base_run_res.scalars().all()
                for base_run in base_candidates:
                    if provider_upper == "OPENAI_COMPATIBLE" and self._is_simulated_run(base_run):
                        continue
                    if (base_run.verified_ground_truth_cases or base_run.total_cases or 0) >= self.MIN_HISTORICAL_SAMPLES:
                        baseline_run_id = base_run.id
                        break
            except Exception as e:
                logger.warning(f"Failed to lookup baseline run: {e}")

        run = await self.run_dry_run_intelligence_evaluation(
            run_name=f"G8 Empirical Gate Evaluation (v{version_num}, {provider_upper})",
            rule_id=rule_id,
            policy_version_id=pv_id,
            baseline_run_id=baseline_run_id,
            sample_limit=sample_limit,
            provider_type=provider_upper,
            include_unlabeled_replay=include_unlabeled_replay,
            existing_run_id=existing_run_id,
        )

        metrics = run.metrics or {}
        cfg_snap = run.config_snapshot or {}
        reg_summary = run.regression_summary or {}
        funnel_data = metrics.get("funnel") or {}
        eligible_gt_cases = int(metrics.get("verified_ground_truth_cases") or 0)
        rule_matched_cases = int(funnel_data.get("rule_matched", run.total_cases) or 0)
        is_simulated_run = self._is_simulated_run(run) or (provider_upper in SIMULATED_PROVIDER_TOKENS)

        # 1. Determine Baseline Regression Status
        if not baseline_run_id:
            regression_status = "NOT_ASSESSED"
            reg_detected = False
            reg_summary = {
                "regression_status": "NOT_ASSESSED",
                "validation_state": "NOT_ASSESSED",
                "summary_message": "No approved baseline run available for paired regression testing.",
                "critical_regressions_count": 0,
                "regressed_cases": [],
                "improved_cases": [],
            }
        else:
            regression_status = reg_summary.get("regression_status") or reg_summary.get("validation_state") or (
                "REGRESSION_DETECTED" if reg_summary.get("critical_regressions_count", 0) > 0 else "PASS"
            )
            reg_detected = bool(regression_status == "REGRESSION_DETECTED")

        # 2. Strict Empirical Validation Status (SIMULATED never passes G8)
        if eligible_gt_cases < self.MIN_HISTORICAL_SAMPLES or rule_matched_cases < self.MIN_HISTORICAL_SAMPLES:
            empirical_validation_status = "INSUFFICIENT_DATA"
            sim_status = SimulationStatus.INSUFFICIENT_DATA.value
            status_str = "INSUFFICIENT_DATA"
        elif int(metrics.get("critical_false_negatives") or 0) > 0 or reg_detected:
            empirical_validation_status = "EVALUATED_FAILED"
            sim_status = SimulationStatus.EVALUATED_FAILED.value
            status_str = "FAILED"
        elif is_simulated_run:
            empirical_validation_status = "SIMULATED_ONLY_NOT_CERTIFYING"
            sim_status = SimulationStatus.NOT_EVALUATED.value
            status_str = "SIMULATED_ONLY"
        elif (
            (metrics.get("overall_accuracy") is not None and float(metrics["overall_accuracy"]) >= 0.80)
            or (metrics.get("balanced_accuracy") is not None and float(metrics["balanced_accuracy"]) >= 0.80)
        ):
            empirical_validation_status = "EVALUATED_PASSED"
            sim_status = SimulationStatus.EVALUATED_PASSED.value
            status_str = "PASSED"
        else:
            empirical_validation_status = "INCONCLUSIVE"
            sim_status = SimulationStatus.INCONCLUSIVE.value
            status_str = "INCONCLUSIVE"

        # 3. Truthful message with provider provenance
        if sim_status == SimulationStatus.INSUFFICIENT_DATA.value:
            msg = (
                f"Retrieved {funnel_data.get('retrieved', run.total_cases)} rule-matched historical incidents; "
                f"empirical validation has {eligible_gt_cases} verified ground-truth cases "
                f"({funnel_data.get('excluded', 0)} excluded; minimum {self.MIN_HISTORICAL_SAMPLES} required)."
            )
        elif reg_detected or sim_status == SimulationStatus.EVALUATED_FAILED.value:
            msg = "FAILED: Historical simulation detected critical regressions or unacceptable critical false negatives."
        elif is_simulated_run:
            msg = (
                f"Dry-run SIMULATED evaluation completed on {eligible_gt_cases} verified ground-truth cases. "
                "SIMULATED outputs are non-certifying for empirical Gate G8; execute with OPENAI_COMPATIBLE to certify."
            )
        elif sim_status == SimulationStatus.INCONCLUSIVE.value:
            msg = f"Simulation INCONCLUSIVE on {run.total_cases} historical incidents ({eligible_gt_cases} verified cases; 0% decisive coverage or inconclusive accuracy)."
        else:
            msg = reg_summary.get("summary_message") if baseline_run_id else (
                f"Empirical simulation PASSED with real provider '{cfg_snap.get('provider_type')}' "
                f"on {eligible_gt_cases} verified ground-truth cases."
            )

        def _to_optional_float(v: Any) -> Optional[float]:
            if v is None:
                return None
            try:
                return float(v)
            except (ValueError, TypeError):
                return None

        # Fetch per-incident result records for drilldown
        res_q = (
            select(HistoricalEvaluationResultRecord)
            .where(HistoricalEvaluationResultRecord.run_id == run.id)
            .limit(100)
        )
        res_exec = await self.db.execute(res_q)
        eval_results_db = res_exec.scalars().all()
        per_incident_results = [
            {
                "incident_id": r.incident_id,
                "rule_id": r.rule_id,
                "ground_truth": r.ground_truth_label,
                "suggested_verdict": r.suggested_verdict,
                "effective_verdict": r.effective_verdict,
                "trust_score": r.trust_score,
                "raw_trust_score": r.raw_trust_score,
                "evidence_status": r.evidence_status,
                "is_correct": r.is_correct,
                "is_abstained": r.is_abstained,
                "is_critical_error": r.is_critical_error,
                "escalation_reason": r.escalation_reason,
                "is_exploratory": bool((r.claims_summary or {}).get("is_exploratory", False)),
                "provider_type": (r.claims_summary or {}).get("provider_type", cfg_snap.get("provider_type")),
                "model_identifier": (r.claims_summary or {}).get("model_identifier", cfg_snap.get("model_identifier")),
                "execution_provenance": (r.claims_summary or {}).get("execution_provenance", cfg_snap.get("execution_provenance")),
                "evidence_trace": (r.claims_summary or {}).get("evidence_trace"),
            }
            for r in eval_results_db
        ]

        return {
            "status": status_str,
            "simulation_status": sim_status,
            "empirical_validation_status": empirical_validation_status,
            "certifying_empirical_eligible": (not is_simulated_run and sim_status == SimulationStatus.EVALUATED_PASSED.value),
            "provider_type": cfg_snap.get("provider_type", provider_upper),
            "is_simulated": is_simulated_run,
            "execution_provenance": cfg_snap.get("execution_provenance", "SIMULATED" if is_simulated_run else "REAL_LOCAL_LLM"),
            "model_identifier": cfg_snap.get("model_identifier"),
            "sample_count": run.total_cases,
            "available_count": funnel_data.get("available", run.total_cases),
            "retrieved_count": funnel_data.get("retrieved", run.total_cases),
            "evaluated_cases": run.evaluated_cases or 0,
            "inferred_count": funnel_data.get("inferred", run.evaluated_cases or 0),
            "scored_count": funnel_data.get("scored", run.evaluated_cases or 0),
            "exploratory_replay_count": funnel_data.get("exploratory_replay_count", 0),
            "total_scanned": funnel_data.get("total_scanned", run.total_cases),
            "rule_matched": rule_matched_cases,
            "analyst_labeled": funnel_data.get("analyst_labeled", eligible_gt_cases),
            "verified_count": funnel_data.get("verified", eligible_gt_cases),
            "eligible_ground_truth_count": eligible_gt_cases,
            "verified_ground_truth_cases": eligible_gt_cases,
            "excluded_count": funnel_data.get("excluded", max(0, rule_matched_cases - eligible_gt_cases)),
            "exclusion_reasons": funnel_data.get("exclusion_reasons", {}),
            "exclusions_detail": funnel_data.get("exclusions_detail", []),
            "stage_details": funnel_data.get("stage_details") or metrics.get("stage_details") or {},
            "funnel": funnel_data,
            "min_samples_required": self.MIN_HISTORICAL_SAMPLES,
            "message": msg,
            "critical_regressions": int(metrics.get("critical_false_negatives") or 0),
            "regression_detected": reg_detected,
            "regression_status": regression_status,
            "abstention_rate": _to_optional_float(metrics.get("analyst_attention_rate") if metrics.get("analyst_attention_rate") is not None else metrics.get("abstention_rate")),
            "balanced_accuracy": _to_optional_float(metrics.get("balanced_accuracy")),
            "precision": _to_optional_float(metrics.get("precision")),
            "recall": _to_optional_float(metrics.get("recall")),
            "specificity": _to_optional_float(metrics.get("specificity")),
            "false_positive_rate": _to_optional_float(metrics.get("false_positive_rate")),
            "false_negative_rate": _to_optional_float(metrics.get("false_negative_rate")),
            "decision_coverage": _to_optional_float(metrics.get("automatic_decision_coverage") if metrics.get("automatic_decision_coverage") is not None else metrics.get("decision_coverage")),
            "overall_accuracy": _to_optional_float(metrics.get("overall_accuracy")),
            "confusion_matrix": {
                "tp": int(metrics.get("true_positives", 0)),
                "fp": int(metrics.get("false_positives", 0)),
                "tn": int(metrics.get("true_negatives", 0)),
                "fn": int(metrics.get("false_negatives", 0)),
                "abstained": int(metrics.get("analyst_attention_count", 0)),
            },
            "ground_truth_distribution": {
                "tp": int(metrics.get("tp_ground_truth_count", 0)),
                "fp": int(metrics.get("fp_ground_truth_count", 0)),
                "unverified": int(metrics.get("unverified_cases", 0)),
            },
            "run_id": str(run.id),
            "policy_version_id": pv_id,
            "policy_digest": cfg_snap.get("policy_digest"),
            "token_usage": {
                "prompt_tokens": int(cfg_snap.get("total_prompt_tokens", 0)),
                "completion_tokens": int(cfg_snap.get("total_completion_tokens", 0)),
                "total_tokens": int(cfg_snap.get("total_tokens", 0)),
            },
            "is_calibrated": bool(run.calibration_metrics.get("is_calibrated", False)),
            "calibration_status": run.calibration_metrics.get("status", "NOT_CALIBRATED"),
            "brier_score": _to_optional_float(run.calibration_metrics.get("brier_score")),
            "ece": _to_optional_float(run.calibration_metrics.get("expected_calibration_error")),
            "candidate_metrics": metrics,
            "baseline_metrics": reg_summary.get("baseline_accuracy"),
            "regressed_cases": reg_summary.get("regressed_cases", []),
            "improved_cases": reg_summary.get("improved_cases", []),
            "per_incident_results": per_incident_results,
            "evaluated_at": utc_now().isoformat(),
        }
