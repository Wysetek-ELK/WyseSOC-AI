"""
Non-Destructive Server 1 + Server 2 Integration Readiness CLI (AIS 2.3).

Executes `IntegrationDiagnosticService.run_diagnostics(...)` strictly in read-only mode
against the configured database (or `--db-url`) without modifying incidents, SIEM state,
or policy approval records.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402

from app.config import settings  # noqa: E402
from app.services.integration_diagnostic_service import IntegrationDiagnosticService  # noqa: E402


async def execute_integration_diagnostics(
    *,
    db_url: Optional[str] = None,
    rule_id: Optional[str] = None,
    probe_remote: bool = False,
    strict_production: bool = False,
) -> Dict[str, Any]:
    target_url = db_url or settings.DATABASE_URL
    engine = create_async_engine(target_url, echo=False)
    try:
        sess_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with sess_maker() as db:
            svc = IntegrationDiagnosticService(db)
            return await svc.run_diagnostics(
                rule_id=rule_id,
                probe_remote=probe_remote,
                strict_production=strict_production,
            )
    finally:
        await engine.dispose()


def _format_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# AIS 2.3 Server 1 + Server 2 Integration Diagnostic Report",
        "",
        f"- **Generated At:** {report.get('generated_at')}",
        f"- **Read-Only:** `{report.get('read_only')}` | **DB Mutated:** `{report.get('database_mutated')}` | **External Mutations:** `{report.get('external_mutations')}`",
        f"- **Overall Status:** `{report.get('overall_status')}` | **Integration Verified:** `{report.get('integration_verified')}`",
        "",
        "## Check Statuses",
        "| Check | Status |",
        "| --- | --- |",
    ]
    for name, status in (report.get("check_statuses") or {}).items():
        lines.append(f"| {name} | `{status}` |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only AIS 2.3 Server 1 + Server 2 integration diagnostics")
    parser.add_argument("--db-url", default=None, help="Optional SQLAlchemy async DB URL (defaults to settings.DATABASE_URL)")
    parser.add_argument("--rule-id", default=None, help="Optional canonical Rule UUID or logical rule_id")
    parser.add_argument("--probe-remote", action="store_true", help="Probe live Server 2 LLM & Redis/Celery endpoints (GET/PING only)")
    parser.add_argument("--strict-prod", action="store_true", help="Enforce strict production dependency checks")
    parser.add_argument("--fail-on-blocker", action="store_true", help="Exit with code 2 when overall_status == BLOCKED")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--output", default=None, help="Optional output file path")
    args = parser.parse_args()

    report = asyncio.run(
        execute_integration_diagnostics(
            db_url=args.db_url,
            rule_id=args.rule_id,
            probe_remote=bool(args.probe_remote),
            strict_production=bool(args.strict_prod),
        )
    )
    rendered = (
        _format_markdown(report)
        if args.format == "markdown"
        else json.dumps(report, indent=2, default=str)
    )
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered)

    if args.fail_on_blocker and report.get("overall_status") == "BLOCKED":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

