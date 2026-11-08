from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, desc, delete
from sqlalchemy.orm import selectinload

from app.models.incident import Incident, IncidentEvent, HistoricalGroundTruth
from app.models.rule import Rule
from app.schemas.incident import (
    IncidentListItemResponse,
    IncidentDetailResponse,
    IncidentEventResponse,
    HistoricalGroundTruthResponse,
    ModelFacingIncidentPayload,
    ModelFacingEvent,
)

FORBIDDEN_GROUND_TRUTH_KEYS = {
    "resolution",
    "cleared_reason",
    "clearedreason",
    "cleared_user",
    "cleareduser",
    "cleared_time",
    "clearedtime",
    "cleared_time_epoch",
    "comments",
    "analyst_verdict",
    "analyst_notes",
    "analyst_explanation",
    "analyst_verdict_confidence",
    "actual_verdict",
    "human_label",
    "ground_truth",
    "ground_truth_verdict",
    "incidentressummary",
    "incident_res_summary",
    "verification_status",
    "verified_verdict",
    "historical_resolution",
}


def sanitize_blind_review_payload(data: Any) -> Any:
    """
    Recursively purges all analyst determinations, ground truth annotations,
    and historical closure comments from raw payloads and event telemetry
    during blind review evaluations (REQ-04 / AV-006).
    """
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            norm_k = str(k).lower().replace("-", "_").replace(" ", "_")
            if norm_k in FORBIDDEN_GROUND_TRUTH_KEYS or any(f in norm_k for f in ["cleared_reason", "clearedreason", "incidentres"]):
                continue
            cleaned[k] = sanitize_blind_review_payload(v)
        return cleaned
    elif isinstance(data, list):
        return [sanitize_blind_review_payload(item) for item in data]
    return data


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

        # Sort and paginate: Latest incident occurrence on top (nulls last)
        occurrence_order = func.coalesce(
            Incident.first_seen_epoch,
            Incident.created_at_epoch,
            Incident.last_seen_epoch,
        )
        query = query.order_by(
            desc(occurrence_order).nulls_last(),
            desc(Incident.created_at)
        )
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
                    ai_verdict=inc.ai_verdict,
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

        # Self-healing: if events in database lack attributes or raw_log, re-extract from raw_payload
        needs_repair = False
        if inc.events:
            for evt in inc.events:
                if (not evt.attributes or not evt.raw_log) and inc.raw_payload:
                    needs_repair = True
                    break
        elif inc.raw_payload and (inc.raw_payload.get("rawEvents") or inc.raw_payload.get("triggeringEvents")):
            needs_repair = True

        if needs_repair and inc.raw_payload:
            from app.services.ingestion_service import extract_event_data
            raw_evts = inc.raw_payload.get("rawEvents") or inc.raw_payload.get("triggeringEvents") or []
            if raw_evts:
                await self.db.execute(delete(IncidentEvent).where(IncidentEvent.incident_id == inc.id))
                repaired = []
                for idx, revt in enumerate(raw_evts):
                    if not isinstance(revt, dict):
                        continue
                    evt_id, evt_recv, evt_t, raw_log, attrs = extract_event_data(
                        revt, inc.incident_id, idx, fallback_event_type=inc.event_type
                    )
                    db_evt = IncidentEvent(
                        incident_id=inc.id,
                        event_id=evt_id,
                        event_receive_time=evt_recv or inc.first_seen_epoch,
                        event_type=evt_t,
                        raw_log=raw_log,
                        attributes=attrs,
                    )
                    self.db.add(db_evt)
                    repaired.append(db_evt)
                await self.db.commit()
                inc.events = repaired

        # Build events response (purging ground-truth leakage in blind review mode)
        events_resp = [
            IncidentEventResponse(
                id=evt.id,
                event_id=evt.event_id,
                event_receive_time=evt.event_receive_time or inc.first_seen_epoch,
                event_type=evt.event_type,
                raw_log=evt.raw_log,
                attributes=sanitize_blind_review_payload(evt.attributes or {}) if blind_review else (evt.attributes or {}),
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

        sanitized_raw_payload = sanitize_blind_review_payload(inc.raw_payload or {}) if blind_review else (inc.raw_payload or {})

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
            raw_payload=sanitized_raw_payload,
            events=events_resp,
            ground_truth=gt_resp,
            ai_verdict=inc.ai_verdict,
            created_at=inc.created_at,
            updated_at=inc.updated_at,
        )

    def get_model_facing_payload(self, inc: Incident) -> Dict[str, Any]:
        """
        Constructs strictly sanitized, ground-truth-isolated model-facing payload.
        Adheres to explicit allowlist. Excludes all resolution, comments, clearedReason, etc.
        """
        from app.services.model_payload_allowlist import build_model_facing_payload
        return build_model_facing_payload(
            incident=inc,
            rule=inc.rule,
            events=inc.events or [],
        )

