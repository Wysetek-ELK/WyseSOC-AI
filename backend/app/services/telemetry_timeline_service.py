from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from sqlalchemy.orm import selectinload

from app.models.incident import Incident, IncidentEvent, HistoricalGroundTruth
from app.models.token_usage import TokenUsageRecord
from app.models.telemetry_timeline import TelemetryTimelineRecord
from app.models.investigation import Investigation


class TelemetryTimelineService:
    """
    Historical Telemetry Timeline Service on Server 1.
    Chronologically compiles, indexes, and serves multi-stage telemetry milestones:
    - Initial signal observation & raw security event logs
    - SIEM alert correlation and creation
    - Server 1 persistent ingestion
    - Verdict Triage Agent inference & token consumption
    - Human Review Queue assignment & analyst verdict
    - Ticket closure and ground-truth resolution
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def _format_epoch(self, epoch_ms: Optional[int]) -> str:
        if not epoch_ms:
            return "N/A"
        ms = epoch_ms if epoch_ms > 1e11 else epoch_ms * 1000
        try:
            return datetime.utcfromtimestamp(ms / 1000.0).isoformat() + "Z"
        except Exception:
            return "N/A"

    async def get_incident_timeline(self, incident_id: str) -> Dict[str, Any]:
        """
        Builds the complete historical telemetry timeline for an incident from Server 1 persistent storage.
        """
        stmt = (
            select(Incident)
            .where(or_(Incident.incident_id == incident_id, Incident.id == incident_id))
            .options(
                selectinload(Incident.events),
                selectinload(Incident.ground_truth),
                selectinload(Incident.rule),
            )
        )
        res = await self.db.execute(stmt)
        incident = res.scalars().first()
        if not incident:
            return {"success": False, "error": f"Incident {incident_id} not found", "milestones": []}

        # Query token consumption records on Server 1 for this incident
        tok_stmt = (
            select(TokenUsageRecord)
            .where(TokenUsageRecord.incident_id == incident.incident_id)
            .order_by(TokenUsageRecord.timestamp.asc())
        )
        tok_res = await self.db.execute(tok_stmt)
        token_records = tok_res.scalars().all()

        total_prompt_tokens = sum(t.prompt_tokens for t in token_records)
        total_completion_tokens = sum(t.completion_tokens for t in token_records)
        total_tokens_used = sum(t.total_tokens for t in token_records)

        # Query explicit timeline entries on Server 1
        explicit_stmt = (
            select(TelemetryTimelineRecord)
            .where(TelemetryTimelineRecord.incident_id == incident.incident_id)
            .order_by(TelemetryTimelineRecord.timestamp.asc())
        )
        explicit_res = await self.db.execute(explicit_stmt)
        explicit_entries = explicit_res.scalars().all()

        milestones: List[Dict[str, Any]] = []

        # 1. Milestone: First Observed Telemetry
        if incident.first_seen_epoch:
            milestones.append({
                "stage": "OBSERVATION",
                "type": "FIRST_SEEN",
                "title": "First Telemetry Signal Observed",
                "timestamp": self._format_epoch(incident.first_seen_epoch),
                "epoch_ms": incident.first_seen_epoch,
                "source": "Network / Endpoint Telemetry",
                "description": f"Initial security event signal detected for {incident.event_type} on {incident.reporting_device or 'endpoint'}.",
                "icon": "Eye",
                "severity": incident.severity,
                "metadata": {
                    "source_ip": incident.source_ip,
                    "reporting_device": incident.reporting_device,
                    "reporting_ip": incident.reporting_ip,
                },
            })

        # 2. Raw Events Sequence
        for idx, evt in enumerate(incident.events):
            t_ms = evt.event_receive_time or incident.first_seen_epoch
            raw_excerpt = (evt.raw_log[:160] + "...") if evt.raw_log and len(evt.raw_log) > 160 else (evt.raw_log or "Raw telemetry log recorded")
            milestones.append({
                "stage": "TELEMETRY",
                "type": "RAW_EVENT",
                "title": f"Raw Telemetry Event #{idx + 1} ({evt.event_type})",
                "timestamp": self._format_epoch(t_ms),
                "epoch_ms": t_ms,
                "source": "SIEM Raw Ingestion Stream",
                "description": raw_excerpt,
                "icon": "FileText",
                "severity": incident.severity,
                "metadata": {
                    "event_id": evt.event_id,
                    "attribute_count": len(evt.attributes or {}),
                    "attributes": evt.attributes,
                },
            })

        # 3. Milestone: SIEM Incident Ticket Created
        if incident.created_at_epoch:
            milestones.append({
                "stage": "CORRELATION",
                "type": "SIEM_ALERT_CREATED",
                "title": f"SIEM Alert Triggered: {incident.title or incident.event_type}",
                "timestamp": self._format_epoch(incident.created_at_epoch),
                "epoch_ms": incident.created_at_epoch,
                "source": "SIEM Detection Engine",
                "description": f"Threshold met. Severity: {incident.severity}. Correlated across observed telemetry events.",
                "icon": "AlertTriangle",
                "severity": incident.severity,
                "metadata": {
                    "rule_id": incident.rule_id,
                    "customer": incident.customer,
                    "status": incident.status_name,
                },
            })

        # 4. Milestone: Last Observed Telemetry
        if incident.last_seen_epoch and incident.last_seen_epoch != incident.first_seen_epoch:
            milestones.append({
                "stage": "OBSERVATION",
                "type": "LAST_SEEN",
                "title": "Last Telemetry Activity Observed",
                "timestamp": self._format_epoch(incident.last_seen_epoch),
                "epoch_ms": incident.last_seen_epoch,
                "source": "Network / Endpoint Telemetry",
                "description": "Final telemetry activity captured in this correlation burst.",
                "icon": "Clock",
                "severity": incident.severity,
                "metadata": {},
            })

        # 5. Milestone: Ingestion into Server 1
        ingest_time_ms = int(incident.created_at.timestamp() * 1000) if incident.created_at else None
        milestones.append({
            "stage": "INGESTION",
            "type": "SERVER_1_INGESTED",
            "title": "Archived in Server 1 Persistent DB",
            "timestamp": incident.created_at.isoformat() + "Z" if incident.created_at else "N/A",
            "epoch_ms": ingest_time_ms,
            "source": "Sentinel Ingest Worker (Server 1 Storage)",
            "description": f"Incident {incident.incident_id} successfully parsed, normalized, and committed to local database.",
            "icon": "Database",
            "severity": "INFO",
            "metadata": {
                "events_count": len(incident.events),
                "raw_payload_bytes": len(str(incident.raw_payload or "")),
            },
        })

        # 6. Milestone: AI Verdict Triage Agent Evaluation
        if incident.ai_verdict:
            av = incident.ai_verdict
            eval_dt = av.get("evaluated_at")
            eval_epoch = None
            if eval_dt:
                try:
                    eval_epoch = int(datetime.fromisoformat(eval_dt.replace("Z", "")).timestamp() * 1000)
                except Exception:
                    pass

            v_p_tok = av.get("prompt_tokens", 0)
            v_c_tok = av.get("completion_tokens", 0)
            v_t_tok = av.get("total_tokens", v_p_tok + v_c_tok)

            milestones.append({
                "stage": "TRIAGE",
                "type": "AGENT_EVALUATED",
                "title": f"Verdict Triage Agent: {av.get('verdict', 'UNKNOWN')} ({int(av.get('confidence', 0))}% Conf)",
                "timestamp": eval_dt or "N/A",
                "epoch_ms": eval_epoch,
                "source": f"Verdict Triage Agent ({av.get('model_identifier', 'LLM')})",
                "description": av.get("reason", "Analytical evaluation complete."),
                "icon": "Bot",
                "severity": "HIGH" if av.get("verdict") == "TRUE_POSITIVE" else ("LOW" if av.get("verdict") == "FALSE_POSITIVE" else "MEDIUM"),
                "token_bifurcation": {
                    "prompt_tokens": v_p_tok,
                    "completion_tokens": v_c_tok,
                    "total_tokens": v_t_tok,
                    "latency_ms": av.get("latency_ms", 0),
                    "model": av.get("model_identifier", "Unknown"),
                },
                "metadata": {
                    "supporting_evidence": av.get("supporting_evidence", []),
                    "missing_evidence": av.get("missing_evidence", []),
                },
            })

        # 7. Milestone: SIEM Ground Truth Resolution / Cleared
        gt = incident.ground_truth
        if gt and gt.cleared_time_epoch:
            milestones.append({
                "stage": "RESOLUTION",
                "type": "TICKET_CLEARED",
                "title": f"SIEM Ticket Resolved: {gt.resolution}",
                "timestamp": self._format_epoch(gt.cleared_time_epoch),
                "epoch_ms": gt.cleared_time_epoch,
                "source": "SIEM Ground Truth / Operations",
                "description": f"Ticket cleared by {gt.cleared_user or 'analyst'}. Reason: {gt.cleared_reason or gt.comments or 'None'}",
                "icon": "CheckCircle2",
                "severity": "LOW" if "False" in gt.resolution else "HIGH",
                "metadata": {
                    "cleared_user": gt.cleared_user,
                    "is_ml_generated": gt.is_ml_generated,
                },
            })

        # Sort milestones chronologically
        milestones.sort(key=lambda x: x.get("epoch_ms") or 0)

        return {
            "success": True,
            "incident_id": incident.incident_id,
            "title": incident.title,
            "storage_node": "Server 1 Persistent Storage",
            "token_summary": {
                "total_tokens": total_tokens_used or (incident.ai_verdict or {}).get("total_tokens", 0),
                "prompt_tokens": total_prompt_tokens or (incident.ai_verdict or {}).get("prompt_tokens", 0),
                "completion_tokens": total_completion_tokens or (incident.ai_verdict or {}).get("completion_tokens", 0),
                "records_count": len(token_records),
            },
            "milestone_count": len(milestones),
            "milestones": milestones,
        }

    async def get_global_telemetry_timeline(
        self,
        limit: int = 50,
        stage: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Returns global telemetry milestones logged on Server 1 across all incidents.
        """
        query = select(TelemetryTimelineRecord).order_by(desc(TelemetryTimelineRecord.timestamp))
        if stage:
            query = query.where(TelemetryTimelineRecord.stage == stage.upper().strip())
        query = query.limit(limit)

        res = await self.db.execute(query)
        records = res.scalars().all()

        items = []
        for r in records:
            items.append({
                "id": r.id,
                "incident_id": r.incident_id,
                "event_type": r.event_type,
                "stage": r.stage,
                "summary": r.summary,
                "source": r.source,
                "severity": r.severity,
                "source_ip": r.source_ip,
                "reporting_device": r.reporting_device,
                "epoch_ms": r.epoch_ms,
                "token_count": r.token_count,
                "timestamp": r.timestamp.isoformat() + "Z",
                "details": r.details,
            })

        return {
            "success": True,
            "storage_node": "Server 1 Database",
            "total_records": len(items),
            "timeline": items,
        }

