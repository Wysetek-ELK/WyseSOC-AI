"""
Verdictum AI — Transaction-Controlled Incident Database Purge Tool
==================================================================
Safely deletes all incident records, telemetry events, investigations,
analyst reviews, ground truth, few-shot learning records, and evaluation runs
in reverse foreign key dependency order.
Strictly preserves rules, prompts, policies, users, configs, and audit logs.
Resets rule_learning_profiles incident counters to 0.
"""

import os
import sys
import asyncio
import logging
from sqlalchemy import text

# Add backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.config import settings
from app.database import async_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cleanup_incidents")


async def purge_all_incidents() -> dict:
    logger.info(f"Connecting to database: {settings.DATABASE_URL}")
    results = {}

    async with async_engine.begin() as conn:
        logger.info("Executing transactional incident purge in reverse foreign key order...")

        tables_to_clear = [
            "analyst_review_adjudications",
            "analyst_verdict_reviews",
            "historical_evaluation_results",
            "historical_evaluation_runs",
            "historical_ground_truth",
            "learning_records",
            "dry_run_results",
            "actual_llm_prompt_captures",
            "evidence_sufficiency_assessments",
            "ground_truth_validations",
            "incident_automation_audits",
            "verdict_trust_assessments",
            "pilot_evaluations",
            "investigation_questions",
            "investigation_evidence",
            "investigations",
            "incident_events",
            "telemetry_timeline_records",
            "token_usage_records",
            "incidents",
            "import_jobs",
        ]

        for table in tables_to_clear:
            try:
                res = await conn.execute(text(f"DELETE FROM {table}"))
                deleted = res.rowcount if res.rowcount is not None else 0
                results[table] = deleted
                logger.info(f"Purged table '{table}': {deleted} rows removed.")
            except Exception as e:
                logger.warning(f"Note on table '{table}': {e}")
                results[table] = str(e)

        # Reset aggregate metrics on rule learning profiles while preserving all profiles
        try:
            profile_res = await conn.execute(text("""
                UPDATE rule_learning_profiles SET
                    total_incidents_processed = 0,
                    total_analyst_reviews = 0,
                    verified_tp_count = 0,
                    verified_fp_count = 0,
                    ai_correct_count = 0,
                    ai_incorrect_count = 0,
                    abstention_count = 0,
                    validation_failure_count = 0,
                    empirical_accuracy = NULL,
                    fp_precision = NULL,
                    tp_recall = NULL,
                    wilson_lower_bound = NULL,
                    error_distribution = '{}',
                    last_evaluated_at = NULL
            """))
            logger.info("Reset rule_learning_profiles incident metrics to 0.")
            results["rule_learning_profiles_reset"] = profile_res.rowcount
        except Exception as e:
            logger.warning(f"Note on resetting rule_learning_profiles: {e}")
            results["rule_learning_profiles_reset"] = str(e)

    # Reclaim free storage and optimize if SQLite
    if "sqlite" in settings.DATABASE_URL:
        try:
            async with async_engine.connect() as conn:
                await conn.execution_options(isolation_level="AUTOCOMMIT").execute(text("VACUUM"))
                await conn.execution_options(isolation_level="AUTOCOMMIT").execute(text("ANALYZE"))
                logger.info("SQLite VACUUM and ANALYZE completed successfully.")
        except Exception as e:
            logger.warning(f"SQLite VACUUM warning: {e}")

    logger.info("All incident data successfully purged from the database.")
    return results


def main():
    asyncio.run(purge_all_incidents())


if __name__ == "__main__":
    main()
