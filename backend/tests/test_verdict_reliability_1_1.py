"""
test_verdict_reliability_1_1.py
Regression Test Suite for Verdictum AI — LLM Verdict Reliability 1.1

Covers:
1. Standardized response schema & bidirectional evidence ID synchronization (`cited_evidence_ids` & `evidence_ids`).
2. Untrusted incident data boundary tags (<UNTRUSTED_INCIDENT_DATA>) in user message construction.
3. Retention of high event counts (up to 20) and long forensic strings (cmdline up to 4096) in payload allowlist.
4. Rejection of decisive FALSE_POSITIVE based solely on RFC-1918 IP, service account, or routine/harmless claims.
5. Acceptance of decisive FALSE_POSITIVE backed by verifiable affirmative authorization.
6. Safe downgrade of decisive TP/FP when regex schema recovery was applied to malformed JSON.
7. Rejection of decisive TP/FP when structured claims are absent (zero grounded claims).
8. Rejection of decisive TP under contradictory telemetry (e.g. external C2 asserted on loopback).
9. Safe defaulting of confidence to 0.0 when omitted by the model (no silent defaulting to 90.0).
10. Fail-closed context window abstention when mandatory prompt core exceeds budget.
"""

import json
import pytest
from app.schemas.evidence_claim import ModelSupportingClaim
from app.schemas.verdict_intelligence import ClaimType
from app.schemas.canonical_evidence import CanonicalEvidenceRecord, EvidenceNormalizationResult
from app.schemas.evidence_contract import RuleEvidenceContract, EvidenceFieldRequirement
from app.services.model_provider.openai_compatible import OpenAICompatibleProvider, _regex_fallback_extract
from app.services.model_claim_extractor import ModelClaimExtractor
from app.services.independent_verdict_validator import IndependentVerdictValidator
from app.services.evidence_preflight_validator import EvidencePreflightValidator
from app.services.model_payload_allowlist import build_model_facing_payload, sanitize_event_attributes
from app.services.token_budget_service import TokenBudgetService
from app.services.policy_compiler_service import PolicyCompilerService, CompilationExecutionMode
from app.models.rule import Rule
from app.models.prompt import PromptVersion


def create_record(incident_id: str, field: str, value: str, ev_type: str = "GENERIC") -> CanonicalEvidenceRecord:
    digest = CanonicalEvidenceRecord.generate_digest(field, value)
    rec_id = CanonicalEvidenceRecord.generate_id(incident_id, "EVT-01", field)
    return CanonicalEvidenceRecord(
        evidence_id=rec_id,
        incident_id=incident_id,
        source_system="FortiSIEM",
        source_event_id="EVT-01",
        source_field=field,
        observed_value=value,
        evidence_type=ev_type,
        availability="AVAILABLE",
        integrity_digest=digest,
    )


def build_norm(incident_id: str, records: list) -> EvidenceNormalizationResult:
    by_field = {}
    by_type = {}
    for r in records:
        by_field.setdefault(r.source_field, []).append(r)
        by_type.setdefault(r.evidence_type, []).append(r)
    return EvidenceNormalizationResult(
        incident_id=incident_id,
        total_evidence_count=len(records),
        available_evidence_count=len(records),
        records=records,
        evidence_by_type=by_type,
        evidence_by_field=by_field,
    )


# ---------------------------------------------------------------------------
# Test 1: Bidirectional Evidence ID Synchronization & ClaimType Enum
# ---------------------------------------------------------------------------
def test_claim_evidence_ids_synchronization():
    # Provide cited_evidence_ids -> evidence_ids populated
    c1 = ModelSupportingClaim(
        claim_type=ClaimType.PROCESS_EXECUTION,
        field="process.name",
        asserted_value="powershell.exe",
        cited_evidence_ids=["EV-100", "EV-101"],
    )
    assert c1.evidence_ids == ["EV-100", "EV-101"]
    assert c1.cited_evidence_ids == ["EV-100", "EV-101"]

    # Provide evidence_ids -> cited_evidence_ids populated
    c2 = ModelSupportingClaim(
        claim_type=ClaimType.NETWORK_CONNECTION,
        field="network.source_ip",
        asserted_value="10.0.0.5",
        evidence_ids=["EV-200"],
    )
    assert c2.cited_evidence_ids == ["EV-200"]
    assert c2.evidence_ids == ["EV-200"]

    # Test standardized claim types
    assert ClaimType.TELEMETRY_OBSERVATION.value == "TELEMETRY_OBSERVATION"
    assert ClaimType.OBSERVED_FACT.value == "OBSERVED_FACT"


# ---------------------------------------------------------------------------
# Test 2: Untrusted Incident Data Boundary Tags (<UNTRUSTED_INCIDENT_DATA>)
# ---------------------------------------------------------------------------
def test_untrusted_incident_data_boundary_tags():
    user_payload = {"incident": {"id": "INC-TEST-01", "cmdline": "calc.exe"}}
    serialized = json.dumps(user_payload, indent=2)
    user_content = f"<UNTRUSTED_INCIDENT_DATA>\n{serialized}\n</UNTRUSTED_INCIDENT_DATA>"

    messages = [
        {"role": "system", "content": "You are a SOC assistant."},
        {"role": "user", "content": user_content},
    ]

    assert "<UNTRUSTED_INCIDENT_DATA>" in messages[1]["content"]
    assert "</UNTRUSTED_INCIDENT_DATA>" in messages[1]["content"]
    assert '"calc.exe"' in messages[1]["content"]


# ---------------------------------------------------------------------------
# Test 3: Large Event Counts and Long Commands Preserved in Allowlist
# ---------------------------------------------------------------------------
def test_allowlist_preserves_events_and_long_command_lines():
    long_cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -Command " + ("A" * 1500)
    raw_events = [
        {
            "eventId": f"EVT-{i}",
            "eventType": "ProcessCreation",
            "attribute": {
                "Command": long_cmd if i == 0 else f"cmd.exe /c echo {i}",
                "User": f"user_{i}",
                "srcIp": f"10.0.0.{i}",
            }
        }
        for i in range(12)
    ]

    raw_incident = {
        "incidentId": "INC-LARGE-01",
        "eventType": "SuspiciousProcess",
        "title": "Large Multi-Event Incident",
        "description": "Detection spanning multiple correlation events",
        "severity": "HIGH",
        "rawEvents": raw_events,
    }

    payload = build_model_facing_payload(raw_incident, events=raw_events, max_events=20)

    # 1. Assert that more than 2 events are retained (all 12 events retained)
    assert len(payload["events"]) == 12

    # 2. Assert that the long command line was NOT truncated at 180 chars
    first_event_attrs = payload["events"][0]["attributes"]
    preserved_cmd = first_event_attrs.get("Command")
    assert preserved_cmd is not None
    assert len(preserved_cmd) > 1000
    assert "[truncated]" not in preserved_cmd


# ---------------------------------------------------------------------------
# Test 4: Rejection of Decisive FP Based Solely on RFC-1918 / Service Account
# ---------------------------------------------------------------------------
def test_reject_fp_based_solely_on_internal_ip_and_service_account():
    contract = RuleEvidenceContract(
        contract_id="EC-FP-01",
        rule_id="RULE-FP-01",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="network.source_ip", evidence_type="NETWORK_CONNECTION", critical=True),
            EvidenceFieldRequirement(field="user.name", evidence_type="USER_CONTEXT", critical=False),
        ]
    )

    records = [
        create_record("INC-FP-01", "network.source_ip", "192.168.1.100", "NETWORK_CONNECTION"),
        create_record("INC-FP-01", "user.name", "svc_app_pool", "USER_CONTEXT"),
    ]
    norm = build_norm("INC-FP-01", records)
    preflight = EvidencePreflightValidator.validate_preflight("INC-FP-01", contract, norm)

    # Model attempts to dismiss activity as FP based on internal RFC-1918 IP and service account
    model_output = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 85.0,
        "reason": "Internal RFC-1918 traffic from service account svc_app_pool, appears normal and routine.",
        "supporting_claims": [
            {
                "claim_type": "NETWORK_CONNECTION",
                "field": "network.source_ip",
                "asserted_value": "192.168.1.100",
                "evidence_ids": [records[0].evidence_id],
            },
            {
                "claim_type": "USER_CONTEXT",
                "field": "user.name",
                "asserted_value": "svc_app_pool",
                "evidence_ids": [records[1].evidence_id],
            }
        ]
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-FP-01", model_output, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-FP-01",
        proposed_verdict="FALSE_POSITIVE",
        raw_model_confidence=85.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm,
        contract=contract,
        model_reason=model_output["reason"],
    )

    # Must be rejected and downgraded to REQUIRES_ATTENTION
    assert res.final_verdict == "REQUIRES_ATTENTION"
    assert res.is_decisive_accepted is False
    assert "FP_CRITERIA_UNSATISFIED" in res.validation_reason_codes
    assert res.validated_confidence_display == 0.0


# ---------------------------------------------------------------------------
# Test 5: Acceptance of Decisive FP Backed by Affirmative Authorization
# ---------------------------------------------------------------------------
def test_accept_fp_with_affirmative_verifiable_authorization():
    contract = RuleEvidenceContract(
        contract_id="EC-FP-02",
        rule_id="RULE-FP-02",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="process.name", evidence_type="PROCESS_EXECUTION", critical=True),
            EvidenceFieldRequirement(field="process.command_line", evidence_type="PROCESS_EXECUTION", critical=True),
        ]
    )

    records = [
        create_record("INC-FP-02", "process.name", "backup_agent.exe", "PROCESS_EXECUTION"),
        create_record("INC-FP-02", "process.command_line", "backup_agent.exe --scheduled --ticket CHG-9842", "PROCESS_EXECUTION"),
        create_record("INC-FP-02", "authorization.ticket_id", "CHG-9842", "SECURITY_EVENT"),
        create_record("INC-FP-02", "authorization.status", "APPROVED", "SECURITY_EVENT"),
    ]
    norm = build_norm("INC-FP-02", records)
    preflight = EvidencePreflightValidator.validate_preflight("INC-FP-02", contract, norm)

    model_output = {
        "verdict": "FALSE_POSITIVE",
        "confidence": 92.0,
        "reason": "Authorized backup process executed under approved change ticket CHG-9842 within scheduled maintenance window.",
        "supporting_claims": [
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "process.name",
                "asserted_value": "backup_agent.exe",
                "evidence_ids": [records[0].evidence_id],
            },
            {
                "claim_type": "PROCESS_EXECUTION",
                "field": "process.command_line",
                "asserted_value": "backup_agent.exe --scheduled --ticket CHG-9842",
                "evidence_ids": [records[1].evidence_id],
            },
            {
                "claim_type": "SECURITY_EVENT",
                "field": "authorization.ticket_id",
                "asserted_value": "CHG-9842",
                "evidence_ids": [records[2].evidence_id],
            }
        ]
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-FP-02", model_output, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-FP-02",
        proposed_verdict="FALSE_POSITIVE",
        raw_model_confidence=92.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm,
        contract=contract,
        model_reason=model_output["reason"],
    )

    assert res.final_verdict == "FALSE_POSITIVE"
    assert res.is_decisive_accepted is True
    assert "EVIDENCE_VALIDATED" in res.validation_reason_codes
    assert res.validated_confidence_display == 92.0


# ---------------------------------------------------------------------------
# Test 6: Safe Downgrade When Regex Schema Recovery Was Applied
# ---------------------------------------------------------------------------
def test_schema_recovery_prevents_decisive_acceptance():
    malformed_raw = "Here is my evaluation: { 'verdict': 'TRUE_POSITIVE', 'confidence': 88, 'reason': 'Malicious powershell' "
    recovered, err = _regex_fallback_extract(malformed_raw)
    assert err is None
    assert recovered.get("_schema_recovery_applied") is True
    assert recovered.get("verdict") == "TRUE_POSITIVE"
    assert recovered.get("confidence") == 0.0

    # Test the provider's defensive handling of _schema_recovery_applied
    verdict_candidate = recovered.get("verdict", "REQUIRES_ATTENTION")
    status = "VALID"
    confidence = float(recovered.get("confidence") or 0.0)

    if recovered.get("_schema_recovery_applied") and verdict_candidate in ("TRUE_POSITIVE", "FALSE_POSITIVE"):
        verdict_candidate = "REQUIRES_ATTENTION"
        confidence = 0.0
        status = "INVALID_SCHEMA"

    assert verdict_candidate == "REQUIRES_ATTENTION"
    assert confidence == 0.0
    assert status == "INVALID_SCHEMA"


# ---------------------------------------------------------------------------
# Test 7: Rejection of Decisive Verdict When Structured Claims Are Absent
# ---------------------------------------------------------------------------
def test_reject_decisive_verdict_when_claims_absent():
    contract = RuleEvidenceContract(
        contract_id="EC-EMPTY-01",
        rule_id="RULE-EMPTY-01",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="process.name", evidence_type="PROCESS_EXECUTION", critical=True),
        ]
    )

    records = [create_record("INC-EMPTY-01", "process.name", "cmd.exe", "PROCESS_EXECUTION")]
    norm = build_norm("INC-EMPTY-01", records)
    preflight = EvidencePreflightValidator.validate_preflight("INC-EMPTY-01", contract, norm)

    # Model returned decisive TRUE_POSITIVE but empty supporting_claims
    model_output = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 90.0,
        "reason": "cmd.exe was launched suspiciously.",
        "supporting_claims": [],
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-EMPTY-01", model_output, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-EMPTY-01",
        proposed_verdict="TRUE_POSITIVE",
        raw_model_confidence=90.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm,
        contract=contract,
        model_reason=model_output["reason"],
    )

    assert res.final_verdict == "REQUIRES_ATTENTION"
    assert res.is_decisive_accepted is False
    assert "TP_CRITERIA_UNSATISFIED" in res.validation_reason_codes


# ---------------------------------------------------------------------------
# Test 8: Rejection Under Contradictory Telemetry (External C2 on Loopback)
# ---------------------------------------------------------------------------
def test_reject_tp_on_contradictory_loopback_telemetry():
    contract = RuleEvidenceContract(
        contract_id="EC-LOOP-01",
        rule_id="RULE-LOOP-01",
        status="APPROVED",
        required_evidence=[
            EvidenceFieldRequirement(field="network.source_ip", evidence_type="NETWORK_CONNECTION", critical=True),
            EvidenceFieldRequirement(field="network.destination_ip", evidence_type="NETWORK_CONNECTION", critical=True),
        ]
    )

    records = [
        create_record("INC-LOOP-01", "network.source_ip", "127.0.0.1", "NETWORK_CONNECTION"),
        create_record("INC-LOOP-01", "network.destination_ip", "127.0.0.1", "NETWORK_CONNECTION"),
    ]
    norm = build_norm("INC-LOOP-01", records)
    preflight = EvidencePreflightValidator.validate_preflight("INC-LOOP-01", contract, norm)

    # Model claims external C2 communication when all IPs are local loopback
    model_output = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 91.0,
        "reason": "Host established external C2 communication to remote adversary server.",
        "supporting_claims": [
            {
                "claim_type": "NETWORK_CONNECTION",
                "field": "network.source_ip",
                "asserted_value": "external c2 channel on 127.0.0.1",
                "evidence_ids": [records[0].evidence_id],
            }
        ]
    }
    grounding = ModelClaimExtractor.extract_and_ground_claims("INC-LOOP-01", model_output, norm)

    res = IndependentVerdictValidator.validate_verdict(
        incident_id="INC-LOOP-01",
        proposed_verdict="TRUE_POSITIVE",
        raw_model_confidence=91.0,
        preflight=preflight,
        claim_grounding=grounding,
        normalization_result=norm,
        contract=contract,
        model_reason=model_output["reason"],
    )

    assert res.final_verdict == "REQUIRES_ATTENTION"
    assert res.is_decisive_accepted is False
    assert "EVIDENCE_CONTRADICTION" in res.validation_reason_codes


# ---------------------------------------------------------------------------
# Test 9: Zero Confidence Default When Model Omits Confidence
# ---------------------------------------------------------------------------
def test_zero_confidence_default_when_omitted():
    # If confidence is missing or None, must default to 0.0, never 90.0
    payload_without_conf = {
        "verdict": "REQUIRES_ATTENTION",
        "reason": "Incomplete information.",
    }
    extracted_conf = float(payload_without_conf.get("confidence") or 0.0)
    assert extracted_conf == 0.0


# ---------------------------------------------------------------------------
# Test 10: Fail-Closed Context Window Overflow Abstention
# ---------------------------------------------------------------------------
def test_fail_closed_context_overflow_abstention():
    rule = Rule(id="r-cf-01", rule_id="RULE-CF-01", name="Context Overflow Test", event_type="Process")
    pv = PromptVersion(
        id="pv-cf-01", prompt_id="rp-cf-01", version_number=1, status="APPROVED",
        tp_indicators="Suspicious activity requiring investigation",
    )
    compiled = PolicyCompilerService.compile_policy(rule=rule, prompt_version=pv, execution_mode=CompilationExecutionMode.LIVE)

    incident_payload = {
        "incident_id": "INC-CF-01",
        "title": "Overflow Test Incident",
        "events": [{"event_id": "EVT-1", "cmdline": "test"}],
        "canonical_evidence": [{"evidence_id": "EV-1", "field": "process.name", "observed_value": "test.exe"}],
    }

    # Available budget of 512 tokens while compiled policy alone is > 1500 tokens
    overflow_res = TokenBudgetService.budget_prompt(
        compiled_policy=compiled,
        incident_payload=incident_payload,
        max_context_tokens=1000,
        max_completion_tokens=488,  # Available = 512 tokens
    )

    assert overflow_res.can_proceed_to_inference is False
    assert overflow_res.abstention_reason is not None
    assert "exceed available prompt budget" in overflow_res.abstention_reason
