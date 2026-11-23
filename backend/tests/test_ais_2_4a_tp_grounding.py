"""
Unit and regression tests for AIS 2.4a:
- Corrected TRUE_POSITIVE decision grounding (Check 5 in IndependentVerdictValidator).
- Prevention of unsupported TP acceptance on 132499009 (ss-widget.min.js survey widget).
- Rule trigger, filename, and internal IP alone cannot prove malicious tradecraft.
- Direct forensic evidence (e.g., LOLBin attack markers) supports TP without external TI.
- Strict forensic ground truth adjudication: operational escalation/ticketing notes are UNVERIFIED.
- Auditable execution provenance taxonomy (LIVE_PROVIDER, PREFLIGHT_ABSTENTION, OFFLINE_SIMULATION, PROVIDER_FAILURE).
"""

import pytest
from typing import Dict, Any, List

from app.schemas.canonical_evidence import CanonicalEvidenceRecord, EvidenceNormalizationResult
from app.schemas.evidence_contract import RuleEvidenceContract, EvidenceFieldRequirement
from app.services.evidence_preflight_validator import EvidencePreflightValidator
from app.services.model_claim_extractor import ModelClaimExtractor
from app.services.independent_verdict_validator import IndependentVerdictValidator
from app.services.historical_ground_truth_validator import HistoricalGroundTruthValidator
from app.schemas.verdict_intelligence import GroundTruthLabel
from app.services.empirical_benchmark_harness import (
    EmpiricalBenchmarkHarness,
    BenchmarkIncidentRecord,
    BenchmarkIncidentResult,
)


def _make_rec(ev_id: str, field: str, value: Any, ev_type: str, inc_id: str = "INC-TEST") -> CanonicalEvidenceRecord:
    return CanonicalEvidenceRecord(
        evidence_id=ev_id,
        incident_id=inc_id,
        source_field=field,
        observed_value=value,
        evidence_type=ev_type,
        integrity_digest=f"digest-{ev_id}",
    )


def _make_norm(records: List[CanonicalEvidenceRecord], inc_id: str = "INC-TEST") -> EvidenceNormalizationResult:
    by_type: Dict[str, List[CanonicalEvidenceRecord]] = {}
    by_field: Dict[str, List[CanonicalEvidenceRecord]] = {}
    for r in records:
        by_type.setdefault(r.evidence_type, []).append(r)
        by_field.setdefault(r.source_field, []).append(r)
    return EvidenceNormalizationResult(
        incident_id=inc_id,
        total_evidence_count=len(records),
        available_evidence_count=len(records),
        records=records,
        evidence_by_type=by_type,
        evidence_by_field=by_field,
        field_validation_status={r.source_field: "PRESENT_VALID" for r in records},
    )


def _make_contract(rule_id: str = "PH_RULE_TEST", required_fields: List[str] = None) -> RuleEvidenceContract:
    reqs = [
        EvidenceFieldRequirement(field=f, evidence_type="OBSERVED_FACT", critical=True)
        for f in (required_fields or ["process.file_name", "network.source_ip"])
    ]
    return RuleEvidenceContract(
        contract_id=f"CONTRACT-{rule_id}",
        rule_id=rule_id,
        rule_name="Test Rule",
        version_number=1,
        status="APPROVED",
        required_evidence=reqs,
    )


def test_tp_rejection_for_survey_widget_132499009():
    """
    CRITICAL DEFECT REMEDIATION:
    Incident 132499009 (ss-widget.min.js SurveySensum widget, internal IP 172.25.14.80)
    must NOT be accepted as TRUE_POSITIVE when proposed by the model.
    The validator must reject it because internal IP and JS filename alone do not prove malicious attack tradecraft.
    """
    inc_id = "132499009"
    records = [
        _make_rec("EV-1", "file.name", "ss-widget.min.js", "FILE_CONTEXT", inc_id),
        _make_rec("EV-2", "network.source_ip", "172.25.14.80", "NETWORK_CONNECTION", inc_id),
        _make_rec("EV-3", "security.alert_title", "Prisma SASE ss-widget.min.js Suspicious File Threat Detection", "SECURITY_EVENT", inc_id),
        _make_rec("EV-4", "security.action", "alert", "SECURITY_EVENT", inc_id),
        _make_rec("EV-5", "application.name", "surveysensum-base", "NETWORK_CONNECTION", inc_id),
    ]
    norm_result = _make_norm(records, inc_id)
    contract = _make_contract("PH_RULE_PRISMA", ["file.name", "network.source_ip"])
    preflight = EvidencePreflightValidator.validate_preflight(
        incident_id=inc_id,
        contract=contract,
        normalization_result=norm_result,
        allow_simulation=True,
    )

    # Flawed or adversarial model proposal asserting TRUE_POSITIVE
    model_output = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 88.0,
        "reason": "Suspicious file threat ss-widget.min.js detected from source 172.25.14.80.",
        "supporting_claims": [
            {
                "claim_type": "SECURITY_EVENT",
                "field": "file.name",
                "asserted_value": "ss-widget.min.js",
                "cited_evidence_ids": ["EV-1"],
            },
            {
                "claim_type": "NETWORK_CONNECTION",
                "field": "network.source_ip",
                "asserted_value": "172.25.14.80",
                "cited_evidence_ids": ["EV-2"],
            },
        ],
    }

    grounding = ModelClaimExtractor.extract_and_ground_claims(inc_id, model_output, norm_result)
    val_res = IndependentVerdictValidator.validate_verdict(
        incident_id=inc_id,
        proposed_verdict="TRUE_POSITIVE",
        raw_model_confidence=88.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm_result,
        contract=contract,
        model_reason=model_output["reason"],
    )

    # Invariant: Must NOT accept TRUE_POSITIVE!
    assert val_res.final_verdict == "REQUIRES_ATTENTION", f"Expected REQUIRES_ATTENTION but got {val_res.final_verdict}"
    assert val_res.is_decisive_accepted is False
    assert "TP_CRITERIA_UNSATISFIED" in val_res.validation_reason_codes
    assert "Insufficient grounded tradecraft" in val_res.analyst_action_directive


def test_filename_and_ip_alone_cannot_prove_tradecraft():
    """
    Filename, IP addresses, and rule names are identifiers and alerts, NOT proof of attack tradecraft.
    """
    inc_id = "INC-IDENTIFIER-ONLY"
    records = [
        _make_rec("EV-PROC-1", "process.file_name", "update.exe", "PROCESS_EXECUTION", inc_id),
        _make_rec("EV-NET-1", "network.destination_ip", "10.0.0.5", "NETWORK_CONNECTION", inc_id),
    ]
    norm_result = _make_norm(records, inc_id)
    contract = _make_contract("PH_RULE_TEST", ["process.file_name", "network.destination_ip"])
    preflight = EvidencePreflightValidator.validate_preflight(
        incident_id=inc_id,
        contract=contract,
        normalization_result=norm_result,
        allow_simulation=True,
    )

    model_output = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 85.0,
        "reason": "Process update.exe connected to 10.0.0.5.",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "process.file_name",
                "asserted_value": "update.exe",
                "cited_evidence_ids": ["EV-PROC-1"],
            },
            {
                "claim_type": "NETWORK_CONNECTION",
                "field": "network.destination_ip",
                "asserted_value": "10.0.0.5",
                "cited_evidence_ids": ["EV-NET-1"],
            },
        ],
    }

    grounding = ModelClaimExtractor.extract_and_ground_claims(inc_id, model_output, norm_result)
    val_res = IndependentVerdictValidator.validate_verdict(
        incident_id=inc_id,
        proposed_verdict="TRUE_POSITIVE",
        raw_model_confidence=85.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm_result,
        contract=contract,
        model_reason=model_output["reason"],
    )

    assert val_res.final_verdict == "REQUIRES_ATTENTION"
    assert val_res.is_decisive_accepted is False
    assert "TP_CRITERIA_UNSATISFIED" in val_res.validation_reason_codes


def test_direct_forensic_evidence_supports_tp_without_external_ti():
    """
    Direct forensic attack markers (e.g. vssadmin delete shadows, LOLBin encoded command)
    MUST support TRUE_POSITIVE even in the absence of an external threat-intel feed.
    """
    inc_id = "INC-ATTACK-FORENSIC"
    attack_cmd = "vssadmin.exe delete shadows /all /quiet"
    records = [
        _make_rec("EV-CMD-1", "process.command_line", attack_cmd, "PROCESS_EXECUTION", inc_id),
        _make_rec("EV-HOST-1", "endpoint.hostname", "FIN-SRV-01", "USER_CONTEXT", inc_id),
    ]
    norm_result = _make_norm(records, inc_id)
    contract = _make_contract("PH_RULE_TEST", ["process.command_line", "endpoint.hostname"])
    preflight = EvidencePreflightValidator.validate_preflight(
        incident_id=inc_id,
        contract=contract,
        normalization_result=norm_result,
        allow_simulation=True,
    )

    model_output = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 95.0,
        "reason": f"Adversary shadow copy deletion detected: {attack_cmd}.",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "process.command_line",
                "asserted_value": attack_cmd,
                "cited_evidence_ids": ["EV-CMD-1"],
            },
            {
                "claim_type": "USER_CONTEXT",
                "field": "endpoint.hostname",
                "asserted_value": "FIN-SRV-01",
                "cited_evidence_ids": ["EV-HOST-1"],
            },
        ],
    }

    grounding = ModelClaimExtractor.extract_and_ground_claims(inc_id, model_output, norm_result)
    val_res = IndependentVerdictValidator.validate_verdict(
        incident_id=inc_id,
        proposed_verdict="TRUE_POSITIVE",
        raw_model_confidence=95.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm_result,
        contract=contract,
        model_reason=model_output["reason"],
    )

    assert val_res.final_verdict == "TRUE_POSITIVE"
    assert val_res.is_decisive_accepted is True
    assert "EVIDENCE_VALIDATED" in val_res.validation_reason_codes


def test_encoded_powershell_supports_tp():
    """
    Encoded command execution in command line represents verified tradecraft.
    """
    inc_id = "INC-PS-ENC"
    cmd = "powershell.exe -nop -w hidden -enc JABzACAAPQAgAE4AZQB3AC0ATwBiAGoAZQBjAHQA..."
    records = [
        _make_rec("EV-PS-1", "process.command_line", cmd, "PROCESS_EXECUTION", inc_id),
        _make_rec("EV-HOST-2", "endpoint.hostname", "WORKSTATION-99", "USER_CONTEXT", inc_id),
    ]
    norm_result = _make_norm(records, inc_id)
    contract = _make_contract("PH_RULE_TEST", ["process.command_line", "endpoint.hostname"])
    preflight = EvidencePreflightValidator.validate_preflight(
        incident_id=inc_id,
        contract=contract,
        normalization_result=norm_result,
        allow_simulation=True,
    )

    model_output = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 92.0,
        "reason": f"Obfuscated PowerShell execution with -enc argument.",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "process.command_line",
                "asserted_value": cmd,
                "cited_evidence_ids": ["EV-PS-1"],
            }
        ],
    }

    grounding = ModelClaimExtractor.extract_and_ground_claims(inc_id, model_output, norm_result)
    val_res = IndependentVerdictValidator.validate_verdict(
        incident_id=inc_id,
        proposed_verdict="TRUE_POSITIVE",
        raw_model_confidence=92.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm_result,
        contract=contract,
        model_reason=model_output["reason"],
    )

    assert val_res.final_verdict == "TRUE_POSITIVE"
    assert val_res.is_decisive_accepted is True


def test_strict_forensic_ground_truth_adjudication():
    """
    Operational escalation or notification actions alone ('Mail has been sent already',
    'Case has been raised for the similar incidents.') must be adjudicated as UNVERIFIED
    when strict_forensic_only is enabled.
    """
    # Incident 132596403: "Mail has been sent already"
    lbl, score, rat = HistoricalGroundTruthValidator.adjudicate_label(
        raw_resolution="True Positive",
        cleared_reason="Mail has been sent already",
        strict_forensic_only=True,
    )
    assert lbl == GroundTruthLabel.UNVERIFIED
    assert "Operational escalation or notification note" in rat

    # Incident 132599145: "Case has been raised for the similar incidents."
    lbl2, score2, rat2 = HistoricalGroundTruthValidator.adjudicate_label(
        raw_resolution="True Positive",
        cleared_reason="Case has been raised for the similar incidents.",
        strict_forensic_only=True,
    )
    assert lbl2 == GroundTruthLabel.UNVERIFIED
    assert "Operational escalation or notification note" in rat2

    # Verified attack with forensic rationale:
    lbl3, score3, rat3 = HistoricalGroundTruthValidator.adjudicate_label(
        raw_resolution="True Positive",
        cleared_reason="Malware confirmed: cobaltstrike beacon payload detected and isolated.",
        strict_forensic_only=True,
    )
    assert lbl3 == GroundTruthLabel.VERIFIED_TP
    assert score3 == 1.0


def test_provenance_taxonomy_types():
    """
    Verifies that BenchmarkIncidentResult supports the strict execution provenance taxonomy:
    LIVE_PROVIDER, PREFLIGHT_ABSTENTION, OFFLINE_SIMULATION, PROVIDER_FAILURE.
    """
    res_live = BenchmarkIncidentResult(
        incident_id="INC-1",
        rule_id="RULE-1",
        rule_name="Rule 1",
        ground_truth_label="VERIFIED_FP",
        execution_provenance="LIVE_PROVIDER",
        is_live_measurement=True,
        latency_ms=1250,
        prompt_tokens=2048,
        completion_tokens=256,
        total_tokens=2304,
        finish_reason="stop",
        prompt_hash="a1b2c3d4",
        policy_version="1",
        raw_model_response_id="RESP-001",
        execution_git_sha="2033c09156c68d51ce45ab829f6e691257e995dc",
    )
    assert res_live.execution_provenance == "LIVE_PROVIDER"
    assert res_live.is_live_measurement is True
    assert res_live.latency_ms == 1250

    res_abstained = BenchmarkIncidentResult(
        incident_id="INC-2",
        rule_id="RULE-1",
        rule_name="Rule 1",
        ground_truth_label="VERIFIED_FP",
        execution_provenance="PREFLIGHT_ABSTENTION",
        is_live_measurement=False,
        finish_reason="abstained_preflight",
    )
    assert res_abstained.execution_provenance == "PREFLIGHT_ABSTENTION"
    assert res_abstained.is_live_measurement is False

    res_sim = BenchmarkIncidentResult(
        incident_id="INC-3",
        rule_id="RULE-1",
        rule_name="Rule 1",
        ground_truth_label="VERIFIED_FP",
        execution_provenance="OFFLINE_SIMULATION",
        is_live_measurement=False,
    )
    assert res_sim.execution_provenance == "OFFLINE_SIMULATION"
    assert res_sim.is_live_measurement is False


def test_alert_trigger_alone_does_not_prove_tradecraft():
    """
    A detection-rule trigger or alert title is an alert, not independent confirmation of malicious tradecraft.
    """
    inc_id = "INC-ALERT-TRIGGER-ONLY"
    records = [
        _make_rec("EV-ALERT-1", "security.alert_title", "Crowdstrike: Suspicious Activity", "SECURITY_EVENT", inc_id),
        _make_rec("EV-ALERT-2", "security.event_type", "EndpointProcessSuspicious", "SECURITY_EVENT", inc_id),
    ]
    norm_result = _make_norm(records, inc_id)
    contract = _make_contract("PH_RULE_TEST", ["security.alert_title", "security.event_type"])
    preflight = EvidencePreflightValidator.validate_preflight(
        incident_id=inc_id,
        contract=contract,
        normalization_result=norm_result,
        allow_simulation=True,
    )

    model_output = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 85.0,
        "reason": "Detection rule triggered for EndpointProcessSuspicious.",
        "supporting_claims": [
            {
                "claim_type": "SECURITY_EVENT",
                "field": "security.alert_title",
                "asserted_value": "Crowdstrike: Suspicious Activity",
                "cited_evidence_ids": ["EV-ALERT-1"],
            },
            {
                "claim_type": "SECURITY_EVENT",
                "field": "security.event_type",
                "asserted_value": "EndpointProcessSuspicious",
                "cited_evidence_ids": ["EV-ALERT-2"],
            },
        ],
    }

    grounding = ModelClaimExtractor.extract_and_ground_claims(inc_id, model_output, norm_result)
    val_res = IndependentVerdictValidator.validate_verdict(
        incident_id=inc_id,
        proposed_verdict="TRUE_POSITIVE",
        raw_model_confidence=85.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm_result,
        contract=contract,
        model_reason=model_output["reason"],
    )

    assert val_res.final_verdict == "REQUIRES_ATTENTION"
    assert val_res.is_decisive_accepted is False
    assert "TP_CRITERIA_UNSATISFIED" in val_res.validation_reason_codes


def test_benign_evidence_evaluated_under_fp_criteria():
    """
    Legitimate benign evidence (e.g. authorized administrative tool or verified clean reputation)
    is properly evaluated under approved FP criteria.
    """
    inc_id = "INC-BENIGN-FP"
    records = [
        _make_rec("EV-PROC-1", "process.file_name", "ccmexec.exe", "PROCESS_EXECUTION", inc_id),
        _make_rec("EV-PATH-1", "process.executable_path", "C:\\Windows\\CCM\\CcmExec.exe", "PROCESS_EXECUTION", inc_id),
        _make_rec("EV-AUTH-1", "user.name", "SYSTEM", "USER_CONTEXT", inc_id),
        _make_rec("EV-HOST-1", "endpoint.hostname", "CORP-WKS-12", "USER_CONTEXT", inc_id),
        _make_rec("EV-TICKET-1", "authorization.ticket_id", "CHG-10293", "AUTHORIZATION", inc_id),
        _make_rec("EV-STATUS-1", "authorization.status", "approved", "AUTHORIZATION", inc_id),
    ]
    norm_result = _make_norm(records, inc_id)
    contract = _make_contract("PH_RULE_TEST", ["process.file_name", "user.name", "endpoint.hostname"])
    preflight = EvidencePreflightValidator.validate_preflight(
        incident_id=inc_id,
        contract=contract,
        normalization_result=norm_result,
        allow_simulation=True,
    )

    model_output = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 90.0,
        "reason": "Authorized standard SCCM client agent execution by SYSTEM under approved ticket CHG-10293.",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "process.file_name",
                "asserted_value": "ccmexec.exe",
                "cited_evidence_ids": ["EV-PROC-1"],
            },
            {
                "claim_type": "USER_CONTEXT",
                "field": "user.name",
                "asserted_value": "SYSTEM",
                "cited_evidence_ids": ["EV-AUTH-1"],
            },
        ],
    }

    grounding = ModelClaimExtractor.extract_and_ground_claims(inc_id, model_output, norm_result)
    val_res = IndependentVerdictValidator.validate_verdict(
        incident_id=inc_id,
        proposed_verdict="FALSE_POSITIVE",
        raw_model_confidence=90.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm_result,
        contract=contract,
        model_reason=model_output["reason"],
    )

    # Benign execution validated under FP rules
    assert val_res.final_verdict == "FALSE_POSITIVE"
    assert val_res.is_decisive_accepted is True
    assert "EVIDENCE_VALIDATED" in val_res.validation_reason_codes


def test_duplicate_clusters_isolated_in_metrics():
    """
    Cohort metrics must isolate unique-cluster metrics separately from raw duplicate counts.
    """
    results = [
        BenchmarkIncidentResult(
            incident_id="INC-1", rule_id="R1", rule_name="R1", ground_truth_label="VERIFIED_FP",
            final_authoritative_verdict="FALSE_POSITIVE", is_decisive_accepted=True,
            is_duplicate=False, cluster_key="cluster-A"
        ),
        BenchmarkIncidentResult(
            incident_id="INC-2", rule_id="R1", rule_name="R1", ground_truth_label="VERIFIED_FP",
            final_authoritative_verdict="FALSE_POSITIVE", is_decisive_accepted=True,
            is_duplicate=True, cluster_key="cluster-A"
        ),
        BenchmarkIncidentResult(
            incident_id="INC-3", rule_id="R1", rule_name="R1", ground_truth_label="VERIFIED_FP",
            final_authoritative_verdict="FALSE_POSITIVE", is_decisive_accepted=True,
            is_duplicate=True, cluster_key="cluster-A"
        ),
        BenchmarkIncidentResult(
            incident_id="INC-4", rule_id="R1", rule_name="R1", ground_truth_label="VERIFIED_FP",
            final_authoritative_verdict="FALSE_POSITIVE", is_decisive_accepted=True,
            is_duplicate=False, cluster_key="cluster-B"
        ),
    ]

    metrics = EmpiricalBenchmarkHarness.calculate_cohort_metrics(results)
    assert metrics.total_incidents == 4
    assert metrics.duplicate_incident_count == 2
    assert metrics.unique_clusters_count == 2
    assert metrics.duplicate_cluster_count == 1
    assert metrics.unique_cluster_metrics is not None
    assert metrics.unique_cluster_metrics["total_unique_clusters"] == 2
    assert metrics.unique_cluster_metrics["decisive_decisions"] == 2

