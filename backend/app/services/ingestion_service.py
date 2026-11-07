import json
import io
import re
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.models.incident import Incident, IncidentEvent, HistoricalGroundTruth
from app.models.rule import Rule
from app.models.import_job import ImportJob
from app.models.audit import AuditLog
from app.services.rule_parser import RuleParser
from app.utils.zip_guard import ZipGuard, ZipSecurityException


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
            job.completed_at = datetime.utcnow()
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
        job.completed_at = datetime.utcnow()

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

        job.completed_at = datetime.utcnow()
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

        status_code = raw_data.get("status")
        try:
            status_code = int(status_code) if status_code is not None else 1
        except Exception:
            status_code = 1

        status_name = "Closed" if status_code == 2 else "Open"

        # Timestamps
        def parse_epoch(val: Any) -> Optional[int]:
            if val is None:
                return None
            try:
                return int(val)
            except Exception:
                return None

        first_seen = parse_epoch(raw_data.get("firstSeen"))
        last_seen = parse_epoch(raw_data.get("lastSeen"))
        created_at_epoch = parse_epoch(raw_data.get("createdAt"))
        updated_at_epoch = parse_epoch(raw_data.get("updatedAt"))

        incident = Incident(
            incident_id=incident_id,
            rule_id=rule.id if rule else None,
            import_job_id=import_job_id,
            event_type=event_type,
            title=str(raw_data.get("title") or raw_data.get("eventName") or f"Incident {incident_id}"),
            description=str(raw_data.get("description") or ""),
            detail=str(raw_data.get("detail") or ""),
            severity=severity,
            event_severity=str(raw_data.get("eventSeverity") or ""),
            status_code=status_code,
            status_name=status_name,
            category=str(raw_data.get("category") or ""),
            subcategory=str(raw_data.get("subcategory") or ""),
            source_ip=str(raw_data.get("sourceIp") or ""),
            reporting_device=str(raw_data.get("reportingDevice") or ""),
            reporting_ip=str(raw_data.get("reportingIp") or ""),
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
        raw_events = raw_data.get("rawEvents", [])
        if isinstance(raw_events, list):
            for idx, revt in enumerate(raw_events):
                if not isinstance(revt, dict):
                    continue
                attrs = revt.get("attribute", {})
                if not isinstance(attrs, dict):
                    attrs = {}

                raw_log = ""
                if "Raw Event Log" in attrs:
                    raw_log = str(attrs.get("Raw Event Log", ""))

                evt_id = str(revt.get("eventId") or f"{incident_id}_evt_{idx}")
                evt_receive_time = parse_epoch(attrs.get("Event Receive Time") or revt.get("eventReceiveTime"))

                evt_obj = IncidentEvent(
                    incident_id=incident.id,
                    event_id=evt_id,
                    event_receive_time=evt_receive_time,
                    event_type=str(attrs.get("Event Type") or event_type),
                    raw_log=raw_log,
                    attributes=attrs,  # Retains vendor-specific nested attributes
                )
                self.db.add(evt_obj)

        # ISOLATED GROUND TRUTH
        resolution = str(raw_data.get("resolution") or "").strip()
        cleared_reason = str(raw_data.get("clearedReason") or "").strip()
        comments = str(raw_data.get("comments") or "").strip()
        cleared_user = str(raw_data.get("clearedUser") or raw_data.get("cmsClearUser") or "").strip()
        cleared_time = parse_epoch(raw_data.get("clearedTime"))
        resolved_at = parse_epoch(raw_data.get("resolvedAt"))

        is_ml_generated = (
            "Machine Learning" in comments or
            "Machine Learning" in resolution or
            "ML" in comments
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

        rule_name = str(raw_data.get("eventName") or raw_data.get("title") or clean_event_type).strip()
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

        metadata = {
            "source": "AUTO_SYNCED_FROM_INCIDENT",
            "category": category,
            "subCategory": sub_cat,
            "attackTechnique": raw_data.get("attackTechnique"),
            "attackTactic": raw_data.get("attackTactic"),
            "customer": raw_data.get("customer"),
            "auto_registered_at": datetime.utcnow().isoformat(),
        }

        new_rule = Rule(
            rule_id=clean_event_type,
            name=rule_name,
            event_type=clean_event_type,
            description=f"Detection rule '{rule_name}' ({category} / {sub_cat}) registered automatically from SIEM incident telemetry.",
            severity=severity,
            status="ACTIVE",
            data_source=data_src,
            detection_tech=sub_cat or "SIEM Rule Engine",
            evaluation_mode="ONLINE",
            pattern_logic=pattern,
            raw_rule_text=f"Rule: {rule_name}\nEventType: {clean_event_type}\nCategory: {category}\nSubCategory: {sub_cat}\nPattern: {pattern}",
            parsed_metadata=metadata,
        )
        self.db.add(new_rule)
        await self.db.flush()

        # Generate template draft prompt for Rule Prompt Studio
        try:
            from app.services.prompt_studio_service import PromptStudioService
            prompt_svc = PromptStudioService(self.db)
            draft = await prompt_svc.generate_template_draft(rule_id=new_rule.id)
            # Ensure rule prompt points to active version
            from app.models.prompt import RulePrompt
            rp_res = await self.db.execute(select(RulePrompt).where(RulePrompt.rule_id == new_rule.id))
            rp = rp_res.scalars().first()
            if rp and not rp.active_version_id and draft:
                rp.active_version_id = draft.id
                await self.db.flush()
        except Exception:
            pass

        return new_rule

