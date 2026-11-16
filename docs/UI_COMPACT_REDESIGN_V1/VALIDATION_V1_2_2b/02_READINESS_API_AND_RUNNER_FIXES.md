# Verdictum AI — Validation V1.2.2b
## 02: Readiness API Routing and Runner Conjunction Fixes

### 1. Problem Definition & Anomaly Audit
In Validation V1.2.2a, automated test evidence reported a 100% pass rate. However, audit review of the raw payload data in `docs/UI_COMPACT_REDESIGN_V1/VALIDATION_V1_2_2a/VALIDATION_EVIDENCE.json` revealed:
- `scenarioId`: `SCN-V122A-06-HEAVY-TCP-V1-HISTORICAL` -> `actualBackendStatus`: **404**, `readiness`: `undefined`
- `scenarioId`: `SCN-V122A-07-HEAVY-TCP-V3-CANDIDATE` -> `actualBackendStatus`: **404**, `readiness`: `undefined`
- `scenarioId`: `SCN-V122A-08-HEAVY-TCP-OFFLINE-STATE` -> `actualBackendStatus`: **404**, `readiness`: `undefined`

Despite receiving HTTP 404 responses from the backend, the runner stamped each scenario with `status: PASS`.

---

### 2. Root Cause Analysis
The defect comprised two distinct failures:
1. **Invalid Route Formulation in Test Runner:**
   The runner script attempted to fetch:
   ```javascript
   `${BACKEND_URL}/api/prompts/readiness/${rule_id}?version_id=${version_id}`
   ```
   FastAPI router in `backend/app/api/prompts.py` defines the canonical path as:
   ```python
   @router.get("/rule/{rule_id}/readiness", response_model=ProductionReadinessResponse)
   async def get_rule_production_readiness(...)
   ```
   Mounted under prefix `/api`, the actual canonical path is `/api/prompts/rule/{rule_id}/readiness`.

2. **Decoupled DOM-Only Assertion Evaluation:**
   In `run_v1_2_2a_validation.mjs`, the scenario outcome was calculated via:
   ```javascript
   const scenarioPassed = domResult.isValid;
   ```
   The HTTP status code and API payload were logged to the console and recorded in the JSON structure, but were never factored into the boolean pass/fail decision.

---

### 3. Engineering Implementation

#### A. Canonical Route Targeting
All runner definitions and frontend clients now query the canonical route:
```
GET /api/prompts/rule/{rule_id}/readiness?version_id={version_id}
```
Authentication headers (`Authorization: Bearer <token>`) are strictly enforced.

#### B. Fail-Fast Conjunction Logic
In `scripts/run_v1_2_2b_validation.mjs`, evaluation logic was replaced with a strict boolean conjunction:
```javascript
let apiValid = false;
try {
  const apiRes = await fetch(scenario.apiEndpoint, {
    headers: { "Authorization": `Bearer ${scenario.user.access_token}` },
  });
  apiStatus = apiRes.status;
  apiData = await apiRes.json();
  if (scenario.validateApi) {
    apiValid = scenario.validateApi(apiData, apiStatus);
  } else {
    apiValid = apiStatus === (scenario.expectedBackendStatus || 200);
  }
} catch (e) {
  apiValid = false;
}

// Fail-fast conjunction: Both backend API and DOM render must pass!
const scenarioPassed = apiValid && domResult.isValid;
```

#### C. Response Schema Validation
The API validator explicitly checks canonical response fields defined in `ProductionReadinessResponse`:
- `readiness_status`: String (`"READY"`, `"BLOCKED"`, `"PILOT_ELIGIBLE"`, `"SUSPENDED"`, `"NOT_CONFIGURED"`)
- `quality_score`: Float (e.g. `54.0` for v1, `77.0` for v3)
- `quality_gates_passed`: Integer (e.g. `2` for v1, `6` for v3)
- `approval_eligible`: Boolean (`false` for unapproved or sub-8 gate versions)

---

### 4. Verification Evidence
During the execution of `scripts/run_v1_2_2b_validation.mjs`:
- `SCN-V122B-01-HEAVY-TCP-V1`: Expected 200, Actual 200, Valid: YES (score: 54.0, gates: 2/8, status: BLOCKED) -> **PASS**
- `SCN-V122B-02-HEAVY-TCP-V3`: Expected 200, Actual 200, Valid: YES (score: 77.0, gates: 6/8, status: BLOCKED) -> **PASS**
- `SCN-V122B-03-AI-RUNTIME-OFFLINE`: Expected 200, Actual 200, Valid: YES (runtime_availability: verified) -> **PASS**

All three scenarios achieved green status under strict fail-fast validation.
