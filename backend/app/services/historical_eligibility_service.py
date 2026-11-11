import csv
import io
import json
from datetime import datetime
from app.utils.datetime_utils import utc_now
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.incident import HistoricalGroundTruth, Incident
from app.models.investigation import Investigation
from app.models.prompt import RulePrompt
from app.models.rule import Rule
from app.schemas.verdict_intelligence import GroundTruthLabel
from app.services.evidence_contract_service import EvidenceContractService
from app.services.evidence_normalization_service import EvidenceNormalizationService
from app.services.historical_ground_truth_validator import HistoricalGroundTruthValidator
from app.services.policy_governance import (
    RuleMatchContext,
    build_rule_incident_context,
    verify_incident_matches_rule,
)


class HistoricalEligibilityService:
    """
    Produces a reusable, machine-readable historical corpus eligibility & ground-truth
    readiness diagnostic report across rules without altering historical labels,
    verification flags, or database records.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _classify_ml_flag_reevaluation(
        inc: Incident,
        gt: Optional[HistoricalGroundTruth],
        inv: Optional[Investigation],
    ) -> Optional[Dict[str, Any]]:
        """
        Read-only audit classifying an existing `is_ml_generated=True` row against
        AIS 2.1/2.2 word-boundary ML detection and human provenance rules.
        Never mutates any database field.
        """
        if gt is None or not bool(getattr(gt, "is_ml_generated", False)):
            return None

        raw_res = str(getattr(gt, "resolution", "") or "")
        comments = str(getattr(gt, "comments", "") or "")
        cleared_reason = str(getattr(gt, "cleared_reason", "") or "")
        cleared_user = str(getattr(gt, "cleared_user", "") or "")
        raw_status = str(getattr(inc, "status_name", "") or "")

        still_detected_ml = HistoricalGroundTruthValidator.detect_automated_or_ml_text(
            comments=comments,
            resolution=raw_res,
            cleared_reason=cleared_reason,
            cleared_user=cleared_user,
            raw_status=raw_status,
        )
        inv_verified = bool(
            inv is not None
            and getattr(inv, "is_independently_verified", False)
            and not getattr(inv, "is_disputed", False)
        )

        if still_detected_ml:
            if inv_verified:
                action = "CONFIRMED_ML_WITH_INDEPENDENT_HUMAN_REVIEW"
                reason = "Original closure automated/ML, but Investigation.is_independently_verified=True exists."
            else:
                action = "KEEP_ML_AUTOMATED"
                reason = "Confirmed ML/automated token or system actor under AIS 2.1 word-boundary detection."
        else:
            adj_if_unflagged, _, rationale = HistoricalGroundTruthValidator.adjudicate_label(
                raw_resolution=raw_res,
                analyst_comments=comments,
                is_ml_generated=False,
                cleared_reason=cleared_reason,
                cleared_user=cleared_user,
            )
            if adj_if_unflagged in (GroundTruthLabel.VERIFIED_TP, GroundTruthLabel.VERIFIED_FP) and inv_verified:
                action = "RECLASSIFY_FALSE_SUBSTRING_HUMAN_VERIFIED"
                reason = f"False-positive 'ml' substring (not ML/automated) with independent verification ({adj_if_unflagged.value})."
            elif adj_if_unflagged in (GroundTruthLabel.VERIFIED_TP, GroundTruthLabel.VERIFIED_FP):
                action = "RECLASSIFY_FALSE_SUBSTRING_NEEDS_REVIEW"
                reason = (
                    f"False-positive 'ml' substring candidate ({adj_if_unflagged.value}: {rationale}); "
                    "requires human verification approval before unflagging is_ml_generated."
                )
            else:
                action = "KEEP_UNVERIFIED_NON_ML"
                reason = f"No ML/automated token found, but resolution remains unverified ({adj_if_unflagged.value})."

        return {
            "incident_id": str(inc.incident_id or inc.id),
            "rule_id": str(inc.rule_id or inc.event_type or ""),
            "stored_is_ml_generated": True,
            "ais21_detected_ml_or_automated": still_detected_ml,
            "investigation_independently_verified": inv_verified,
            "recommended_action": action,
            "reason": reason,
        }

    async def generate_report(self, rule_id: Optional[str] = None) -> Dict[str, Any]:
        rules_res = await self.db.execute(select(Rule).order_by(Rule.name.asc()))
        all_rules = list(rules_res.scalars().all())
        rule_by_uuid: Dict[str, Rule] = {r.id: r for r in all_rules}
        rule_by_logical: Dict[str, Rule] = {r.rule_id: r for r in all_rules if r.rule_id}
        rules_by_event: Dict[str, List[Rule]] = {}
        for r in all_rules:
            if r.event_type:
                rules_by_event.setdefault(r.event_type, []).append(r)

        rule_contexts: Dict[str, RuleMatchContext] = {}
        for r in all_rules:
            rule_contexts[r.id] = await build_rule_incident_context(self.db, r)

        inc_q = select(Incident).options(
            selectinload(Incident.ground_truth),
            selectinload(Incident.events),
            selectinload(Incident.rule),
        )
        inc_res = await self.db.execute(inc_q)
        incidents = list(inc_res.scalars().all())

        inv_res = await self.db.execute(select(Investigation))
        inv_map: Dict[str, Investigation] = {inv.incident_id: inv for inv in inv_res.scalars().all()}

        # Group incidents canonically by Rule without merging distinct sibling rules
        buckets: Dict[str, Dict[str, Any]] = {}
        for r in all_rules:
            if rule_id and rule_id not in (r.id, r.rule_id, r.event_type):
                continue
            buckets[r.id] = {
                "rule_uuid": r.id,
                "rule_id": r.rule_id,
                "event_type": r.event_type,
                "rule_name": r.name,
                "incidents": [],
                "rule_obj": r,
                "rule_ctx": rule_contexts[r.id],
            }

        target_ctx: Optional[RuleMatchContext] = None
        if rule_id:
            matching_bucket = next(
                (b for b in buckets.values() if rule_id in (b["rule_uuid"], b["rule_id"])),
                None,
            ) or next(
                (b for b in buckets.values() if b["event_type"] == rule_id),
                None,
            )
            if matching_bucket:
                target_ctx = matching_bucket["rule_ctx"]

        for inc in incidents:
            matched_rule: Optional[Rule] = inc.rule
            if not matched_rule and inc.rule_id:
                matched_rule = rule_by_uuid.get(inc.rule_id) or rule_by_logical.get(inc.rule_id)
            if not matched_rule and inc.event_type:
                ev_owners = rules_by_event.get(inc.event_type, [])
                if len(ev_owners) == 1:
                    matched_rule = ev_owners[0]

            if matched_rule and matched_rule.id in rule_contexts:
                ok_m, _ = verify_incident_matches_rule(inc, rule_contexts[matched_rule.id])
                if not ok_m:
                    matched_rule = None

            if target_ctx is not None:
                ok_t, _ = verify_incident_matches_rule(inc, target_ctx)
                if not ok_t:
                    continue
                key = target_ctx.canonical_rule_uuid or target_ctx.canonical_rule_identifier or str(rule_id)
            elif rule_id:
                cand_ids = {str(inc.rule_id or ""), str(inc.event_type or "")}
                if matched_rule:
                    cand_ids.update({matched_rule.id, matched_rule.rule_id, matched_rule.event_type})
                if rule_id not in cand_ids:
                    continue
                key = matched_rule.id if matched_rule else (inc.rule_id or inc.event_type or "UNMAPPED")
            else:
                key = matched_rule.id if matched_rule else (inc.rule_id or inc.event_type or "UNMAPPED")

            if key not in buckets:
                buckets[key] = {
                    "rule_uuid": matched_rule.id if matched_rule else None,
                    "rule_id": matched_rule.rule_id if matched_rule else key,
                    "event_type": matched_rule.event_type if matched_rule else inc.event_type,
                    "rule_name": matched_rule.name if matched_rule else key,
                    "incidents": [],
                    "rule_obj": matched_rule,
                    "rule_ctx": rule_contexts.get(matched_rule.id) if matched_rule else None,
                }
            buckets[key]["incidents"].append(inc)

        rule_reports: List[Dict[str, Any]] = []
        totals = {
            "available_incident_count": 0,
            "verified_tp_count": 0,
            "verified_fp_count": 0,
            "disputed_count": 0,
            "insufficient_evidence_count": 0,
            "unverified_or_ml_count": 0,
            "synthetic_count": 0,
            "duplicate_group_count": 0,
            "eligible_independent_count": 0,
        }
        ml_totals = {
            "total_flagged_ml_generated": 0,
            "confirmed_ml_or_automated": 0,
            "false_positive_ml_candidates": 0,
            "human_verified_ready_candidates": 0,
            "needs_human_verification_candidates": 0,
            "confirmed_ml_with_human_review": 0,
            "keep_unverified_non_ml": 0,
        }
        ml_sample_candidates: List[Dict[str, Any]] = []
        overall_exclusion_reasons: Dict[str, int] = {}
        overall_missing_fields: Dict[str, int] = {}
        overall_partitions = {"TRAIN": 0, "TUNING": 0, "CALIBRATION": 0, "LOCKED_TEST": 0}
        earliest_epoch: Optional[int] = None
        latest_epoch: Optional[int] = None

        for b in buckets.values():
            incs: List[Incident] = b["incidents"]
            rule_obj: Optional[Rule] = b["rule_obj"]
            verified_tp = 0
            verified_fp = 0
            disputed = 0
            insufficient_ev = 0
            unverified_ml = 0
            synthetic = 0
            duplicate_excluded = 0
            duplicate_clusters = set()
            eligible = 0
            missing_fields_map: Dict[str, int] = {}
            exclusion_reasons_map: Dict[str, int] = {}
            partitions = {"TRAIN": 0, "TUNING": 0, "CALIBRATION": 0, "LOCKED_TEST": 0}
            rule_ml_audit = {
                "total_flagged_ml_generated": 0,
                "confirmed_ml_or_automated": 0,
                "false_positive_ml_candidates": 0,
                "human_verified_ready_candidates": 0,
                "needs_human_verification_candidates": 0,
            }

            contract = None
            if rule_obj and incs:
                rp_res = await self.db.execute(
                    select(RulePrompt).where(RulePrompt.rule_id == rule_obj.id).options(selectinload(RulePrompt.versions))
                )
                rp_obj = rp_res.scalars().first()
                active_pv = None
                if rp_obj and rp_obj.versions and rp_obj.active_version_id:
                    active_pv = next((v for v in rp_obj.versions if v.id == rp_obj.active_version_id), None)
                contract = EvidenceContractService.get_contract_for_rule(rule_obj, active_pv)

            # Pre-compute best representative per cluster
            cluster_best: Dict[str, Tuple[int, str]] = {}
            for inc in incs:
                rp = inc.raw_payload if isinstance(inc.raw_payload, dict) else {}
                gt = inc.ground_truth
                if HistoricalGroundTruthValidator.is_synthetic_fixture(inc, rp, gt):
                    continue
                miss_c, _ = HistoricalGroundTruthValidator.is_missing_evidence(inc, rp)
                if miss_c:
                    continue
                adj_c, ex_c, _, _, _ = HistoricalGroundTruthValidator.adjudicate_incident_ground_truth(
                    ground_truth=gt,
                    investigation=inv_map.get(inc.id),
                    incident=inc,
                )
                if ex_c is None and gt is not None and adj_c in (GroundTruthLabel.VERIFIED_TP, GroundTruthLabel.VERIFIED_FP):
                    ckey = HistoricalGroundTruthValidator.compute_duplicate_cluster_key(inc, gt, adj_c.value)
                    if ckey:
                        ev_score = len(inc.events or []) + len(rp.get("rawEvents") or [])
                        cid_str = str(inc.incident_id or inc.id)
                        cur = cluster_best.get(ckey)
                        if cur is None or ev_score > cur[0] or (ev_score == cur[0] and cid_str < cur[1]):
                            cluster_best[ckey] = (ev_score, cid_str)

            for inc in incs:
                rp = inc.raw_payload if isinstance(inc.raw_payload, dict) else {}
                gt = inc.ground_truth
                inv = inv_map.get(inc.id)
                inc_epoch = inc.first_seen_epoch or inc.created_at_epoch
                if inc_epoch:
                    earliest_epoch = inc_epoch if earliest_epoch is None else min(earliest_epoch, inc_epoch)
                    latest_epoch = inc_epoch if latest_epoch is None else max(latest_epoch, inc_epoch)

                # Non-mutating ML re-evaluation diagnostic
                ml_diag = self._classify_ml_flag_reevaluation(inc, gt, inv)
                if ml_diag is not None:
                    rule_ml_audit["total_flagged_ml_generated"] += 1
                    ml_totals["total_flagged_ml_generated"] += 1
                    act = ml_diag["recommended_action"]
                    if act == "KEEP_ML_AUTOMATED":
                        rule_ml_audit["confirmed_ml_or_automated"] += 1
                        ml_totals["confirmed_ml_or_automated"] += 1
                    elif act == "CONFIRMED_ML_WITH_INDEPENDENT_HUMAN_REVIEW":
                        rule_ml_audit["confirmed_ml_or_automated"] += 1
                        ml_totals["confirmed_ml_or_automated"] += 1
                        ml_totals["confirmed_ml_with_human_review"] += 1
                    elif act == "RECLASSIFY_FALSE_SUBSTRING_HUMAN_VERIFIED":
                        rule_ml_audit["false_positive_ml_candidates"] += 1
                        rule_ml_audit["human_verified_ready_candidates"] += 1
                        ml_totals["false_positive_ml_candidates"] += 1
                        ml_totals["human_verified_ready_candidates"] += 1
                    elif act == "RECLASSIFY_FALSE_SUBSTRING_NEEDS_REVIEW":
                        rule_ml_audit["false_positive_ml_candidates"] += 1
                        rule_ml_audit["needs_human_verification_candidates"] += 1
                        ml_totals["false_positive_ml_candidates"] += 1
                        ml_totals["needs_human_verification_candidates"] += 1
                    else:
                        ml_totals["keep_unverified_non_ml"] += 1
                    if len(ml_sample_candidates) < 50:
                        ml_sample_candidates.append(ml_diag)

                # Inspect missing canonical evidence fields
                norm = EvidenceNormalizationService.normalize_incident_evidence(inc, inc.events or [])
                present_fields = {
                    r.source_field
                    for r in norm.records
                    if getattr(r, "availability", "AVAILABLE") == "AVAILABLE"
                }
                if contract:
                    for req_f in contract.required_evidence:
                        if req_f.critical and req_f.field not in present_fields:
                            missing_fields_map[req_f.field] = missing_fields_map.get(req_f.field, 0) + 1
                            overall_missing_fields[req_f.field] = overall_missing_fields.get(req_f.field, 0) + 1

                def _record_exclusion(code: str):
                    exclusion_reasons_map[code] = exclusion_reasons_map.get(code, 0) + 1
                    overall_exclusion_reasons[code] = overall_exclusion_reasons.get(code, 0) + 1

                if HistoricalGroundTruthValidator.is_synthetic_fixture(inc, rp, gt):
                    synthetic += 1
                    _record_exclusion("SYNTHETIC_FIXTURE_EXCLUDED")
                    continue

                miss_code, _ = HistoricalGroundTruthValidator.is_missing_evidence(inc, rp)
                if miss_code:
                    insufficient_ev += 1
                    _record_exclusion(miss_code)
                    continue

                adj, ex_code, _, _, _ = HistoricalGroundTruthValidator.adjudicate_incident_ground_truth(
                    ground_truth=gt,
                    investigation=inv,
                    incident=inc,
                )
                if ex_code is not None:
                    if ex_code == "DISPUTED_LABEL":
                        disputed += 1
                    else:
                        unverified_ml += 1
                    _record_exclusion(ex_code)
                    continue

                if adj not in (GroundTruthLabel.VERIFIED_TP, GroundTruthLabel.VERIFIED_FP):
                    unverified_ml += 1
                    _record_exclusion("AMBIGUOUS_LABEL")
                    continue

                cid_str = str(inc.incident_id or inc.id)
                if gt is not None:
                    ckey = HistoricalGroundTruthValidator.compute_duplicate_cluster_key(inc, gt, adj.value)
                    if ckey:
                        duplicate_clusters.add(ckey)
                        if cluster_best.get(ckey, (0, ""))[1] != cid_str:
                            duplicate_excluded += 1
                            _record_exclusion("DUPLICATE_CLUSTER_EXCLUDED")
                            continue

                eligible += 1
                if adj == GroundTruthLabel.VERIFIED_TP:
                    verified_tp += 1
                else:
                    verified_fp += 1

                part = HistoricalGroundTruthValidator.assign_partition(cid_str).value
                partitions[part] = partitions.get(part, 0) + 1
                overall_partitions[part] = overall_partitions.get(part, 0) + 1

            g8_elig = "ELIGIBLE" if eligible >= 5 else "INSUFFICIENT_DATA"
            cal_elig = "ELIGIBLE" if (eligible >= 30 and verified_tp >= 3 and verified_fp >= 3) else "INSUFFICIENT_DATA"

            rule_reports.append(
                {
                    "rule_uuid": b["rule_uuid"],
                    "rule_id": b["rule_id"],
                    "event_type": b.get("event_type"),
                    "rule_name": b["rule_name"],
                    "available_incident_count": len(incs),
                    "verified_tp_count": verified_tp,
                    "verified_fp_count": verified_fp,
                    "disputed_count": disputed,
                    "insufficient_evidence_count": insufficient_ev,
                    "unverified_or_ml_count": unverified_ml,
                    "synthetic_count": synthetic,
                    "duplicate_group_count": len(duplicate_clusters),
                    "duplicate_excluded_count": duplicate_excluded,
                    "eligible_independent_count": eligible,
                    "exclusion_reasons": exclusion_reasons_map,
                    "missing_evidence_fields": [
                        {"field": k, "missing_count": v}
                        for k, v in sorted(missing_fields_map.items(), key=lambda kv: -kv[1])
                    ],
                    "g8_eligibility": g8_elig,
                    "calibration_eligibility": cal_elig,
                    "governance_readiness": {
                        "g8_min_samples_met": eligible >= 5,
                        "sample_threshold_alone_sufficient": False,
                        "autonomous_requires": [
                            "APPROVED policy version with zero structural blockers (G1-G7)",
                            "Non-simulated OPENAI_COMPATIBLE Gate G8 EVALUATED_PASSED run on exact active policy_digest",
                            "Balanced empirical accuracy >= 80% with zero critical false negatives",
                        ],
                    },
                    "ml_reevaluation_audit": rule_ml_audit,
                    "holdout_partitions": partitions,
                }
            )

            totals["available_incident_count"] += len(incs)
            totals["verified_tp_count"] += verified_tp
            totals["verified_fp_count"] += verified_fp
            totals["disputed_count"] += disputed
            totals["insufficient_evidence_count"] += insufficient_ev
            totals["unverified_or_ml_count"] += unverified_ml
            totals["synthetic_count"] += synthetic
            totals["duplicate_group_count"] += len(duplicate_clusters)
            totals["eligible_independent_count"] += eligible

        overall_g8 = "ELIGIBLE" if totals["eligible_independent_count"] >= 5 else "INSUFFICIENT_DATA"
        overall_cal = (
            "ELIGIBLE"
            if (
                totals["eligible_independent_count"] >= 30
                and totals["verified_tp_count"] >= 3
                and totals["verified_fp_count"] >= 3
            )
            else "INSUFFICIENT_DATA"
        )

        return {
            "generated_at": utc_now().isoformat() + "Z",
            "rule_filter": rule_id,
            "integrity_notice": (
                "Read-only ground-truth diagnostic report. Excludes synthetic debug fixtures, disputed investigations, "
                "ML/automated closures without independent verification, missing-evidence wrappers, and duplicate cluster members. "
                "Does not mutate stored labels or authorize autonomous operation on sample threshold alone."
            ),
            "summary": {
                **totals,
                "g8_eligibility": overall_g8,
                "calibration_eligibility": overall_cal,
                "exclusion_reasons": overall_exclusion_reasons,
                "governance_readiness": {
                    "min_sample_threshold": 5,
                    "sample_threshold_alone_sufficient": False,
                    "autonomous_operation_requires_empirical_g8_pass": True,
                },
                "ml_reevaluation_audit": {
                    **ml_totals,
                    "mutated_records": 0,
                    "sample_candidates": ml_sample_candidates,
                },
                "holdout_partitions": overall_partitions,
                "time_window": {
                    "earliest_epoch": earliest_epoch,
                    "latest_epoch": latest_epoch,
                },
                "missing_evidence_fields": [
                    {"field": k, "missing_count": v}
                    for k, v in sorted(overall_missing_fields.items(), key=lambda kv: -kv[1])
                ],
            },
            "rules": rule_reports,
        }

    @staticmethod
    def to_csv(report: Dict[str, Any]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "rule_id",
            "rule_name",
            "available_incident_count",
            "verified_tp_count",
            "verified_fp_count",
            "disputed_count",
            "insufficient_evidence_count",
            "unverified_or_ml_count",
            "synthetic_count",
            "duplicate_group_count",
            "eligible_independent_count",
            "g8_eligibility",
            "calibration_eligibility",
            "missing_evidence_fields",
        ])
        for r in report.get("rules", []):
            miss_str = "; ".join(f"{m['field']}({m['missing_count']})" for m in r.get("missing_evidence_fields", []))
            writer.writerow([
                r["rule_id"],
                r["rule_name"],
                r["available_incident_count"],
                r["verified_tp_count"],
                r["verified_fp_count"],
                r["disputed_count"],
                r["insufficient_evidence_count"],
                r["unverified_or_ml_count"],
                r["synthetic_count"],
                r["duplicate_group_count"],
                r["eligible_independent_count"],
                r["g8_eligibility"],
                r["calibration_eligibility"],
                miss_str,
            ])
        return output.getvalue()
