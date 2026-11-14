"""
Automated Regression Suite for Phase B & Final Empirical Benchmark Readiness.
Tests dataset loading from ZIP and DB, ground truth adjudication, anti-data-leakage blinding,
production-equivalent pipeline execution, Wilson score confidence intervals,
deterministic positive/negative acceptance and rejection, separation of live vs mock metrics,
and report generation.
"""

import copy
import os
import pytest
from app.services.empirical_benchmark_harness import (
    EmpiricalBenchmarkHarness,
    BenchmarkIncidentRecord,
    BenchmarkIncidentResult,
    BenchmarkMetrics,
    IncidentAdapter,
)
from app.services.evidence_normalization_service import EvidenceNormalizationService


def test_load_dataset_from_zip():
    """Verifies loading and adjudicating historical FortiSIEM incidents from zip fixtures."""
    records = EmpiricalBenchmarkHarness.load_dataset_from_zip()
    assert len(records) == 20, f"Expected 20 historical incidents, found {len(records)}"

    rule_ids = {r.rule_id for r in records}
    assert "PH_RULE_CS_SUSPICIOUS_ACTIVITY" in rule_ids
    assert "PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE" in rule_ids

    # Check ground truth label adjudication
    gt_labels = [r.ground_truth_label for r in records]
    assert "VERIFIED_TP" in gt_labels
    assert "VERIFIED_FP" in gt_labels
    assert "UNVERIFIED" in gt_labels

    # Verify zero leakage detected in sanitized payload
    for r in records:
        assert r.leakage_detected is False, f"Incident {r.incident_id} leaked keys: {r.leakage_keys_found}"
        assert "resolution" not in r.sanitized_payload
        assert "clearedReason" not in r.sanitized_payload
        assert "comments" not in r.sanitized_payload


def test_load_dataset_from_db():
    """Verifies loading and adjudicating incidents from SQLite database in read-only mode."""
    records = EmpiricalBenchmarkHarness.load_dataset_from_db()
    assert len(records) >= 20, f"Expected at least 20 incidents from DB, found {len(records)}"
    for r in records:
        assert r.leakage_detected is False
        assert "resolution" not in r.sanitized_payload
        assert r.source_origin == "DB"


def test_load_dataset_unified():
    """Verifies merging and deduplicating records across ZIP and DB sources."""
    unified = EmpiricalBenchmarkHarness.load_dataset_unified()
    assert len(unified) >= 20
    inc_ids = [r.incident_id for r in unified]
    assert len(inc_ids) == len(set(inc_ids)), "Unified dataset must not contain duplicate incident IDs"

    dups = [r for r in unified if r.is_duplicate]
    assert len(dups) >= 0


def test_blinding_integrity_blocks_all_leakage():
    """Verifies that sensitive analyst labels and comments are completely stripped."""
    records = EmpiricalBenchmarkHarness.load_dataset_from_zip()
    for r in records:
        sanitized = r.sanitized_payload
        assert "resolution" not in sanitized
        assert "clearedReason" not in sanitized
        assert "clearedTime" not in sanitized
        assert "clearedUser" not in sanitized
        assert "cmsClearUser" not in sanitized
        assert "comments" not in sanitized


@pytest.mark.asyncio
async def test_single_incident_offline_evaluation():
    """Verifies execution of a single incident through production-equivalent pipeline."""
    records = EmpiricalBenchmarkHarness.load_dataset_from_zip()
    rec = records[0]

    result = await EmpiricalBenchmarkHarness.evaluate_single_incident(
        incident_rec=rec,
        mode="offline",
    )

    assert result.incident_id == rec.incident_id
    assert result.rule_id == rec.rule_id
    assert result.ground_truth_label == rec.ground_truth_label
    assert result.raw_proposed_verdict in ("TRUE_POSITIVE", "FALSE_POSITIVE", "REQUIRES_ATTENTION")
    assert result.final_authoritative_verdict in ("TRUE_POSITIVE", "FALSE_POSITIVE", "REQUIRES_ATTENTION")
    assert isinstance(result.trust_score, int)
    assert 1 <= result.trust_score <= 10
    # In offline mode, live tokens and latency must be None (not mock values)
    assert result.latency_ms is None
    assert result.total_tokens is None
    assert result.is_live_measurement is False
    assert result.execution_provenance == "OFFLINE_SIMULATION"


@pytest.mark.asyncio
async def test_deterministic_positive_tp_acceptance():
    """
    Positive Test: Verifies that a well-grounded TRUE_POSITIVE proposal with matching
    attack evidence is validated and accepted as decisive TRUE_POSITIVE.
    """
    records = EmpiricalBenchmarkHarness.load_dataset_from_zip()
    # Pick a Prisma SASE verified TP incident (e.g. 132596403)
    rec = next(r for r in records if r.incident_id == "132596403")
    inc_obj = IncidentAdapter(rec.sanitized_payload, rec.incident_id)
    norm = EvidenceNormalizationService.normalize_incident_evidence(inc_obj)

    # Locate actual normalized file and source IP records
    file_rec = next(r for r in norm.records if r.source_field == "process.file_name")
    src_rec = next(r for r in norm.records if r.source_field == "network.source_ip")

    well_grounded_proposal = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 92.0,
        "reason": f"Suspicious file threat {file_rec.observed_value} detected from network source IP {src_rec.observed_value}.",
        "supporting_claims": [
            {
                "claim_type": "SECURITY_EVENT",
                "field": file_rec.source_field,
                "asserted_value": file_rec.observed_value,
                "evidence_ids": [file_rec.evidence_id],
                "cited_evidence_ids": [file_rec.evidence_id],
            },
            {
                "claim_type": "NETWORK_CONNECTION",
                "field": src_rec.source_field,
                "asserted_value": src_rec.observed_value,
                "evidence_ids": [src_rec.evidence_id],
                "cited_evidence_ids": [src_rec.evidence_id],
            }
        ]
    }

    res = await EmpiricalBenchmarkHarness.evaluate_single_incident(
        incident_rec=rec,
        mode="offline",
        simulated_output_fn=lambda inc, n: well_grounded_proposal,
    )

    assert res.raw_proposed_verdict == "TRUE_POSITIVE"
    assert res.final_authoritative_verdict == "TRUE_POSITIVE"
    assert res.is_decisive_accepted is True
    assert res.validation_status == "VALIDATED"
    assert res.grounding_ratio == 1.0


@pytest.mark.asyncio
async def test_deterministic_positive_fp_acceptance():
    """
    Positive Test: Verifies that an approved administrative management binary (CcmExec.exe)
    executing from its verified path under SYSTEM is validated and accepted as decisive FALSE_POSITIVE.
    """
    sanitized = {
        "incidentId": "INC-ADMIN-FP-01",
        "title": "Crowdstrike suspicious activity detected on DESKTOP-E0G2R49",
        "severity": 5,
        "reportingDevice": "CrowdStrike Falcon",
        "reportingIp": "192.168.1.10",
        "rawEvents": [
            {
                "Process": "ccmexec.exe",
                "ImagePath": "C:\\Windows\\CCM\\CcmExec.exe",
                "User": "NT AUTHORITY\\SYSTEM",
                "Command": "C:\\Windows\\CCM\\CcmExec.exe",
                "ComputerName": "DESKTOP-E0G2R49",
            }
        ]
    }

    auth_rec = BenchmarkIncidentRecord(
        incident_id="INC-ADMIN-FP-01",
        rule_id="PH_RULE_CS_SUSPICIOUS_ACTIVITY",
        rule_name="Crowdstrike: Suspicious Activity",
        ground_truth_label="VERIFIED_FP",
        sanitized_payload=sanitized,
        incident_time_epoch=1793783492,
    )

    inc_obj = IncidentAdapter(auth_rec.sanitized_payload, auth_rec.incident_id)
    norm = EvidenceNormalizationService.normalize_incident_evidence(inc_obj)

    proc_rec = next(r for r in norm.records if r.source_field in ("process.name", "process.file_name"))
    host_rec = next((r for r in norm.records if r.source_field == "endpoint.hostname"), None)

    claims = [
        {
            "claim_type": "PROCESS_EXECUTION",
            "field": proc_rec.source_field,
            "asserted_value": proc_rec.observed_value,
            "evidence_ids": [proc_rec.evidence_id],
            "cited_evidence_ids": [proc_rec.evidence_id],
        }
    ]
    if host_rec:
        claims.append({
            "claim_type": "USER_CONTEXT",
            "field": host_rec.source_field,
            "asserted_value": host_rec.observed_value,
            "evidence_ids": [host_rec.evidence_id],
            "cited_evidence_ids": [host_rec.evidence_id],
        })

    fp_proposal = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 92.0,
        "reason": "Authorized execution of Microsoft SCCM management agent (CcmExec.exe) from verified system directory.",
        "supporting_claims": claims,
    }

    res = await EmpiricalBenchmarkHarness.evaluate_single_incident(
        incident_rec=auth_rec,
        mode="offline",
        simulated_output_fn=lambda inc, n: fp_proposal,
    )

    assert res.raw_proposed_verdict == "FALSE_POSITIVE"
    assert res.final_authoritative_verdict == "FALSE_POSITIVE"
    assert res.is_decisive_accepted is True
    assert res.validation_status == "VALIDATED"
    assert res.auto_incident_closure_allowed is True


@pytest.mark.asyncio
async def test_deterministic_negative_unsupported_fp_rejection():
    """
    Negative Test: Verifies that an unverified FALSE_POSITIVE (without maintenance ticket)
    is strictly rejected and demoted to REQUIRES_ATTENTION, blocking automatic closure.
    """
    records = EmpiricalBenchmarkHarness.load_dataset_from_zip()
    # Incident 132474210 is a Crowdstrike incident with no change ticket in raw telemetry
    rec = next(r for r in records if r.incident_id == "132474210")

    unsupported_fp = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 88.0,
        "reason": "Routine activity observed, seems benign.",
        "supporting_claims": [],
    }

    res = await EmpiricalBenchmarkHarness.evaluate_single_incident(
        incident_rec=rec,
        mode="offline",
        simulated_output_fn=lambda inc, n: unsupported_fp,
    )

    assert res.raw_proposed_verdict == "FALSE_POSITIVE"
    assert res.final_authoritative_verdict == "REQUIRES_ATTENTION"
    assert res.is_decisive_accepted is False
    assert res.auto_incident_closure_allowed is False


@pytest.mark.asyncio
async def test_deterministic_negative_fabrication_rejection():
    """
    Negative Test: Verifies that fabricated entities or invalid evidence IDs
    (EVIDENCE_VALUE_MISMATCH) cause claim rejection and force REQUIRES_ATTENTION.
    """
    records = EmpiricalBenchmarkHarness.load_dataset_from_zip()
    rec = records[0]

    inc_obj = IncidentAdapter(rec.sanitized_payload, rec.incident_id)
    norm = EvidenceNormalizationService.normalize_incident_evidence(inc_obj)

    fabricated_proposal = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 99.0,
        "reason": "Malicious payload detected.",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "process.file_name",
                "asserted_value": "totally_fabricated_malware.exe",
                "evidence_ids": [norm.records[0].evidence_id],  # ID of a timestamp record!
                "cited_evidence_ids": [norm.records[0].evidence_id],
            }
        ],
    }

    res = await EmpiricalBenchmarkHarness.evaluate_single_incident(
        incident_rec=rec,
        mode="offline",
        simulated_output_fn=lambda inc, n: fabricated_proposal,
    )

    assert res.final_authoritative_verdict == "REQUIRES_ATTENTION"
    assert res.is_decisive_accepted is False
    assert res.grounding_ratio == 0.0


def test_wilson_confidence_interval_calculation():
    """Verifies Wilson score confidence intervals for proportions."""
    # 0 successes out of 10
    ci0 = EmpiricalBenchmarkHarness.calculate_wilson_ci(0, 10)
    assert ci0.point_estimate == 0.0
    assert ci0.lower_bound == 0.0
    assert ci0.upper_bound > 0.0  # Wilson bound is non-zero even at 0 successes

    # 10 successes out of 10
    ci10 = EmpiricalBenchmarkHarness.calculate_wilson_ci(10, 10)
    assert ci10.point_estimate == 1.0
    assert ci10.lower_bound < 1.0
    assert ci10.upper_bound == 1.0

    # 8 successes out of 10
    ci8 = EmpiricalBenchmarkHarness.calculate_wilson_ci(8, 10)
    assert 0.0 <= ci8.lower_bound <= ci8.point_estimate <= ci8.upper_bound <= 1.0


@pytest.mark.asyncio
async def test_full_harness_run_and_report_generation():
    """Verifies full benchmark run across historical cohort, metric calculation, and report generation."""
    report = await EmpiricalBenchmarkHarness.run_benchmark(
        source="unified",
        mode="offline",
    )

    assert report.report_id.startswith("EMP-BENCH-")
    assert report.overall_metrics.total_incidents >= 20
    assert report.overall_metrics.verified_ground_truth_count > 0

    m = report.overall_metrics
    # Statistical power warning must be active because N < 30
    assert m.statistical_power_warning is True
    assert "N=" in m.power_warning_reason

    # Confusion matrix consistency
    assert (m.tp + m.tn + m.fp + m.fn + m.total_abstained) == m.verified_ground_truth_count

    # Check rule breakdown
    assert len(report.rule_breakdown) >= 2
    for r_id, rm in report.rule_breakdown.items():
        assert rm.total_incidents > 0

    # In offline mode, tokens and latency must be None / unmeasured
    assert m.is_live_measurement is False
    assert m.total_tokens is None
    assert m.mean_latency_ms is None

    # Check Markdown report generation
    md_content = EmpiricalBenchmarkHarness.generate_markdown_report(report)
    assert "# Verdictum AI — Empirical Accuracy Benchmark Report" in md_content
    assert "Confusion Matrix" in md_content
    assert "Trust Score Calibration Bins" in md_content
    assert "Performance by Detection Rule" in md_content
    assert "Statistical Power & Sample Size Limitation" in md_content
    assert "OFFLINE SAFETY SIMULATION" in md_content
