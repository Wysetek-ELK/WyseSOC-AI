"""
AIS 2.6f — Human Ground Truth Certification & Blind Cohort Service

Establishes independently verified human ground truth (GT-0 -> GT-2 -> GT-3 / Adjudication)
for frozen benchmark cohorts (`AIS_2_6E_FROZEN_20`) while enforcing:
1. Strict blind review: AI predictions, trust scores, historical FortiSIEM resolutions,
   and sibling reviewer conclusions are NEVER leaked during active human review.
2. Benchmark isolation: Certification reviews NEVER write into `LearningRecord`, RAG pools,
   or operational prompt optimization.
3. Transactional review locking, dual-reviewer independence, conflict adjudication,
   and immutable reopen revision history.
"""

import hashlib
import json
import logging
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analyst_feedback import (
    AnalystReviewAdjudication,
    AnalystVerdictReview,
    BenchmarkCohort,
    BenchmarkCohortItem,
    BenchmarkReviewRevision,
)
from app.models.audit import AuditLog
from app.models.incident import HistoricalGroundTruth, Incident, IncidentEvent
from app.models.investigation import Investigation, InvestigationEvidence
from app.models.learning import LearningRecord
from app.models.prompt import PromptVersion, RulePrompt
from app.models.rule import Rule
from app.schemas.ground_truth import (
    AdditionalEvidenceInput,
    CohortProgressCounters,
    CohortSummaryResponse,
    GroundTruthAdjudicateRequest,
    GroundTruthDetailResponse,
    GroundTruthQueueItem,
    GroundTruthQueueResponse,
    GroundTruthReopenRequest,
    GroundTruthReviewSubmitRequest,
    GroundTruthUnlockRequest,
    RawLogEntry,
    ReviewerSubmissionSummary,
    RuleDefinitionView,
)
from app.services.blind_review_guard import (
    AIS_3_0_HOLDOUT_COHORT_ID,
    AIS_3_0_HOLDOUT_COHORT_NAME,
    FROZEN_AIS_2_6E_COHORT_ID,
    FROZEN_AIS_2_6E_COHORT_NAME,
    FROZEN_AIS_2_6E_ITEMS,
    has_ai_notes_contamination,
)
from app.services.evidence_normalization_service import EvidenceNormalizationService
from app.utils.datetime_utils import utc_now

logger = logging.getLogger("ai_verdict.ground_truth")

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_FIXTURE_ZIP = _REPO_ROOT / "fixtures" / "Incident json.zip"


def _sha256_canonical(obj: Any) -> str:
    serialized = json.dumps(obj, sort_keys=True, default=str, ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _user_identity(current_user: Any) -> Tuple[str, str, bool]:
    user_id = str(getattr(current_user, "id", "") or "")
    username = str(getattr(current_user, "username", "") or "")
    role = str(getattr(current_user, "role", "") or "")
    is_admin = role in ("Administrator", "SuperAdmin", "SOC_Manager") or bool(
        getattr(current_user, "is_superuser", False)
    )
    reviewer_key = username or user_id or "reviewer"
    return reviewer_key, user_id, is_admin


def _resolve_cohort_item_vendor(
    rule_id: Optional[str],
    rule_obj: Optional[Rule] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> str:
    """Deterministically resolves vendor/telemetry source without falling back to Prisma SASE for unrelated rules."""
    if meta and meta.get("vendor"):
        return str(meta["vendor"])
    rid = str(rule_id or (rule_obj.rule_id if rule_obj else "") or "").upper()
    if "CS_" in rid or "CROWDSTRIKE" in rid:
        return "CrowdStrike"
    if "PRISMA" in rid:
        return "Prisma SASE"
    if "MISP" in rid:
        return "MISP Threat Intel"
    if "FGT_" in rid or "_FGT_" in rid:
        return "FortiGate"
    if "IPS_" in rid or "SEC_IPS" in rid:
        return "IPS / Firewall"
    if "ACCELOPS" in rid or "NO_LOGS" in rid:
        return "FortiSIEM System"
    if rule_obj is not None:
        ds = str(getattr(rule_obj, "data_source", "") or "").strip()
        if "fgt" in ds.lower() or "fw" in ds.lower() or "fortigate" in ds.lower():
            return "FortiGate / Firewall"
    return "FortiSIEM"


def _classify_item_exposure(
    *,
    inc: Optional[Incident],
    in_learning: bool,
    in_other_cohort: bool,
    has_unmasked_ai_notes: bool,
    has_prompt_capture: bool,
) -> Tuple[str, bool, str, Dict[str, Any]]:
    """
    Distinguishes actual leakage (`CONFIRMED_EXPOSURE`) from masked historical/operational
    records (`HISTORICAL_LABEL_EXISTS_BUT_MASKED`) and clean records (`VERIFIED_NO_DETECTED_EXPOSURE`).
    """
    if not inc:
        return (
            "EXPOSURE_UNCERTAIN",
            True,
            "Incident telemetry missing from operational store; exposure telemetry unavailable.",
            {"incident_present": False},
        )

    hist_gt = getattr(inc, "ground_truth", None)
    hist_res = str(getattr(hist_gt, "resolution", "") or "").strip()
    has_hist_label = bool(hist_res)
    has_op_ai = bool(getattr(inc, "ai_verdict", None))
    op_model = str((inc.ai_verdict or {}).get("model_identifier") or "") if has_op_ai else ""
    details = {
        "incident_present": True,
        "has_historical_resolution": has_hist_label,
        "historical_label_masked": True,
        "has_operational_ai_verdict": has_op_ai,
        "operational_ai_model": op_model or None,
        "operational_ai_masked": True,
        "in_learning_records": bool(in_learning),
        "in_other_benchmark_cohort": bool(in_other_cohort),
        "has_prompt_capture": bool(has_prompt_capture),
        "has_unmasked_ai_notes": bool(has_unmasked_ai_notes),
    }

    if in_learning or in_other_cohort:
        reasons = []
        if in_learning:
            reasons.append("Present in LearningRecord/RAG pool")
        if in_other_cohort:
            reasons.append("Overlaps another benchmark cohort")
        return ("CONFIRMED_EXPOSURE", True, "; ".join(reasons), details)

    if has_hist_label or has_op_ai or has_unmasked_ai_notes:
        reasons = []
        if has_hist_label:
            lbl_kind = "ML-generated" if getattr(hist_gt, "is_ml_generated", False) else "Historical SIEM"
            reasons.append(f"{lbl_kind} label present in DB (masked during blind review)")
        if has_op_ai:
            reasons.append(f"Prior operational ai_verdict ({op_model or 'GUARD'}) masked during blind review")
        if has_unmasked_ai_notes:
            reasons.append("Legacy [AI Verdict] handover note sanitized on read")
        return ("HISTORICAL_LABEL_EXISTS_BUT_MASKED", False, "; ".join(reasons), details)

    return (
        "VERIFIED_NO_DETECTED_EXPOSURE",
        False,
        "No historical resolution label, no operational AI verdict, and zero RAG/LearningRecord exposure detected.",
        details,
    )


class GroundTruthCertificationService:
    """Service layer managing frozen benchmark cohorts and blind GT-2/GT-3 certification."""

    @classmethod
    async def ensure_ais_2_6e_cohort_registered(
        cls,
        db: AsyncSession,
        load_from_zip_if_missing: bool = True,
        zip_path: Optional[Path] = None,
    ) -> BenchmarkCohort:
        """
        Idempotently ensures `AIS_2_6E_FROZEN_20` and all 20 frozen CrowdStrike & Prisma SASE
        items are registered. Links existing DB incidents cleanly without overwriting data,
        and imports raw telemetry from `fixtures/Incident json.zip` ONLY for items missing in DB.
        """
        c_res = await db.execute(
            select(BenchmarkCohort).where(BenchmarkCohort.cohort_key == FROZEN_AIS_2_6E_COHORT_ID)
        )
        cohort = c_res.scalar_one_or_none()
        if not cohort:
            cohort = BenchmarkCohort(
                cohort_key=FROZEN_AIS_2_6E_COHORT_ID,
                name=FROZEN_AIS_2_6E_COHORT_NAME,
                description=(
                    "Frozen 20-incident empirical benchmark cohort (10 CrowdStrike + 10 Prisma SASE) "
                    "established in AIS 2.6e, starting with 5 priority pilot incidents."
                ),
                version="2.6e",
                is_frozen=True,
                required_reviewers=2,
                excluded_from_learning=True,
            )
            db.add(cohort)
            await db.flush()

        # Check existing cohort items
        existing_items_res = await db.execute(
            select(BenchmarkCohortItem).where(BenchmarkCohortItem.cohort_id == cohort.id)
        )
        existing_by_fid = {item.fortisiem_incident_id: item for item in existing_items_res.scalars().all()}

        # Index ZIP payloads lazily only if needed
        zip_index: Optional[Dict[str, dict]] = None
        target_zip = zip_path or _DEFAULT_FIXTURE_ZIP

        def _load_zip_payload(fid: str) -> Optional[dict]:
            nonlocal zip_index
            if zip_index is None:
                zip_index = {}
                if load_from_zip_if_missing and target_zip.exists():
                    try:
                        with zipfile.ZipFile(target_zip, "r") as zf:
                            for name in zf.namelist():
                                if not name.lower().endswith(".json"):
                                    continue
                                try:
                                    data = json.loads(zf.read(name).decode("utf-8"))
                                    if isinstance(data, dict):
                                        z_fid = str(data.get("incidentId") or data.get("id") or "").strip()
                                        if z_fid:
                                            zip_index[z_fid] = data
                                except Exception:
                                    continue
                    except Exception as exc:
                        logger.warning(f"Unable to index fixture ZIP {target_zip}: {exc}")
            return zip_index.get(fid)

        for meta in FROZEN_AIS_2_6E_ITEMS:
            fid = meta["fortisiem_incident_id"]
            # Resolve Incident row in DB
            inc_res = await db.execute(
                select(Incident)
                .where(Incident.incident_id == fid)
                .options(selectinload(Incident.events), selectinload(Incident.ground_truth), selectinload(Incident.rule))
            )
            inc = inc_res.scalars().first()

            if not inc and load_from_zip_if_missing:
                raw_json = _load_zip_payload(fid)
                if raw_json:
                    try:
                        from app.services.ingestion_service import IngestionService
                        ing = IngestionService(db)
                        await ing.ingest_single_json(
                            raw_data=raw_json,
                            filename=f"benchmark_seed_{fid}.json",
                            username="system_cohort_seed",
                        )
                        inc_res = await db.execute(
                            select(Incident)
                            .where(Incident.incident_id == fid)
                            .options(
                                selectinload(Incident.events),
                                selectinload(Incident.ground_truth),
                                selectinload(Incident.rule),
                            )
                        )
                        inc = inc_res.scalars().first()
                    except Exception as exc:
                        logger.warning(f"Failed ingesting frozen incident {fid} from fixture ZIP: {exc}")

            # Resolve Rule metadata
            rule_obj = inc.rule if (inc and inc.rule) else None
            if not rule_obj:
                r_res = await db.execute(
                    select(Rule).where(
                        or_(
                            Rule.event_type == meta["event_type"],
                            Rule.rule_id == meta["event_type"],
                        )
                    )
                )
                rule_obj = r_res.scalars().first()

            # Compute deterministic digests
            raw_hash = ""
            canon_hash = ""
            rule_hash = ""
            if inc:
                raw_payload_data = inc.raw_payload or [
                    {
                        "event_id": ev.event_id,
                        "raw_log": ev.raw_log,
                        "attributes": ev.attributes,
                    }
                    for ev in (inc.events or [])
                ]
                raw_hash = _sha256_canonical(raw_payload_data)
                try:
                    norm = EvidenceNormalizationService.normalize_incident_evidence(
                        incident=inc, events=list(inc.events or [])
                    )
                    canon_hash = _sha256_canonical([r.model_dump() for r in norm.records])
                except Exception:
                    canon_hash = raw_hash
            if rule_obj:
                rule_hash = _sha256_canonical({
                    "rule_id": rule_obj.rule_id,
                    "name": rule_obj.name,
                    "description": rule_obj.description,
                    "severity": rule_obj.severity,
                    "pattern_logic": rule_obj.pattern_logic,
                    "parsed_metadata": rule_obj.parsed_metadata,
                    "raw_rule_text": rule_obj.raw_rule_text,
                })

            # Detect pre-existing exposure risk (without modifying historical/ai records!)
            exposure_flag = False
            exposure_reasons: List[str] = []
            if inc:
                if inc.ai_verdict:
                    exposure_flag = True
                    exposure_reasons.append("AI evaluation record present in operational store (masked in UI/API)")
                if inc.ground_truth and inc.ground_truth.resolution:
                    exposure_flag = True
                    lbl_kind = "ML-generated" if inc.ground_truth.is_ml_generated else "Historical SIEM"
                    exposure_reasons.append(f"{lbl_kind} label present in DB (masked during blind review)")
                inv_res = await db.execute(
                    select(Investigation).where(Investigation.incident_id == inc.id)
                )
                inv = inv_res.scalars().first()
                if inv and has_ai_notes_contamination(inv.analyst_notes):
                    exposure_flag = True
                    exposure_reasons.append("Legacy [AI Verdict] handover note on Investigation record (sanitized on read)")

            has_hist_gt = bool(inc and inc.ground_truth and inc.ground_truth.resolution)
            initial_cert_status = "GT1_HISTORICAL_ONLY" if has_hist_gt else "GT0_UNREVIEWED"

            existing = existing_by_fid.get(fid)
            if not existing:
                item = BenchmarkCohortItem(
                    cohort_id=cohort.id,
                    incident_db_id=inc.id if inc else None,
                    fortisiem_incident_id=fid,
                    rule_id=meta["event_type"],
                    rule_name=meta["rule_name"],
                    expected_policy_version_id=meta["approved_prompt_version_id"],
                    expected_policy_prompt_id=meta["approved_rule_prompt_id"],
                    customer=(inc.customer if inc else meta["customer"]) or meta["customer"],
                    is_priority=(meta["priority_tier"] == "PRIORITY_5"),
                    priority_rank=meta["sequence_order"],
                    raw_evidence_sha256=raw_hash,
                    rule_definition_sha256=rule_hash,
                    canonical_evidence_sha256=canon_hash,
                    eligibility_status="ELIGIBLE" if inc else "PENDING_INGEST",
                    certification_status=initial_cert_status,
                    exposure_risk_flag=exposure_flag,
                    exposure_risk_reason="; ".join(exposure_reasons),
                )
                db.add(item)
            else:
                if inc and not existing.incident_db_id:
                    existing.incident_db_id = inc.id
                    existing.eligibility_status = "ELIGIBLE"
                if raw_hash and not existing.raw_evidence_sha256:
                    existing.raw_evidence_sha256 = raw_hash
                if canon_hash and not existing.canonical_evidence_sha256:
                    existing.canonical_evidence_sha256 = canon_hash
                if rule_hash and not existing.rule_definition_sha256:
                    existing.rule_definition_sha256 = rule_hash
                existing.exposure_risk_flag = exposure_flag
                existing.exposure_risk_reason = "; ".join(exposure_reasons)
                # Only upgrade GT0 -> GT1 automatically if no human reviews started yet
                if existing.certification_status == "GT0_UNREVIEWED" and has_hist_gt:
                    existing.certification_status = "GT1_HISTORICAL_ONLY"
                db.add(existing)

        await db.commit()
        await db.refresh(cohort)
        return cohort

    @classmethod
    async def list_cohorts(
        cls, db: AsyncSession, current_user: Any
    ) -> List[CohortSummaryResponse]:
        # Always ensure the frozen AIS 2.6e cohort exists cleanly
        res = await db.execute(
            select(BenchmarkCohort).where(BenchmarkCohort.cohort_key == FROZEN_AIS_2_6E_COHORT_ID)
        )
        cohort = res.scalar_one_or_none()
        if not cohort:
            cohort = await cls.ensure_ais_2_6e_cohort_registered(db)
        else:
            cnt_res = await db.execute(
                select(BenchmarkCohortItem.id).where(BenchmarkCohortItem.cohort_id == cohort.id)
            )
            if len(cnt_res.all()) < 20:
                cohort = await cls.ensure_ais_2_6e_cohort_registered(db)

        all_cohorts = (await db.execute(select(BenchmarkCohort).order_by(BenchmarkCohort.created_at))).scalars().all()
        summaries: List[CohortSummaryResponse] = []
        for c in all_cohorts:
            progress = await cls._build_progress_counters(db, c, current_user)
            summaries.append(
                CohortSummaryResponse(
                    id=c.id,
                    cohort_key=c.cohort_key,
                    name=c.name,
                    description=c.description,
                    version=c.version,
                    is_frozen=c.is_frozen,
                    required_reviewers=c.required_reviewers,
                    excluded_from_learning=c.excluded_from_learning,
                    progress=progress,
                )
            )
        return summaries

    @classmethod
    async def _get_cohort_or_404(cls, db: AsyncSession, cohort_key: str) -> BenchmarkCohort:
        res = await db.execute(
            select(BenchmarkCohort).where(BenchmarkCohort.cohort_key == cohort_key)
        )
        cohort = res.scalar_one_or_none()
        if not cohort and cohort_key == FROZEN_AIS_2_6E_COHORT_ID:
            cohort = await cls.ensure_ais_2_6e_cohort_registered(db)
        if not cohort:
            raise ValueError(f"Benchmark cohort '{cohort_key}' not found.")
        return cohort

    @classmethod
    async def _build_progress_counters(
        cls,
        db: AsyncSession,
        cohort: BenchmarkCohort,
        current_user: Any,
    ) -> CohortProgressCounters:
        items = (
            await db.execute(
                select(BenchmarkCohortItem).where(BenchmarkCohortItem.cohort_id == cohort.id)
            )
        ).scalars().all()

        reviewer_key, user_id, _ = _user_identity(current_user)
        user_keys = {k for k in (reviewer_key, user_id) if k}

        inc_ids = [it.incident_db_id for it in items if it.incident_db_id]
        rev_by_inc: Dict[str, List[AnalystVerdictReview]] = {}
        learned_ids: set = set()
        other_cohort_ids: set = set()
        captured_fids: set = set()
        bench_status_by_fid: Dict[str, str] = {}
        inc_by_id: Dict[str, Incident] = {}

        if inc_ids:
            revs = (
                await db.execute(
                    select(AnalystVerdictReview).where(
                        AnalystVerdictReview.incident_id.in_(inc_ids),
                        AnalystVerdictReview.review_mode == "BENCHMARK_CERTIFICATION",
                    )
                )
            ).scalars().all()
            for r in revs:
                rev_by_inc.setdefault(r.incident_id, []).append(r)

            incs = (
                await db.execute(
                    select(Incident)
                    .where(Incident.id.in_(inc_ids))
                    .options(selectinload(Incident.ground_truth))
                )
            ).scalars().all()
            inc_by_id = {x.id: x for x in incs}
            learned_ids = {
                row[0]
                for row in (
                    await db.execute(
                        select(LearningRecord.incident_id).where(LearningRecord.incident_id.in_(inc_ids))
                    )
                ).all()
            }
            other_cohort_ids = {
                row[0]
                for row in (
                    await db.execute(
                        select(BenchmarkCohortItem.incident_db_id).where(
                            BenchmarkCohortItem.cohort_id != cohort.id,
                            BenchmarkCohortItem.incident_db_id.in_(inc_ids),
                        )
                    )
                ).all()
            }

        try:
            from app.models.ais31_benchmark import AIS31BenchmarkResult, AIS31BenchmarkRun
            latest_run = (
                await db.execute(
                    select(AIS31BenchmarkRun)
                    .where(AIS31BenchmarkRun.cohort_key == cohort.cohort_key)
                    .order_by(desc(AIS31BenchmarkRun.started_at))
                    .limit(1)
                )
            ).scalar_one_or_none()
            if latest_run:
                b_res = (
                    await db.execute(
                        select(AIS31BenchmarkResult).where(AIS31BenchmarkResult.run_id == latest_run.id)
                    )
                ).scalars().all()
                for br in b_res:
                    bench_status_by_fid[br.fortisiem_incident_id] = br.execution_status
        except Exception:
            pass

        p = CohortProgressCounters(
            cohort_key=cohort.cohort_key,
            total=len(items),
            excluded_from_learning=cohort.excluded_from_learning,
        )
        for it in items:
            st = it.certification_status
            if it.is_priority:
                p.priority_total += 1
                if st == "GT3_CERTIFIED":
                    p.priority_certified += 1
                if st in ("GT2_SINGLE_REVIEW", "GT3_CERTIFIED", "CERTIFIED_INCONCLUSIVE"):
                    p.priority_single_reviewed += 1
            else:
                p.remaining_total += 1
                if st == "GT3_CERTIFIED":
                    p.remaining_certified += 1

            if st == "GT0_UNREVIEWED":
                p.gt0_unreviewed += 1
            elif st == "GT1_HISTORICAL_ONLY":
                p.gt1_historical_only += 1
            elif st == "IN_PROGRESS":
                p.in_progress += 1
            elif st == "GT2_SINGLE_REVIEW":
                p.gt2_single_review += 1
            elif st == "CONFLICT_PENDING_ADJUDICATION":
                p.conflict_pending_adjudication += 1
            elif st == "GT3_CERTIFIED":
                p.gt3_certified += 1
            elif st == "CERTIFIED_INCONCLUSIVE":
                p.certified_inconclusive += 1

            inc_obj = inc_by_id.get(it.incident_db_id or "")
            exp_status, exp_flag, _, _ = _classify_item_exposure(
                inc=inc_obj,
                in_learning=(it.incident_db_id in learned_ids) if it.incident_db_id else False,
                in_other_cohort=(it.incident_db_id in other_cohort_ids) if it.incident_db_id else False,
                has_unmasked_ai_notes=False,
                has_prompt_capture=(it.fortisiem_incident_id in captured_fids),
            )
            if exp_status == "VERIFIED_NO_DETECTED_EXPOSURE":
                p.verified_no_exposure_count += 1
            elif exp_status == "HISTORICAL_LABEL_EXISTS_BUT_MASKED":
                p.historical_masked_count += 1
            elif exp_status == "CONFIRMED_EXPOSURE":
                p.confirmed_exposure_count += 1
                p.quarantined_count += 1
            else:
                p.exposure_uncertain_count += 1

            if exp_flag:
                p.exposure_risk_count += 1

            if it.eligibility_status == "ELIGIBLE" and exp_status != "CONFIRMED_EXPOSURE":
                p.benchmark_eligible_count += 1

            b_st = bench_status_by_fid.get(it.fortisiem_incident_id)
            if b_st:
                p.benchmark_executed_count += 1
                if b_st == "COMPLETED":
                    p.benchmark_completed_count += 1

            inc_revs = rev_by_inc.get(it.incident_db_id or "", [])
            for r in inc_revs:
                if r.reviewer_id in user_keys:
                    if r.is_locked:
                        p.my_locked_reviews += 1
                    elif r.is_draft:
                        p.my_draft_reviews += 1

        p.ready_for_priority_benchmark = (
            p.priority_total > 0 and p.priority_certified >= p.priority_total
        )
        p.ready_for_full_benchmark = (
            p.total > 0 and (p.gt3_certified + p.certified_inconclusive) >= p.total
        )
        p.provisional_gt2_benchmark_ready = (
            p.total > 0
            and (p.gt2_single_review + p.gt3_certified + p.certified_inconclusive) >= p.total
            and p.benchmark_eligible_count > 0
        )
        return p

    @classmethod
    async def get_cohort_queue(
        cls,
        db: AsyncSession,
        cohort_key: str,
        current_user: Any,
        priority_only: Optional[bool] = None,
        certification_status: Optional[str] = None,
        vendor: Optional[str] = None,
        customer: Optional[str] = None,
        exposure_risk_only: Optional[bool] = None,
        my_pending_only: bool = False,
        search: Optional[str] = None,
    ) -> GroundTruthQueueResponse:
        cohort = await cls._get_cohort_or_404(db, cohort_key)
        progress = await cls._build_progress_counters(db, cohort, current_user)
        cohort_summary = CohortSummaryResponse(
            id=cohort.id,
            cohort_key=cohort.cohort_key,
            name=cohort.name,
            description=cohort.description,
            version=cohort.version,
            is_frozen=cohort.is_frozen,
            required_reviewers=cohort.required_reviewers,
            excluded_from_learning=cohort.excluded_from_learning,
            progress=progress,
        )

        stmt = (
            select(BenchmarkCohortItem)
            .where(BenchmarkCohortItem.cohort_id == cohort.id)
            .options(
                selectinload(BenchmarkCohortItem.incident).selectinload(Incident.ground_truth),
                selectinload(BenchmarkCohortItem.incident).selectinload(Incident.rule),
            )
            .order_by(BenchmarkCohortItem.priority_rank.asc(), BenchmarkCohortItem.fortisiem_incident_id.asc())
        )
        items = (await db.execute(stmt)).scalars().all()

        reviewer_key, user_id, is_admin = _user_identity(current_user)
        user_keys = {k for k in (reviewer_key, user_id) if k}

        inc_ids = [it.incident_db_id for it in items if it.incident_db_id]
        rev_by_inc: Dict[str, List[AnalystVerdictReview]] = {}
        learned_ids: set = set()
        other_cohort_ids: set = set()
        bench_status_by_fid: Dict[str, str] = {}
        if inc_ids:
            revs = (
                await db.execute(
                    select(AnalystVerdictReview).where(
                        AnalystVerdictReview.incident_id.in_(inc_ids),
                        AnalystVerdictReview.review_mode == "BENCHMARK_CERTIFICATION",
                    )
                )
            ).scalars().all()
            for r in revs:
                rev_by_inc.setdefault(r.incident_id, []).append(r)
            learned_ids = {
                row[0]
                for row in (
                    await db.execute(
                        select(LearningRecord.incident_id).where(LearningRecord.incident_id.in_(inc_ids))
                    )
                ).all()
            }
            other_cohort_ids = {
                row[0]
                for row in (
                    await db.execute(
                        select(BenchmarkCohortItem.incident_db_id).where(
                            BenchmarkCohortItem.cohort_id != cohort.id,
                            BenchmarkCohortItem.incident_db_id.in_(inc_ids),
                        )
                    )
                ).all()
            }

        try:
            from app.models.ais31_benchmark import AIS31BenchmarkResult, AIS31BenchmarkRun
            latest_run = (
                await db.execute(
                    select(AIS31BenchmarkRun)
                    .where(AIS31BenchmarkRun.cohort_key == cohort.cohort_key)
                    .order_by(desc(AIS31BenchmarkRun.started_at))
                    .limit(1)
                )
            ).scalar_one_or_none()
            if latest_run:
                b_res = (
                    await db.execute(
                        select(AIS31BenchmarkResult).where(AIS31BenchmarkResult.run_id == latest_run.id)
                    )
                ).scalars().all()
                for br in b_res:
                    bench_status_by_fid[br.fortisiem_incident_id] = br.execution_status
        except Exception:
            pass

        meta_by_fid = {m["fortisiem_incident_id"]: m for m in FROZEN_AIS_2_6E_ITEMS}
        out_items: List[GroundTruthQueueItem] = []

        for it in items:
            inc = it.incident
            m = meta_by_fid.get(it.fortisiem_incident_id, {})
            item_vendor = _resolve_cohort_item_vendor(
                it.rule_id,
                inc.rule if inc else None,
                m,
            )
            exp_status, exp_flag, exp_reason_calc, exp_details = _classify_item_exposure(
                inc=inc,
                in_learning=(it.incident_db_id in learned_ids) if it.incident_db_id else False,
                in_other_cohort=(it.incident_db_id in other_cohort_ids) if it.incident_db_id else False,
                has_unmasked_ai_notes=False,
                has_prompt_capture=False,
            )
            inc_revs = rev_by_inc.get(it.incident_db_id or "", [])
            locked_revs = [r for r in inc_revs if r.is_locked and r.certification_round == 1]
            my_rev = next((r for r in inc_revs if r.reviewer_id in user_keys), None)

            if my_rev and my_rev.is_locked:
                my_status = "LOCKED"
                my_verdict = my_rev.analyst_verdict
            elif my_rev:
                my_status = "DRAFT"
                my_verdict = my_rev.analyst_verdict
            else:
                my_status = "NOT_STARTED"
                my_verdict = None

            # Apply filters
            if priority_only is True and not it.is_priority:
                continue
            if priority_only is False and it.is_priority:
                continue
            if certification_status and it.certification_status != certification_status:
                continue
            if vendor and item_vendor.lower() != vendor.lower():
                continue
            if customer and (it.customer or "").lower() != customer.lower():
                continue
            if exposure_risk_only is True and not exp_flag:
                continue
            if my_pending_only and my_status == "LOCKED":
                continue
            if search:
                q = search.strip().lower()
                hay = " ".join([
                    it.fortisiem_incident_id or "",
                    it.incident_db_id or "",
                    it.rule_name or "",
                    it.rule_id or "",
                    it.customer or "",
                    item_vendor,
                    inc.title if inc else "",
                    m.get("observed_entity", ""),
                    m.get("target_host", ""),
                ]).lower()
                if q not in hay:
                    continue

            is_cert_done = it.certification_status in ("GT3_CERTIFIED", "CERTIFIED_INCONCLUSIVE")
            out_items.append(
                GroundTruthQueueItem(
                    cohort_item_id=it.id,
                    cohort_key=cohort.cohort_key,
                    fortisiem_incident_id=it.fortisiem_incident_id,
                    incident_db_id=it.incident_db_id,
                    rule_id=it.rule_id,
                    rule_name=it.rule_name,
                    vendor=item_vendor,
                    customer=it.customer,
                    title=inc.title if inc else it.rule_name,
                    observed_entity=m.get("observed_entity") or (inc.source_ip if inc else None),
                    target_host=m.get("target_host") or (inc.reporting_device if inc else None),
                    is_priority=it.is_priority,
                    priority_rank=it.priority_rank,
                    eligibility_status=it.eligibility_status,
                    certification_status=it.certification_status,
                    certified_verdict=it.certified_verdict if is_cert_done else None,
                    locked_reviewers_count=len({r.reviewer_id for r in locked_revs}),
                    my_review_status=my_status,
                    my_review_verdict=my_verdict,
                    exposure_risk_flag=exp_flag,
                    exposure_risk_reason=exp_reason_calc,
                    exposure_status=exp_status,
                    exposure_details=exp_details if is_admin else {},
                    benchmark_status=bench_status_by_fid.get(it.fortisiem_incident_id, "NOT_EXECUTED"),
                    blind_status=(
                        "CERTIFICATION_FINALIZED"
                        if is_cert_done
                        else "BLIND_ENFORCED"
                    ),
                    created_at=it.created_at,
                    updated_at=it.updated_at,
                )
            )

        return GroundTruthQueueResponse(
            cohort=cohort_summary,
            items=out_items,
            total=len(out_items),
        )

    @classmethod
    async def _resolve_cohort_item_and_incident(
        cls,
        db: AsyncSession,
        cohort_key: str,
        incident_identifier: str,
    ) -> Tuple[BenchmarkCohort, BenchmarkCohortItem, Optional[Incident]]:
        cohort = await cls._get_cohort_or_404(db, cohort_key)
        item_res = await db.execute(
            select(BenchmarkCohortItem)
            .where(
                BenchmarkCohortItem.cohort_id == cohort.id,
                or_(
                    BenchmarkCohortItem.fortisiem_incident_id == incident_identifier,
                    BenchmarkCohortItem.incident_db_id == incident_identifier,
                    BenchmarkCohortItem.id == incident_identifier,
                ),
            )
            .options(
                selectinload(BenchmarkCohortItem.incident).selectinload(Incident.events),
                selectinload(BenchmarkCohortItem.incident).selectinload(Incident.rule),
                selectinload(BenchmarkCohortItem.incident).selectinload(Incident.ground_truth),
            )
        )
        item = item_res.scalar_one_or_none()
        if not item:
            raise ValueError(
                f"Incident '{incident_identifier}' is not a member of frozen cohort '{cohort_key}'."
            )
        return cohort, item, item.incident

    @classmethod
    def _build_raw_logs(cls, inc: Optional[Incident]) -> List[RawLogEntry]:
        entries: List[RawLogEntry] = []
        if not inc:
            return entries

        if inc.events:
            for idx, ev in enumerate(inc.events, start=1):
                attrs = ev.attributes if isinstance(ev.attributes, dict) else {}
                ts_str = None
                if ev.event_receive_time:
                    from app.utils.datetime_utils import utc_from_timestamp
                    ep = ev.event_receive_time / 1000.0 if ev.event_receive_time > 1e11 else float(ev.event_receive_time)
                    ts_str = utc_from_timestamp(ep).isoformat()
                elif attrs.get("eventTime"):
                    ts_str = str(attrs.get("eventTime"))
                elif ev.created_at:
                    ts_str = ev.created_at.isoformat()
                entries.append(
                    RawLogEntry(
                        index=idx,
                        event_id=ev.event_id,
                        event_type=ev.event_type or inc.event_type,
                        timestamp=ts_str,
                        source_ip=attrs.get("srcIpAddr") or attrs.get("source_ip") or inc.source_ip,
                        destination_ip=attrs.get("destIpAddr") or attrs.get("destination_ip") or attrs.get("destIp"),
                        host=attrs.get("hostName") or attrs.get("compName") or attrs.get("host") or inc.reporting_device,
                        process_name=attrs.get("procName") or attrs.get("processName") or attrs.get("process"),
                        file_name=attrs.get("fileName") or attrs.get("targetFile"),
                        command_line=attrs.get("command") or attrs.get("cmdLine"),
                        raw_log=ev.raw_log or json.dumps(attrs, default=str),
                        parsed_attributes=attrs,
                    )
                )
        elif inc.raw_payload:
            raw_list = inc.raw_payload if isinstance(inc.raw_payload, list) else [inc.raw_payload]
            for idx, r in enumerate(raw_list, start=1):
                if isinstance(r, dict):
                    attrs = r.get("attribute") or r.get("attributes") or r
                    entries.append(
                        RawLogEntry(
                            index=idx,
                            event_id=str(r.get("eventId") or r.get("id") or f"raw-{idx}"),
                            event_type=inc.event_type,
                            source_ip=attrs.get("srcIpAddr") or inc.source_ip,
                            host=attrs.get("hostName") or inc.reporting_device,
                            process_name=attrs.get("procName"),
                            file_name=attrs.get("fileName"),
                            command_line=attrs.get("command"),
                            raw_log=str(attrs.get("rawMessage") or json.dumps(r, default=str)),
                            parsed_attributes=attrs if isinstance(attrs, dict) else {},
                        )
                    )
                else:
                    entries.append(RawLogEntry(index=idx, raw_log=str(r), event_type=inc.event_type))
        return entries

    @classmethod
    def _review_to_summary(cls, rev: AnalystVerdictReview) -> ReviewerSubmissionSummary:
        return ReviewerSubmissionSummary(
            review_id=rev.id,
            reviewer_id=rev.reviewer_id,
            analyst_verdict=rev.analyst_verdict,
            detection_correctness=rev.detection_correctness,
            authorization_context=rev.authorization_context,
            confidence_level=rev.confidence_level,
            evidence_sufficiency_status=rev.evidence_sufficiency_status,
            analyst_notes=rev.analyst_notes,
            evidence_references=list(rev.evidence_references or []),
            additional_evidence_json=list(rev.additional_evidence_json or []),
            attestation_flags=dict(rev.attestation_flags or {}),
            is_locked=bool(rev.is_locked),
            is_draft=bool(rev.is_draft),
            certification_round=int(rev.certification_round or 1),
            certification_version=int(rev.review_version or 1),
            created_at=rev.created_at,
        )

    @classmethod
    async def get_incident_detail(
        cls,
        db: AsyncSession,
        cohort_key: str,
        incident_identifier: str,
        current_user: Any,
    ) -> GroundTruthDetailResponse:
        """
        Returns strictly blind investigation detail for human ground truth certification:
        ONLY original incident telemetry, triggered rule definition, normalized factual evidence,
        additional investigation evidence, and the reviewer's OWN draft/locked review.
        AI predictions, confidence scores, and historical FortiSIEM resolutions are NEVER returned
        during active review.
        """
        cohort, item, inc = await cls._resolve_cohort_item_and_incident(
            db, cohort_key, incident_identifier
        )
        reviewer_key, user_id, is_admin = _user_identity(current_user)
        user_keys = {k for k in (reviewer_key, user_id) if k}

        meta = next((m for m in FROZEN_AIS_2_6E_ITEMS if m["fortisiem_incident_id"] == item.fortisiem_incident_id), {})

        # Resolve Rule definition
        rule = inc.rule if (inc and inc.rule) else None
        if not rule:
            r_res = await db.execute(
                select(Rule).where(or_(Rule.event_type == item.rule_id, Rule.rule_id == item.rule_id))
            )
            rule = r_res.scalars().first()

        # Policy metadata (version reference ONLY; NEVER prompt feedback/AI labels)
        approved_ver_num = None
        if item.expected_policy_version_id:
            pv_res = await db.execute(
                select(PromptVersion.version_number).where(PromptVersion.id == item.expected_policy_version_id)
            )
            approved_ver_num = pv_res.scalar_one_or_none()

        rule_spec = (
            {
                "rule_id": rule.rule_id,
                "name": rule.name,
                "event_type": rule.event_type,
                "severity": rule.severity,
                "data_source": rule.data_source,
                "detection_tech": rule.detection_tech,
                "evaluation_mode": rule.evaluation_mode,
                "pattern_logic": rule.pattern_logic,
                "remediation": rule.remediation,
                "parsed_metadata": rule.parsed_metadata or {},
                "raw_rule_text": rule.raw_rule_text,
            }
            if rule
            else {}
        )
        cond_summary = (
            (rule.pattern_logic if rule else "")
            or (rule.description if rule else "")
            or (rule.raw_rule_text if rule else "")
            or f"Triggered rule: {item.rule_name} ({item.rule_id})"
        )
        rule_view = RuleDefinitionView(
            rule_id=item.rule_id,
            rule_name=rule.name if rule else item.rule_name,
            category=meta.get("vendor") or (rule.detection_tech if rule else ""),
            severity=(inc.severity if inc else None) or (rule.severity if rule else "MEDIUM"),
            description=(rule.description if rule else "") or f"FortiSIEM Detection Rule {item.rule_id}",
            condition_summary=str(cond_summary),
            rule_definition_sha256=item.rule_definition_sha256 or "",
            approved_policy_version_id=item.expected_policy_version_id,
            approved_policy_version_number=approved_ver_num or 1,
            raw_rule_spec=rule_spec,
        )

        # Raw logs & normalized canonical evidence (strictly zero AI / ground-truth fields!)
        raw_logs = cls._build_raw_logs(inc)
        norm_records: List[Dict[str, Any]] = []
        if inc:
            try:
                norm_res = EvidenceNormalizationService.normalize_incident_evidence(
                    incident=inc, events=list(inc.events or [])
                )
                norm_records = [r.model_dump() for r in norm_res.records]
            except Exception as exc:
                logger.warning(f"Normalization fallback for {item.fortisiem_incident_id}: {exc}")

        # Additional manual investigation evidence (from InvestigationEvidence, filtered to non-AI entries)
        additional_ev: List[Dict[str, Any]] = []
        if inc:
            inv_res = await db.execute(
                select(Investigation)
                .where(Investigation.incident_id == inc.id)
                .options(selectinload(Investigation.evidence_items))
            )
            inv = inv_res.scalars().first()
            if inv:
                for ev in inv.evidence_items:
                    additional_ev.append({
                        "id": ev.id,
                        "evidence_type": ev.evidence_type,
                        "reference_key": ev.reference_key,
                        "evidence_content": ev.evidence_content,
                        "analyst_rationale": ev.analyst_rationale,
                        "created_at": ev.created_at.isoformat() if ev.created_at else None,
                    })

        # Reviews in BENCHMARK_CERTIFICATION mode
        inc_revs: List[AnalystVerdictReview] = []
        if inc:
            rev_res = await db.execute(
                select(AnalystVerdictReview)
                .where(
                    AnalystVerdictReview.incident_id == inc.id,
                    AnalystVerdictReview.review_mode == "BENCHMARK_CERTIFICATION",
                )
                .order_by(AnalystVerdictReview.created_at.asc())
            )
            inc_revs = rev_res.scalars().all()

        locked_revs = [r for r in inc_revs if r.is_locked and r.certification_round == 1]
        my_rev = next((r for r in inc_revs if r.reviewer_id in user_keys), None)
        locked_distinct_reviewers = {r.reviewer_id for r in locked_revs}
        other_locked = [r for r in locked_revs if r.reviewer_id not in user_keys]

        can_submit_lock = True
        lock_blocked_reason = None
        can_unlock_my_review = False
        unlock_blocked_reason = None
        if my_rev and my_rev.is_locked:
            can_submit_lock = False
            lock_blocked_reason = (
                "You have already locked an independent review for this incident. "
                "Self-approval for Dual-Reviewer GT-3 requires a second distinct reviewer."
            )
            is_finalized_or_conflict = item.certification_status in (
                "GT3_CERTIFIED",
                "CERTIFIED_INCONCLUSIVE",
                "CONFLICT_PENDING_ADJUDICATION",
            )
            if is_finalized_or_conflict and not is_admin:
                can_unlock_my_review = False
                unlock_blocked_reason = (
                    "This incident has reached dual-reviewer conflict or GT-3 certification; "
                    "an Administrator must unlock your review."
                )
            else:
                can_unlock_my_review = True
        elif len(locked_distinct_reviewers) >= 2 and not (my_rev and my_rev.is_locked):
            can_submit_lock = False
            lock_blocked_reason = "Dual-reviewer quorum already locked for this incident."

        is_cert_done = item.certification_status in ("GT3_CERTIFIED", "CERTIFIED_INCONCLUSIVE")
        is_conflict = item.certification_status == "CONFLICT_PENDING_ADJUDICATION"

        # Adjudication allowed only for Admins / Senior Analysts NOT among the conflicting reviewers
        can_adjudicate = bool(is_conflict and is_admin and not (user_keys & locked_distinct_reviewers))
        conflict_reviews: List[ReviewerSubmissionSummary] = []
        if (is_conflict and is_admin) or is_cert_done:
            conflict_reviews = [cls._review_to_summary(r) for r in locked_revs]

        certified_result = None
        if is_cert_done:
            certified_result = {
                "certification_status": item.certification_status,
                "certified_verdict": item.certified_verdict,
                "certified_at": item.updated_at.isoformat() if item.updated_at else None,
                "distinct_reviewers": len(locked_distinct_reviewers),
                "post_certification_comparison_unlocked": True,
            }

        # Revision audit history
        rev_ids = [r.id for r in inc_revs]
        revisions: List[Dict[str, Any]] = []
        if rev_ids:
            revs_hist = (
                await db.execute(
                    select(BenchmarkReviewRevision)
                    .where(BenchmarkReviewRevision.review_id.in_(rev_ids))
                    .order_by(desc(BenchmarkReviewRevision.created_at))
                )
            ).scalars().all()
            revisions = [
                {
                    "id": h.id,
                    "review_id": h.review_id,
                    "previous_verdict": h.previous_verdict,
                    "new_verdict": h.new_verdict,
                    "revised_by_user_id": h.revised_by_user_id,
                    "revision_reason": h.revision_reason,
                    "created_at": h.created_at.isoformat() if h.created_at else None,
                }
                for h in revs_hist
            ]

        in_learning = False
        in_other_cohort = False
        if inc:
            in_learning = (
                await db.execute(
                    select(LearningRecord.id).where(LearningRecord.incident_id == inc.id).limit(1)
                )
            ).scalar_one_or_none() is not None
            in_other_cohort = (
                await db.execute(
                    select(BenchmarkCohortItem.id)
                    .where(
                        BenchmarkCohortItem.cohort_id != cohort.id,
                        BenchmarkCohortItem.incident_db_id == inc.id,
                    )
                    .limit(1)
                )
            ).scalar_one_or_none() is not None

        exp_status, exp_flag, exp_reason_calc, exp_details = _classify_item_exposure(
            inc=inc,
            in_learning=in_learning,
            in_other_cohort=in_other_cohort,
            has_unmasked_ai_notes=False,
            has_prompt_capture=False,
        )

        q_item = GroundTruthQueueItem(
            cohort_item_id=item.id,
            cohort_key=cohort.cohort_key,
            fortisiem_incident_id=item.fortisiem_incident_id,
            incident_db_id=item.incident_db_id,
            rule_id=item.rule_id,
            rule_name=item.rule_name,
            vendor=_resolve_cohort_item_vendor(item.rule_id, rule, meta),
            customer=item.customer,
            title=inc.title if inc else item.rule_name,
            observed_entity=meta.get("observed_entity") or (inc.source_ip if inc else None),
            target_host=meta.get("target_host") or (inc.reporting_device if inc else None),
            is_priority=item.is_priority,
            priority_rank=item.priority_rank,
            eligibility_status=item.eligibility_status,
            certification_status=item.certification_status,
            certified_verdict=item.certified_verdict if is_cert_done else None,
            locked_reviewers_count=len(locked_distinct_reviewers),
            my_review_status="LOCKED" if (my_rev and my_rev.is_locked) else ("DRAFT" if my_rev else "NOT_STARTED"),
            my_review_verdict=my_rev.analyst_verdict if my_rev else None,
            exposure_risk_flag=exp_flag,
            exposure_risk_reason=exp_reason_calc,
            exposure_status=exp_status,
            exposure_details=exp_details if is_admin else {},
            blind_status="CERTIFICATION_FINALIZED" if is_cert_done else "BLIND_ENFORCED",
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

        incident_overview = {
            "fortisiem_incident_id": item.fortisiem_incident_id,
            "incident_db_id": inc.id if inc else None,
            "customer": item.customer,
            "title": inc.title if inc else item.rule_name,
            "description": inc.description if inc else "",
            "severity": inc.severity if inc else "MEDIUM",
            "category": (inc.category if inc else None) or meta.get("vendor") or "",
            "event_type": item.rule_id,
            "reporting_device": inc.reporting_device if inc else meta.get("target_host"),
            "source_ip": inc.source_ip if inc else None,
            "observed_entity": meta.get("observed_entity"),
            "target_host": meta.get("target_host"),
            "created_at_utc": inc.created_at.isoformat() if (inc and inc.created_at) else None,
            "event_count": len(raw_logs),
        }

        return GroundTruthDetailResponse(
            cohort_item=q_item,
            incident_overview=incident_overview,
            rule_definition=rule_view,
            raw_logs=raw_logs,
            normalized_evidence=norm_records,
            additional_evidence=additional_ev,
            raw_evidence_sha256=item.raw_evidence_sha256 or "",
            canonical_evidence_sha256=item.canonical_evidence_sha256 or "",
            blind_review_guarantees={
                "ai_verdict_hidden": True,
                "ai_confidence_hidden": True,
                "historical_fortisiem_label_hidden": True,
                "sibling_reviewer_verdict_hidden": not is_cert_done and not (is_conflict and is_admin),
                "excluded_from_learning_and_rag": True,
            },
            my_review=cls._review_to_summary(my_rev) if my_rev else None,
            locked_reviewers_count=len(locked_distinct_reviewers),
            other_reviewer_submitted=len(other_locked) > 0,
            can_submit_lock=can_submit_lock,
            lock_blocked_reason=lock_blocked_reason,
            can_unlock_my_review=can_unlock_my_review,
            unlock_blocked_reason=unlock_blocked_reason,
            can_adjudicate=can_adjudicate,
            conflict_reviews=conflict_reviews,
            certified_result=certified_result,
            revisions=revisions,
        )

    @classmethod
    async def attach_additional_evidence(
        cls,
        db: AsyncSession,
        cohort_key: str,
        incident_identifier: str,
        req: AdditionalEvidenceInput,
        current_user: Any,
    ) -> Dict[str, Any]:
        cohort, item, inc = await cls._resolve_cohort_item_and_incident(
            db, cohort_key, incident_identifier
        )
        if not inc:
            raise ValueError("Incident telemetry record must be present before attaching evidence.")

        inv_res = await db.execute(select(Investigation).where(Investigation.incident_id == inc.id))
        inv = inv_res.scalars().first()
        if not inv:
            inv = Investigation(incident_id=inc.id, status="IN_PROGRESS")
            db.add(inv)
            await db.flush()

        ev = InvestigationEvidence(
            investigation_id=inv.id,
            evidence_type=req.evidence_type.upper().strip(),
            reference_key=req.reference_key.strip(),
            evidence_content=req.evidence_content.strip(),
            analyst_rationale=req.analyst_rationale.strip(),
        )
        db.add(ev)
        await db.commit()
        await db.refresh(ev)
        return {
            "id": ev.id,
            "evidence_type": ev.evidence_type,
            "reference_key": ev.reference_key,
            "evidence_content": ev.evidence_content,
            "analyst_rationale": ev.analyst_rationale,
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
        }

    @staticmethod
    def _recompute_item_and_investigation_state(
        db: AsyncSession,
        item: BenchmarkCohortItem,
        inv: Optional[Investigation],
        all_locked: List[AnalystVerdictReview],
    ) -> Dict[str, AnalystVerdictReview]:
        """Recomputes BenchmarkCohortItem and Investigation status from locked round-1 reviews."""
        distinct_reviewers = {r.reviewer_id: r for r in all_locked}

        if len(distinct_reviewers) == 0:
            item.certification_status = "IN_PROGRESS"
            item.assigned_reviewer_1 = None
            item.assigned_reviewer_2 = None
            item.certified_verdict = None
        elif len(distinct_reviewers) == 1:
            only_rev = next(iter(distinct_reviewers.values()))
            item.certification_status = "GT2_SINGLE_REVIEW"
            item.assigned_reviewer_1 = only_rev.reviewer_id
            item.assigned_reviewer_2 = None
            item.certified_verdict = None
            only_rev.ground_truth_status = "GT2_SINGLE_REVIEW"
            db.add(only_rev)
        else:
            rev_list = list(distinct_reviewers.values())
            item.assigned_reviewer_1 = rev_list[0].reviewer_id
            item.assigned_reviewer_2 = rev_list[1].reviewer_id
            verdicts = {r.analyst_verdict for r in rev_list[:2]}
            if len(verdicts) == 1:
                agreed_v = next(iter(verdicts))
                if agreed_v == "INCONCLUSIVE":
                    item.certification_status = "CERTIFIED_INCONCLUSIVE"
                    item.certified_verdict = "INCONCLUSIVE"
                else:
                    item.certification_status = "GT3_CERTIFIED"
                    item.certified_verdict = agreed_v
                for r in rev_list[:2]:
                    r.ground_truth_status = item.certification_status
                    db.add(r)
            else:
                item.certification_status = "CONFLICT_PENDING_ADJUDICATION"
                item.certified_verdict = None
                for r in rev_list[:2]:
                    r.ground_truth_status = "CONFLICT"
                    db.add(r)

        item.updated_at = utc_now()
        db.add(item)

        if inv:
            if item.certification_status in ("GT3_CERTIFIED", "CERTIFIED_INCONCLUSIVE"):
                inv.status = "REVIEWED"
                inv.analyst_verdict = item.certified_verdict
                inv.is_independently_verified = item.certified_verdict in ("TRUE_POSITIVE", "FALSE_POSITIVE")
                inv.is_disputed = False
            elif item.certification_status == "CONFLICT_PENDING_ADJUDICATION":
                inv.status = "IN_PROGRESS"
                inv.analyst_verdict = None
                inv.is_independently_verified = False
                inv.is_disputed = True
            else:
                inv.status = "IN_PROGRESS"
                inv.analyst_verdict = None
                inv.is_independently_verified = False
                inv.is_disputed = False
            db.add(inv)

        return distinct_reviewers

    @classmethod
    async def submit_or_save_review(
        cls,
        db: AsyncSession,
        cohort_key: str,
        incident_identifier: str,
        req: GroundTruthReviewSubmitRequest,
        current_user: Any,
    ) -> Dict[str, Any]:
        """
        Saves a DRAFT or submits & LOCKS an independent blind human ground-truth review.
        Strictly enforces:
        - Attestations and minimum rationale on LOCK
        - Self-approval / duplicate reviewer lock block (409 ValueError)
        - Dual-reviewer agreement -> GT3_CERTIFIED (or CERTIFIED_INCONCLUSIVE)
        - Disagreement -> CONFLICT_PENDING_ADJUDICATION
        - ZERO writes to LearningRecord!
        """
        cohort, item, inc = await cls._resolve_cohort_item_and_incident(
            db, cohort_key, incident_identifier
        )
        if not inc:
            raise ValueError("Incident record is not available in database.")

        reviewer_key, user_id, _ = _user_identity(current_user)
        user_keys = {k for k in (reviewer_key, user_id) if k}

        existing_revs = (
            await db.execute(
                select(AnalystVerdictReview).where(
                    AnalystVerdictReview.incident_id == inc.id,
                    AnalystVerdictReview.review_mode == "BENCHMARK_CERTIFICATION",
                    AnalystVerdictReview.certification_round == 1,
                )
            )
        ).scalars().all()

        my_rev = next((r for r in existing_revs if r.reviewer_id in user_keys), None)
        locked_others = [r for r in existing_revs if r.is_locked and r.reviewer_id not in user_keys]

        if my_rev and my_rev.is_locked:
            raise PermissionError(
                "DUPLICATE_OR_LOCKED_REVIEW: Your independent review for this benchmark incident is already locked. "
                "A second distinct reviewer must complete GT-3 dual verification."
            )

        is_lock = req.mode == "LOCK"
        if is_lock:
            if len(locked_others) >= 2:
                raise PermissionError(
                    "CERTIFICATION_QUORUM_REACHED: Two distinct reviewers have already locked reviews for this incident."
                )
            att = req.attestation_flags
            if not (att.evidence_reviewed and att.no_ai_or_historical_influence and att.independent_judgment):
                raise ValueError(
                    "All three blind-review attestations must be confirmed before locking your ground truth verdict."
                )
            if len((req.rationale or "").strip()) < 15:
                raise ValueError(
                    "Please enter an evidence-grounded rationale (at least 15 characters) before locking."
                )

        # Ensure Investigation row exists without injecting AI or GT labels
        inv_res = await db.execute(select(Investigation).where(Investigation.incident_id == inc.id))
        inv = inv_res.scalars().first()
        if not inv:
            inv = Investigation(
                incident_id=inc.id,
                status="IN_PROGRESS",
            )
            db.add(inv)
            await db.flush()

        ev_refs = [x.strip() for x in (req.evidence_references or []) if x and x.strip()]
        add_ev_payload = [e.model_dump() for e in (req.additional_evidence or [])]
        att_dict = req.attestation_flags.model_dump()

        if not my_rev:
            my_rev = AnalystVerdictReview(
                incident_id=inc.id,
                investigation_id=inv.id,
                rule_id=item.rule_id,
                customer=item.customer,
                reviewer_id=reviewer_key,
                analyst_verdict=req.human_verdict,
                analyst_notes=(req.rationale or "").strip(),
                evidence_references=ev_refs,
                blind_mode_active=True,
                revealed_ai_verdict=None,  # Strict blind isolation: do NOT populate pre-cert
                comparison_outcome=None,
                ground_truth_status="DRAFT" if not is_lock else "GT2_SINGLE_REVIEW",
                benchmark_cohort_id=cohort.id,
                certification_round=1,
                review_mode="BENCHMARK_CERTIFICATION",
                detection_correctness=req.detection_correctness,
                authorization_context=req.authorization_context,
                confidence_level=req.confidence_level,
                evidence_sufficiency_status=req.evidence_sufficiency_status,
                evidence_snapshot_hash=item.canonical_evidence_sha256 or item.raw_evidence_sha256,
                rule_snapshot_hash=item.rule_definition_sha256,
                additional_evidence_json=add_ev_payload,
                attestation_flags=att_dict,
                is_locked=is_lock,
                is_draft=not is_lock,
                exposure_risk_flag=item.exposure_risk_flag,
                excluded_from_learning=True,
            )
            db.add(my_rev)
            await db.flush()
        else:
            my_rev.analyst_verdict = req.human_verdict
            my_rev.analyst_notes = (req.rationale or "").strip()
            my_rev.evidence_references = ev_refs
            my_rev.detection_correctness = req.detection_correctness
            my_rev.authorization_context = req.authorization_context
            my_rev.confidence_level = req.confidence_level
            my_rev.evidence_sufficiency_status = req.evidence_sufficiency_status
            my_rev.evidence_snapshot_hash = item.canonical_evidence_sha256 or item.raw_evidence_sha256
            my_rev.rule_snapshot_hash = item.rule_definition_sha256
            my_rev.additional_evidence_json = add_ev_payload
            my_rev.attestation_flags = att_dict
            my_rev.is_locked = is_lock
            my_rev.is_draft = not is_lock
            my_rev.excluded_from_learning = True
            my_rev.review_version = int(my_rev.review_version or 1) + 1
            if is_lock:
                my_rev.ground_truth_status = "GT2_SINGLE_REVIEW"
            db.add(my_rev)

        # Recompute certification state across all locked reviewers for round 1
        all_locked = list(locked_others) + ([my_rev] if is_lock else [])
        distinct_reviewers = cls._recompute_item_and_investigation_state(
            db, item, inv, all_locked
        )

        # Immutable audit trail
        db.add(
            AuditLog(
                user_id=user_id or reviewer_key,
                username=reviewer_key,
                action="BENCHMARK_GT_REVIEW_LOCKED" if is_lock else "BENCHMARK_GT_DRAFT_SAVED",
                resource_type="BENCHMARK_COHORT_ITEM",
                resource_id=item.fortisiem_incident_id,
                details={
                    "cohort_key": cohort.cohort_key,
                    "certification_status": item.certification_status,
                    "reviewer": reviewer_key,
                    "is_locked": is_lock,
                    "excluded_from_learning": True,
                },
            )
        )

        await db.commit()
        return {
            "success": True,
            "mode": req.mode,
            "review_id": my_rev.id,
            "certification_status": item.certification_status,
            "certified_verdict": (
                item.certified_verdict
                if item.certification_status in ("GT3_CERTIFIED", "CERTIFIED_INCONCLUSIVE")
                else None
            ),
            "locked_reviewers_count": len(distinct_reviewers),
            "excluded_from_learning": True,
        }

    @classmethod
    async def unlock_review(
        cls,
        db: AsyncSession,
        cohort_key: str,
        incident_identifier: str,
        req: GroundTruthUnlockRequest,
        current_user: Any,
    ) -> Dict[str, Any]:
        """
        Unlocks a locked blind review back to DRAFT so the reviewer can correct mistakes.
        Option 1 policy:
        - Any reviewer (SOC Analyst or Admin) may unlock their own locked review while
          the incident has not yet reached conflict or GT-3 certification.
        - Administrators may unlock even after conflict or GT-3 certification, and may
          optionally target a specific `review_id`.
        """
        cohort, item, inc = await cls._resolve_cohort_item_and_incident(
            db, cohort_key, incident_identifier
        )
        if not inc:
            raise ValueError("Incident record is not available in database.")

        reviewer_key, user_id, is_admin = _user_identity(current_user)
        user_keys = {k for k in (reviewer_key, user_id) if k}

        existing_revs = (
            await db.execute(
                select(AnalystVerdictReview).where(
                    AnalystVerdictReview.incident_id == inc.id,
                    AnalystVerdictReview.review_mode == "BENCHMARK_CERTIFICATION",
                    AnalystVerdictReview.certification_round == 1,
                )
            )
        ).scalars().all()

        if req.review_id:
            target_rev = next((r for r in existing_revs if r.id == req.review_id), None)
            if not target_rev:
                raise ValueError(f"Review '{req.review_id}' not found for this incident.")
            if target_rev.reviewer_id not in user_keys and not is_admin:
                raise PermissionError("Only Administrators may unlock another reviewer's locked review.")
        else:
            target_rev = next((r for r in existing_revs if r.reviewer_id in user_keys), None)
            if not target_rev:
                raise ValueError("No review found for your account on this incident.")

        if not target_rev.is_locked:
            raise ValueError("This review is already unlocked in draft state.")

        prev_cert_status = item.certification_status
        is_finalized_or_conflict = prev_cert_status in (
            "GT3_CERTIFIED",
            "CERTIFIED_INCONCLUSIVE",
            "CONFLICT_PENDING_ADJUDICATION",
        )
        if is_finalized_or_conflict and not is_admin:
            raise PermissionError(
                "UNLOCK_REQUIRES_ADMIN: This incident has already reached dual-reviewer conflict or GT-3 "
                "certification. An Administrator must unlock your review to preserve blind-review integrity."
            )

        reason = (req.reason or "").strip()
        if len(reason) < 5:
            raise ValueError("Please provide an unlock reason of at least 5 characters.")

        # Record immutable revision history for auditability
        revision = BenchmarkReviewRevision(
            review_id=target_rev.id,
            incident_id=target_rev.incident_id,
            previous_verdict=target_rev.analyst_verdict,
            new_verdict="UNLOCKED_TO_DRAFT",
            previous_rationale=target_rev.analyst_notes,
            new_rationale=target_rev.analyst_notes,
            revised_by_user_id=reviewer_key,
            revision_reason=f"[UNLOCKED] {reason}",
        )
        db.add(revision)

        # If unlocking out of an adjudicated state, clear stale adjudication rows so future re-adjudication won't conflict
        if prev_cert_status in ("GT3_CERTIFIED", "CERTIFIED_INCONCLUSIVE"):
            rev_ids = [r.id for r in existing_revs]
            if rev_ids:
                stale_adjs = (
                    await db.execute(
                        select(AnalystReviewAdjudication).where(
                            AnalystReviewAdjudication.review_id.in_(rev_ids)
                        )
                    )
                ).scalars().all()
                for adj in stale_adjs:
                    await db.delete(adj)

        # Revert target review to editable DRAFT
        target_rev.is_locked = False
        target_rev.is_draft = True
        target_rev.ground_truth_status = "DRAFT"
        target_rev.correction_reason = reason[:64]
        target_rev.review_version = int(target_rev.review_version or 1) + 1
        db.add(target_rev)

        inv_res = await db.execute(select(Investigation).where(Investigation.incident_id == inc.id))
        inv = inv_res.scalars().first()

        remaining_locked = [r for r in existing_revs if r.is_locked and r.id != target_rev.id]
        distinct_reviewers = cls._recompute_item_and_investigation_state(
            db, item, inv, remaining_locked
        )
        item.certification_version = int(item.certification_version or 1) + 1
        db.add(item)

        db.add(
            AuditLog(
                user_id=user_id or reviewer_key,
                username=reviewer_key,
                action="BENCHMARK_GT_REVIEW_UNLOCKED",
                resource_type="BENCHMARK_COHORT_ITEM",
                resource_id=item.fortisiem_incident_id,
                details={
                    "cohort_key": cohort.cohort_key,
                    "review_id": target_rev.id,
                    "reviewer": target_rev.reviewer_id,
                    "unlocked_by": reviewer_key,
                    "previous_certification_status": prev_cert_status,
                    "new_certification_status": item.certification_status,
                    "reason": reason,
                    "excluded_from_learning": True,
                },
            )
        )

        await db.commit()
        return {
            "success": True,
            "review_id": target_rev.id,
            "is_locked": False,
            "is_draft": True,
            "certification_status": item.certification_status,
            "locked_reviewers_count": len(distinct_reviewers),
            "revision_id": revision.id,
            "excluded_from_learning": True,
        }

    @classmethod
    async def adjudicate_conflict(
        cls,
        db: AsyncSession,
        cohort_key: str,
        incident_identifier: str,
        req: GroundTruthAdjudicateRequest,
        current_user: Any,
    ) -> Dict[str, Any]:
        cohort, item, inc = await cls._resolve_cohort_item_and_incident(
            db, cohort_key, incident_identifier
        )
        if not inc:
            raise ValueError("Incident record not found.")

        reviewer_key, user_id, is_admin = _user_identity(current_user)
        if not is_admin:
            raise PermissionError("Only Senior Analysts / Administrators may adjudicate dual-reviewer conflicts.")

        revs = (
            await db.execute(
                select(AnalystVerdictReview).where(
                    AnalystVerdictReview.incident_id == inc.id,
                    AnalystVerdictReview.review_mode == "BENCHMARK_CERTIFICATION",
                    AnalystVerdictReview.is_locked.is_(True),
                )
            )
        ).scalars().all()
        if not revs:
            raise ValueError("No locked reviews exist to adjudicate.")

        prior_reviewers = {r.reviewer_id for r in revs}
        if {reviewer_key, user_id} & prior_reviewers:
            raise PermissionError(
                "INDEPENDENT_ADJUDICATION_REQUIRED: A reviewer cannot adjudicate their own conflicting review."
            )

        primary_rev = revs[0]
        adjudication = AnalystReviewAdjudication(
            review_id=primary_rev.id,
            incident_id=inc.id,
            adjudicator_user_id=reviewer_key,
            final_verdict=req.final_verdict,
            adjudication_rationale=req.rationale.strip(),
            original_dispute_reason="Dual-reviewer disagreement during GT-3 benchmark certification",
        )
        db.add(adjudication)

        new_cert_status = "CERTIFIED_INCONCLUSIVE" if req.final_verdict == "INCONCLUSIVE" else "GT3_CERTIFIED"
        item.certification_status = new_cert_status
        item.certified_verdict = req.final_verdict
        item.updated_at = utc_now()
        db.add(item)

        for r in revs:
            r.ground_truth_status = new_cert_status
            db.add(r)

        inv_res = await db.execute(select(Investigation).where(Investigation.incident_id == inc.id))
        inv = inv_res.scalars().first()
        if inv:
            inv.status = "REVIEWED"
            inv.analyst_verdict = req.final_verdict
            inv.verdict_reason = req.rationale.strip()
            inv.is_disputed = False
            inv.is_independently_verified = req.final_verdict in ("TRUE_POSITIVE", "FALSE_POSITIVE")
            db.add(inv)

        db.add(
            AuditLog(
                user_id=user_id or reviewer_key,
                username=reviewer_key,
                action="BENCHMARK_GT_CONFLICT_ADJUDICATED",
                resource_type="BENCHMARK_COHORT_ITEM",
                resource_id=item.fortisiem_incident_id,
                details={
                    "cohort_key": cohort.cohort_key,
                    "final_verdict": req.final_verdict,
                    "certification_status": new_cert_status,
                    "excluded_from_learning": True,
                },
            )
        )
        await db.commit()
        return {
            "success": True,
            "adjudication_id": adjudication.id,
            "certification_status": new_cert_status,
            "certified_verdict": req.final_verdict,
            "excluded_from_learning": True,
        }

    @classmethod
    async def reopen_and_revise_review(
        cls,
        db: AsyncSession,
        cohort_key: str,
        req: GroundTruthReopenRequest,
        current_user: Any,
    ) -> Dict[str, Any]:
        cohort = await cls._get_cohort_or_404(db, cohort_key)
        reviewer_key, user_id, is_admin = _user_identity(current_user)
        if not is_admin:
            raise PermissionError("Only Administrators may reopen locked certification reviews.")

        rev = (
            await db.execute(
                select(AnalystVerdictReview).where(AnalystVerdictReview.id == req.review_id)
            )
        ).scalar_one_or_none()
        if not rev:
            raise ValueError(f"Review '{req.review_id}' not found.")

        revision = BenchmarkReviewRevision(
            review_id=rev.id,
            incident_id=rev.incident_id,
            previous_verdict=rev.analyst_verdict,
            new_verdict=req.new_verdict,
            previous_rationale=rev.analyst_notes,
            new_rationale=req.new_rationale.strip(),
            revised_by_user_id=reviewer_key,
            revision_reason=req.revision_reason.strip(),
        )
        db.add(revision)

        rev.analyst_verdict = req.new_verdict
        rev.analyst_notes = req.new_rationale.strip()
        rev.review_version = int(rev.review_version or 1) + 1
        db.add(rev)

        # Recompute cohort item state
        item = (
            await db.execute(
                select(BenchmarkCohortItem).where(
                    BenchmarkCohortItem.cohort_id == cohort.id,
                    BenchmarkCohortItem.incident_db_id == rev.incident_id,
                )
            )
        ).scalar_one_or_none()
        if item:
            locked_revs = (
                await db.execute(
                    select(AnalystVerdictReview).where(
                        AnalystVerdictReview.incident_id == rev.incident_id,
                        AnalystVerdictReview.review_mode == "BENCHMARK_CERTIFICATION",
                        AnalystVerdictReview.is_locked.is_(True),
                    )
                )
            ).scalars().all()
            if len(locked_revs) >= 2:
                vs = {r.analyst_verdict for r in locked_revs[:2]}
                if len(vs) == 1:
                    v_only = next(iter(vs))
                    item.certification_status = "CERTIFIED_INCONCLUSIVE" if v_only == "INCONCLUSIVE" else "GT3_CERTIFIED"
                    item.certified_verdict = v_only
                else:
                    item.certification_status = "CONFLICT_PENDING_ADJUDICATION"
                    item.certified_verdict = None
            elif len(locked_revs) == 1:
                item.certification_status = "GT2_SINGLE_REVIEW"
                item.certified_verdict = None
            item.certification_version = int(item.certification_version or 1) + 1
            item.updated_at = utc_now()
            db.add(item)

        db.add(
            AuditLog(
                user_id=user_id or reviewer_key,
                username=reviewer_key,
                action="BENCHMARK_GT_REVIEW_REVISED",
                resource_type="ANALYST_VERDICT_REVIEW",
                resource_id=rev.id,
                details={
                    "previous_verdict": revision.previous_verdict,
                    "new_verdict": req.new_verdict,
                    "revision_reason": req.revision_reason,
                },
            )
        )
        await db.commit()
        return {
            "success": True,
            "revision_id": revision.id,
            "review_id": rev.id,
            "certification_status": item.certification_status if item else None,
        }

    @classmethod
    async def get_post_certification_comparison(
        cls,
        db: AsyncSession,
        cohort_key: str,
        incident_identifier: str,
        current_user: Any,
    ) -> Dict[str, Any]:
        """
        Strictly post-certification endpoint: returns AI evaluation & historical FortiSIEM
        metadata ONLY after dual-reviewer certification (`GT3_CERTIFIED` or `CERTIFIED_INCONCLUSIVE`)
        is finalized! Fails closed (403) before certification completion.
        """
        _, _, is_admin = _user_identity(current_user)
        cohort, item, inc = await cls._resolve_cohort_item_and_incident(
            db, cohort_key, incident_identifier
        )
        if item.certification_status not in ("GT3_CERTIFIED", "CERTIFIED_INCONCLUSIVE"):
            raise PermissionError(
                "POST_CERTIFICATION_LOCKED: AI predictions and historical labels remain strictly sealed "
                "until dual-reviewer GT-3 certification is completed."
            )
        if not is_admin:
            raise PermissionError(
                "ADMIN_OR_LEAD_REQUIRED: Post-certification AI comparison is restricted to Administrators and SOC Managers."
            )

        hist_gt = None
        if inc and inc.ground_truth:
            hist_gt = {
                "resolution": inc.ground_truth.resolution,
                "is_ml_generated": inc.ground_truth.is_ml_generated,
                "cleared_user": inc.ground_truth.cleared_user,
                "cleared_reason": inc.ground_truth.cleared_reason,
            }
        return {
            "cohort_key": cohort.cohort_key,
            "fortisiem_incident_id": item.fortisiem_incident_id,
            "certification_status": item.certification_status,
            "certified_human_verdict": item.certified_verdict,
            "stored_ai_verdict": inc.ai_verdict if inc else None,
            "historical_fortisiem_ground_truth": hist_gt,
        }

    @classmethod
    async def get_audit_readiness(
        cls, db: AsyncSession, cohort_key: str, current_user: Any
    ) -> Dict[str, Any]:
        cohort = await cls._get_cohort_or_404(db, cohort_key)
        progress = await cls._build_progress_counters(db, cohort, current_user)
        return {
            "cohort_key": cohort.cohort_key,
            "name": cohort.name,
            "version": cohort.version,
            "is_frozen": cohort.is_frozen,
            "excluded_from_learning": cohort.excluded_from_learning,
            "progress": progress.model_dump(),
        }

    @classmethod
    async def ensure_ais_3_0_holdout_cohort(
        cls,
        db: AsyncSession,
        target_size: int = 100,
        per_rule_cap: int = 12,
    ) -> BenchmarkCohort:
        """
        Prepares `AIS_3_0_INDEPENDENT_HOLDOUT_100` for future AIS 3.0 blind certification.
        Strictly excludes `AIS_2_6E_FROZEN_20` incidents, CrowdStrike/Prisma development rule
        families, LearningRecord/RAG precedents, and prior human-reviewed incidents, while
        deduplicating repeated campaign floods and leaving all items `GT0_UNREVIEWED`.
        """
        await cls.ensure_ais_2_6e_cohort_registered(db, load_from_zip_if_missing=False)

        c_res = await db.execute(
            select(BenchmarkCohort).where(BenchmarkCohort.cohort_key == AIS_3_0_HOLDOUT_COHORT_ID)
        )
        cohort = c_res.scalar_one_or_none()
        if not cohort:
            cohort = BenchmarkCohort(
                cohort_key=AIS_3_0_HOLDOUT_COHORT_ID,
                name=AIS_3_0_HOLDOUT_COHORT_NAME,
                description=(
                    "Unseen multi-rule holdout benchmark cohort prepared in AIS 2.9 across >=5 "
                    "non-development detection families for independent GT-3 human certification."
                ),
                version="3.0",
                is_frozen=True,
                required_reviewers=2,
                excluded_from_learning=True,
            )
            db.add(cohort)
            await db.flush()

        existing_holdout_res = await db.execute(
            select(BenchmarkCohortItem).where(BenchmarkCohortItem.cohort_id == cohort.id)
        )
        existing_holdout = existing_holdout_res.scalars().all()
        if len(existing_holdout) >= target_size:
            return cohort

        existing_fids = {it.fortisiem_incident_id for it in existing_holdout}

        # Collect contamination exclusion sets
        other_items = (
            await db.execute(
                select(BenchmarkCohortItem).where(BenchmarkCohortItem.cohort_id != cohort.id)
            )
        ).scalars().all()
        excluded_fids = {it.fortisiem_incident_id for it in other_items}
        excluded_db_ids = {it.incident_db_id for it in other_items if it.incident_db_id}

        learned_ids = {row[0] for row in (await db.execute(select(LearningRecord.incident_id))).all()}
        reviewed_ids = {row[0] for row in (await db.execute(select(AnalystVerdictReview.incident_id))).all()}
        excluded_db_ids |= learned_ids | reviewed_ids

        # Fetch candidate incidents evenly across ALL non-CS / non-Prisma rules so
        # high-volume rules (e.g. Web Policy Violation) do not starve diverse rule families.
        all_rules = (await db.execute(select(Rule))).scalars().all()
        candidates: List[Incident] = []
        seen_inc_pks = set()
        for r_obj in all_rules:
            r_up = str(r_obj.rule_id or r_obj.event_type or "").upper()
            if "CS_SUSPICIOUS" in r_up or "CROWDSTRIKE" in r_up or "PRISMA" in r_up:
                continue
            r_cands = (
                await db.execute(
                    select(Incident)
                    .where(or_(Incident.rule_id == r_obj.id, Incident.event_type == r_obj.rule_id))
                    .options(selectinload(Incident.events), selectinload(Incident.ground_truth), selectinload(Incident.rule))
                    .order_by(Incident.created_at.desc())
                    .limit(40)
                )
            ).scalars().all()
            for inc in r_cands:
                if inc.id not in seen_inc_pks:
                    seen_inc_pks.add(inc.id)
                    candidates.append(inc)
        # Include any non-CS/Prisma incidents not linked via Rule FK
        if len(candidates) < target_size * 2:
            fallback_res = (
                await db.execute(
                    select(Incident)
                    .options(selectinload(Incident.events), selectinload(Incident.ground_truth), selectinload(Incident.rule))
                    .order_by(Incident.created_at.desc())
                    .limit(400)
                )
            ).scalars().all()
            for inc in fallback_res:
                if inc.id not in seen_inc_pks:
                    seen_inc_pks.add(inc.id)
                    candidates.append(inc)

        by_rule: Dict[str, List[Incident]] = {}
        seen_signatures = set()
        for inc in candidates:
            fid = str(inc.incident_id or "").strip()
            if not fid or fid in excluded_fids or fid in existing_fids or inc.id in excluded_db_ids:
                continue
            r_id = str((inc.rule.rule_id if inc.rule else None) or inc.event_type or "").strip()
            r_upper = r_id.upper()
            # Isolate holdout from development rule families (CrowdStrike / Prisma SASE)
            if "CS_SUSPICIOUS" in r_upper or "CROWDSTRIKE" in r_upper or "PRISMA" in r_upper:
                continue
            if not inc.events and not inc.raw_payload:
                continue
            # Deduplicate repeated campaign floods within same rule + source_ip + normalized title
            sig = (r_upper, str(inc.source_ip or ""), str(inc.title or "").strip().lower()[:80])
            if sig in seen_signatures:
                continue
            seen_signatures.add(sig)
            by_rule.setdefault(r_id or "UNKNOWN_RULE", []).append(inc)

        # Prioritize unexposed (no prior ai_verdict) within each rule bucket
        for r_id, lst in by_rule.items():
            lst.sort(key=lambda x: (0 if not x.ai_verdict else 1, -(len(x.events or [])), str(x.incident_id)))

        selected: List[Incident] = []
        rule_keys = sorted(by_rule.keys(), key=lambda k: len(by_rule[k]), reverse=True)
        per_rule_counts: Dict[str, int] = {k: 0 for k in rule_keys}
        idx_map: Dict[str, int] = {k: 0 for k in rule_keys}

        # Pass 1: Round-robin across distinct rules up to per_rule_cap
        needed = max(0, target_size - len(existing_holdout))
        while len(selected) < needed:
            progressed = False
            for rk in rule_keys:
                if len(selected) >= needed:
                    break
                if per_rule_counts[rk] >= per_rule_cap:
                    continue
                pos = idx_map[rk]
                if pos < len(by_rule[rk]):
                    selected.append(by_rule[rk][pos])
                    idx_map[rk] = pos + 1
                    per_rule_counts[rk] += 1
                    progressed = True
            if not progressed:
                break

        # Pass 2: If fewer than target_size filled under strict cap, fill remaining unique deduplicated candidates
        if len(selected) < needed:
            for rk in rule_keys:
                while len(selected) < needed and idx_map[rk] < len(by_rule[rk]):
                    selected.append(by_rule[rk][idx_map[rk]])
                    idx_map[rk] += 1

        seq_start = len(existing_holdout) + 1
        for offset, inc in enumerate(selected):
            seq = seq_start + offset
            rule_obj = inc.rule
            norm_res = EvidenceNormalizationService.normalize_incident_evidence(
                incident=inc, events=inc.events
            )
            raw_hash = _sha256_canonical(
                [
                    {
                        "event_id": ev.event_id,
                        "event_type": ev.event_type,
                        "raw_log": ev.raw_log,
                        "attributes": ev.attributes,
                    }
                    for ev in (inc.events or [])
                ]
                or inc.raw_payload
                or {"incident_id": inc.incident_id}
            )
            can_hash = _sha256_canonical([r.model_dump() for r in norm_res.records])
            rule_hash = (
                _sha256_canonical(
                    {
                        "rule_id": rule_obj.rule_id,
                        "raw_rule_text": rule_obj.raw_rule_text,
                        "pattern_logic": rule_obj.pattern_logic,
                        "parsed_metadata": rule_obj.parsed_metadata,
                    }
                )
                if rule_obj
                else None
            )
            exposure_reasons: List[str] = []
            if inc.ai_verdict:
                exposure_reasons.append("Prior operational ai_verdict masked during blind review")
            if inc.ground_truth is not None:
                exposure_reasons.append("Historical SIEM ground truth masked during blind review")

            r_id = (rule_obj.rule_id if rule_obj else None) or inc.event_type or "UNKNOWN_RULE"
            item = BenchmarkCohortItem(
                cohort_id=cohort.id,
                incident_db_id=inc.id,
                fortisiem_incident_id=str(inc.incident_id),
                rule_id=r_id,
                rule_name=(rule_obj.name if rule_obj else None) or inc.title or r_id,
                customer=inc.customer or "DEFAULT",
                is_priority=False,
                priority_rank=seq,
                eligibility_status="ELIGIBLE",
                certification_status="GT0_UNREVIEWED",
                raw_evidence_sha256=raw_hash,
                canonical_evidence_sha256=can_hash,
                rule_definition_sha256=rule_hash,
                exposure_risk_flag=bool(exposure_reasons),
                exposure_risk_reason="; ".join(exposure_reasons),
            )
            db.add(item)

        await db.commit()
        await db.refresh(cohort)
        return cohort

    @classmethod
    async def get_holdout_eligibility_summary(
        cls, db: AsyncSession, current_user: Any
    ) -> Dict[str, Any]:
        """Reports frozen GT-3 readiness + AIS 3.0 holdout eligibility, diversity, and contamination isolation."""
        frozen_cohort = await cls.ensure_ais_2_6e_cohort_registered(db, load_from_zip_if_missing=False)
        holdout_cohort = await cls.ensure_ais_3_0_holdout_cohort(db)

        frozen_prog = await cls._build_progress_counters(db, frozen_cohort, current_user)
        holdout_prog = await cls._build_progress_counters(db, holdout_cohort, current_user)

        frozen_items = (
            await db.execute(select(BenchmarkCohortItem).where(BenchmarkCohortItem.cohort_id == frozen_cohort.id))
        ).scalars().all()
        holdout_items = (
            await db.execute(select(BenchmarkCohortItem).where(BenchmarkCohortItem.cohort_id == holdout_cohort.id))
        ).scalars().all()

        frozen_fids = {i.fortisiem_incident_id for i in frozen_items}
        holdout_fids = {i.fortisiem_incident_id for i in holdout_items}
        rule_counts: Dict[str, int] = {}
        unexposed_count = 0
        for hi in holdout_items:
            rule_counts[hi.rule_id] = rule_counts.get(hi.rule_id, 0) + 1
            if not hi.exposure_risk_flag:
                unexposed_count += 1

        return {
            "frozen_cohort": {
                "cohort_key": frozen_cohort.cohort_key,
                "progress": frozen_prog.model_dump(),
            },
            "holdout_cohort": {
                "cohort_key": holdout_cohort.cohort_key,
                "target_size": 100,
                "actual_count": len(holdout_items),
                "shortfall": max(0, 100 - len(holdout_items)),
                "distinct_rule_families": len(rule_counts),
                "rules_breakdown": rule_counts,
                "zero_overlap_with_frozen": len(frozen_fids & holdout_fids) == 0,
                "overlap_count": len(frozen_fids & holdout_fids),
                "unexposed_count": unexposed_count,
                "progress": holdout_prog.model_dump(),
            },
        }
