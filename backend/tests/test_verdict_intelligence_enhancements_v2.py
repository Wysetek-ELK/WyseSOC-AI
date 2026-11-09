import pytest
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident, HistoricalGroundTruth
from app.models.rule import Rule
from app.models.prompt import RulePrompt, PromptVersion
from app.schemas.evidence_contract import (
    RuleEvidenceContract,
    EvidenceFieldRequirement,
)
from app.schemas.policy_quality import GateStatus, SimulationStatus
from app.schemas.verdict_intelligence import (
    GroundTruthLabel,
    UserVisibleVerdict,
)
from app.services.verdict_trustworthiness_engine import VerdictTrustworthinessEngine
from app.services.calibration_evaluator import CalibrationEvaluator
from app.services.empirical_accuracy_evaluator import EmpiricalAccuracyEvaluator
from app.services.policy_simulation_service import PolicySimulationService
from app.services.policy_quality_validator import PolicyQualityValidator


# ==============================================================================
# SECTION A: VERDICT TRUSTWORTHINESS ENGINE (v2.2.0)
# ==============================================================================

def test_verdict_trustworthiness_not_calculable_on_empty_telemetry():
    """Verify that empty telemetry or total absence of evidence yields NOT_CALCULABLE state."""
    contract = RuleEvidenceContract(
        contract_id="EC-TEST-EMPTY",
        rule_id="RULE_TEST_EMPTY",
        detection_archetype="NETWORK_EXFILTRATION",
        required_evidence=[
            EvidenceFieldRequirement(field="destination_ip", evidence_type="NETWORK_FLOW", required_for_tp=True, critical=True),
        ],
    )

    empty_telemetry = {}
    model_output = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 0.95,
        "reason": "Suspicious network transfer",
    }

    result = VerdictTrustworthinessEngine.evaluate_verdict_trust(
        incident_payload=empty_telemetry,
        model_output=model_output,
        contract=contract,
        archetype_id="NETWORK_EXFILTRATION",
    )

    assert result.trust_status == "NOT_CALCULABLE"
    assert result.trust_score is None
    assert result.calculation_version == "v2.2.0"
    assert "not_calculable" in result.human_readable_explanation.lower() or "not_calculable" in " ".join(result.confidence_limitations).lower()


def test_verdict_trustworthiness_calculated_with_telemetry():
    """Verify that valid telemetry yields CALCULATED status with 1-10 score and v2.2.0 version."""
    contract = RuleEvidenceContract(
        contract_id="EC-TEST-VALID",
        rule_id="RULE_TEST_VALID",
        detection_archetype="NETWORK_EXFILTRATION",
        required_evidence=[
            EvidenceFieldRequirement(field="destination_ip", evidence_type="NETWORK_FLOW", required_for_tp=True, critical=True),
        ],
    )

    telemetry = {
        "destination_ip": "198.51.100.22",
        "bytes_out": 52428800,
        "direction": "outbound",
    }
    model_output = {
        "verdict": "TRUE_POSITIVE",
        "confidence": 0.90,
        "reason": "Large outbound exfiltration to external IP",
    }

    result = VerdictTrustworthinessEngine.evaluate_verdict_trust(
        incident_payload=telemetry,
        model_output=model_output,
        contract=contract,
        archetype_id="NETWORK_EXFILTRATION",
        is_calibrated=True,
        historical_sample_count=45,
    )

    assert result.trust_status == "CALCULATED"
    assert result.trust_score is not None
    assert 1 <= result.trust_score <= 10
    assert result.calculation_version == "v2.2.0"


# ==============================================================================
# SECTION B: CONFIDENCE CALIBRATION (Configurable Thresholds & Class Balance)
# ==============================================================================

def test_calibration_evaluator_insufficient_samples():
    """Calibration must remain NOT_CALIBRATED when sample size < min_samples (30)."""
    predictions = [
        {
            "ground_truth_label": GroundTruthLabel.VERIFIED_TP.value,
            "effective_verdict": UserVisibleVerdict.TRUE_POSITIVE.value,
            "trust_score": 8,
        }
        for _ in range(10)
    ] + [
        {
            "ground_truth_label": GroundTruthLabel.VERIFIED_FP.value,
            "effective_verdict": UserVisibleVerdict.FALSE_POSITIVE.value,
            "trust_score": 3,
        }
        for _ in range(10)
    ]

    report = CalibrationEvaluator.evaluate_calibration(predictions, min_samples=30)
    assert report.status == "NOT_CALIBRATED"
    assert report.is_calibrated is False
    assert report.brier_score is None
    assert any("BELOW_MINIMUM_THRESHOLD" in note for note in report.calibration_notes)


def test_calibration_evaluator_unbalanced_class_representation():
    """Calibration must remain NOT_CALIBRATED when class representation is deficient (< 3 in either class)."""
    # 35 samples, all VERIFIED_TP (0 VERIFIED_FP)
    predictions = [
        {
            "ground_truth_label": GroundTruthLabel.VERIFIED_TP.value,
            "effective_verdict": UserVisibleVerdict.TRUE_POSITIVE.value,
            "trust_score": 9,
        }
        for _ in range(35)
    ]

    report = CalibrationEvaluator.evaluate_calibration(predictions, min_samples=30)
    assert report.status == "NOT_CALIBRATED"
    assert report.is_calibrated is False
    assert report.brier_score is None
    assert any("INSUFFICIENT_CLASS_REPRESENTATION" in note for note in report.calibration_notes)


def test_calibration_evaluator_sufficient_and_balanced():
    """Calibration calculates Brier score and bins when N >= 30 and class balance is satisfied."""
    predictions = [
        {
            "ground_truth_label": GroundTruthLabel.VERIFIED_TP.value,
            "effective_verdict": UserVisibleVerdict.TRUE_POSITIVE.value,
            "trust_score": 8,
            "raw_trust_score": 80.0,
        }
        for _ in range(20)
    ] + [
        {
            "ground_truth_label": GroundTruthLabel.VERIFIED_FP.value,
            "effective_verdict": UserVisibleVerdict.FALSE_POSITIVE.value,
            "trust_score": 3,
            "raw_trust_score": 30.0,
        }
        for _ in range(15)
    ]

    report = CalibrationEvaluator.evaluate_calibration(predictions, min_samples=30)
    assert report.status == "CALIBRATED"
    assert report.is_calibrated is True
    assert report.brier_score is not None
    assert report.expected_calibration_error is not None
    assert len(report.reliability_bins) == 5


# ==============================================================================
# SECTION C: EMPIRICAL ACCURACY & UNDEFINED METRICS HANDLING
# ==============================================================================

def test_empirical_accuracy_undefined_metrics_return_none():
    """Metrics with zero denominators (e.g. TN=0 and FP=0) must return None, not 0.0."""
    # Only TP cases present: 5 TPs, 0 FPs, 0 TNs, 0 FNs
    cases = [
        {
            "effective_verdict": UserVisibleVerdict.TRUE_POSITIVE.value,
            "ground_truth_label": GroundTruthLabel.VERIFIED_TP.value,
            "trust_score": 8,
        }
        for _ in range(5)
    ]

    metrics = EmpiricalAccuracyEvaluator.evaluate_performance(
        evaluations=cases,
        compute_curve=False,
    )

    # Specificity = TN / (TN + FP) -> 0 / 0 -> None
    assert metrics.specificity is None
    # False Positive Rate = FP / (FP + TN) -> 0 / 0 -> None
    assert metrics.false_positive_rate is None
    # Balanced Accuracy = (Recall + Specificity) / 2 -> None because Specificity is None
    assert metrics.balanced_accuracy is None
    # Recall = TP / (TP + FN) -> 5 / 5 = 1.0
    assert metrics.recall == 1.0
    # TP and FP ground truth counts tracked
    assert metrics.tp_ground_truth_count == 5
    assert metrics.fp_ground_truth_count == 0


# ==============================================================================
# SECTION D: INCIDENT ELIGIBILITY FUNNEL & EXCLUSION REASONS
# ==============================================================================

@pytest.mark.asyncio
async def test_incident_eligibility_funnel_and_exclusion_reasons(db_session: AsyncSession):
    """Verify that PolicySimulationService tracks a 6-stage eligibility funnel with explicit reasons."""
    rule = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_FUNNEL_TEST_01",
        name="Funnel Test Rule",
        event_type="ProcessExecution",
        severity="MEDIUM",
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
    )
    db_session.add(pv)
    await db_session.flush()

    # Create 6 incidents for this rule:
    # 1. Eligible TP with analyst ground truth
    inc_1 = Incident(
        id=str(uuid.uuid4()),
        incident_id="INC-FUNNEL-01",
        rule_id=rule.rule_id,
        event_type="ProcessExecution",
        severity="HIGH",
        raw_payload={"command_line": "powershell -enc aW52b2tl"},
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(inc_1)
    await db_session.flush()
    gt_1 = HistoricalGroundTruth(
        id=str(uuid.uuid4()),
        incident_id=inc_1.id,
        resolution="True Positive",
        is_ml_generated=False,
    )
    db_session.add(gt_1)

    # 2. Eligible FP with analyst ground truth
    inc_2 = Incident(
        id=str(uuid.uuid4()),
        incident_id="INC-FUNNEL-02",
        rule_id=rule.rule_id,
        event_type="ProcessExecution",
        severity="MEDIUM",
        raw_payload={"command_line": "ccmexec.exe /maintenance"},
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(inc_2)
    await db_session.flush()
    gt_2 = HistoricalGroundTruth(
        id=str(uuid.uuid4()),
        incident_id=inc_2.id,
        resolution="False Positive",
        is_ml_generated=False,
    )
    db_session.add(gt_2)

    # 3. Excluded: Missing Analyst Label
    inc_3 = Incident(
        id=str(uuid.uuid4()),
        incident_id="INC-FUNNEL-03",
        rule_id=rule.rule_id,
        event_type="ProcessExecution",
        severity="LOW",
        raw_payload={"command_line": "whoami.exe"},
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(inc_3)

    # 4. Excluded: Ambiguous Label (analyst resolution is Pending / unconfirmed)
    inc_4 = Incident(
        id=str(uuid.uuid4()),
        incident_id="INC-FUNNEL-04",
        rule_id=rule.rule_id,
        event_type="ProcessExecution",
        severity="LOW",
        raw_payload={"command_line": "net user"},
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(inc_4)
    await db_session.flush()
    gt_4 = HistoricalGroundTruth(
        id=str(uuid.uuid4()),
        incident_id=inc_4.id,
        resolution="Under Investigation",
        is_ml_generated=False,
    )
    db_session.add(gt_4)

    # 5. Excluded: Corrupt / Empty Payload
    inc_5 = Incident(
        id=str(uuid.uuid4()),
        incident_id="INC-FUNNEL-05",
        rule_id=rule.rule_id,
        event_type="ProcessExecution",
        severity="LOW",
        raw_payload={},
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(inc_5)

    # 6. Excluded: Heuristic / ML Generated Label
    inc_6 = Incident(
        id=str(uuid.uuid4()),
        incident_id="INC-FUNNEL-06",
        rule_id=rule.rule_id,
        event_type="ProcessExecution",
        severity="LOW",
        raw_payload={"command_line": "calc.exe"},
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(inc_6)
    await db_session.flush()
    gt_6 = HistoricalGroundTruth(
        id=str(uuid.uuid4()),
        incident_id=inc_6.id,
        resolution="True Positive",
        is_ml_generated=True,
    )
    db_session.add(gt_6)

    await db_session.commit()

    sim_svc = PolicySimulationService(db_session)
    result = await sim_svc.evaluate_candidate_policy(rule_id=rule.id, candidate_version=pv)

    # Validate Funnel metrics
    assert "funnel" in result
    funnel = result["funnel"]
    assert funnel["total_scanned"] == 6
    assert funnel["rule_matched"] == 6
    assert funnel["analyst_labeled"] == 4
    assert funnel["eligible"] == 2
    assert funnel["excluded"] == 4

    # Validate explicit exclusion reasons breakdown
    reasons = funnel["exclusion_reasons"]
    assert reasons["MISSING_ANALYST_LABEL"] == 1
    assert reasons["AMBIGUOUS_LABEL"] == 1
    assert reasons["CORRUPT_OR_EMPTY_PAYLOAD"] == 1
    assert reasons["HEURISTIC_OR_ML_LABEL"] == 1

    # Eligible ground truth is 2 (< 5), so empirical validation status is INSUFFICIENT_DATA
    assert result["empirical_validation_status"] == "INSUFFICIENT_DATA"
    # No baseline run exists, so regression status is NOT_ASSESSED
    assert result["regression_status"] == "NOT_ASSESSED"


# ==============================================================================
# SECTION E: QUALITY GATE G8 VALIDATION & REGRESSION PREVENTION
# ==============================================================================

def test_gate_8_blocks_when_insufficient_ground_truth():
    """Gate G8 must return WARNING with 0.0 pts when eligible ground truth < 5."""
    validator = PolicyQualityValidator()

    # Simulating 24 evaluated incidents, but 0 eligible ground truth cases
    sim_results_insufficient = {
        "status": "INSUFFICIENT_DATA",
        "sample_count": 24,
        "eligible_ground_truth_count": 0,
        "verified_ground_truth_cases": 0,
        "balanced_accuracy": None,
        "regression_status": "NOT_ASSESSED",
    }

    score, status, sim_status, blockers, warns, details = validator._evaluate_gate_8_simulation(sim_results_insufficient)
    assert status == GateStatus.WARNING
    assert score == 0.0
    assert any("INSUFFICIENT_DATA" in w or "verified historical cases" in w for w in warns)
    assert "INSUFFICIENT_DATA" in details


def test_gate_8_fails_when_critical_regressions_detected():
    """Gate G8 must return FAILED (blocking gate) with 0.0 pts when critical regressions are detected."""
    validator = PolicyQualityValidator()

    sim_results_regressed = {
        "status": "FAILED",
        "sample_count": 15,
        "eligible_ground_truth_count": 15,
        "verified_ground_truth_cases": 15,
        "balanced_accuracy": 0.65,
        "regression_status": "REGRESSION_DETECTED",
        "critical_regressions": 2,
    }

    score, status, sim_status, blockers, warns, details = validator._evaluate_gate_8_simulation(sim_results_regressed)
    assert status == GateStatus.FAILED
    assert score == 0.0
    assert len(blockers) > 0
    assert "FAILED_REGRESSION_GATE" in blockers[0]


def test_gate_8_passes_when_sufficient_ground_truth_and_no_regression():
    """Gate G8 awards 15.0 pts when N_eligible >= 5 and empirical validation passes."""
    validator = PolicyQualityValidator()

    sim_results_passed = {
        "status": "PASSED",
        "sample_count": 10,
        "eligible_ground_truth_count": 10,
        "verified_ground_truth_cases": 10,
        "balanced_accuracy": 0.95,
        "regression_status": "PASS",
        "critical_regressions": 0,
    }

    score, status, sim_status, blockers, warns, details = validator._evaluate_gate_8_simulation(sim_results_passed)
    assert status == GateStatus.PASSED
    assert score == 15.0
    assert len(blockers) == 0


# ==============================================================================
# SECTION F: GATE G5 BROAD BENIGN ASSUMPTIONS DETECTION
# ==============================================================================

def test_gate_5_rejects_broad_benign_assumptions():
    """Gate G5 must reject policies that assume loopback/localhost is blanket benign without authorization."""
    validator = PolicyQualityValidator()

    pv = PromptVersion(
        id="pv-g5-test",
        prompt_id="rp-g5-test",
        version_number=1,
        status="DRAFT",
        fp_indicators="All traffic originating from 127.0.0.1 and loopback is automatically benign.",
        common_prompt="Standard baseline",
        rule_specific_prompt="Exfiltration policy",
    )

    score, status, blockers, warns, details = validator._evaluate_gate_5_fp_criteria(pv, None)
    assert status == GateStatus.FAILED
    assert any("loopback" in b.lower() or "127.0.0.1" in b.lower() for b in blockers)
