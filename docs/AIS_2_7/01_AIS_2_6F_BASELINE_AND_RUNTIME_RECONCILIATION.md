# 01 — AIS 2.6f Baseline & Runtime Reconciliation

**Phase:** AIS 2.7 (Workstream 1)  
**Target Server 1:** `172.26.41.240` (`/opt/wysesoc-ai`)  
**Deployed Commit SHA:** `dfe4e6e59aefddd29347f3103c5c59832e386e9f`  
**Authoritative Database:** PostgreSQL (`ai_verdict` on Server 1, Alembic head `016_ground_truth_certification_and_cohort_isolation`)

---

## 1. Executive Summary

Reconciliation of AIS 2.6e/2.6f documentation against live Server 1 PostgreSQL API telemetry (`/api/health`, `/api/llm/config`, `/api/llm/test-connection`, `/api/ground-truth/cohorts/AIS_2_6E_FROZEN_20/...`, `/api/prompts/summary`, `/api/verdict-intelligence/integration-diagnostics`, `/api/learning/records`) identified **six material discrepancies** between prior local-SQLite-based reports and actual Server 1 production runtime truth. All six are transparently documented and corrected below before GPU benchmark execution.

---

## 2. Reconciled Discrepancies

| ID | Historical Claim (AIS 2.6e / 2.6f) | Actual Server 1 Runtime Truth | Impact & Resolution |
|---|---|---|---|
| **REC-01** | `APPROVED_POLICY_IDENTITY.json` (AIS 2.6f) reported Rule UUIDs `271b0831...` / `b2f1f1e4...` and Approved PromptVersions `bd751fac...` (v1) / `8ae7beaa...` (v1), calling `b6d9df2f...` v3 and `ed7ff3c7...` v1 "legacy fallback UUIDs". | Server 1 PostgreSQL uses Rule UUID `0974a66e-ede2-4a6a-821b-6283a99c8aa4` (`PH_RULE_CS_SUSPICIOUS_ACTIVITY`) with Active Approved **`b6d9df2f-aad8-4208-89de-3e94e64e1b49` (v3)**, and Rule UUID `14481ebd-4e8c-421e-8579-b6ee7995b746` (`Prisma_SASE_Suspicious_File_Threat_Detection_`) with Active Approved **`ed7ff3c7-ff30-49cb-a0f8-fa10eba79ece` (v1)**. | Mode B must evaluate Server 1's actual approved policies (`b6d9df2f` v3 and `ed7ff3c7` v1), not local SQLite fallback v1 fixtures. |
| **REC-02** | `FROZEN_COHORT_MANIFEST.json` (AIS 2.6e) recorded SQLite incident UUIDs (e.g., `4a575b5f...` for `132474210`), and AIS 2.6f `INCIDENT_ID_MAPPING.json` omitted internal UUIDs. | Server 1 PostgreSQL stores distinct internal UUIDs (e.g., `02b2f0a4-534b-4a9c-86b1-ded35526476f` for `132474210`). Both IDs are mapped in [INCIDENT_ID_MAPPING.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_7/INCIDENT_ID_MAPPING.json). | Reconciled across all 20 incidents. |
| **REC-03** | `BENCHMARK_CONTAMINATION_AUDIT.json` (AIS 2.6f) reported `learning_records_count_for_cohort: 0` (inspected local SQLite). | Server 1 `/api/learning/records` returns **20 pre-existing `LearningRecord` rows** matching all 20 frozen benchmark cohort incidents (carrying legacy `[AI Verdict (REQUIRES_ATTENTION - 0%)]:` notes and historical labels). | Documented in [REVIEWER_EXPOSURE_RISK_REGISTER.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_7/REVIEWER_EXPOSURE_RISK_REGISTER.json). RAG is disabled (`rag_block=""`) during AIS 2.7, and `GroundTruthCertificationService` does not write to `LearningRecord`. |
| **REC-04** | AIS 2.6f closeout reported Server 2 (`13.204.214.64`) was `STOPPED` and GT status was `0 GT2 / 20 GT1`. | Server 1 `/api/health` and `/api/llm/test-connection` confirm Server 2 at `http://13.204.214.64:8000/v1` is **currently ONLINE** (`200 OK`, `12.4 ms`, model `Qwen/Qwen2.5-7B-Instruct-AWQ`, `max_model_len=8192`). Operator completed **20/20 locked GT-2 reviews**. | Recorded in Checkpoint A; awaiting explicit benchmark execution authorization before dispatching generation requests. |
| **REC-05** | Server 1 `/api/llm/config` reports `target_input_budget=7424`, `verified_max_model_len=8192`, while `LOCAL_LLM_CONTEXT_BUDGET=16384` and `LOCAL_LLM_MAX_TOKENS=512` (`timeout=30.0s`). | `/api/verdict-intelligence/integration-diagnostics` reports `overall_status: BLOCKED` solely because `LOCAL_LLM_CONTEXT_BUDGET=16384 > 8192`. Model profile for `Qwen/Qwen2.5-7B-Instruct-AWQ` is `{8192, 768, 7424}`. | AIS 2.7 freezes `max_context_tokens=8192` and `reserved_completion_tokens=768` (`<= 7424` input ceiling). Also note `FORTISIEM_AUTO_POLL_ENABLED=true` & `FORTISIEM_AUTO_AI_VERDICT=true` on Server 1. |
| **REC-06** | AIS 2.6e/2.6f evidence hashes were computed from ZIP/SQLite rows and omitted in AIS 2.6f cohort manifest. | Live Server 1 PostgreSQL `raw_evidence_sha256`, `canonical_evidence_sha256`, and `rule_definition_sha256` retrieved for all 20 items. | Reconciled in [INCIDENT_EVIDENCE_HASH_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_7/INCIDENT_EVIDENCE_HASH_MANIFEST.json). |

---

## 3. Verified Server 1 Runtime State (Pre-GPU Execution)

- **Database:** PostgreSQL connected (`3.63 ms` via `/api/health`, `0.61 ms` via diagnostics), `10,440` incidents, `46` rules, Alembic `016_ground_truth_certification_and_cohort_isolation`.
- **Redis / Celery:** Healthy (`live_triage_queue_depth: 0`).
- **Circuit Breaker:** `CLOSED`, `active_concurrent_slots: 0 / 4`.
- **Interactive Browser Verification (AIS 2.6f limitation):** Confirmed via Server 1 HTTP API that all 20 GT-2 reviews persisted cleanly in PostgreSQL.
