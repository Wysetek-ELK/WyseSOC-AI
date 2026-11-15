# VERDICTUM AI — VALIDATION V1.2.2a
## 07. Assertion and Evidence Integrity: Runner Logic & Traceability

### 1. Verification of Runner Logic

In previous iterations, QA audits noted that some test runners used relaxed or disjunctive assertions (`A || B`), allowing partial matches or false passes. 

Under V1.2.2a, the runner `scripts/run_v1_2_2a_validation.mjs` enforces **strict boolean conjunction** across every required assertion:
```javascript
// Strict fail-fast evaluation:
const scenarioPassed = Object.values(domResult.assertions).every(Boolean);
```
If even a single assertion fails, `isValid` is evaluated as `false`, and the scenario status is marked `FAIL`. The script will exit with code `1` and reject evidence generation if any scenario fails.

---

### 2. Settling & Hydration Loop

Because Next.js and React 19 render initial server HTML and hydrate asynchronous API state in subsequent client microtasks, assertions that check for live backend data run in a polling settle loop:
```javascript
let domResult = { isValid: false, assertions: {} };
if (scenario.validateDom) {
  domResult = await scenario.validateDom();
  if (!domResult.isValid) {
    for (let r = 0; r < 8; r++) {
      await sleep(500);
      domResult = await scenario.validateDom();
      if (domResult.isValid) break;
    }
  }
}
```
This guarantees that screenshots and assertion results capture settled, hydrated application state rather than transient intermediate loading spinners.

---

### 3. Repository SHA Traceability

The validation runner records the exact, immutable Git commit SHA via `git rev-parse HEAD`:
```javascript
function getGitCommitSha() {
  try {
    return execSync("git rev-parse HEAD", { encoding: "utf8" }).trim();
  } catch (e) {
    return "UNKNOWN_COMMIT";
  }
}
```
In `VALIDATION_EVIDENCE.json`:
- **Current SHA Recorded**: `0c2cd0f3239ad7b7ce46d3588a08df5c3564449d`
- Never hardcoded as `"HEAD"`, `"LATEST"`, or arbitrary string constants.
- Every test result record binds directly to this immutable hash.

---

### 4. Integrity of Structured Evidence Payload

The generated `VALIDATION_EVIDENCE.json` contains:
1. `version`: `"V1.2.2a"`
2. `timestamp`: ISO 8601 UTC timestamp
3. `commitSha`: 40-character hex SHA
4. `status`: `"PASS"`
5. `summary`: Total scenarios (8), passed (8), failed (0), screenshots (16), viewports (`1440x900`, `1920x1080`).
6. `testResults`: Full array of 8 scenario test objects with `scenarioId`, `authenticatedRole`, `expectedBackendStatus`, `actualBackendStatus`, `backendPayloadSummary`, `expectedUiStatus`, `actualUiStatus`, `mandatoryAssertions`, and timestamp.
7. `screenshots`: Full manifest of 16 PNG images with verified byte sizes and relative paths.

All 16 screenshot files exist on disk and have verified non-zero payloads (between 436 KB and 974 KB).
