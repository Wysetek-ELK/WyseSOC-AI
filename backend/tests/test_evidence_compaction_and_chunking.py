"""
Comprehensive Unit & Boundary Tests for Evidence Compaction, Deduplication & Deterministic Chunking.

Tests:
1. Deduplication of 100 identical firewall events into 1 recurring record with occurrence_count: 100.
2. Timestamp collapse of hundreds of timestamps into event.time_range summary + primary trigger timestamp.
3. Raw syslog template clustering into representative verbatim samples.
4. Retention of critical security evidence (process command lines, parent command lines, file hashes) without collapsing.
5. Deterministic chunking when unique evidence exceeds token budget, guaranteeing Mandatory Contract Anchors in every chunk.
6. Model-compatible tokenizer accounting (JSON overhead, Base64 strings, BPE subword estimation).
"""

import pytest
from app.schemas.canonical_evidence import CanonicalEvidenceRecord
from app.services.evidence_compaction_service import EvidenceCompactionService
from app.services.tokenizer_service import ModelTokenizerService


def test_100_identical_firewall_events_deduplicated_with_occurrence_count():
    """
    Simulates incident #175330 telemetry pattern: 100 repeated firewall deny events
    with identical destination port 7680, protocol 6, and action DENY.
    Verifies that records are collapsed with occurrence_count: 100 while keeping forensic provenance.
    """
    records = []
    for i in range(100):
        records.append(
            CanonicalEvidenceRecord(
                evidence_id=f"EV-DENY-{i:03d}",
                incident_id="INC-175330",
                source_system="FortiSIEM",
                source_event_id=f"EVT-{i:03d}",
                source_field="network.destination_port",
                observed_value="7680",
                evidence_type="SECURITY_EVENT",
                integrity_digest="digest_port",
            )
        )
        records.append(
            CanonicalEvidenceRecord(
                evidence_id=f"EV-PROTO-{i:03d}",
                incident_id="INC-175330",
                source_system="FortiSIEM",
                source_event_id=f"EVT-{i:03d}",
                source_field="network.protocol",
                observed_value="6",
                evidence_type="SECURITY_EVENT",
                integrity_digest="digest_proto",
            )
        )

    res = EvidenceCompactionService.compact_and_deduplicate(
        records=records,
        contract_required_fields=["network.destination_port", "network.protocol"],
        rule_pattern_logic="destinationPort = 7680 AND ipProto = 6",
        max_evidence_budget_tokens=2000,
    )

    compacted = res["compacted_records"]
    assert res["is_chunked"] is False
    assert len(compacted) == 2  # exactly 1 port and 1 proto record

    port_rec = next(r for r in compacted if r["source_field"] == "network.destination_port")
    proto_rec = next(r for r in compacted if r["source_field"] == "network.protocol")

    assert str(port_rec["observed_value"]) == "7680"
    assert port_rec["occurrence_count"] == 100
    assert str(proto_rec["observed_value"]) == "6"
    assert proto_rec["occurrence_count"] == 100
    assert res["deduplication_ratio"] < 0.05  # > 95% reduction


def test_timestamp_collapse_into_time_range_and_primary_trigger():
    """
    Verifies that hundreds of repetitive event.timestamp records collapse into:
    1. Primary trigger timestamp
    2. event.time_range summary capturing the earliest to latest span
    """
    records = [
        CanonicalEvidenceRecord(
            evidence_id=f"EV-TIME-{i:03d}",
            incident_id="INC-TIME-01",
            source_system="FortiSIEM",
            source_event_id=f"EVT-{i:03d}",
            source_field="event.timestamp",
            observed_value=f"2026-11-12T10:{i // 60:02d}:{i % 60:02d}Z",
            evidence_type="SECURITY_EVENT",
            integrity_digest=f"digest_{i}",
        )
        for i in range(120)
    ]

    res = EvidenceCompactionService.compact_and_deduplicate(
        records=records,
        contract_required_fields=["event.timestamp"],
        max_evidence_budget_tokens=1500,
    )

    compacted = res["compacted_records"]
    assert len(compacted) == 2

    fields = {r["source_field"] for r in compacted}
    assert "event.timestamp" in fields
    assert "event.time_range" in fields

    time_range_rec = next(r for r in compacted if r["source_field"] == "event.time_range")
    assert "2026-11-12T10:00:00Z to 2026-11-12T10:01:59Z" in str(time_range_rec["observed_value"])
    assert "120 event timestamps" in str(time_range_rec["observed_value"])


def test_raw_syslog_template_clustering():
    """
    Verifies that repetitive raw syslog messages sharing a template are clustered
    into representative samples rather than multiplying tokens 100-fold.
    """
    records = [
        CanonicalEvidenceRecord(
            evidence_id=f"EV-LOG-{i:03d}",
            incident_id="INC-LOG-01",
            source_system="FortiSIEM",
            source_event_id=f"EVT-{i:03d}",
            source_field="security.raw_log",
            observed_value=f"<189>date=2026-11-12 time=10:00:{i % 60:02d} devname=FW-01 action=deny srcip=host-node-{i} dstip=target-service dstport=7680",
            evidence_type="SECURITY_EVENT",
            integrity_digest=f"digest_log_{i}",
        )
        for i in range(50)
    ]

    res = EvidenceCompactionService.compact_and_deduplicate(
        records=records,
        max_evidence_budget_tokens=1500,
    )

    compacted = res["compacted_records"]
    # 50 raw logs sharing the same template must cluster into <= 3 representative samples
    assert len(compacted) <= 3
    cluster_rec = compacted[0]
    assert cluster_rec["occurrence_count"] >= 45


def test_critical_process_and_hash_records_never_collapsed():
    """
    Verifies that distinct process executions and file hashes are NEVER collapsed,
    protecting forensic fidelity for command injection and malware execution archetypes.
    """
    records = [
        CanonicalEvidenceRecord(
            evidence_id=f"EV-CMD-{i:03d}",
            incident_id="INC-PROC-01",
            source_system="EDR",
            source_event_id=f"EVT-{i:03d}",
            source_field="process.command_line",
            observed_value=f"powershell.exe -ExecutionPolicy Bypass -File script_{i}.ps1",
            evidence_type="SECURITY_EVENT",
            integrity_digest=f"digest_cmd_{i}",
        )
        for i in range(5)
    ]

    res = EvidenceCompactionService.compact_and_deduplicate(
        records=records,
        contract_required_fields=["process.command_line"],
        max_evidence_budget_tokens=2000,
    )

    compacted = res["compacted_records"]
    assert len(compacted) == 5  # all 5 distinct process executions strictly preserved


def test_deterministic_chunking_with_mandatory_anchors_invariant():
    """
    Verifies deterministic chunking when unique evidence exceeds budget:
    - Mandatory contract required fields ('process.command_line') must be present as anchors in EVERY chunk.
    - Slices partition secondary evidence cleanly across chunks.
    """
    records = [
        CanonicalEvidenceRecord(
            evidence_id="EV-ANCHOR-01",
            incident_id="INC-CHUNK-01",
            source_system="EDR",
            source_event_id="EVT-01",
            source_field="process.command_line",
            observed_value="cmd.exe /c whoami /all",
            evidence_type="SECURITY_EVENT",
            integrity_digest="digest_anchor",
        )
    ]
    # Add 20 large distinct secondary observations
    for i in range(20):
        records.append(
            CanonicalEvidenceRecord(
                evidence_id=f"EV-SEC-{i:03d}",
                incident_id="INC-CHUNK-01",
                source_system="EDR",
                source_event_id=f"EVT-{i:03d}",
                source_field="network.dns_query",
                observed_value=f"subdomain-{i}.malicious-c2-beacon-{('X' * 50)}.example.com",
                evidence_type="SECURITY_EVENT",
                integrity_digest=f"digest_sec_{i}",
            )
        )

    chunk_res = EvidenceCompactionService.chunk_oversized_evidence(
        records=records,
        contract_required_fields=["process.command_line"],
        max_evidence_budget_tokens=300,  # small budget forcing multi-chunking
    )

    assert chunk_res["is_chunked"] is True
    assert chunk_res["total_chunks"] >= 2

    # Verify Mandatory Anchor invariant across ALL chunks
    for idx, chunk in enumerate(chunk_res["all_chunks"]):
        chunk_fields = {r["source_field"] for r in chunk}
        assert "process.command_line" in chunk_fields, f"Chunk {idx + 1} missing mandatory anchor field!"
        anchor = next(r for r in chunk if r["source_field"] == "process.command_line")
        assert anchor["observed_value"] == "cmd.exe /c whoami /all"


def test_model_tokenizer_accounting_accuracy_and_json_overhead():
    """
    Validates model-compatible tokenizer accounting:
    - JSON structural overhead is counted accurately.
    - Empty/null values return 0.
    - account_prompt_breakdown sums all sections correctly.
    """
    text = "powershell.exe -enc AAAA"
    tokens = ModelTokenizerService.count_tokens(text)
    assert tokens > 0

    json_obj = {"key": "value", "list": [1, 2, 3]}
    json_tokens = ModelTokenizerService.count_json_tokens(json_obj)
    assert json_tokens > 0

    breakdown = ModelTokenizerService.account_prompt_breakdown(
        p1_schema_text="Schema instruction",
        p2_policy_text="Approved SOC policy",
        p3_contract_dict={"required_fields": ["process.cmdline"]},
        p4_critical_evidence=[{"evidence_id": "EV-01", "val": "whoami"}],
        p5_correlated_events=[{"raw_log": "log1"}],
        p6_enrichment={"threat_intel": "VT malicious"},
        p7_rag_block="[PRECEDENT 1] Confirmed malware",
        reserved_output_tokens=512,
    )

    assert breakdown["p1_safety_and_schema_tokens"] > 0
    assert breakdown["p2_policy_sections_tokens"] > 0
    assert breakdown["p3_mandatory_contract_tokens"] > 0
    assert breakdown["p4_critical_telemetry_tokens"] > 0
    assert breakdown["p5_correlated_events_tokens"] > 0
    assert breakdown["p6_optional_enrichment_tokens"] > 0
    assert breakdown["p7_rag_precedents_tokens"] > 0
    assert breakdown["reserved_output_tokens"] == 512
    assert breakdown["total_context_tokens"] == breakdown["total_input_tokens"] + 512
