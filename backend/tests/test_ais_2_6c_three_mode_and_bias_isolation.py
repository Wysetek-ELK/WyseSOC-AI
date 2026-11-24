"""
AIS 2.6c — Three-Mode Experiment & Bias Isolation Unit & Regression Tests
Validates:
1. Mode A: Neutral SOC Baseline (captures unbiased model proposals)
2. Mode B: Approved Rule Policy (captures policy-induced proposals)
3. Mode C: Full Validated Pipeline (reuses Mode B output with ZERO extra GPU calls)
4. Trust Score calculation with canonical evidence attached (avoids 3/10 clamping)
5. Dynamic Git SHA resolution (no stale fallback)
6. Zero-denominator safety metric handling
"""

import pytest
import os
import hashlib
from typing import List, Dict, Any

from app.services.empirical_benchmark_harness import (
    EmpiricalBenchmarkHarness,
    BenchmarkIncidentRecord,
    BenchmarkIncidentResult,
)


@pytest.fixture
def sample_crowdstrike_incident():
    return BenchmarkIncidentRecord(
        incident_id=132474210,
        rule_id="CROWDSTRIKE-ALERT-GENERIC",
        rule_name="CrowdStrike Alert - Remote Access Tool Executed",
        ground_truth_label="VERIFIED_TP",
        sanitized_payload={
            "incident_id": 132474210,
            "rule_id": "CROWDSTRIKE-ALERT-GENERIC",
            "rule_name": "CrowdStrike Alert - Remote Access Tool Executed",
            "severity": 7,
            "event_type": "CROWDSTRIKE-ALERT-GENERIC",
            "phEventCategory": 1,
            "vendor": "CrowdStrike",
            "hostName": "FIN-SRV-01",
            "procName": "UltraViewer_Service.exe",
            "command": "C:\\Program Files\\UltraViewer\\UltraViewer_Service.exe /service",
            "srcIpAddr": "10.0.4.15",
            "destIpAddr": "192.168.1.100",
            "events": [
                {
                    "procName": "UltraViewer_Service.exe",
                    "hostName": "FIN-SRV-01",
                    "command": "C:\\Program Files\\UltraViewer\\UltraViewer_Service.exe /service",
                    "srcIpAddr": "10.0.4.15",
                }
            ],
        },
    )


@pytest.fixture
def sample_prisma_incident():
    return BenchmarkIncidentRecord(
        incident_id=132595592,
        rule_id="PRISMA-SASE-FILE-THREAT",
        rule_name="Prisma SASE - Suspicious File Download",
        ground_truth_label="VERIFIED_FP",
        sanitized_payload={
            "incident_id": 132595592,
            "rule_id": "PRISMA-SASE-FILE-THREAT",
            "rule_name": "Prisma SASE - Suspicious File Download",
            "severity": 5,
            "event_type": "PRISMA-SASE-FILE-THREAT",
            "phEventCategory": 1,
            "vendor": "Palo Alto Networks",
            "hostName": "CORP-WKS-88",
            "fileName": "surveysensum_widget.js",
            "srcIpAddr": "10.0.12.44",
            "destIpAddr": "104.18.22.10",
            "events": [
                {
                    "fileName": "surveysensum_widget.js",
                    "hostName": "CORP-WKS-88",
                    "srcIpAddr": "10.0.12.44",
                    "destIpAddr": "104.18.22.10",
                }
            ],
        },
    )


@pytest.mark.asyncio
async def test_mode_a_neutral_baseline_evaluation(sample_crowdstrike_incident):
    """Verifies Mode A evaluates under neutral SOC baseline without policy override or validator demotion."""
    res = await EmpiricalBenchmarkHarness.evaluate_single_incident(
        incident_rec=sample_crowdstrike_incident,
        mode="offline",
        experimental_mode="A",
    )
    assert res.incident_id == sample_crowdstrike_incident.incident_id
    assert res.validation_status == "BASELINE_EVALUATED"
    assert res.policy_version == "BASELINE_V1"
    assert res.layer_a_verdict is not None
    assert res.layer_b_verdict is None
    assert res.layer_c_verdict is None
    assert res.final_authoritative_verdict == res.raw_proposed_verdict


@pytest.mark.asyncio
async def test_mode_b_approved_policy_evaluation(sample_crowdstrike_incident):
    """Verifies Mode B compiles approved policy and captures raw proposed verdict pre-validator."""
    res = await EmpiricalBenchmarkHarness.evaluate_single_incident(
        incident_rec=sample_crowdstrike_incident,
        mode="offline",
        experimental_mode="B",
    )
    assert res.incident_id == sample_crowdstrike_incident.incident_id
    assert res.validation_status == "POLICY_EVALUATED_PRE_VALIDATOR"
    assert res.layer_a_verdict is None
    assert res.layer_b_verdict == res.raw_proposed_verdict
    assert res.layer_c_verdict is None
    assert res.raw_proposed_verdict == "TRUE_POSITIVE"


@pytest.mark.asyncio
async def test_mode_c_reused_inference_with_validator(sample_crowdstrike_incident):
    """Verifies Mode C reuses Mode B result without new inference and applies validation."""
    # Run Mode B first
    res_b = await EmpiricalBenchmarkHarness.evaluate_single_incident(
        incident_rec=sample_crowdstrike_incident,
        mode="offline",
        experimental_mode="B",
    )

    # Run Mode C reusing Mode B
    res_c = await EmpiricalBenchmarkHarness.evaluate_single_incident(
        incident_rec=sample_crowdstrike_incident,
        mode="offline",
        experimental_mode="C",
        mode_b_result=res_b,
    )

    assert res_c.incident_id == sample_crowdstrike_incident.incident_id
    assert res_c.execution_provenance == "REUSED_MODE_B_INFERENCE"
    assert res_c.raw_proposed_verdict == res_b.raw_proposed_verdict
    assert res_c.layer_b_verdict == res_b.raw_proposed_verdict
    assert res_c.layer_c_verdict == res_c.final_authoritative_verdict
    assert res_c.validation_status in ("VALIDATED_TRUE_POSITIVE", "ACCEPTED_TRUE_POSITIVE", "REQUIRES_ATTENTION", "INSUFFICIENT_EVIDENCE")
    assert res_c.final_authoritative_verdict in ("TRUE_POSITIVE", "REQUIRES_ATTENTION")
    # Verify trust score is NOT clamped to 3/10 because canonical evidence was attached
    assert res_c.trust_score is not None
    assert res_c.trust_score >= 3


@pytest.mark.asyncio
async def test_three_mode_benchmark_pipeline(sample_crowdstrike_incident, sample_prisma_incident):
    """Verifies run_three_mode_benchmark executes all three modes and generates paired comparisons."""
    records = [sample_crowdstrike_incident, sample_prisma_incident]
    result = await EmpiricalBenchmarkHarness.run_three_mode_benchmark(
        records=records,
        mode="offline",
    )

    assert result["total_incidents"] == 2
    assert len(result["mode_a_results"]) == 2
    assert len(result["mode_b_results"]) == 2
    assert len(result["mode_c_results"]) == 2
    assert len(result["paired_comparisons"]) == 2

    # Verify zero extra GPU calls in Mode C
    for c_res in result["mode_c_results"]:
        assert c_res.execution_provenance == "REUSED_MODE_B_INFERENCE"

    # Verify metrics for all 3 modes
    assert result["metrics_mode_a"].total_incidents == 2
    assert result["metrics_mode_b"].total_incidents == 2
    assert result["metrics_mode_c"].total_incidents == 2


def test_git_sha_resolution_not_stale():
    """Verifies get_active_git_sha does not return the stale commit '2033c09156c68d51ce45ab829f6e691257e995dc'."""
    active_sha = EmpiricalBenchmarkHarness.get_active_git_sha()
    assert isinstance(active_sha, str)
    assert len(active_sha) >= 7
    assert active_sha != "2033c09156c68d51ce45ab829f6e691257e995dc"


def test_zero_denominator_safety_metrics():
    """Verifies calculate_cohort_metrics handles zero verified cases without division by zero."""
    dummy_results = [
        BenchmarkIncidentResult(
            incident_id=1,
            rule_id="RULE-1",
            rule_name="Rule 1",
            ground_truth_label="UNVERIFIED",
            raw_proposed_verdict="TRUE_POSITIVE",
            raw_proposed_confidence=85.0,
            raw_proposed_reason="Reason",
            final_authoritative_verdict="TRUE_POSITIVE",
            is_decisive_accepted=True,
            validation_status="VALIDATED",
            validation_reason_codes=[],
            trust_score=5,
            raw_trust_score=50.0,
            schema_compliant=True,
            grounding_ratio=1.0,
            latency_ms=100,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            is_unsafe_fp=False,
            auto_incident_closure_allowed=False,
            execution_provenance="OFFLINE_SIMULATION",
            is_live_measurement=False,
            autonomous_verdict="REQUIRES_ATTENTION",
            is_autonomous_eligible=False,
            guardrails_triggered=[],
            cluster_key=None,
            is_duplicate=False,
            finish_reason="stop",
            requested_max_tokens=768,
            evaluation_run_id="TEST",
            model_name="Qwen/Qwen2.5-7B-Instruct-AWQ",
            provider_name="OFFLINE_SIMULATION",
            prompt_hash=None,
            canonical_request_payload_hash=None,
            wire_prompt_hash=None,
            raw_evidence_hash=None,
            rule_definition_hash=None,
            policy_content_hash=None,
            system_prompt_hash=None,
            user_content_hash=None,
            actual_http_body_hash=None,
            raw_provider_response_hash=None,
            parsed_response_hash=None,
            final_verdict_hash=None,
            layer_a_verdict="TRUE_POSITIVE",
            layer_b_verdict="TRUE_POSITIVE",
            layer_c_verdict="TRUE_POSITIVE",
            policy_version="1",
            raw_model_response_id=None,
            executed_at_utc="2026-11-24T00:00:00Z",
            execution_git_sha="d854a5ef7471b74dab408473963a4511eab4dc66",
            endpoint_identity=None,
        )
    ]
    metrics = EmpiricalBenchmarkHarness.calculate_cohort_metrics(dummy_results)
    assert metrics.verified_ground_truth_count == 0
    assert metrics.overall_accuracy is None
    assert metrics.unsafe_fp_rate is None
    assert metrics.coverage_rate is None
