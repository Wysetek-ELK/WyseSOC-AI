import csv
import io
import json
from datetime import datetime
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


class HistoricalEligibilityService:
    """
    Produces a reusable, machine-readable historical corpus eligibility report (Stage 7)
    across rules and the full corpus without fabricating labels or mixing synthetic/duplicate items.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_report(self, rule_id: Optional[str] = None) -> Dict[str, Any]:
        rules_res = await self.db.execute(select(Rule).order_by(Rule.name.asc()))
        all_rules = list(rules_res.scalars().all())
        rule_lookup: Dict[str, Rule] = {}
        for r in all_rules:
            rule_lookup[r.id] = r
            rule_lookup[r.rule_id] = r
            if r.event_type:
                rule_lookup.setdefault(r.event_type, r)

        inc_q = select(Incident).options(
            selectinload(Incident.ground_truth),
            selectinload(Incident.events),
            selectinload(Incident.rule),
        )
        inc_res = await self.db.execute(inc_q)
        incidents = list(inc_res.scalars().all())

        inv_res = await self.db.execute(select(Investigation).where(Investigation.is_disputed == True))
        disputed_inc_db_ids = {inv.incident_id for inv in inv_res.scalars().all()}

        # Group incidents by canonical rule key
        buckets: Dict[str, Dict[str, Any]] = {}
        for r in all_rules:
            if rule_id and rule_id not in (r.id, r.rule_id, r.event_type):
                continue
            buckets[r.id] = {
                "rule_uuid": r.id,
                "rule_id": r.rule_id,
                "rule_name": r.name,
                "incidents": [],
                "rule_obj": r,
            }

        for inc in incidents:
            matched_rule = inc.rule or rule_lookup.get(inc.rule_id or "") or rule_lookup.get(inc.event_type or "")
            if rule_id:
                cand_ids = {str(inc.rule_id or ""), str(inc.event_type or "")}
                if matched_rule:
                    cand_ids.update({matched_rule.id, matched_rule.rule_id, matched_rule.event_type})
                if rule_id not in cand_ids:
                    continue

            key = matched_rule.id if matched_rule else (inc.rule_id or inc.event_type or "UNMAPPED")
            if key not in buckets:
                buckets[key] = {
                    "rule_uuid": key,
                    "rule_id": matched_rule.rule_id if matched_rule else key,
                    "rule_name": matched_rule.name if matched_rule else key,
                    "incidents": [],
                    "rule_obj": matched_rule,
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
            seen_clusters: Dict[str, str] = {}
            eligible = 0
            missing_fields_map: Dict[str, int] = {}
            partitions = {"TRAIN": 0, "TUNING": 0, "CALIBRATION": 0, "LOCKED_TEST": 0}

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
                if miss_c or not gt or not gt.resolution:
                    continue
                adj_c, _, _ = HistoricalGroundTruthValidator.adjudicate_label(
                    raw_resolution=gt.resolution,
                    analyst_comments=gt.comments,
                    is_ml_generated=gt.is_ml_generated,
                    cleared_reason=getattr(gt, "cleared_reason", None),
                    cleared_user=getattr(gt, "cleared_user", None),
                )
                if adj_c in (GroundTruthLabel.VERIFIED_TP, GroundTruthLabel.VERIFIED_FP):
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
                inc_epoch = inc.first_seen_epoch or inc.created_at_epoch
                if inc_epoch:
                    earliest_epoch = inc_epoch if earliest_epoch is None else min(earliest_epoch, inc_epoch)
                    latest_epoch = inc_epoch if latest_epoch is None else max(latest_epoch, inc_epoch)

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

                if HistoricalGroundTruthValidator.is_synthetic_fixture(inc, rp, gt):
                    synthetic += 1
                    continue

                miss_code, _ = HistoricalGroundTruthValidator.is_missing_evidence(inc, rp)
                if miss_code:
                    insufficient_ev += 1
                    continue

                if inc.id in disputed_inc_db_ids:
                    disputed += 1
                    continue

                if not gt or not gt.resolution:
                    unverified_ml += 1
                    continue

                if HistoricalGroundTruthValidator._is_automated_resolution_text(
                    is_ml_generated=bool(gt.is_ml_generated),
                    comments=str(gt.comments or ""),
                    cleared_reason=str(getattr(gt, "cleared_reason", "") or ""),
                    cleared_user=str(getattr(gt, "cleared_user", "") or ""),
                ):
                    unverified_ml += 1
                    continue

                adj, _, _ = HistoricalGroundTruthValidator.adjudicate_label(
                    raw_resolution=gt.resolution,
                    analyst_comments=gt.comments,
                    is_ml_generated=gt.is_ml_generated,
                    cleared_reason=getattr(gt, "cleared_reason", None),
                    cleared_user=getattr(gt, "cleared_user", None),
                )
                if adj == GroundTruthLabel.CONFLICTING:
                    disputed += 1
                    continue
                if adj not in (GroundTruthLabel.VERIFIED_TP, GroundTruthLabel.VERIFIED_FP):
                    unverified_ml += 1
                    continue

                ckey = HistoricalGroundTruthValidator.compute_duplicate_cluster_key(inc, gt, adj.value)
                cid_str = str(inc.incident_id or inc.id)
                if ckey:
                    duplicate_clusters.add(ckey)
                    if cluster_best.get(ckey, (0, ""))[1] != cid_str:
                        duplicate_excluded += 1
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
                    "missing_evidence_fields": [
                        {"field": k, "missing_count": v}
                        for k, v in sorted(missing_fields_map.items(), key=lambda kv: -kv[1])
                    ],
                    "g8_eligibility": g8_elig,
                    "calibration_eligibility": cal_elig,
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
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "rule_filter": rule_id,
            "integrity_notice": (
                "Excludes synthetic debug fixtures, ML-generated resolutions, missing-evidence wrappers, "
                "and near-duplicate cluster members. Eligibility counts do not represent empirical model accuracy."
            ),
            "summary": {
                **totals,
                "g8_eligibility": overall_g8,
                "calibration_eligibility": overall_cal,
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
