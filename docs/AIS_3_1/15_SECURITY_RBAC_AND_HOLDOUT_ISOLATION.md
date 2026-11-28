# AIS 3.1 — Workstream 15: Security, RBAC & Holdout Isolation Verification

**Verification Scope:** Code audit, isolated FastAPI/SQLite RBAC integration tests, and live read-only HTTP security probes against Server 1 (`172.26.41.240`).

---

## 1. Role-Based & Authentication Controls Verified

### Live Server 1 Unauthenticated Enforcement (`HTTP 401`)
Probed directly against Server 1 (`172.26.41.240`) with zero cookies/tokens:

| Endpoint | HTTP Method | Expected / Verified Status | Result |
|---|---|---:|---|
| `/api/ground-truth/ais31/cohorts/AIS_3_0_INDEPENDENT_HOLDOUT_100/manifest` | `GET` | `401 Unauthorized` | **PASS** |
| `/api/ground-truth/ais31/cohorts/AIS_3_0_INDEPENDENT_HOLDOUT_100/token-audit` | `GET` | `401 Unauthorized` | **PASS** |
| `/api/ground-truth/ais31/cohorts/AIS_3_0_INDEPENDENT_HOLDOUT_100/runs` | `POST` | `401 Unauthorized` | **PASS** |
| `/api/ground-truth/cohorts/AIS_3_0_INDEPENDENT_HOLDOUT_100/queue` | `GET` | `401 Unauthorized` | **PASS** |
| `/api/ground-truth/cohorts/AIS_3_0_INDEPENDENT_HOLDOUT_100/incidents/13960` | `GET` | `401 Unauthorized` | **PASS** |
| `/api/ground-truth/ais31/latest-summary` | `GET` | `401 Unauthorized` | **PASS** |

### Backend FastAPI RBAC Role-Separation Tests (`test_ais31_rbac_and_wire_prompt_access` + `test_ais_2_6f_certification_and_blind_review.py`)
- **`SOC Analyst` role** calling `/ais31/.../manifest`, `/ais31/.../token-audit`, `/ais31/.../runs`: strictly rejected with `403 Forbidden` (`require_admin` dependency enforced).
- **`/ais31/runs/{run_id}/wire-prompt/{incident_id}` & `/ais31/runs/{run_id}/evaluate`:** Protected by `require_admin`.
- **`/ais31/latest-summary`:** Restricted to authenticated active users (`get_current_active_user`) and exposes aggregate metrics only (zero per-incident ground truth verdict disclosure or wire prompt leakage).

---

## 2. Server-Side Blind Review & Anti-Leakage Enforcement

- Checked `/api/ground-truth/cohorts/AIS_3_0_INDEPENDENT_HOLDOUT_100/incidents/16164` on Server 1:
  - `blind_review_guarantees`:
    - `ai_verdict_hidden`: `true`
    - `ai_confidence_hidden`: `true`
    - `historical_fortisiem_label_hidden`: `true`
    - `sibling_reviewer_verdict_hidden`: `true`
    - `excluded_from_learning_and_rag`: `true`
- Blind enforcement is enforced server-side inside `GroundTruthCertificationService` and `blind_review_guard.py`, never relying solely on frontend visibility flags.
- **Harmless Fallback Sanitizer Hardening Discovered & Closed:** Adding the `raw_payload` event fallback in Pilot Cycle 1 revealed that raw FortiSIEM dicts can carry `"incidentReso"` (e.g., `"True Positive"`) and ML `"confidence": "90"`. Added `"incidentreso"`, `"reso"`, and `"incident_reso"` to `HistoricalGroundTruthValidator._NORMALIZED_LEAKAGE_KEYS` and `model_payload_allowlist.FORBIDDEN_GROUND_TRUTH_KEYS`, and stripped historical ML `confidence`/`incidentStatus` inside `AIS31BenchmarkService._extract_sanitized_raw_events_and_summary`. Verified `0` leaks on `test_ais31_raw_payload_fallback_preserves_evidence_and_strips_leakage` and live Pilot V2 wire captures.

---

## 3. Operational, RAG & Memory Isolation

- **Zero Holdout RAG / Memory Pollution:** `AIS31BenchmarkService._prepare_incident_wire_payload` forces `rag_block=""`, `rag_excluded=True`, `memory_excluded=True`. Platform `LearningRecord` table contains `0/100` holdout incidents.
- **Zero Production Verdict Mutation:** AIS 3.1 benchmark writes exclusively to dedicated tables `ais31_benchmark_runs` and `ais31_benchmark_results`. Operational `Incident.status_code`, `Incident.ai_verdict`, `AnalystVerdictReview`, `RulePrompt` / `PromptVersion`, and `LearningRecord` rows remain completely untouched.
- **Prompt Injection Boundary:** All incident-derived fields are delimited inside `<UNTRUSTED_INCIDENT_DATA>...</UNTRUSTED_INCIDENT_DATA>` with closing-tag escaping and neutral system directives treating incident data strictly as untrusted evidence.
- **Secret Redaction:** `GPU_RUNTIME_MANIFEST.json`, `TEST_EXECUTION_RESULTS.json`, UPLA reports, and `docs/AIS_3_1/` exclude passwords, JWTs, API keys, and SSH key paths.
