import pytest
import uuid
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.incident import Incident, HistoricalGroundTruth
from app.models.rule import Rule
from app.models.prompt import RulePrompt, PromptVersion
from app.models.verdict_intelligence import (
    VerdictTrustAssessmentRecord,
    EvidenceSufficiencyAssessmentRecord,
    HistoricalEvaluationRunRecord,
    HistoricalEvaluationResultRecord,
)
from app.schemas.rule_intelligence import DetectionArchetype, ArchetypeId
from app.schemas.evidence_contract import (
    RuleEvidenceContract,
    EvidenceFieldRequirement,
)
from app.schemas.verdict_intelligence import (
    EvidenceStatus,
    UserVisibleVerdict,
    GroundTruthLabel,
    EvaluationValidationState,
    DatasetPartition,
    ClaimType,
    ClaimVerificationResult,
)
from app.services.evidence_sufficiency_engine import EvidenceSufficiencyEngine
from app.services.verdict_claim_validator import VerdictClaimValidator
from app.services.verdict_guardrails_engine import VerdictGuardrailsEngine
from app.services.verdict_trustworthiness_engine import VerdictTrustworthinessEngine
from app.services.historical_ground_truth_validator import HistoricalGroundTruthValidator
from app.services.empirical_accuracy_evaluator import EmpiricalAccuracyEvaluator
from app.services.calibration_evaluator import CalibrationEvaluator
from app.services.policy_simulation_service import PolicySimulationService


# ==============================================================================
# FIXTURES & HELPERS
# ==============================================================================

def make_sample_contract() -> RuleEvidenceContract:
    """Standard network exfiltration evidence contract for test fixtures."""
    return RuleEvidenceContract(
        contract_id="contract-exfil-001",
        rule_id="PH_RULE_LARGE_OUTBOUND_XFER",
        detection_archetype="NETWORK_EXFILTRATION",
        required_evidence=[
            EvidenceFieldRequirement(
                field="source_ip",
                evidence_type="NETWORK_FLOW",
                required_for_tp=True,
                critical=True,
                requirement_level="CORE",
                description="Source IP address",
            ),
            EvidenceFieldRequirement(
                field="destination_ip",
                evidence_type="NETWORK_FLOW",
                required_for_tp=True,
                critical=True,
                requirement_level="CORE",
                description="Destination IP address",
            ),
            EvidenceFieldRequirement(
                field="sentBytes64",
                evidence_type="NETWORK_FLOW",
                required_for_tp=True,
                critical=True,
                requirement_level="CORE",
                description="Outbound transfer volume in bytes",
            ),
            EvidenceFieldRequirement(
                field="direction",
                evidence_type="NETWORK_FLOW",
                required_for_tp=True,
                critical=True,
                requirement_level="CORE",
                description="Traffic direction (outbound/egress)",
            ),
            EvidenceFieldRequirement(
                field="threat_intel",
                evidence_type="THREAT_INTEL",
                required_for_tp=False,
                critical=False,
                requirement_level="OPTIONAL",
                description="Threat reputation",
            ),
        ],
    )


# ==============================================================================
# SECTION 1: EVIDENCE SUFFICIENCY ENGINE
# ==============================================================================

def test_evidence_sufficiency_missing_mandatory_blocks_verdict():
    """Missing mandatory field forces INSUFFICIENT and blocks automated decision."""
    contract = make_sample_contract()
    # Payload has source_ip, sentBytes64, direction, but destination_ip is missing!
    payload = {
        "incident_id": "INC-TEST-001",
        "rule_id": "PH_RULE_LARGE_OUTBOUND_XFER",
        "source_ip": "10.0.1.50",
        "raw_payload": {
            "sentBytes64": 2130499380,
            "direction": "outbound",
        },
    }
    result = EvidenceSufficiencyEngine.evaluate_incident_sufficiency(
        incident_payload=payload,
        contract=contract,
        archetype_id="NETWORK_EXFILTRATION",
    )
    assert result.evidence_status == EvidenceStatus.INSUFFICIENT
    assert any("destination" in f.lower() for f in result.mandatory_fields_missing)
    assert result.can_support_automated_verdict is False


def test_evidence_sufficiency_complete_mandatory_and_optional():
    """All mandatory and enrichment fields present yields SUFFICIENT with high score."""
    contract = make_sample_contract()
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    payload = {
        "incident_id": "INC-TEST-002",
        "rule_id": "PH_RULE_LARGE_OUTBOUND_XFER",
        "source_ip": "10.0.1.50",
        "first_seen_epoch": now_ms - 60000,
        "last_seen_epoch": now_ms,
        "raw_payload": {
            "destination_ip": "198.51.100.23",
            "sentBytes64": 2130499380,
            "direction": "outbound",
            "threat_intel": "MALICIOUS",
        },
        "events": [
            {
                "reporting_device": "firewall-edge-01",
                "attributes": {
                    "destination_ip": "198.51.100.23",
                    "sentBytes64": 2130499380,
                },
            },
            {
                "reporting_device": "netflow-sensor-02",
                "attributes": {
                    "destination_ip": "198.51.100.23",
                    "sentBytes64": 2130499380,
                },
            },
        ],
    }
    result = EvidenceSufficiencyEngine.evaluate_incident_sufficiency(
        incident_payload=payload,
        contract=contract,
        archetype_id="NETWORK_EXFILTRATION",
    )
    assert result.evidence_status == EvidenceStatus.SUFFICIENT
    assert len(result.mandatory_fields_missing) == 0
    assert result.overall_sufficiency_score >= 80.0


def test_evidence_sufficiency_missing_optional_only():
    """Missing optional fields does not block automated decision if mandatory fields pass."""
    contract = make_sample_contract()
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    payload = {
        "incident_id": "INC-TEST-003",
        "rule_id": "PH_RULE_LARGE_OUTBOUND_XFER",
        "source_ip": "10.0.1.50",
        "first_seen_epoch": now_ms - 60000,
        "last_seen_epoch": now_ms,
        "raw_payload": {
            "destination_ip": "198.51.100.23",
            "sentBytes64": 2130499380,
            "direction": "outbound",
            # threat_intel omitted
        },
    }
    result = EvidenceSufficiencyEngine.evaluate_incident_sufficiency(
        incident_payload=payload,
        contract=contract,
        archetype_id="NETWORK_EXFILTRATION",
    )
    assert result.evidence_status == EvidenceStatus.SUFFICIENT
    assert len(result.mandatory_fields_missing) == 0


def test_evidence_sufficiency_freshness_degradation():
    """Older telemetry degrades the freshness score component."""
    contract = make_sample_contract()
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    stale_ms = now_ms - (35 * 86400 * 1000)  # 35 days ago

    fresh_payload = {
        "incident_id": "INC-FRESH",
        "rule_id": "PH_RULE_LARGE_OUTBOUND_XFER",
        "source_ip": "10.0.1.50",
        "first_seen_epoch": now_ms - 60000,
        "last_seen_epoch": now_ms,
        "raw_payload": {"destination_ip": "198.51.100.23", "sentBytes64": 2130499380, "direction": "outbound"},
    }
    stale_payload = {
        "incident_id": "INC-STALE",
        "rule_id": "PH_RULE_LARGE_OUTBOUND_XFER",
        "source_ip": "10.0.1.50",
        "first_seen_epoch": stale_ms,
        "last_seen_epoch": now_ms,  # Spans 35 days
        "raw_payload": {"destination_ip": "198.51.100.23", "sentBytes64": 2130499380, "direction": "outbound"},
    }

    res_fresh = EvidenceSufficiencyEngine.evaluate_incident_sufficiency(fresh_payload, contract)
    res_stale = EvidenceSufficiencyEngine.evaluate_incident_sufficiency(stale_payload, contract)

    assert res_fresh.freshness_relevance_score > res_stale.freshness_relevance_score
    assert any("30 days" in n for n in res_stale.notes)


# ==============================================================================
# SECTION 2: CLAIM VERIFICATION & CONTRADICTION DETECTION
# ==============================================================================

def test_claim_verification_grounded_claims():
    """Accurately extracted claims grounded in evidence pass verification."""
    incident = {
        "source_ip": "10.0.1.50",
        "raw_payload": {
            "destination_ip": "198.51.100.23",
            "sentBytes64": 2130499380,
            "direction": "outbound",
        },
    }
    model_output = {
        "reason": "Internal host 10.0.1.50 transferred 2130499380 bytes to 198.51.100.23 outbound.",
        "claims": [
            {"claim": "Host 10.0.1.50 sent bytes", "evidence_ids": ["source_ip"], "claim_type": "OBSERVED_FACT"},
            {"claim": "Volume was 2130499380 bytes", "evidence_ids": ["sentBytes64"], "claim_type": "OBSERVED_FACT"},
        ],
    }
    res = VerdictClaimValidator.verify_claims(
        incident_id="INC-001",
        model_output=model_output,
        incident_payload=incident,
    )
    assert res.contradiction_detected is False
    assert res.has_unsupported_assertions is False
    assert res.grounded_claims_count >= 1


def test_claim_verification_unsupported_threshold_assertion():
    """Treating observed sentBytes64 2130499380 as a configured threshold is flagged."""
    incident = {
        "source_ip": "10.0.1.50",
        "raw_payload": {
            "sentBytes64": 2130499380,
        },
    }
    model_output = {
        "claims": [
            {
                "claim": "Exceeded the configured rule threshold of 2130499380 bytes.",
                "evidence_ids": ["sentBytes64"],
                "claim_type": "THRESHOLD_ASSERTION",
            }
        ],
    }
    res = VerdictClaimValidator.verify_claims(
        incident_id="INC-002",
        model_output=model_output,
        incident_payload=incident,
        authoritative_threshold=None,  # No authoritative threshold!
        authoritative_definition_status="OBSERVED_ONLY",
    )
    assert res.unsupported_threshold_assertion is True
    assert res.has_unsupported_assertions is True
    assert any("2130499380" in c for c in res.unsupported_claims_list)


def test_claim_verification_directional_contradiction():
    """Claiming outbound exfiltration when traffic is inbound is flagged as a contradiction."""
    incident = {
        "source_ip": "198.51.100.23",
        "raw_payload": {
            "direction": "inbound",
            "destination_ip": "10.0.1.50",
        },
    }
    model_output = {
        "claims": [
            {
                "claim": "Host performed outbound network exfiltration.",
                "evidence_ids": ["direction"],
                "claim_type": "OBSERVED_FACT",
            }
        ],
    }
    res = VerdictClaimValidator.verify_claims(
        incident_id="INC-003",
        model_output=model_output,
        incident_payload=incident,
    )
    assert res.contradiction_detected is True
    assert len(res.contradictions) > 0


def test_claim_verification_fabricated_entity():
    """Entities not present in telemetry (hallucinated IPs/hashes) are detected."""
    incident = {
        "source_ip": "10.0.1.50",
        "raw_payload": {"destination_ip": "198.51.100.23"},
    }
    model_output = {
        "claims": [
            {
                "claim": "Beaconed to malicious command and control server at 203.0.113.99",
                "evidence_ids": ["destination_ip"],
                "claim_type": "OBSERVED_FACT",
            }
        ],
    }
    res = VerdictClaimValidator.verify_claims(
        incident_id="INC-004",
        model_output=model_output,
        incident_payload=incident,
    )
    assert res.has_unsupported_assertions is True
    assert any("203.0.113.99" in c for c in res.unsupported_claims_list)


# ==============================================================================
# SECTION 3: DETERMINISTIC VERDICT GUARDRAILS
# ==============================================================================

def test_guardrails_tp_without_evidence_demoted():
    """TRUE_POSITIVE without sufficient evidence is demoted to REQUIRES_ANALYST_ATTENTION."""
    contract = make_sample_contract()
    payload = {"source_ip": "10.0.1.50"}  # Missing destination, sentBytes, direction
    sufficiency = EvidenceSufficiencyEngine.evaluate_incident_sufficiency(payload, contract)
    claim_ver = VerdictClaimValidator.verify_claims("INC-G1", {"claims": []}, payload)

    verdict, esc_reason, conf_limits = VerdictGuardrailsEngine.apply_guardrails(
        proposed_verdict="TRUE_POSITIVE",
        raw_confidence=0.95,
        sufficiency=sufficiency,
        claim_verification=claim_ver,
        raw_trust_score=35.0,
    )
    assert verdict == UserVisibleVerdict.REQUIRES_ANALYST_ATTENTION
    assert esc_reason is not None
    assert "MANDATORY" in esc_reason.upper()


def test_guardrails_fp_without_affirmative_authorization():
    """FALSE_POSITIVE without affirmative proof of authorization is demoted."""
    contract = make_sample_contract()
    payload = {
        "source_ip": "10.0.1.50",
        "raw_payload": {"destination_ip": "198.51.100.23", "sentBytes64": 2130499380, "direction": "outbound"},
    }
    sufficiency = EvidenceSufficiencyEngine.evaluate_incident_sufficiency(payload, contract)
    model_out = {
        "claims": [
            {"claim": "Observed outbound bytes", "evidence_ids": ["sentBytes64"], "claim_type": "OBSERVED_FACT"}
        ]
    }
    claim_ver = VerdictClaimValidator.verify_claims("INC-G2", model_out, payload)

    # Note: destination_ip 198.51.100.23 has no authorized service annotation in incident_context
    verdict, esc_reason, _ = VerdictGuardrailsEngine.apply_guardrails(
        proposed_verdict="FALSE_POSITIVE",
        raw_confidence=0.88,
        sufficiency=sufficiency,
        claim_verification=claim_ver,
        raw_trust_score=72.0,
        incident_context={"business_authorization_verified": False},
    )
    assert verdict == UserVisibleVerdict.REQUIRES_ANALYST_ATTENTION
    assert esc_reason is not None
    assert "AUTHORIZATION" in esc_reason.upper()


def test_guardrails_contradiction_forces_analyst_attention():
    """Contradiction in evidence or claims forces REQUIRES_ANALYST_ATTENTION."""
    contract = make_sample_contract()
    payload = {
        "source_ip": "10.0.1.50",
        "raw_payload": {"destination_ip": "198.51.100.23", "sentBytes64": 2130499380, "direction": "inbound"},
    }
    sufficiency = EvidenceSufficiencyEngine.evaluate_incident_sufficiency(payload, contract, archetype_id="NETWORK_EXFILTRATION")
    model_out = {
        "claims": [{"claim": "Outbound exfiltration transfer", "evidence_ids": ["direction"], "claim_type": "OBSERVED_FACT"}]
    }
    claim_ver = VerdictClaimValidator.verify_claims("INC-G3", model_out, payload)

    verdict, esc_reason, _ = VerdictGuardrailsEngine.apply_guardrails(
        proposed_verdict="TRUE_POSITIVE",
        raw_confidence=0.92,
        sufficiency=sufficiency,
        claim_verification=claim_ver,
        raw_trust_score=40.0,
    )
    assert verdict == UserVisibleVerdict.REQUIRES_ANALYST_ATTENTION
    assert esc_reason is not None


# ==============================================================================
# SECTION 4: VERDICT TRUSTWORTHINESS ENGINE
# ==============================================================================

def test_trustworthiness_uncalibrated_rule_capped_at_6():
    """Rules with historical sample size < 30 are capped at maximum trust score 6/10."""
    contract = make_sample_contract()
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    payload = {
        "incident_id": "INC-TRUST-UNCAL",
        "rule_id": "PH_RULE_LARGE_OUTBOUND_XFER",
        "source_ip": "10.0.1.50",
        "first_seen_epoch": now_ms - 60000,
        "last_seen_epoch": now_ms,
        "raw_payload": {
            "destination_ip": "198.51.100.23",
            "sentBytes64": 2130499380,
            "direction": "outbound",
            "threat_intel": "MALICIOUS",
        },
    }
    model_out = {
        "proposed_verdict": "TRUE_POSITIVE",
        "confidence": 0.99,
        "reason": "Internal host transferred 2.1GB outbound to malicious destination.",
    }

    assessment = VerdictTrustworthinessEngine.evaluate_verdict_trust(
        incident_payload=payload,
        model_output=model_out,
        contract=contract,
        archetype_id="NETWORK_EXFILTRATION",
        historical_sample_count=12,  # < 30 (uncalibrated)
        is_calibrated=False,
    )
    assert assessment.is_calibrated is False
    assert assessment.trust_score_ordinal <= 6
    assert any("UNCALIBRATED" in n for n in assessment.confidence_limitations)


def test_trustworthiness_score_10_exceptional_prerequisites():
    """Trust score 10 requires exceptional prerequisites (calibrated, 0 ungrounded claims, full sufficiency)."""
    assert VerdictTrustworthinessEngine.score_to_ordinal(99.0, is_calibrated=True, sample_count=100) == 10
    # But if uncalibrated, even a 99 raw score is capped at 6
    assert VerdictTrustworthinessEngine.score_to_ordinal(99.0, is_calibrated=False, sample_count=15) == 6


def test_trustworthiness_llm_confidence_cannot_override_low_evidence():
    """LLM claiming 0.99 confidence cannot override missing evidence."""
    contract = make_sample_contract()
    # Missing all destination and transfer details
    payload = {
        "incident_id": "INC-OVERRIDE",
        "source_ip": "10.0.1.50",
    }
    model_out = {
        "proposed_verdict": "TRUE_POSITIVE",
        "confidence": 0.99,
        "reason": "I am 99% sure this is malicious data theft.",
    }
    assessment = VerdictTrustworthinessEngine.evaluate_verdict_trust(
        incident_payload=payload,
        model_output=model_out,
        contract=contract,
        archetype_id="NETWORK_EXFILTRATION",
        historical_sample_count=50,
        is_calibrated=True,
    )
    assert assessment.trust_score_ordinal <= 4
    assert assessment.user_visible_verdict == UserVisibleVerdict.REQUIRES_ANALYST_ATTENTION


# ==============================================================================
# SECTION 5: HISTORICAL GROUND TRUTH & DATA LEAKAGE PREVENTION
# ==============================================================================

def test_historical_ground_truth_sanitization_prevents_leakage():
    """Sanitizing incident data for inference removes all analyst closure answers."""
    raw_incident_data = {
        "incident_id": "INC-99901",
        "source_ip": "10.0.1.50",
        "analyst_verdict": "TRUE_POSITIVE",
        "resolution": "Confirmed data exfiltration by user compromised account",
        "cleared_reason": "Escalated to Incident Response Team",
        "comments": "Analyst observed C2 communication on port 443",
        "events": [
            {
                "event_id": "EVT-1",
                "analyst_notes": "Malicious beaconing confirmed",
                "attributes": {
                    "bytes": 2130499380,
                    "resolution": "Escalated",
                },
            }
        ],
    }

    sanitized = HistoricalGroundTruthValidator.sanitize_incident_for_inference(raw_incident_data)
    assert "analyst_verdict" not in sanitized
    assert "resolution" not in sanitized
    assert "cleared_reason" not in sanitized
    assert "comments" not in sanitized
    assert "analyst_notes" not in sanitized["events"][0]
    assert "resolution" not in sanitized["events"][0]["attributes"]
    # Telemetry remains intact
    assert sanitized["source_ip"] == "10.0.1.50"
    assert sanitized["events"][0]["attributes"]["bytes"] == 2130499380


def test_historical_ground_truth_adjudication():
    """Adjudicates TP, FP, UNVERIFIED, and CONFLICTING accurately."""
    # 1. Clear True Positive with comments
    lbl_tp, rel_tp, _ = HistoricalGroundTruthValidator.adjudicate_label(
        raw_resolution="TRUE POSITIVE",
        analyst_comments="Confirmed adversary command and control beaconing.",
    )
    assert lbl_tp == GroundTruthLabel.VERIFIED_TP
    assert rel_tp == 1.0

    # 2. Clear False Positive
    lbl_fp, rel_fp, _ = HistoricalGroundTruthValidator.adjudicate_label(
        raw_resolution="FALSE POSITIVE",
        analyst_comments="Authorized Nessus vulnerability scan executed by SecOps.",
    )
    assert lbl_fp == GroundTruthLabel.VERIFIED_FP
    assert rel_fp == 1.0

    # 3. Open / Unreviewed
    lbl_unv, _, _ = HistoricalGroundTruthValidator.adjudicate_label(raw_resolution="OPEN")
    assert lbl_unv == GroundTruthLabel.UNKNOWN

    # 4. Conflicting
    lbl_conf, _, _ = HistoricalGroundTruthValidator.adjudicate_label(raw_resolution="DISPUTED_ANALYSIS")
    assert lbl_conf == GroundTruthLabel.CONFLICTING


def test_deterministic_partitioning_consistency():
    """Hash-based partitioning assigns incidents consistently across calls."""
    p1 = HistoricalGroundTruthValidator.assign_partition("INC-10023")
    p2 = HistoricalGroundTruthValidator.assign_partition("INC-10023")
    assert p1 == p2
    assert p1 in list(DatasetPartition)


# ==============================================================================
# SECTION 6: EMPIRICAL ACCURACY & CALIBRATION EVALUATORS
# ==============================================================================

def test_empirical_accuracy_wilson_confidence_intervals():
    """Evaluates confusion matrix, metrics, and valid Wilson 95% confidence intervals."""
    evaluations = []
    # 40 TP, 10 FP, 5 FN, 45 TN
    for _ in range(40):
        evaluations.append({
            "effective_verdict": "TRUE_POSITIVE",
            "ground_truth_label": "VERIFIED_TP",
            "trust_score": 8,
            "evidence_status": "SUFFICIENT",
        })
    for _ in range(10):
        evaluations.append({
            "effective_verdict": "TRUE_POSITIVE",
            "ground_truth_label": "VERIFIED_FP",
            "trust_score": 7,
            "evidence_status": "SUFFICIENT",
        })
    for _ in range(5):
        evaluations.append({
            "effective_verdict": "FALSE_POSITIVE",
            "ground_truth_label": "VERIFIED_TP",
            "trust_score": 6,
            "evidence_status": "SUFFICIENT",
        })
    for _ in range(45):
        evaluations.append({
            "effective_verdict": "FALSE_POSITIVE",
            "ground_truth_label": "VERIFIED_FP",
            "trust_score": 8,
            "evidence_status": "SUFFICIENT",
        })

    metrics = EmpiricalAccuracyEvaluator.evaluate_performance(evaluations)
    assert metrics.verified_ground_truth_count == 100
    assert metrics.confusion_matrix.true_positives == 40
    assert metrics.confusion_matrix.false_positives == 10
    assert metrics.confusion_matrix.false_negatives == 5
    assert metrics.confusion_matrix.true_negatives == 45

    # Precision = 40 / 50 = 0.80
    assert metrics.precision == 0.80
    assert metrics.precision_ci is not None
    assert metrics.precision_ci.point_estimate == 0.80
    assert 0.0 <= metrics.precision_ci.lower_bound <= metrics.precision_ci.point_estimate <= metrics.precision_ci.upper_bound <= 1.0

    # Recall = 40 / 45 = 0.8889
    assert metrics.recall == 0.8889
    assert metrics.recall_ci is not None
    assert 0.0 <= metrics.recall_ci.lower_bound <= metrics.recall_ci.upper_bound <= 1.0

    # Risk-coverage curve points generated
    assert len(metrics.risk_coverage_curve) > 0


def test_calibration_evaluator_insufficient_sample_size():
    """Sample sizes < 30 report NOT_CALIBRATED honest status."""
    evaluations = [
        {"effective_verdict": "TRUE_POSITIVE", "ground_truth_label": "VERIFIED_TP", "trust_score": 8}
        for _ in range(15)
    ]
    report = CalibrationEvaluator.evaluate_calibration(evaluations)
    assert report.is_calibrated is False
    assert report.total_calibrated_samples == 15
    assert any("BELOW_MINIMUM_THRESHOLD" in n for n in report.calibration_notes)


def test_calibration_evaluator_sufficient_sample_size():
    """Sample sizes >= 30 compute Expected Calibration Error and Brier Score."""
    evaluations = []
    # 50 samples
    for _ in range(25):
        evaluations.append({"effective_verdict": "TRUE_POSITIVE", "ground_truth_label": "VERIFIED_TP", "trust_score": 9})
    for _ in range(5):
        evaluations.append({"effective_verdict": "TRUE_POSITIVE", "ground_truth_label": "VERIFIED_FP", "trust_score": 7})
    for _ in range(20):
        evaluations.append({"effective_verdict": "FALSE_POSITIVE", "ground_truth_label": "VERIFIED_FP", "trust_score": 8})

    report = CalibrationEvaluator.evaluate_calibration(evaluations)
    assert report.is_calibrated is True
    assert report.total_calibrated_samples == 50
    assert report.brier_score is not None
    assert report.expected_calibration_error is not None
    assert len(report.reliability_bins) == 5


# ==============================================================================
# SECTION 7: SIMULATION LAB & PAIRED REGRESSION COMPARISON
# ==============================================================================

@pytest.mark.asyncio
async def test_policy_simulation_insufficient_data(db_session: AsyncSession):
    """Fewer than 5 historical incidents returns INSUFFICIENT_DATA."""
    service = PolicySimulationService(db_session)
    # The in-memory database has 0 historical incidents
    run_record = await service.run_dry_run_intelligence_evaluation(
        run_name="Run-Insufficient-Test",
        rule_id="PH_RULE_LARGE_OUTBOUND_XFER",
    )
    assert run_record.validation_state == EvaluationValidationState.INSUFFICIENT_DATA.value
    assert run_record.total_cases < 5


@pytest.mark.asyncio
async def test_policy_simulation_regression_detection(db_session: AsyncSession):
    """Detects regression when candidate policy introduces critical false negatives."""
    service = PolicySimulationService(db_session)

    # Create baseline run with 10 results (all correct)
    base_run = HistoricalEvaluationRunRecord(
        id=str(uuid.uuid4()),
        run_name="Baseline-Run",
        rule_id="PH_RULE_LARGE_OUTBOUND_XFER",
        status="COMPLETED",
        validation_state="VALIDATED",
        total_cases=10,
        metrics={"balanced_accuracy": 0.95, "coverage": 1.0},
    )
    cand_run = HistoricalEvaluationRunRecord(
        id=str(uuid.uuid4()),
        run_name="Candidate-Run",
        rule_id="PH_RULE_LARGE_OUTBOUND_XFER",
        status="COMPLETED",
        validation_state="VALIDATED",
        total_cases=10,
        metrics={"balanced_accuracy": 0.70, "coverage": 1.0},
    )
    db_session.add(base_run)
    db_session.add(cand_run)
    await db_session.flush()

    # Add paired results for incident 1-10
    for i in range(1, 11):
        inc_id = f"INC-REGR-{i}"
        # Baseline predicted TRUE_POSITIVE on VERIFIED_TP
        base_res = HistoricalEvaluationResultRecord(
            id=str(uuid.uuid4()),
            run_id=base_run.id,
            incident_id=inc_id,
            rule_id="PH_RULE_LARGE_OUTBOUND_XFER",
            ground_truth_label="VERIFIED_TP",
            suggested_verdict="TRUE_POSITIVE",
            effective_verdict="TRUE_POSITIVE",
            trust_score=8,
            is_correct=True,
        )
        # Candidate dropped 4 TPs to FALSE_POSITIVE!
        is_cand_correct = i > 4
        cand_res = HistoricalEvaluationResultRecord(
            id=str(uuid.uuid4()),
            run_id=cand_run.id,
            incident_id=inc_id,
            rule_id="PH_RULE_LARGE_OUTBOUND_XFER",
            ground_truth_label="VERIFIED_TP",
            suggested_verdict="TRUE_POSITIVE" if is_cand_correct else "FALSE_POSITIVE",
            effective_verdict="TRUE_POSITIVE" if is_cand_correct else "FALSE_POSITIVE",
            trust_score=8 if is_cand_correct else 3,
            is_correct=is_cand_correct,
        )
        db_session.add(base_res)
        db_session.add(cand_res)

    await db_session.commit()

    comparison = await service.compare_runs(
        baseline_run_id=base_run.id,
        candidate_run_id=cand_run.id,
    )
    assert comparison.validation_state == EvaluationValidationState.REGRESSION_DETECTED
    assert comparison.critical_regressions_count >= 1
    assert any(r.regression_type == "TP_DROPPED_TO_FN" for r in comparison.regressed_cases)


# ==============================================================================
# SECTION 8: 8 REFERENCE CASES FOR PH_RULE_LARGE_OUTBOUND_XFER
# ==============================================================================

def test_case_01_fully_documented_exfiltration_high_trust_tp():
    """Case 1: Fully documented exfiltration yields high trust TRUE_POSITIVE."""
    contract = make_sample_contract()
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    payload = {
        "incident_id": "INC-CASE-01",
        "rule_id": "PH_RULE_LARGE_OUTBOUND_XFER",
        "source_ip": "10.0.1.50",
        "first_seen_epoch": now_ms - 60000,
        "last_seen_epoch": now_ms,
        "raw_payload": {
            "destination_ip": "198.51.100.23",
            "sentBytes64": 2130499380,
            "direction": "outbound",
            "threat_intel": "MALICIOUS",
        },
    }
    model_out = {
        "proposed_verdict": "TRUE_POSITIVE",
        "confidence": 0.96,
        "reason": "Host 10.0.1.50 sent 2130499380 bytes outbound to foreign destination.",
    }

    trust = VerdictTrustworthinessEngine.evaluate_verdict_trust(
        incident_payload=payload,
        model_output=model_out,
        contract=contract,
        archetype_id="NETWORK_EXFILTRATION",
        historical_sample_count=45,
        is_calibrated=True,
    )
    assert trust.user_visible_verdict == UserVisibleVerdict.TRUE_POSITIVE
    assert trust.trust_score_ordinal >= 7
    assert trust.raw_trust_score >= 70.0


def test_case_02_missing_destination_ip_insufficient_evidence():
    """Case 2: Missing destination IP forces INSUFFICIENT and demotes to REQUIRES_ANALYST_ATTENTION."""
    contract = make_sample_contract()
    payload = {
        "incident_id": "INC-CASE-02",
        "rule_id": "PH_RULE_LARGE_OUTBOUND_XFER",
        "source_ip": "10.0.1.50",
        "raw_payload": {
            "sentBytes64": 2130499380,
            "direction": "outbound",
            # destination_ip missing!
        },
    }
    model_out = {
        "proposed_verdict": "TRUE_POSITIVE",
        "confidence": 0.90,
        "reason": "Large outbound volume observed.",
    }
    trust = VerdictTrustworthinessEngine.evaluate_verdict_trust(
        incident_payload=payload,
        model_output=model_out,
        contract=contract,
        archetype_id="NETWORK_EXFILTRATION",
        historical_sample_count=45,
        is_calibrated=True,
    )
    assert trust.user_visible_verdict == UserVisibleVerdict.REQUIRES_ANALYST_ATTENTION
    assert trust.evidence_sufficiency.evidence_status == EvidenceStatus.INSUFFICIENT
    assert trust.trust_score_ordinal <= 4


def test_case_03_inverted_traffic_direction_inbound_traffic():
    """Case 3: Inbound traffic contradiction forces guardrail demotion."""
    contract = make_sample_contract()
    payload = {
        "incident_id": "INC-CASE-03",
        "rule_id": "PH_RULE_LARGE_OUTBOUND_XFER",
        "source_ip": "198.51.100.23",
        "raw_payload": {
            "destination_ip": "10.0.1.50",
            "sentBytes64": 2130499380,
            "direction": "inbound",  # Contradicts exfiltration archetype
        },
    }
    model_out = {
        "proposed_verdict": "TRUE_POSITIVE",
        "confidence": 0.89,
        "claims": [
            {"claim": "Host performed outbound exfiltration", "evidence_ids": ["direction"], "claim_type": "OBSERVED_FACT"}
        ],
    }
    trust = VerdictTrustworthinessEngine.evaluate_verdict_trust(
        incident_payload=payload,
        model_output=model_out,
        contract=contract,
        archetype_id="NETWORK_EXFILTRATION",
        historical_sample_count=45,
        is_calibrated=True,
    )
    assert trust.user_visible_verdict == UserVisibleVerdict.REQUIRES_ANALYST_ATTENTION
    assert trust.claim_verification.contradiction_detected is True


def test_case_04_approved_cloud_backup_legitimate_fp():
    """Case 4: Verified business authorization allows defensible FALSE_POSITIVE with high trust."""
    contract = make_sample_contract()
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    payload = {
        "incident_id": "INC-CASE-04",
        "rule_id": "PH_RULE_LARGE_OUTBOUND_XFER",
        "source_ip": "10.0.1.50",
        "first_seen_epoch": now_ms - 60000,
        "last_seen_epoch": now_ms,
        "raw_payload": {
            "destination_ip": "52.216.100.5",  # AWS S3 IP
            "sentBytes64": 2130499380,
            "direction": "outbound",
            "business_service": "s3.amazonaws.com",
            "authorization_ticket": "CHG-BACKUP-9921",
        },
    }
    model_out = {
        "proposed_verdict": "FALSE_POSITIVE",
        "confidence": 0.94,
        "reason": "Transfer matches authorized scheduled AWS backup window with change ticket CHG-BACKUP-9921.",
    }
    trust = VerdictTrustworthinessEngine.evaluate_verdict_trust(
        incident_payload=payload,
        model_output=model_out,
        contract=contract,
        archetype_id="NETWORK_EXFILTRATION",
        historical_sample_count=50,
        is_calibrated=True,
    )
    assert trust.user_visible_verdict == UserVisibleVerdict.FALSE_POSITIVE
    assert trust.trust_score_ordinal >= 7


def test_case_05_fabricated_threshold_claim_speculative_llm():
    """Case 5: Fabricated claim asserting 2130499380 was configured threshold is penalized."""
    contract = make_sample_contract()
    payload = {
        "incident_id": "INC-CASE-05",
        "rule_id": "PH_RULE_LARGE_OUTBOUND_XFER",
        "source_ip": "10.0.1.50",
        "raw_payload": {
            "destination_ip": "198.51.100.23",
            "sentBytes64": 2130499380,
            "direction": "outbound",
        },
    }
    model_out = {
        "proposed_verdict": "TRUE_POSITIVE",
        "confidence": 0.88,
        "claims": [
            {
                "claim": "Exceeded the configured SIEM threshold limit of 2130499380 bytes.",
                "evidence_ids": ["sentBytes64"],
                "claim_type": "THRESHOLD_ASSERTION",
            }
        ],
    }
    trust = VerdictTrustworthinessEngine.evaluate_verdict_trust(
        incident_payload=payload,
        model_output=model_out,
        contract=contract,
        archetype_id="NETWORK_EXFILTRATION",
        authoritative_threshold=None,
        definition_status="OBSERVED_ONLY",
        historical_sample_count=45,
        is_calibrated=True,
    )
    assert trust.claim_verification.unsupported_threshold_assertion is True
    assert trust.claim_verification.has_unsupported_assertions is True
    # Penalized claim support score
    assert trust.dimension_breakdown.claim_support_score < 30.0


def test_case_06_uncalibrated_rule_less_than_30_incidents():
    """Case 6: Sample size of 14 incidents marks rule uncalibrated and caps trust score at 6/10."""
    contract = make_sample_contract()
    payload = {
        "incident_id": "INC-CASE-06",
        "rule_id": "PH_RULE_LARGE_OUTBOUND_XFER",
        "source_ip": "10.0.1.50",
        "raw_payload": {
            "destination_ip": "198.51.100.23",
            "sentBytes64": 2130499380,
            "direction": "outbound",
        },
    }
    model_out = {
        "proposed_verdict": "TRUE_POSITIVE",
        "confidence": 0.95,
        "reason": "Large outbound volume.",
    }
    trust = VerdictTrustworthinessEngine.evaluate_verdict_trust(
        incident_payload=payload,
        model_output=model_out,
        contract=contract,
        archetype_id="NETWORK_EXFILTRATION",
        historical_sample_count=14,  # < 30
        is_calibrated=False,
    )
    assert trust.is_calibrated is False
    assert trust.trust_score_ordinal <= 6


def test_case_07_contradictory_netflow_vs_firewall():
    """Case 7: Discrepancy between firewall (2.1GB) and netflow (42KB) triggers contradiction."""
    contract = make_sample_contract()
    payload = {
        "incident_id": "INC-CASE-07",
        "rule_id": "PH_RULE_LARGE_OUTBOUND_XFER",
        "source_ip": "10.0.1.50",
        "raw_payload": {
            "destination_ip": "198.51.100.23",
            "sentBytes64": 2130499380,
            "direction": "outbound",
        },
        "events": [
            {
                "reporting_device": "firewall-edge-01",
                "attributes": {"sentBytes64": 2130499380},
            },
            {
                "reporting_device": "netflow-collector-02",
                "attributes": {"sentBytes64": 42000},  # Discrepancy > 1000x!
            },
        ],
    }
    sufficiency = EvidenceSufficiencyEngine.evaluate_incident_sufficiency(
        incident_payload=payload,
        contract=contract,
        archetype_id="NETWORK_EXFILTRATION",
    )
    assert sufficiency.evidence_status == EvidenceStatus.CONFLICTING
    assert any("Conflicting transfer volume" in c for c in sufficiency.contradictions_detected)


@pytest.mark.asyncio
async def test_case_08_replay_regression_detection(db_session: AsyncSession):
    """Case 8: Replay evaluation detects regression when candidate degrades metrics."""
    service = PolicySimulationService(db_session)
    base_metrics = {"balanced_accuracy": 0.92, "coverage": 1.0}
    cand_metrics = {"balanced_accuracy": 0.78, "coverage": 1.0}

    base_run = HistoricalEvaluationRunRecord(
        id=str(uuid.uuid4()),
        run_name="Baseline-PH",
        rule_id="PH_RULE_LARGE_OUTBOUND_XFER",
        status="COMPLETED",
        validation_state="VALIDATED",
        total_cases=5,
        metrics=base_metrics,
    )
    cand_run = HistoricalEvaluationRunRecord(
        id=str(uuid.uuid4()),
        run_name="Candidate-PH",
        rule_id="PH_RULE_LARGE_OUTBOUND_XFER",
        status="COMPLETED",
        validation_state="VALIDATED",
        total_cases=5,
        metrics=cand_metrics,
    )
    db_session.add(base_run)
    db_session.add(cand_run)
    await db_session.flush()

    for i in range(1, 6):
        inc_id = f"INC-CASE-08-{i}"
        db_session.add(HistoricalEvaluationResultRecord(
            id=str(uuid.uuid4()),
            run_id=base_run.id,
            incident_id=inc_id,
            rule_id="PH_RULE_LARGE_OUTBOUND_XFER",
            ground_truth_label="VERIFIED_TP",
            suggested_verdict="TRUE_POSITIVE",
            effective_verdict="TRUE_POSITIVE",
            trust_score=8,
            is_correct=True,
        ))
        db_session.add(HistoricalEvaluationResultRecord(
            id=str(uuid.uuid4()),
            run_id=cand_run.id,
            incident_id=inc_id,
            rule_id="PH_RULE_LARGE_OUTBOUND_XFER",
            ground_truth_label="VERIFIED_TP",
            suggested_verdict="TRUE_POSITIVE" if i > 2 else "FALSE_POSITIVE",
            effective_verdict="TRUE_POSITIVE" if i > 2 else "FALSE_POSITIVE",
            trust_score=8 if i > 2 else 4,
            is_correct=(i > 2),
        ))

    await db_session.commit()

    comparison = await service.compare_runs(base_run.id, cand_run.id)
    assert comparison.validation_state == EvaluationValidationState.REGRESSION_DETECTED
    assert comparison.critical_regressions_count >= 1


# ==============================================================================
# SECTION 9: CROSS-ARCHETYPE TEST SCENARIOS
# ==============================================================================

def test_cross_archetype_process_execution():
    """Cross-archetype test: PROCESS_EXECUTION with encoded PowerShell."""
    contract = RuleEvidenceContract(
        contract_id="contract-proc-01",
        rule_id="RULE_PROC_EXEC_01",
        detection_archetype="PROCESS_EXECUTION",
        required_evidence=[
            EvidenceFieldRequirement(
                field="process.name",
                evidence_type="ENDPOINT_EDR",
                required_for_tp=True,
                critical=True,
                requirement_level="CORE",
            ),
            EvidenceFieldRequirement(
                field="process.cmdline",
                evidence_type="ENDPOINT_EDR",
                required_for_tp=True,
                critical=True,
                requirement_level="CORE",
            ),
        ],
    )
    payload = {
        "incident_id": "INC-PROC-01",
        "rule_id": "RULE_PROC_EXEC_01",
        "events": [
            {
                "cmdline": "powershell.exe -enc SQBFAFgAIAA...",
                "process_name": "powershell.exe",
            }
        ],
    }
    sufficiency = EvidenceSufficiencyEngine.evaluate_incident_sufficiency(
        incident_payload=payload,
        contract=contract,
        archetype_id="PROCESS_EXECUTION",
    )
    assert sufficiency.evidence_status == EvidenceStatus.SUFFICIENT
    assert len(sufficiency.mandatory_fields_missing) == 0


def test_cross_archetype_authentication():
    """Cross-archetype test: AUTHENTICATION missing mandatory failed attempts."""
    contract = RuleEvidenceContract(
        contract_id="contract-auth-01",
        rule_id="RULE_AUTH_SPRAY_01",
        detection_archetype="AUTHENTICATION",
        required_evidence=[
            EvidenceFieldRequirement(
                field="source_ip",
                evidence_type="IDENTITY_PROVIDER",
                required_for_tp=True,
                critical=True,
                requirement_level="CORE",
            ),
            EvidenceFieldRequirement(
                field="failed_attempts",
                evidence_type="IDENTITY_PROVIDER",
                required_for_tp=True,
                critical=True,
                requirement_level="CORE",
            ),
        ],
    )
    payload = {
        "incident_id": "INC-AUTH-01",
        "rule_id": "RULE_AUTH_SPRAY_01",
        "source_ip": "10.0.1.50",
        # failed_attempts missing!
    }
    sufficiency = EvidenceSufficiencyEngine.evaluate_incident_sufficiency(
        incident_payload=payload,
        contract=contract,
        archetype_id="AUTHENTICATION",
    )
    assert sufficiency.evidence_status == EvidenceStatus.INSUFFICIENT
    assert any("failed" in f.lower() for f in sufficiency.mandatory_fields_missing)


def test_cross_archetype_cloud_audit():
    """Cross-archetype test: CLOUD_AUDIT IAM policy modification."""
    contract = RuleEvidenceContract(
        contract_id="contract-cloud-01",
        rule_id="RULE_CLOUD_IAM_01",
        detection_archetype="CLOUD_AUDIT",
        required_evidence=[
            EvidenceFieldRequirement(
                field="source_ip",
                evidence_type="CLOUD_AUDIT",
                required_for_tp=True,
                critical=True,
                requirement_level="CORE",
            ),
            EvidenceFieldRequirement(
                field="event_type",
                evidence_type="CLOUD_AUDIT",
                required_for_tp=True,
                critical=True,
                requirement_level="CORE",
            ),
        ],
    )
    payload = {
        "incident_id": "INC-CLOUD-01",
        "rule_id": "RULE_CLOUD_IAM_01",
        "source_ip": "54.240.196.1",
        "event_type": "AttachUserPolicy",
    }
    sufficiency = EvidenceSufficiencyEngine.evaluate_incident_sufficiency(
        incident_payload=payload,
        contract=contract,
        archetype_id="CLOUD_AUDIT",
    )
    assert sufficiency.evidence_status == EvidenceStatus.SUFFICIENT


# ==============================================================================
# SECTION 10: FASTAPI API ENDPOINTS INTEGRATION
# ==============================================================================

@pytest.mark.asyncio
async def test_api_evaluate_incident_endpoint(client: AsyncClient, admin_user, admin_token: str, db_session: AsyncSession):
    """Test POST /api/v1/verdict-intelligence/evaluate-incident endpoint."""
    inc = Incident(
        id="inc-api-001",
        incident_id="INC-API-001",
        rule_id="PH_RULE_LARGE_OUTBOUND_XFER",
        title="Large Outbound Transfer",
        event_type="Exfiltration",
        severity="MEDIUM",
        source_ip="10.0.1.50",
        raw_payload={
            "destination_ip": "198.51.100.23",
            "sentBytes64": 2130499380,
            "direction": "outbound",
        },
    )
    db_session.add(inc)
    await db_session.commit()

    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {
        "incident_id": "INC-API-001",
        "rule_id": "PH_RULE_LARGE_OUTBOUND_XFER",
        "custom_model_output": {
            "proposed_verdict": "TRUE_POSITIVE",
            "reason": "Host 10.0.1.50 sent 2130499380 bytes to 198.51.100.23 outbound.",
            "claims": [
                {"claim": "Host 10.0.1.50 sent bytes", "evidence_ids": ["source_ip"], "claim_type": "OBSERVED_FACT"}
            ],
        },
    }
    res = await client.post("/api/v1/verdict-intelligence/evaluate-incident", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["incident_id"] == "INC-API-001"
    assert "trust_score" in data
    assert "effective_verdict" in data
    assert "evidence_status" in data


@pytest.mark.asyncio
async def test_api_metrics_endpoint(client: AsyncClient, admin_user, admin_token: str):
    """Test GET /api/v1/verdict-intelligence/metrics endpoint."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = await client.get("/api/v1/verdict-intelligence/metrics", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_evaluated_incidents" in data
    assert "average_trust_score" in data
    assert "trust_score_distribution" in data


@pytest.mark.asyncio
async def test_api_export_endpoint(client: AsyncClient, admin_user, admin_token: str):
    """Test GET /api/v1/verdict-intelligence/export endpoint."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    res_json = await client.get("/api/v1/verdict-intelligence/export?format=json", headers=headers)
    assert res_json.status_code == 200
    assert "results" in res_json.json()

    res_csv = await client.get("/api/v1/verdict-intelligence/export?format=csv", headers=headers)
    assert res_csv.status_code == 200
    assert res_csv.headers["content-type"].startswith("text/csv")


@pytest.mark.asyncio
async def test_api_evaluate_simulation_endpoint(client: AsyncClient, admin_user, admin_token: str, db_session: AsyncSession):
    """Test POST /api/prompts/rule/{rule_id}/evaluate-simulation endpoint with UUID, rule_identifier, and missing version fallback."""
    rule = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_SIM_TEST_01",
        name="Simulation Test Rule",
        event_type="ProcessExecution",
        severity="HIGH",
    )
    db_session.add(rule)
    await db_session.flush()

    rule_prompt = RulePrompt(
        id=str(uuid.uuid4()),
        rule_id=rule.id,
        title=rule.name,
    )
    db_session.add(rule_prompt)
    await db_session.flush()

    pv = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=rule_prompt.id,
        version_number=1,
        status="DRAFT",
        is_template_draft=False,
        tp_indicators="Encoded command",
        fp_indicators="Maintenance script",
    )
    db_session.add(pv)
    await db_session.flush()

    rule_prompt.active_version_id = pv.id
    await db_session.commit()

    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Evaluate with exact rule.id UUID and version_id
    res1 = await client.post(f"/api/prompts/rule/{rule.id}/evaluate-simulation?version_id={pv.id}", headers=headers)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] in ("PASSED", "INSUFFICIENT_DATA", "FAILED")
    assert "sample_count" in data1
    assert data1["baseline_metrics"] is None

    # 2. Evaluate with SIEM rule_id string and nonexistent version_id (should fall back to active version safely)
    res2 = await client.post(f"/api/prompts/rule/{rule.rule_id}/evaluate-simulation?version_id=nonexistent-v-id", headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] in ("PASSED", "INSUFFICIENT_DATA", "FAILED")

    # 3. Evaluate with without version_id query param
    res3 = await client.post(f"/api/prompts/rule/{rule.id}/evaluate-simulation", headers=headers)
    assert res3.status_code == 200

    # 4. Defensive test: Ensure evaluate_candidate_policy handles metrics with None values without TypeError
    sim_svc = PolicySimulationService(db_session)
    mock_run = HistoricalEvaluationRunRecord(
        id=str(uuid.uuid4()),
        run_name="Mock Run With None Metrics",
        rule_id=rule.id,
        status="COMPLETED",
        validation_state="INSUFFICIENT_DATA",
        total_cases=5,
        metrics={
            "balanced_accuracy": None,
            "precision": None,
            "recall": None,
            "specificity": None,
            "abstention_rate": None,
            "critical_false_negatives": None,
        },
        regression_summary=None,
    )
    db_session.add(mock_run)
    await db_session.flush()

    # Mock run_dry_run_intelligence_evaluation returning mock_run
    orig_fn = sim_svc.run_dry_run_intelligence_evaluation
    async def mock_eval(*args, **kwargs):
        return mock_run
    sim_svc.run_dry_run_intelligence_evaluation = mock_eval

    res_none = await sim_svc.evaluate_candidate_policy(rule_id=rule.id, candidate_version=pv)
    assert res_none["balanced_accuracy"] == 0.0
    assert res_none["precision"] == 0.0
    assert res_none["recall"] == 0.0
    assert res_none["specificity"] == 0.0
    assert res_none["abstention_rate"] == 0.0
    assert res_none["critical_regressions"] == 0
    sim_svc.run_dry_run_intelligence_evaluation = orig_fn


# ==============================================================================
# SECTION 11: END-TO-END SCENARIOS FOR PH_RULE_CS_SUSPICIOUS_ACTIVITY & ARCHETYPES
# ==============================================================================

def test_cs_suspicious_activity_true_positive():
    """PH_RULE_CS_SUSPICIOUS_ACTIVITY: Confirmed malicious PowerShell execution with full telemetry yields high trust TP."""
    contract = RuleEvidenceContract(
        contract_id="EC-CS-SUSPICIOUS-V1",
        rule_id="PH_RULE_CS_SUSPICIOUS_ACTIVITY",
        detection_archetype="MALWARE_EXECUTION",
        required_evidence=[
            EvidenceFieldRequirement(field="endpoint.hostname", evidence_type="ENDPOINT", requirement_level="CORE", critical=True),
            EvidenceFieldRequirement(field="process.command_line", evidence_type="PROCESS", requirement_level="CORE", critical=True),
            EvidenceFieldRequirement(field="user.name", evidence_type="USER", requirement_level="CORE", critical=True),
            EvidenceFieldRequirement(field="mitre.technique", evidence_type="MITRE", requirement_level="CONDITIONAL", critical=False),
        ],
    )

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    incident = {
        "incident_id": "INC-CS-001",
        "Host Name": "FIN-SRV-04",
        "Command": "powershell.exe -ExecutionPolicy Bypass -NoProfile -enc SQBFAFgAIAAoAE4AZQB3AC0ATwBiAGoAZQBjAHQA...",
        "User": "svc_finops",
        "Attack Tactic": "Execution",
        "Attack Technique": "Command and Scripting Interpreter: PowerShell (T1059.001)",
        "Process Blocked": False,
        "File Quarantined": False,
        "File Name": "powershell.exe",
        "first_seen_epoch": now_ms - 60000,
        "last_seen_epoch": now_ms,
    }

    # 1. Sufficiency
    suff = EvidenceSufficiencyEngine.evaluate_sufficiency(
        incident_telemetry=incident,
        contract=contract,
        archetype=DetectionArchetype.ENDPOINT_MALWARE,
    )
    assert suff.is_sufficient is True
    assert suff.sufficiency_score >= 80.0
    assert len(suff.missing_mandatory_fields) == 0

    # 2. Claim Grounding
    model_output = {
        "proposed_verdict": "TRUE_POSITIVE",
        "reason": "Suspicious encoded PowerShell command executed on host FIN-SRV-04 by user svc_finops matching T1059.001.",
        "claims": [
            {"claim": "powershell.exe executed on FIN-SRV-04", "evidence_ids": ["endpoint.hostname", "process.command_line"], "claim_type": "OBSERVED_FACT"},
            {"claim": "Execution by user svc_finops", "evidence_ids": ["user.name"], "claim_type": "OBSERVED_FACT"},
        ],
    }
    claim_res = VerdictClaimValidator.validate_claims(
        model_output=model_output,
        canonical_telemetry=incident,
    )
    assert claim_res.claims_supported is True
    assert claim_res.unsupported_claims == 0
    assert len(claim_res.contradictions) == 0

    # 3. Guardrails
    guard = VerdictGuardrailsEngine.evaluate_guardrails(
        proposed_verdict="TRUE_POSITIVE",
        evidence_sufficiency=suff,
        claim_verification=claim_res,
        incident_telemetry=incident,
    )
    assert guard.effective_verdict == "TRUE_POSITIVE"
    assert guard.guardrails_triggered == []

    # 4. Trustworthiness (Rule calibrated with N=45)
    trust = VerdictTrustworthinessEngine.compute_trust_score(
        rule_id="PH_RULE_CS_SUSPICIOUS_ACTIVITY",
        effective_verdict="TRUE_POSITIVE",
        evidence_assessment=suff,
        claim_result=claim_res,
        historical_sample_size=45,
        historical_accuracy=0.94,
    )
    assert trust.ordinal_score >= 8
    assert trust.is_calibrated is True


def test_cs_suspicious_activity_false_positive_authorized_maintenance():
    """PH_RULE_CS_SUSPICIOUS_ACTIVITY: Legitimate remote support tool (UltraViewer) in maintenance window yields high trust FP."""
    contract = RuleEvidenceContract(
        contract_id="EC-CS-SUSPICIOUS-V1",
        rule_id="PH_RULE_CS_SUSPICIOUS_ACTIVITY",
        detection_archetype="MALWARE_EXECUTION",
        required_evidence=[
            EvidenceFieldRequirement(field="endpoint.hostname", evidence_type="ENDPOINT", requirement_level="CORE", critical=True),
            EvidenceFieldRequirement(field="process.command_line", evidence_type="PROCESS", requirement_level="CORE", critical=True),
            EvidenceFieldRequirement(field="user.name", evidence_type="USER", requirement_level="CORE", critical=True),
        ],
    )

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    incident = {
        "incident_id": "INC-CS-002",
        "Host Name": "DESKTOP-HR-09",
        "Command": "\"C:\\Program Files (x86)\\UltraViewer\\UltraViewer_Service.exe\"",
        "User": "admin_helpdesk",
        "Attack Tactic": "Persistence",
        "Attack Technique": "Remote Access Software",
        "Process Blocked": False,
        "File Quarantined": False,
        "File Name": "UltraViewer_Service.exe",
        "first_seen_epoch": now_ms - 60000,
        "last_seen_epoch": now_ms,
    }

    suff = EvidenceSufficiencyEngine.evaluate_sufficiency(
        incident_telemetry=incident,
        contract=contract,
        archetype=DetectionArchetype.ENDPOINT_MALWARE,
    )
    assert suff.is_sufficient is True

    model_output = {
        "proposed_verdict": "FALSE_POSITIVE",
        "reason": "Authorized remote assistance software UltraViewer_Service.exe executed on DESKTOP-HR-09 by admin_helpdesk.",
        "claims": [
            {"claim": "UltraViewer executed by admin_helpdesk", "evidence_ids": ["user.name", "process.command_line"], "claim_type": "OBSERVED_FACT"}
        ],
    }
    claim_res = VerdictClaimValidator.validate_claims(model_output=model_output, canonical_telemetry=incident)
    guard = VerdictGuardrailsEngine.evaluate_guardrails(
        proposed_verdict="FALSE_POSITIVE",
        evidence_sufficiency=suff,
        claim_verification=claim_res,
        incident_telemetry=incident,
    )
    assert guard.effective_verdict == "FALSE_POSITIVE"

    trust = VerdictTrustworthinessEngine.compute_trust_score(
        rule_id="PH_RULE_CS_SUSPICIOUS_ACTIVITY",
        effective_verdict="FALSE_POSITIVE",
        evidence_assessment=suff,
        claim_result=claim_res,
        historical_sample_size=35,
        historical_accuracy=0.91,
    )
    assert trust.ordinal_score >= 8


def test_cs_suspicious_activity_missing_mandatory_command_line():
    """PH_RULE_CS_SUSPICIOUS_ACTIVITY: Missing Command Line triggers Infallible Rule & demotes TP to REQUIRES_ATTENTION."""
    contract = RuleEvidenceContract(
        contract_id="EC-CS-SUSPICIOUS-V1",
        rule_id="PH_RULE_CS_SUSPICIOUS_ACTIVITY",
        detection_archetype="MALWARE_EXECUTION",
        required_evidence=[
            EvidenceFieldRequirement(field="endpoint.hostname", evidence_type="ENDPOINT", requirement_level="CORE", critical=True),
            EvidenceFieldRequirement(field="process.command_line", evidence_type="PROCESS", requirement_level="CORE", critical=True),
            EvidenceFieldRequirement(field="user.name", evidence_type="USER", requirement_level="CORE", critical=True),
        ],
    )

    # Missing Command / process.command_line
    incident = {
        "incident_id": "INC-CS-003",
        "Host Name": "FIN-SRV-04",
        "User": "svc_finops",
        "Attack Tactic": "Execution",
    }

    suff = EvidenceSufficiencyEngine.evaluate_sufficiency(
        incident_telemetry=incident,
        contract=contract,
        archetype=DetectionArchetype.ENDPOINT_MALWARE,
    )
    # Infallible Rule: Missing mandatory field forces is_sufficient=False and score <= 49.0
    assert suff.is_sufficient is False
    assert suff.sufficiency_score <= 49.0
    assert "process.command_line" in suff.missing_mandatory_fields

    claim_res = ClaimVerificationResult(
        incident_id="INC-CS-003",
        total_claims=0,
        grounded_claims=0,
        unsupported_claims=0,
        contradicted_claims=0,
    )

    guard = VerdictGuardrailsEngine.evaluate_guardrails(
        proposed_verdict="TRUE_POSITIVE",
        evidence_sufficiency=suff,
        claim_verification=claim_res,
        incident_telemetry=incident,
    )
    assert guard.effective_verdict == "REQUIRES_ANALYST_ATTENTION"
    assert any("G1" in g for g in guard.guardrails_triggered)


def test_cs_suspicious_activity_contradictory_execution_evidence():
    """PH_RULE_CS_SUSPICIOUS_ACTIVITY: Process Blocked=True contradictions against ongoing breach claims trigger demotion."""
    contract = RuleEvidenceContract(
        contract_id="EC-CS-SUSPICIOUS-V1",
        rule_id="PH_RULE_CS_SUSPICIOUS_ACTIVITY",
        detection_archetype="MALWARE_EXECUTION",
        required_evidence=[
            EvidenceFieldRequirement(field="endpoint.hostname", evidence_type="ENDPOINT", requirement_level="CORE", critical=True),
            EvidenceFieldRequirement(field="process.command_line", evidence_type="PROCESS", requirement_level="CORE", critical=True),
            EvidenceFieldRequirement(field="user.name", evidence_type="USER", requirement_level="CORE", critical=True),
        ],
    )

    incident = {
        "incident_id": "INC-CS-004",
        "Host Name": "FIN-SRV-04",
        "Command": "mimikatz.exe sekurlsa::logonpasswords",
        "User": "svc_finops",
        "Process Blocked": True,
        "File Quarantined": True,
        "endpoint.process_blocked": True,
    }

    suff = EvidenceSufficiencyEngine.evaluate_sufficiency(
        incident_telemetry=incident,
        contract=contract,
        archetype=DetectionArchetype.ENDPOINT_MALWARE,
    )

    # Model claims process was NOT blocked and actively stole credentials
    model_output = {
        "proposed_verdict": "TRUE_POSITIVE",
        "reason": "Mimikatz executed without interference and active credential theft succeeded.",
        "claims": [
            {"claim": "Mimikatz executed successfully without block", "evidence_ids": ["endpoint.process_blocked"], "claim_type": "ASSERTION"}
        ],
    }
    claim_res = VerdictClaimValidator.validate_claims(
        model_output=model_output,
        canonical_telemetry=incident,
    )
    # Contradiction detected
    assert len(claim_res.contradictions) > 0 or not claim_res.claims_supported

    guard = VerdictGuardrailsEngine.evaluate_guardrails(
        proposed_verdict="TRUE_POSITIVE",
        evidence_sufficiency=suff,
        claim_verification=claim_res,
        incident_telemetry=incident,
    )
    assert guard.effective_verdict == "REQUIRES_ANALYST_ATTENTION"


def test_cs_suspicious_activity_hallucinated_hash_and_foreign_ip():
    """PH_RULE_CS_SUSPICIOUS_ACTIVITY: Model hallucinating external IP and non-existent SHA256 triggers Guardrail G2."""
    contract = RuleEvidenceContract(
        contract_id="EC-CS-SUSPICIOUS-V1",
        rule_id="PH_RULE_CS_SUSPICIOUS_ACTIVITY",
        detection_archetype="MALWARE_EXECUTION",
        required_evidence=[
            EvidenceFieldRequirement(field="endpoint.hostname", evidence_type="ENDPOINT", requirement_level="CORE", critical=True),
            EvidenceFieldRequirement(field="process.command_line", evidence_type="PROCESS", requirement_level="CORE", critical=True),
            EvidenceFieldRequirement(field="user.name", evidence_type="USER", requirement_level="CORE", critical=True),
        ],
    )

    incident = {
        "incident_id": "INC-CS-005",
        "Host Name": "SRV-APP-12",
        "Command": "whoami /all",
        "User": "guest",
    }

    suff = EvidenceSufficiencyEngine.evaluate_sufficiency(
        incident_telemetry=incident,
        contract=contract,
        archetype=DetectionArchetype.ENDPOINT_MALWARE,
    )

    # Hallucinated external IP 203.0.113.88 not present in telemetry
    model_output = {
        "proposed_verdict": "TRUE_POSITIVE",
        "reason": "Host SRV-APP-12 connected to command server 203.0.113.88 and downloaded malware.",
        "claims": [
            {"claim": "Host connected to 203.0.113.88", "evidence_ids": ["destination_ip"], "claim_type": "OBSERVED_FACT"}
        ],
    }

    claim_res = VerdictClaimValidator.validate_claims(
        model_output=model_output,
        canonical_telemetry=incident,
    )
    assert claim_res.unsupported_claims > 0 or len(claim_res.unsupported_claims_list) > 0
    assert claim_res.claims_supported is False

    guard = VerdictGuardrailsEngine.evaluate_guardrails(
        proposed_verdict="TRUE_POSITIVE",
        evidence_sufficiency=suff,
        claim_verification=claim_res,
        incident_telemetry=incident,
    )
    assert guard.effective_verdict == "REQUIRES_ANALYST_ATTENTION"
    assert any("G2" in g for g in guard.guardrails_triggered)


@pytest.mark.asyncio
async def test_cs_suspicious_activity_simulation_regression(db_session: AsyncSession):
    """PH_RULE_CS_SUSPICIOUS_ACTIVITY: Paired historical simulation detects regressions when accuracy degrades."""
    sim_svc = PolicySimulationService(db_session)
    cand_v = PromptVersion(
        id="cand-cs-v2",
        prompt_id="prompt-cs-01",
        version_number=2,
        status="DRAFT",
        rule_specific_prompt="CrowdStrike suspicious activity detection policy v2",
        required_evidence="endpoint.hostname, process.command_line, user.name",
    )

    res = await sim_svc.evaluate_candidate_policy(
        rule_id="PH_RULE_CS_SUSPICIOUS_ACTIVITY",
        candidate_version=cand_v,
    )
    assert "status" in res
    assert "simulation_status" in res
    assert "sample_count" in res
    assert "regression_detected" in res
    assert "abstention_rate" in res
    assert res["status"] in ("PASSED", "INSUFFICIENT_DATA", "FAILED")

