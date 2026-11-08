import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.models.incident import Incident, IncidentEvent
from app.schemas.canonical_evidence import CanonicalEvidenceRecord, EvidenceNormalizationResult
from app.services.model_payload_allowlist import FORBIDDEN_GROUND_TRUTH_KEYS

logger = logging.getLogger(__name__)

# Canonical mapping of raw attribute keys to standardized canonical fields and categories
FIELD_MAPPINGS: Dict[str, Dict[str, str]] = {
    # Process Execution
    "cmdline": {"field": "process.command_line", "type": "PROCESS_EXECUTION"},
    "command": {"field": "process.command_line", "type": "PROCESS_EXECUTION"},
    "processcommandline": {"field": "process.command_line", "type": "PROCESS_EXECUTION"},
    "command_line": {"field": "process.command_line", "type": "PROCESS_EXECUTION"},
    "process": {"field": "process.name", "type": "PROCESS_EXECUTION"},
    "process_name": {"field": "process.name", "type": "PROCESS_EXECUTION"},
    "app": {"field": "process.name", "type": "PROCESS_EXECUTION"},
    "imagepath": {"field": "process.file_path", "type": "PROCESS_EXECUTION"},
    "filepath": {"field": "process.file_path", "type": "PROCESS_EXECUTION"},
    "filename": {"field": "process.file_name", "type": "PROCESS_EXECUTION"},
    "pid": {"field": "process.pid", "type": "PROCESS_EXECUTION"},
    "processid": {"field": "process.pid", "type": "PROCESS_EXECUTION"},

    # Process Lineage
    "parentcmd": {"field": "process.parent_command_line", "type": "PROCESS_LINEAGE"},
    "parentcmdline": {"field": "process.parent_command_line", "type": "PROCESS_LINEAGE"},
    "parent_command_line": {"field": "process.parent_command_line", "type": "PROCESS_LINEAGE"},
    "parentprocess": {"field": "process.parent_name", "type": "PROCESS_LINEAGE"},
    "parent_process": {"field": "process.parent_name", "type": "PROCESS_LINEAGE"},
    "parent": {"field": "process.parent_name", "type": "PROCESS_LINEAGE"},
    "ppid": {"field": "process.parent_pid", "type": "PROCESS_LINEAGE"},
    "parentprocessid": {"field": "process.parent_pid", "type": "PROCESS_LINEAGE"},

    # User Context
    "username": {"field": "user.name", "type": "USER_CONTEXT"},
    "user": {"field": "user.name", "type": "USER_CONTEXT"},
    "srcuser": {"field": "user.name", "type": "USER_CONTEXT"},
    "source_user": {"field": "user.name", "type": "USER_CONTEXT"},
    "targetuser": {"field": "user.target_name", "type": "USER_CONTEXT"},
    "account": {"field": "user.name", "type": "USER_CONTEXT"},

    # Network Connection
    "srcip": {"field": "network.source_ip", "type": "NETWORK_CONNECTION"},
    "src_ip": {"field": "network.source_ip", "type": "NETWORK_CONNECTION"},
    "source_ip": {"field": "network.source_ip", "type": "NETWORK_CONNECTION"},
    "sourceip": {"field": "network.source_ip", "type": "NETWORK_CONNECTION"},
    "destip": {"field": "network.destination_ip", "type": "NETWORK_CONNECTION"},
    "dest_ip": {"field": "network.destination_ip", "type": "NETWORK_CONNECTION"},
    "destination_ip": {"field": "network.destination_ip", "type": "NETWORK_CONNECTION"},
    "destinationip": {"field": "network.destination_ip", "type": "NETWORK_CONNECTION"},
    "srcport": {"field": "network.source_port", "type": "NETWORK_CONNECTION"},
    "src_port": {"field": "network.source_port", "type": "NETWORK_CONNECTION"},
    "destport": {"field": "network.destination_port", "type": "NETWORK_CONNECTION"},
    "dest_port": {"field": "network.destination_port", "type": "NETWORK_CONNECTION"},
    "proto": {"field": "network.protocol", "type": "NETWORK_CONNECTION"},
    "protocol": {"field": "network.protocol", "type": "NETWORK_CONNECTION"},

    # DNS / Web
    "destdomain": {"field": "dns.domain", "type": "DNS_QUERY"},
    "domain": {"field": "dns.domain", "type": "DNS_QUERY"},
    "dest_domain": {"field": "dns.domain", "type": "DNS_QUERY"},
    "dns_query": {"field": "dns.domain", "type": "DNS_QUERY"},
    "url": {"field": "web.url", "type": "DNS_QUERY"},
    "uri": {"field": "web.url", "type": "DNS_QUERY"},

    # File Hashes
    "sha256": {"field": "file.hash_sha256", "type": "FILE_HASH"},
    "hash_sha256": {"field": "file.hash_sha256", "type": "FILE_HASH"},
    "filesha256": {"field": "file.hash_sha256", "type": "FILE_HASH"},
    "md5": {"field": "file.hash_md5", "type": "FILE_HASH"},
    "hash_md5": {"field": "file.hash_md5", "type": "FILE_HASH"},
    "filemd5": {"field": "file.hash_md5", "type": "FILE_HASH"},
    "hash": {"field": "file.hash_sha256", "type": "FILE_HASH"},

    # Endpoint Telemetry
    "devname": {"field": "endpoint.hostname", "type": "ENDPOINT_TELEMETRY"},
    "hostname": {"field": "endpoint.hostname", "type": "ENDPOINT_TELEMETRY"},
    "dev_name": {"field": "endpoint.hostname", "type": "ENDPOINT_TELEMETRY"},
    "devip": {"field": "endpoint.ip", "type": "ENDPOINT_TELEMETRY"},
    "devid": {"field": "endpoint.device_id", "type": "ENDPOINT_TELEMETRY"},

    # Security & Event Actions
    "action": {"field": "security.action", "type": "SECURITY_EVENT"},
    "status": {"field": "security.status", "type": "SECURITY_EVENT"},
    "eventmsg": {"field": "security.message", "type": "SECURITY_EVENT"},
    "rawmsg": {"field": "security.raw_message", "type": "SECURITY_EVENT"},
}


class EvidenceNormalizationService:
    """
    P2-REQ-01: Canonical Evidence Normalization Service.
    Transforms raw SIEM incident telemetry and linked event attributes into
    traceable, canonical evidence records with cryptographic integrity digests.
    Strictly purges ground truth and never hallucinates missing facts.
    """

    @classmethod
    def normalize_incident_evidence(
        cls,
        incident: Incident,
        events: Optional[List[IncidentEvent]] = None,
        source_system: str = "FortiSIEM",
    ) -> EvidenceNormalizationResult:
        """
        Normalizes all available telemetry for an incident into canonical evidence records.
        Processes top-level normalized fields, linked events, and raw payload attributes.
        """
        incident_id = str(incident.incident_id or incident.id)
        records: List[CanonicalEvidenceRecord] = []
        seen_digests = set()

        def add_record(
            source_field: str,
            observed_value: Any,
            evidence_type: str,
            source_event_id: Optional[str] = None,
            observed_at: Optional[str] = None,
        ) -> None:
            if observed_value is None or observed_value == "":
                return

            # Clean and canonicalize value
            val_str = str(observed_value).strip()
            if not val_str:
                return

            digest = CanonicalEvidenceRecord.generate_digest(source_field, val_str)
            if digest in seen_digests:
                return
            seen_digests.add(digest)

            rec_id = CanonicalEvidenceRecord.generate_id(incident_id, source_event_id, source_field)
            record = CanonicalEvidenceRecord(
                evidence_id=rec_id,
                incident_id=incident_id,
                source_system=source_system,
                source_event_id=source_event_id,
                source_field=source_field,
                observed_value=val_str,
                observed_at=observed_at,
                evidence_type=evidence_type,
                availability="AVAILABLE",
                provenance_status="SOURCE_RECORDED",
                integrity_digest=digest,
            )
            records.append(record)

        # 1. Top-Level Incident Fields
        obs_time = None
        if incident.created_at_epoch:
            try:
                obs_time = datetime.fromtimestamp(incident.created_at_epoch / 1000.0, timezone.utc).isoformat()
            except Exception:
                pass

        if incident.source_ip and incident.source_ip.strip():
            add_record("network.source_ip", incident.source_ip.strip(), "NETWORK_CONNECTION", "TOP", obs_time)

        if incident.reporting_device and incident.reporting_device.strip():
            add_record("endpoint.hostname", incident.reporting_device.strip(), "ENDPOINT_TELEMETRY", "TOP", obs_time)

        if incident.reporting_ip and incident.reporting_ip.strip():
            add_record("endpoint.ip", incident.reporting_ip.strip(), "ENDPOINT_TELEMETRY", "TOP", obs_time)

        if incident.event_type and incident.event_type.strip():
            add_record("security.event_type", incident.event_type.strip(), "SECURITY_EVENT", "TOP", obs_time)

        if incident.title and incident.title.strip() and incident.title != "No description provided by SIEM.":
            add_record("security.alert_title", incident.title.strip(), "SECURITY_EVENT", "TOP", obs_time)

        # 2. Linked Events Extraction
        evts = events if events is not None else (incident.events or [])
        for evt in evts:
            evt_id = str(getattr(evt, "event_id", "") or getattr(evt, "id", "") or "EVT")
            evt_type = getattr(evt, "event_type", None)
            evt_time_str = None
            evt_rx_time = getattr(evt, "event_receive_time", None)
            if evt_rx_time:
                try:
                    evt_time_str = datetime.fromtimestamp(evt_rx_time / 1000.0, timezone.utc).isoformat()
                except Exception:
                    pass

            if evt_type and evt_type.strip():
                add_record("security.event_type", evt_type.strip(), "SECURITY_EVENT", evt_id, evt_time_str)

            raw_log = getattr(evt, "raw_log", "")
            if raw_log and raw_log.strip():
                add_record("security.raw_log", raw_log.strip()[:1000], "SECURITY_EVENT", evt_id, evt_time_str)

            attrs = getattr(evt, "attributes", {}) or {}
            if isinstance(attrs, dict):
                cls._extract_from_dict(attrs, evt_id, evt_time_str, add_record)

        # 3. Raw Payload Extraction (if raw_payload has nested events not in incident.events)
        if incident.raw_payload and isinstance(incident.raw_payload, dict):
            raw = incident.raw_payload
            raw_event = raw.get("event") or raw.get("events") or raw.get("attributes")
            if isinstance(raw_event, dict):
                cls._extract_from_dict(raw_event, "PAYLOAD", obs_time, add_record)
            elif isinstance(raw_event, list):
                for idx, item in enumerate(raw_event):
                    if isinstance(item, dict):
                        cls._extract_from_dict(item, f"PAYLOAD_{idx}", obs_time, add_record)
            else:
                cls._extract_from_dict(raw, "PAYLOAD", obs_time, add_record)

        # Aggregate and categorize
        by_type: Dict[str, List[CanonicalEvidenceRecord]] = {}
        by_field: Dict[str, List[CanonicalEvidenceRecord]] = {}
        for r in records:
            by_type.setdefault(r.evidence_type, []).append(r)
            by_field.setdefault(r.source_field, []).append(r)

        return EvidenceNormalizationResult(
            incident_id=incident_id,
            total_evidence_count=len(records),
            available_evidence_count=len(records),
            records=records,
            evidence_by_type=by_type,
            evidence_by_field=by_field,
        )

    @classmethod
    def _extract_from_dict(
        cls,
        data: Dict[str, Any],
        source_event_id: str,
        observed_at: Optional[str],
        add_fn: Any,
    ) -> None:
        """Recursively parses a dictionary, mapping known SOC attributes to canonical fields."""
        for key, val in data.items():
            if val is None or val == "":
                continue

            norm_k = str(key).strip().lower()
            if norm_k in FORBIDDEN_GROUND_TRUTH_KEYS or any(fgk in norm_k for fgk in ("ground_truth", "analyst_verdict", "cleared")):
                continue

            if isinstance(val, dict):
                cls._extract_from_dict(val, source_event_id, observed_at, add_fn)
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        cls._extract_from_dict(item, source_event_id, observed_at, add_fn)
            else:
                # Check mapping
                mapping = FIELD_MAPPINGS.get(norm_k)
                if mapping:
                    add_fn(
                        source_field=mapping["field"],
                        observed_value=val,
                        evidence_type=mapping["type"],
                        source_event_id=source_event_id,
                        observed_at=observed_at,
                    )
                else:
                    # Generic heuristic for unrecognized fields if high-signal
                    if any(term in norm_k for term in ("ip", "host", "domain", "user", "file", "path", "hash", "proc")):
                        add_fn(
                            source_field=f"telemetry.{norm_k}",
                            observed_value=val,
                            evidence_type="ENDPOINT_TELEMETRY",
                            source_event_id=source_event_id,
                            observed_at=observed_at,
                        )
