"""
Mandatory Automated Test Suite: Production Database Isolation & Safety Guard
Verifies that any attempt to execute tests or test fixtures against operational database
configurations is immediately blocked with fail-closed exception without mutating any table.
"""

import os
import pytest
from app.core.db_guard import (
    enforce_database_safety,
    check_is_operational_target,
    inspect_database_target,
    OperationalDatabaseProtectionError,
    PROHIBITED_OPERATIONAL_HOSTS,
    PROHIBITED_OPERATIONAL_DB_NAMES,
)


def test_operational_server1_target_is_blocked():
    """Verify that an operational connection to Server 1 (172.26.41.240) is immediately blocked."""
    operational_url = "postgresql+asyncpg://postgres:SuperSecret123@172.26.41.240:5432/ai_verdict"
    with pytest.raises(OperationalDatabaseProtectionError) as exc_info:
        enforce_database_safety(operational_url, app_env="testing")
    assert "BLOCKED — OPERATIONAL DATABASE TEST EXECUTION PROHIBITED" in str(exc_info.value)
    assert "172.26.41.240" in str(exc_info.value) or "Server 1" in str(exc_info.value)


def test_operational_db_name_on_any_remote_host_is_blocked():
    """Verify that operational database name 'ai_verdict' on a remote or staging host is blocked."""
    remote_url = "postgresql+asyncpg://app_user:pass123@prod-db.internal:5432/ai_verdict"
    with pytest.raises(OperationalDatabaseProtectionError) as exc_info:
        enforce_database_safety(remote_url, app_env="testing")
    assert "BLOCKED — OPERATIONAL DATABASE TEST EXECUTION PROHIBITED" in str(exc_info.value)
    assert "ai_verdict" in str(exc_info.value)


def test_operational_user_is_blocked():
    """Verify that connection with production user 'ai_verdict_prod' is blocked."""
    user_url = "postgresql+asyncpg://ai_verdict_prod:pass123@localhost:5432/some_db"
    with pytest.raises(OperationalDatabaseProtectionError) as exc_info:
        enforce_database_safety(user_url, app_env="testing")
    assert "BLOCKED — OPERATIONAL DATABASE TEST EXECUTION PROHIBITED" in str(exc_info.value)


def test_dbname_containing_test_on_operational_host_is_still_blocked():
    """
    CRITICAL: A database name containing 'test' must not be the sole protection.
    If the target host is Server 1 (172.26.41.240), it must still be blocked!
    """
    bypass_attempt_url = "postgresql+asyncpg://postgres:secret@172.26.41.240:5432/ai_verdict_test"
    with pytest.raises(OperationalDatabaseProtectionError) as exc_info:
        enforce_database_safety(bypass_attempt_url, app_env="testing")
    assert "BLOCKED — OPERATIONAL DATABASE TEST EXECUTION PROHIBITED" in str(exc_info.value)
    assert "172.26.41.240" in str(exc_info.value)


def test_production_sqlite_file_is_blocked_in_test_mode():
    """Verify that default production SQLite file 'ai_verdict.db' cannot be targeted by tests."""
    prod_sqlite_url = "sqlite+aiosqlite:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/ai_verdict.db"
    with pytest.raises(OperationalDatabaseProtectionError) as exc_info:
        enforce_database_safety(prod_sqlite_url, app_env="testing")
    assert "BLOCKED — OPERATIONAL DATABASE TEST EXECUTION PROHIBITED" in str(exc_info.value)


def test_isolated_in_memory_sqlite_passes():
    """Verify that authorized in-memory test database passes safety checks cleanly."""
    in_memory_url = "sqlite+aiosqlite:///:memory:"
    # Should not raise any exception
    enforce_database_safety(in_memory_url, app_env="testing")


def test_isolated_dedicated_test_db_with_marker_passes():
    """Verify that dedicated local test database with test isolation marker passes."""
    os.environ["AI_VERDICT_TEST_ENV"] = "isolated_unit_test"
    dedicated_test_url = "postgresql+asyncpg://test_runner:test_pass@127.0.0.1:5433/ai_verdict_isolated_test"
    # Should not raise any exception
    enforce_database_safety(dedicated_test_url, app_env="testing")


def test_zero_mutation_guarantee_on_blocked_target():
    """
    Confirms that when safety guard blocks an operational URL, execution terminates immediately
    before any engine or connection is created, guaranteeing zero mutation.
    """
    operational_url = "postgresql+asyncpg://postgres:fake@172.26.41.240:5432/ai_verdict"
    executed_sql = False
    try:
        enforce_database_safety(operational_url, app_env="testing")
        executed_sql = True  # Should never reach here
    except OperationalDatabaseProtectionError:
        pass

    assert executed_sql is False, "Safety guard failed to prevent execution pipeline continuation!"
