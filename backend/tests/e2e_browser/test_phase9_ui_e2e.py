"""
Phase 9 Headless Chromium Browser E2E Suite (Stage 12).

Verifies real Next.js production UI + FastAPI/SQLite backend across:
  1. Agent Mission Control SOC Pilot banner & DISABLED default state.
  2. Issue 1 Fix: Verdict Intelligence Dashboard B never shows 50% coverage alongside Decisive = 0.
  3. Issue 2 Fix: AI Triage Workbench shows Trust: 6/10 (Uncalibrated Cap) + Historical stored: 8/10 (pre-cap).
  4. SOC Pilot Lifecycle: Config -> SHADOW activation -> Controlled LIVE run against local OpenAI mock ->
     Pilot Evaluation Log provenance & Shadow isolation.
  5. ANALYST_ASSISTED + Human Review Queue AI Assurance drawer -> Analyst override preserves AI output ->
     Independent Supervisor verification -> Pause -> Safe Disable preserving history.
  6. Server 2 Offline fail-closed check (never simulated fallback on LIVE).
  7. Read-Only Viewer RBAC UI enforcement (all pilot & review mutations disabled).
  8. Dashboard G Historical Data Eligibility Report & G8 readiness rendering.
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List
from urllib.request import urlopen

import pytest
from playwright.sync_api import expect, sync_playwright
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent
FRONTEND_EVIDENCE_DIR = REPO_ROOT / "docs" / "phase9" / "evidence" / "frontend"
SCREENSHOTS_DIR = REPO_ROOT / "docs" / "phase9" / "evidence" / "screenshots"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models.incident import HistoricalGroundTruth, Incident, IncidentEvent  # noqa: E402
from app.models.investigation import Investigation  # noqa: E402
from app.models.prompt import PromptVersion, RulePrompt  # noqa: E402
from app.models.rule import Rule  # noqa: E402
from app.models.rule_intelligence import RuleIntelligenceSnapshot  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.verdict_intelligence import HistoricalEvaluationRunRecord  # noqa: E402
from app.utils.security import get_password_hash  # noqa: E402


class _MockLLMServer:
    def __init__(self) -> None:
        self.online = True
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if not parent.online:
                    self.send_response(503)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                if self.path.startswith("/metrics"):
                    body = b"vllm:num_requests_running 0\n"
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if self.path.startswith("/health"):
                    body = b'{"status":"ok"}'
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                body = json.dumps({"object": "list", "data": [{"id": "qwen2.5-32b-instruct"}]}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or "0")
                if length > 0:
                    _ = self.rfile.read(length)
                if not parent.online:
                    self.send_response(503)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                payload = {
                    "id": "chatcmpl-p9-ui",
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "verdict": "TRUE_POSITIVE",
                                        "confidence": 91.0,
                                        "reason": "Observed powershell.exe encoded payload from 192.0.2.50 on WORKSTATION-P9UI matching rule telemetry.",
                                        "supporting_evidence": [
                                            "source_ip=192.0.2.50",
                                            "process_name=powershell.exe",
                                            "command_line=powershell -enc AAAA",
                                        ],
                                        "missing_evidence": [],
                                        "analyst_questions": ["Confirm authorized admin ticket."],
                                    }
                                )
                            }
                        }
                    ],
                    "usage": {"prompt_tokens": 110, "completion_tokens": 45, "total_tokens": 155},
                }
                body = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()


def _wait_http_ok(url: str, timeout_s: float, proc: subprocess.Popen, log_path: Path) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            logs = log_path.read_text(encoding="utf-8", errors="ignore")[-2000:] if log_path.exists() else ""
            raise RuntimeError(f"Process exited prematurely ({proc.returncode}) for {url}:\n{logs}")
        try:
            with urlopen(url, timeout=1.5) as resp:
                if resp.status < 500:
                    return
        except Exception:
            time.sleep(0.4)
    raise RuntimeError(f"Timed out waiting for {url} after {timeout_s}s")


async def _seed_p9_database(db_path: Path) -> Dict[str, str]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sess_mk = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    admin_secret = secrets.token_urlsafe(12)
    supervisor_secret = secrets.token_urlsafe(12)
    analyst_secret = secrets.token_urlsafe(12)
    viewer_secret = secrets.token_urlsafe(12)

    async with sess_mk() as db:
        users = [
            User(
                username="admin",
                email="admin-p9@example.test",
                hashed_password=get_password_hash(admin_secret),
                full_name="Phase 9 Admin",
                role="Administrator",
                is_active=True,
            ),
            User(
                username="supervisor",
                email="supervisor-p9@example.test",
                hashed_password=get_password_hash(supervisor_secret),
                full_name="Phase 9 Supervisor",
                role="Administrator",
                is_active=True,
            ),
            User(
                username="analyst",
                email="analyst-p9@example.test",
                hashed_password=get_password_hash(analyst_secret),
                full_name="Phase 9 Analyst",
                role="SOC Analyst",
                is_active=True,
            ),
            User(
                username="viewer",
                email="viewer-p9@example.test",
                hashed_password=get_password_hash(viewer_secret),
                full_name="Phase 9 Viewer",
                role="Read-Only Viewer",
                is_active=True,
            ),
        ]
        db.add_all(users)
        await db.flush()

        rule = Rule(
            rule_id="P9-UI-RULE-001",
            name="Phase 9 Pilot Execution Rule",
            event_type="P9-UI-RULE-001",
            severity="HIGH",
            description="Detects suspicious encoded PowerShell execution",
            data_source="FortiSIEM",
            status="ACTIVE",
        )
        db.add(rule)
        await db.flush()

        db.add(
            RuleIntelligenceSnapshot(
                rule_id=rule.id,
                rule_identifier=rule.rule_id,
                primary_archetype="PROCESS_EXECUTION",
                definition_status="COMPLETE",
                source_provenance="TEST",
            )
        )

        rp = RulePrompt(rule_id=rule.id)
        db.add(rp)
        await db.flush()

        pv = PromptVersion(
            prompt_id=rp.id,
            version_number=1,
            status="APPROVED",
            is_template_draft=False,
            quality_status="PASSED",
            quality_score=96.0,
            common_prompt="SOC evidence-first policy",
            rule_specific_prompt="Validate PowerShell host, user, and command line telemetry.",
            detection_conditions="powershell.exe -enc",
            required_evidence="source_ip, host_name, process_name, command_line",
            tp_indicators="Encoded payload without admin approval",
            fp_indicators="Signed IT automation script",
            missing_info_criteria="Missing command_line",
            escalation_conditions="Any privilege escalation ambiguity",
            analyst_questions=["Confirm change ticket"],
            change_summary="Approved Phase 9 UI policy",
        )
        db.add(pv)
        await db.flush()
        rp.active_version_id = pv.id
        db.add(rp)

        inc_legacy = Incident(
            incident_id="P9-UI-INC-1",
            rule_id=rule.id,
            event_type=rule.event_type,
            title="Legacy Stored Trust 8 Uncalibrated Case",
            severity="HIGH",
            status_code=1,
            status_name="Active",
            category="Endpoint",
            source_ip="192.0.2.50",
            reporting_ip="198.51.100.10",
            reporting_device="WORKSTATION-P9UI",
            first_seen_epoch=int(time.time()),
            raw_payload={"source_ip": "192.0.2.50", "host_name": "WORKSTATION-P9UI", "process_name": "powershell.exe", "command_line": "powershell -enc AAAA"},
            ai_verdict={
                "incident_id": "P9-UI-INC-1",
                "verdict": "TRUE_POSITIVE",
                "proposed_verdict": "TRUE_POSITIVE",
                "confidence": 88.0,
                "reason": "Legacy uncalibrated trust 8 verdict fixture",
                "supporting_evidence": ["source_ip=192.0.2.50"],
                "missing_evidence": [],
                "analyst_questions": [],
                "latency_ms": 100,
                "model_identifier": "legacy-test-model",
                "is_simulated": False,
                "trust_score": 8,
                "is_calibrated": False,
                "calibration_status": "UNCALIBRATED_ORDINAL",
                "validation_status": "VALIDATED",
            },
        )
        inc_pilot = Incident(
            incident_id="P9-UI-INC-2",
            rule_id=rule.id,
            event_type=rule.event_type,
            title="Phase 9 Controlled Pilot Triage Case",
            severity="HIGH",
            status_code=1,
            status_name="Active",
            category="Endpoint",
            source_ip="192.0.2.50",
            reporting_ip="198.51.100.10",
            reporting_device="WORKSTATION-P9UI",
            first_seen_epoch=int(time.time()),
            raw_payload={"source_ip": "192.0.2.50", "host_name": "WORKSTATION-P9UI", "process_name": "powershell.exe", "command_line": "powershell -enc AAAA"},
            ai_verdict=None,
        )
        inc_offline_probe = Incident(
            incident_id="P9-UI-INC-3",
            rule_id=rule.id,
            event_type=rule.event_type,
            title="Phase 9 Offline Fail-Closed Probe Case",
            severity="INFO",
            status_code=1,
            status_name="Active",
            category="Endpoint",
            source_ip="192.0.2.50",
            reporting_ip="198.51.100.10",
            reporting_device="WORKSTATION-P9UI",
            first_seen_epoch=int(time.time()),
            raw_payload={"source_ip": "192.0.2.50", "host_name": "WORKSTATION-P9UI", "process_name": "powershell.exe", "command_line": "powershell -enc AAAA"},
            ai_verdict=None,
        )
        db.add_all([inc_legacy, inc_pilot, inc_offline_probe])
        await db.flush()

        for inc in (inc_legacy, inc_pilot, inc_offline_probe):
            db.add(
                IncidentEvent(
                    incident_id=inc.id,
                    event_id=f"EV-{inc.incident_id}",
                    event_type=rule.event_type,
                    raw_log="powershell.exe -enc AAAA",
                    attributes={"source_ip": "192.0.2.50", "host_name": "WORKSTATION-P9UI", "process_name": "powershell.exe", "command_line": "powershell -enc AAAA"},
                )
            )

        db.add(
            HistoricalGroundTruth(
                incident_id=inc_legacy.id,
                resolution="True Positive",
                comments="Verified in Tier-3 historical ticket.",
                cleared_user="tier3_reviewer",
                cleared_reason="Confirmed unauthorized PowerShell payload",
                is_ml_generated=False,
            )
        )
        db.add_all([
            Investigation(incident_id=inc_legacy.id, status="PENDING_REVIEW"),
            Investigation(incident_id=inc_pilot.id, status="PENDING_REVIEW"),
            HistoricalEvaluationRunRecord(
                run_name="P9 Issue 1 Zero-Denominator Legacy Coverage Run",
                rule_id=rule.id,
                archetype="PROCESS_EXECUTION",
                dataset_id="p9-ui",
                status="COMPLETED",
                validation_state="INSUFFICIENT_DATA",
                total_cases=2,
                evaluated_cases=2,
                verified_ground_truth_cases=0,
                metrics={"balanced_accuracy": None, "automatic_decision_coverage": 0.5, "analyst_attention_rate": 0.5, "critical_false_negatives": 0},
                calibration_metrics={"status": "NOT_CALIBRATED", "is_calibrated": False},
            ),
        ])
        await db.commit()
        await engine.dispose()

        return {
            "admin_secret": admin_secret,
            "supervisor_secret": supervisor_secret,
            "analyst_secret": analyst_secret,
            "viewer_secret": viewer_secret,
        }


@pytest.fixture(scope="module")
def e2e_p9_servers(tmp_path_factory):
    mock_llm = _MockLLMServer()
    mock_llm.start()

    db_dir = tmp_path_factory.mktemp("p9_e2e_db")
    db_path = db_dir / "p9_e2e.db"
    env = os.environ.copy()
    env["APP_ENV"] = "development"
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    env["SYNC_DATABASE_URL"] = f"sqlite:///{db_path}"
    env["USE_ASYNC_CELERY"] = "false"
    env["LOCAL_LLM_BASE_URL"] = f"http://127.0.0.1:{mock_llm.port}/v1"
    env["LOCAL_LLM_MODEL_NAME"] = "qwen2.5-32b-instruct"
    env["LOCAL_LLM_ALLOW_MOCK_FALLBACK"] = "false"
    env["SECRET_KEY"] = f"p9-e2e-secret-{secrets.token_hex(16)}"

    alembic_res = subprocess.run(["alembic", "upgrade", "head"], cwd=str(BACKEND_DIR), env=env, capture_output=True, text=True)
    assert alembic_res.returncode == 0, alembic_res.stderr
    seed_meta = asyncio.run(_seed_p9_database(db_path))

    be_log = db_dir / "backend_p9.log"
    fe_log = db_dir / "frontend_p9.log"
    be_f = open(be_log, "w", encoding="utf-8")
    fe_f = open(fe_log, "w", encoding="utf-8")

    be_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(BACKEND_DIR),
        env=env,
        stdout=be_f,
        stderr=subprocess.STDOUT,
    )
    fe_cmd = "npm.cmd run start -- -H 127.0.0.1 -p 3000" if os.name == "nt" else "npm run start -- -H 127.0.0.1 -p 3000"
    fe_proc = subprocess.Popen(
        fe_cmd,
        cwd=str(REPO_ROOT / "frontend"),
        env=env,
        shell=True,
        stdout=fe_f,
        stderr=subprocess.STDOUT,
    )

    try:
        _wait_http_ok("http://127.0.0.1:8000/api/health", 35.0, be_proc, be_log)
        _wait_http_ok("http://127.0.0.1:3000/login", 45.0, fe_proc, fe_log)
        yield {"base_url": "http://127.0.0.1:3000", "mock_llm": mock_llm, **seed_meta}
    finally:
        for proc in (fe_proc, be_proc):
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    proc.kill()
        be_f.close()
        fe_f.close()
        mock_llm.stop()


def test_phase9_soc_pilot_and_audit_remediations_browser_e2e(e2e_p9_servers):
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    FRONTEND_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    base_url = e2e_p9_servers["base_url"]
    mock_llm: _MockLLMServer = e2e_p9_servers["mock_llm"]

    console_errors: List[str] = []
    page_errors: List[str] = []
    steps: List[Dict[str, Any]] = []

    def _login(page, username: str, password: str) -> None:
        page.goto(f"{base_url}/login", wait_until="domcontentloaded")
        page.locator('input[placeholder="admin"]').fill(username)
        page.locator('input[type="password"]').fill(password)
        page.get_by_role("button", name="Sign In to Platform").click()
        page.wait_for_url("**/agent-mission-control", timeout=15000)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: page_errors.append(str(e)))

        main = page.get_by_role("main")

        # 1. Admin login & Mission Control Pilot Banner (default DISABLED)
        _login(page, "admin", e2e_p9_servers["admin_secret"])
        expect(main.get_by_test_id("mission-control-pilot-banner")).to_be_visible(timeout=15000)
        expect(main.get_by_test_id("mission-control-pilot-banner")).to_contain_text("DISABLED")
        steps.append({"step": "1_mission_control_pilot_disabled_banner", "status": "PASSED"})

        # 2. Issue 1 Regression: Dashboard B never shows 50% coverage alongside Decisive = 0
        page.goto(f"{base_url}/verdict-intelligence?tab=accuracy", wait_until="domcontentloaded")
        expect(main.get_by_text("NOT_CALCULABLE", exact=True).first).to_be_visible(timeout=15000)
        expect(main.get_by_text("Decisive = 0").first).to_be_visible()
        expect(main).not_to_contain_text("50%")
        steps.append({"step": "2_issue1_coverage_regression_ui", "status": "PASSED"})

        # 3. Issue 2 Regression: AI Triage Workbench shows 6/10 Cap + 8/10 Historical Provenance
        page.goto(f"{base_url}/ai-triage-workbench/P9-UI-INC-1", wait_until="domcontentloaded")
        expect(main.get_by_text("Trust: 6/10 (Uncalibrated Cap)").first).to_be_visible(timeout=15000)
        expect(main.get_by_text("Historical stored: 8/10 (pre-cap)").first).to_be_visible()
        steps.append({"step": "3_issue2_uncalibrated_trust_cap_ui", "status": "PASSED"})

        # 4. Pilot Control: Activate SHADOW + run LIVE batch against local OpenAI mock + verify Shadow isolation
        page.goto(f"{base_url}/verdict-intelligence?tab=pilot", wait_until="domcontentloaded")
        expect(main.get_by_test_id("pilot-mode-badge")).to_contain_text("MODE: DISABLED", timeout=15000)
        main.get_by_test_id("btn-activate-shadow").click()
        expect(main.get_by_test_id("pilot-mode-badge")).to_contain_text("MODE: SHADOW", timeout=15000)

        main.get_by_test_id("btn-run-pilot-batch").click()
        expect(main.get_by_test_id("pilot-success-banner")).to_be_visible(timeout=20000)
        expect(main.get_by_text("P9-UI-INC-2").first).to_be_visible(timeout=10000)
        expect(main.get_by_text("LIVE_PROVIDER").first).to_be_visible()
        page.screenshot(path=str(SCREENSHOTS_DIR / "01_pilot_shadow_dashboard.png"), full_page=True)

        # Verify P9-UI-INC-2 Incident AI Verdict remains untouched/absent in SHADOW mode!
        page.goto(f"{base_url}/ai-triage-workbench/P9-UI-INC-2", wait_until="domcontentloaded")
        expect(main.get_by_role("button", name="Verdict Triage Agent")).to_be_visible(timeout=15000)
        expect(main.get_by_text("Stored Verdict")).to_have_count(0)
        steps.append({"step": "4_pilot_shadow_execution_and_isolation", "status": "PASSED"})

        # 5. Switch to ANALYST_ASSISTED and evaluate P9-UI-INC-2
        page.goto(f"{base_url}/verdict-intelligence?tab=pilot", wait_until="domcontentloaded")
        main.get_by_test_id("btn-activate-assisted").click()
        expect(main.get_by_test_id("pilot-mode-badge")).to_contain_text("MODE: ANALYST_ASSISTED", timeout=15000)
        main.get_by_test_id("btn-run-pilot-batch").click()
        expect(main.get_by_test_id("pilot-success-banner")).to_be_visible(timeout=20000)

        # Sign in as Analyst: check RBAC guard on Admin buttons, then Human Review Queue AI Assurance & Override
        _login(page, "analyst", e2e_p9_servers["analyst_secret"])
        page.goto(f"{base_url}/verdict-intelligence?tab=pilot", wait_until="domcontentloaded")
        expect(main.get_by_test_id("pilot-rbac-notice")).to_be_visible(timeout=15000)
        expect(main.get_by_test_id("btn-disable-pilot")).to_be_disabled()

        page.goto(f"{base_url}/human-review-queue", wait_until="domcontentloaded")
        main.locator("tr", has_text="P9-UI-INC-2").first.get_by_role("button", name="Investigate").click()
        expect(main.get_by_test_id("drawer-ai-assurance")).to_be_visible(timeout=15000)
        expect(main.get_by_test_id("drawer-ai-assurance")).to_contain_text("ANALYST_ASSISTED")
        expect(main.get_by_test_id("drawer-ai-assurance")).to_contain_text("Policy: v1")
        page.screenshot(path=str(SCREENSHOTS_DIR / "02_human_review_ai_assurance.png"), full_page=True)

        main.get_by_role("button", name="OVERRIDDEN").click()
        main.get_by_role("button", name="False Positive").click()
        main.locator('textarea[placeholder="Explain the definitive rationale for this verdict..."]').fill("Phase 9 UI analyst override verified against ticket.")
        main.get_by_role("button", name="Finalize & Save Verified Verdict").click()
        expect(main.get_by_text("submitted and verified successfully")).to_be_visible(timeout=10000)
        page.reload(wait_until="domcontentloaded")
        main.locator("tr", has_text="P9-UI-INC-2").first.get_by_role("button", name="Investigate").click()
        expect(main.get_by_test_id("drawer-ai-assurance")).to_contain_text("TRUE_POSITIVE")
        steps.append({"step": "5_analyst_assisted_assurance_override_persistence", "status": "PASSED"})

        # 6. Supervisor verification by independent Administrator + Safe Pause & Safe Disable preserving history
        _login(page, "supervisor", e2e_p9_servers["supervisor_secret"])
        page.goto(f"{base_url}/verdict-intelligence?tab=pilot", wait_until="domcontentloaded")
        main.get_by_role("button", name="Supervisor Verify").first.click()
        expect(main.get_by_test_id("pilot-success-banner")).to_contain_text("Supervisor verification recorded", timeout=10000)

        main.get_by_test_id("btn-pause-resume").click()
        expect(main.get_by_text("PAUSED").first).to_be_visible(timeout=10000)
        main.get_by_test_id("btn-disable-pilot").click()
        expect(main.get_by_test_id("pilot-mode-badge")).to_contain_text("MODE: DISABLED", timeout=10000)
        expect(main.get_by_text("P9-UI-INC-2").first).to_be_visible()
        steps.append({"step": "6_supervisor_verify_pause_and_safe_disable", "status": "PASSED"})

        # 7. Server 2 Offline error handling check on LIVE mode (include INFO severity for fresh un-evaluated P9-UI-INC-3)
        mock_llm.online = False
        main.get_by_label("INFO").check()
        main.get_by_test_id("btn-save-pilot-config").click()
        expect(main.get_by_test_id("pilot-success-banner")).to_be_visible(timeout=10000)
        main.get_by_test_id("btn-activate-shadow").click()
        expect(main.get_by_test_id("pilot-mode-badge")).to_contain_text("MODE: SHADOW", timeout=10000)
        main.get_by_test_id("btn-run-pilot-batch").click()
        expect(main.get_by_test_id("pilot-error-banner")).to_be_visible(timeout=20000)
        main.get_by_test_id("btn-disable-pilot").click()
        expect(main.get_by_test_id("pilot-mode-badge")).to_contain_text("MODE: DISABLED", timeout=10000)
        steps.append({"step": "7_server2_offline_fail_closed_ui", "status": "PASSED"})

        # 8. Dashboard G: Historical Data Eligibility Report
        page.goto(f"{base_url}/verdict-intelligence?tab=eligibility", wait_until="domcontentloaded")
        expect(main.get_by_test_id("historical-eligibility-panel")).to_be_visible(timeout=15000)
        expect(main.get_by_text("INSUFFICIENT_DATA").first).to_be_visible(timeout=10000)
        expect(main.get_by_text("P9-UI-RULE-001").first).to_be_visible()
        page.screenshot(path=str(SCREENSHOTS_DIR / "04_historical_eligibility_report.png"), full_page=True)
        steps.append({"step": "8_historical_eligibility_panel", "status": "PASSED"})

        # 9. Read-Only Viewer UX lock verification (zero console/page errors)
        _login(page, "viewer", e2e_p9_servers["viewer_secret"])
        page.goto(f"{base_url}/verdict-intelligence?tab=pilot", wait_until="domcontentloaded")
        expect(main.get_by_test_id("pilot-rbac-notice")).to_be_visible(timeout=15000)
        expect(main.get_by_test_id("btn-save-pilot-config")).to_be_disabled()
        expect(main.get_by_test_id("btn-run-pilot-batch")).to_be_disabled()
        page.screenshot(path=str(SCREENSHOTS_DIR / "03_pilot_viewer_readonly.png"), full_page=True)

        page.goto(f"{base_url}/human-review-queue", wait_until="domcontentloaded")
        main.locator("tr", has_text="P9-UI-INC-2").first.get_by_role("button", name="Investigate").click()
        expect(main.get_by_text("Read-Only Viewer: investigation edits")).to_be_visible(timeout=10000)
        expect(main.get_by_role("button", name="Finalize & Save Verified Verdict")).to_be_disabled()
        steps.append({"step": "9_read_only_viewer_controls_locked", "status": "PASSED"})

        browser.close()

    assert not page_errors, f"Uncaught page errors: {page_errors}"
    assert not console_errors, f"Console errors observed: {console_errors}"

    report = {
        "suite": "Phase 9 Browser E2E (Chromium)",
        "steps": steps,
        "console_errors": console_errors,
        "page_errors": page_errors,
        "screenshots": sorted([p.name for p in SCREENSHOTS_DIR.glob("*.png")]),
    }
    (FRONTEND_EVIDENCE_DIR / "phase9_browser_e2e_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
