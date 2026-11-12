import logging
import re
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime, timezone

from app.models.incident import Incident, IncidentEvent
from app.schemas.canonical_evidence import CanonicalEvidenceRecord, EvidenceNormalizationResult
from app.services.model_payload_allowlist import FORBIDDEN_GROUND_TRUTH_KEYS

logger = logging.getLogger(__name__)

# Regular expression for parsing key-value pairs from raw syslog/CEF logs
KV_PATTERN = re.compile(r'([a-zA-Z0-9_\.\-]+)=(?:"([^"]*)"|\'([^\']*)\'|(\S+))')

# Regex for extracting source/destination IPs and hosts from FortiSIEM incidentSrc/incidentTarget strings
SRC_IP_RE = re.compile(r'(?:srcIpAddr|srcIp|src|sourceIp)\s*[:=]\s*([0-9a-fA-F\.:]+)', re.IGNORECASE)
DST_IP_RE = re.compile(r'(?:destIpAddr|dstIpAddr|destIp|dstIp|dst|destinationIp)\s*[:=]\s*([0-9a-fA-F\.:]+)', re.IGNORECASE)
DST_HOST_RE = re.compile(r'(?:destName|destinationName|destDomain|domain|hostName)\s*[:=]\s*([^\s,;]+)', re.IGNORECASE)


def parse_key_value_string(raw_text: str) -> Dict[str, str]:
    """Extracts key-value pairs from standard syslog, CEF, or key=value telemetry strings."""
    result: Dict[str, str] = {}
    if not raw_text or not isinstance(raw_text, str):
        return result
    for match in KV_PATTERN.finditer(raw_text):
        k = match.group(1)
        v = match.group(2) if match.group(2) is not None else (
            match.group(3) if match.group(3) is not None else match.group(4)
        )
        if k and v is not None:
            result[k.strip()] = v.strip()
    return result


def clean_attr_key(key: str) -> str:
    """Collapses spaces, underscores, dots, hyphens to produce normalized matching token."""
    return re.sub(r'[\s_\.\-]+', '', str(key).strip().lower())


# Canonical mapping of raw attribute keys to standardized canonical fields and categories
FIELD_MAPPINGS: Dict[str, Dict[str, str]] = {
    # Process Execution
    "cmdline": {"field": "process.command_line", "type": "PROCESS_EXECUTION"},
    "command": {"field": "process.command_line", "type": "PROCESS_EXECUTION"},
    "processcommandline": {"field": "process.command_line", "type": "PROCESS_EXECUTION"},
    "command_line": {"field": "process.command_line", "type": "PROCESS_EXECUTION"},
    "commandline": {"field": "process.command_line", "type": "PROCESS_EXECUTION"},
    "process": {"field": "process.name", "type": "PROCESS_EXECUTION"},
    "process_name": {"field": "process.name", "type": "PROCESS_EXECUTION"},
    "processname": {"field": "process.name", "type": "PROCESS_EXECUTION"},
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
    "parentcommandline": {"field": "process.parent_command_line", "type": "PROCESS_LINEAGE"},
    "parentprocess": {"field": "process.parent_name", "type": "PROCESS_LINEAGE"},
    "parent_process": {"field": "process.parent_name", "type": "PROCESS_LINEAGE"},
    "parentprocessname": {"field": "process.parent_name", "type": "PROCESS_LINEAGE"},
    "parent": {"field": "process.parent_name", "type": "PROCESS_LINEAGE"},
    "ppid": {"field": "process.parent_pid", "type": "PROCESS_LINEAGE"},
    "parentprocessid": {"field": "process.parent_pid", "type": "PROCESS_LINEAGE"},

    # User Context
    "username": {"field": "user.name", "type": "USER_CONTEXT"},
    "user": {"field": "user.name", "type": "USER_CONTEXT"},
    "srcuser": {"field": "user.name", "type": "USER_CONTEXT"},
    "sourceuser": {"field": "user.name", "type": "USER_CONTEXT"},
    "source_user": {"field": "user.name", "type": "USER_CONTEXT"},
    "targetuser": {"field": "user.target_name", "type": "USER_CONTEXT"},
    "account": {"field": "user.name", "type": "USER_CONTEXT"},
    "userdomain": {"field": "user.domain", "type": "USER_CONTEXT"},

    # Network Connection - Source IP
    "srcip": {"field": "network.source_ip", "type": "NETWORK_CONNECTION"},
    "srcipaddr": {"field": "network.source_ip", "type": "NETWORK_CONNECTION"},
    "src_ip": {"field": "network.source_ip", "type": "NETWORK_CONNECTION"},
    "src": {"field": "network.source_ip", "type": "NETWORK_CONNECTION"},
    "source_ip": {"field": "network.source_ip", "type": "NETWORK_CONNECTION"},
    "sourceip": {"field": "network.source_ip", "type": "NETWORK_CONNECTION"},
    "source ip": {"field": "network.source_ip", "type": "NETWORK_CONNECTION"},
    "source.ip": {"field": "network.source_ip", "type": "NETWORK_CONNECTION"},
    "sourceipaddress": {"field": "network.source_ip", "type": "NETWORK_CONNECTION"},
    "src_ip_addr": {"field": "network.source_ip", "type": "NETWORK_CONNECTION"},
    "network.source_ip": {"field": "network.source_ip", "type": "NETWORK_CONNECTION"},

    # Network Connection - Destination IP
    "destip": {"field": "network.destination_ip", "type": "NETWORK_CONNECTION"},
    "destipaddr": {"field": "network.destination_ip", "type": "NETWORK_CONNECTION"},
    "dest_ip": {"field": "network.destination_ip", "type": "NETWORK_CONNECTION"},
    "destination_ip": {"field": "network.destination_ip", "type": "NETWORK_CONNECTION"},
    "destinationip": {"field": "network.destination_ip", "type": "NETWORK_CONNECTION"},
    "destination ip": {"field": "network.destination_ip", "type": "NETWORK_CONNECTION"},
    "destination.ip": {"field": "network.destination_ip", "type": "NETWORK_CONNECTION"},
    "dstip": {"field": "network.destination_ip", "type": "NETWORK_CONNECTION"},
    "dstipaddr": {"field": "network.destination_ip", "type": "NETWORK_CONNECTION"},
    "dst_ip": {"field": "network.destination_ip", "type": "NETWORK_CONNECTION"},
    "dst": {"field": "network.destination_ip", "type": "NETWORK_CONNECTION"},
    "dest": {"field": "network.destination_ip", "type": "NETWORK_CONNECTION"},
    "destinationipaddress": {"field": "network.destination_ip", "type": "NETWORK_CONNECTION"},
    "dst_ip_addr": {"field": "network.destination_ip", "type": "NETWORK_CONNECTION"},
    "network.destination_ip": {"field": "network.destination_ip", "type": "NETWORK_CONNECTION"},

    # Network Connection - Ports
    "srcport": {"field": "network.source_port", "type": "NETWORK_CONNECTION"},
    "src_port": {"field": "network.source_port", "type": "NETWORK_CONNECTION"},
    "source_port": {"field": "network.source_port", "type": "NETWORK_CONNECTION"},
    "sourceport": {"field": "network.source_port", "type": "NETWORK_CONNECTION"},
    "source port": {"field": "network.source_port", "type": "NETWORK_CONNECTION"},
    "source.port": {"field": "network.source_port", "type": "NETWORK_CONNECTION"},
    "destport": {"field": "network.destination_port", "type": "NETWORK_CONNECTION"},
    "dest_port": {"field": "network.destination_port", "type": "NETWORK_CONNECTION"},
    "destinationport": {"field": "network.destination_port", "type": "NETWORK_CONNECTION"},
    "destination_port": {"field": "network.destination_port", "type": "NETWORK_CONNECTION"},
    "destination port": {"field": "network.destination_port", "type": "NETWORK_CONNECTION"},
    "destination.port": {"field": "network.destination_port", "type": "NETWORK_CONNECTION"},
    "dstport": {"field": "network.destination_port", "type": "NETWORK_CONNECTION"},
    "dst_port": {"field": "network.destination_port", "type": "NETWORK_CONNECTION"},

    # Protocol & Direction
    "proto": {"field": "network.protocol", "type": "NETWORK_CONNECTION"},
    "protocol": {"field": "network.protocol", "type": "NETWORK_CONNECTION"},
    "ipprotocol": {"field": "network.protocol", "type": "NETWORK_CONNECTION"},
    "ip_protocol": {"field": "network.protocol", "type": "NETWORK_CONNECTION"},
    "ip protocol": {"field": "network.protocol", "type": "NETWORK_CONNECTION"},
    "service": {"field": "network.service", "type": "NETWORK_CONNECTION"},
    "sentbytes64": {"field": "network.bytes_out", "type": "NETWORK_CONNECTION"},
    "sentbytes": {"field": "network.bytes_out", "type": "NETWORK_CONNECTION"},
    "sentbyte": {"field": "network.bytes_out", "type": "NETWORK_CONNECTION"},
    "sent_byte": {"field": "network.bytes_out", "type": "NETWORK_CONNECTION"},
    "bytes_out": {"field": "network.bytes_out", "type": "NETWORK_CONNECTION"},
    "bytes_sent": {"field": "network.bytes_out", "type": "NETWORK_CONNECTION"},
    "byteswritten": {"field": "network.bytes_out", "type": "NETWORK_CONNECTION"},
    "recvbytes64": {"field": "network.bytes_in", "type": "NETWORK_CONNECTION"},
    "recvbytes": {"field": "network.bytes_in", "type": "NETWORK_CONNECTION"},
    "rcvdbyte": {"field": "network.bytes_in", "type": "NETWORK_CONNECTION"},
    "rcvdbytes": {"field": "network.bytes_in", "type": "NETWORK_CONNECTION"},
    "bytes_in": {"field": "network.bytes_in", "type": "NETWORK_CONNECTION"},
    "bytes_recv": {"field": "network.bytes_in", "type": "NETWORK_CONNECTION"},
    "bytesread": {"field": "network.bytes_in", "type": "NETWORK_CONNECTION"},
    "direction": {"field": "network.direction", "type": "NETWORK_CONNECTION"},
    "trafficdirection": {"field": "network.direction", "type": "NETWORK_CONNECTION"},
    "traffic_direction": {"field": "network.direction", "type": "NETWORK_CONNECTION"},

    # DNS / Domain / Hostname
    "destdomain": {"field": "network.destination_domain", "type": "DNS_QUERY"},
    "domain": {"field": "network.destination_domain", "type": "DNS_QUERY"},
    "dest_domain": {"field": "network.destination_domain", "type": "DNS_QUERY"},
    "dns_query": {"field": "dns.domain", "type": "DNS_QUERY"},
    "dnsquery": {"field": "dns.domain", "type": "DNS_QUERY"},
    "destinationhost": {"field": "network.destination_domain", "type": "DNS_QUERY"},
    "destinationhostname": {"field": "network.destination_domain", "type": "DNS_QUERY"},
    "destination_host_name": {"field": "network.destination_domain", "type": "DNS_QUERY"},
    "destination host name": {"field": "network.destination_domain", "type": "DNS_QUERY"},
    "destname": {"field": "network.destination_domain", "type": "DNS_QUERY"},

    # HTTP / Web
    "url": {"field": "http.url", "type": "NETWORK_CONNECTION"},
    "uri": {"field": "http.url", "type": "NETWORK_CONNECTION"},
    "requesturl": {"field": "http.url", "type": "NETWORK_CONNECTION"},
    "request_url": {"field": "http.url", "type": "NETWORK_CONNECTION"},
    "requesturi": {"field": "http.url", "type": "NETWORK_CONNECTION"},
    "request_uri": {"field": "http.url", "type": "NETWORK_CONNECTION"},
    "http_url": {"field": "http.url", "type": "NETWORK_CONNECTION"},
    "http.url": {"field": "http.url", "type": "NETWORK_CONNECTION"},
    "web.url": {"field": "http.url", "type": "NETWORK_CONNECTION"},
    "method": {"field": "http.method", "type": "NETWORK_CONNECTION"},
    "httpmethod": {"field": "http.method", "type": "NETWORK_CONNECTION"},
    "http_method": {"field": "http.method", "type": "NETWORK_CONNECTION"},
    "http.method": {"field": "http.method", "type": "NETWORK_CONNECTION"},
    "requestmethod": {"field": "http.method", "type": "NETWORK_CONNECTION"},
    "request_method": {"field": "http.method", "type": "NETWORK_CONNECTION"},
    "reqtype": {"field": "http.method", "type": "NETWORK_CONNECTION"},
    "statuscode": {"field": "http.status_code", "type": "NETWORK_CONNECTION"},
    "status_code": {"field": "http.status_code", "type": "NETWORK_CONNECTION"},
    "httpstatus": {"field": "http.status_code", "type": "NETWORK_CONNECTION"},
    "http_status": {"field": "http.status_code", "type": "NETWORK_CONNECTION"},
    "httpstatuscode": {"field": "http.status_code", "type": "NETWORK_CONNECTION"},
    "http_status_code": {"field": "http.status_code", "type": "NETWORK_CONNECTION"},
    "http.status_code": {"field": "http.status_code", "type": "NETWORK_CONNECTION"},
    "useragent": {"field": "http.user_agent", "type": "NETWORK_CONNECTION"},
    "user_agent": {"field": "http.user_agent", "type": "NETWORK_CONNECTION"},
    "http_user_agent": {"field": "http.user_agent", "type": "NETWORK_CONNECTION"},

    # Web Category
    "webcategory": {"field": "webCategory", "type": "SECURITY_EVENT"},
    "web_category": {"field": "webCategory", "type": "SECURITY_EVENT"},
    "websitecategory": {"field": "webCategory", "type": "SECURITY_EVENT"},
    "web site category": {"field": "webCategory", "type": "SECURITY_EVENT"},
    "website_category": {"field": "webCategory", "type": "SECURITY_EVENT"},
    "urlcategory": {"field": "webCategory", "type": "SECURITY_EVENT"},
    "url_category": {"field": "webCategory", "type": "SECURITY_EVENT"},
    "catdesc": {"field": "webCategory", "type": "SECURITY_EVENT"},
    "categorydesc": {"field": "webCategory", "type": "SECURITY_EVENT"},
    "webCategory": {"field": "webCategory", "type": "SECURITY_EVENT"},

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
    "host name": {"field": "endpoint.hostname", "type": "ENDPOINT_TELEMETRY"},
    "dev_name": {"field": "endpoint.hostname", "type": "ENDPOINT_TELEMETRY"},
    "devip": {"field": "endpoint.ip", "type": "ENDPOINT_TELEMETRY"},
    "devid": {"field": "endpoint.device_id", "type": "ENDPOINT_TELEMETRY"},
    "reportingip": {"field": "endpoint.ip", "type": "ENDPOINT_TELEMETRY"},
    "reporting ip": {"field": "endpoint.ip", "type": "ENDPOINT_TELEMETRY"},
    "reporting_ip": {"field": "endpoint.ip", "type": "ENDPOINT_TELEMETRY"},
    "reportingdevice": {"field": "endpoint.hostname", "type": "ENDPOINT_TELEMETRY"},
    "reporting device": {"field": "endpoint.hostname", "type": "ENDPOINT_TELEMETRY"},
    "serialnumber": {"field": "endpoint.device_id", "type": "ENDPOINT_TELEMETRY"},
    "serial number": {"field": "endpoint.device_id", "type": "ENDPOINT_TELEMETRY"},
    "process blocked": {"field": "endpoint.process_blocked", "type": "ENDPOINT_TELEMETRY"},
    "process_blocked": {"field": "endpoint.process_blocked", "type": "ENDPOINT_TELEMETRY"},
    "processblocked": {"field": "endpoint.process_blocked", "type": "ENDPOINT_TELEMETRY"},
    "file quarantined": {"field": "endpoint.file_quarantined", "type": "ENDPOINT_TELEMETRY"},
    "file_quarantined": {"field": "endpoint.file_quarantined", "type": "ENDPOINT_TELEMETRY"},
    "filequarantined": {"field": "endpoint.file_quarantined", "type": "ENDPOINT_TELEMETRY"},

    # Security & Event Actions
    "action": {"field": "security.action", "type": "SECURITY_EVENT"},
    "firewallaction": {"field": "security.action", "type": "SECURITY_EVENT"},
    "firewall action": {"field": "security.action", "type": "SECURITY_EVENT"},
    "fwaction": {"field": "security.action", "type": "SECURITY_EVENT"},
    "ruleaction": {"field": "security.action", "type": "SECURITY_EVENT"},
    "security.action": {"field": "security.action", "type": "SECURITY_EVENT"},
    "status": {"field": "security.status", "type": "SECURITY_EVENT"},
    "eventmsg": {"field": "security.message", "type": "SECURITY_EVENT"},
    "msg": {"field": "security.message", "type": "SECURITY_EVENT"},
    "message": {"field": "security.message", "type": "SECURITY_EVENT"},
    "userdefinedmsg": {"field": "security.message", "type": "SECURITY_EVENT"},
    "user defined msg": {"field": "security.message", "type": "SECURITY_EVENT"},
    "rawmsg": {"field": "security.raw_message", "type": "SECURITY_EVENT"},
    "attacktactic": {"field": "mitre.tactic", "type": "SECURITY_EVENT"},
    "attack tactic": {"field": "mitre.tactic", "type": "SECURITY_EVENT"},
    "attacktechnique": {"field": "mitre.technique", "type": "SECURITY_EVENT"},
    "attack technique": {"field": "mitre.technique", "type": "SECURITY_EVENT"},
    "timestamp": {"field": "event.timestamp", "type": "SECURITY_EVENT"},
    "eventtime": {"field": "event.timestamp", "type": "SECURITY_EVENT"},
    "event_time": {"field": "event.timestamp", "type": "SECURITY_EVENT"},
    "eventreceivetime": {"field": "event.timestamp", "type": "SECURITY_EVENT"},
    "event_receive_time": {"field": "event.timestamp", "type": "SECURITY_EVENT"},
    "event receive time": {"field": "event.timestamp", "type": "SECURITY_EVENT"},
}

# Pre-compute secondary lookup table indexed by clean_attr_key for resilient alias resolution
_CLEAN_FIELD_MAPPINGS: Dict[str, Dict[str, str]] = {}
for _k, _v in FIELD_MAPPINGS.items():
    _ck = clean_attr_key(_k)
    if _ck not in _CLEAN_FIELD_MAPPINGS:
        _CLEAN_FIELD_MAPPINGS[_ck] = _v


def resolve_field_mapping(key: str) -> Optional[Dict[str, str]]:
    """Resolves an attribute key to a canonical field mapping deterministically."""
    norm_k = str(key).strip().lower()
    if norm_k in FIELD_MAPPINGS:
        return FIELD_MAPPINGS[norm_k]
    clean_k = clean_attr_key(key)
    if clean_k in _CLEAN_FIELD_MAPPINGS:
        return _CLEAN_FIELD_MAPPINGS[clean_k]
    return None


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
        Processes top-level normalized fields, linked events, raw log key-values, and payload attributes.
        """
        incident_id = str(incident.incident_id or incident.id)
        records: List[CanonicalEvidenceRecord] = []
        seen_digests: Set[str] = set()
        seen_rec_ids: Set[str] = set()
        unmapped_fields: List[Dict[str, Any]] = []

        def add_record(
            source_field: str,
            observed_value: Any,
            evidence_type: str,
            source_event_id: Optional[str] = None,
            observed_at: Optional[str] = None,
            raw_field_name: Optional[str] = None,
            transformation: str = "DIRECT",
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
            if rec_id in seen_rec_ids:
                # Disambiguate distinct observed values colliding under the same source event & canonical field
                rec_id = f"{rec_id}-{digest[:6]}"
            seen_rec_ids.add(rec_id)
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
                raw_field_name=raw_field_name or source_field,
                transformation=transformation,
                validation_status="PRESENT_VALID",
            )
            records.append(record)

        # 1. Top-Level Incident Fields
        obs_time = None
        top_epoch = (
            getattr(incident, "first_seen_epoch", None)
            or getattr(incident, "created_at_epoch", None)
            or getattr(incident, "last_seen_epoch", None)
        )
        if top_epoch:
            try:
                ep_num = float(top_epoch)
                ep_sec = ep_num / 1000.0 if ep_num >= 1e11 else ep_num
                obs_time = datetime.fromtimestamp(ep_sec, timezone.utc).isoformat()
            except Exception:
                pass

        if obs_time:
            add_record("event.timestamp", obs_time, "SECURITY_EVENT", "TOP", obs_time, "first_seen_epoch", "TIMESTAMP_CONVERTED")

        # Top-level source IP
        top_source_ip = (getattr(incident, "source_ip", None) or "").strip()
        raw_p = incident.raw_payload or {}
        if not top_source_ip and isinstance(raw_p, dict):
            src_str = raw_p.get("incidentSrc") or raw_p.get("sourceIp") or raw_p.get("srcIpAddr") or ""
            if src_str:
                match_src = SRC_IP_RE.search(str(src_str))
                top_source_ip = match_src.group(1).strip() if match_src else str(src_str).strip()

        if top_source_ip:
            add_record("network.source_ip", top_source_ip, "NETWORK_CONNECTION", "TOP", obs_time, "source_ip", "ALIASED")

        # Top-level destination IP / target
        if isinstance(raw_p, dict):
            target_str = raw_p.get("incidentTarget") or raw_p.get("destIpAddr") or raw_p.get("destinationIp") or ""
            if target_str:
                match_dst = DST_IP_RE.search(str(target_str))
                if match_dst:
                    add_record("network.destination_ip", match_dst.group(1).strip(), "NETWORK_CONNECTION", "TOP", obs_time, "incidentTarget", "ALIASED")
                match_host = DST_HOST_RE.search(str(target_str))
                if match_host:
                    add_record("endpoint.hostname", match_host.group(1).strip(), "ENDPOINT_TELEMETRY", "TOP", obs_time, "incidentTarget", "ALIASED")

        if incident.reporting_device and incident.reporting_device.strip():
            add_record("endpoint.hostname", incident.reporting_device.strip(), "ENDPOINT_TELEMETRY", "TOP", obs_time, "reporting_device", "DIRECT")

        if incident.reporting_ip and incident.reporting_ip.strip():
            add_record("endpoint.ip", incident.reporting_ip.strip(), "ENDPOINT_TELEMETRY", "TOP", obs_time, "reporting_ip", "DIRECT")

        if incident.event_type and incident.event_type.strip():
            add_record("security.event_type", incident.event_type.strip(), "SECURITY_EVENT", "TOP", obs_time, "event_type", "DIRECT")

        if incident.title and incident.title.strip() and incident.title != "No description provided by SIEM.":
            add_record("security.alert_title", incident.title.strip(), "SECURITY_EVENT", "TOP", obs_time, "title", "DIRECT")

        # Extract top-level incident correlation metadata (e.g. incidentDetailJson)
        if isinstance(raw_p, dict):
            detail_json = raw_p.get("incidentDetailJson")
            if isinstance(detail_json, dict):
                cls._extract_from_dict(detail_json, "PAYLOAD_DETAIL", obs_time, add_record, unmapped_fields)
            elif isinstance(detail_json, str) and detail_json.strip().startswith("{"):
                try:
                    import json
                    parsed_det = json.loads(detail_json)
                    if isinstance(parsed_det, dict):
                        cls._extract_from_dict(parsed_det, "PAYLOAD_DETAIL", obs_time, add_record, unmapped_fields)
                except Exception:
                    pass

            detail_str = raw_p.get("incidentDetail")
            if isinstance(detail_str, str) and detail_str.strip().startswith("{"):
                try:
                    import json
                    parsed_det = json.loads(detail_str)
                    if isinstance(parsed_det, dict):
                        cls._extract_from_dict(parsed_det, "PAYLOAD_DETAIL", obs_time, add_record, unmapped_fields)
                except Exception:
                    pass

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

            if evt_time_str:
                add_record("event.timestamp", evt_time_str, "SECURITY_EVENT", evt_id, evt_time_str, "event_receive_time", "TIMESTAMP_CONVERTED")

            if evt_type and evt_type.strip():
                add_record("security.event_type", evt_type.strip(), "SECURITY_EVENT", evt_id, evt_time_str, "event_type", "DIRECT")

            raw_log = getattr(evt, "raw_log", "")
            if raw_log and raw_log.strip():
                clean_log = raw_log.strip()
                add_record("security.raw_log", clean_log[:1000], "SECURITY_EVENT", evt_id, evt_time_str, "raw_log", "DIRECT")
                
                # Automated Key-Value syslog parser (e.g. srcip=..., dstip=..., url=..., catdesc=...)
                kv_extracted = parse_key_value_string(clean_log)
                if kv_extracted:
                    cls._extract_from_dict(
                        kv_extracted,
                        evt_id,
                        evt_time_str,
                        add_record,
                        unmapped_fields,
                        is_kv_extracted=True,
                    )

            attrs = getattr(evt, "attributes", {}) or {}
            if isinstance(attrs, dict):
                cls._extract_from_dict(attrs, evt_id, evt_time_str, add_record, unmapped_fields)

        # 3. Raw Payload Extraction (fallback nested events if evts is empty)
        if incident.raw_payload and isinstance(incident.raw_payload, dict):
            raw = incident.raw_payload
            has_existing_events = bool(evts and len(evts) > 0)
            if not has_existing_events:
                for container_key in ("attributes", "event", "events", "rawEvents", "triggeringEvents"):
                    raw_sub = raw.get(container_key)
                    if isinstance(raw_sub, dict):
                        cls._extract_from_dict(raw_sub, f"PAYLOAD_{container_key.upper()}", obs_time, add_record, unmapped_fields)
                    elif isinstance(raw_sub, list):
                        for idx, item in enumerate(raw_sub):
                            if isinstance(item, dict):
                                # Check if rawMessage exists in rawEvents item
                                item_raw_msg = item.get("rawMessage") or item.get("rawEventLog") or item.get("rawLog")
                                if item_raw_msg and isinstance(item_raw_msg, str):
                                    kv_ext = parse_key_value_string(item_raw_msg)
                                    if kv_ext:
                                        cls._extract_from_dict(kv_ext, f"PAYLOAD_{container_key.upper()}_{idx}", obs_time, add_record, unmapped_fields, is_kv_extracted=True)
                                cls._extract_from_dict(item, f"PAYLOAD_{container_key.upper()}_{idx}", obs_time, add_record, unmapped_fields)

            # Always extract top-level scalar attributes outside nested event containers
            top_scalars = {
                k: v for k, v in raw.items()
                if k not in ("attributes", "event", "events", "rawEvents", "triggeringEvents") and not isinstance(v, (dict, list))
            }
            if top_scalars:
                cls._extract_from_dict(top_scalars, "PAYLOAD", obs_time, add_record, unmapped_fields)

        # Aggregate and categorize
        by_type: Dict[str, List[CanonicalEvidenceRecord]] = {}
        by_field: Dict[str, List[CanonicalEvidenceRecord]] = {}
        field_status_map: Dict[str, str] = {}
        for r in records:
            by_type.setdefault(r.evidence_type, []).append(r)
            by_field.setdefault(r.source_field, []).append(r)
            field_status_map[r.source_field] = "PRESENT_VALID"

        return EvidenceNormalizationResult(
            incident_id=incident_id,
            total_evidence_count=len(records),
            available_evidence_count=len(records),
            records=records,
            evidence_by_type=by_type,
            evidence_by_field=by_field,
            unmapped_fields=unmapped_fields,
            missing_fields=[],
            field_validation_status=field_status_map,
        )

    @classmethod
    def _extract_from_dict(
        cls,
        data: Dict[str, Any],
        source_event_id: str,
        observed_at: Optional[str],
        add_fn: Any,
        unmapped_fields: Optional[List[Dict[str, Any]]] = None,
        is_kv_extracted: bool = False,
    ) -> None:
        """Recursively parses a dictionary, mapping known SOC attributes to canonical fields."""
        for key, val in data.items():
            if val is None or val == "":
                continue

            norm_k = str(key).strip().lower()
            if norm_k in FORBIDDEN_GROUND_TRUTH_KEYS or any(fgk in norm_k for fgk in ("ground_truth", "analyst_verdict", "cleared")):
                continue

            # Skip large unparsed raw log text containers in recursive dict parsing to prevent self-recursion
            if norm_k in ("rawmessage", "raweventlog", "rawlog", "rawmsg", "rawevent", "eventlog", "datastr"):
                continue

            if isinstance(val, dict):
                cls._extract_from_dict(val, source_event_id, observed_at, add_fn, unmapped_fields, is_kv_extracted)
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        cls._extract_from_dict(item, source_event_id, observed_at, add_fn, unmapped_fields, is_kv_extracted)
            else:
                # Check mapping via literal and cleaned key lookup
                mapping = resolve_field_mapping(key)
                if mapping:
                    trans = "KEY_VALUE_EXTRACTED" if is_kv_extracted else "ALIASED"
                    add_fn(
                        source_field=mapping["field"],
                        observed_value=val,
                        evidence_type=mapping["type"],
                        source_event_id=source_event_id,
                        observed_at=observed_at,
                        raw_field_name=str(key),
                        transformation=trans,
                    )
                else:
                    # Record unmapped field
                    if unmapped_fields is not None:
                        unmapped_fields.append({
                            "raw_field": str(key),
                            "value": str(val)[:200],
                            "reason": "NO_CANONICAL_MAPPING",
                            "source_event_id": source_event_id,
                        })

                    # Generic heuristic for unrecognized fields if high-signal
                    if any(term in norm_k for term in ("ip", "port", "host", "domain", "user", "file", "path", "hash", "proc")):
                        add_fn(
                            source_field=f"telemetry.{norm_k}",
                            observed_value=val,
                            evidence_type="ENDPOINT_TELEMETRY",
                            source_event_id=source_event_id,
                            observed_at=observed_at,
                            raw_field_name=str(key),
                            transformation="HEURISTIC_FALLBACK",
                        )
