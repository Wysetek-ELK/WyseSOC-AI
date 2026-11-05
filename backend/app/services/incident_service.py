from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, desc
from sqlalchemy.orm import selectinload

from app.models.incident import Incident, IncidentEvent, HistoricalGroundTruth
from app.models.rule import Rule
from app.schemas.incident import (
    IncidentListItemResponse,
    IncidentDetailResponse,
    IncidentEventResponse,
    HistoricalGroundTruthResponse,
)


class IncidentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_incidents(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        rule_id: Optional[str] = None,
        resolution: Optional[str] = None,
        blind_review: bool = False,
    ) -> Tuple[List[IncidentListItemResponse], int]:
        query = select(Incident).options(
            selectinload(Incident.rule),
            selectinload(Incident.ground_truth),
            selectinload(Incident.events)
        )

        # Filters
        if severity:
            query = query.where(Incident.severity == severity.upper())

        if status:
            if status.lower() == "open":
                query = query.where(Incident.status_code == 1)
            elif status.lower() == "closed":
                query = query.where(Incident.status_code == 2)

        if rule_id:
            query = query.where(or_(Incident.rule_id == rule_id, Incident.event_type == rule_id))

        if resolution:
            query = query.join(Incident.ground_truth).where(HistoricalGroundTruth.resolution == resolution)

        if search:
            search_term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Incident.incident_id.ilike(search_term),
                    Incident.title.ilike(search_term),
                    Incident.description.ilike(search_term),
                    Incident.source_ip.ilike(search_term),
                    Incident.reporting_device.ilike(search_term),
                    Incident.event_type.ilike(search_term),
                )
            )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_res = await self.db.execute(count_query)
        total = total_res.scalar_one()

        # Sort and paginate
        query = query.order_by(desc(Incident.created_at_epoch), desc(Incident.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        incidents = result.scalars().all()

        items: List[IncidentListItemResponse] = []
        for inc in incidents:
            hist_res = None
            if not blind_review and inc.ground_truth:
                hist_res = inc.ground_truth.resolution
            elif blind_review:
                hist_res = "[Hidden - Blind Review]"

            items.append(
                IncidentListItemResponse(
                    id=inc.id,
                    incident_id=inc.incident_id,
                    rule_id=inc.rule_id,
                    rule_name=inc.rule.name if inc.rule else None,
                    event_type=inc.event_type,
                    title=inc.title,
                    severity=inc.severity,
                    status_code=inc.status_code,
                    status_name=inc.status_name,
                    category=inc.category,
                    source_ip=inc.source_ip,
                    reporting_device=inc.reporting_device,
                    created_at_epoch=inc.created_at_epoch,
                    first_seen_epoch=inc.first_seen_epoch,
                    last_seen_epoch=inc.last_seen_epoch,
                    historical_resolution=hist_res,
                    event_count=len(inc.events),
                    created_at=inc.created_at,
                )
            )

        return items, total

    async def get_incident(
        self,
        identifier: str,  # can be UUID id or incident_id (e.g. "132438483")
        blind_review: bool = False,
    ) -> Optional[IncidentDetailResponse]:
        query = select(Incident).where(
            or_(Incident.id == identifier, Incident.incident_id == identifier)
        ).options(
            selectinload(Incident.rule),
            selectinload(Incident.ground_truth),
            selectinload(Incident.events)
        )

        result = await self.db.execute(query)
        inc = result.scalar_one_or_none()
        if not inc:
            return None

        # Build events
        events_resp = [
            IncidentEventResponse(
                id=evt.id,
                event_id=evt.event_id,
                event_receive_time=evt.event_receive_time,
                event_type=evt.event_type,
                raw_log=evt.raw_log,
                attributes=evt.attributes or {},
            )
            for evt in inc.events
        ]

        # Ground truth (suppressed in blind review)
        gt_resp = None
        if not blind_review and inc.ground_truth:
            gt_resp = HistoricalGroundTruthResponse(
                id=inc.ground_truth.id,
                resolution=inc.ground_truth.resolution,
                cleared_reason=inc.ground_truth.cleared_reason,
                comments=inc.ground_truth.comments,
                cleared_user=inc.ground_truth.cleared_user,
                cleared_time_epoch=inc.ground_truth.cleared_time_epoch,
                resolved_at_epoch=inc.ground_truth.resolved_at_epoch,
                is_ml_generated=inc.ground_truth.is_ml_generated,
                created_at=inc.ground_truth.created_at,
            )

        return IncidentDetailResponse(
            id=inc.id,
            incident_id=inc.incident_id,
            rule_id=inc.rule_id,
            rule_name=inc.rule.name if inc.rule else None,
            rule_description=inc.rule.description if inc.rule else None,
            import_job_id=inc.import_job_id,
            event_type=inc.event_type,
            title=inc.title,
            description=inc.description,
            detail=inc.detail,
            severity=inc.severity,
            event_severity=inc.event_severity,
            status_code=inc.status_code,
            status_name=inc.status_name,
            category=inc.category,
            subcategory=inc.subcategory,
            source_ip=inc.source_ip,
            reporting_device=inc.reporting_device,
            reporting_ip=inc.reporting_ip,
            customer=inc.customer,
            ticket_id=inc.ticket_id,
            first_seen_epoch=inc.first_seen_epoch,
            last_seen_epoch=inc.last_seen_epoch,
            created_at_epoch=inc.created_at_epoch,
            updated_at_epoch=inc.updated_at_epoch,
            raw_payload=inc.raw_payload or {},
            events=events_resp,
            ground_truth=gt_resp,
            created_at=inc.created_at,
            updated_at=inc.updated_at,
        )

