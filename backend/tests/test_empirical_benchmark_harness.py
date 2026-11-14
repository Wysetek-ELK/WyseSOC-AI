"""
Automated Regression Suite for Phase B: Empirical Benchmark Harness.
Tests dataset loading, ground truth adjudication, anti-data-leakage blinding,
production-equivalent pipeline execution, Wilson score confidence intervals,
unsafe FP detection, and report generation.
"""

import os
import pytest
from app.services.empirical_benchmark_harness import (
    EmpiricalBenchmarkHarness,
    BenchmarkIncidentRecord,
    BenchmarkIncidentResult,
    BenchmarkMetrics,
)


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

    # Verify zero leakage detected in sanitized payload
    for r in records:
        assert r.leakage_detected is False, f"Incident {r.incident_id} leaked keys: {r.leakage_keys_found}"
        assert "resolution" not in r.sanitized_payload
        assert "clearedReason" not in r.sanitized_payload
        assert "comments" not in r.sanitized_payload


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
    assert result.latency_ms >= 0
    assert result.total_tokens > 0
    assert result.execution_provenance == "OFFLINE_SIMULATION"


@pytest.mark.asyncio
async def test_unsafe_fp_detection_and_blocking():
    """
    Verifies that when an incident is verified TP, the validator rejects unverified FP,
    preventing any unsafe false positive and blocking automatic incident closure.
    """
    records = EmpiricalBenchmarkHarness.load_dataset_from_zip()
    tp_records = [r for r in records if r.ground_truth_label == "VERIFIED_TP"]
    assert len(tp_records) > 0

    # Pick a verified TP incident
    tp_rec = tp_records[0]

    # Force simulated model to propose FALSE_POSITIVE without authorization
    def force_unverified_fp(inc, norm):
        return {
            "verdict": "FALSE_POSITIVE",
            "confidence": 95.0,
            "reason": "Internal routine administrative execution.",
            "supporting_claims": [
                {
                    "claim_type": "PROCESS_EXECUTION",
                    "field": "process.name",
                    "asserted_value": "powershell.exe",
                    "evidence_ids": [norm.records[0].evidence_id] if norm.records else [],
                }
            ],
        }

    res = await EmpiricalBenchmarkHarness.evaluate_single_incident(
        incident_rec=tp_rec,
        mode="offline",
        simulated_output_fn=force_unverified_fp,
    )

    # Must be forced to REQUIRES_ATTENTION by IndependentVerdictValidator
    assert res.final_authoritative_verdict == "REQUIRES_ATTENTION"
    assert res.is_decisive_accepted is False
    assert res.is_unsafe_fp is False  # Correctly prevented from being accepted as FP!
    assert res.auto_incident_closure_allowed is False


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
        source="fixtures",
        mode="offline",
    )

    assert report.report_id.startswith("EMP-BENCH-")
    assert report.overall_metrics.total_incidents == 20
    assert report.overall_metrics.verified_ground_truth_count > 0

    m = report.overall_metrics
    # Statistical power warning must be active because N = 20 < 30
    assert m.statistical_power_warning is True
    assert "N=" in m.power_warning_reason

    # Confusion matrix consistency
    assert (m.tp + m.tn + m.fp + m.fn + m.total_abstained) == m.verified_ground_truth_count

    # Check rule breakdown
    assert len(report.rule_breakdown) >= 2
    for r_id, rm in report.rule_breakdown.items():
        assert rm.total_incidents > 0

    # Check Markdown report generation
    md_content = EmpiricalBenchmarkHarness.generate_markdown_report(report)
    assert "# Verdictum AI — Empirical Accuracy Benchmark Report" in md_content
    assert "Confusion Matrix" in md_content
    assert "Trust Score Calibration Bins" in md_content
    assert "Performance by Detection Rule" in md_content
    assert "Statistical Power & Sample Size Limitation" in md_content

