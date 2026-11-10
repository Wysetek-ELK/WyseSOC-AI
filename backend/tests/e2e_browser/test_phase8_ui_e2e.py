"""
Phase 8 Stage 7: Real Headless Chromium Frontend E2E Test Suite (Playwright).

Spins up an isolated Alembic-migrated SQLite database, a real FastAPI uvicorn
server on 127.0.0.1:8000, and the compiled Next.js production server on
127.0.0.1:3000, then exercises the core analyst and admin workflows in headless
Chromium while recording screenshots, browser trace ZIP, and JSON results under
docs/phase8/evidence/.
"""

import asyncio
import json
import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

import pytest
from playwright.sync_api import expect, sync_playwright
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"
EVIDENCE_DIR = REPO_ROOT / "docs" / "phase8" / "evidence"
SCREENSHOTS_DIR = EVIDENCE_DIR / "screenshots"
TRACES_DIR = EVIDENCE_DIR / "traces"
RESULTS_DIR = EVIDENCE_DIR / "test-results"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models.incident import HistoricalGroundTruth, Incident  # noqa: E402
from app.models.investigation import Investigation  # noqa: E402
from app.models.prompt import PromptVersion, RulePrompt  # noqa: E402
from app.models.rule import Rule  # noqa: E402
from app.models.rule_intelligence import RuleIntelligenceSnapshot  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.verdict_intelligence import (  # noqa: E402
    EvidenceSufficiencyAssessmentRecord,
    HistoricalEvaluationResultRecord,
    HistoricalEvaluationRunRecord,
    VerdictTrustAssessmentRecord,
)
from app.utils.security import get_password_hash  # noqa: E402


def _assert_port_free(host: str, port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        if s.connect_ex((host, port)) == 0:
            raise RuntimeError(f"Required E2E port {host}:{port} is already in use.")


def _wait_http_ok(
    url: str,
    timeout_s: float = 45.0,
    proc: subprocess.Popen | None = None,
    log_path: Path | None = None,
) -> None:
    deadline = time.time() + timeout_s
    last_err = ""
    while time.time() < deadline:
        if proc is not None and proc.poll() is not None:
            out = log_path.read_text(encoding="utf-8", errors="replace") if log_path and log_path.exists() else ""
            raise RuntimeError(f"Server exited early (code={proc.returncode}): {out[-2000:]}")
        try:
            with urllib.request.urlopen(url, timeout=8.0) as resp:
                if 200 <= resp.status < 400:
                    return
        except Exception as exc:
            last_err = str(exc)
        time.sleep(0.5)
    raise TimeoutError(f"Timed out waiting for {url} (last error: {last_err})")


async def _seed_e2e_database(db_path: Path) -> Dict[str, str]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    admin_secret = f"E2E-Adm-{secrets.token_hex(6)}!"
    analyst_secret = f"E2E-Anl-{secrets.token_hex(6)}!"
    viewer_secret = f"E2E-Vwr-{secrets.token_hex(6)}!"

    async with SessionLocal() as db:
        admin = User(
            username="admin",
            email="admin-p8@example.com",
            hashed_password=get_password_hash(admin_secret),
            full_name="Phase 8 Administrator",
            role="Administrator",
            is_active=True,
        )
        analyst = User(
            username="analyst",
            email="analyst-p8@example.com",
            hashed_password=get_password_hash(analyst_secret),
            full_name="Phase 8 SOC Analyst",
            role="SOC Analyst",
            is_active=True,
        )
        viewer = User(
            username="viewer",
            email="viewer-p8@example.com",
            hashed_password=get_password_hash(viewer_secret),
            full_name="Phase 8 ReadOnly Viewer",
            role="Read-Only Viewer",
            is_active=True,
        )
        db.add_all([admin, analyst, viewer])
        await db.flush()

        # Rule 1: Complete & Approved Exfiltration Policy
        rule_ok = Rule(
            rule_id="PH_RULE_UI_COMPLETE_EXFIL",
            name="Phase 8 UI Outbound Exfiltration Rule",
            event_type="PH_RULE_UI_COMPLETE_EXFIL",
            severity="HIGH",
            description="Detects large outbound transfers > 1GB",
            pattern_logic="sentBytes64 > 1000000000 AND direction == 'outbound'",
            status="ACTIVE",
            parsed_metadata={"definition_status": "VERIFIED"},
        )
        # Rule 2: Incomplete SIEM Threshold -> G1 Hard Block
        rule_inc = Rule(
            rule_id="PH_RULE_UI_INCOMPLETE_SPEC",
            name="Phase 8 Incomplete Threshold Rule",
            event_type="PH_RULE_UI_INCOMPLETE_SPEC",
            severity="MEDIUM",
            description="Network scan rule missing authoritative SIEM threshold",
            pattern_logic=None,
            status="ACTIVE",
            parsed_metadata={"definition_status": "INCOMPLETE"},
        )
        db.add_all([rule_ok, rule_inc])
        await db.flush()

        db.add_all(
            [
                RuleIntelligenceSnapshot(
                    rule_id=rule_ok.id,
                    rule_identifier=rule_ok.rule_id,
                    primary_archetype="NETWORK_EXFILTRATION",
                    definition_status="VERIFIED",
                    threshold=1000000000.0,
                    threshold_unit="bytes",
                    source_provenance="AUTHORITATIVE_SIEM_DEFINITION",
                ),
                RuleIntelligenceSnapshot(
                    rule_id=rule_inc.id,
                    rule_identifier=rule_inc.rule_id,
                    primary_archetype="NETWORK_SCAN",
                    definition_status="INCOMPLETE",
                    threshold=None,
                    threshold_unit=None,
                    source_provenance="INCOMPLETE_DEFINITION",
                ),
            ]
        )

        rp_ok = RulePrompt(rule_id=rule_ok.id)
        rp_inc = RulePrompt(rule_id=rule_inc.id)
        db.add_all([rp_ok, rp_inc])
        await db.flush()

        pv_ok = PromptVersion(
            prompt_id=rp_ok.id,
            version_number=1,
            status="APPROVED",
            change_summary="Phase 8 UI Approved Baseline",
            common_prompt="SOC Tier-2 Evidence-First Policy Baseline",
            rule_specific_prompt="Analyze suspicious outbound exfiltration against approved baseline.",
            detection_conditions="Outbound transfer sentBytes64 > 1000000000 bytes",
            required_evidence="network.source_ip, network.destination_ip, network.bytes_out, network.direction",
            tp_indicators="Unapproved bulk transfer to external untrusted destination.",
            fp_indicators="Confirmed scheduled enterprise backup or documented change ticket.",
            missing_info_criteria="Abstain if destination_ip or bytes_out is missing.",
            escalation_conditions="Contradictory Process Blocked=true requires escalation.",
            analyst_questions=["Confirm change ticket authorization for large outbound bytes."],
        )
        pv_inc = PromptVersion(
            prompt_id=rp_inc.id,
            version_number=1,
            status="DRAFT",
            change_summary="Provisional incomplete draft",
            common_prompt="SOC Tier-2 Baseline",
            rule_specific_prompt="Provisional draft missing authoritative SIEM scan threshold.",
            detection_conditions="Pending authoritative SIEM threshold.",
            required_evidence="network.source_ip, network.destination_port",
            tp_indicators="Multiple destination ports contacted.",
            fp_indicators="Authorized vulnerability scanner.",
            missing_info_criteria="Missing authoritative count threshold.",
            escalation_conditions="Escalate when ambiguous.",
            analyst_questions=["Check vulnerability scan schedule."],
        )
        db.add_all([pv_ok, pv_inc])
        await db.flush()
        rp_ok.active_version_id = pv_ok.id

        # Incident 1: Validated Authoritative TRUE_POSITIVE with Ground Truth Isolation check
        inc_tp = Incident(
            incident_id="P8-UI-INC-TP",
            rule_id=rule_ok.id,
            event_type=rule_ok.event_type,
            title="Phase 8 UI Validated Exfiltration Incident",
            severity="HIGH",
            source_ip="192.0.2.77",
            reporting_device="WKSTN-P8-UI",
            raw_payload={
                "source_ip": "192.0.2.77",
                "destination_ip": "198.51.100.44",
                "sentBytes64": 2130499380,
                "direction": "outbound",
                "clearedReason": "GT_SECRET_ISOLATION_TOKEN",
            },
            ai_verdict={
                "incident_id": "P8-UI-INC-TP",
                "proposed_verdict": "TRUE_POSITIVE",
                "verdict": "TRUE_POSITIVE",
                "is_decisive_accepted": True,
                "confidence": 92.0,
                "raw_model_confidence": 92.0,
                "trust_score": 8,
                "is_calibrated": False,
                "calibration_status": "NOT_CALIBRATED",
                "latency_ms": 1420,
                "prompt_tokens": 320,
                "completion_tokens": 95,
                "total_tokens": 415,
                "reason": "Host 192.0.2.77 sent 2130499380 bytes outbound to 198.51.100.44 exceeding threshold.",
                "supporting_evidence": ["192.0.2.77", "198.51.100.44", "2130499380"],
                "supporting_claims": [
                    {
                        "field": "network.destination_ip",
                        "asserted_value": "198.51.100.44",
                        "is_grounded": True,
                        "grounding_status": "GROUNDED",
                    }
                ],
                "claim_grounding": {"total_claims": 1, "grounded_claims": 1},
                "model_identifier": "local-qwen-test",
                "is_simulated": False,
                "validation_status": "VALIDATED",
                "validation_reason_codes": ["EVIDENCE_VALIDATED"],
                "evidence_completeness": 0.8,
                "grounding_ratio": 1.0,
                "canonical_evidence_count": 4,
            },
        )
        # Incident 2: Overruled LLM Proposal (0/0 claims -> Deterministic Guard)
        inc_guard = Incident(
            incident_id="P8-UI-INC-GUARD",
            rule_id=rule_ok.id,
            event_type=rule_ok.event_type,
            title="Phase 8 UI Guardrail Abstention Incident",
            severity="HIGH",
            source_ip="192.0.2.88",
            reporting_device="WKSTN-P8-GUARD",
            raw_payload={
                "source_ip": "192.0.2.88",
                "destination_ip": "198.51.100.99",
                "sentBytes64": 1500000000,
                "direction": "outbound",
            },
            ai_verdict={
                "incident_id": "P8-UI-INC-GUARD",
                "proposed_verdict": "TRUE_POSITIVE",
                "verdict": "REQUIRES_ATTENTION",
                "is_decisive_accepted": False,
                "confidence": 0.0,
                "raw_model_confidence": 88.0,
                "trust_score": 2,
                "is_calibrated": False,
                "calibration_status": "NOT_CALIBRATED",
                "latency_ms": 980,
                "prompt_tokens": 290,
                "completion_tokens": 60,
                "total_tokens": 350,
                "reason": "Insufficient grounded claims or corroborating evidence to confirm malicious attack.",
                "supporting_evidence": [],
                "supporting_claims": [],
                "claim_grounding": {"total_claims": 0, "grounded_claims": 0},
                "model_identifier": "local-qwen-test",
                "is_simulated": False,
                "validation_status": "INSUFFICIENT_EVIDENCE",
                "validation_reason_codes": ["TP_CRITERIA_UNSATISFIED"],
                "evidence_completeness": 0.8,
                "grounding_ratio": 0.0,
                "canonical_evidence_count": 4,
            },
        )
        # Incident 3: Pending review for Human Review Queue & Offline Error Fail-Safe UI check
        inc_queue = Incident(
            incident_id="P8-UI-INC-QUEUE",
            rule_id=rule_ok.id,
            event_type=rule_ok.event_type,
            title="Phase 8 UI Pending Triage & Queue Incident",
            severity="MEDIUM",
            source_ip="192.0.2.55",
            reporting_device="WKSTN-P8-QUEUE",
            raw_payload={
                "source_ip": "192.0.2.55",
                "destination_ip": "198.51.100.25",
                "sentBytes64": 1200000000,
                "direction": "outbound",
            },
        )
        db.add_all([inc_tp, inc_guard, inc_queue])
        await db.flush()

        db.add_all(
            [
                HistoricalGroundTruth(
                    incident_id=inc_tp.id,
                    resolution="True Positive",
                    cleared_reason="GT_SECRET_ISOLATION_TOKEN",
                    comments="GT_SECRET_ISOLATION_TOKEN verified ground truth",
                    is_ml_generated=False,
                ),
                Investigation(incident_id=inc_tp.id, status="PENDING_REVIEW"),
                Investigation(incident_id=inc_guard.id, status="PENDING_REVIEW"),
                Investigation(incident_id=inc_queue.id, status="PENDING_REVIEW"),
                VerdictTrustAssessmentRecord(
                    incident_id="P8-UI-INC-TP",
                    rule_id=rule_ok.id,
                    archetype="NETWORK_EXFILTRATION",
                    suggested_verdict="TRUE_POSITIVE",
                    effective_verdict="TRUE_POSITIVE",
                    trust_score=8,
                    raw_trust_score=82.0,
                    evidence_sufficiency_score=84.0,
                    evidence_status="SUFFICIENT",
                    historical_validation_status="UNCALIBRATED",
                    is_calibrated=False,
                    model_identifier="local-qwen-test",
                    is_simulated=False,
                ),
                VerdictTrustAssessmentRecord(
                    incident_id="P8-UI-INC-GUARD",
                    rule_id=rule_ok.id,
                    archetype="NETWORK_EXFILTRATION",
                    suggested_verdict="TRUE_POSITIVE",
                    effective_verdict="REQUIRES_ANALYST_ATTENTION",
                    trust_score=2,
                    raw_trust_score=20.0,
                    evidence_sufficiency_score=80.0,
                    evidence_status="SUFFICIENT",
                    historical_validation_status="UNCALIBRATED",
                    is_calibrated=False,
                    escalation_reason="Zero grounded supporting claims",
                    model_identifier="local-qwen-test",
                    is_simulated=False,
                ),
                EvidenceSufficiencyAssessmentRecord(
                    incident_id="P8-UI-INC-TP",
                    rule_id=rule_ok.id,
                    archetype="NETWORK_EXFILTRATION",
                    overall_sufficiency_score=84.0,
                    required_coverage_score=40.0,
                    evidence_status="SUFFICIENT",
                    mandatory_fields_present=["network.source_ip", "network.destination_ip", "network.bytes_out", "network.direction"],
                ),
                EvidenceSufficiencyAssessmentRecord(
                    incident_id="P8-UI-INC-GUARD",
                    rule_id=rule_ok.id,
                    archetype="NETWORK_EXFILTRATION",
                    overall_sufficiency_score=80.0,
                    required_coverage_score=40.0,
                    evidence_status="SUFFICIENT",
                    mandatory_fields_present=["network.source_ip", "network.destination_ip", "network.bytes_out", "network.direction"],
                ),
            ]
        )

        # Historical Evaluation Run & Results so Dashboards B & E display non-empty calibrated/uncalibrated state
        eval_run = HistoricalEvaluationRunRecord(
            run_name="Phase 8 E2E Baseline Replay",
            rule_id=rule_ok.id,
            archetype="NETWORK_EXFILTRATION",
            dataset_id="phase8-ui-dataset",
            status="COMPLETED",
            validation_state="INSUFFICIENT_DATA",
            total_cases=2,
            evaluated_cases=2,
            verified_ground_truth_cases=2,
            metrics={
                "overall_accuracy": 1.0,
                "balanced_accuracy": 1.0,
                "tp_precision": 1.0,
                "fp_precision": 1.0,
                "automatic_decision_coverage": 0.5,
                "analyst_attention_rate": 0.5,
                "critical_false_negatives": 0,
            },
            calibration_metrics={
                "status": "NOT_CALIBRATED",
                "is_calibrated": False,
                "reliability_bins": [],
            },
        )
        db.add(eval_run)
        await db.flush()
        db.add_all(
            [
                HistoricalEvaluationResultRecord(
                    run_id=eval_run.id,
                    incident_id="P8-UI-INC-TP",
                    rule_id=rule_ok.id,
                    suggested_verdict="TRUE_POSITIVE",
                    effective_verdict="TRUE_POSITIVE",
                    ground_truth_label="VERIFIED_TP",
                    trust_score=8,
                    raw_trust_score=82.0,
                    evidence_sufficiency_score=84.0,
                    evidence_status="SUFFICIENT",
                    is_correct=True,
                    is_abstained=False,
                    is_critical_error=False,
                ),
                HistoricalEvaluationResultRecord(
                    run_id=eval_run.id,
                    incident_id="P8-UI-INC-GUARD",
                    rule_id=rule_ok.id,
                    suggested_verdict="TRUE_POSITIVE",
                    effective_verdict="REQUIRES_ANALYST_ATTENTION",
                    ground_truth_label="VERIFIED_FP",
                    trust_score=2,
                    raw_trust_score=20.0,
                    evidence_sufficiency_score=80.0,
                    evidence_status="SUFFICIENT",
                    is_correct=None,
                    is_abstained=True,
                    is_critical_error=False,
                ),
            ]
        )
        await db.commit()
        return {
            "rule_ok_uuid": rule_ok.id,
            "rule_inc_uuid": rule_inc.id,
            "pv_inc_uuid": pv_inc.id,
            "admin_secret": admin_secret,
            "viewer_secret": viewer_secret,
        }


@pytest.fixture(scope="module")
def e2e_servers(tmp_path_factory):
    _assert_port_free("127.0.0.1", 8000)
    _assert_port_free("127.0.0.1", 3000)

    db_dir = tmp_path_factory.mktemp("p8_ui_db")
    db_path = db_dir / "phase8_ui_e2e.db"

    base_env = os.environ.copy()
    base_env["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    base_env["SYNC_DATABASE_URL"] = f"sqlite:///{db_path}"
    base_env["APP_ENV"] = "development"
    base_env["LOCAL_LLM_BASE_URL"] = "http://127.0.0.1:19999/v1"
    base_env["LOCAL_LLM_ALLOW_MOCK_FALLBACK"] = "false"
    base_env["FORTISIEM_MOCK_FALLBACK"] = "false"
    base_env["USE_ASYNC_CELERY"] = "false"
    base_env["FORTISIEM_AUTO_POLL_ENABLED"] = "false"
    base_env["AUTO_MIGRATE_ON_STARTUP"] = "false"

    alembic_res = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_DIR),
        env=base_env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert alembic_res.returncode == 0, f"Alembic failed: {alembic_res.stdout}\n{alembic_res.stderr}"

    seed_meta = asyncio.run(_seed_e2e_database(db_path))

    backend_log = db_dir / "uvicorn_e2e.log"
    frontend_log = db_dir / "nextjs_e2e.log"
    be_fh = backend_log.open("w", encoding="utf-8", errors="replace")
    fe_fh = frontend_log.open("w", encoding="utf-8", errors="replace")

    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(BACKEND_DIR),
        env=base_env,
        stdout=be_fh,
        stderr=subprocess.STDOUT,
    )
    frontend_cmd = "npm.cmd" if os.name == "nt" else "npm"
    frontend_proc = subprocess.Popen(
        [frontend_cmd, "run", "start", "--", "-H", "127.0.0.1", "-p", "3000"],
        cwd=str(FRONTEND_DIR),
        env=os.environ.copy(),
        stdout=fe_fh,
        stderr=subprocess.STDOUT,
    )

    try:
        _wait_http_ok("http://127.0.0.1:8000/openapi.json", timeout_s=45.0, proc=backend_proc, log_path=backend_log)
        _wait_http_ok("http://127.0.0.1:3000/login", timeout_s=45.0, proc=frontend_proc, log_path=frontend_log)
        yield {"seed": seed_meta, "backend_url": "http://127.0.0.1:8000", "frontend_url": "http://127.0.0.1:3000"}
    finally:
        for proc in (frontend_proc, backend_proc):
            if proc.poll() is None:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True, check=False)
                else:
                    proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
        for fh in (fe_fh, be_fh):
            try:
                fh.close()
            except Exception:
                pass


def test_phase8_stage7_full_browser_e2e(e2e_servers):
    """
    Executes Playwright headless Chromium UI journeys across Login, AIS Studio,
    AI Triage Workbench, Verdict Intelligence, and Human Review Queue, saving
    screenshots, trace ZIP, and structured PASS/FAIL summary under docs/phase8/evidence/.
    """
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    TRACES_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    base_url = e2e_servers["frontend_url"]
    seed = e2e_servers["seed"]
    console_errors: List[str] = []
    page_errors: List[str] = []
    steps_report: List[Dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()

        def _on_console(msg):
            if msg.type == "error":
                text = msg.text or ""
                # Ignore intentional negative HTTP error tests logged by fetch/XHR
                if "status of 400" in text or "status of 401" in text or "status of 403" in text or "status of 404" in text or "status of 503" in text:
                    return
                console_errors.append(text)

        page.on("console", _on_console)
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        try:
            # 1. Invalid Login + Valid Admin Login
            page.goto(f"{base_url}/login", wait_until="domcontentloaded")
            page.locator('input[placeholder="admin"]').fill("admin")
            page.locator('input[type="password"]').fill(f"Invalid-{secrets.token_hex(4)}")
            page.get_by_role("button", name="Sign In to Platform").click()
            expect(page.locator("text=/invalid|incorrect|failed|401/i").first).to_be_visible(timeout=10000)
            page.screenshot(path=str(SCREENSHOTS_DIR / "01_login_error.png"), full_page=True)
            steps_report.append({"step": "1_invalid_login_rejected", "status": "PASSED"})

            page.locator('input[type="password"]').fill(seed["admin_secret"])
            page.get_by_role("button", name="Sign In to Platform").click()
            page.wait_for_url("**/agent-mission-control", timeout=15000)
            token = page.evaluate("() => window.localStorage.getItem('ai_verdict_token')")
            assert token and len(token) > 20, "JWT token missing from localStorage after login"
            page.screenshot(path=str(SCREENSHOTS_DIR / "02_mission_control.png"), full_page=True)
            steps_report.append({"step": "2_valid_login_and_session", "status": "PASSED"})

            # 2. Agent Intelligence Studio — Complete Rule, Quality Gates, Simulation, Incomplete Blocker, RBAC
            page.goto(f"{base_url}/agent-intelligence-studio", wait_until="domcontentloaded")
            expect(page.get_by_text("PH_RULE_UI_COMPLETE_EXFIL").first).to_be_visible(timeout=15000)
            expect(page.get_by_text("PH_RULE_UI_INCOMPLETE_SPEC").first).to_be_visible(timeout=15000)

            row_ok = page.locator("tr", has_text="PH_RULE_UI_COMPLETE_EXFIL").first
            row_ok.get_by_role("button", name="Open Studio").click()
            expect(page.get_by_text("1. COMMON SOC BASELINE PROTOCOL")).to_be_visible(timeout=15000)

            page.get_by_role("button", name="Quality Gates (G1–G8)").click()
            page.get_by_role("button", name="Validate Quality").click()
            page.wait_for_timeout(1500)
            page.screenshot(path=str(SCREENSHOTS_DIR / "03_ais_quality_gates.png"), full_page=True)

            page.get_by_role("button", name="Simulation Lab").click()
            page.wait_for_timeout(800)
            page.screenshot(path=str(SCREENSHOTS_DIR / "04_ais_simulation_lab.png"), full_page=True)

            # Go back & open incomplete rule -> G1 incomplete blocker + disabled Approve button
            page.goto(f"{base_url}/agent-intelligence-studio", wait_until="domcontentloaded")
            row_inc = page.locator("tr", has_text="PH_RULE_UI_INCOMPLETE_SPEC").first
            row_inc.get_by_role("button", name="Open Studio").click()
            expect(page.get_by_text("Rule Definition Incomplete — Approval Gate 1 (G1) Blocked")).to_be_visible(timeout=15000)
            expect(page.get_by_role("button", name="Approve & Activate")).to_be_disabled()
            page.screenshot(path=str(SCREENSHOTS_DIR / "05_ais_incomplete_g1_blocked.png"), full_page=True)

            # Verify backend API approval gate & RBAC reject viewer / incomplete draft cleanly
            rbac_status = page.evaluate(
                """async ({adminToken, ruleId, verId, viewerCred}) => {
                    const loginResp = await fetch('/api/auth/login', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({username: 'viewer', password: viewerCred})
                    });
                    const viewerData = await loginResp.json();
                    const viewerApprove = await fetch(`/api/prompts/rule/${ruleId}/approve/${verId}`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${viewerData.access_token}`},
                        body: JSON.stringify({change_summary: 'viewer attempt'})
                    });
                    const adminApprove = await fetch(`/api/prompts/rule/${ruleId}/approve/${verId}`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${adminToken}`},
                        body: JSON.stringify({change_summary: 'incomplete attempt'})
                    });
                    return {viewerStatus: viewerApprove.status, adminStatus: adminApprove.status};
                }""",
                {"adminToken": token, "ruleId": seed["rule_inc_uuid"], "verId": seed["pv_inc_uuid"], "viewerCred": seed["viewer_secret"]},
            )
            assert rbac_status["viewerStatus"] == 403, f"Expected 403 for viewer approve, got {rbac_status}"
            assert rbac_status["adminStatus"] == 400, f"Expected 400 for incomplete draft approve, got {rbac_status}"
            steps_report.append({"step": "3_agent_intelligence_studio_and_rbac", "status": "PASSED", "rbac": rbac_status})

            # 3. AI Triage Workbench — TP Authoritative Verdict, Guardrail 0/0 Claims, Blind Review & Offline Fail-Safe
            main = page.get_by_role("main")
            page.goto(f"{base_url}/ai-triage-workbench/P8-UI-INC-TP", wait_until="domcontentloaded")
            expect(main.get_by_text("TRUE POSITIVE").first).to_be_visible(timeout=15000)
            main.get_by_role("button", name="Evidence Integrity Guardrail").click()
            expect(page.locator("body")).not_to_contain_text("GT_SECRET_ISOLATION_TOKEN")
            main.get_by_role("button", name="Canonical Evidence").click()
            expect(main.get_by_text("198.51.100.44").first).to_be_visible(timeout=10000)
            page.get_by_role("button", name="Blind Review: OFF").last.click()
            expect(page.get_by_role("button", name="Blind Review: ON").first).to_be_visible(timeout=10000)
            page.screenshot(path=str(SCREENSHOTS_DIR / "06_triage_workbench_tp_gt_isolated.png"), full_page=True)
            page.get_by_role("button", name="Blind Review: ON").last.click()
            steps_report.append({"step": "4_triage_workbench_tp_and_gt_isolation", "status": "PASSED"})

            page.goto(f"{base_url}/ai-triage-workbench/P8-UI-INC-GUARD", wait_until="domcontentloaded")
            expect(main.get_by_text("Phase 8 UI Guardrail Abstention Incident").first).to_be_visible(timeout=15000)
            expect(main.locator("text=/REQUIRES[_ ]ATTENTION/i").first).to_be_visible(timeout=10000)
            expect(main.get_by_text("Deterministic Safety Override Applied")).to_be_visible()
            expect(main.get_by_text("0/0 claims — unclaimed").first).to_be_visible()
            expect(main.get_by_text("TP_CRITERIA_UNSATISFIED")).to_be_visible()
            page.screenshot(path=str(SCREENSHOTS_DIR / "07_triage_workbench_guard_unclaimed.png"), full_page=True)
            steps_report.append({"step": "5_triage_workbench_guard_0_claims", "status": "PASSED"})

            # Offline Local LLM error state check (must show error banner and never fake verdict)
            page.goto(f"{base_url}/ai-triage-workbench/P8-UI-INC-QUEUE", wait_until="domcontentloaded")
            main.get_by_role("button", name="Verdict Triage Agent").click()
            expect(main.locator("text=/offline|unavailable|failed|error/i").first).to_be_visible(timeout=15000)
            page.screenshot(path=str(SCREENSHOTS_DIR / "08_triage_offline_fail_closed.png"), full_page=True)
            steps_report.append({"step": "6_triage_offline_fail_closed", "status": "PASSED"})

            # 404 Nonexistent incident check
            page.goto(f"{base_url}/ai-triage-workbench/DOES_NOT_EXIST_P8", wait_until="domcontentloaded")
            expect(main.locator("text=/not found|error|failed/i").first).to_be_visible(timeout=10000)
            steps_report.append({"step": "7_triage_404_error_handling", "status": "PASSED"})

            # 4. Verdict Intelligence — DOM-to-API Parity, Simulation Checkbox Default OFF & NOT_CALIBRATED
            with page.expect_response(lambda r: "/api/verdict-intelligence/metrics/summary" in r.url and r.status == 200) as api_resp_info:
                page.goto(f"{base_url}/verdict-intelligence", wait_until="domcontentloaded")
            api_overview = api_resp_info.value.json()
            total_card = main.locator("div", has_text="Total Evaluated Cases").filter(has_text=str(api_overview["total_evaluated_incidents"])).first
            expect(total_card).to_be_visible(timeout=10000)

            sim_checkbox = main.locator("label", has_text="Allow simulation fallback").locator("input[type='checkbox']")
            expect(sim_checkbox).not_to_be_checked()

            main.locator('input[placeholder^="Enter Incident ID to evaluate trust"]').fill("P8-UI-INC-QUEUE")
            with page.expect_response(lambda r: "/api/verdict-intelligence/evaluate-incident" in r.url) as blocked_eval:
                main.get_by_role("button", name="Evaluate Trust").click()
            assert blocked_eval.value.status >= 400, f"Expected offline eval to reject simulation-off request, got {blocked_eval.value.status}"
            expect(main.locator("text=/simulation|offline|unavailable|failed|blocked|local llm/i").first).to_be_visible(timeout=10000)

            sim_checkbox.check()
            expect(sim_checkbox).to_be_checked()
            main.get_by_role("button", name="Evaluate Trust").click()
            expect(main.get_by_text("Dashboard D: Incident Verdict Drill-Down")).to_be_visible(timeout=10000)
            expect(main.locator("text=/SIMULATED|Simulation/i").first).to_be_visible(timeout=15000)

            main.get_by_role("button", name="Dashboard E: Replay & Regression Comparison").click()
            main.get_by_text("Phase 8 E2E Baseline Replay").first.click()
            main.get_by_role("button", name="Dashboard B: Empirical Accuracy").click()
            expect(main.get_by_text("Status: NOT_CALIBRATED")).to_be_visible(timeout=10000)
            page.screenshot(path=str(SCREENSHOTS_DIR / "09_verdict_intelligence_simulation_and_calibration.png"), full_page=True)
            steps_report.append({"step": "8_verdict_intelligence_parity_and_sim_toggle", "status": "PASSED", "api_total_evaluated": api_overview["total_evaluated_incidents"]})

            # 5. Human Review Queue — Analyst Decision Persistence Across Reload
            page.goto(f"{base_url}/human-review-queue", wait_until="domcontentloaded")
            queue_row = main.locator("tr", has_text="P8-UI-INC-QUEUE").first
            expect(queue_row).to_be_visible(timeout=15000)
            queue_row.get_by_role("button", name="Investigate").click()
            main.get_by_role("button", name="False Positive").click()
            main.locator('textarea[placeholder="Explain the definitive rationale for this verdict..."]').fill(
                "Verified scheduled nightly backup during Phase 8 Playwright E2E."
            )
            with page.expect_response(lambda r: "/api/investigations/" in r.url and r.request.method in ("POST", "PUT", "PATCH")) as verdict_save:
                main.get_by_role("button", name="Finalize & Save Verified Verdict").click()
            assert verdict_save.value.status < 300, f"Expected verdict save 2xx, got {verdict_save.value.status}"
            expect(main.locator("tr", has_text="P8-UI-INC-QUEUE").first).to_contain_text("REVIEWED", timeout=15000)
            page.wait_for_timeout(300)

            page.reload(wait_until="domcontentloaded")
            expect(main.locator("tr", has_text="P8-UI-INC-QUEUE").first).to_contain_text("False Positive", timeout=15000)
            page.wait_for_timeout(300)
            page.screenshot(path=str(SCREENSHOTS_DIR / "10_human_review_queue_persisted.png"), full_page=True)
            steps_report.append({"step": "9_human_review_queue_persistence", "status": "PASSED"})

        except Exception:
            try:
                page.screenshot(path=str(SCREENSHOTS_DIR / "_failure_debug.png"), full_page=True)
            except Exception:
                pass
            raise
        finally:
            context.tracing.stop(path=str(TRACES_DIR / "playwright_e2e_trace.zip"))
            browser.close()

    assert not page_errors, f"Uncaught page errors observed in Chromium: {page_errors}"
    assert not console_errors, f"Unexpected console errors observed in Chromium: {console_errors}"

    summary = {
        "runner": "pytest backend/tests/e2e_browser/test_phase8_ui_e2e.py",
        "browser": "chromium-headless",
        "total_steps": len(steps_report),
        "passed_steps": sum(1 for s in steps_report if s["status"] == "PASSED"),
        "console_errors_count": len(console_errors),
        "page_errors_count": len(page_errors),
        "screenshots_captured": sorted(p.name for p in SCREENSHOTS_DIR.glob("*.png")),
        "trace_zip": "docs/phase8/evidence/traces/playwright_e2e_trace.zip",
        "steps": steps_report,
    }
    (RESULTS_DIR / "playwright_e2e_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

