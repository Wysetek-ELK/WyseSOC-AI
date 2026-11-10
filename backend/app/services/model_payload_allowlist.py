from typing import Dict, Any, List, Optional
from app.schemas.incident import ModelFacingIncidentPayload, ModelFacingEvent

# FORBIDDEN KEYS: Any field related to ground truth, historical closure, analyst verdict, or post-investigation metadata
FORBIDDEN_GROUND_TRUTH_KEYS = frozenset({
    "resolution",
    "incidentresolution",
    "clearedreason",
    "cleared_reason",
    "incidentclearedreason",
    "comments",
    "incidentcomments",
    "closure_comments",
    "closurecomments",
    "cleareduser",
    "cleared_user",
    "cmsclearuser",
    "cms_clear_user",
    "clearedtime",
    "cleared_time",
    "resolvedat",
    "resolved_at",
    "historical_resolution",
    "is_ml_generated",
    "analyst_verdict",
    "analystverdict",
    "analyst_notes",
    "analystnotes",
    "mttr",  # Mean Time To Resolution (post-closure calculation)
})


PRIORITY_SOC_KEYS = frozenset({
    "cmdline", "command", "processcommandline", "parentcmd", "parentcmdline",
    "filepath", "process", "app", "imagepath", "filename",
    "username", "user", "srcuser", "targetuser",
    "srcip", "destip", "srcport", "destport", "destdomain", "url", "uri",
    "action", "status", "eventmsg", "rawmsg", "sha256", "md5", "hash",
    "devname", "hostname", "devip", "devid"
})


def sanitize_event_attributes(attributes: Dict[str, Any], max_str_len: int = 180, max_keys: int = 8) -> Dict[str, Any]:
    """Filters nested event attributes, dropping forbidden resolution/closure fields, prioritizing high-signal SOC keys, and truncating strings."""
    sanitized: Dict[str, Any] = {}
    
    # 1. Filter out forbidden keys and empty/none values
    candidates: Dict[str, Any] = {}
    for key, val in attributes.items():
        norm_key = key.lower().strip()
        if norm_key in FORBIDDEN_GROUND_TRUTH_KEYS:
            continue
        if val is None or val == "":
            continue
        candidates[key] = val

    # 2. Extract priority SOC investigation keys first
    priority_items = []
    other_items = []
    for key, val in candidates.items():
        norm_key = key.lower().strip()
        if norm_key in PRIORITY_SOC_KEYS:
            priority_items.append((key, val))
        else:
            other_items.append((key, val))

    ordered_items = (priority_items + other_items)[:max_keys]

    # 3. Format and bounded truncation
    for key, val in ordered_items:
        if isinstance(val, str):
            if len(val) > max_str_len:
                sanitized[key] = val[:max_str_len] + "... [truncated]"
            else:
                sanitized[key] = val
        elif isinstance(val, dict):
            sanitized[key] = sanitize_event_attributes(val, max_str_len=max_str_len, max_keys=max_keys)
        else:
            sanitized[key] = val

    return sanitized


def _get_field(obj: Any, attr_name: str, dict_key: str, default: Any = "") -> Any:
    """Safely extracts field whether obj is a SQLAlchemy model or a dictionary."""
    if isinstance(obj, dict):
        return obj.get(dict_key, default)
    val = getattr(obj, attr_name, default)
    return val if val is not None else default


def build_model_facing_payload(
    incident: Any,
    rule: Optional[Any] = None,
    events: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """
    Constructs an explicit, strictly allowlisted incident investigation payload.
    Guarantees 100% absence of historical ground-truth resolution or closure fields.
    Budgets payload size to fit comfortably within LLM context windows.
    """
    sanitized_events: List[Dict[str, Any]] = []
    if events:
        # Cap to 2 most relevant telemetry events to preserve LLM token budget and fast inference
        for evt in events[:2]:
            evt_id = _get_field(evt, "event_id", "eventId", "")
            evt_type = _get_field(evt, "event_type", "eventType", "")
            evt_time = _get_field(evt, "event_receive_time", "eventReceiveTime", None)
            raw_attrs = _get_field(evt, "attributes", "attribute", {})
            if not isinstance(raw_attrs, dict):
                raw_attrs = {}

            sanitized_attrs = sanitize_event_attributes(raw_attrs, max_str_len=180, max_keys=8)
            sanitized_events.append({
                "event_id": str(evt_id),
                "event_type": str(evt_type),
                "event_receive_time": evt_time,
                "attributes": sanitized_attrs,
            })

    def _trunc(val: Any, max_len: int = 250) -> str:
        s = str(val or "")
        return s[:max_len] + ("... [truncated]" if len(s) > max_len else "")

    rule_pattern = getattr(rule, "pattern_logic", None) if rule else None

    # Safely extract and backfill network and device entities if top-level fields are generic or empty
    src_ip = str(_get_field(incident, "source_ip", "sourceIp", "")).strip()
    rep_dev = str(_get_field(incident, "reporting_device", "reportingDevice", "")).strip()
    rep_ip = str(_get_field(incident, "reporting_ip", "reportingIp", "")).strip()

    if (not src_ip or src_ip.lower() in ("internal", "host", "internal / host", "n/a", "none")) and sanitized_events:
        for ev in sanitized_events:
            attrs = ev.get("attributes", {})
            candidate = attrs.get("srcIp") or attrs.get("src_ip") or attrs.get("sourceIp") or attrs.get("sourceIP")
            if candidate:
                src_ip = str(candidate).strip()
                break

    if not rep_dev and sanitized_events:
        for ev in sanitized_events:
            attrs = ev.get("attributes", {})
            candidate = attrs.get("devName") or attrs.get("reportingDevice") or attrs.get("hostName") or attrs.get("deviceName")
            if candidate:
                rep_dev = str(candidate).strip()
                break

    # Strict allowlist of top-level incident fields with bounded text length
    payload: Dict[str, Any] = {
        "incident_id": str(_get_field(incident, "incident_id", "incidentId", "")),
        "event_type": str(_get_field(incident, "event_type", "eventType", "")),
        "title": _trunc(_get_field(incident, "title", "title", ""), 200),
        "description": _trunc(_get_field(incident, "description", "description", ""), 250),
        "detail": _trunc(_get_field(incident, "detail", "detail", ""), 250),
        "severity": str(_get_field(incident, "severity", "severity", "MEDIUM")),
        "category": str(_get_field(incident, "category", "category", "")),
        "subcategory": str(_get_field(incident, "subcategory", "subcategory", "")),
        "source_ip": src_ip,
        "reporting_device": rep_dev,
        "reporting_ip": rep_ip,
        "first_seen_epoch": _get_field(incident, "first_seen_epoch", "firstSeen", None),
        "last_seen_epoch": _get_field(incident, "last_seen_epoch", "lastSeen", None),
        "created_at_epoch": _get_field(incident, "created_at_epoch", "createdAt", None),
        "events": sanitized_events,
        "rule_id": getattr(rule, "rule_id", None) if rule else None,
        "rule_name": getattr(rule, "name", None) if rule else None,
        "rule_pattern": _trunc(rule_pattern, 250) if rule_pattern else None,
    }

    # Strict audit verification before returning: assert zero leakage
    for forbidden_key in FORBIDDEN_GROUND_TRUTH_KEYS:
        if forbidden_key in payload:
            raise ValueError(f"CRITICAL SECURITY VIOLATION: Forbidden key '{forbidden_key}' in model payload!")

    return payload


class EvidenceIntegrityGuardrail:
    """
    Evidence Integrity Guardrail.
    Enforces strict zero-leakage evidence filtering, sanitization of event attributes,
    and exclusion of ground truth / resolution / analyst notes before model ingestion.
    """
    sanitize_event_attributes = staticmethod(sanitize_event_attributes)
    build_model_facing_payload = staticmethod(build_model_facing_payload)

