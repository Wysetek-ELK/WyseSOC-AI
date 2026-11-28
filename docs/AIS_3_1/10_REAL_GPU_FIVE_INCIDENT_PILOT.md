# AIS 3.1 — Workstream 10: Live Five-Incident GPU Pilot

**Cohort:** `AIS_3_0_INDEPENDENT_HOLDOUT_100`  
**Selected Pilot FIDs (Blind Ranked `1..5`):** `13960`, `13947`, `14263`, `16164`, `16133`  
**Machine-Readable Evidence:** [GPU_PILOT_RESULTS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_3_1/GPU_PILOT_RESULTS.json)

---

## 1. Pilot Cycle 1 — Technical Defect Discovery (`run_id = ff650d09-74bd-43c2-bdd1-c43295c8531f`)

- **Technical Execution:** `5/5` succeeded against `Qwen/Qwen3-14B-AWQ` (`chatcmpl-*` vLLM request IDs, `35.55s–40.08s`, `0` GT leaks).
- **Wire Prompt Inspection Finding:** All `5/5` returned `REQUIRES_ATTENTION` citing missing destination IPs/ports/details (`scan.raw_events_count = 0`). Inspection of `wire_user_content` for `13960` and `16133` revealed `"events": []` because aggregated FortiSIEM incidents stored telemetry in `Incident.raw_payload` rather than `incident_events` rows.
- **Root-Cause Action Taken (Blind to Holdout Ground Truth Labels):**
  - Fixed `AIS31BenchmarkService._extract_sanitized_raw_events_and_summary` to include sanitized `Incident.raw_payload` when `inc.events` is empty (`raw_payload` keys such as `incidentReso`, `incidentComments`, `incidentClearedTime`, and ML `confidence` strictly stripped).
  - Verified the fix with synthetic unit test `test_ais31_raw_payload_fallback_preserves_evidence_and_strips_leakage` (`28 passed`), pushed via UPLA Gate 1 (`8c760c3b9f7957ad4283678ff1f8d1a31dd5dd96`), and deployed to Server 1 via Gate 2.

---

## 2. Pilot Cycle 2 — Verified Post-Fix Technical Acceptance (`run_id = 0e83d84b-696a-41e5-9231-3434989842ac`)

Executed with `run_key = AIS31-PILOT5-V2-20261128` after re-verifying live `/tokenize` (`100/100` fit `<= 7424`, `0` items with `events == []`):

| Seq | FortiSIEM ID | Rule ID | Events in Wire | Wire Tokens (`vllm_tokenize_api`) | Model Returned | vLLM Request ID | Raw LLM Verdict | Validated App Verdict | Validator Status | GT / Reso Leaks | Latency (s) |
|---:|---|---|---:|---:|---|---|---|---|---|---:|---:|
| 1 | `13960` | `PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT` | 1 | 6,210 | `Qwen/Qwen3-14B-AWQ` | `chatcmpl-9d478ec66bd54612` | `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` | `VALIDATED` | `0` | 64.13 |
| 2 | `13947` | `PH_RULE_WEB_POL_VIOLATION_SAME_SRC_MANY_CATEGORIES` | 1 | 4,313 | `Qwen/Qwen3-14B-AWQ` | `chatcmpl-9a26a8f2a06fb591` | `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` | `VALIDATED` | `0` | 38.29 |
| 3 | `14263` | `PH_RULE_ANOMALY_DNS_DEST` | 1 | 4,853 | `Qwen/Qwen3-14B-AWQ` | `chatcmpl-a00e4ea805518ee0` | `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` | `ABSTENTION_WITH_UNSUPPORTED_CLAIMS` | `0` | 49.40 |
| 4 | `16164` | `PH_RULE_ANOMALY_TRAFFIC_DENIED_OUTBOUND_PORT` | 1 | 5,270 | `Qwen/Qwen3-14B-AWQ` | `chatcmpl-a81e453325e78a50` | `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` | `VALIDATED` | `0` | 53.51 |
| 5 | `16133` | `PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST` | 1 | 5,218 | `Qwen/Qwen3-14B-AWQ` | `chatcmpl-8c47de193e4918b9` | `FALSE_POSITIVE` | `REQUIRES_ATTENTION` | `VERDICT_EVIDENCE_CONFLICT` | `0` | 53.05 |

- **Technical Pilot Gate Decision:** **PASS** (`5/5` real GPU responses, exact target model `Qwen/Qwen3-14B-AWQ`, `events_in_wire_count = 1`, `0` leakage, valid structured JSON outputs citing concrete evidence such as port `443`, `115` connections, UDP port `8801`, and `ad.doubleclick.net`; holdout labels never consulted or used to tune prompts). Proceeded to full 100-incident benchmark.
