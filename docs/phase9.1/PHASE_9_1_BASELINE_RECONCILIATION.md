# Phase 9.1 — Baseline Source and Documentation Reconciliation

## 1. Purpose

Reconcile Phase 8.2 (`docs/phase8.2/PHASE_8_2_FINAL_REPORT.md`) and Phase 9 (`docs/phase9/PHASE_9_FINAL_REPORT.md`) artifacts against live source code, Alembic schema revisions, tests, and the central feature registry (`docs/feature_registry.json`). Preserve historical phase folders (`docs/phase8/`, `docs/phase8.1/`, `docs/phase8.2/`, `docs/phase9/`) completely unmodified.

---

## 2. Historical vs Reconciled Baseline

| Item | Phase 8.2 Reported | Phase 9 Reported | Phase 9.1 Observed & Reconciled |
|---|---|---|---|
| Base Git Commit | `cefe4ad` / `9b15dc8` | `8b91592` | `8b91592cae41352602116567e9c6f5e8b5505844` + Phase 9.1 fixes |
| Registered Modules | 19 | 19 | **19** verified |
| Registered Features | 37 | 44 | **44** verified (`AIS-*`, `EVC-*`, `RAG-*`, `VTI-*`, `QGS-*`, `FSI-*`, `LLM-*`, `WRK-*`, `INV-*`, `SEC-*`, `DBM-*`, `MON-*`, `TST-*`, `DOC-*`, `PIL-01..04`, `HGT-03`, `DEP-01`, `PRF-01`) |
| Implementation Criteria | `67/67` (100.0%) | `78/78` (100.0%) | **78/78 (100.0%)** (`SATISFIED`) |
| Verified Acceptance Criteria | `61/67` (91.0%) | `69/78` (88.5%) | **69/78 (88.5%)** (`VERIFIED`), **9** `NOT_TESTED` (external infra) |
| Backend Automated Tests | 283 passed | 293 passed | **299 passed** (`+6` new Phase 9.1 regression tests), **0 warnings** |
| Alembic Head Revision | `007_rule_intelligence` | `008_soc_pilot` | **`008_soc_pilot`** verified (upgrade & downgrade roundtrip green) |
| Documentation Suite Under `docs/phase9/` | — | 21 Markdown files | All **21** Markdown files + evidence directories confirmed present & intact |

---

## 3. Verified Implementation Artifacts

- **Controlled SOC Pilot & Eligibility Models/APIs:**
  - `backend/app/models/pilot.py` (`PilotConfiguration`, `PilotConfigHistory`, `PilotEvaluationRecord`)
  - `backend/alembic/versions/008_soc_pilot.py`
  - `backend/app/schemas/pilot.py` (enforces `allow_external_writeback=False`, `allow_auto_incident_closure=False`)
  - `backend/app/services/pilot_service.py` & `backend/app/api/pilot.py`
  - `backend/app/services/historical_eligibility_service.py`
- **Review & Verdict Assurance:**
  - `backend/app/services/investigation_service.py` (`build_ai_assurance`) & `backend/app/schemas/investigation.py` (`AIAssuranceSummary`)
- **Frontend Pilot & Eligibility UI:**
  - `frontend/src/components/pilot/PilotControlAndDashboard.tsx`
  - `frontend/src/components/pilot/HistoricalEligibilityPanel.tsx`
  - `frontend/src/app/human-review-queue/page.tsx`
  - `frontend/src/app/page.tsx` (Agent Mission Control pilot banner)

---

## 4. Genuine Discrepancies Identified & Remediated in Phase 9.1

1. **Feature Registry Metadata Drift:** `docs/feature_registry.json` contained Phase 9 features (`PIL-01..04`, `HGT-03`, `DEP-01`, `PRF-01`), yet `metadata.git_commit` (`cefe4ad+phase8.2`), `metadata.updated_at`, and `metadata.architecture_version` remained pinned to Phase 8.2, and `TST-01` cited stale `283 passed`.
2. **Pilot UI Role & Loading Mismatch (`P91-DEF-001`):** `Header.tsx` fell back to `"Analyst"` / `"SOC Analyst"` while `user` was `null`/loading, and `PilotControlAndDashboard.tsx` rendered `"Role: Unknown"` alongside `"Read-Only Viewer mode"` before `/api/auth/me` resolved.
3. **Live/Mock Execution Provenance Conflation (`P91-DEF-002`):** `Sidebar.tsx` displayed `Arch: S1 + S2 (GPU)` and `PilotControlAndDashboard.tsx` displayed `LIVE_PROVIDER` when connected to loopback HTTP mock test endpoints (`_MockLLMServer` on `127.0.0.1`), and `PilotService.get_pilot_metrics()` used a 30s cached `is_local_llm_available()` status instead of live probing.
4. **Seeded Synthetic Fixture Vulnerability (`P91-DEF-003`):** `HistoricalGroundTruthValidator.is_synthetic_fixture` skipped exclusion once `main.py` startup migration backfilled `first_seen_epoch` onto `INC-DEBUG-*` zero-event rows in `backend/ai_verdict.db`.
5. **Production Default Admin Auto-Seed (`P91-DEF-004`):** `backend/app/main.py` auto-created `admin` / `AdminPassword123!` when the user table was empty even under `APP_ENV=production`, and `frontend/src/app/login/page.tsx` prefilled default credentials in client builds.
6. **Pytest Warning Backlog (`P91-DEF-005`):** `6,072` Python 3.13 / SQLAlchemy / Pydantic v2 / Alembic deprecation warnings existed across the backend suite.
7. **Deployment Script & CRLF Inconsistencies (`P91-DEF-006`):** `deploy_server1.sh`, `setup_server2_gpu.sh`, and several `.service`/`.conf` files had CRLF (`\r\n`) endings, and `install_ubuntu.sh` / `start_services.sh` / `stop_services.sh` / `verify_server1.sh` / `rollback_server1.sh` omitted `ai-verdict-scheduler` or `ai-verdict-worker`.

