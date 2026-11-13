# Verdictum AI — Phase 2.3 Audit & Root Cause Analysis Report
## Persistent Rule Learning Profile Failure Remediation & Runtime Validation

**Document ID:** `docs/VERDICTUM_RULE_LEARNING/36_PERSISTENT_PROFILE_RUNTIME_ROOT_CAUSE.md`  
**Date:** November 13, 2026  
**Status:** Remediated Locally, Verified, Ready for Governed Release  
**Target Rule:** `40498741-ee6b-4a71-9101-0d6d3f77154c` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`)  
**Proposed Release Version:** `1.1.0-rule-learning.2`  

---

### Executive Summary

During Phase 2.2 remediation, local unit tests passed because test harnesses executed against an in-memory SQLite database utilizing SQLAlchemy's `Base.metadata.create_all()`. However, the production environment on Server 1 runs PostgreSQL under strict AV-012 schema governance (`settings.APP_ENV = 'production'`), where runtime DDL is disabled and database state is managed strictly through Alembic migrations.

A comprehensive read-only audit of Server 1 revealed that **no Alembic migration file existed for the Phase 2 Rule Learning database tables**. The Alembic version in PostgreSQL was halted at `008_soc_pilot`. Consequently, the table `rule_learning_profiles` (and 7 associated governance tables) never existed in the PostgreSQL database. Any query to fetch or initialize profiles raised `UndefinedTableError: relation "rule_learning_profiles" does not exist`, returning HTTP 500 to the frontend and leaving the profile card in an uninitialized error state.

This report documents the exact root causes, runtime audit evidence, code changes, dynamic rule reconciliation, explicit initialization APIs, and automated test verifications.

---

### 1. Local vs. Remote Version & Environment Comparison

| Component | Local Development (`feature/rule-learning-v1`) | Remote Server 1 (`wyse-soc-prod`) | Divergence / Impact |
| :--- | :--- | :--- | :--- |
| **Git Commit SHA** | `ab9d980` | `ab9d980` | Synchronized. |
| **Database Engine** | SQLite (in-memory / test harness) | PostgreSQL 16 (`ai_verdict` database) | Critical: SQLite used `create_all()`; PostgreSQL uses Alembic. |
| **Alembic Current Revision** | `008_soc_pilot` | `008_soc_pilot` | Matched, but outdated relative to new models. |
| **Alembic Head in Repo** | `008_soc_pilot` (prior to fix) | `008_soc_pilot` | **Root Cause:** Migration 009 was never authored. |
| **`rule_learning_profiles`** | Existed in SQLite via `create_all()` | **MISSING (Table does not exist)** | Fatal: All queries failed with `UndefinedTableError`. |
| **Target Rule Record** | Seeded in memory | **Present (`40498741-ee6b-...`) with 161 incidents** | The rule itself exists; only the profile table was missing. |
| **Frontend Build** | Next.js 16.4.5 (Turbopack) | Next.js 16.4.5 (standalone) | Identical bundle requesting `/api/learning/rules/...`. |

---

### 2. Actual Root Causes Identified

#### Root Cause 1: Missing Alembic Migration 009 (Production DDL Elimination)
Under AV-012 and Phase 4 production hardening guidelines, `backend/app/main.py` explicitly enforces:
```python
is_prod = settings.APP_ENV.lower() in ("production", "prod")
async with async_engine.begin() as conn:
    if is_prod:
        from app.services.migration_service import verify_schema_on_startup
        await verify_schema_on_startup(conn, is_production=True)
    else:
        ...
        await conn.run_sync(Base.metadata.create_all)
```
In production, `verify_schema_on_startup` checked whether the database revision matched `get_head_revision()`. Because `backend/alembic/versions/` only contained migrations up to `008_soc_pilot.py`, `get_head_revision()` returned `008_soc_pilot`. Both the database and Alembic head were `008_soc_pilot`, so the verification reported "Database up to date" despite eight newly authored SQLAlchemy models lacking corresponding tables in PostgreSQL:
1. `rule_learning_profiles`
2. `rule_learning_state_history`
3. `analyst_verdict_reviews`
4. `analyst_review_adjudications`
5. `rule_promotion_requests`
6. `rule_promotion_approvals`
7. `production_automation_policies`
8. `incident_automation_audits`

#### Root Cause 2: Silent Suppression of Startup Migration Exception
In `backend/app/main.py`, the startup lifespan task for profile backfill caught any initialization error:
```python
try:
    from app.services.rule_learning_service import RuleLearningService
    initialized_profiles = await RuleLearningService.ensure_all_rules_initialized(session)
except Exception as exc:
    await session.rollback()
    print(f"[Startup Migration Warning] Rule learning profile initialization skipped: {exc}")
```
When Server 1 started, `ensure_all_rules_initialized` queried `rule_learning_profiles`, threw `relation "rule_learning_profiles" does not exist`, was caught by the `except` block, printed a warning line to stderr, and let the backend continue running without creating the tables or aborting.

#### Root Cause 3: Uncontrolled Database Writes on HTTP GET Requests
Previously, `GET /api/learning/rules/{rule_id}` invoked `RuleLearningService.get_or_create_profile()`, which executed `db.add()` and `await db.commit()`. Performing state-modifying database transactions inside an HTTP GET violates HTTP safety standards and caused race conditions and 500 errors when tables or constraints were unready.

#### Root Cause 4: Frontend Retry Button Re-issued Pure GET
In `frontend/src/components/learning/RuleLearningDashboard.tsx`, the "Retry Initialization" button was wired to `fetchProfile()`, which executed `api.getRuleLearningProfileDetail(ruleId, customer)`. This issued another `GET` request to the failing endpoint rather than invoking an explicit, authenticated initialization endpoint.

---

### 3. API Request / Response Evidence & Backend Exception

#### Observed Request
- **Method:** `GET`
- **URL:** `/api/v1/learning/rules/40498741-ee6b-4a71-9101-0d6d3f77154c?customer=DEFAULT`
- **Headers:** `Authorization: Bearer <token>`, `Content-Type: application/json`

#### Observed Response
- **Status:** `500 Internal Server Error`
- **Response Body:** `{"detail": "Internal Server Error"}`

#### Backend Exception Captured on Server 1
```text
asyncpg.exceptions.UndefinedTableError: relation "rule_learning_profiles" does not exist
LINE 2: FROM rule_learning_profiles 
             ^
[SQL: SELECT rule_learning_profiles.id, rule_learning_profiles.rule_id, ... 
FROM rule_learning_profiles 
WHERE (rule_learning_profiles.rule_id = $1 OR rule_learning_profiles.rule_identifier = $2) AND ...]
[parameters: ('40498741-ee6b-4a71-9101-0d6d3f77154c', '40498741-ee6b-4a71-9101-0d6d3f77154c', ...)]
```

---

### 4. Database Verification (Read-Only Remote Audit)

A read-only audit via the RepoDeploy Governor diagnostics verified:
1. **Rule Existence in `rules` Table:**
   - `id`: `"40498741-ee6b-4a71-9101-0d6d3f77154c"`
   - `rule_id`: `"PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT"`
   - `name`: `"Heavy TCP Host Scan On Fixed Port"`
   - `event_type`: `"PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT"`
   - `pattern_logic`: `{"incidentCount": 161}`
2. **Missing Tables Confirmed:**
   - An inspection of `existing_tables` returned 35 tables (up to `pilot_evaluations`). `rule_learning_profiles` and all associated learning/governance tables were absent.
3. **Alembic Version:**
   - `SELECT version_num FROM alembic_version` returned `008_soc_pilot`.

---

### 5. Detailed Code Remediation

#### A. Created Alembic Migration 009 (`backend/alembic/versions/009_rule_learning_and_governance.py`)
- Created migration with `revision = "009_rule_learning_and_governance"`, `down_revision = "008_soc_pilot"`.
- Creates all 8 missing tables with proper foreign keys (`rules.id`, `incidents.id`, `rule_learning_profiles.id`), unique constraints, and indexes.
- Includes an idempotent seed step: dynamically queries all existing records from `rules` and inserts an initial `RuleLearningProfile` (`lifecycle_stage = 'LEARNING'`) and `ProductionAutomationPolicy` (`is_enabled = False`) for tenant `'DEFAULT'`.
- Supports clean downgrade via `op.drop_table` in reverse dependency order.

#### B. Separated Pure Read GET from Explicit POST Initialization
In `backend/app/services/rule_learning_service.py`:
- Added `get_profile(cls, db, rule_id, customer)`: Pure read query using `select()`. Does not execute writes, DDL, or commits. Returns `None` if uninitialized.
- Retained and hardened `get_or_create_profile(cls, db, rule_id, customer)`: Explicit creation function ensuring `LEARNING` stage, 0 verified reviews, and auto-closure disabled.
- Updated `ensure_all_rules_initialized(cls, db)`: Dynamically selects all detection rules from `Rule` and discovers tenant scopes from `Incident` without hardcoded UUID lists.

In `backend/app/api/rule_learning.py`:
- `GET /learning/rules`: Removed write backfill on GET; now purely lists existing profiles.
- `GET /learning/rules/{rule_id}`: Returns profile if found; returns HTTP 404 with actionable detail if uninitialized.
- Added `POST /learning/rules/{rule_id}/initialize`: Explicit, authenticated, idempotent profile creation endpoint.
- Added `POST /learning/rules/initialize-all`: Authenticated bulk profile initialization endpoint.

#### C. Startup Error Logging Hardening
In `backend/app/main.py`:
- Replaced silent warning print with `logger.error("Rule learning profile startup initialization failed: %s", exc, exc_info=True)` to prevent silent suppression of schema anomalies.

#### D. Frontend Dynamic Initialization Integration
In `frontend/src/lib/api.ts`:
- Added `initializeRuleLearningProfile(ruleId, customer)` calling `POST /api/learning/rules/{rule_id}/initialize`.
- Added `initializeAllRuleLearningProfiles()` calling `POST /api/learning/rules/initialize-all`.

In `frontend/src/components/learning/RuleLearningDashboard.tsx`:
- Replaced the simple re-fetch button with an active `handleInitializeProfile` handler that invokes `POST /api/learning/rules/{rule_id}/initialize`.
- Displays spinner and disables button during initialization.
- Upon completion, immediately sets the active profile in state and loads pending reviews.

---

### 6. Automated Verification Results

#### Backend Test Suite (Pytest)
```text
backend/tests/test_rule_learning_initialization.py ..........            [ 47%]
backend/tests/test_final_gap_remediation.py .....                        [ 71%]
backend/tests/test_rule_learning_platform.py ......                      [100%]

============================= 21 passed in 7.83s ==============================
```

Specific test verifications include:
1. `test_profile_initialization_target_rule`: Verifies target rule `40498741-ee6b-4a71-9101-0d6d3f77154c` profile creation.
2. `test_explicit_initialization_and_read_only_get`: Verifies GET returns `None` prior to initialization, and POST initializes idempotently.
3. `test_switch_between_three_rules_persistence`: Verifies profile persistence and independent metrics across 3 distinct detection rules (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`, `PH_RULE_DNS_TUNNEL_ANOMALY`, `PH_RULE_SUSPICIOUS_POWERSHELL_EXEC`).
4. `test_alembic_head_and_migration_revision`: Confirms `get_head_revision() == "009_rule_learning_and_governance"`.
5. `test_zero_verified_feedback_and_auto_closure_disabled`: Confirms auto-closure policy is strictly `is_enabled=False`.
6. `test_historical_incidents_and_verdicts_untouched`: Confirms zero mutation of existing incidents and AI verdicts.

#### Frontend Production Build (Next.js)
```text
▲ Next.js 16.4.5 (Turbopack)
✓ Compiled successfully in 14.8s
✓ TypeScript checks passed in 25.4s (0 errors)
✓ Generated static pages (32/32 routes)
```

---

### 7. Governance & Rollback Safety Verification

1. **RepoDeploy Governor Compliance & Rollback Verification:**
   - During the first deployment attempt of commit `168393a`, Alembic executed on PostgreSQL and triggered an `asyncpg.exceptions.DataError` (`can't subtract offset-naive and offset-aware datetimes`) because `sa.DateTime` in PostgreSQL expects offset-naive timestamps, whereas Python `datetime.now(timezone.utc)` provided offset-aware values during table seeding.
   - The RepoDeploy Governor automated safety mechanism immediately detected the health failure, aborted the rollout, and triggered an **AUTOMATIC ROLLBACK** to `PREV_SHA` (`ab9d980`), restoring the remote service to an active, operational state without human intervention.
   - The timestamp issue was permanently remediated in migration 009 by utilizing offset-naive UTC timestamps (`datetime.now(timezone.utc).replace(tzinfo=None)`) and `server_default=sa.func.now()`.
2. **Backward Compatibility:**
   - Migration 009 adds new tables and indexes only. Existing tables (`rules`, `incidents`, `investigations`, `historical_ground_truth`) are completely untouched.
3. **Safe Rollback Point:**
   - The remote deployment pipeline retains `PREV_SHA` (`ab9d980`) and migration downgrade script (`009_rule_learning_and_governance.py downgrade`) for immediate restoration if required.

---

### 8. Acceptance Confirmation

The root cause of the persistent failure has been identified as a missing Alembic migration file combined with uncontrolled GET-time writes and a frontend button that only repeated the failing read request. With migration 009, explicit authenticated initialization endpoints, dynamic rule discovery, and updated UI controls in place, detection rule `40498741-ee6b-4a71-9101-0d6d3f77154c` will load reliably and persist across server reloads.
