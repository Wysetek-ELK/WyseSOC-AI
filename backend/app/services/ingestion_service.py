import json
import io
import re
from datetime import datetime
from app.utils.datetime_utils import utc_now
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.models.incident import Incident, IncidentEvent, HistoricalGroundTruth
from app.models.rule import Rule
from app.models.import_job import ImportJob
from app.models.audit import AuditLog
from app.services.rule_parser import RuleParser
from app.services.historical_ground_truth_validator import HistoricalGroundTruthValidator
from app.utils.zip_guard import ZipGuard, ZipSecurityException


def parse_any_timestamp(val: Any) -> Optional[int]:
    """
    Parses timestamp from integer, float, string epoch (seconds or ms),
    or common date/ISO strings into epoch milliseconds.
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        if val <= 0:
            return None
        # Heuristic: < 1e11 is in seconds (e.g. 1731000000), convert to ms
        if val < 1e11:
            return int(val * 1000)
        return int(val)
    if isinstance(val, str):
        val_str = val.strip()
        if not val_str:
            return None
        try:
            num = float(val_str)
            if num <= 0:
                return None
            if num < 1e11:
                return int(num * 1000)
            return int(num)
        except ValueError:
            pass
        # Common ISO and formatted date strings
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%b %d, %Y %I:%M:%S %p",
            "%b %d, %Y %H:%M:%S",
        ):
            try:
                dt = datetime.strptime(val_str, fmt)
                return int(dt.timestamp() * 1000)
            except ValueError:
                continue
        try:
            dt = datetime.fromisoformat(val_str.replace("Z", "+00:00"))
            return int(dt.timestamp() * 1000)
        except Exception:
            pass
    return None


def extract_incident_network_endpoints(raw_data: Dict[str, Any]) -> Tuple[str, str, str]:
    """Extracts (source_ip, reporting_ip, reporting_device) from FortiSIEM incident JSON or aliases."""
    src_ip = str(raw_data.get("sourceIp") or raw_data.get("srcIpAddr") or raw_data.get("src_ip") or raw_data.get("source_ip") or "").strip()
    if not src_ip and raw_data.get("incidentSrc"):
        m = re.search(r'(?:srcIpAddr|srcIp|src|sourceIp)\s*[:=]\s*([0-9a-fA-F\.:]+)', str(raw_data["incidentSrc"]), re.IGNORECASE)
        if m:
            src_ip = m.group(1).strip()
    if not src_ip:
        raw_evts = raw_data.get("rawEvents") or raw_data.get("triggeringEvents") or []
        if isinstance(raw_evts, list) and raw_evts:
            for revt in raw_evts:
                if isinstance(revt, dict):
                    attrs = revt.get("attributes") or revt.get("attribute") or {}
                    if isinstance(attrs, dict) and attrs.get("Source IP"):
                        src_ip = str(attrs["Source IP"]).strip()
                        break
                    raw_msg = revt.get("rawMessage") or revt.get("rawEventLog") or ""
                    if raw_msg:
                        m = re.search(r'\bsrcip=([0-9a-fA-F\.:]+)', str(raw_msg))
                        if m:
                            src_ip = m.group(1).strip()
                            break

    rpt_ip = str(raw_data.get("reportingIp") or raw_data.get("incidentRptIp") or raw_data.get("reporting_ip") or "").strip()
    rpt_dev = str(raw_data.get("reportingDevice") or raw_data.get("incidentRptDevName") or raw_data.get("reporting_device") or "").strip()

    return src_ip, rpt_ip, rpt_dev


def extract_incident_timestamps(raw_data: Dict[str, Any]) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int]]:
    """
    Extracts (first_seen, last_seen, created_at, updated_at) in epoch milliseconds
    from any FortiSIEM JSON, XML-dict, or SIEM incident representation.
    """
    first_seen_candidates = [
        "incidentFirstSeen", "firstSeen", "incidentFirstSeenTime", "incidentStartTime",
        "startTime", "first_seen", "incidentOccurTime", "incidentTime", "phIncidentTime",
        "incidentDate", "eventTime", "time"
    ]
    last_seen_candidates = [
        "incidentLastSeen", "lastSeen", "incidentLastSeenTime", "incidentEndTime",
        "endTime", "last_seen", "incidentClearedTime"
    ]
    created_at_candidates = [
        "incidentCreatedTime", "createdAt", "creationTime", "createdTime", "incidentTime",
        "incidentRptTime", "incidentDate", "incidentOccurTime", "firstSeen",
        "incidentFirstSeen", "created_at"
    ]
    updated_at_candidates = [
        "incidentUpdatedTime", "updatedAt", "lastModifiedTime", "updateTime", "modifiedTime", "updated_at"
    ]

    def _find(keys: List[str]) -> Optional[int]:
        for k in keys:
            if k in raw_data and raw_data[k] is not None:
                parsed = parse_any_timestamp(raw_data[k])
                if parsed is not None:
                    return parsed
        return None

    first_seen = _find(first_seen_candidates)
    last_seen = _find(last_seen_candidates)
    created_at_epoch = _find(created_at_candidates)
    updated_at_epoch = _find(updated_at_candidates)

    # Check rawEvents / triggeringEvents if first_seen or created_at_epoch are still missing
    if not first_seen or not created_at_epoch:
        raw_evts = raw_data.get("rawEvents") or raw_data.get("triggeringEvents") or []
        if isinstance(raw_evts, list) and len(raw_evts) > 0:
            for revt in raw_evts:
                if not isinstance(revt, dict):
                    continue
                attrs = revt.get("attribute", {}) if isinstance(revt.get("attribute"), dict) else {}
                evt_ts = (
                    parse_any_timestamp(attrs.get("Event Receive Time"))
                    or parse_any_timestamp(attrs.get("Device Time"))
                    or parse_any_timestamp(revt.get("eventReceiveTime"))
                    or parse_any_timestamp(revt.get("deviceTime"))
                    or parse_any_timestamp(revt.get("receiveTime"))
                )
                if evt_ts:
                    if not first_seen:
                        first_seen = evt_ts
                    if not created_at_epoch:
                        created_at_epoch = evt_ts
                    if not last_seen:
                        last_seen = evt_ts
                    break

    # Mutual fallbacks so occurrence time is preserved
    if not first_seen and created_at_epoch:
        first_seen = created_at_epoch
    elif not created_at_epoch and first_seen:
        created_at_epoch = first_seen

    if not last_seen and first_seen:
        last_seen = first_seen

    return first_seen, last_seen, created_at_epoch, updated_at_epoch


def extract_event_data(
    revt: Dict[str, Any],
    incident_id: str,
    idx: int,
    fallback_event_type: str = ""
) -> Tuple[str, Optional[int], str, str, Dict[str, Any]]:
    """
    Extracts (evt_id, evt_receive_time, evt_type, raw_log, attributes)
    from a raw event object across FortiSIEM live REST APIs (e.g. rawMessage, attributes dict)
    and offline fixture archives (e.g. attribute dict, Raw Event Log).
    """
    attrs = {}
    if isinstance(revt.get("attributes"), dict):
        attrs = dict(revt["attributes"])
    elif isinstance(revt.get("attribute"), dict):
        attrs = dict(revt["attribute"])
    elif isinstance(revt.get("eventAttributes"), dict):
        attrs = dict(revt["eventAttributes"])

    # If no nested attributes container exists, use the event object itself
    if not attrs:
        ignored_keys = {"rawMessage", "rawEventLog", "rawLog", "dataStr", "attributes", "attribute", "eventAttributes"}
        attrs = {k: v for k, v in revt.items() if k not in ignored_keys and v is not None}

    # Extract raw event log
    raw_log = ""
    for raw_candidate in (
        attrs.get("Raw Event Log"),
        attrs.get("rawMessage"),
        attrs.get("rawEventLog"),
        revt.get("rawMessage"),
        revt.get("rawEventLog"),
        revt.get("rawLog"),
        revt.get("rawEvent"),
        revt.get("rawMsg"),
        revt.get("eventLog"),
        revt.get("message"),
        revt.get("dataStr"),
    ):
        if raw_candidate:
            raw_log = str(raw_candidate).strip()
            break

    # Ensure Raw Event Log is present in attributes for consistent inspector display
    if raw_log and "Raw Event Log" not in attrs:
        attrs["Raw Event Log"] = raw_log

    # Extract event ID
    evt_id = str(
        revt.get("eventId")
        or revt.get("id")
        or revt.get("nid")
        or attrs.get("Event ID")
        or attrs.get("EventId")
        or f"{incident_id}_evt_{idx}"
    )

    # Extract receive timestamp
    evt_receive_time = (
        parse_any_timestamp(attrs.get("Event Receive Time"))
        or parse_any_timestamp(attrs.get("Device Time"))
        or parse_any_timestamp(attrs.get("deviceTime"))
        or parse_any_timestamp(revt.get("receiveTime"))
        or parse_any_timestamp(revt.get("eventReceiveTime"))
        or parse_any_timestamp(revt.get("deviceTime"))
        or parse_any_timestamp(revt.get("phRecvTime"))
    )

    # Extract event type
    evt_type = str(
        attrs.get("Event Type")
        or attrs.get("eventType")
        or revt.get("eventType")
        or revt.get("eventName")
        or fallback_event_type
    )

    return evt_id, evt_receive_time, evt_type, raw_log, attrs


class IngestionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_import_job(
        self,
        filename: str,
        file_type: str,
        file_size: int,
        username: Optional[str] = None
    ) -> ImportJob:
        job = ImportJob(
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            status="PROCESSING",
            created_by=username or "system",
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def ingest_zip(
        self,
        file_bytes: bytes,
        filename: str,
        username: Optional[str] = None
    ) -> Tuple[ImportJob, Dict[str, Any]]:
        job = await self.create_import_job(filename, "ZIP", len(file_bytes), username)

        try:
            entries = ZipGuard.validate_and_extract_entries(io.BytesIO(file_bytes))
        except ZipSecurityException as e:
            job.status = "FAILED"
            job.error_details = [{"error": str(e), "file": filename}]
            job.completed_at = utc_now()
            await self.db.commit()
            return job, {
                "job_id": job.id,
                "status": "FAILED",
                "filename": filename,
                "total_found": 0,
                "imported": 0,
                "duplicates": 0,
                "rules_detected": 0,
                "errors": 1,
                "error_messages": [str(e)],
            }

        job.total_files = len(entries)

        # 1. First pass: detect and ingest rule text files (e.g. Rule_info.txt, *.txt)
        rules_found = 0
        rule_map: Dict[str, Rule] = {}

        # Fetch existing rules from DB to map against
        stmt_rules = select(Rule)
        res_rules = await self.db.execute(stmt_rules)
        for r in res_rules.scalars().all():
            rule_map[r.event_type] = r

        for path, content in entries:
            norm_path = path.lower()
            if norm_path.endswith(".txt") and ("rule" in norm_path or "info" in norm_path):
                try:
                    text = content.decode("utf-8", errors="ignore")
                    parsed_rule = RuleParser.parse_rule_text(text)
                    if parsed_rule["event_type"]:
                        # Check if rule already exists in DB
                        existing_rule = rule_map.get(parsed_rule["event_type"])
                        if not existing_rule:
                            # Also check DB directly
                            q = await self.db.execute(
                                select(Rule).where(Rule.event_type == parsed_rule["event_type"])
                            )
                            existing_rule = q.scalar_one_or_none()

                        if existing_rule:
                            # Update existing rule
                            existing_rule.name = parsed_rule["name"]
                            existing_rule.description = parsed_rule["description"]
                            existing_rule.severity = parsed_rule["severity"]
                            existing_rule.status = parsed_rule["status"]
                            existing_rule.data_source = parsed_rule["data_source"]
                            existing_rule.detection_tech = parsed_rule["detection_tech"]
                            existing_rule.pattern_logic = parsed_rule["pattern_logic"]
                            existing_rule.remediation = parsed_rule["remediation"]
                            existing_rule.raw_rule_text = parsed_rule["raw_rule_text"]
                            existing_rule.parsed_metadata = parsed_rule["parsed_metadata"]
                            rule_map[existing_rule.event_type] = existing_rule
                        else:
                            new_rule = Rule(
                                rule_id=parsed_rule["rule_id"],
                                name=parsed_rule["name"],
                                event_type=parsed_rule["event_type"],
                                description=parsed_rule["description"],
                                severity=parsed_rule["severity"],
                                status=parsed_rule["status"],
                                data_source=parsed_rule["data_source"],
                                detection_tech=parsed_rule["detection_tech"],
                                evaluation_mode=parsed_rule["evaluation_mode"],
                                pattern_logic=parsed_rule["pattern_logic"],
                                remediation=parsed_rule["remediation"],
                                raw_rule_text=parsed_rule["raw_rule_text"],
                                parsed_metadata=parsed_rule["parsed_metadata"],
                            )
                            self.db.add(new_rule)
                            await self.db.flush()
                            rule_map[new_rule.event_type] = new_rule
                        rules_found += 1
                except Exception as e:
                    job.error_details.append({"file": path, "error": f"Failed to parse rule file: {str(e)}"})

        await self.db.commit()

        # 2. Second pass: ingest JSON incident files
        imported = 0
        duplicates = 0
        errors = 0
        error_msgs = []

        for path, content in entries:
            if not path.lower().endswith(".json"):
                continue

            try:
                raw_json = json.loads(content.decode("utf-8"))
                result, msg = await self._ingest_single_incident_dict(
                    raw_data=raw_json,
                    import_job_id=job.id,
                    rule_map=rule_map,
                    source_filename=path
                )
                if result == "imported":
                    imported += 1
                elif result == "duplicate":
                    duplicates += 1
                else:
                    errors += 1
                    job.error_details.append({"file": path, "error": msg})
                    error_msgs.append(f"{path}: {msg}")
            except Exception as e:
                errors += 1
                job.error_details.append({"file": path, "error": f"JSON parse error: {str(e)}"})
                error_msgs.append(f"{path}: {str(e)}")

        job.imported_count = imported
        job.duplicate_count = duplicates
        job.error_count = errors
        job.status = "COMPLETED" if errors == 0 else "COMPLETED_WITH_ERRORS"
        job.completed_at = utc_now()

        # Audit log entry
        audit = AuditLog(
            username=username or "system",
            action="IMPORT_ZIP",
            resource_type="IMPORT_JOB",
            resource_id=job.id,
            details={
                "filename": filename,
                "total_files": len(entries),
                "imported": imported,
                "duplicates": duplicates,
                "errors": errors,
                "rules_found": rules_found,
            }
        )
        self.db.add(audit)
        await self.db.commit()
        await self.db.refresh(job)

        return job, {
            "job_id": job.id,
            "status": job.status,
            "filename": filename,
            "total_found": len(entries),
            "imported": imported,
            "duplicates": duplicates,
            "rules_detected": rules_found,
            "errors": errors,
            "error_messages": error_msgs,
        }

    async def ingest_single_json(
        self,
        raw_data: Dict[str, Any],
        filename: str,
        username: Optional[str] = None
    ) -> Tuple[ImportJob, str, str]:
        job = await self.create_import_job(filename, "JSON", len(json.dumps(raw_data)), username)
        job.total_files = 1

        # Fetch rules
        rule_map = {}
        stmt_rules = select(Rule)
        res_rules = await self.db.execute(stmt_rules)
        for r in res_rules.scalars().all():
            rule_map[r.event_type] = r

        result, msg = await self._ingest_single_incident_dict(
            raw_data=raw_data,
            import_job_id=job.id,
            rule_map=rule_map,
            source_filename=filename
        )

        if result == "imported":
            job.imported_count = 1
            job.status = "COMPLETED"
        elif result == "duplicate":
            job.duplicate_count = 1
            job.status = "COMPLETED"
        else:
            job.error_count = 1
            job.status = "FAILED"
            job.error_details = [{"file": filename, "error": msg}]

        job.completed_at = utc_now()
        await self.db.commit()
        await self.db.refresh(job)
        return job, result, msg

    async def _ingest_single_incident_dict(
        self,
        raw_data: Dict[str, Any],
        import_job_id: str,
        rule_map: Dict[str, Rule],
        source_filename: str = ""
    ) -> Tuple[str, str]:
        # Validate critical identifiers
        incident_id = str(raw_data.get("incidentId") or raw_data.get("id") or "").strip()
        if not incident_id:
            return "error", "Missing 'incidentId' or 'id' in incident JSON"

        event_type = str(raw_data.get("eventType") or "").strip()
        if not event_type:
            return "error", "Missing 'eventType' in incident JSON"

        # Check for duplicate
        dup_stmt = select(Incident).where(Incident.incident_id == incident_id)
        dup_res = await self.db.execute(dup_stmt)
        if dup_res.scalar_one_or_none():
            return "duplicate", f"Incident '{incident_id}' already exists in database"

        # Find matching rule in local cache/database
        rule = rule_map.get(event_type) or rule_map.get(str(raw_data.get("eventName") or "").strip())
        if not rule:
            # Query local DB as fallback
            rule_name_candidate = str(raw_data.get("eventName") or raw_data.get("title") or "").strip()
            filters = [Rule.event_type == event_type, Rule.rule_id == event_type]
            if rule_name_candidate:
                filters.append(Rule.name == rule_name_candidate)
            rq = await self.db.execute(select(Rule).where(or_(*filters)))
            rule = rq.scalar_one_or_none()
            if rule:
                rule_map[event_type] = rule
                rule_map[rule.rule_id] = rule
            else:
                # CACHE MISS: Dynamically extract, register, and persist rule locally from incident telemetry
                rule = await self._auto_create_rule_from_incident(raw_data, event_type)
                if rule:
                    rule_map[event_type] = rule
                    rule_map[rule.rule_id] = rule

        # Extract normalized fields
        severity = str(raw_data.get("severity") or "MEDIUM").upper()
        if severity not in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"]:
            # Map numeric or vendor severity if needed
            ev_sev = str(raw_data.get("eventSeverity") or "").upper()
            if "CRIT" in ev_sev or "HIGH" in ev_sev:
                severity = "HIGH"
            elif "LOW" in ev_sev or "INFO" in ev_sev:
                severity = "LOW"
            else:
                severity = "MEDIUM"

        raw_status = raw_data.get("incidentStatus") or raw_data.get("statusName") or raw_data.get("status") or raw_data.get("Incident Status")
        status_code = 1
        try:
            if raw_status is not None:
                status_code = int(raw_status)
        except Exception:
            status_code = 2 if str(raw_status).strip().lower() in ("closed", "manually cleared", "auto cleared", "resolved") else 1

        raw_status_str = str(raw_status or "").strip()
        if status_code == 2 or raw_status_str.lower() in ("closed", "manually cleared", "auto cleared", "resolved"):
            status_code = 2
            status_name = "Manually Cleared" if "manually" in raw_status_str.lower() else ("Closed" if not raw_status_str or raw_status_str == "2" else raw_status_str)
        else:
            status_code = 1
            status_name = "Open"

        # Timestamps: robust extraction across FortiSIEM APIs, formats, and event telemetry
        first_seen, last_seen, created_at_epoch, updated_at_epoch = extract_incident_timestamps(raw_data)
        src_ip, rpt_ip, rpt_dev = extract_incident_network_endpoints(raw_data)

        incident = Incident(
            incident_id=incident_id,
            rule_id=rule.id if rule else None,
            import_job_id=import_job_id,
            event_type=event_type,
            title=str(raw_data.get("title") or raw_data.get("eventName") or raw_data.get("incidentTitle") or f"Incident {incident_id}"),
            description=str(raw_data.get("description") or ""),
            detail=str(raw_data.get("detail") or ""),
            severity=severity,
            event_severity=str(raw_data.get("eventSeverity") or ""),
            status_code=status_code,
            status_name=status_name,
            category=str(raw_data.get("category") or ""),
            subcategory=str(raw_data.get("subcategory") or ""),
            source_ip=src_ip,
            reporting_device=rpt_dev,
            reporting_ip=rpt_ip,
            customer=str(raw_data.get("customer") or ""),
            ticket_id=str(raw_data.get("ticketId") or ""),
            first_seen_epoch=first_seen,
            last_seen_epoch=last_seen,
            created_at_epoch=created_at_epoch,
            updated_at_epoch=updated_at_epoch,
            raw_payload=raw_data,  # Entire original JSON stored unmodified
        )
        self.db.add(incident)
        await self.db.flush()

        # Ingest raw events
        raw_events = raw_data.get("rawEvents") or raw_data.get("triggeringEvents") or []
        if isinstance(raw_events, list):
            for idx, revt in enumerate(raw_events):
                if not isinstance(revt, dict):
                    continue
                evt_id, evt_recv, evt_t, raw_log, attrs = extract_event_data(
                    revt, incident_id, idx, fallback_event_type=event_type
                )
                evt_obj = IncidentEvent(
                    incident_id=incident.id,
                    event_id=evt_id,
                    event_receive_time=evt_recv,
                    event_type=evt_t,
                    raw_log=raw_log,
                    attributes=attrs,
                )
                self.db.add(evt_obj)

        # ISOLATED GROUND TRUTH
        raw_res = str(
            raw_data.get("resolution") or
            raw_data.get("incidentResolution") or
            raw_data.get("incidentReso") or
            raw_data.get("incidentRes") or
            raw_data.get("Resolution") or
            ""
        ).strip()
        if raw_res.lower() in ("open", "none", "null", "unassigned", "0"):
            resolution = ""
        elif "false positive" in raw_res.lower() or raw_res.lower() == "fp":
            resolution = "False Positive"
        elif "true positive" in raw_res.lower() or raw_res.lower() == "tp":
            resolution = "True Positive"
        else:
            resolution = raw_res

        cleared_reason = str(
            raw_data.get("clearedReason") or
            raw_data.get("clearReason") or
            raw_data.get("incidentClearedReason") or
            raw_data.get("Cleared Reason") or
            ""
        ).strip()

        comments = str(
            raw_data.get("comments") or
            raw_data.get("incidentComments") or
            raw_data.get("comment") or
            raw_data.get("notes") or
            raw_data.get("Comments") or
            ""
        ).strip()

        cleared_user = str(
            raw_data.get("clearedUser") or
            raw_data.get("cmsClearUser") or
            raw_data.get("clearUser") or
            raw_data.get("caseUser") or
            raw_data.get("case_user") or
            raw_data.get("Cleared User") or
            raw_data.get("Case User") or
            ""
        ).strip()

        cleared_time = parse_any_timestamp(
            raw_data.get("clearedTime") or
            raw_data.get("incidentClearedTime") or
            raw_data.get("clearTime") or
            raw_data.get("Cleared Time")
        )
        if cleared_time == 0:
            cleared_time = None

        resolved_at = parse_any_timestamp(
            raw_data.get("resolvedAt") or
            raw_data.get("incidentResolvedTime") or
            raw_data.get("incidentResTime") or
            raw_data.get("Resolved Time")
        )
        if resolved_at == 0:
            resolved_at = None
        if resolved_at is None and cleared_time is not None:
            resolved_at = cleared_time

        # If incident had clearing details or resolution, ensure status reflects Closed / Manually Cleared
        if (cleared_reason or cleared_user or (cleared_time and cleared_time > 0) or resolution) and incident.status_code == 1:
            incident.status_code = 2
            incident.status_name = "Manually Cleared" if cleared_user or "manually" in str(raw_status or "").lower() else "Closed"

        is_ml_generated = HistoricalGroundTruthValidator.detect_automated_or_ml_text(
            comments=comments,
            resolution=resolution,
            cleared_reason=cleared_reason,
            cleared_user=cleared_user,
            raw_status=str(raw_status or ""),
        )

        ground_truth = HistoricalGroundTruth(
            incident_id=incident.id,
            resolution=resolution,
            cleared_reason=cleared_reason,
            comments=comments,
            cleared_user=cleared_user,
            cleared_time_epoch=cleared_time,
            resolved_at_epoch=resolved_at,
            is_ml_generated=is_ml_generated,
        )
        self.db.add(ground_truth)

        # Record Historical Telemetry Ingestion Timeline on Server 1
        from app.models.telemetry_timeline import TelemetryTimelineRecord
        self.db.add(
            TelemetryTimelineRecord(
                incident_id=incident_id,
                event_type="TELEMETRY_INGESTION",
                stage="INGESTION",
                summary=f"Incident telemetry ingested into Server 1 persistent storage: {len(raw_events)} raw events captured.",
                source="Sentinel Ingest Worker (Server 1 Storage)",
                severity=severity,
                source_ip=incident.source_ip,
                reporting_device=incident.reporting_device,
                epoch_ms=created_at_epoch or int(utc_now().timestamp() * 1000),
                token_count=0,
                details={
                    "event_count": len(raw_events),
                    "event_type": event_type,
                    "customer": str(raw_data.get("customer") or ""),
                },
            )
        )

        await self.db.commit()
        return "imported", f"Successfully imported incident {incident_id}"

    async def _auto_create_rule_from_incident(
        self,
        raw_data: Dict[str, Any],
        event_type: str,
    ) -> Optional[Rule]:
        """
        Cache-miss handler: Automatically creates and registers a local Rule record
        from incident metadata when a rule does not exist in the local database.
        Also synthesizes an initial PromptVersion via PromptStudioService.
        """
        clean_event_type = (event_type or "").strip()
        if not clean_event_type:
            return None

        # Double check if rule was created concurrently
        check_q = await self.db.execute(select(Rule).where(
            or_(
                Rule.event_type == clean_event_type,
                Rule.rule_id == clean_event_type
            )
        ))
        existing = check_q.scalar_one_or_none()
        if existing:
            return existing

        rule_name_candidate = str(raw_data.get("eventName") or raw_data.get("title") or clean_event_type).strip()
        incident_id = str(raw_data.get("incidentId") or raw_data.get("id") or "").strip()

        # 1. Attempt to pull official rule configuration from live FortiSIEM Supervisor API
        live_rule: Optional[Dict[str, Any]] = None
        try:
            from app.services.fortisiem_service import FortiSIEMService
            fortisiem_svc = FortiSIEMService(self.db)
            live_rule = await fortisiem_svc.fetch_rule_from_siem(
                rule_identifier=clean_event_type,
                rule_name=rule_name_candidate,
                incident_id=incident_id if incident_id else None,
            )
        except Exception:
            pass

        # 2. Extract normalized rule parameters (from live SIEM rule API or fallback to incident telemetry)
        if live_rule:
            rule_id = live_rule.get("rule_id") or clean_event_type
            rule_name = live_rule.get("name") or rule_name_candidate
            severity = live_rule.get("severity") or "MEDIUM"
            category = live_rule.get("category") or "Security"
            sub_cat = live_rule.get("sub_category") or "Policy Violation"
            data_src = live_rule.get("data_source") or "FortiSIEM"
            pattern = live_rule.get("pattern_logic") or ""
            desc = live_rule.get("description") or f"Detection rule '{rule_name}' ({category} / {sub_cat}) pulled live from FortiSIEM."
            raw_text = live_rule.get("raw_rule_text") or f"Rule: {rule_name}\nEventType: {clean_event_type}\nPattern: {pattern}"
            metadata = live_rule.get("metadata") or {
                "source": "FORTISIEM_LIVE_RULE_API",
                "synced_at": utc_now().isoformat(),
            }
        else:
            rule_id = clean_event_type
            rule_name = rule_name_candidate
            raw_sev = str(raw_data.get("eventSeverityCat") or raw_data.get("eventSeverity") or raw_data.get("severity") or "MEDIUM").upper()
            if "CRIT" in raw_sev:
                severity = "CRITICAL"
            elif "HIGH" in raw_sev:
                severity = "HIGH"
            elif "LOW" in raw_sev or "INFO" in raw_sev:
                severity = "LOW"
            else:
                severity = "MEDIUM"

            category = str(raw_data.get("phIncidentCategory") or raw_data.get("category") or "Security")
            sub_cat = str(raw_data.get("phSubIncidentCategory") or raw_data.get("incidentTagName") or "Policy Violation")
            data_src = str(raw_data.get("incidentRptDevName") or raw_data.get("dataSource") or "FortiSIEM")
            pattern = str(raw_data.get("incidentDetail") or "")
            if not pattern and raw_data.get("incidentDetailJson"):
                try:
                    pattern = json.dumps(raw_data.get("incidentDetailJson"))
                except Exception:
                    pattern = str(raw_data.get("incidentDetailJson"))

            desc = f"Detection rule '{rule_name}' ({category} / {sub_cat}) registered automatically from SIEM incident telemetry."
            raw_text = f"Rule: {rule_name}\nEventType: {clean_event_type}\nCategory: {category}\nSubCategory: {sub_cat}\nPattern: {pattern}"
            metadata = {
                "source": "AUTO_SYNCED_FROM_INCIDENT",
                "category": category,
                "subCategory": sub_cat,
                "attackTechnique": raw_data.get("attackTechnique"),
                "attackTactic": raw_data.get("attackTactic"),
                "customer": raw_data.get("customer"),
                "auto_registered_at": utc_now().isoformat(),
            }

        new_rule = Rule(
            rule_id=rule_id,
            name=rule_name,
            event_type=clean_event_type,
            description=desc,
            severity=severity,
            status="ACTIVE",
            data_source=data_src,
            detection_tech=sub_cat or "SIEM Rule Engine",
            evaluation_mode="ONLINE",
            pattern_logic=pattern,
            raw_rule_text=raw_text,
            parsed_metadata=metadata,
        )
        self.db.add(new_rule)
        await self.db.flush()

        # Generate template draft prompt for Rule Prompt Studio
        try:
            from app.services.prompt_studio_service import PromptStudioService
            prompt_svc = PromptStudioService(self.db)
            draft = await prompt_svc.generate_template_draft(rule_id=new_rule.id)
            # REQ-03 / AV-001: Template drafts remain strictly in DRAFT status.
            # Do NOT automatically set active_version_id = draft.id.
            # Production triage requires explicit Administrator approval in Agent Intelligence Studio.
        except Exception:
            pass

        return new_rule

