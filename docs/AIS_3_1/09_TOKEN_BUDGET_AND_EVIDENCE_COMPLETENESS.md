# AIS 3.1 — Workstream 9: Token Budget & Evidence Completeness

**Cohort:** `AIS_3_0_INDEPENDENT_HOLDOUT_100`  
**Target Model Verified:** `Qwen/Qwen3-14B-AWQ` (`vLLM 0.33.0`, `max_model_len = 8192`)  
**Machine-Readable Evidence:** [TOKEN_BUDGET_RESULTS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_3_1/TOKEN_BUDGET_RESULTS.json)

---

## 1. Token Budget Configuration

- **Context Ceiling:** `8192` tokens (`max_model_len` verified via `/v1/models`)
- **Reserved Completion Tokens:** `768` tokens (`enable_thinking: false`, `temperature: 0.0`)
- **Target Input Budget:** `7424` tokens (`8192 - 768`)
- **Tokenizer Verification Method:** Live Server 2 `vllm_tokenize_api` (`messages_chat_template`) executed from Server 1 via `GET /api/ground-truth/ais31/cohorts/AIS_3_0_INDEPENDENT_HOLDOUT_100/token-audit?verify_remote_tokenize=true`

---

## 2. Pilot Defect & Remediation (`raw_payload` Fallback + Sanitizer Hardening)

During Workstream 10 initial pilot wire inspection (`13960`, `16133`), **54/100** aggregated FortiSIEM incidents had `0` rows in `incident_events` (`events_total = 0`) because their event attributes (`incidentSrc`, `incidentTarget`, `incidentDetailJson`, `count`, `incidentTitle`) were stored on `Incident.raw_payload`.

1. **Evidence Plumbing Fix:** Added `AIS31BenchmarkService._extract_sanitized_raw_events_and_summary` (mirroring `GroundTruthCertificationService._build_raw_logs`) so all 100 incidents receive non-empty sanitized raw events and canonical evidence (`events_total >= 1` across `100/100` items).
2. **Leakage Guard Hardening:** Added `"incidentreso"`, `"reso"`, and `"incident_reso"` to `HistoricalGroundTruthValidator._NORMALIZED_LEAKAGE_KEYS` and `model_payload_allowlist.FORBIDDEN_GROUND_TRUTH_KEYS`, and stripped historical ML `confidence` and `incidentStatus` prior to fallback event creation. Verified on synthetic non-holdout unit tests (`test_ais31_raw_payload_fallback_preserves_evidence_and_strips_leakage`).

---

## 3. Final Post-Fix Live Remote `/tokenize` Results (All 100 Holdout Items)

| Metric | Pre-Fix Audit | Post-Fix Live `/tokenize` Audit |
|---|---:|---:|
| Cohort Items Audited | 100 (`vllm_tokenize_api`) | **100** (`vllm_tokenize_api`) |
| Items with `events_total == 0` | 54 | **0** (`100/100` have raw event payloads) |
| Context Overflows (`> 7424`) | 0 | **0** |
| All Fit Safely (`<= 7424`) | `true` | **`true`** |
| Min Wire Prompt Tokens | 2,992 | **3,821** |
| Median Wire Prompt Tokens | 4,202.5 | **5,307.0** |
| Mean Wire Prompt Tokens | 4,852.8 | **5,772.3** |
| P95 Wire Prompt Tokens | 7,255 | **7,279** |
| Max Wire Prompt Tokens | 7,284 | **7,317** |
| Auto-Rebudgeted Items | 31 | **29** |

- `FROZEN_NEUTRAL_SYSTEM_PROMPT`, `RuleDefinitionBuilder` rule specs, and required JSON response schema were never truncated on any incident.
