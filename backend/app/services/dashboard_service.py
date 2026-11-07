from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.models.incident import Incident, HistoricalGroundTruth
from app.models.rule import Rule
from app.models.import_job import ImportJob
from app.schemas.dashboard import (
    DashboardMetricsResponse,
    SeverityCount,
    SourceCount,
    GroundTruthCount,
    RecentActivityItem,
    RecentImportJobItem,
)


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_metrics(self) -> DashboardMetricsResponse:
        # Total incidents
        inc_count_stmt = select(func.count(Incident.id))
        total_incidents = (await self.db.execute(inc_count_stmt)).scalar_one()

        # Total rules
        rule_count_stmt = select(func.count(Rule.id))
        total_rules = (await self.db.execute(rule_count_stmt)).scalar_one()

        if total_incidents == 0:
            return DashboardMetricsResponse(
                total_incidents=0,
                total_rules=total_rules,
                historical_true_positives=0,
                historical_false_positives=0,
                unresolved_incidents=0,
                ai_evaluated_count=0,
                ai_true_positives=0,
                ai_false_positives=0,
                ai_requires_attention=0,
                ai_pending_evaluation=0,
                severity_breakdown=[],
                source_breakdown=[],
                ground_truth_breakdown=[],
                recent_activity=[],
                recent_imports=[],
                is_empty=True,
            )

        # AI Verdict evaluation metrics across all incidents
        ai_incs_stmt = select(Incident.ai_verdict).where(Incident.ai_verdict.isnot(None))
        ai_incs_res = (await self.db.execute(ai_incs_stmt)).scalars().all()
        ai_evaluated_count = len(ai_incs_res)
        ai_tp = sum(1 for v in ai_incs_res if isinstance(v, dict) and v.get("verdict") == "TRUE_POSITIVE")
        ai_fp = sum(1 for v in ai_incs_res if isinstance(v, dict) and v.get("verdict") == "FALSE_POSITIVE")
        ai_ra = sum(1 for v in ai_incs_res if isinstance(v, dict) and v.get("verdict") == "REQUIRES_ATTENTION")
        ai_pending = max(0, total_incidents - ai_evaluated_count)

        # Ground truth counts (legacy analyst validation baseline)
        tp_stmt = select(func.count(HistoricalGroundTruth.id)).where(
            HistoricalGroundTruth.resolution.ilike("%True Positive%")
        )
        historical_tp = (await self.db.execute(tp_stmt)).scalar_one()

        fp_stmt = select(func.count(HistoricalGroundTruth.id)).where(
            HistoricalGroundTruth.resolution.ilike("%False Positive%")
        )
        historical_fp = (await self.db.execute(fp_stmt)).scalar_one()

        labeled_count_stmt = select(func.count(HistoricalGroundTruth.id)).where(
            HistoricalGroundTruth.resolution != "",
            HistoricalGroundTruth.resolution.isnot(None)
        )
        labeled_count = (await self.db.execute(labeled_count_stmt)).scalar_one()
        unresolved_incidents = max(0, total_incidents - labeled_count)

        # Severity breakdown
        sev_stmt = select(
            Incident.severity,
            func.count(Incident.id)
        ).group_by(Incident.severity)
        sev_res = (await self.db.execute(sev_stmt)).all()
        severity_breakdown = [
            SeverityCount(
                severity=s or "UNKNOWN",
                count=c,
                percentage=round((c / total_incidents) * 100, 1) if total_incidents > 0 else 0.0
            )
            for s, c in sev_res
        ]
        # Order by standard severity
        sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFORMATIONAL": 4}
        severity_breakdown.sort(key=lambda x: sev_order.get(x.severity, 5))

        # Source / Event Type breakdown
        src_stmt = select(
            Incident.event_type,
            func.count(Incident.id)
        ).group_by(Incident.event_type).order_by(desc(func.count(Incident.id))).limit(10)
        src_res = (await self.db.execute(src_stmt)).all()
        source_breakdown = [
            SourceCount(
                source=s or "UNKNOWN",
                count=c,
                percentage=round((c / total_incidents) * 100, 1) if total_incidents > 0 else 0.0
            )
            for s, c in src_res
        ]

        # Ground truth breakdown
        gt_stmt = select(
            HistoricalGroundTruth.resolution,
            func.count(HistoricalGroundTruth.id)
        ).group_by(HistoricalGroundTruth.resolution)
        gt_res = (await self.db.execute(gt_stmt)).all()
        ground_truth_breakdown = [
            GroundTruthCount(
                verdict=v if v else "Unlabeled",
                count=c,
                percentage=round((c / total_incidents) * 100, 1) if total_incidents > 0 else 0.0
            )
            for v, c in gt_res
        ]

        # Recent activity (latest 10 incidents ordered by incident occurrence time)
        occurrence_order = func.coalesce(
            Incident.first_seen_epoch,
            Incident.created_at_epoch,
            Incident.last_seen_epoch,
        )
        recent_inc_stmt = select(
            Incident,
            HistoricalGroundTruth.resolution
        ).outerjoin(
            HistoricalGroundTruth, Incident.id == HistoricalGroundTruth.incident_id
        ).order_by(
            desc(occurrence_order).nulls_last(),
            desc(Incident.created_at)
        ).limit(10)
        recent_res = (await self.db.execute(recent_inc_stmt)).all()

        recent_activity = [
            RecentActivityItem(
                incident_id=inc.incident_id,
                title=inc.title,
                severity=inc.severity,
                event_type=inc.event_type,
                created_at_epoch=inc.first_seen_epoch or inc.created_at_epoch or inc.last_seen_epoch,
                historical_verdict=res,
                ai_verdict=inc.ai_verdict,
                created_at=inc.created_at,
            )
            for inc, res in recent_res
        ]

        # Recent import jobs (latest 5)
        jobs_stmt = select(ImportJob).order_by(desc(ImportJob.created_at)).limit(5)
        jobs_res = (await self.db.execute(jobs_stmt)).scalars().all()
        recent_imports = [
            RecentImportJobItem(
                id=j.id,
                filename=j.filename,
                file_type=j.file_type,
                imported_count=j.imported_count,
                duplicate_count=j.duplicate_count,
                error_count=j.error_count,
                status=j.status,
                created_at=j.created_at,
            )
            for j in jobs_res
        ]

        return DashboardMetricsResponse(
            total_incidents=total_incidents,
            total_rules=total_rules,
            historical_true_positives=historical_tp,
            historical_false_positives=historical_fp,
            unresolved_incidents=unresolved_incidents,
            ai_evaluated_count=ai_evaluated_count,
            ai_true_positives=ai_tp,
            ai_false_positives=ai_fp,
            ai_requires_attention=ai_ra,
            ai_pending_evaluation=ai_pending,
            severity_breakdown=severity_breakdown,
            source_breakdown=source_breakdown,
            ground_truth_breakdown=ground_truth_breakdown,
            recent_activity=recent_activity,
            recent_imports=recent_imports,
            is_empty=False,
        )

