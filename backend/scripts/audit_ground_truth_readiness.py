"""
Read-only Ground-Truth Readiness & `is_ml_generated` Re-evaluation Dry-Run Diagnostic.

Performs zero database mutations (read-only SELECT queries only).
Evaluates:
  1. Per-rule incident counts, verified TP/FP counts, exclusion reasons, and G8 / calibration readiness.
  2. Existing `historical_ground_truth.is_ml_generated = True` records re-checked against
     AIS 2.1/2.2 word-boundary detection (`detect_automated_or_ml_text`) and `Investigation.is_independently_verified`.
  3. Confirms sample threshold alone (`>= 5`) never authorizes autonomous operation.
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
from app.services.historical_eligibility_service import HistoricalEligibilityService  # noqa: E402


async def run_read_only_ground_truth_audit(
    db_url: Optional[str] = None,
    rule_id: Optional[str] = None,
) -> Dict[str, Any]:
    target_url = db_url or settings.DATABASE_URL
    engine = create_async_engine(target_url, echo=False)
    try:
        sess_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with sess_maker() as db:
            svc = HistoricalEligibilityService(db)
            report = await svc.generate_report(rule_id=rule_id)
            report["dry_run_only"] = True
            report["database_mutated"] = False
            report["database_target_scheme"] = str(target_url).split("://", 1)[0]
            return report
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only ground-truth & is_ml_generated readiness audit")
    parser.add_argument("--db-url", default=None, help="Optional SQLAlchemy async DB URL (defaults to settings.DATABASE_URL)")
    parser.add_argument("--rule-id", default=None, help="Optional canonical UUID or logical rule_id filter")
    parser.add_argument("--output", default=None, help="Optional JSON output path")
    args = parser.parse_args()

    report = asyncio.run(run_read_only_ground_truth_audit(db_url=args.db_url, rule_id=args.rule_id))
    rendered = json.dumps(report, indent=2, default=str)
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

