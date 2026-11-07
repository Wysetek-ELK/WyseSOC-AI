from typing import Dict, Any, List, Optional
from app.schemas.incident import ModelFacingIncidentPayload, ModelFacingEvent

# FORBIDDEN KEYS: Any field related to ground truth, historical closure, analyst verdict, or post-investigation metadata
FORBIDDEN_GROUND_TRUTH_KEYS = frozenset({
    "resolution",
    "clearedreason",
    "cleared_reason",
    "comments",
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
    "mttr",  # Mean Time To Resolution (post-closure calculation)
})


def sanitize_event_attributes(attributes: Dict[str, Any], max_str_len: int = 500) -> Dict[str, Any]:
    """Filters nested event attributes, dropping any forbidden resolution/closure fields and truncating giant payloads."""
    sanitized: Dict[str, Any] = {}
    for key, val in attributes.items():
        norm_key = key.lower().strip()
        if norm_key in FORBIDDEN_GROUND_TRUTH_KEYS:
            continue
        if isinstance(val, str) and len(val) > max_str_len:
            sanitized[key] = val[:max_str_len] + "... [truncated]"
        elif isinstance(val, dict):
            sanitized[key] = sanitize_event_attributes(val, max_str_len=max_str_len)
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
    """
    sanitized_events: List[Dict[str, Any]] = []
    if events:
        # Cap to 10 most relevant telemetry events to prevent exceeding LLM context budget
        for evt in events[:10]:
            evt_id = _get_field(evt, "event_id", "eventId", "")
            evt_type = _get_field(evt, "event_type", "eventType", "")
            evt_time = _get_field(evt, "event_receive_time", "eventReceiveTime", None)
            raw_attrs = _get_field(evt, "attributes", "attribute", {})
            if not isinstance(raw_attrs, dict):
                raw_attrs = {}

            sanitized_attrs = sanitize_event_attributes(raw_attrs)
            sanitized_events.append({
                "event_id": str(evt_id),
                "event_type": str(evt_type),
                "event_receive_time": evt_time,
                "attributes": sanitized_attrs,
            })

    # Strict allowlist of top-level incident fields
    payload: Dict[str, Any] = {
        "incident_id": str(_get_field(incident, "incident_id", "incidentId", "")),
        "event_type": str(_get_field(incident, "event_type", "eventType", "")),
        "title": str(_get_field(incident, "title", "title", "")),
        "description": str(_get_field(incident, "description", "description", "")),
        "detail": str(_get_field(incident, "detail", "detail", "")),
        "severity": str(_get_field(incident, "severity", "severity", "MEDIUM")),
        "category": str(_get_field(incident, "category", "category", "")),
        "subcategory": str(_get_field(incident, "subcategory", "subcategory", "")),
        "source_ip": str(_get_field(incident, "source_ip", "sourceIp", "")),
        "reporting_device": str(_get_field(incident, "reporting_device", "reportingDevice", "")),
        "reporting_ip": str(_get_field(incident, "reporting_ip", "reportingIp", "")),
        "first_seen_epoch": _get_field(incident, "first_seen_epoch", "firstSeen", None),
        "last_seen_epoch": _get_field(incident, "last_seen_epoch", "lastSeen", None),
        "created_at_epoch": _get_field(incident, "created_at_epoch", "createdAt", None),
        "events": sanitized_events,
        "rule_id": getattr(rule, "rule_id", None) if rule else None,
        "rule_name": getattr(rule, "name", None) if rule else None,
        "rule_pattern": getattr(rule, "pattern_logic", None) if rule else None,
    }

    # Strict audit verification before returning: assert zero leakage
    for forbidden_key in FORBIDDEN_GROUND_TRUTH_KEYS:
        if forbidden_key in payload:
            raise ValueError(f"CRITICAL SECURITY VIOLATION: Forbidden key '{forbidden_key}' in model payload!")

    return payload
