#!/usr/bin/env python3
"""
AI Verdict — Integration Readiness Runner (Phase 9 Stage 10).

Explicitly separated execution modes:
  - OFFLINE_CONTRACT_TESTS     : Local wire-contract & schema/config validation without external hosts
  - STAGING_INTEGRATION_TESTS  : Live probes against PostgreSQL, Redis/Celery, FortiSIEM, and Server 2
  - LIVE_MODEL_VALIDATION      : Real Server 2 vLLM chat completion, structured JSON verdict, and timeout checks

Never silently substitutes a mock provider for live infrastructure.
Unavailable external services report BLOCKED / NOT_TESTED (never PASS).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

VALID_MODES = ("OFFLINE_CONTRACT_TESTS", "STAGING_INTEGRATION_TESTS", "LIVE_MODEL_VALIDATION")


def probe_tcp(host: str, port: int, timeout: float = 2.0) -> Dict[str, Any]:
    if not host:
        return {"reachable": False, "error": "Host not configured"}
    try:
        t0 = time.monotonic()
        with socket.create_connection((host, port), timeout=timeout):
            return {"reachable": True, "latency_ms": round((time.monotonic() - t0) * 1000, 1)}
    except Exception as exc:
        return {"reachable": False, "error": f"{type(exc).__name__}: {exc}"}


def run_offline_contract_tests() -> Dict[str, Any]:
    checks: Dict[str, Any] = {}

    # 1. Server 1 <-> Server 2 OpenAI wire contract & JSON repair
    res_wire = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_model_provider.py", "tests/test_phase8_2_validation.py", "-k", "model_provider or wire"],
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
    )
    checks["server1_server2_contract"] = {
        "status": "PASSED" if res_wire.returncode == 0 else "FAILED",
        "exit_code": res_wire.returncode,
        "summary": res_wire.stdout.strip().splitlines()[-1] if res_wire.stdout.strip() else "",
    }

    # 2. App <-> PostgreSQL dialect compile + Alembic 008 roundtrip + DistributedLock
    res_db = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_database_migrations.py", "tests/test_postgresql_and_pooling.py"],
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
    )
    checks["app_postgresql_contract"] = {
        "status": "PASSED" if res_db.returncode == 0 else "FAILED",
        "exit_code": res_db.returncode,
        "summary": res_db.stdout.strip().splitlines()[-1] if res_db.stdout.strip() else "",
    }

    # 3. App <-> Redis/Celery task routing & state machine contract
    res_wrk = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_celery_queues.py"],
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
    )
    checks["app_redis_celery_contract"] = {
        "status": "PASSED" if res_wrk.returncode == 0 else "FAILED",
        "exit_code": res_wrk.returncode,
        "summary": res_wrk.stdout.strip().splitlines()[-1] if res_wrk.stdout.strip() else "",
    }

    # 4. App <-> FortiSIEM ingestion, dedup, XML rule parsing, triggering event enrichment
    res_siem = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_fortisiem_pull.py", "tests/test_rule_parser.py"],
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
    )
    checks["app_fortisiem_contract"] = {
        "status": "PASSED" if res_siem.returncode == 0 else "FAILED",
        "exit_code": res_siem.returncode,
        "summary": res_siem.stdout.strip().splitlines()[-1] if res_siem.stdout.strip() else "",
    }

    overall = "PASSED" if all(c["status"] == "PASSED" for c in checks.values()) else "FAILED"
    return {
        "mode": "OFFLINE_CONTRACT_TESTS",
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "overall_status": overall,
        "checks": checks,
    }


async def run_staging_probes(mode: str) -> Dict[str, Any]:
    from app.config import settings
    from deployment.scripts.smoke_test_server2 import run_smoke_test

    checks: Dict[str, Any] = {}

    # 1. Server 1 <-> Server 2 probe
    llm_url = str(getattr(settings, "LOCAL_LLM_BASE_URL", "") or "")
    parsed_llm = urlparse(llm_url)
    llm_host = parsed_llm.hostname or ""
    llm_port = parsed_llm.port or (443 if parsed_llm.scheme == "https" else 8000)
    llm_tcp = probe_tcp(llm_host, llm_port, timeout=2.0)

    if not llm_tcp["reachable"]:
        checks["server1_to_server2"] = {
            "status": "BLOCKED",
            "classification": "NOT_TESTED",
            "target": f"{parsed_llm.scheme}://<configured>:{llm_port}",
            "reason": llm_tcp["error"],
        }
    else:
        smoke = run_smoke_test(
            base_url=llm_url,
            model=settings.LOCAL_LLM_MODEL_NAME,
            api_key=settings.LOCAL_LLM_API_KEY,
            timeout=float(settings.LOCAL_LLM_TIMEOUT or 30.0),
        )
        if smoke.get("execution_provenance") == "HTTP_MOCK":
            checks["server1_to_server2"] = {
                "status": "BLOCKED",
                "classification": "NOT_TESTED",
                "execution_provenance": "HTTP_MOCK",
                "reason": "Loopback/mock HTTP endpoint detected; cannot certify LIVE_MODEL_VALIDATION against HTTP_MOCK.",
                "checks": smoke["checks"],
            }
        else:
            checks["server1_to_server2"] = {
                "status": smoke["overall_status"],
                "classification": smoke["overall_status"],
                "execution_provenance": smoke.get("execution_provenance", "LIVE_PROVIDER"),
                "checks": smoke["checks"],
            }

    if mode == "LIVE_MODEL_VALIDATION":
        return {
            "mode": mode,
            "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "overall_status": checks["server1_to_server2"]["status"],
            "checks": checks,
        }

    # 2. App <-> PostgreSQL probe
    db_url = str(getattr(settings, "DATABASE_URL", "") or "")
    if "postgresql" not in db_url.lower():
        checks["app_to_postgresql"] = {
            "status": "BLOCKED",
            "classification": "NOT_TESTED",
            "reason": "DATABASE_URL is not configured for PostgreSQL in current environment.",
        }
    else:
        p_db = urlparse(db_url.replace("+asyncpg", "").replace("+psycopg2", ""))
        pg_tcp = probe_tcp(p_db.hostname or "127.0.0.1", p_db.port or 5432, timeout=2.0)
        checks["app_to_postgresql"] = {
            "status": "PASSED" if pg_tcp["reachable"] else "BLOCKED",
            "classification": "VERIFIED" if pg_tcp["reachable"] else "NOT_TESTED",
            "probe": pg_tcp,
        }

    # 3. App <-> Redis/Celery probe
    redis_url = str(getattr(settings, "REDIS_URL", "") or "")
    p_rd = urlparse(redis_url)
    rd_tcp = probe_tcp(p_rd.hostname or "127.0.0.1", p_rd.port or 6379, timeout=2.0)
    checks["app_to_redis_celery"] = {
        "status": "PASSED" if rd_tcp["reachable"] else "BLOCKED",
        "classification": "VERIFIED" if rd_tcp["reachable"] else "NOT_TESTED",
        "probe": rd_tcp,
    }

    # 4. App <-> FortiSIEM probe
    siem_host = str(getattr(settings, "FORTISIEM_HOST", "") or "").strip()
    if not siem_host or "CONFIGURED" in siem_host or "example" in siem_host:
        checks["app_to_fortisiem"] = {
            "status": "BLOCKED",
            "classification": "NOT_TESTED",
            "reason": "Live FortiSIEM supervisor host not provisioned in environment.",
        }
    else:
        p_fs = urlparse(siem_host if "://" in siem_host else f"https://{siem_host}")
        fs_tcp = probe_tcp(p_fs.hostname or "", p_fs.port or 443, timeout=2.0)
        checks["app_to_fortisiem"] = {
            "status": "PASSED" if fs_tcp["reachable"] else "BLOCKED",
            "classification": "VERIFIED" if fs_tcp["reachable"] else "NOT_TESTED",
            "probe": fs_tcp,
        }

    statuses = {c["status"] for c in checks.values()}
    overall = "PASSED" if statuses == {"PASSED"} else ("BLOCKED" if "FAILED" not in statuses else "FAILED")
    return {
        "mode": mode,
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "overall_status": overall,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Verdict Phase 9 Integration Readiness Runner")
    parser.add_argument("--mode", choices=VALID_MODES, default="OFFLINE_CONTRACT_TESTS")
    parser.add_argument("--output", default="", help="Optional path to write JSON report")
    args = parser.parse_args()

    if args.mode == "OFFLINE_CONTRACT_TESTS":
        report = run_offline_contract_tests()
    else:
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        report = asyncio.run(run_staging_probes(args.mode))

    text = json.dumps(report, indent=2)
    print(text)
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n", encoding="utf-8")

    if report["overall_status"] == "PASSED":
        return 0
    if report["overall_status"] == "BLOCKED":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
