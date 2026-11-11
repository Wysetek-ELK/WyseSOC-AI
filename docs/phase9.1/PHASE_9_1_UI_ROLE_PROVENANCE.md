# Phase 9.1 — Pilot UI Role Consistency & Live/Mock Provenance Separation

## 1. Investigation & Root Cause: Header `"Analyst"` vs `"Role: Unknown"` + Read-Only Banner

Tracing JWT decoding (`backend/app/api/deps.py`), React auth state (`frontend/src/context/AppContext.tsx`), Header rendering (`frontend/src/components/layout/Header.tsx`), Pilot console (`frontend/src/components/pilot/PilotControlAndDashboard.tsx`), and Playwright E2E screenshots (`docs/phase9/evidence/screenshots/03_pilot_viewer_readonly.png`) revealed **two real frontend UI defects triggered during async auth hydration**:

1. **Misleading Unauthenticated/Loading Header Fallback:** `Header.tsx` previously rendered `{user ? user.username : "Analyst"}` and `{user?.role || "Analyst"}`. Whenever `page.goto()` reloaded Next.js and `AppProvider` initialized `user = null` while `GET /api/auth/me` was in flight (`isLoading === true`), the Header falsely displayed `"Analyst"` (`SOC Analyst`).
2. **Premature `Role: Unknown` + Viewer Banner on Reload:** `PilotControlAndDashboard.tsx` ignored `isLoading` from `useApp()`. Before `/api/auth/me` completed, `user` was `null`, causing `Role: Unknown` alongside the fallback branch (`!isAdmin && !isAnalystOrAdmin` -> `"Read-Only Viewer mode: All SOC Pilot configuration, execution, and feedback controls are locked"`). Furthermore, a race between trailing `loadPilotData()` calls and form edits could overwrite checkbox selections (`P91-DEF-007`).

### Fixes Implemented
- **Role Normalization:** Backend `deps.py` enforces 3 canonical roles: `Administrator` (SOC Lead permissions), `SOC Analyst`, and `Read-Only Viewer`.
- **Header (`Header.tsx`):** Consumes `{ user, isLoading }` from `useApp()`, rendering `"Verifying..."` / `"SYNCING"` while loading and `"Guest"` / `"UNAUTHENTICATED"` when unauthenticated — never `"Analyst"`.
- **AppContext (`AppContext.tsx`):** Clears `ai_verdict_token` and `ai_verdict_user` cleanly in `logout()` (`try/finally`) and on failed `refreshUser()`.
- **Pilot Dashboard (`PilotControlAndDashboard.tsx`):** Consumes `{ user, isLoading: authLoading }`, renders `"Role: Verifying session..."` and a neutral `"Verifying authenticated role and RBAC permissions..."` notice until `authLoading` finishes, and prevents background refreshes from overwriting unsaved operator form inputs (`formInitializedRef` + `syncForm` flag).
- **Playwright Verification (`test_phase9_1_ui_e2e.py`):** Verified all 3 configured roles (`Administrator`, `SOC Analyst`, `Read-Only Viewer`) display identical role badges in both Header and Pilot banners (`p91_01`, `p91_03`, `p91_04`) and enforced RBAC disabled states match backend HTTP `403` enforcement.

---

## 2. Live / Mock / Simulated / Historical / Offline / Degraded Provenance Separation

### Five-Axis Provenance Architecture
Implemented in [`backend/app/services/provenance.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/provenance.py) and [`frontend/src/lib/provenance.ts`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/frontend/src/lib/provenance.ts):

1. **Configured Inference Provider:** `OPENAI_COMPATIBLE` | `SIMULATED` | `DISABLED` | `POLICY_GUARD`.
2. **Actual Execution Provenance (`execution_provenance`):**
   - `LIVE_PROVIDER`: Non-mock remote OpenAI-compatible Server 2 inference call.
   - `HTTP_MOCK`: Loopback (`127.0.0.1`, `localhost`, `::1`) in non-production environments or explicit `LOCAL_LLM_PROVENANCE=HTTP_MOCK` / test environment flags. Never labeled as verified Server 2 GPU inference.
   - `SIMULATED`: Deterministic offline simulator (`is_simulated=True`).
   - `POLICY_GUARD` / `PREFLIGHT_GUARD` / `TOKEN_BUDGET_GUARD`: Deterministic abstention guardrails.
   - `OFFLINE`: Provider unreachable at evaluation time (`SERVER2_OFFLINE`).
   - `DEGRADED`: Provider returned non-200 HTTP error / timeout / invalid model output.
   - `HISTORICAL`: Legacy historical records without live runtime attribution (`historical_execution_provenance`).
3. **Current Server 2 Health:** Live-probed (not 30s-cached on `/api/pilot/metrics` & `build_ai_assurance`) via `ONLINE` / `OFFLINE` / `DEGRADED` / `HTTP_MOCK`, with explicit `gpu_telemetry_verified` boolean (`False` for all `HTTP_MOCK` targets even if `/metrics` returns mock counters).
4. **Historical Execution Provenance Persistence:** Each `PilotEvaluationRecord` persists an HMAC-signed `AuditLog` (`resource_type="PILOT_EVALUATION"`) containing exact execution provenance and test environment metadata, while `Incident.ai_verdict` JSON records `execution_provenance`, `configured_provider`, and `test_environment`. Taking Server 2 offline or switching URLs later preserves `HTTP_MOCK` or `LIVE_PROVIDER` on historical records without rewriting history.
5. **Test Environment Identity (`AI_VERDICT_TEST_ENV`):** Returned via `/api/health`, `/api/dashboard/llm-status`, `/api/chat/status`, `/api/pilot/metrics`, and rendered visibly in `Sidebar.tsx` (`TEST ENV: MOCK_HTTP_E2E`), `PilotControlAndDashboard.tsx`, `human-review-queue`, and `inference-control` during mock-backed runs so browser screenshots and JSON evidence never masquerade as production GPU validation.

