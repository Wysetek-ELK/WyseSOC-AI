"""
Verdictum AI — Production Database Safety & Fail-Closed Test Isolation Guard
Enforces strict fail-closed boundary preventing automated tests, test fixtures,
or non-production harnesses from connecting to or mutating operational databases.
"""

import os
import sys
import logging
from typing import Tuple, Dict, Any, Optional, Set
from sqlalchemy.engine.url import make_url

logger = logging.getLogger("ai_verdict.core.db_guard")


class OperationalDatabaseProtectionError(RuntimeError):
    """Raised when an operation attempts to run tests or unauthorized mutations against an operational database."""
    pass


# Known operational hostnames, IP addresses, and identifiers
PROHIBITED_OPERATIONAL_HOSTS: Set[str] = {
    "172.26.41.240",
    "server1",
    "server-1",
    "prod.wysesoc.internal",
    "production.wysesoc.internal",
}

# Known operational database names
PROHIBITED_OPERATIONAL_DB_NAMES: Set[str] = {
    "ai_verdict",
    "wysesoc",
    "wysesoc_ai",
    "production_ai_verdict",
}

# Known operational user accounts
PROHIBITED_OPERATIONAL_USERS: Set[str] = {
    "ai_verdict_prod",
    "wysesoc_prod",
    "postgres_prod",
}


def is_test_execution_active(app_env: Optional[str] = None) -> bool:
    """
    Determines whether the current execution is within a test runner, test harness, or test environment.
    """
    env_val = (app_env or os.getenv("APP_ENV", "")).lower().strip()
    if env_val in {"test", "testing", "pytest"}:
        return True
    if "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ:
        return True
    if os.getenv("AI_VERDICT_TEST_RUN", "").lower() in {"1", "true", "yes"}:
        return True
    return False


def inspect_database_target(url_str: str) -> Dict[str, Any]:
    """
    Parses and extracts normalized connection properties from a database URL.
    """
    try:
        url = make_url(url_str)
        driver = url.drivername or ""
        host = (url.host or "").lower().strip()
        port = url.port
        database = (url.database or "").lower().strip()
        user = (url.username or "").lower().strip()
        return {
            "driver": driver,
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "is_sqlite": "sqlite" in driver,
            "is_memory": database == ":memory:" or ":memory:" in url_str,
            "raw_url": url_str,
        }
    except Exception as exc:
        logger.warning(f"Failed to parse database URL '{url_str}': {exc}")
        return {
            "driver": "unknown",
            "host": "",
            "port": None,
            "database": "",
            "user": "",
            "is_sqlite": False,
            "is_memory": False,
            "raw_url": url_str,
        }


def check_is_operational_target(url_str: str) -> Tuple[bool, str]:
    """
    Authoritative evaluation: Checks whether the given target database resolves to an operational or production target.
    Returns (is_operational, reason).
    """
    target = inspect_database_target(url_str)
    host = target["host"]
    db_name = target["database"]
    user = target["user"]

    # 1. Operational Host Verification (Server 1 / Production Hosts)
    if host in PROHIBITED_OPERATIONAL_HOSTS:
        return True, f"Prohibited operational host target: '{host}' (Server 1 / Production Host)"

    server1_env = os.getenv("SERVER1_HOST", "").lower().strip()
    if server1_env and host == server1_env:
        return True, f"Target matches configured SERVER1_HOST: '{host}'"

    server1_outbound = os.getenv("SERVER1_OUTBOUND_IP", "").lower().strip()
    if server1_outbound and host == server1_outbound:
        return True, f"Target matches configured SERVER1_OUTBOUND_IP: '{host}'"

    # 2. Operational User Verification
    if user in PROHIBITED_OPERATIONAL_USERS:
        return True, f"Prohibited operational database user: '{user}'"

    # 3. Operational Database Name Verification
    # Even if on localhost or via a tunnel, the exact production database name is protected
    if db_name in PROHIBITED_OPERATIONAL_DB_NAMES:
        return True, f"Prohibited operational database name: '{db_name}'"

    # 4. Check for production SQLite database file
    if target["is_sqlite"] and not target["is_memory"]:
        norm_db = os.path.basename(db_name).lower()
        if norm_db == "ai_verdict.db":
            return True, "Default operational SQLite file 'ai_verdict.db' detected"

    return False, ""


def enforce_database_safety(url_str: str, app_env: Optional[str] = None) -> None:
    """
    Fail-closed guard:
    If test execution is detected, verifies all connection properties.
    If the target resolves to an operational database, aborts immediately before any connection or mutation.
    A database name containing 'test' must not be the sole protection.
    """
    is_test = is_test_execution_active(app_env)
    is_operational, reason = check_is_operational_target(url_str)

    if is_test:
        target = inspect_database_target(url_str)
        host = target["host"]
        db_name = target["database"]

        # CRITICAL: A database name containing 'test' is NOT sufficient if the host is operational!
        # Example: postgres://...172.26.41.240/ai_verdict_test is STILL BLOCKED!
        if host in PROHIBITED_OPERATIONAL_HOSTS or (os.getenv("SERVER1_HOST") and host == os.getenv("SERVER1_HOST", "").lower()):
            raise OperationalDatabaseProtectionError(
                f"BLOCKED — OPERATIONAL DATABASE TEST EXECUTION PROHIBITED: "
                f"Target host '{host}' is an operational server. Automated test execution is forbidden."
            )

        # If it matches any operational target, fail closed
        if is_operational:
            raise OperationalDatabaseProtectionError(
                f"BLOCKED — OPERATIONAL DATABASE TEST EXECUTION PROHIBITED: "
                f"{reason}. Automated tests must execute only against isolated test databases."
            )

        # For non-memory databases in test mode, ensure test environment isolation marker or test prefix/suffix
        if not target["is_memory"]:
            test_marker = os.getenv("AI_VERDICT_TEST_ENV", "").strip()
            has_test_name = "test" in db_name
            if not has_test_name and not test_marker:
                raise OperationalDatabaseProtectionError(
                    f"BLOCKED — OPERATIONAL DATABASE TEST EXECUTION PROHIBITED: "
                    f"Target database '{db_name}' lacks explicit test-environment marker or test isolation credentials."
                )

    logger.debug(f"Database safety check passed for URL target (is_test={is_test})")
