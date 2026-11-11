import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict

import pytest
from httpx import AsyncClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.incident import HistoricalGroundTruth, Incident, IncidentEvent
from app.models.investigation import Investigation
from app.models.prompt import PromptVersion, RulePrompt
from app.models.rule import Rule
from app.models.rule_intelligence import RuleIntelligenceSnapshot
from app.models.user import User
from app.models.verdict_intelligence import (
    HistoricalEvaluationResultRecord,
    HistoricalEvaluationRunRecord,
    VerdictTrustAssessmentRecord,
)
from app.services.empirical_accuracy_evaluator import EmpiricalAccuracyEvaluator
from app.services.model_provider.openai_compatible import OpenAICompatibleProvider
from app.services.verdict_trustworthiness_engine import VerdictTrustworthinessEngine


def _auth_header(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _seed_rule_with_policy(
    db: AsyncSession,
    rule_id_str: str = "P9-RULE-001",
    approved: bool = True,
    archetype: str = "PROCESS_EXECUTION",
):
    rule = Rule(
        rule_id=rule_id_str,
        name=f"Rule {rule_id_str}",
        event_type=rule_id_str,
        severity="HIGH",
        description="Phase 9 test rule",
        data_source="FortiSIEM",
        status="ACTIVE",
    )
    db.add(rule)
    await db.flush()

    snap = RuleIntelligenceSnapshot(
        rule_id=rule.id,
        rule_identifier=rule.rule_id,
        primary_archetype=archetype,
        definition_status="COMPLETE",
        source_provenance="TEST",
    )
    db.add(snap)

    rp = RulePrompt(rule_id=rule.id)
    db.add(rp)
    await db.flush()

    pv = PromptVersion(
        prompt_id=rp.id,
        version_number=1,
        status="APPROVED" if approved else "DRAFT",
        is_template_draft=False,
        quality_status="PASSED" if approved else "GENERATED_DRAFT",
        quality_score=95.0 if approved else 60.0,
        common_prompt="Standard SOC baseline.",
        rule_specific_prompt="Validate host command execution lineage.",
        detection_conditions="powershell encoded command",
        required_evidence="source_ip, host_name, process_name, command_line",
        tp_indicators="Encoded payload + suspicious parent",
        fp_indicators="Signed admin script",
        missing_info_criteria="Missing command_line",
        escalation_conditions="Any unverified privilege execution",
        analyst_questions=["Confirm parent PID?"],
        change_summary="Phase 9 test policy",
    )
    db.add(pv)
    await db.flush()
    if approved:
        rp.active_version_id = pv.id
        db.add(rp)
    await db.commit()
    return rule, rp, pv


async def _seed_incident(
    db: AsyncSession,
    inc_code: str,
    rule: Rule,
    severity: str = "HIGH",
    verified_gt: str | None = None,
    ai_verdict: dict | None = None,
    epoch_ts: int | None = None,
):
    ep = epoch_ts or int(time.time())
    inc = Incident(
        incident_id=inc_code,
        rule_id=rule.id,
        event_type=rule.event_type,
        title=f"Incident {inc_code}",
        severity=severity,
        status_code=1,
        status_name="Active",
        category="Endpoint",
        source_ip="192.0.2.50",
        reporting_ip="198.51.100.10",
        reporting_device="WORKSTATION-P9",
        first_seen_epoch=ep,
        created_at_epoch=ep,
        raw_payload={"source_ip": "192.0.2.50", "host_name": "WORKSTATION-P9", "process_name": "powershell.exe", "command_line": "powershell -enc AAAA"},
        ai_verdict=ai_verdict,
    )
    db.add(inc)
    await db.flush()

    ev = IncidentEvent(
        incident_id=inc.id,
        event_id=f"EV-{inc_code}",
        event_type=rule.event_type,
        raw_log="powershell.exe -enc AAAA",
        attributes={"source_ip": "192.0.2.50", "host_name": "WORKSTATION-P9", "process_name": "powershell.exe", "command_line": "powershell -enc AAAA"},
    )
    db.add(ev)

    if verified_gt:
        gt = HistoricalGroundTruth(
            incident_id=inc.id,
            resolution=verified_gt,
            comments="Verified by independent Tier-3 analyst review.",
            cleared_user="tier3_supervisor",
            cleared_reason="Confirmed malicious / benign",
            is_ml_generated=False,
        )
        db.add(gt)

    await db.commit()
    return inc


# =========================================================================
# STAGE 1 MANDATORY FINAL CHECKS: REGRESSION TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_issue1_decision_coverage_legacy_and_zero_denominator_sanitized(
    client: AsyncClient, db_session: AsyncSession, analyst_token: str
):
    """Issue 1 Regression: zero verified/decisive cases must NEVER display stale 50% automatic decision coverage."""
    empty_metrics = EmpiricalAccuracyEvaluator.evaluate_performance([])
    assert empty_metrics.automatic_decision_coverage is None
    assert empty_metrics.analyst_attention_rate is None

    legacy_run = HistoricalEvaluationRunRecord(
        id="RUN-LEGACY-COV50",
        run_name="Legacy Partial Coverage Run",
        status="COMPLETED",
        validation_state="INSUFFICIENT_DATA",
        total_cases=20,
        evaluated_cases=20,
        verified_ground_truth_cases=0,
        metrics={
            "balanced_accuracy": None,
            "automatic_decision_coverage": 0.5,
            "analyst_attention_rate": 0.5,
            "verified_ground_truth_cases": 0,
            "critical_false_negatives": 0,
        },
    )
    all_abstain_run = HistoricalEvaluationRunRecord(
        id="RUN-ZERO-DECISIVE",
        run_name="Zero Decisive Run",
        status="COMPLETED",
        validation_state="INSUFFICIENT_DATA",
        total_cases=4,
        evaluated_cases=4,
        verified_ground_truth_cases=4,
        metrics={
            "true_positives": 0,
            "false_positives": 0,
            "true_negatives": 0,
            "false_negatives": 0,
            "total_evaluated_cases": 4,
            "verified_ground_truth_cases": 4,
            "abstention_count": 4,
            "automatic_decision_coverage": 0.5,
            "analyst_attention_rate": 1.0,
        },
    )
    db_session.add(legacy_run)
    db_session.add(all_abstain_run)
    await db_session.commit()

    # Check list runs endpoint
    list_res = await client.get("/api/verdict-intelligence/dry-run/runs", headers=_auth_header(analyst_token))
    assert list_res.status_code == 200
    by_id_list = {r["id"]: r["automatic_coverage"] for r in list_res.json()}
    assert by_id_list["RUN-LEGACY-COV50"] is None
    assert by_id_list["RUN-ZERO-DECISIVE"] == 0.0

    # Check detail endpoint
    det_res = await client.get("/api/verdict-intelligence/dry-run/runs/RUN-LEGACY-COV50", headers=_auth_header(analyst_token))
    assert det_res.status_code == 200
    assert det_res.json()["run"]["metrics"]["automatic_decision_coverage"] is None
    assert det_res.json()["run"]["metrics"]["analyst_attention_rate"] is None

    # Check export endpoint also sanitizes!
    exp_res = await client.get("/api/verdict-intelligence/export?run_id=RUN-LEGACY-COV50&format=json", headers=_auth_header(analyst_token))
    assert exp_res.status_code == 200
    assert exp_res.json()["run"]["metrics"]["automatic_decision_coverage"] is None


@pytest.mark.asyncio
async def test_issue2_uncalibrated_trust_capped_with_historical_provenance(
    client: AsyncClient, db_session: AsyncSession, analyst_token: str
):
    """
    Issue 2 Regression: Legacy uncalibrated trust_score=8 must be presented as <=6/10
    while preserving historical_trust_score=8 provenance and never silently overwriting DB.
    """
    t_res = VerdictTrustworthinessEngine.compute_trust_score(
        rule_id="P9-TRUST-001",
        effective_verdict="TRUE_POSITIVE",
        proposed_verdict="TRUE_POSITIVE",
        historical_sample_size=50,
        historical_accuracy=None,
        is_calibrated=None,
    )
    assert t_res.is_calibrated is False
    assert (t_res.trust_score or 0) <= 6

    rule, _, _ = await _seed_rule_with_policy(db_session, rule_id_str="P9-TRUST-001")
    inc = await _seed_incident(
        db_session,
        inc_code="INC-LEGACY-TRUST8",
        rule=rule,
        ai_verdict={
            "verdict": "TRUE_POSITIVE",
            "proposed_verdict": "TRUE_POSITIVE",
            "trust_score": 8,
            "is_calibrated": False,
            "calibration_status": "UNCALIBRATED_ORDINAL",
            "validation_status": "VALIDATED",
            "model_identifier": "legacy-model-v1",
            "is_simulated": True,
        },
    )
    assess = VerdictTrustAssessmentRecord(
        incident_id=inc.incident_id,
        rule_id=rule.rule_id,
        archetype="PROCESS_EXECUTION",
        suggested_verdict="TRUE_POSITIVE",
        effective_verdict="TRUE_POSITIVE",
        trust_score=8,
        raw_trust_score=82.0,
        evidence_sufficiency_score=100.0,
        evidence_status="SUFFICIENT",
        supporting_evidence=["source_ip=192.0.2.50"],
        historical_validation_status="INSUFFICIENT_HISTORICAL_DATA",
        is_calibrated=False,
        model_identifier="legacy-model-v1",
        is_simulated=True,
    )
    run_rec = HistoricalEvaluationRunRecord(
        id="RUN-LEGACY-TRUST8",
        run_name="Legacy Uncalibrated 8 Run",
        status="COMPLETED",
        validation_state="INSUFFICIENT_DATA",
        total_cases=1,
        evaluated_cases=1,
        verified_ground_truth_cases=1,
        metrics={"true_positives": 1, "false_positives": 0, "true_negatives": 0, "false_negatives": 0},
        calibration_metrics={"status": "NOT_CALIBRATED", "is_calibrated": False},
    )
    db_session.add(assess)
    db_session.add(run_rec)
    await db_session.flush()
    db_session.add(
        HistoricalEvaluationResultRecord(
            run_id="RUN-LEGACY-TRUST8",
            incident_id=inc.incident_id,
            rule_id=rule.rule_id,
            suggested_verdict="TRUE_POSITIVE",
            effective_verdict="TRUE_POSITIVE",
            trust_score=8,
            raw_trust_score=82.0,
            evidence_sufficiency_score=100.0,
            evidence_status="SUFFICIENT",
        )
    )
    await db_session.commit()

    # 1. Incident detail API returns capped trust=6 and historical_trust_score=8
    inc_res = await client.get(f"/api/incidents/{inc.id}", headers=_auth_header(analyst_token))
    assert inc_res.status_code == 200
    v = inc_res.json()["ai_verdict"]
    assert v["trust_score"] == 6
    assert v["historical_trust_score"] == 8
    assert v["trust_cap_applied"] is True

    # Verify DB JSON column was NOT destructively overwritten
    await db_session.refresh(inc)
    assert inc.ai_verdict["trust_score"] == 8

    # 2. Trust drilldown & Overview & Rules aggregate capped <=6 scores
    tr_res = await client.get(f"/api/verdict-intelligence/incident/{inc.incident_id}/trust", headers=_auth_header(analyst_token))
    assert tr_res.status_code == 200
    assert tr_res.json()["trust_score"] == 6
    assert tr_res.json()["historical_trust_score"] == 8
    assert tr_res.json()["trust_cap_applied"] is True

    ov_res = await client.get("/api/verdict-intelligence/metrics/summary", headers=_auth_header(analyst_token))
    assert ov_res.status_code == 200
    assert ov_res.json()["average_trust_score"] == 6.0

    rules_res = await client.get("/api/verdict-intelligence/metrics/rule-wise", headers=_auth_header(analyst_token))
    assert rules_res.status_code == 200
    assert rules_res.json()[0]["average_trust_score"] == 6.0

    # 3. Historical run drilldown results normalized
    run_res = await client.get("/api/verdict-intelligence/dry-run/runs/RUN-LEGACY-TRUST8", headers=_auth_header(analyst_token))
    assert run_res.status_code == 200
    c0 = run_res.json()["results"][0]
    assert c0["trust_score"] == 6
    assert c0["historical_trust_score"] == 8


# =========================================================================
# STAGE 2-5: SOC PILOT GOVERNANCE, SHADOW / ANALYST_ASSISTED & RBAC
# =========================================================================

@pytest.mark.asyncio
async def test_pilot_default_disabled_safety_blocks_and_rbac(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, analyst_token: str, viewer_token: str
):
    """Verify Pilot defaults to DISABLED, blocks dangerous flags, and enforces strict 3-role RBAC."""
    res = await client.get("/api/pilot/config", headers=_auth_header(viewer_token))
    assert res.status_code == 200
    cfg = res.json()
    assert cfg["mode"] == "DISABLED"
    assert cfg["is_paused"] is False
    assert cfg["allow_external_writeback"] is False
    assert cfg["allow_auto_incident_closure"] is False

    assert (await client.post("/api/pilot/run-batch", json={"max_batch": 5}, headers=_auth_header(viewer_token))).status_code == 403
    assert (await client.post("/api/pilot/activate", json={"mode": "SHADOW", "change_reason": "test"}, headers=_auth_header(viewer_token))).status_code == 403

    assert (await client.put("/api/pilot/config", json={"pilot_name": "Hack", "change_reason": "test"}, headers=_auth_header(analyst_token))).status_code == 403
    assert (await client.post("/api/pilot/activate", json={"mode": "SHADOW", "change_reason": "test"}, headers=_auth_header(analyst_token))).status_code == 403
    assert (await client.post("/api/pilot/pause", json={"reason": "test"}, headers=_auth_header(analyst_token))).status_code == 403
    assert (await client.post("/api/pilot/disable", json={"reason": "test"}, headers=_auth_header(analyst_token))).status_code == 403

    bad1 = await client.put(
        "/api/pilot/config",
        json={"pilot_name": "Unsafe Pilot", "allow_external_writeback": True, "change_reason": "unsafe"},
        headers=_auth_header(admin_token),
    )
    assert bad1.status_code == 422
    bad2 = await client.put(
        "/api/pilot/config",
        json={"pilot_name": "Unsafe Pilot 2", "allow_auto_incident_closure": True, "change_reason": "unsafe"},
        headers=_auth_header(admin_token),
    )
    assert bad2.status_code == 422

    batch_dis = await client.post("/api/pilot/run-batch", json={"max_batch": 5}, headers=_auth_header(analyst_token))
    assert batch_dis.status_code == 200
    assert batch_dis.json()["status"] == "SKIPPED"
    assert batch_dis.json()["reason"] == "PILOT_DISABLED"


@pytest.mark.asyncio
async def test_pilot_shadow_isolation_idempotency_budgets_and_rollback(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, analyst_token: str
):
    """Verify SHADOW mode keeps Incident.ai_verdict & Investigation clean, enforces budgets/rules & idempotency."""
    rule_in, _, _ = await _seed_rule_with_policy(db_session, rule_id_str="P9-SCOPE-IN", approved=True)
    rule_out, _, _ = await _seed_rule_with_policy(db_session, rule_id_str="P9-SCOPE-OUT", approved=True)
    inc_in = await _seed_incident(db_session, "INC-P9-SHADOW-1", rule_in, severity="HIGH")
    inc_in2 = await _seed_incident(db_session, "INC-P9-SHADOW-2", rule_in, severity="HIGH")
    inc_out = await _seed_incident(db_session, "INC-P9-OUT-1", rule_out, severity="HIGH")
    inc_low = await _seed_incident(db_session, "INC-P9-LOW-1", rule_in, severity="LOW")

    upd = await client.put(
        "/api/pilot/config",
        json={
            "pilot_name": "Phase 9 Shadow Scope Test",
            "mode": "SHADOW",
            "selected_rule_ids": ["P9-SCOPE-IN"],
            "included_severities": ["CRITICAL", "HIGH"],
            "hourly_evaluation_budget": 1,
            "daily_evaluation_budget": 10,
            "change_reason": "Enable narrow SHADOW pilot for P9-SCOPE-IN",
        },
        headers=_auth_header(admin_token),
    )
    assert upd.status_code == 200
    assert upd.json()["version_number"] == 2

    res_out = await client.post(
        f"/api/pilot/evaluate/{inc_out.incident_id}?source_type=HISTORICAL&allow_simulated=true",
        headers=_auth_header(analyst_token),
    )
    assert res_out.status_code == 200
    assert res_out.json()["status"] == "SKIPPED"
    assert res_out.json()["reason"] == "RULE_NOT_IN_PILOT_SCOPE"

    res_low = await client.post(
        f"/api/pilot/evaluate/{inc_low.incident_id}?source_type=HISTORICAL&allow_simulated=true",
        headers=_auth_header(analyst_token),
    )
    assert res_low.status_code == 200
    assert "SEVERITY_EXCLUDED" in res_low.json()["reason"]

    res_1 = await client.post(
        f"/api/pilot/evaluate/{inc_in.incident_id}?source_type=HISTORICAL&allow_simulated=true",
        headers=_auth_header(analyst_token),
    )
    assert res_1.status_code == 200
    assert res_1.json()["status"] in ("EVALUATED", "ABSTAINED")
    assert res_1.json()["execution_mode"] == "SHADOW"

    await db_session.refresh(inc_in)
    assert inc_in.ai_verdict is None

    res_budget = await client.post(
        f"/api/pilot/evaluate/{inc_in2.incident_id}?source_type=HISTORICAL&allow_simulated=true",
        headers=_auth_header(analyst_token),
    )
    assert res_budget.status_code == 200
    assert res_budget.json()["status"] == "SKIPPED"
    assert res_budget.json()["reason"] == "HOURLY_BUDGET_EXCEEDED"

    await client.put(
        "/api/pilot/config",
        json={
            "pilot_name": "Phase 9 Shadow Scope Test",
            "mode": "SHADOW",
            "selected_rule_ids": ["P9-SCOPE-IN"],
            "included_severities": ["CRITICAL", "HIGH"],
            "hourly_evaluation_budget": 10,
            "daily_evaluation_budget": 10,
            "change_reason": "Expand hourly budget",
        },
        headers=_auth_header(admin_token),
    )
    res_idem = await client.post(
        f"/api/pilot/evaluate/{inc_in.incident_id}?source_type=HISTORICAL&allow_simulated=true",
        headers=_auth_header(analyst_token),
    )
    assert res_idem.status_code == 200
    assert res_idem.json()["status"] == "IDEMPOTENT_SKIP"

    rb = await client.post("/api/pilot/rollback", json={"target_version": 1, "reason": "Rollback test"}, headers=_auth_header(admin_token))
    assert rb.status_code == 200
    assert rb.json()["mode"] == "DISABLED"

    evals = await client.get("/api/pilot/evaluations", headers=_auth_header(analyst_token))
    assert evals.status_code == 200
    assert len(evals.json()) >= 1

    aud = await client.get("/api/pilot/audit", headers=_auth_header(analyst_token))
    assert aud.status_code == 200
    assert len(aud.json()["items"]) >= 3

    met = await client.get("/api/pilot/metrics", headers=_auth_header(analyst_token))
    assert met.status_code == 200
    mdata = met.json()
    assert mdata["operational"]["simulated_evaluations_excluded_count"] >= 1
    assert mdata["empirical_accuracy"]["balanced_accuracy"] is None
    assert mdata["empirical_accuracy"]["metric_status"] == "NOT_CALCULABLE"


@pytest.mark.asyncio
async def test_live_source_blocks_mock_fallback_and_auto_pauses(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, analyst_token: str, monkeypatch
):
    """Verify LIVE jobs NEVER use simulated fallback and consecutive provider outages auto-pause pilot."""
    rule, _, _ = await _seed_rule_with_policy(db_session, rule_id_str="P9-LIVE-001", approved=True)
    inc1 = await _seed_incident(db_session, "INC-P9-LIVE-1", rule)
    inc2 = await _seed_incident(db_session, "INC-P9-LIVE-2", rule)

    monkeypatch.setattr(settings, "LOCAL_LLM_BASE_URL", "http://127.0.0.1:59999/v1")
    await client.put(
        "/api/pilot/config",
        json={
            "pilot_name": "Live Resilience Test",
            "mode": "SHADOW",
            "error_handling_policy": "PAUSE_ON_CONSECUTIVE_ERRORS",
            "consecutive_error_pause_threshold": 2,
            "change_reason": "Configure auto-pause at 2 errors",
        },
        headers=_auth_header(admin_token),
    )

    r1 = await client.post(
        f"/api/pilot/evaluate/{inc1.incident_id}?source_type=LIVE&allow_simulated=true",
        headers=_auth_header(analyst_token),
    )
    assert r1.status_code == 200
    assert r1.json()["status"] == "FAILED"
    assert "SERVER2_OFFLINE" in r1.json()["error"]
    assert r1.json()["auto_paused"] is False

    r2 = await client.post(
        "/api/pilot/evaluate/INC-P9-LIVE-2?source_type=LIVE&allow_simulated=true",
        headers=_auth_header(analyst_token),
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "FAILED"
    assert r2.json()["auto_paused"] is True

    cfg_after = (await client.get("/api/pilot/config", headers=_auth_header(admin_token))).json()
    assert cfg_after["is_paused"] is True


@pytest.mark.asyncio
async def test_analyst_assisted_assurance_override_and_supervisor_gate(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str, analyst_token: str
):
    """Verify Stage 4: Human Review Queue AI Assurance, non-destructive override, and self-verification block."""
    rule, _, pv = await _seed_rule_with_policy(db_session, rule_id_str="P9-ASSIST-001", approved=True)
    inc = await _seed_incident(db_session, "INC-P9-ASSIST-1", rule)

    inv = Investigation(incident_id=inc.id, status="PENDING_REVIEW")
    db_session.add(inv)
    await db_session.commit()

    await client.post(
        "/api/pilot/activate",
        json={"mode": "ANALYST_ASSISTED", "change_reason": "Enable Analyst Assisted Review"},
        headers=_auth_header(admin_token),
    )

    ev_res = await client.post(
        f"/api/pilot/evaluate/{inc.incident_id}?source_type=HISTORICAL&allow_simulated=true",
        headers=_auth_header(analyst_token),
    )
    assert ev_res.status_code == 200
    eval_id = ev_res.json()["evaluation_id"]

    det = await client.get(f"/api/investigations/{inv.id}", headers=_auth_header(analyst_token))
    assert det.status_code == 200
    assurance = det.json()["ai_assurance"]
    assert assurance is not None
    assert assurance["policy_version_number"] == pv.version_number
    assert assurance["pilot_mode"] == "ANALYST_ASSISTED"
    assert assurance["supervisor_verified"] is False
    orig_validated = assurance["validated_verdict"]

    sub = await client.post(
        f"/api/investigations/{inv.id}/verdict",
        json={
            "analyst_verdict": "FALSE_POSITIVE",
            "verdict_reason": "Confirmed benign scheduled IT admin task",
            "analyst_notes": "Checked host change ticket CHG-9001",
            "is_disputed": False,
            "is_independently_verified": False,
            "status": "REVIEWED",
            "action_type": "OVERRIDDEN",
        },
        headers=_auth_header(analyst_token),
    )
    assert sub.status_code == 200

    evals = (await client.get("/api/pilot/evaluations", headers=_auth_header(analyst_token))).json()
    target_ev = next(x for x in evals if x["id"] == eval_id)
    assert target_ev["validated_verdict"] == orig_validated
    assert target_ev["analyst_feedback_action"] == "OVERRIDDEN"
    assert target_ev["analyst_decision"] == "FALSE_POSITIVE"
    assert target_ev["analyst_user"] == "analyst_test"
    assert target_ev["supervisor_verified"] is False

    sup_ok = await client.post(
        f"/api/pilot/evaluations/{eval_id}/supervisor-verify",
        json={"approved": True, "notes": "Reviewed ticket CHG-9001 and confirmed override."},
        headers=_auth_header(admin_token),
    )
    assert sup_ok.status_code == 200
    assert sup_ok.json()["supervisor_verified"] is True
    assert sup_ok.json()["supervisor_user"] == admin_user.username

    await client.post(
        f"/api/pilot/evaluations/{eval_id}/feedback",
        json={"action": "ACCEPTED", "analyst_decision": "TRUE_POSITIVE", "reason": "Admin testing self-verify guard"},
        headers=_auth_header(admin_token),
    )
    self_sup = await client.post(
        f"/api/pilot/evaluations/{eval_id}/supervisor-verify",
        json={"approved": True, "notes": "Attempt self verify"},
        headers=_auth_header(admin_token),
    )
    assert self_sup.status_code == 400
    assert "SELF_VERIFICATION_PROHIBITED" in self_sup.json()["detail"]


# =========================================================================
# STAGE 7-10: ELIGIBILITY REPORT, TIME-AWARE REPLAY, CONFIGURABLE PROVIDER & MIGRATION
# =========================================================================

@pytest.mark.asyncio
async def test_historical_eligibility_report_and_chronological_replay(
    client: AsyncClient, db_session: AsyncSession, analyst_token: str
):
    """Verify HistoricalEligibilityService JSON/CSV reports and epoch/partition replay filters."""
    rule, _, _ = await _seed_rule_with_policy(db_session, rule_id_str="P9-ELIG-001", approved=True)
    await _seed_incident(db_session, "INC-ELIG-OLD-TP", rule, verified_gt="True Positive", epoch_ts=1700000000)
    await _seed_incident(db_session, "INC-ELIG-NEW-FP", rule, verified_gt="False Positive", epoch_ts=1750000000)

    rep_res = await client.get("/api/verdict-intelligence/eligibility-report", headers=_auth_header(analyst_token))
    assert rep_res.status_code == 200
    rep = rep_res.json()
    assert rep["summary"]["available_incident_count"] == 2
    assert rep["summary"]["verified_tp_count"] == 1
    assert rep["summary"]["verified_fp_count"] == 1
    assert rep["summary"]["g8_eligibility"] == "INSUFFICIENT_DATA"
    assert rep["summary"]["calibration_eligibility"] == "INSUFFICIENT_DATA"

    csv_res = await client.get("/api/pilot/eligibility-report?format=csv", headers=_auth_header(analyst_token))
    assert csv_res.status_code == 200
    assert "P9-ELIG-001" in csv_res.text

    replay_res = await client.post(
        "/api/verdict-intelligence/dry-run/evaluate",
        json={
            "run_name": "Chronological Time-Window Replay",
            "rule_id": "P9-ELIG-001",
            "provider_type": "SIMULATED",
            "after_epoch": 1720000000,
            "sample_limit": 20,
        },
        headers=_auth_header(analyst_token),
    )
    assert replay_res.status_code == 200
    run_id = replay_res.json()["run_id"]
    run_det = (await client.get(f"/api/verdict-intelligence/dry-run/runs/{run_id}", headers=_auth_header(analyst_token))).json()
    assert len(run_det["results"]) == 1
    assert run_det["results"][0]["incident_id"] == "INC-ELIG-NEW-FP"


def test_openai_compatible_provider_honors_configurable_timeout_and_max_tokens():
    """Verify configurable LOCAL_LLM_TIMEOUT and LOCAL_LLM_MAX_TOKENS are NOT clamped at 60s / 350 tokens."""
    p = OpenAICompatibleProvider(
        base_url="http://127.0.0.1:8080/v1",
        model_name="qwen2.5-32b-instruct",
        timeout_seconds=12.5,
        max_tokens=1024,
    )
    assert p.timeout_seconds == 12.5
    assert p.max_tokens == 1024


def test_smoke_test_server2_live_mock_and_unreachable_honesty():
    """Verify smoke_test_server2.py passes against complete HTTP OpenAI mock and returns NOT_EXECUTED offline."""
    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/metrics"):
                body = b"vllm:num_requests_running 0\n"
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path.startswith("/health"):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
                return
            body = json.dumps({"object": "list", "data": [{"id": "mock-qwen"}]}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8", errors="replace")
            req_json = json.loads(raw or "{}")
            if req_json.get("model") == "nonexistent-model-smoke-check":
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":"model not found"}')
                return
            payload = {
                "id": "chatcmpl-test",
                "choices": [{"message": {"content": json.dumps({"verdict": "REQUIRES_ATTENTION", "confidence": 0.5, "reason": "ok"})}}],
                "usage": {"prompt_tokens": 22, "completion_tokens": 11, "total_tokens": 33},
            }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    server = HTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_port
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        repo_root = Path(__file__).resolve().parents[2]
        script = repo_root / "deployment" / "scripts" / "smoke_test_server2.py"

        ok = subprocess.run(
            [sys.executable, str(script), "--base-url", f"http://127.0.0.1:{port}/v1", "--model", "mock-qwen"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert ok.returncode == 0, ok.stdout + ok.stderr
        ok_json = json.loads(ok.stdout)
        assert ok_json["overall_status"] == "PASSED"

        fail = subprocess.run(
            [sys.executable, str(script), "--base-url", "http://127.0.0.1:59998/v1", "--model", "mock-qwen", "--timeout", "1"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert fail.returncode == 2
        fail_json = json.loads(fail.stdout)
        assert fail_json["overall_status"] == "NOT_EXECUTED"
    finally:
        server.shutdown()
        server.server_close()


def test_alembic_008_soc_pilot_upgrade_and_downgrade(tmp_path):
    """Verify Alembic 008_soc_pilot migrates cleanly on SQLite file DB and downgrades cleanly."""
    db_file = tmp_path / "alembic_p9_test.db"
    backend_root = Path(__file__).resolve().parents[1]

    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_file}"

    up = subprocess.run(["alembic", "upgrade", "008_soc_pilot"], cwd=str(backend_root), env=env, capture_output=True, text=True)
    assert up.returncode == 0, up.stderr

    eng = create_engine(f"sqlite:///{db_file}")
    tables = set(inspect(eng).get_table_names())
    assert "pilot_configurations" in tables
    assert "pilot_config_history" in tables
    assert "pilot_evaluations" in tables
    eng.dispose()

    down = subprocess.run(["alembic", "downgrade", "007_distributed_locks"], cwd=str(backend_root), env=env, capture_output=True, text=True)
    assert down.returncode == 0, down.stderr

    eng2 = create_engine(f"sqlite:///{db_file}")
    tables_after = set(inspect(eng2).get_table_names())
    assert "pilot_configurations" not in tables_after
    assert "pilot_evaluations" not in tables_after
    eng2.dispose()
