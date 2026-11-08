"""
test_evidence_normalization.py
Phase 2 Test Suite: Canonical Evidence Normalization (Scenarios 1-10)

Tests:
1. Valid FortiSIEM process execution telemetry normalization
2. Telemetry with missing command line
3. Telemetry with missing parent process
4. Telemetry with null user context
5. Telemetry with missing destination IP in network event
6. Telemetry with invalid/string epoch timestamp
7. Telemetry with malformed raw JSON payload
8. Telemetry with duplicate events (deduplication & uniqueness)
9. Multiple correlated events normalization
10. Preservation of original raw payload without mutation
11. Ground truth isolation: forbidden keys strictly excluded from canonical evidence
"""

import pytest
from app.services.evidence_normalization_service import EvidenceNormalizationService
from app.schemas.canonical_evidence import CanonicalEvidenceRecord, EvidenceNormalizationResult


class DummyEvent:
    def __init__(self, event_id, event_type="FortiSIEM-Event", receive_time=1700000000, attributes=None, raw_log=None):
        self.id = event_id
        self.event_id = event_id
        self.event_type = event_type
        self.event_receive_time = receive_time
        self.attributes = attributes or {}
        self.raw_log = raw_log


class DummyIncident:
    def __init__(self, incident_id="INC-1001", source_ip="192.168.1.50", reporting_device="EDR-AGENT-01",
                 category="Malware", subcategory="ProcessExecution", raw_payload=None, events=None,
                 created_at_epoch=1700000000000, reporting_ip=None, event_type=None, title=None):
        self.id = incident_id
        self.incident_id = incident_id
        self.source_ip = source_ip
        self.reporting_device = reporting_device
        self.reporting_ip = reporting_ip
        self.category = category
        self.subcategory = subcategory
        self.event_type = event_type or "Trojan Detection"
        self.title = title or "Malware Activity Detected"
        self.created_at_epoch = created_at_epoch
        self.raw_payload = raw_payload or {}
        self.events = events or []


def test_scenario_01_valid_process_execution():
    """Scenario 1: Valid FortiSIEM process execution is normalized into canonical records."""
    evt = DummyEvent(
        event_id="EVT-01",
        attributes={
            "process": "cmd.exe",
            "processPath": "C:\\Windows\\System32\\cmd.exe",
            "cmdline": "cmd.exe /c whoami",
            "parentProcess": "powershell.exe",
            "parentCmdline": "powershell.exe -ep bypass",
            "user": "DOMAIN\\analyst_bob",
            "sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        }
    )
    inc = DummyIncident(incident_id="INC-01", events=[evt])

    norm_res = EvidenceNormalizationService.normalize_incident_evidence(inc)
    assert norm_res.total_evidence_count > 0
    records_by_field = {r.source_field: r for r in norm_res.records}

    assert "process.name" in records_by_field
    assert records_by_field["process.name"].observed_value == "cmd.exe"
    assert records_by_field["process.name"].evidence_type == "PROCESS_EXECUTION"

    assert "process.command_line" in records_by_field
    assert records_by_field["process.command_line"].observed_value == "cmd.exe /c whoami"

    assert "process.parent_name" in records_by_field
    assert "user.name" in records_by_field
    assert "file.hash_sha256" in records_by_field
    assert records_by_field["file.hash_sha256"].evidence_type == "FILE_HASH"

    # Check deterministic evidence ID and SHA256 integrity digest
    for r in norm_res.records:
        assert r.evidence_id.startswith("EV-INC-01-")
        assert len(r.integrity_digest) == 64  # valid SHA-256 hex string


def test_scenario_02_missing_command_line():
    """Scenario 2: Telemetry with missing command line handles omission gracefully."""
    evt = DummyEvent(
        event_id="EVT-02",
        attributes={
            "process": "rundll32.exe",
            "imagepath": "C:\\Windows\\System32\\rundll32.exe",
            # No cmdline provided
            "user": "SYSTEM",
        }
    )
    inc = DummyIncident(incident_id="INC-02", events=[evt])
    norm_res = EvidenceNormalizationService.normalize_incident_evidence(inc)

    fields = [r.source_field for r in norm_res.records]
    assert "process.name" in fields
    assert "process.command_line" not in fields  # Missing field is safely omitted


def test_scenario_03_missing_parent_process():
    """Scenario 3: Telemetry with missing parent process."""
    evt = DummyEvent(
        event_id="EVT-03",
        attributes={
            "process": "svchost.exe",
            "cmdline": "svchost.exe -k netsvcs",
            # No parent process
        }
    )
    inc = DummyIncident(incident_id="INC-03", events=[evt])
    norm_res = EvidenceNormalizationService.normalize_incident_evidence(inc)

    fields = [r.source_field for r in norm_res.records]
    assert "process.name" in fields
    assert "process.parent_name" not in fields


def test_scenario_04_null_user_context():
    """Scenario 4: Telemetry with explicit null or empty user context."""
    evt = DummyEvent(
        event_id="EVT-04",
        attributes={
            "process": "svchost.exe",
            "user": None,
            "username": "",
            "account": "   ",
        }
    )
    inc = DummyIncident(incident_id="INC-04", events=[evt])
    norm_res = EvidenceNormalizationService.normalize_incident_evidence(inc)

    fields = [r.source_field for r in norm_res.records]
    assert "user.name" not in fields  # None and empty strings are dropped cleanly


def test_scenario_05_missing_dest_ip_in_network_event():
    """Scenario 5: Network event with source IP but missing destination IP."""
    evt = DummyEvent(
        event_id="EVT-05",
        event_type="Firewall-Traffic",
        attributes={
            "srcip": "10.0.0.15",
            "srcport": "44322",
            # destip is absent
        }
    )
    inc = DummyIncident(incident_id="INC-05", events=[evt])
    norm_res = EvidenceNormalizationService.normalize_incident_evidence(inc)

    fields = [r.source_field for r in norm_res.records]
    assert "network.source_ip" in fields
    assert "network.destination_ip" not in fields


def test_scenario_06_invalid_timestamp():
    """Scenario 6: Event with non-integer or malformed timestamp falls back safely."""
    evt = DummyEvent(
        event_id="EVT-06",
        receive_time="NOT_A_TIMESTAMP",  # type: ignore
        attributes={"process": "taskmgr.exe"}
    )
    inc = DummyIncident(incident_id="INC-06", events=[evt])
    norm_res = EvidenceNormalizationService.normalize_incident_evidence(inc)
    assert norm_res.total_evidence_count > 0
    # Process name is still normalized cleanly
    assert any(r.source_field == "process.name" for r in norm_res.records)


def test_scenario_07_malformed_raw_payload():
    """Scenario 7: Incident with malformed/non-dict raw payload does not crash."""
    inc = DummyIncident(incident_id="INC-07", raw_payload="not a dictionary payload", events=[])
    norm_res = EvidenceNormalizationService.normalize_incident_evidence(inc)
    # Should safely extract incident-level source_ip and reporting_device
    fields = [r.source_field for r in norm_res.records]
    assert "network.source_ip" in fields
    assert "endpoint.hostname" in fields


def test_scenario_08_duplicate_raw_events():
    """Scenario 8: Duplicate raw events are deduplicated."""
    evt1 = DummyEvent(event_id="EVT-DUP", attributes={"process": "cmd.exe", "user": "alice"})
    evt2 = DummyEvent(event_id="EVT-DUP", attributes={"process": "cmd.exe", "user": "alice"})
    inc = DummyIncident(incident_id="INC-08", events=[evt1, evt2])

    norm_res = EvidenceNormalizationService.normalize_incident_evidence(inc)
    evidence_ids = [r.evidence_id for r in norm_res.records]
    # No duplicate evidence IDs
    assert len(evidence_ids) == len(set(evidence_ids))


def test_scenario_09_multiple_correlated_events():
    """Scenario 9: Multiple correlated events normalized into distinct evidence records."""
    evt1 = DummyEvent(event_id="EVT-A", attributes={"process": "powershell.exe", "cmdline": "powershell.exe -c curl"})
    evt2 = DummyEvent(event_id="EVT-B", attributes={"destip": "203.0.113.5", "destport": 443})
    inc = DummyIncident(incident_id="INC-09", events=[evt1, evt2])

    norm_res = EvidenceNormalizationService.normalize_incident_evidence(inc)
    event_ids = {r.source_event_id for r in norm_res.records}
    assert "EVT-A" in event_ids
    assert "EVT-B" in event_ids


def test_scenario_10_preservation_of_raw_payload():
    """Scenario 10: Normalization never mutates original raw payload or events."""
    raw_copy = {"original_key": "original_val", "nested": {"param": 42}}
    inc = DummyIncident(incident_id="INC-10", raw_payload=dict(raw_copy), events=[])

    EvidenceNormalizationService.normalize_incident_evidence(inc)
    assert inc.raw_payload == raw_copy


def test_scenario_ground_truth_isolation():
    """Forbidden ground truth keys must NEVER appear in canonical evidence."""
    evt = DummyEvent(
        event_id="EVT-GT",
        attributes={
            "process": "malware.exe",
            "resolution": "True Positive - Malicious",
            "cleared_reason": "Confirmed Trojan",
            "cleared_user": "Tier 3 Analyst",
            "ground_truth": {"verdict": "TRUE_POSITIVE"}
        }
    )
    inc = DummyIncident(
        incident_id="INC-GT",
        raw_payload={
            "resolution": "True Positive",
            "cleared_reason": "Analyst Confirmed",
            "process": "malware.exe"
        },
        events=[evt]
    )

    norm_res = EvidenceNormalizationService.normalize_incident_evidence(inc)
    source_fields = {r.source_field for r in norm_res.records}

    assert "resolution" not in source_fields
    assert "cleared_reason" not in source_fields
    assert "cleared_user" not in source_fields
    assert "ground_truth" not in source_fields
    for rec in norm_res.records:
        assert "resolution" not in rec.source_field.lower()
        assert "cleared_reason" not in rec.source_field.lower()
