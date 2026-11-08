import os
import sys
import logging
from typing import Optional, Tuple
from sqlalchemy import text
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic import command
from app.config import settings

logger = logging.getLogger("ai_verdict.migrations")

ALEMBIC_INI_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini")
)


def get_alembic_config() -> Config:
    """Returns configured Alembic Config object."""
    cfg = Config(ALEMBIC_INI_PATH)
    cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    alembic_dir = os.path.abspath(os.path.join(os.path.dirname(ALEMBIC_INI_PATH), "alembic"))
    cfg.set_main_option("script_location", alembic_dir)
    cfg.set_main_option("version_locations", os.path.join(alembic_dir, "versions"))
    return cfg


def get_head_revision() -> str:
    """Returns the head revision ID defined in the migrations directory."""
    cfg = get_alembic_config()
    script = ScriptDirectory.from_config(cfg)
    return script.get_current_head()


async def get_current_db_revision(conn) -> Optional[str]:
    """
    Queries the database's alembic_version table to determine the currently applied revision.
    Returns None if alembic_version table does not exist or is empty.
    """
    try:
        result = await conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
        row = result.fetchone()
        if row:
            return row[0]
        return None
    except Exception:
        return None


async def verify_schema_on_startup(conn, is_production: bool, auto_migrate: bool = False) -> Tuple[bool, str]:
    """
    Strict AV-012 Migration Compliance Gate:
    In production: Verifies that database schema matches Alembic head revision.
    Fails startup with RuntimeError if schema is unmigrated or mismatched.
    Prevents runtime DDL (create_all or raw ALTER statements) during production startup.
    
    In development: Can automatically run migration or initialize schema cleanly.
    """
    head_rev = get_head_revision()
    current_rev = await get_current_db_revision(conn)

    logger.info(f"Database schema check: current revision='{current_rev}', expected head='{head_rev}'")

    if current_rev == head_rev:
        logger.info(f"Schema is up to date at head revision '{head_rev}'.")
        return True, f"Database up to date ({head_rev})"

    if is_production:
        msg = (
            f"Critical Schema Blocker (AV-012): Production database schema is out of date. "
            f"Expected revision '{head_rev}', but database is at '{current_rev}'. "
            f"Runtime DDL is forbidden in production. "
            f"Run 'alembic upgrade head' as an authorized migration step before launching the application."
        )
        logger.critical(msg)
        raise RuntimeError(msg)

    # In development/test mode:
    if auto_migrate or current_rev is None:
        logger.info(f"Development mode: auto-migrating database from '{current_rev}' to '{head_rev}'")
        # Run synchronous alembic upgrade via sync url
        try:
            cfg = get_alembic_config()
            cfg.set_main_option("sqlalchemy.url", settings.SYNC_DATABASE_URL)
            command.upgrade(cfg, "head")
            logger.info("Alembic upgrade to head completed successfully.")
            return True, f"Auto-migrated to {head_rev}"
        except Exception as e:
            logger.warning(f"Alembic auto-upgrade encountered error: {e}. Falling back to safe DDL.")
            return False, str(e)

    return True, f"Schema at {current_rev} (Head: {head_rev})"
