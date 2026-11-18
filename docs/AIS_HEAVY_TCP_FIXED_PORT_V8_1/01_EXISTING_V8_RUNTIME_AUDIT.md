# 01 — Existing V8 Runtime Audit & Deployment Reconciliation

**Audit Timestamp (UTC):** `2026-11-18T16:37:00Z` – `2026-11-18T16:47:13Z`
**Target Rule:** `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`, UUID `40498741-ee6b-4a71-9101-0d6d3f77154c`)
**Active Approved Policy (UNCHANGED):** **v7** (`d79fb576-c6b9-4f63-9167-3c7a2419b70a`, `APPROVED`, `ELIGIBLE`)
**Candidate Policy (UNMODIFIED DIGEST):** **DRAFT v8** (`20d4f788-85a5-437d-afbe-fe7fd80abca1`, `policy_digest: c5e87a1e...`, `DRAFT`)
**Local LLM (UNTOUCHED):** `Qwen/Qwen2.5-7B-Instruct-AWQ` on Server 2 (`Verdictum Cortex`, `13.204.214.64:8000`, `ONLINE`, `max_model_len = 4096`)

---

## 1. Server 1 Deployed Code vs. GitHub Sync Reconciliation

| Artifact / Commit | Commit SHA | Scope | Server 1 Deployed? | Evidence |
| :--- | :--- | :--- | :---: | :--- |
| V8 Application Code | `10021a3ffcb8fe5af0e5b769d9d725b5e5745c3c` | Backend + Frontend V8 code | **Yes** (`23 passed`) | Deployed on Server 1 (`pytest` + `npm run build` + `systemctl restart`) |
| V8 Validation Docs Only | `a26da1b5d605297b36ce6424101a140bd8a625ec` | 11 markdown/JSON reports (`upla-20261118-161852-e605a9`) | **GitHub-only docs sync** (not a code deploy) | Explicitly distinguished from code deployment per Phase 1 rule |
| V8.1 Runtime Optimization | `8120d882bbcdf62389ce5053dd8e6565a9451d0e` | Backend V8.1 context/truncation/sample-context engine | **Yes (Live on Server 1 during V8.1 re-benchmark)** | Verified live: `/api/health` = `healthy`, `db=2.05 ms`, `llm=ONLINE`, `14/14` scan fields + `max_tokens=768` confirmed in wire captures |

---

## 2. End-to-End Inference Path Audit (`FortiSIEM → Trust Score`)

Auditing the live V8 inference path (`9e2ebd30-e039-440a-89fd-0b37700c87c2`) isolated the exact origin of every V8 limitation:

| Pipeline Stage | V8 Baseline Behavior | Root Origin of Bottleneck | V8.1 Disposition |
| :--- | :--- | :--- | :--- |
| **1. Evidence Normalization** | `3,197` FortiGate events normalized cleanly; `0/3,197` had `network.tcp_flags`; `appctrl_pass_events` added. | Sampled `100` events contained `32–75` unique hosts, which LLM misread on `#167157` as "below 100-host threshold". | **Fixed in V8.1:** added deterministic `scan.sample_context` distinguishing sample stats from full-window SIEM trigger. |
| **2. Evidence Contract** | 3-tier contract (`required`/`conditional`/`optional`) fixed false `tcp_flags` complaints. | Wire payload duplicated `conditional_fields` & `optional_fields` already present in Section 4 (~80 wasted tokens). | **Fixed in V8.1:** deduplicated wire arrays while preserving local compaction priority. |
| **3. Token Budget & Compaction** | Prompt hit `3,286`–`3,336` tokens out of `4,096`, leaving only `11` compacted fields on 4/5 rich logs. | Empty incident header strings, duplicate `rule_pattern`, and repeated `"evidence_type"` wire keys consumed `~380` tokens, pushing `scan.policy_and_service` out on 4/5 rich incidents. | **Fixed in V8.1:** lossless wire cleanup + `scan.policy_and_service` priority `#0` → **`14/14` fields preserved on `5/5` (`100%`) rich incidents**. |
| **4. Completion Allocation** | `LOCAL_LLM_MAX_TOKENS = 512` and `verdict_pipeline` capped output at `512` tokens. | **5/5 rich-log V8 runs hit `512/512` truncation**, and Section 11 duplicated `evidence_ids` + `cited_evidence_ids`. | **Fixed in V8.1:** raised `4096`-context completion budget to **`768`** tokens + compact Section 11 → **`0/6` (`0%`) truncations**. |
| **5. Structured Output Validation** | `_repair_truncated_json` silently patched cut-off JSON and returned `VALID` without checking `finish_reason == "length"`. | Silent acceptance of truncated output masked incomplete responses. | **Fixed in V8.1:** explicit `finish_reason == "length"` & `_truncated_output` detection → first-class `TRUNCATED_OUTPUT` status + trust cap `<= 4/10`. |
| **6. Model Reasoning (`Qwen2.5-7B-AWQ`)** | Under V8: 6/6 abstained (`0` hallucinations, `16/16` grounded claims). Under V8.1: 4/6 decisive `TRUE_POSITIVE` proposals. | **Critical Model Behavior Finding:** Quantized 7B model misread `bidirectional_sessions=100, unanswered_probes=0` as "predominantly unanswered probes" on 4 browsing incidents; validator actively caught `#164575` (`EVIDENCE_VALUE_MISMATCH`, `REJECTED`). | **Documented honestly;** proves why human ground truth, verified RAG precedents, and deterministic contradiction guards are mandatory before any policy approval. |
