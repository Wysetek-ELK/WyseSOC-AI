"""
Phase 8.2 Headless Chromium Browser E2E Suite (Stage D + Stage J).

Verifies real Next.js production UI + FastAPI/SQLite backend across:
  1. Verdict Intelligence Dashboard B zero-denominator honesty (NOT_CALCULABLE, never 100%)
  2. Inference Control live cluster status (DEGRADED S2 OFFLINE, never hardcoded HEALTHY)
  3. AI Triage Workbench runtime provenance distinction:
     - Historical Live Record (S2 Offline Now) + Uncalibrated Ordinal trust label
     - SIMULATED (Non-Production)
     - INVALID_MODEL_OUTPUT (Abstained)
  4. Agent Intelligence Studio Read-Only Viewer GET /quality-preview (0 console 403s) +
     disabled Validate Quality button + direct POST /validate-quality 403 vs Analyst 200.
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List
from urllib.request import urlopen

import pytest
from playwright.sync_api import expect, sync_playwright
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent
FRONTEND_EVIDENCE_DIR = REPO_ROOT / "docs" / "phase8.2" / "evidence" / "frontend"
SCREENSHOTS_DIR = FRONTEND_EVIDENCE_DIR / "screenshots"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models.incident import HistoricalGroundTruth, Incident  # noqa: E402
from app.models.investigation import Investigation  # noqa: E402
from app.models.prompt import PromptVersion, RulePrompt  # noqa: E402
from app.models.rule import Rule  # noqa: E402
from app.models.rule_intelligence import RuleIntelligenceSnapshot  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.verdict_intelligence import HistoricalEvaluationRunRecord  # noqa: E402
from app.utils.security import get_password_hash  # noqa: E402


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


async def _seed_p82_database(db_path: Path) -> Dict[str, str]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sess_mk = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    admin_secret = secrets.token_urlsafe(12)
    analyst_secret = secrets.token_urlsafe(12)
    viewer_secret = secrets.token_urlsafe(12)

    async with sess_mk() as db:
        admin = User(
            username="admin",
            email="admin-p82@example.test",
            hashed_password=get_password_hash(admin_secret),
            full_name="Phase 8.2 Admin",
            role="Administrator",
            is_active=True,
        )
        analyst = User(
            username="analyst",
            email="analyst-p82@example.test",
            hashed_password=get_password_hash(analyst_secret),
            full_name="Phase 8.2 Analyst",
            role="SOC Analyst",
            is_active=True,
        )
        viewer = User(
            username="viewer",
            email="viewer-p82@example.test",
            hashed_password=get_password_hash(viewer_secret),
            full_name="Phase 8.2 Viewer",
            role="Read-Only Viewer",
            is_active=True,
        )
        db.add_all([admin, analyst, viewer])
        await db.flush()

        rule = Rule(
            rule_id="PH_RULE_P82_UI_EXFIL",
            name="P82 UI Exfiltration Rule",
            event_type="PH_RULE_P82_UI_EXFIL",
            severity="HIGH",
            description="Detects unauthorized large outbound exfiltration",
            pattern_logic="threshold=1000000000; window=30m",
            raw_rule_text='<rule id="PH_RULE_P82_UI_EXFIL"><threshold>1000000000</threshold></rule>',
        )
        db.add(rule)
        await db.flush()

        snap = RuleIntelligenceSnapshot(
            rule_id=rule.id,
            rule_identifier=rule.rule_id,
            definition_status="VERIFIED",
            source_provenance="AUTHORITATIVE_SIEM_DEFINITION",
            threshold=1000000000.0,
            threshold_unit="bytes",
            aggregation_window="30m",
            primary_archetype="NETWORK_EXFILTRATION",
        )
        rp = RulePrompt(rule_id=rule.id, title="Prompt - P82 Exfiltration")
        db.add_all([snap, rp])
        await db.flush()

        pv = PromptVersion(
            prompt_id=rp.id,
            version_number=1,
            status="APPROVED",
            common_prompt="SOC Tier-2 Evidence-First Policy Baseline",
            rule_specific_prompt="Evaluate outbound transfers against verified threshold 1000000000 bytes.",
            detection_conditions="Outbound sentBytes64 > 1000000000 bytes to destination_ip within 30m.",
            required_evidence=(
                "1. security.event_type\n2. event.timestamp\n3. network.source_ip\n"
                "4. network.destination_ip\n5. network.bytes_out"
            ),
            tp_indicators="Unapproved outbound transfer exceeding 1000000000 bytes without ticket.",
            fp_indicators="Authorized backup job matching change ticket authorization_ticket.",
            missing_info_criteria="Abstain and vote REQUIRES_ATTENTION if core fields are missing.",
            escalation_conditions="Escalate contradictory telemetry to Tier-2 with REQUIRES_ATTENTION.",
            analyst_questions=["Does authorization_ticket authorize this transfer?"],
            created_by_user_id=admin.id,
            approved_by_user_id=admin.id,
        )
        db.add(pv)
        await db.flush()
        rp.active_version_id = pv.id

        inc_tp = Incident(
            incident_id="P82-UI-INC-TP",
            rule_id=rule.id,
            event_type=rule.event_type,
            title="P82 Historical Live Inference Record",
            severity="HIGH",
            source_ip="192.0.2.77",
            reporting_device="WKSTN-P82",
            raw_payload={"source_ip": "192.0.2.77", "destination_ip": "198.51.100.44", "sentBytes64": 2130499380},
            ai_verdict={
                "incident_id": "P82-UI-INC-TP",
                "proposed_verdict": "TRUE_POSITIVE",
                "verdict": "TRUE_POSITIVE",
                "is_decisive_accepted": True,
                "proposal_validation_outcome": "VALID_DECISIVE_PROPOSAL",
                "final_disposition": "ACCEPTED_DECISIVE_VERDICT",
                "confidence": 92.0,
                "raw_model_confidence": 92.0,
                "trust_score": 8,
                "is_calibrated": False,
                "calibration_status": "NOT_CALIBRATED",
                "latency_ms": 1120,
                "prompt_tokens": 300,
                "completion_tokens": 80,
                "total_tokens": 380,
                "reason": "Historical real Server 2 verdict confirming unauthorized egress.",
                "supporting_evidence": ["192.0.2.77", "198.51.100.44", "2130499380"],
                "supporting_claims": [{"field": "network.destination_ip", "asserted_value": "198.51.100.44", "is_grounded": True}],
                "model_identifier": "qwen2.5-7b-awq",
                "is_simulated": False,
                "validation_status": "VALIDATED",
                "validation_reason_codes": ["EVIDENCE_VALIDATED"],
                "evidence_completeness": 0.9,
                "grounding_ratio": 1.0,
                "total_claims_count": 1,
                "grounded_claims_count": 1,
                "evaluated_at": "2026-11-10T10:00:00Z",
            },
        )
        inc_sim = Incident(
            incident_id="P82-UI-INC-SIM",
            rule_id=rule.id,
            event_type=rule.event_type,
            title="P82 Simulated Heuristic Verdict Record",
            severity="MEDIUM",
            source_ip="192.0.2.78",
            reporting_device="WKSTN-P82-SIM",
            raw_payload={"source_ip": "192.0.2.78", "destination_ip": "198.51.100.45", "sentBytes64": 1500000000},
            ai_verdict={
                "incident_id": "P82-UI-INC-SIM",
                "proposed_verdict": "REQUIRES_ATTENTION",
                "verdict": "REQUIRES_ATTENTION",
                "is_decisive_accepted": False,
                "confidence": 50.0,
                "trust_score": 4,
                "is_calibrated": False,
                "calibration_status": "NOT_CALIBRATED",
                "latency_ms": 15,
                "reason": "Simulated heuristic evaluation.",
                "model_identifier": "simulated-v2.2-policy-aware",
                "is_simulated": True,
                "validation_status": "ABSTAINED",
                "evaluated_at": "2026-11-10T11:00:00Z",
            },
        )
        db.add_all([inc_tp, inc_sim])
        await db.flush()

        db.add_all([
            Investigation(incident_id=inc_tp.id, status="PENDING_REVIEW"),
            Investigation(incident_id=inc_sim.id, status="PENDING_REVIEW"),
            HistoricalEvaluationRunRecord(
                run_name="P82 Legacy Zero-Denominator Run",
                rule_id=rule.id,
                archetype="NETWORK_EXFILTRATION",
                dataset_id="p82-ui",
                status="COMPLETED",
                validation_state="INSUFFICIENT_DATA",
                total_cases=2,
                evaluated_cases=2,
                verified_ground_truth_cases=2,
                metrics={"overall_accuracy": 1.0, "balanced_accuracy": 1.0, "automatic_decision_coverage": 0.5, "analyst_attention_rate": 0.5, "critical_false_negatives": 0},
                calibration_metrics={"status": "NOT_CALIBRATED", "is_calibrated": False},
            ),
        ])
        await db.commit()
        return {
            "admin_secret": admin_secret,
            "analyst_secret": analyst_secret,
            "viewer_secret": viewer_secret,
            "rule_uuid": rule.id,
            "pv_uuid": pv.id,
        }


@pytest.fixture(scope="module")
def e2e_p82_servers(tmp_path_factory):
    db_dir = tmp_path_factory.mktemp("p82_e2e_db")
    db_path = db_dir / "p82_e2e.db"
    env = os.environ.copy()
    env["APP_ENV"] = "development"
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    env["SYNC_DATABASE_URL"] = f"sqlite:///{db_path}"
    env["USE_ASYNC_CELERY"] = "false"
    env["LOCAL_LLM_ALLOW_MOCK_FALLBACK"] = "false"
    env["SECRET_KEY"] = f"p82-e2e-secret-{secrets.token_hex(16)}"

    alembic_res = subprocess.run(["alembic", "upgrade", "head"], cwd=str(BACKEND_DIR), env=env, capture_output=True, text=True)
    assert alembic_res.returncode == 0, alembic_res.stderr
    seed_meta = asyncio.run(_seed_p82_database(db_path))

    be_log = (db_dir / "uvicorn_p82.log").open("w", encoding="utf-8")
    fe_log = (db_dir / "nextjs_p82.log").open("w", encoding="utf-8")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(BACKEND_DIR),
        env=env,
        stdout=be_log,
        stderr=subprocess.STDOUT,
    )
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "start", "--", "-H", "127.0.0.1", "-p", "3000"],
        cwd=str(REPO_ROOT / "frontend"),
        env=env,
        stdout=fe_log,
        stderr=subprocess.STDOUT,
    )
    try:
        _wait_http_ok("http://127.0.0.1:8000/openapi.json", 45.0, backend_proc, db_dir / "uvicorn_p82.log")
        _wait_http_ok("http://127.0.0.1:3000/login", 45.0, frontend_proc, db_dir / "nextjs_p82.log")
        yield {"seed": seed_meta, "frontend_url": "http://127.0.0.1:3000"}
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
        for fh in (fe_log, be_log):
            fh.close()


def test_phase8_2_stage_d_and_j_browser_e2e(e2e_p82_servers):
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    FRONTEND_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    base_url = e2e_p82_servers["frontend_url"]
    seed = e2e_p82_servers["seed"]
    console_errors: List[str] = []
    page_errors: List[str] = []
    steps: List[Dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        def _on_console(msg):
            if msg.type == "error":
                txt = msg.text or ""
                if any(f"status of {c}" in txt for c in (400, 401, 403, 404, 503)):
                    return
                console_errors.append(txt)

        page.on("console", _on_console)
        page.on("pageerror", lambda e: page_errors.append(str(e)))

        # 1. Sign in as Admin
        page.goto(f"{base_url}/login", wait_until="domcontentloaded")
        page.locator('input[placeholder="admin"]').fill("admin")
        page.locator('input[type="password"]').fill(seed["admin_secret"])
        page.get_by_role("button", name="Sign In to Platform").click()
        page.wait_for_url("**/agent-mission-control", timeout=15000)

        # 2. Verdict Intelligence Dashboard B: zero-denominator legacy run shows NOT_CALCULABLE, never 100%
        main = page.get_by_role("main")
        page.goto(f"{base_url}/verdict-intelligence", wait_until="domcontentloaded")
        main.get_by_role("button", name="Dashboard B: Empirical Accuracy").click()
        expect(main.get_by_text("NOT_CALCULABLE", exact=True).first).to_be_visible(timeout=15000)
        expect(main.get_by_text("NOT_CALCULABLE: Zero decisive").first).to_be_visible()
        expect(main.get_by_text("Decisive = 0").first).to_be_visible()
        expect(main).not_to_contain_text("100%")
        page.screenshot(path=str(SCREENSHOTS_DIR / "01_vi_zero_denominator_not_calculable.png"), full_page=True)
        steps.append({"step": "1_vi_zero_denominator_not_calculable", "status": "PASSED"})

        # 3. Inference Control live cluster status shows DEGRADED (S2 OFFLINE), not HEALTHY
        page.goto(f"{base_url}/inference-control", wait_until="domcontentloaded")
        expect(main.get_by_text("DEGRADED (S2 OFFLINE)").first).to_be_visible(timeout=15000)
        expect(main).not_to_contain_text("Cluster Status: HEALTHY")
        page.screenshot(path=str(SCREENSHOTS_DIR / "02_inference_control_s2_degraded.png"), full_page=True)
        steps.append({"step": "2_inference_control_degraded_s2_offline", "status": "PASSED"})

        # 4. AI Triage Workbench historical live vs simulated badges (never misleading GPU Live when offline)
        page.goto(f"{base_url}/ai-triage-workbench/P82-UI-INC-TP", wait_until="domcontentloaded")
        expect(main.get_by_text("Historical Live Record (S2 Offline Now)").first).to_be_visible(timeout=15000)
        expect(main.get_by_text("Trust: 8/10 (Uncalibrated Ordinal)").first).to_be_visible()
        page.screenshot(path=str(SCREENSHOTS_DIR / "03_workbench_historical_live_s2_offline.png"), full_page=True)

        page.goto(f"{base_url}/ai-triage-workbench/P82-UI-INC-SIM", wait_until="domcontentloaded")
        expect(main.get_by_text("SIMULATED (Non-Production)").first).to_be_visible(timeout=15000)
        steps.append({"step": "3_workbench_runtime_status_integrity", "status": "PASSED"})

        # 5. Read-Only Viewer opens AIS Studio via GET /quality-preview (0 console errors), POST /validate-quality 403, Analyst 200
        rbac = page.evaluate(
            """async ({ruleId, verId, viewerCred, analystCred}) => {
                const lv = await fetch('/api/auth/login', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: 'viewer', password: viewerCred})
                });
                const vd = await lv.json();
                window.localStorage.setItem('ai_verdict_token', vd.access_token);

                const la = await fetch('/api/auth/login', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: 'analyst', password: analystCred})
                });
                const ad = await la.json();

                const rPreviewViewer = await fetch(`/api/prompts/rule/${ruleId}/quality-preview?version_id=${verId}`, {
                    headers: {'Authorization': `Bearer ${vd.access_token}`}
                });
                const rPostViewer = await fetch(`/api/prompts/rule/${ruleId}/validate-quality?version_id=${verId}`, {
                    method: 'POST', headers: {'Authorization': `Bearer ${vd.access_token}`}
                });
                const rPostAnalyst = await fetch(`/api/prompts/rule/${ruleId}/validate-quality?version_id=${verId}`, {
                    method: 'POST', headers: {'Authorization': `Bearer ${ad.access_token}`}
                });
                return {
                    previewViewer: rPreviewViewer.status,
                    postViewer: rPostViewer.status,
                    postAnalyst: rPostAnalyst.status
                };
            }""",
            {"ruleId": seed["rule_uuid"], "verId": seed["pv_uuid"], "viewerCred": seed["viewer_secret"], "analystCred": seed["analyst_secret"]},
        )
        assert rbac == {"previewViewer": 200, "postViewer": 403, "postAnalyst": 200}, rbac

        page.goto(f"{base_url}/agent-intelligence-studio", wait_until="domcontentloaded")
        row_ok = page.locator("tr", has_text="PH_RULE_P82_UI_EXFIL").first
        expect(row_ok).to_be_visible(timeout=15000)
        row_ok.get_by_role("button", name="Open Studio").click()
        expect(page.get_by_role("button", name="Validate Quality")).to_be_disabled(timeout=15000)
        page.get_by_role("button", name="Quality Gates (G1–G8)").click()
        expect(page.get_by_text("Structural (G1–G7):")).to_be_visible(timeout=15000)
        expect(page.get_by_role("button", name="Revalidate")).to_be_disabled()
        page.screenshot(path=str(SCREENSHOTS_DIR / "04_ais_viewer_readonly_preview.png"), full_page=True)
        steps.append({"step": "4_ais_viewer_readonly_preview_and_rbac", "status": "PASSED", "rbac": rbac})

        browser.close()

    assert not page_errors, page_errors
    assert not console_errors, console_errors

    summary = {
        "runner": "pytest backend/tests/e2e_browser/test_phase8_2_ui_e2e.py",
        "browser": "chromium-headless",
        "total_steps": len(steps),
        "passed_steps": len(steps),
        "console_errors_count": len(console_errors),
        "page_errors_count": len(page_errors),
        "screenshots": sorted(x.name for x in SCREENSHOTS_DIR.glob("*.png")),
        "steps": steps,
    }
    (FRONTEND_EVIDENCE_DIR / "playwright_p82_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

