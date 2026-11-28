# AIS 3.1 — Workstream 9: Token Budget & Evidence Completeness

**Cohort:** `AIS_3_0_INDEPENDENT_HOLDOUT_100`  
**Target Model Verified:** `Qwen/Qwen3-14B-AWQ` (`vLLM 0.33.0`, `max_model_len = 8192`)  
**Machine-Readable Evidence:** [TOKEN_BUDGET_RESULTS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_3_1/TOKEN_BUDGET_RESULTS.json)

---

## 1. Token Budget Configuration

- **Context Ceiling:** `8192` tokens (`max_model_len` verified via `/v1/models`)
- **Reserved Completion Tokens:** `768` tokens (`enable_thinking: false`, `temperature: 0.0`)
- **Target Input Budget:** `7424` tokens (`8192 - 768`)
- **Tokenizer Verification Method:** Live Server 2 `vllm_tokenize_api` (`messages_chat_template`) invoked from Server 1 via `GET /api/ground-truth/ais31/cohorts/AIS_3_0_INDEPENDENT_HOLDOUT_100/token-audit?verify_remote_tokenize=true`

---

## 2. Live Remote `/tokenize` Results (Initial Pass Across All 100 Incidents)

> [!NOTE]
> An initial live `/tokenize` pass ran on `100/100` holdout incidents. Following the 5-incident pilot evidence-completeness finding (`inc.raw_payload` fallback for aggregated FortiSIEM incidents where `inc.events == []`), `/tokenize` audit is re-executed after redeploying the `raw_payload` fallback fix to verify that adding sanitized summary events preserves `0` context overflows.

| Metric (Initial Pre-Fix Live `/tokenize`) | Verified Value |
|---|---:|
| Cohort Items Audited | **100** (`100` `vllm_tokenize_api`) |
| Context Overflows (`> 7424`) | **0** |
| All Fit Safely | **`true`** |
| Min Wire Prompt Tokens | **2,992** |
| Median Wire Prompt Tokens | **4,202.5** |
| Mean Wire Prompt Tokens | **4,852.8** |
| P95 Wire Prompt Tokens | **7,255** |
| Max Wire Prompt Tokens | **7,284** |
| Auto-Rebudgeted Items | **31 / 100** |

---

## 3. Evidence Completeness Defect Found During Pilot & Remediated

During Workstream 10 pilot wire-prompt inspection (`13960`, `16133`), **54/100** aggregated FortiSIEM incidents had `0` rows in the relational `incident_events` table (`events_total = 0`), storing their triggering attributes (`incidentSrc`, `incidentTarget`, `incidentDetailJson`, `incidentTitle`, `count`) instead in `Incident.raw_payload`. Although `GroundTruthCertificationService._build_raw_logs` rendered `inc.raw_payload` for human reviewers, `AIS31BenchmarkService._prepare_incident_wire_payload` previously only read `inc.events`, leaving `events: []` on those 54 items.

- **Fix Applied (`AIS31BenchmarkService._extract_sanitized_raw_events_and_summary`):** Falls back to sanitized `Incident.raw_payload` when `inc.events` is empty and merges safe summary fields (`incidentSrc`, `incidentTarget`, `incidentDetailJson`, `incidentDetail`, `count`), strictly preserving `FROZEN_NEUTRAL_SYSTEM_PROMPT`, rule definitions, and required JSON output schema.
- **Leakage Guard Hardened:** Added `"incidentreso"`, `"reso"`, and `"incident_reso"` to both `HistoricalGroundTruthValidator._NORMALIZED_LEAKAGE_KEYS` and `model_payload_allowlist.FORBIDDEN_GROUND_TRUTH_KEYS`, and explicitly stripped historical ML `confidence` and `incidentStatus` before creating fallback events.
