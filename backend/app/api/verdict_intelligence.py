"""
FastAPI Router for Verdict Intelligence & Dry-Run Intelligence Validation (AIS 2.1).
Exposes endpoints for:
- Incident-level Trust Score & Evidence Sufficiency evaluation
- Historical dry-run empirical accuracy backtesting
- Risk-coverage curves and calibration analysis
- Paired baseline vs candidate regression comparisons
- JSON and CSV report export
"""

import io
import csv
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.database import get_db
from app.api.deps import get_current_active_user, require_analyst, require_admin
from app.models.user import User
from app.models.incident import Incident, HistoricalGroundTruth
from app.models.rule import Rule
from app.models.prompt import PromptVersion
from app.models.verdict_intelligence import (
    VerdictTrustAssessmentRecord,
    EvidenceSufficiencyAssessmentRecord,
    GroundTruthValidationRecord,
    HistoricalEvaluationRunRecord,
    HistoricalEvaluationResultRecord,
)
from app.config import settings
from app.schemas.verdict_intelligence import (
    IncidentTrustEvaluationRequest,
    HistoricalEvaluationRunRequest,
    VerdictTrustAssessmentResult,
    TrustScoreDimensionBreakdown,
    EvidenceSufficiencyAssessmentResult,
    EmpiricalAccuracyMetrics,
    RegressionComparisonReport,
    CalibrationReport,
)
from app.services.verdict_trustworthiness_engine import VerdictTrustworthinessEngine
from app.services.evidence_sufficiency_engine import EvidenceSufficiencyEngine
from app.services.policy_simulation_service import PolicySimulationService
from app.services.evidence_contract_service import EvidenceContractService

logger = logging.getLogger("ai_verdict.api.verdict_intelligence")

router = APIRouter(prefix="/verdict-intelligence", tags=["Verdict Intelligence Validation"])


# --------------------------------------------------------------------------
# 1. Incident Trust Evaluation
# --------------------------------------------------------------------------

@router.post("/evaluate-incident-trust", response_model=VerdictTrustAssessmentResult)
@router.post("/evaluate-incident", response_model=VerdictTrustAssessmentResult)
async def evaluate_incident_trust(
    req: IncidentTrustEvaluationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """
    Evaluates evidence sufficiency, claim grounding, and computes an ordinal 1-10 Trust Score
    and guardrail-adjusted effective verdict for an incident.
    """
    # 1. Fetch Incident
    q = select(Incident).where(Incident.incident_id == req.incident_id)
    res = await db.execute(q)
    inc = res.scalar_one_or_none()
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident {req.incident_id} not found.")

    rule_id = req.rule_id or inc.rule_id or "RULE-UNKNOWN"

    # 2. Fetch Evidence Contract if available
    contract = None
    try:
        contract_srv = EvidenceContractService(db)
        contract = await contract_srv.get_active_contract_for_rule(rule_id)
    except Exception as e:
        logger.warning(f"Contract fetch warning: {e}")

    # Build incident payload
    inc_payload = {
        "id": inc.id,
        "incident_id": inc.incident_id,
        "rule_id": rule_id,
        "source_ip": inc.source_ip,
        "event_type": inc.event_type,
        "severity": inc.severity,
        "category": inc.category,
        "raw_payload": inc.raw_payload or {},
        "first_seen_epoch": inc.first_seen_epoch,
        "last_seen_epoch": inc.last_seen_epoch,
        "prompt_version_number": req.policy_version_number or 1,
        "contract_version": contract.status if contract else "UNVERIFIED",
    }

    sim_srv = PolicySimulationService(db)
    is_prod = getattr(settings, "APP_ENV", "development").lower() in ("production", "prod")

    # Model output (custom, saved real/evaluated output, or explicitly permitted simulation)
    if req.custom_model_output:
        model_output = req.custom_model_output
    elif isinstance(inc.ai_verdict, dict) and inc.ai_verdict.get("verdict") and not (inc.ai_verdict.get("is_simulated") and not req.allow_simulation):
        model_output = {
            "verdict": inc.ai_verdict.get("proposed_verdict") or inc.ai_verdict.get("verdict"),
            "confidence": inc.ai_verdict.get("raw_model_confidence") or inc.ai_verdict.get("confidence") or 0.0,
            "reason": inc.ai_verdict.get("reason", ""),
            "supporting_claims": inc.ai_verdict.get("supporting_claims") or [],
            "supporting_evidence": inc.ai_verdict.get("supporting_evidence") or [],
            "model_identifier": inc.ai_verdict.get("model_identifier", "stored-verdict"),
            "is_simulated": bool(inc.ai_verdict.get("is_simulated", False)),
        }
    elif is_prod or not req.allow_simulation:
        raise HTTPException(
            status_code=400,
            detail="Simulated trust evaluation is disabled in production or when allow_simulation=False without stored verdict or custom_model_output.",
        )
    else:
        model_output = sim_srv._simulate_model_output(inc_payload, contract)

    # Query real rule-level historical empirical stats (no fabricated samples or 85% accuracy)
    hist_stats = await sim_srv.get_rule_calibration_stats(rule_id)

    # 3. Evaluate Trust Score
    trust_res = VerdictTrustworthinessEngine.evaluate_verdict_trust(
        incident_payload=inc_payload,
        model_output=model_output,
        contract=contract,
        historical_sample_count=int(hist_stats.get("sample_count", 0)),
        historical_accuracy=hist_stats.get("accuracy"),
        is_calibrated=bool(hist_stats.get("is_calibrated", False)),
    )

    # 4. Persist Evidence Sufficiency & Trust Records
    if trust_res.evidence_sufficiency is not None:
        suff = trust_res.evidence_sufficiency
        suff_rec = EvidenceSufficiencyAssessmentRecord(
            incident_id=inc.incident_id,
            rule_id=rule_id,
            archetype=suff.archetype,
            overall_sufficiency_score=suff.overall_sufficiency_score,
            required_coverage_score=suff.required_coverage_score,
            integrity_provenance_score=suff.integrity_provenance_score,
            consistency_corroboration_score=suff.consistency_corroboration_score,
            freshness_relevance_score=suff.freshness_relevance_score,
            evidence_status=suff.evidence_status.value,
            mandatory_fields_present=suff.mandatory_fields_present,
            mandatory_fields_missing=suff.mandatory_fields_missing,
            conditional_fields_evaluated=suff.conditional_fields_evaluated,
            optional_enrichment_present=suff.optional_enrichment_present,
            unsupported_fields_requested=suff.unsupported_fields_requested,
            contradictions_detected=suff.contradictions_detected,
            evaluated_at=datetime.utcnow(),
        )
        db.add(suff_rec)

    record = VerdictTrustAssessmentRecord(
        incident_id=inc.incident_id,
        rule_id=rule_id,
        archetype=trust_res.archetype,
        suggested_verdict=trust_res.suggested_verdict,
        effective_verdict=trust_res.effective_verdict.value,
        trust_score=trust_res.trust_score,
        raw_trust_score=trust_res.raw_trust_score,
        evidence_sufficiency_score=trust_res.evidence_sufficiency_score,
        evidence_status=trust_res.evidence_status.value,
        score_dimensions=trust_res.score_dimensions.model_dump(),
        supporting_evidence=trust_res.supporting_evidence,
        contradictory_evidence=trust_res.contradictory_evidence,
        missing_evidence=trust_res.missing_evidence,
        confidence_limitations=trust_res.confidence_limitations,
        historical_validation_status=trust_res.historical_validation_status,
        is_calibrated=trust_res.is_calibrated,
        applicable_policy_version=trust_res.applicable_policy_version,
        applicable_contract_version=trust_res.applicable_contract_version,
        escalation_reason=str(trust_res.escalation_reason)[:256] if trust_res.escalation_reason else None,
        human_readable_explanation=trust_res.human_readable_explanation,
        model_identifier=trust_res.model_identifier,
        is_simulated=trust_res.is_simulated,
        evaluated_at=datetime.utcnow(),
    )
    db.add(record)
    await db.commit()

    return trust_res


@router.get("/incident/{incident_id}/trust", response_model=Optional[VerdictTrustAssessmentResult])
async def get_incident_trust(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """
    Retrieves the most recent persisted trust assessment for an incident.
    """
    q = (
        select(VerdictTrustAssessmentRecord)
        .where(VerdictTrustAssessmentRecord.incident_id == incident_id)
        .order_by(desc(VerdictTrustAssessmentRecord.evaluated_at))
        .limit(1)
    )
    res = await db.execute(q)
    rec = res.scalar_one_or_none()
    if not rec:
        return None

    dims = rec.score_dimensions if isinstance(rec.score_dimensions, dict) and "direct_claim_support" in rec.score_dimensions else {
        "direct_claim_support": 0.0,
        "source_reliability": 0.0,
        "contradiction_handling": 0.0,
        "independent_corroboration": 0.0,
        "historical_validation_support": 0.0,
        "total_raw_score": float(rec.raw_trust_score or 0.0),
    }

    return VerdictTrustAssessmentResult(
        incident_id=rec.incident_id,
        rule_id=rec.rule_id,
        archetype=rec.archetype,
        suggested_verdict=rec.suggested_verdict,
        effective_verdict=rec.effective_verdict,
        trust_score=rec.trust_score,
        trust_status="CALCULATED" if rec.trust_score is not None else "NOT_CALCULABLE",
        raw_trust_score=rec.raw_trust_score,
        evidence_sufficiency_score=rec.evidence_sufficiency_score,
        evidence_status=rec.evidence_status,
        score_dimensions=TrustScoreDimensionBreakdown(**dims),
        supporting_evidence=rec.supporting_evidence or [],
        contradictory_evidence=rec.contradictory_evidence or [],
        missing_evidence=rec.missing_evidence or [],
        confidence_limitations=rec.confidence_limitations or [],
        historical_validation_status=rec.historical_validation_status,
        is_calibrated=rec.is_calibrated,
        calibrated_probability=rec.calibrated_probability,
        applicable_policy_version=rec.applicable_policy_version,
        applicable_contract_version=rec.applicable_contract_version,
        escalation_reason=rec.escalation_reason,
        human_readable_explanation=rec.human_readable_explanation,
        model_identifier=rec.model_identifier,
        is_simulated=rec.is_simulated,
        evaluated_at=rec.evaluated_at,
    )


# --------------------------------------------------------------------------
# 2. Historical Dry-Run Intelligence Evaluation
# --------------------------------------------------------------------------

@router.post("/dry-run/evaluate")
async def start_historical_evaluation(
    req: HistoricalEvaluationRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """
    Executes a historical dry-run intelligence evaluation run across adjudicated SIEM incidents.
    """
    sim_srv = PolicySimulationService(db)
    run_record = await sim_srv.run_dry_run_intelligence_evaluation(
        run_name=req.run_name,
        rule_id=req.rule_id,
        archetype=req.archetype,
        policy_version_id=req.policy_version_id,
        baseline_run_id=req.baseline_run_id,
        sample_limit=req.sample_limit or 50,
        provider_type=req.provider_type,
    )
    return {
        "run_id": run_record.id,
        "run_name": run_record.run_name,
        "status": run_record.status,
        "validation_state": run_record.validation_state,
        "total_cases": run_record.total_cases,
        "evaluated_cases": run_record.evaluated_cases,
        "metrics": run_record.metrics,
        "selective_metrics": run_record.selective_metrics,
        "calibration_metrics": run_record.calibration_metrics,
        "regression_summary": run_record.regression_summary,
    }


def _sanitize_run_metrics(run: HistoricalEvaluationRunRecord) -> Optional[Dict[str, Any]]:
    """Enforces zero-denominator and missing-class honesty on stored run metrics."""
    if run.metrics is None:
        return None
    m = dict(run.metrics)
    if "verified_ground_truth_cases" not in m:
        m["verified_ground_truth_cases"] = int(run.verified_ground_truth_cases or 0)
    tp = int(m.get("true_positives") or 0)
    fp = int(m.get("false_positives") or 0)
    tn = int(m.get("true_negatives") or 0)
    fn = int(m.get("false_negatives") or 0)
    decisive = tp + fp + tn + fn
    verified_n = int(m.get("verified_ground_truth_cases") or 0)
    if verified_n == 0 or decisive == 0:
        m["overall_accuracy"] = None
        m["precision"] = None
        m["recall"] = None
        m["specificity"] = None
        m["balanced_accuracy"] = None
        m["f1_score"] = None
        m["metric_status"] = "NOT_CALCULABLE"
        m["balanced_accuracy_reason"] = (
            "NOT_CALCULABLE: Zero verified ground-truth cases (N=0)."
            if verified_n == 0
            else "NOT_CALCULABLE: Zero decisive automated verdicts (TP+FP+TN+FN = 0)."
        )
    elif m.get("recall") is None or m.get("specificity") is None or (tp + fn) == 0 or (tn + fp) == 0:
        m["balanced_accuracy"] = None
        m["metric_status"] = "PARTIAL"
        m["balanced_accuracy_reason"] = "NOT_CALCULABLE: Requires both non-zero TP (TP+FN > 0) and FP (TN+FP > 0) denominators."
    else:
        m.setdefault("metric_status", "CALCULATED")
    return m


@router.get("/dry-run/runs")
async def list_evaluation_runs(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """
    Lists recent historical dry-run evaluation runs.
    """
    q = select(HistoricalEvaluationRunRecord).order_by(desc(HistoricalEvaluationRunRecord.started_at)).limit(limit)
    res = await db.execute(q)
    runs = res.scalars().all()
    items = []
    for r in runs:
        san = _sanitize_run_metrics(r) or {}
        items.append(
            {
                "id": r.id,
                "run_name": r.run_name,
                "rule_id": r.rule_id,
                "archetype": r.archetype,
                "status": r.status,
                "validation_state": r.validation_state,
                "total_cases": r.total_cases,
                "evaluated_cases": r.evaluated_cases,
                "started_at": r.started_at.isoformat(),
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "overall_accuracy": san.get("overall_accuracy"),
                "automatic_coverage": san.get("automatic_decision_coverage"),
            }
        )
    return items


@router.get("/dry-run/runs/{run_id}")
async def get_evaluation_run_details(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """
    Retrieves comprehensive evaluation run details, metrics, risk-coverage curves,
    and individual incident results.
    """
    q = select(HistoricalEvaluationRunRecord).where(HistoricalEvaluationRunRecord.id == run_id)
    res = await db.execute(q)
    run = res.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found.")

    # Fetch incident results
    q_results = select(HistoricalEvaluationResultRecord).where(HistoricalEvaluationResultRecord.run_id == run_id)
    res_results = await db.execute(q_results)
    results = res_results.scalars().all()

    return {
        "run": {
            "id": run.id,
            "run_name": run.run_name,
            "rule_id": run.rule_id,
            "archetype": run.archetype,
            "status": run.status,
            "validation_state": run.validation_state,
            "total_cases": run.total_cases,
            "evaluated_cases": run.evaluated_cases,
            "verified_ground_truth_cases": run.verified_ground_truth_cases,
            "metrics": _sanitize_run_metrics(run),
            "selective_metrics": run.selective_metrics,
            "calibration_metrics": run.calibration_metrics,
            "regression_summary": run.regression_summary,
            "started_at": run.started_at.isoformat(),
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        },
        "results": [
            {
                "id": r.id,
                "incident_id": r.incident_id,
                "rule_id": r.rule_id,
                "suggested_verdict": r.suggested_verdict,
                "effective_verdict": r.effective_verdict,
                "ground_truth_label": r.ground_truth_label,
                "trust_score": r.trust_score,
                "raw_trust_score": r.raw_trust_score,
                "evidence_sufficiency_score": r.evidence_sufficiency_score,
                "evidence_status": r.evidence_status,
                "is_correct": r.is_correct,
                "is_abstained": r.is_abstained,
                "is_critical_error": r.is_critical_error,
                "claims_summary": r.claims_summary,
                "escalation_reason": r.escalation_reason,
            }
            for r in results
        ]
    }


# --------------------------------------------------------------------------
# 3. Paired Regression Comparison
# --------------------------------------------------------------------------

@router.get("/dry-run/compare", response_model=RegressionComparisonReport)
async def compare_evaluation_runs(
    baseline_run_id: str = Query(...),
    candidate_run_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """
    Executes paired regression comparison between baseline and candidate evaluation runs.
    """
    sim_srv = PolicySimulationService(db)
    report = await sim_srv.compare_runs(baseline_run_id=baseline_run_id, candidate_run_id=candidate_run_id)
    return report


# --------------------------------------------------------------------------
# 4. Dashboard Metrics & Rule-Wise Trustworthiness
# --------------------------------------------------------------------------

@router.get("/metrics/summary")
@router.get("/metrics")
async def get_verdict_trust_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """
    Dashboard A: Overview statistics on evaluated incidents, trust distributions,
    unsupported counts, and abstention volumes.
    """
    q_assess = select(VerdictTrustAssessmentRecord).order_by(desc(VerdictTrustAssessmentRecord.evaluated_at)).limit(200)
    res_assess = await db.execute(q_assess)
    assessments = res_assess.scalars().all()

    total_evaluated = len(assessments)
    tp_count = sum(1 for a in assessments if a.effective_verdict == "TRUE_POSITIVE")
    fp_count = sum(1 for a in assessments if a.effective_verdict == "FALSE_POSITIVE")
    attention_count = sum(1 for a in assessments if a.effective_verdict == "REQUIRES_ANALYST_ATTENTION")

    # Trust Score Distribution 1 to 10
    score_dist = {str(i): 0 for i in range(1, 11)}
    for a in assessments:
        if a.trust_score and 1 <= a.trust_score <= 10:
            score_dist[str(a.trust_score)] += 1

    low_trust_count = sum(1 for a in assessments if a.trust_score and a.trust_score < 7)
    missing_evidence_count = sum(1 for a in assessments if a.missing_evidence)
    conflicting_count = sum(1 for a in assessments if a.evidence_status == "CONFLICTING")

    avg_trust = (sum(a.raw_trust_score for a in assessments) / total_evaluated) if total_evaluated > 0 else None
    avg_sufficiency = (sum(a.evidence_sufficiency_score for a in assessments) / total_evaluated) if total_evaluated > 0 else None

    return {
        "total_evaluated_incidents": total_evaluated,
        "true_positive_recommendations": tp_count,
        "false_positive_recommendations": fp_count,
        "analyst_attention_decisions": attention_count,
        "average_trust_score": round(avg_trust / 10.0, 1) if avg_trust is not None else None,
        "average_sufficiency_score": round(avg_sufficiency, 1) if avg_sufficiency is not None else None,
        "trust_score_distribution": score_dist,
        "low_trust_verdicts_count": low_trust_count,
        "missing_evidence_count": missing_evidence_count,
        "conflicting_evidence_count": conflicting_count,
    }


@router.get("/metrics/rule-wise")
async def get_rule_wise_trustworthiness(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """
    Dashboard C: Searchable table of rule-level and archetype-level trust,
    sufficiency, measured accuracy, and validation status.
    """
    # Query rules and their assessment aggregates
    q_rules = select(Rule).limit(100)
    res_rules = await db.execute(q_rules)
    rules = res_rules.scalars().all()

    # Query latest assessments
    q_assess = select(VerdictTrustAssessmentRecord).order_by(desc(VerdictTrustAssessmentRecord.evaluated_at))
    res_assess = await db.execute(q_assess)
    assessments = res_assess.scalars().all()

    # Query latest evaluation run results
    q_runs = select(HistoricalEvaluationRunRecord).order_by(desc(HistoricalEvaluationRunRecord.started_at)).limit(10)
    res_runs = await db.execute(q_runs)
    runs = res_runs.scalars().all()

    assess_by_rule: Dict[str, List[VerdictTrustAssessmentRecord]] = {}
    for a in assessments:
        assess_by_rule.setdefault(a.rule_id, []).append(a)

    items = []
    for r in rules:
        r_assess = assess_by_rule.get(r.id, []) or assess_by_rule.get(r.rule_id, [])
        inc_count = len(r_assess)
        if inc_count > 0:
            avg_trust = round(sum(a.raw_trust_score for a in r_assess) / inc_count / 10.0, 1)
            avg_suff = round(sum(a.evidence_sufficiency_score for a in r_assess) / inc_count, 1)
            abstain_count = sum(1 for a in r_assess if a.effective_verdict == "REQUIRES_ANALYST_ATTENTION")
            abstain_rate = round((abstain_count / inc_count) * 100.0, 1)
            arch = r_assess[0].archetype
        else:
            avg_trust = None
            avg_suff = None
            abstain_rate = None
            arch = r.event_type or "UNKNOWN"

        # Find matching run if any
        matching_run = next((run for run in runs if run.rule_id in (r.id, r.rule_id)), None)
        if matching_run and matching_run.metrics:
            san_metrics = _sanitize_run_metrics(matching_run) or {}
            measured_acc = san_metrics.get("overall_accuracy")
            tp_recall = san_metrics.get("recall")
            fp_spec = san_metrics.get("specificity")
            val_state = matching_run.validation_state
        else:
            measured_acc = None
            tp_recall = None
            fp_spec = None
            val_state = "UNCALIBRATED" if inc_count > 0 else "NO_DATA"

        items.append({
            "rule_id": r.rule_id or r.id,
            "rule_name": r.name,
            "archetype": arch,
            "incident_count": inc_count,
            "average_trust_score": avg_trust,
            "evidence_sufficiency": avg_suff,
            "measured_accuracy": round(measured_acc * 100.0, 1) if measured_acc is not None else None,
            "tp_recall": round(tp_recall * 100.0, 1) if tp_recall is not None else None,
            "fp_specificity": round(fp_spec * 100.0, 1) if fp_spec is not None else None,
            "abstention_rate": abstain_rate,
            "validation_status": val_state,
        })

    return items


# --------------------------------------------------------------------------
# 5. Export Reports (JSON & CSV)
# --------------------------------------------------------------------------

@router.get("/export")
async def export_evaluation_report(
    run_id: Optional[str] = None,
    format: str = Query("json", pattern="^(json|csv)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """
    Exports evaluation run results, metrics, and incident explanations as JSON or CSV.
    """
    if run_id:
        q = select(HistoricalEvaluationRunRecord).where(HistoricalEvaluationRunRecord.id == run_id)
        res = await db.execute(q)
        run = res.scalar_one_or_none()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found.")

        q_res = select(HistoricalEvaluationResultRecord).where(HistoricalEvaluationResultRecord.run_id == run_id)
        res_results = await db.execute(q_res)
        results = res_results.scalars().all()
    else:
        q_res = select(HistoricalEvaluationResultRecord).order_by(desc(HistoricalEvaluationResultRecord.created_at)).limit(200)
        res_results = await db.execute(q_res)
        results = res_results.scalars().all()
        run = None

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "incident_id", "rule_id", "suggested_verdict", "effective_verdict",
            "ground_truth_label", "trust_score", "raw_trust_score",
            "evidence_sufficiency_score", "evidence_status", "is_correct", "is_abstained",
            "is_critical_error", "escalation_reason"
        ])
        for r in results:
            writer.writerow([
                r.incident_id, r.rule_id, r.suggested_verdict, r.effective_verdict,
                r.ground_truth_label or "", r.trust_score or "", r.raw_trust_score,
                r.evidence_sufficiency_score, r.evidence_status, r.is_correct if r.is_correct is not None else "",
                r.is_abstained, r.is_critical_error, r.escalation_reason or ""
            ])
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=verdict_validation_{run_id or 'all'}.csv"}
        )
    else:
        export_data = {
            "run": {
                "id": run.id if run else "aggregate",
                "run_name": run.run_name if run else "Aggregate Results",
                "validation_state": run.validation_state if run else "N/A",
                "metrics": run.metrics if run else {},
                "selective_metrics": run.selective_metrics if run else [],
                "calibration_metrics": run.calibration_metrics if run else {},
            },
            "results": [
                {
                    "incident_id": r.incident_id,
                    "rule_id": r.rule_id,
                    "suggested_verdict": r.suggested_verdict,
                    "effective_verdict": r.effective_verdict,
                    "ground_truth_label": r.ground_truth_label,
                    "trust_score": r.trust_score,
                    "raw_trust_score": r.raw_trust_score,
                    "evidence_sufficiency_score": r.evidence_sufficiency_score,
                    "evidence_status": r.evidence_status,
                    "is_correct": r.is_correct,
                    "is_abstained": r.is_abstained,
                    "is_critical_error": r.is_critical_error,
                    "escalation_reason": r.escalation_reason,
                }
                for r in results
            ]
        }
        return Response(
            content=json.dumps(export_data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=verdict_validation_{run_id or 'all'}.json"}
        )
