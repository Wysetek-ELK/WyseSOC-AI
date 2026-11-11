# Phase 9.1 — Pytest Warning Root-Cause Analysis & Remediation

## 1. Objective & Rule Compliance

Phase 9 baseline execution (`docs/phase9/evidence/backend/pytest_backend_full_report.txt`) reported **6,072 warnings** across 293 tests. Per Phase 9.1 requirements:
- Warnings were grouped by unique root cause rather than suppressed via `filterwarnings = ignore`.
- Compatibility with SQLite (`aiosqlite`) and PostgreSQL (`asyncpg` / naive `DateTime` columns) and Pydantic v2 was strictly preserved.

---

## 2. Exact Root-Cause Grouping (`6,072` -> `0`, `100.0%` Eliminated)

Exact parsing of [`pytest_backend_full_report.txt`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/phase9/evidence/backend/pytest_backend_full_report.txt) vs post-fix [`docs/phase9.1/evidence/tests/pytest_backend_full_report.txt`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/phase9.1/evidence/tests/pytest_backend_full_report.txt) (recorded in [`warnings_comparison.json`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/phase9.1/evidence/logs/warnings_comparison.json)):

| # | Warning Class & Root Cause | Phase 9 Count | Share | Remediation Applied | Post-Fix Count |
|---|---|---|---|---|---|
| 1 | `DeprecationWarning`: SQLAlchemy ORM `mapped_column(DateTime, default/onupdate=datetime.utcnow)` (`sqlalchemy/sql/schema.py:3624`) | **4,573** | 75.31% | Replaced column defaults/onupdates across all ORM models in `backend/app/models/*.py` with shared helper `utc_now` (`datetime.now(timezone.utc).replace(tzinfo=None)`). | **0** |
| 2 | `DeprecationWarning`: Direct `datetime.utcnow()` calls across services, APIs, workers, scripts, and tests | **1,017** | 16.75% | Migrated all runtime and test calls to `app.utils.datetime_utils.utc_now()` (and stdlib `datetime.now(timezone.utc)` in `scripts/run_integration_suite.py`). | **0** |
| 3 | `DeprecationWarning`: Pydantic v2 Schema `Field(default_factory=datetime.utcnow)` (`pydantic/main.py:253`) | **400** | 6.59% | Migrated `policy_quality.py`, `rule_intelligence.py`, and `verdict_intelligence.py` default factories to `utc_now`. | **0** |
| 4 | `DeprecationWarning`: `datetime.utcfromtimestamp()` (`telemetry_timeline_service.py`, `verified_semantic_retrieval_service.py`) | **58** | 0.96% | Replaced with `app.utils.datetime_utils.utc_from_timestamp()`. | **0** |
| 5 | `PydanticDeprecatedSince20`: Class-based `class Config:` deprecated in `backend/app/schemas/` | **12** | 0.20% | Converted all 12 occurrences (`dry_run.py`, `evaluation.py`, `investigation.py`, `learning.py`, `prompt.py`) to `model_config = ConfigDict(from_attributes=True)`. | **0** |
| 6 | `DeprecationWarning`: Missing `path_separator` in `backend/alembic.ini` (`alembic/config.py`) | **8** | 0.13% | Added `path_separator = os` to `[alembic]` in `backend/alembic.ini`. | **0** |
| 7 | `PydanticDeprecatedSince20`: Deprecated `.from_orm()` calls (`backend/app/api/investigations.py`) | **3** | 0.05% | Replaced all `.from_orm(...)` calls with `.model_validate(...)`. | **0** |
| 8 | `PydanticDeprecatedSince20`: Deprecated `.dict()` call (`backend/app/api/evaluations.py:180`) | **1** | 0.02% | Replaced `metrics.dict()` with `metrics.model_dump()`. | **0** |
| | **TOTAL** | **6,072** | **100.0%** | **Zero global suppressions added** | **0** |

---

## 3. Compatibility Design Note (`utc_now` Returning Naive UTC)

All database schema columns across Alembic revisions `001`–`008` use timezone-naive `DateTime` (`sqlalchemy.DateTime`). Returning `datetime.now(timezone.utc).replace(tzinfo=None)` from `app.utils.datetime_utils.utc_now()` resolves Python 3.13 deprecation warnings **without** breaking SQLite comparison arithmetic or `asyncpg`'s strict prohibition against mixing offset-aware and offset-naive datetimes.

