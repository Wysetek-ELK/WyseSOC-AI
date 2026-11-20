from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, desc, delete
from sqlalchemy.orm import selectinload

from app.models.incident import Incident, IncidentEvent, HistoricalGroundTruth
from app.models.analyst_feedback import AnalystVerdictReview
from app.models.rule import Rule
from app.services.policy_governance import (
    RuleMatchContext,
    build_rule_incident_context,
    build_rule_incident_sql_filter,
    resolve_canonical_rule,
    verify_incident_matches_rule,
)
from app.services.verdict_trustworthiness_engine import VerdictTrustworthinessEngine
from app.schemas.incident import (
    IncidentListItemResponse,
    IncidentDetailResponse,
    IncidentEventResponse,
    HistoricalGroundTruthResponse,
    IncidentMatchedRuleSummary,
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

    async def list_incidents_with_rule_summary(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        rule_id: Optional[str] = None,
        exact_rule_id: Optional[str] = None,
        resolution: Optional[str] = None,
        blind_review: bool = False,
        current_user: Optional[Any] = None,
    ) -> Tuple[List[IncidentListItemResponse], int, Dict[str, Any]]:
        all_rules = list((await self.db.execute(select(Rule))).scalars().all())
        rules_by_uuid = {str(r.id): r for r in all_rules}
        rules_by_logical = {str(r.rule_id): r for r in all_rules if r.rule_id}
        rules_by_event_map: Dict[str, List[Rule]] = {}
        for r in all_rules:
            if r.event_type:
                rules_by_event_map.setdefault(str(r.event_type), []).append(r)

        def _infer_rule_identity(inc_obj: Incident) -> Tuple[Optional[str], Optional[str], Optional[str]]:
            if inc_obj.rule is not None:
                return str(inc_obj.rule.id), str(inc_obj.rule.rule_id), str(inc_obj.rule.name)
            if inc_obj.rule_id and str(inc_obj.rule_id) in rules_by_uuid:
                r = rules_by_uuid[str(inc_obj.rule_id)]
                return str(r.id), str(r.rule_id), str(r.name)
            if inc_obj.rule_id and str(inc_obj.rule_id) in rules_by_logical:
                r = rules_by_logical[str(inc_obj.rule_id)]
                return str(r.id), str(r.rule_id), str(r.name)
            if inc_obj.event_type and len(rules_by_event_map.get(str(inc_obj.event_type), [])) == 1:
                r = rules_by_event_map[str(inc_obj.event_type)][0]
                return str(r.id), str(r.rule_id), str(r.name)
            raw_p = inc_obj.raw_payload if isinstance(inc_obj.raw_payload, dict) else {}
            embedded = raw_p.get("ruleId") or raw_p.get("rule_id") or raw_p.get("incidentSourceRule")
            if embedded:
                emb_s = str(embedded).strip()
                r = rules_by_logical.get(emb_s) or rules_by_uuid.get(emb_s)
                if r:
                    return str(r.id), str(r.rule_id), str(r.name)
                return None, emb_s, None
            return (str(inc_obj.rule_id) if inc_obj.rule_id else None), str(inc_obj.event_type or inc_obj.rule_id or "UNMAPPED"), None

        base_query = select(Incident).outerjoin(Rule, Incident.rule_id == Rule.id)

        # Multi-Tenant Isolation (P1): Restrict analysts/viewers strictly to their assigned customer tenant.
        # Legacy DEFAULT, empty, and NULL records are restricted to users with customer == "DEFAULT" or Administrators.
        user_customer = getattr(current_user, "customer", None)
        user_role = getattr(current_user, "role", "")
        if user_customer and user_role not in ("Administrator", "SuperAdmin"):
            if user_customer != "DEFAULT":
                # Tenant-specific user can ONLY access incidents belonging strictly to their customer tenant
                base_query = base_query.where(Incident.customer == user_customer)
            else:
                # Platform default analyst with customer == "DEFAULT": restricted to legacy platform DEFAULT scope
                base_query = base_query.where(
                    or_(
                        Incident.customer == "DEFAULT",
                        Incident.customer == "",
                        Incident.customer.is_(None),
                    )
                )

        # Filters
        if severity:
            base_query = base_query.where(Incident.severity == severity.upper())

        if status:
            if status.lower() == "open":
                base_query = base_query.where(Incident.status_code == 1)
            elif status.lower() == "closed":
                base_query = base_query.where(Incident.status_code == 2)

        effective_rule_filter = (exact_rule_id or rule_id or "").strip() or None
        canonical_rule: Optional[Rule] = None
        rule_ctx: Optional[RuleMatchContext] = None
        if effective_rule_filter:
            canonical_rule = await resolve_canonical_rule(self.db, effective_rule_filter)
            if canonical_rule is not None:
                rule_ctx = await build_rule_incident_context(self.db, canonical_rule)
                sql_rule_filter = build_rule_incident_sql_filter(rule_ctx)
                if sql_rule_filter is not None:
                    base_query = base_query.where(sql_rule_filter)
            else:
                base_query = base_query.where(
                    or_(
                        Incident.rule_id == effective_rule_filter,
                        Incident.event_type == effective_rule_filter,
                    )
                )

        if resolution:
            base_query = base_query.join(Incident.ground_truth).where(HistoricalGroundTruth.resolution == resolution)

        if search:
            search_term = f"%{search.strip()}%"
            base_query = base_query.where(
                or_(
                    Incident.incident_id.ilike(search_term),
                    Incident.title.ilike(search_term),
                    Incident.description.ilike(search_term),
                    Incident.source_ip.ilike(search_term),
                    Incident.reporting_device.ilike(search_term),
                    Incident.event_type.ilike(search_term),
                    Rule.rule_id.ilike(search_term),
                    Rule.name.ilike(search_term),
                )
            )

        occurrence_order = func.coalesce(
            Incident.first_seen_epoch,
            Incident.created_at_epoch,
            Incident.last_seen_epoch,
        )

        # If exact canonical rule filtering is active, apply the exact same secondary row-level
        # verify_incident_matches_rule check as PolicySimulationService so counts always reconcile.
        cohort_rows = (
            await self.db.execute(
                base_query.options(selectinload(Incident.rule))
                .order_by(desc(occurrence_order).nulls_last(), desc(Incident.created_at), Incident.id.asc())
            )
        ).scalars().all()

        rule_buckets: Dict[str, Dict[str, Any]] = {}
        filtered_ordered_ids: List[str] = []
        for inc_row in cohort_rows:
            if rule_ctx is not None:
                ok_match, _ = verify_incident_matches_rule(inc_row, rule_ctx)
                if not ok_match:
                    continue
            filtered_ordered_ids.append(inc_row.id)
            r_uuid, l_rule_id, r_name = _infer_rule_identity(inc_row)
            bucket_key = r_uuid or f"logical:{l_rule_id or inc_row.event_type}"
            if bucket_key not in rule_buckets:
                rule_buckets[bucket_key] = {
                    "rule_uuid": r_uuid,
                    "logical_rule_id": l_rule_id or str(inc_row.event_type or "UNMAPPED"),
                    "rule_name": r_name,
                    "event_type": inc_row.event_type,
                    "incident_count": 0,
                }
            rule_buckets[bucket_key]["incident_count"] += 1

        total = len(filtered_ordered_ids)
        start_idx = max(0, (page - 1) * page_size)
        page_ids = filtered_ordered_ids[start_idx : start_idx + page_size]

        incidents: List[Incident] = []
        if page_ids:
            inc_res = await self.db.execute(
                select(Incident)
                .where(Incident.id.in_(page_ids))
                .options(
                    selectinload(Incident.rule),
                    selectinload(Incident.ground_truth),
                    selectinload(Incident.events),
                )
            )
            by_id = {obj.id: obj for obj in inc_res.scalars().all()}
            incidents = [by_id[pid] for pid in page_ids if pid in by_id]

        reviewed_inc_ids = set()
        user_role = getattr(current_user, "role", "")
        is_admin = user_role in ("Administrator", "SuperAdmin")

        if incidents and current_user:
            page_ids_all = [str(inc.id) for inc in incidents] + [str(inc.incident_id) for inc in incidents]
            user_filters = []
            if hasattr(current_user, "id") and current_user.id:
                user_filters.append(AnalystVerdictReview.reviewer_id == str(current_user.id))
            if hasattr(current_user, "username") and current_user.username:
                user_filters.append(AnalystVerdictReview.reviewer_id == str(current_user.username))

            if user_filters and page_ids_all:
                rev_q = select(AnalystVerdictReview.incident_id).where(
                    AnalystVerdictReview.incident_id.in_(page_ids_all),
                    or_(*user_filters)
                )
                rev_res = await self.db.execute(rev_q)
                reviewed_inc_ids = set(rev_res.scalars().all())

        items: List[IncidentListItemResponse] = []
        for inc in incidents:
            is_reviewed = (str(inc.id) in reviewed_inc_ids) or (str(inc.incident_id) in reviewed_inc_ids)
            # Server-enforced double-blind review isolation (P0):
            # 1. Admin: Can view unmasked unless explicitly passing ?blind_review=true
            # 2. SOC Analyst: Strictly double-blind. Client ?blind_review=false CANNOT bypass server protection.
            #    Only revealed IF this analyst has submitted an independent determination for this incident.
            # 3. Read-Only Viewer / others: Always masked / safely redacted.
            norm_role = (user_role or "").strip().lower()
            if is_admin:
                can_see_verdict = is_reviewed if blind_review else True
            elif norm_role in ("soc analyst", "analyst", "security analyst", "senior analyst", "soc_analyst", "senior_analyst"):
                can_see_verdict = is_reviewed
            else:
                can_see_verdict = False

            hist_res = None
            cleared_reason = None
            cleared_user = None
            cleared_time_epoch = None
            if can_see_verdict:
                if inc.ground_truth:
                    hist_res = inc.ground_truth.resolution
                    cleared_reason = inc.ground_truth.cleared_reason
                    cleared_user = inc.ground_truth.cleared_user
                    cleared_time_epoch = inc.ground_truth.cleared_time_epoch
                safe_ai_verdict = VerdictTrustworthinessEngine.normalize_ai_verdict_dict(inc.ai_verdict)
            else:
                hist_res = "[Hidden - Blind Review]"
                safe_ai_verdict = None

            r_uuid, l_rule_id, r_name = _infer_rule_identity(inc)
            items.append(
                IncidentListItemResponse(
                    id=inc.id,
                    incident_id=inc.incident_id,
                    rule_id=inc.rule_id,
                    rule_uuid=r_uuid,
                    logical_rule_id=l_rule_id,
                    rule_name=r_name,
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
                    cleared_reason=cleared_reason,
                    cleared_user=cleared_user,
                    cleared_time_epoch=cleared_time_epoch,
                    ai_verdict=safe_ai_verdict,
                    event_count=len(inc.events),
                    created_at=inc.created_at,
                )
            )

        matched_rules_summary = [
            IncidentMatchedRuleSummary(**b)
            for b in sorted(rule_buckets.values(), key=lambda x: (-x["incident_count"], x["logical_rule_id"]))
        ]
        summary_meta = {
            "exact_rule_id": canonical_rule.id if canonical_rule else (effective_rule_filter if effective_rule_filter else None),
            "exact_logical_rule_id": canonical_rule.rule_id if canonical_rule else None,
            "exact_rule_name": canonical_rule.name if canonical_rule else None,
            "distinct_rule_count": len(matched_rules_summary),
            "combines_multiple_rules": len(matched_rules_summary) > 1,
            "matched_rules": matched_rules_summary,
        }
        return items, total, summary_meta

    async def list_incidents(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        rule_id: Optional[str] = None,
        exact_rule_id: Optional[str] = None,
        resolution: Optional[str] = None,
        blind_review: bool = False,
        current_user: Optional[Any] = None,
    ) -> Tuple[List[IncidentListItemResponse], int]:
        items, total, _ = await self.list_incidents_with_rule_summary(
            page=page,
            page_size=page_size,
            search=search,
            severity=severity,
            status=status,
            rule_id=rule_id,
            exact_rule_id=exact_rule_id,
            resolution=resolution,
            blind_review=blind_review,
            current_user=current_user,
        )
        return items, total

    async def get_incident(
        self,
        identifier: str,  # can be UUID id or incident_id (e.g. "132438483")
        blind_review: bool = False,
        current_user: Optional[Any] = None,
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

        # Multi-Tenant Isolation Check (P1): Fail-closed cross-tenant protection
        user_customer = getattr(current_user, "customer", None)
        user_role = getattr(current_user, "role", "")
        if user_customer and user_role not in ("Administrator", "SuperAdmin"):
            if user_customer != "DEFAULT":
                # Tenant-specific user can ONLY access incidents strictly belonging to their customer tenant
                if inc.customer != user_customer:
                    return None
            else:
                # Platform default analyst with customer == "DEFAULT": restricted to platform DEFAULT scope
                if inc.customer and inc.customer not in ("DEFAULT", ""):
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

        # Check if analyst review has already been submitted for this incident by THIS reviewer
        user_role = getattr(current_user, "role", "")
        is_admin = user_role in ("Administrator", "SuperAdmin")
        has_analyst_review = False
        if current_user:
            user_filters = []
            if hasattr(current_user, "id") and current_user.id:
                user_filters.append(AnalystVerdictReview.reviewer_id == str(current_user.id))
            if hasattr(current_user, "username") and current_user.username:
                user_filters.append(AnalystVerdictReview.reviewer_id == str(current_user.username))

            if user_filters:
                rev_stmt = select(AnalystVerdictReview.id).where(
                    or_(AnalystVerdictReview.incident_id == str(inc.id), AnalystVerdictReview.incident_id == str(inc.incident_id)),
                    or_(*user_filters)
                ).limit(1)
                rev_res = await self.db.execute(rev_stmt)
                has_analyst_review = rev_res.scalar_one_or_none() is not None

        # Server-enforced double-blind review isolation (P0):
        # 1. Admin: Can view unmasked unless explicitly passing ?blind_review=true
        # 2. SOC Analyst: Strictly double-blind. Client ?blind_review=false CANNOT bypass server protection.
        #    Only revealed IF this analyst has submitted an independent determination for this incident.
        # 3. Read-Only Viewer / others: Always masked / safely redacted.
        norm_role = (user_role or "").strip().lower()
        if is_admin:
            can_see_verdict = has_analyst_review if blind_review else True
        elif norm_role in ("soc analyst", "analyst", "security analyst", "senior analyst", "soc_analyst", "senior_analyst"):
            can_see_verdict = has_analyst_review
        else:
            can_see_verdict = False

        # Build events response (purging ground-truth leakage in blind review mode)
        events_resp = [
            IncidentEventResponse(
                id=evt.id,
                event_id=evt.event_id,
                event_receive_time=evt.event_receive_time or inc.first_seen_epoch,
                event_type=evt.event_type,
                raw_log=evt.raw_log,
                attributes=(evt.attributes or {}) if can_see_verdict else sanitize_blind_review_payload(evt.attributes or {}),
            )
            for evt in inc.events
        ]

        # Ground truth (suppressed in blind review)
        gt_resp = None
        if can_see_verdict and inc.ground_truth:
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

        sanitized_raw_payload = (inc.raw_payload or {}) if can_see_verdict else sanitize_blind_review_payload(inc.raw_payload or {})
        safe_ai_verdict = (
            VerdictTrustworthinessEngine.normalize_ai_verdict_dict(inc.ai_verdict) if can_see_verdict
            else None
        )

        return IncidentDetailResponse(
            id=inc.id,
            incident_id=inc.incident_id,
            rule_id=inc.rule_id,
            rule_uuid=(inc.rule.id if inc.rule else inc.rule_id),
            logical_rule_id=(inc.rule.rule_id if inc.rule else inc.event_type),
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
            ai_verdict=safe_ai_verdict,
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

