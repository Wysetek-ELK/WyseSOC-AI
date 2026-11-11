"""
Phase 8.1 Stage 10: Real Headless Chromium Frontend E2E Verification (Playwright).

Spins up an isolated Alembic-migrated SQLite database, a real FastAPI uvicorn
server on 127.0.0.1:8000, and the compiled Next.js production server on
127.0.0.1:3000, then verifies AIS 3-tier eligibility separation, AI Triage Workbench
INVALID_MODEL_OUTPUT / SAFE_ABSTENTION_AFTER_INVALID_OUTPUT / Trust Score rendering,
GT isolation, offline fail-closed safety, Verdict Intelligence DOM-to-API parity,
and Human Review Queue reload persistence under `docs/phase8.1/evidence/browser/`.
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

import pytest
from playwright.sync_api import expect, sync_playwright
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"
BROWSER_DIR = REPO_ROOT / "docs" / "phase8.1" / "evidence" / "browser"
SCREENSHOTS_DIR = BROWSER_DIR / "screenshots"

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


async def _seed_p81_database(db_path: Path) -> Dict[str, str]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    admin_secret = f"P81-Adm-{secrets.token_hex(6)}!"
    viewer_secret = f"P81-Vwr-{secrets.token_hex(6)}!"

    async with SessionLocal() as db:
        admin = User(
            username="admin",
            email="admin-p81@example.com",
            hashed_password=get_password_hash(admin_secret),
            full_name="Phase 8.1 Administrator",
            role="Administrator",
            is_active=True,
        )
        viewer = User(
            username="viewer",
            email="viewer-p81@example.com",
            hashed_password=get_password_hash(viewer_secret),
            full_name="Phase 8.1 Viewer",
            role="Read-Only Viewer",
            is_active=True,
        )
        db.add_all([admin, viewer])
        await db.flush()

        rule_ok = Rule(
            rule_id="PH_RULE_P81_UI_EXFIL",
            name="Phase 8.1 Exfiltration Policy Rule",
            event_type="PH_RULE_P81_UI_EXFIL",
            severity="HIGH",
            description="Detects large outbound exfiltration transfers",
            pattern_logic="sentBytes64 > 1000000000 AND direction == 'outbound'",
            status="ACTIVE",
            parsed_metadata={"definition_status": "VERIFIED"},
        )
        rule_inc = Rule(
            rule_id="PH_RULE_P81_UI_INCOMPLETE",
            name="Phase 8.1 Incomplete Threshold Rule",
            event_type="PH_RULE_P81_UI_INCOMPLETE",
            severity="HIGH",
            description="Detects excessive outbound exfiltration without threshold",
            pattern_logic="sentBytes64 > UNKNOWN_THRESHOLD",
            status="ACTIVE",
            parsed_metadata={"definition_status": "INCOMPLETE"},
        )
        db.add_all([rule_ok, rule_inc])
        await db.flush()

        db.add_all([
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
                primary_archetype="NETWORK_EXFILTRATION",
                definition_status="INCOMPLETE",
                threshold=None,
                source_provenance="MISSING_THRESHOLD",
            ),
        ])

        rp_ok = RulePrompt(rule_id=rule_ok.id)
        rp_inc = RulePrompt(rule_id=rule_inc.id)
        db.add_all([rp_ok, rp_inc])
        await db.flush()

        pv_ok = PromptVersion(
            prompt_id=rp_ok.id,
            version_number=1,
            status="APPROVED",
            common_prompt="Tier-2 SOC Policy Baseline",
            rule_specific_prompt="Evaluate outbound exfiltration alerts strictly against observed bytes and change tickets.",
            detection_conditions="sentBytes64 > 1000000000 AND direction == 'outbound'",
            required_evidence="network.source_ip, network.destination_ip, network.bytes_out, network.direction",
            tp_indicators="Unapproved outbound transfer sentBytes64 > 1000000000",
            fp_indicators="Verified maintenance backup ticket authorization_ticket",
            missing_info_criteria="Abstain to REQUIRES_ATTENTION when destination_ip is absent.",
            escalation_conditions="Contradictory telemetry forces REQUIRES_ATTENTION.",
            analyst_questions=["Verify business change ticket."],
            created_by_user_id=admin.id,
            approved_by_user_id=admin.id,
        )
        pv_inc = PromptVersion(
            prompt_id=rp_inc.id,
            version_number=1,
            status="DRAFT",
            common_prompt="Tier-2 SOC Policy Baseline",
            rule_specific_prompt="Evaluate incomplete threshold rule.",
            detection_conditions="threshold missing",
            required_evidence="network.source_ip, network.destination_ip",
            tp_indicators="Unapproved transfer",
            fp_indicators="Scheduled backup",
            missing_info_criteria="Abstain if missing",
            escalation_conditions="Escalate if unclear",
            analyst_questions=["Check threshold"],
            created_by_user_id=admin.id,
        )
        db.add_all([pv_ok, pv_inc])
        await db.flush()
        rp_ok.active_version_id = pv_ok.id
        db.add(rp_ok)

        inc_tp = Incident(
            incident_id="P81-UI-INC-TP",
            rule_id=rule_ok.id,
            event_type=rule_ok.event_type,
            title="P8.1 Validated Exfiltration Incident",
            severity="HIGH",
            source_ip="192.0.2.77",
            reporting_device="WKSTN-P81",
            raw_payload={
                "source_ip": "192.0.2.77",
                "destination_ip": "198.51.100.44",
                "sentBytes64": 2130499380,
                "direction": "outbound",
                "clearedReason": "P81_SECRET_GT_TOKEN",
            },
            ai_verdict={
                "incident_id": "P81-UI-INC-TP",
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
                "latency_ms": 1240,
                "prompt_tokens": 310,
                "completion_tokens": 90,
                "total_tokens": 400,
                "reason": "Confirmed outbound 2130499380 bytes to 198.51.100.44.",
                "supporting_evidence": ["192.0.2.77", "198.51.100.44", "2130499380"],
                "supporting_claims": [
                    {"field": "network.destination_ip", "asserted_value": "198.51.100.44", "is_grounded": True, "grounding_status": "GROUNDED"}
                ],
                "model_identifier": "local-qwen-test",
                "is_simulated": False,
                "validation_status": "VALIDATED",
                "validation_reason_codes": ["EVIDENCE_VALIDATED"],
                "evidence_completeness": 0.9,
                "grounding_ratio": 1.0,
                "total_claims_count": 1,
                "grounded_claims_count": 1,
            },
        )
        inc_invalid = Incident(
            incident_id="P81-UI-INC-INVALID",
            rule_id=rule_ok.id,
            event_type=rule_ok.event_type,
            title="P8.1 Malformed Model Output Abstention Incident",
            severity="HIGH",
            source_ip="192.0.2.99",
            reporting_device="WKSTN-P81-INV",
            raw_payload={
                "source_ip": "192.0.2.99",
                "destination_ip": "198.51.100.88",
                "sentBytes64": 1900000000,
                "direction": "outbound",
            },
            ai_verdict={
                "incident_id": "P81-UI-INC-INVALID",
                "proposed_verdict": "MALICIOUS_MAYBE",
                "verdict": "REQUIRES_ATTENTION",
                "is_decisive_accepted": False,
                "proposal_validation_outcome": "INVALID_MODEL_OUTPUT",
                "final_disposition": "SAFE_ABSTENTION_AFTER_INVALID_OUTPUT",
                "abstention_reason": "Model returned invalid or malformed structured output; safely abstained.",
                "confidence": 0.0,
                "raw_model_confidence": 82.0,
                "trust_score": 1,
                "is_calibrated": False,
                "calibration_status": "NOT_CALIBRATED",
                "latency_ms": 840,
                "prompt_tokens": 280,
                "completion_tokens": 35,
                "total_tokens": 315,
                "reason": "Model returned malformed output; routed safely to analyst review.",
                "supporting_evidence": [],
                "supporting_claims": [],
                "model_identifier": "local-qwen-test",
                "is_simulated": False,
                "validation_status": "INVALID_MODEL_OUTPUT",
                "validation_reason_codes": ["MODEL_OUTPUT_INVALID"],
                "evidence_completeness": 0.85,
                "grounding_ratio": 0.0,
                "total_claims_count": 0,
                "grounded_claims_count": 0,
            },
        )
        inc_queue = Incident(
            incident_id="P81-UI-INC-QUEUE",
            rule_id=rule_ok.id,
            event_type=rule_ok.event_type,
            title="P8.1 Pending Triage & Human Queue Incident",
            severity="MEDIUM",
            source_ip="192.0.2.55",
            reporting_device="WKSTN-P81-Q",
            raw_payload={
                "source_ip": "192.0.2.55",
                "destination_ip": "198.51.100.25",
                "sentBytes64": 1200000000,
                "direction": "outbound",
            },
        )
        db.add_all([inc_tp, inc_invalid, inc_queue])
        await db.flush()

        db.add_all([
            HistoricalGroundTruth(
                incident_id=inc_tp.id,
                resolution="True Positive",
                cleared_reason="P81_SECRET_GT_TOKEN",
                comments="P81_SECRET_GT_TOKEN ground truth",
                is_ml_generated=False,
            ),
            Investigation(incident_id=inc_tp.id, status="PENDING_REVIEW"),
            Investigation(incident_id=inc_invalid.id, status="PENDING_REVIEW"),
            Investigation(incident_id=inc_queue.id, status="PENDING_REVIEW"),
            VerdictTrustAssessmentRecord(
                incident_id="P81-UI-INC-TP",
                rule_id=rule_ok.id,
                archetype="NETWORK_EXFILTRATION",
                suggested_verdict="TRUE_POSITIVE",
                effective_verdict="TRUE_POSITIVE",
                trust_score=8,
                raw_trust_score=82.0,
                evidence_sufficiency_score=86.0,
                evidence_status="SUFFICIENT",
                historical_validation_status="UNCALIBRATED",
                is_calibrated=False,
                model_identifier="local-qwen-test",
                is_simulated=False,
            ),
            VerdictTrustAssessmentRecord(
                incident_id="P81-UI-INC-INVALID",
                rule_id=rule_ok.id,
                archetype="NETWORK_EXFILTRATION",
                suggested_verdict="MALICIOUS_MAYBE",
                effective_verdict="REQUIRES_ANALYST_ATTENTION",
                trust_score=1,
                raw_trust_score=15.0,
                evidence_sufficiency_score=85.0,
                evidence_status="SUFFICIENT",
                historical_validation_status="UNCALIBRATED",
                is_calibrated=False,
                escalation_reason="INVALID_MODEL_OUTPUT",
                model_identifier="local-qwen-test",
                is_simulated=False,
            ),
            EvidenceSufficiencyAssessmentRecord(
                incident_id="P81-UI-INC-TP",
                rule_id=rule_ok.id,
                archetype="NETWORK_EXFILTRATION",
                overall_sufficiency_score=86.0,
                required_coverage_score=40.0,
                evidence_status="SUFFICIENT",
            ),
            HistoricalEvaluationRunRecord(
                run_name="Phase 8.1 Baseline Uncalibrated Run",
                rule_id=rule_ok.id,
                archetype="NETWORK_EXFILTRATION",
                dataset_id="p81-ui",
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
        res_meta = {
            "admin_secret": admin_secret,
            "viewer_secret": viewer_secret,
            "rule_inc_uuid": rule_inc.id,
            "pv_inc_uuid": pv_inc.id,
        }
    await engine.dispose()
    return res_meta


@pytest.fixture(scope="module")
def e2e_p81_servers(tmp_path_factory):
    _assert_port_free("127.0.0.1", 8000)
    _assert_port_free("127.0.0.1", 3000)

    db_dir = tmp_path_factory.mktemp("p81_e2e_db")
    db_path = db_dir / "p81_e2e.db"
    env = os.environ.copy()
    env["APP_ENV"] = "development"
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    env["SYNC_DATABASE_URL"] = f"sqlite:///{db_path}"
    env["USE_ASYNC_CELERY"] = "false"
    env["LOCAL_LLM_ALLOW_MOCK_FALLBACK"] = "false"
    env["SECRET_KEY"] = f"p81-e2e-secret-{secrets.token_hex(16)}"

    alembic_res = subprocess.run(["alembic", "upgrade", "head"], cwd=str(BACKEND_DIR), env=env, capture_output=True, text=True)
    assert alembic_res.returncode == 0, alembic_res.stderr
    seed_meta = asyncio.run(_seed_p81_database(db_path))

    be_log = (db_dir / "uvicorn_p81.log").open("w", encoding="utf-8")
    fe_log = (db_dir / "nextjs_p81.log").open("w", encoding="utf-8")
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
        cwd=str(FRONTEND_DIR),
        env=os.environ.copy(),
        stdout=fe_log,
        stderr=subprocess.STDOUT,
    )

    try:
        _wait_http_ok("http://127.0.0.1:8000/openapi.json", timeout_s=45.0, proc=backend_proc, log_path=db_dir / "uvicorn_p81.log")
        _wait_http_ok("http://127.0.0.1:3000/login", timeout_s=45.0, proc=frontend_proc, log_path=db_dir / "nextjs_p81.log")
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
            try:
                fh.close()
            except Exception:
                pass


def test_phase8_1_stage10_browser_e2e(e2e_p81_servers):
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    BROWSER_DIR.mkdir(parents=True, exist_ok=True)
    stale_dbg = SCREENSHOTS_DIR / "_failure_debug.png"
    if stale_dbg.exists():
        stale_dbg.unlink()

    base_url = e2e_p81_servers["frontend_url"]
    seed = e2e_p81_servers["seed"]
    console_errors: List[str] = []
    page_errors: List[str] = []
    steps: List[Dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()

        def _on_console(msg):
            if msg.type == "error":
                txt = msg.text or ""
                if any(f"status of {code}" in txt for code in (400, 401, 403, 404, 503)):
                    return
                console_errors.append(txt)

        page.on("console", _on_console)
        page.on("pageerror", lambda e: page_errors.append(str(e)))

        try:
            # 1. Login negative + positive
            page.goto(f"{base_url}/login", wait_until="domcontentloaded")
            page.locator('input[placeholder="admin"]').fill("admin")
            page.locator('input[type="password"]').fill("BadPass123!")
            page.get_by_role("button", name="Sign In to Platform").click()
            expect(page.locator("text=/invalid|incorrect|failed|401/i").first).to_be_visible(timeout=10000)
            steps.append({"step": "1_login_error_state", "status": "PASSED"})

            page.locator('input[type="password"]').fill(seed["admin_secret"])
            page.get_by_role("button", name="Sign In to Platform").click()
            page.wait_for_url("**/agent-mission-control", timeout=15000)
            token = page.evaluate("() => window.localStorage.getItem('ai_verdict_token')")
            assert token and len(token) > 20
            steps.append({"step": "2_login_success_session", "status": "PASSED"})

            # 2. AIS Studio — 3-tier eligibility separation + Incomplete G1 block + Viewer 403 / Admin 400
            page.goto(f"{base_url}/agent-intelligence-studio", wait_until="domcontentloaded")
            row_ok = page.locator("tr", has_text="PH_RULE_P81_UI_EXFIL").first
            expect(row_ok).to_be_visible(timeout=15000)
            row_ok.get_by_role("button", name="Open Studio").click()
            page.get_by_role("button", name="Quality Gates (G1–G8)").click()
            page.get_by_role("button", name="Validate Quality").click()
            expect(page.get_by_text("Structural (G1–G7):")).to_be_visible(timeout=15000)
            expect(page.get_by_text("REQUIRES G8 PASS")).to_be_visible(timeout=10000)
            page.screenshot(path=str(SCREENSHOTS_DIR / "01_ais_3tier_eligibility.png"), full_page=True)
            steps.append({"step": "3_ais_three_tier_eligibility", "status": "PASSED"})

            page.goto(f"{base_url}/agent-intelligence-studio", wait_until="domcontentloaded")
            page.locator("tr", has_text="PH_RULE_P81_UI_INCOMPLETE").first.get_by_role("button", name="Open Studio").click()
            expect(page.get_by_role("button", name="Approve & Activate")).to_be_disabled()
            rbac = page.evaluate(
                """async ({adminToken, ruleId, verId, viewerCred}) => {
                    const lr = await fetch('/api/auth/login', {
                        method: 'POST', headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({username: 'viewer', password: viewerCred})
                    });
                    const vd = await lr.json();
                    const r1 = await fetch(`/api/prompts/rule/${ruleId}/approve/${verId}`, {
                        method: 'POST', headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${vd.access_token}`},
                        body: JSON.stringify({change_summary: 'viewer'})
                    });
                    const r2 = await fetch(`/api/prompts/rule/${ruleId}/approve/${verId}`, {
                        method: 'POST', headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${adminToken}`},
                        body: JSON.stringify({change_summary: 'admin incomplete'})
                    });
                    return {viewer: r1.status, admin: r2.status};
                }""",
                {"adminToken": token, "ruleId": seed["rule_inc_uuid"], "verId": seed["pv_inc_uuid"], "viewerCred": seed["viewer_secret"]},
            )
            assert rbac == {"viewer": 403, "admin": 400}, rbac
            steps.append({"step": "4_ais_incomplete_and_rbac", "status": "PASSED", "rbac": rbac})

            # 3. AI Triage Workbench — GT isolation on TP + New P8.1 INVALID_MODEL_OUTPUT & Trust: 1/10 UI
            main = page.get_by_role("main")
            page.goto(f"{base_url}/ai-triage-workbench/P81-UI-INC-TP", wait_until="domcontentloaded")
            expect(main.get_by_text("TRUE POSITIVE").first).to_be_visible(timeout=15000)
            expect(main.get_by_text("Trust: 8/10")).to_be_visible()
            main.get_by_role("button", name="Evidence Integrity Guardrail").click()
            expect(main.get_by_text("Evidence Integrity Guardrail").first).to_be_visible()
            # Enable Blind Review mode so analyst UI hides SIEM Resolution & GT across full page
            page.get_by_role("button", name="Blind Review: OFF").last.click()
            expect(page.get_by_role("button", name="Blind Review: ON").first).to_be_visible(timeout=10000)
            expect(page.locator("body")).not_to_contain_text("P81_SECRET_GT_TOKEN")
            page.get_by_role("button", name="Blind Review: ON").last.click()
            steps.append({"step": "5_workbench_tp_gt_isolation", "status": "PASSED"})

            page.goto(f"{base_url}/ai-triage-workbench/P81-UI-INC-INVALID", wait_until="domcontentloaded")
            expect(main.get_by_text("INVALID_MODEL_OUTPUT").first).to_be_visible(timeout=15000)
            expect(main.get_by_text("Trust: 1/10")).to_be_visible()
            expect(main.get_by_text("SAFE_ABSTENTION_AFTER_INVALID_OUTPUT")).to_be_visible()
            expect(page.locator("body")).not_to_contain_text("VERIFIED ACCEPTED")
            page.screenshot(path=str(SCREENSHOTS_DIR / "02_workbench_invalid_output_abstained.png"), full_page=True)
            steps.append({"step": "6_workbench_invalid_model_output_ui", "status": "PASSED"})

            # Offline fail-closed + 404 check
            page.goto(f"{base_url}/ai-triage-workbench/P81-UI-INC-QUEUE", wait_until="domcontentloaded")
            main.get_by_role("button", name="Verdict Triage Agent").click()
            expect(main.locator("text=/offline|unavailable|failed|error/i").first).to_be_visible(timeout=15000)
            steps.append({"step": "7_workbench_offline_fail_closed", "status": "PASSED"})

            # 4. Verdict Intelligence DOM-to-API parity & uncalibrated warning
            with page.expect_response(lambda r: "/api/verdict-intelligence/metrics/summary" in r.url and r.status == 200) as resp_info:
                page.goto(f"{base_url}/verdict-intelligence", wait_until="domcontentloaded")
            api_sum = resp_info.value.json()
            expect(main.locator("div", has_text="Total Evaluated Cases").filter(has_text=str(api_sum["total_evaluated_incidents"])).first).to_be_visible(timeout=10000)
            expect(main.locator("label", has_text="Allow simulation fallback").locator("input[type='checkbox']")).not_to_be_checked()
            main.get_by_role("button", name="Dashboard B: Empirical Accuracy").click()
            expect(main.get_by_text("Status: NOT_CALIBRATED")).to_be_visible(timeout=10000)
            page.screenshot(path=str(SCREENSHOTS_DIR / "03_verdict_intelligence_uncalibrated.png"), full_page=True)
            steps.append({"step": "8_verdict_intelligence_parity", "status": "PASSED"})

            # 5. Human Review Queue reload persistence
            page.goto(f"{base_url}/human-review-queue", wait_until="domcontentloaded")
            main.locator("tr", has_text="P81-UI-INC-QUEUE").first.get_by_role("button", name="Investigate").click()
            main.get_by_role("button", name="False Positive").click()
            main.locator('textarea[placeholder="Explain the definitive rationale for this verdict..."]').fill("Phase 8.1 UI verified scheduled task.")
            with page.expect_response(lambda r: "/api/investigations/" in r.url and r.request.method in ("POST", "PUT", "PATCH")) as vs:
                main.get_by_role("button", name="Finalize & Save Verified Verdict").click()
            assert vs.value.status < 300
            expect(main.locator("tr", has_text="P81-UI-INC-QUEUE").first).to_contain_text("REVIEWED", timeout=15000)
            page.reload(wait_until="domcontentloaded")
            expect(main.locator("tr", has_text="P81-UI-INC-QUEUE").first).to_contain_text("False Positive", timeout=15000)
            page.screenshot(path=str(SCREENSHOTS_DIR / "04_human_review_persisted.png"), full_page=True)
            steps.append({"step": "9_human_review_queue_reload_persistence", "status": "PASSED"})

        except Exception:
            try:
                page.screenshot(path=str(SCREENSHOTS_DIR / "_failure_debug.png"), full_page=True)
            except Exception:
                pass
            raise
        finally:
            context.tracing.stop(path=str(BROWSER_DIR / "playwright_e2e_trace.zip"))
            browser.close()

    assert not page_errors, page_errors
    assert not console_errors, console_errors

    summary = {
        "runner": "pytest backend/tests/e2e_browser/test_phase8_1_ui_e2e.py",
        "browser": "chromium-headless",
        "total_steps": len(steps),
        "passed_steps": sum(1 for s in steps if s["status"] == "PASSED"),
        "console_errors_count": len(console_errors),
        "page_errors_count": len(page_errors),
        "screenshots_captured": sorted(p.name for p in SCREENSHOTS_DIR.glob("*.png")),
        "steps": steps,
    }
    (BROWSER_DIR / "playwright_p81_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
