import pytest
from app.services.model_payload_allowlist import (
    build_model_facing_payload,
    FORBIDDEN_GROUND_TRUTH_KEYS,
)


def test_ground_truth_isolation_zero_leakage():
    # Simulate a raw incident dictionary that includes sensitive ground truth and post-closure fields
    raw_incident = {
        "incidentId": "132438483",
        "eventType": "PH_RULE_CS_SUSPICIOUS_ACTIVITY",
        "title": "CrowdStrike Suspicious Activity Detected",
        "description": "Suspicious process executed on host",
        "detail": "powershell.exe -enc ...",
        "severity": "MEDIUM",
        "category": "Malware",
        "subcategory": "Execution",
        "sourceIp": "192.168.1.100",
        "reportingDevice": "CrowdStrike Falcon",
        "reportingIp": "10.0.0.1",
        "firstSeen": 1793781975000,
        "lastSeen": 1793783460000,
        "createdAt": 1793781984408,
        # SENSITIVE HISTORICAL GROUND TRUTH:
        "resolution": "False Positive",
        "clearedReason": "kill process is true and file verified safe",
        "comments": "Resolution set by Machine Learning model",
        "clearedUser": "analyst_bob",
        "clearedTime": 1793783492775,
        "resolvedAt": 1793783492775,
        "mttr": 1500,
        "rawEvents": [
            {
                "eventId": "evt_001",
                "eventType": "ProcessRollup2",
                "eventReceiveTime": 1793781975000,
                "attribute": {
                    "Command": "powershell.exe -NoProfile",
                    "Host Name": "WORKSTATION-01",
                    "Attack Tactic": "Execution",
                    "resolution": "ATTEMPTED_LEAK_IN_EVENT",
                    "clearedReason": "ATTEMPTED_LEAK_IN_ATTR",
                }
            }
        ]
    }

    payload = build_model_facing_payload(raw_incident, events=raw_incident["rawEvents"])

    # 1. Assert top-level payload does NOT contain any forbidden key
    for forbidden_key in FORBIDDEN_GROUND_TRUTH_KEYS:
        assert forbidden_key not in payload, f"Security Violation: '{forbidden_key}' found in top-level payload!"
        assert forbidden_key.lower() not in [k.lower() for k in payload.keys()]

    # 2. Assert nested event attributes do NOT contain any forbidden key
    for evt in payload["events"]:
        for forbidden_key in FORBIDDEN_GROUND_TRUTH_KEYS:
            assert forbidden_key not in evt["attributes"], f"Security Violation: '{forbidden_key}' found in event attributes!"

    # 3. Assert allowed telemetry fields ARE retained properly
    assert payload["incident_id"] == "132438483"
    assert payload["event_type"] == "PH_RULE_CS_SUSPICIOUS_ACTIVITY"
    assert payload["source_ip"] == "192.168.1.100"
    assert len(payload["events"]) == 1
    assert payload["events"][0]["attributes"]["Command"] == "powershell.exe -NoProfile"
    assert payload["events"][0]["attributes"]["Host Name"] == "WORKSTATION-01"

