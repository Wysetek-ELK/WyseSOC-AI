# Report 07 — Deployment Verification & Integration Matrix

## 1. System Integration Status

| System Component | Integration Target | Verified State |
| :--- | :--- | :--- |
| **Database Schema** | SQLite / PostgreSQL Alembic Revision `012` | Cleanly applied (`alembic upgrade head`) |
| **API Endpoints** | `POST /api/prompts/rule/{id}/version/{id}/revoke` | Verified (Admin only, audit log written) |
| **API Endpoints** | `GET /api/prompts/rule/{id}/eligibility` | Verified (Real-time governance resolution) |
| **Frontend UI** | Agent Intelligence Studio 2.0 Overview | Verified (Decoupled badges, single inspector button) |
| **Frontend UI** | Advanced Configuration → Version History | Verified (Full lifecycle table, Revoke/Rollback controls) |
| **Runtime Pipeline**| `verdict_pipeline.py` | Verified (Intercepts suspended/revoked/mismatched rules) |
| **Target Rule** | `Heavy TCP Host Scan On Fixed Port` | Verified (`RULE_SUSPENDED`, V1 flagged, V3 draft preserved) |

---

## 2. Server 1 & Server 2 Operational Boundary

- **Server 1 (Verdictum AI Orchestrator):**
  - Manages incident ingestion, normalization, quality gate evaluation, and prompt compilation.
  - Implements the strict authorization and eligibility gate.
- **Server 2 (Local LLM Inference Engine):**
  - Completely isolated from unapproved or revoked prompts.
  - No outbound requests are dispatched when a policy is suspended, revoked, or semantically mismatched.
  - If Server 2 is offline, UI and inspector remain accessible in Preview/Auditing mode.

---

## 3. Migration Verification

Alembic migration `backend/alembic/versions/012_policy_version_governance.py`:
- Added columns to `rule_prompts`:
  - `ai_execution_suspended` (Boolean, default False)
  - `suspension_reason` (Text, nullable)
- Added columns to `prompt_versions`:
  - `revoked_by_user_id` (String(36), nullable)
  - `revoked_at` (DateTime, nullable)
  - `revocation_reason` (Text, nullable)
  - `previous_status` (String(32), nullable)

Database upgrade verified against live development database `backend/ai_verdict.db`.

---
*Report Completed on 2026-11-15.*
