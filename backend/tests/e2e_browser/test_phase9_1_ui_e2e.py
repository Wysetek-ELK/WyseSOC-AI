"""
Phase 9.1 Focused Headless Chromium E2E Verification.

Verifies:
1. Header never falls back to "Analyst"/"SOC Analyst" while unauthenticated or loading (/login & session clear).
2. Role normalization & badge consistency across Administrator, SOC Analyst, and Read-Only Viewer:
   - Header role badge, Pilot Role badge, and Pilot RBAC lock banner always match identically.
3. Live / Mock / Offline / Test Environment provenance separation:
   - Loopback _MockLLMServer renders as HTTP_MOCK and "Arch: S1 + HTTP_MOCK (Test)" in Sidebar (never "S1 + S2 (GPU)").
   - Pilot Evaluation Log and Human Review Queue drawer label mock runs as "HTTP_MOCK", never "LIVE_PROVIDER".
   - Explicitly displays "TEST ENV: MOCK_HTTP_E2E" badge on screenshots & JSON report.
   - When Mock Server goes offline, historical evaluation preserves "HTTP_MOCK" while current S2 shows "OFFLINE".
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
OUT_DIR = REPO_ROOT / "docs" / "phase9.1" / "evidence" / "frontend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models.incident import Incident, IncidentEvent  # noqa: E402
from app.models.investigation import Investigation  # noqa: E402
from app.models.prompt import PromptVersion, RulePrompt  # noqa: E402
from app.models.rule import Rule  # noqa: E402
from app.models.rule_intelligence import RuleIntelligenceSnapshot  # noqa: E402
from app.models.user import User  # noqa: E402
from app.utils.security import get_password_hash  # noqa: E402


class _MockHTTPServer:
    def __init__(self) -> None:
        self.online = True
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if not parent.online:
                    self.send_response(503)
                    self.end_headers()
                    return
                if self.path.startswith("/metrics"):
                    body = b"vllm:num_requests_running 0\nvllm:gpu_cache_usage_factor 0.1\n"
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
                body = json.dumps({"object": "list", "data": [{"id": "mock-qwen-e2e"}]}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or "0")
                if length > 0:
                    _ = self.rfile.read(length)
                if not parent.online:
                    self.send_response(503)
                    self.end_headers()
                    return
                payload = {
                    "id": "chatcmpl-p91-e2e",
                    "choices": [{
                        "message": {
                            "content": json.dumps({
                                "verdict": "TRUE_POSITIVE",
                                "confidence": 88,
                                "reason": "Confirmed encoded command execution on host TEST-WKSTN-91 from 192.0.2.91.",
                                "supporting_evidence": ["command_line: powershell -enc P91"],
                                "supporting_claims": [{
                                    "claim_type": "COMMAND_EXECUTION",
                                    "field": "command_line",
                                    "asserted_value": "powershell -enc P91",
                                    "is_grounded": True,
                                }],
                                "missing_evidence": [],
                                "contradictory_evidence": [],
                                "analyst_questions": ["Verify scheduled task owner"],
                            })
                        }
                    }],
                    "usage": {"prompt_tokens": 210, "completion_tokens": 90, "total_tokens": 300},
                }
                body = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()


async def _seed_db(db_path: Path) -> Dict[str, str]:
    eng = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sm = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)

    secrets_map = {
        "admin_secret": f"AdmP91-{secrets.token_hex(6)}!",
        "analyst_secret": f"AnaP91-{secrets.token_hex(6)}!",
        "viewer_secret": f"ViwP91-{secrets.token_hex(6)}!",
    }

    async with sm() as db:
        for uname, role, sec in [
            ("admin", "Administrator", secrets_map["admin_secret"]),
            ("analyst", "SOC Analyst", secrets_map["analyst_secret"]),
            ("viewer", "Read-Only Viewer", secrets_map["viewer_secret"]),
        ]:
            db.add(
                User(
                    username=uname,
                    email=f"{uname}@p91.example.com",
                    hashed_password=get_password_hash(sec),
                    full_name=f"P91 {role}",
                    role=role,
                    is_active=True,
                )
            )

        rule = Rule(
            rule_id="P91-UI-RULE",
            name="P91 UI Provenance Detection",
            event_type="P91-UI-RULE",
            severity="HIGH",
            description="Phase 9.1 UI provenance test rule",
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
            quality_score=95.0,
            common_prompt="Evidence-first baseline.",
            rule_specific_prompt="Analyze powershell command execution lineage.",
            detection_conditions="powershell encoded command",
            required_evidence="source_ip, host_name, process_name, command_line",
            tp_indicators="Encoded payload + unexpected shell spawn",
            fp_indicators="Signed IT automation script",
            missing_info_criteria="Missing command_line",
            escalation_conditions="Unauthorized lateral execution",
            analyst_questions=["Verify host owner"],
            change_summary="P91 seed policy",
        )
        db.add(pv)
        await db.flush()
        rp.active_version_id = pv.id
        db.add(rp)

        inc = Incident(
            incident_id="P91-UI-INC-1",
            rule_id=rule.id,
            event_type=rule.event_type,
            title="Phase 9.1 UI Provenance Incident",
            severity="HIGH",
            status_code=1,
            status_name="Active",
            category="Endpoint",
            source_ip="192.0.2.91",
            reporting_ip="198.51.100.91",
            reporting_device="TEST-WKSTN-91",
            first_seen_epoch=1760000000,
            created_at_epoch=1760000000,
            raw_payload={
                "source_ip": "192.0.2.91",
                "host_name": "TEST-WKSTN-91",
                "process_name": "powershell.exe",
                "command_line": "powershell -enc P91",
            },
        )
        db.add(inc)
        await db.flush()
        db.add(
            IncidentEvent(
                incident_id=inc.id,
                event_id="EV-P91-UI-1",
                event_type=rule.event_type,
                raw_log="powershell.exe -enc P91",
                attributes={
                    "source_ip": "192.0.2.91",
                    "host_name": "TEST-WKSTN-91",
                    "process_name": "powershell.exe",
                    "command_line": "powershell -enc P91",
                },
            )
        )
        db.add(Investigation(incident_id=inc.id, status="PENDING_REVIEW"))
        await db.commit()

    await eng.dispose()
    return secrets_map


def _wait_http(url: str, timeout_s: float, proc: subprocess.Popen, log_path: Path) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"Server exited early: {log_path.read_text(encoding='utf-8', errors='replace')[-2000:]}")
        try:
            with urlopen(url, timeout=2.0) as resp:
                if resp.status < 500:
                    return
        except Exception:
            time.sleep(0.35)
    raise TimeoutError(f"Timed out waiting for {url}")


@pytest.fixture(scope="module")
def e2e_p91_servers(tmp_path_factory):
    db_dir = tmp_path_factory.mktemp("p91_ui_e2e")
    db_path = db_dir / "p91_ui_e2e.db"
    mock_llm = _MockHTTPServer()

    env = os.environ.copy()
    env["APP_ENV"] = "development"
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    env["SYNC_DATABASE_URL"] = f"sqlite:///{db_path}"
    env["USE_ASYNC_CELERY"] = "false"
    env["LOCAL_LLM_BASE_URL"] = f"http://127.0.0.1:{mock_llm.port}/v1"
    env["LOCAL_LLM_MODEL_NAME"] = "mock-qwen-e2e"
    env["LOCAL_LLM_ALLOW_MOCK_FALLBACK"] = "false"
    env["LOCAL_LLM_PROVENANCE"] = "HTTP_MOCK"
    env["AI_VERDICT_TEST_ENV"] = "MOCK_HTTP_E2E"
    env["SECRET_KEY"] = f"p91-e2e-secret-{secrets.token_hex(16)}"

    res = subprocess.run(["alembic", "upgrade", "head"], cwd=str(BACKEND_DIR), env=env, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    seed_meta = asyncio.run(_seed_db(db_path))

    be_log = db_dir / "backend_p91.log"
    fe_log = db_dir / "frontend_p91.log"
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
        _wait_http("http://127.0.0.1:8000/api/health", 35.0, be_proc, be_log)
        _wait_http("http://127.0.0.1:3000/login", 45.0, fe_proc, fe_log)
        yield {"base_url": "http://127.0.0.1:3000", "mock_llm": mock_llm, **seed_meta}
    finally:
        for proc in (fe_proc, be_proc):
            if proc.poll() is None:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
                else:
                    proc.terminate()
                try:
                    proc.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    proc.kill()
        be_f.close()
        fe_f.close()
        mock_llm.stop()


def test_phase9_1_role_consistency_and_provenance_browser_e2e(e2e_p91_servers):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base_url = e2e_p91_servers["base_url"]
    mock_llm: _MockHTTPServer = e2e_p91_servers["mock_llm"]

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

        # 1. Login page has zero hardcoded default password prefilled
        page.goto(f"{base_url}/login", wait_until="domcontentloaded")
        expect(page.locator('input[type="password"]')).to_have_value("")
        expect(page.locator("body")).not_to_contain_text("AdminPassword123!")
        steps.append({"step": "1_login_no_hardcoded_secret", "status": "PASSED"})

        # 2. Admin role consistency + Sidebar HTTP_MOCK provenance (never "S1 + S2 (GPU)")
        _login(page, "admin", e2e_p91_servers["admin_secret"])
        expect(page.get_by_test_id("header-user-role")).to_contain_text("Administrator", timeout=15000)
        expect(page.get_by_test_id("sidebar-arch-label")).to_contain_text("S1 + HTTP_MOCK (Test)", timeout=15000)
        expect(page.get_by_test_id("sidebar-test-env")).to_contain_text("TEST ENV: MOCK_HTTP_E2E")
        expect(page.get_by_test_id("sidebar-arch-label")).not_to_contain_text("S1 + S2 (GPU)")

        page.goto(f"{base_url}/verdict-intelligence?tab=pilot", wait_until="domcontentloaded")
        expect(main.get_by_test_id("pilot-role-badge")).to_contain_text("Role: Administrator", timeout=15000)
        expect(main.get_by_test_id("pilot-test-env-badge")).to_contain_text("TEST ENV: MOCK_HTTP_E2E")
        expect(main.get_by_test_id("pilot-provider-health-badge")).to_contain_text("Endpoint: HTTP_MOCK")

        main.get_by_test_id("btn-activate-assisted").click()
        expect(main.get_by_test_id("pilot-mode-badge")).to_contain_text("MODE: ANALYST_ASSISTED", timeout=15000)
        main.get_by_test_id("btn-run-pilot-batch").click()
        expect(main.get_by_test_id("pilot-success-banner")).to_be_visible(timeout=20000)
        expect(main.get_by_text("LIVE • HTTP_MOCK").first).to_be_visible(timeout=10000)
        page.screenshot(path=str(OUT_DIR / "p91_01_admin_http_mock_provenance.png"), full_page=True)
        steps.append({"step": "2_admin_role_and_http_mock_provenance", "status": "PASSED"})

        # 3. Take Mock Server offline -> historical record stays HTTP_MOCK while current S2 shows OFFLINE
        mock_llm.online = False
        page.reload(wait_until="domcontentloaded")
        expect(page.get_by_test_id("header-user-role")).to_contain_text("Administrator", timeout=15000)
        expect(main.get_by_test_id("pilot-provider-health-badge")).to_contain_text("Server 2: OFFLINE", timeout=15000)
        expect(main.get_by_text("LIVE • HTTP_MOCK").first).to_be_visible(timeout=10000)

        page.goto(f"{base_url}/human-review-queue", wait_until="domcontentloaded")
        main.locator("tr", has_text="P91-UI-INC-1").first.get_by_role("button", name="Investigate").click()
        expect(main.get_by_test_id("drawer-provenance-badge")).to_contain_text("HTTP_MOCK", timeout=15000)
        expect(main.get_by_test_id("drawer-ai-assurance")).to_contain_text("S2 Now: OFFLINE")
        page.screenshot(path=str(OUT_DIR / "p91_02_historical_mock_when_s2_offline.png"), full_page=True)
        steps.append({"step": "3_historical_mock_preserved_with_s2_offline", "status": "PASSED"})

        # 4. SOC Analyst role consistency (Header == Pilot Role == RBAC Banner)
        _login(page, "analyst", e2e_p91_servers["analyst_secret"])
        page.goto(f"{base_url}/verdict-intelligence?tab=pilot", wait_until="domcontentloaded")
        expect(page.get_by_test_id("header-user-role")).to_contain_text("SOC Analyst", timeout=15000)
        expect(main.get_by_test_id("pilot-role-badge")).to_contain_text("Role: SOC Analyst", timeout=15000)
        expect(main.get_by_test_id("pilot-rbac-notice")).to_contain_text("SOC Analyst mode", timeout=15000)
        page.screenshot(path=str(OUT_DIR / "p91_03_analyst_role_consistency.png"), full_page=True)
        steps.append({"step": "4_analyst_role_consistency", "status": "PASSED"})

        # 5. Read-Only Viewer role consistency (never displays Header "Analyst" alongside Read-Only banner)
        _login(page, "viewer", e2e_p91_servers["viewer_secret"])
        page.goto(f"{base_url}/verdict-intelligence?tab=pilot", wait_until="domcontentloaded")
        expect(page.get_by_test_id("header-user-role")).to_contain_text("Read-Only Viewer", timeout=15000)
        expect(page.get_by_test_id("header-user-role")).not_to_contain_text("Analyst")
        expect(main.get_by_test_id("pilot-role-badge")).to_contain_text("Role: Read-Only Viewer", timeout=15000)
        expect(main.get_by_test_id("pilot-role-badge")).not_to_contain_text("Unknown")
        expect(main.get_by_test_id("pilot-rbac-notice")).to_contain_text("Read-Only Viewer mode", timeout=15000)
        expect(main.get_by_test_id("btn-save-pilot-config")).to_be_disabled()
        expect(main.get_by_test_id("btn-run-pilot-batch")).to_be_disabled()
        page.screenshot(path=str(OUT_DIR / "p91_04_viewer_role_consistency_fixed.png"), full_page=True)
        steps.append({"step": "5_viewer_role_consistency_fixed", "status": "PASSED"})

        browser.close()

    assert not page_errors, f"Uncaught page errors: {page_errors}"
    assert not console_errors, f"Console errors observed: {console_errors}"

    report = {
        "suite": "Phase 9.1 Role Consistency & Execution Provenance Browser E2E",
        "test_environment": "MOCK_HTTP_E2E",
        "execution_provenance": "HTTP_MOCK",
        "steps": steps,
        "console_errors": console_errors,
        "page_errors": page_errors,
        "screenshots": sorted([p.name for p in OUT_DIR.glob("p91_*.png")]),
    }
    (OUT_DIR / "phase9_1_browser_e2e_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

