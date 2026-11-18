# 04 — Real Local LLM V7 vs V8 A/B Benchmark Results

**Execution Timestamp (UTC):** `2026-11-18T16:09:10Z` – `2026-11-18T16:12:16Z`
**Server 1 Deployed Commit:** `10021a3ffcb8fe5af0e5b769d9d725b5e5745c3c`
**Model & Endpoint:** `Qwen/Qwen2.5-7B-Instruct-AWQ` on Server 2 (`Verdictum Cortex`, `OPENAI_COMPATIBLE`, `LIVE_PROVIDER`, `is_simulated: false`, `max_model_len = 4096`, `max_tokens = 512`, `temperature = 0.1`)
**Baseline Run (Approved v7):** `run_id = ca113d0a-114d-4322-99fd-2519bb21a5b5` (`policy_digest = e4d388ee...`)
**Candidate Run (DRAFT v8):** `run_id = 9e2ebd30-e039-440a-89fd-0b37700c87c2` (`policy_digest = c5e87a1e...`)
**Identical 6-Incident Test Cohort:** `#176011`, `#175129`, `#164575`, `#167157`, `#173449`, `#176122` (isolated unlabeled exploratory replay; `0` live DB/SIEM mutations)

> **Strict Honesty Notice:** All 6 incidents lack independent analyst ground-truth verdicts (`MISSING_ANALYST_LABEL`). Therefore, this benchmark measures **evidence utilization, grounding quality, hallucination elimination, schema validity, trust scoring, and decision coverage** — NOT empirical TP/FP accuracy (which remains `NOT MEASURABLE`).

---

## 1. Paired Side-by-Side Real Local LLM Comparison Table (V7 vs V8)

| Incident ID (Tenant & Telemetry) | Ver | Raw LLM Verdict (Conf) | Effective Verdict | Grounded Claims (Unsup) | Raw Trust / Trust | Validation Status | Kept Fields | Tokens (P / C / Total) | Latency (ms) | Prompt Capture Integrity |
| :--- | :---: | :--- | :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: |
| **`#176011`** (`GDC_NOC`, 100 raw, `int=0, ext=75, bidir=100`) | **v7** | `REQUIRES_ATTENTION` (`0.0`) | `REQUIRES_ATTENTION` | `0/0` (`0`) | `46.0` / `4/10` | `VALIDATED` *(hallucinated "raw count is zero"!)* | `14` | `3,211 / 315 / 3,526` | `10,931` | `VERIFIED` (`hash_match=true`) |
| **`#176011`** | **v8** | `REQUIRES_ATTENTION` (`0.0`) | `REQUIRES_ATTENTION` | **`3/3` (`0`)** | **`81.0` / `6/10`** | `ABSTAINED` (`CONTRACT_UNVERIFIED`) | `11` | `3,288 / 512 / 3,800` | `16,041` | `VERIFIED` (`hash_match=true`) |
| **`#175129`** (`GDC_NOC`, 100 raw, `int=0, ext=49, bidir=100`) | **v7** | `REQUIRES_ATTENTION` (`0.0`) | `REQUIRES_ATTENTION` | `0/0` (`0`) | `81.0` / `6/10` | `VALIDATED` | `14` | `3,207 / 356 / 3,563` | `12,053` | `VERIFIED` (`hash_match=true`) |
| **`#175129`** | **v8** | `REQUIRES_ATTENTION` (`0.0`) | `REQUIRES_ATTENTION` | **`3/3` (`0`)** | **`81.0` / `6/10`** | `ABSTAINED` (`CONTRACT_UNVERIFIED`) | `12` | `3,336 / 512 / 3,848` | `16,298` | `VERIFIED` (`hash_match=true`) |
| **`#164575`** (`Demo-SOC`, 100 raw, `int=0, ext=53, bidir=100`) | **v7** | `REQUIRES_ATTENTION` (`0.0`) | `REQUIRES_ATTENTION` | `0/0` (`0`) | `81.0` / `2/10` | **`INVALID_MODEL_OUTPUT`** | `14` | `3,213 / 512 / 3,725` | `16,215` | `VERIFIED` (`hash_match=true`) |
| **`#164575`** | **v8** | `REQUIRES_ATTENTION` (`0.0`) | `REQUIRES_ATTENTION` | **`3/3` (`0`)** | **`81.0` / `6/10`** | `ABSTAINED` (`CONTRACT_UNVERIFIED`) | `11` | `3,287 / 512 / 3,799` | `16,104` | `VERIFIED` (`hash_match=true`) |
| **`#167157`** (`Demo-SOC`, 100 raw, `int=2, ext=30, bidir=37, appctrl=63`) | **v7** | `REQUIRES_ATTENTION` (`0.0`) | `REQUIRES_ATTENTION` | `0/0` (`0`) | `46.0` / `4/10` | `VALIDATED` *(hallucinated "raw count is zero"!)* | `14` | `3,227 / 315 / 3,542` | `10,972` | `VERIFIED` (`hash_match=true`) |
| **`#167157`** | **v8** | `REQUIRES_ATTENTION` (`0.0`) | `REQUIRES_ATTENTION` | **`3/3` (`0`)** | **`81.0` / `6/10`** | `ABSTAINED` (`CONTRACT_UNVERIFIED`) | `11` | `3,286 / 512 / 3,798` | `16,080` | `VERIFIED` (`hash_match=true`) |
| **`#173449`** (`GDC_NOC`, 100 raw, `int=0, ext=60, bidir=97, unans=3`) | **v7** | `REQUIRES_ATTENTION` (`0.0`) | `REQUIRES_ATTENTION` | `0/0` (`0`) | `46.0` / `4/10` | `VALIDATED` | `14` | `3,213 / 333 / 3,546` | `11,430` | `VERIFIED` (`hash_match=true`) |
| **`#173449`** | **v8** | `REQUIRES_ATTENTION` (`0.0`) | `REQUIRES_ATTENTION` | **`3/3` (`0`)** | **`81.0` / `6/10`** | `ABSTAINED` (`CONTRACT_UNVERIFIED`) | `11` | `3,290 / 512 / 3,802` | `16,092` | `VERIFIED` (`hash_match=true`) |
| **`#176122`** (`GDC_NOC`, `0` raw, header-only) | **v7** | `REQUIRES_ATTENTION` (`0.0`) | `REQUIRES_ATTENTION` | `0/0` (`0`) | `84.0` / `6/10` | `VALIDATED` *(correct abstention)* | `10` | `3,074 / 325 / 3,399` | `13,226` | `VERIFIED` (`hash_match=true`) |
| **`#176122`** | **v8** | `REQUIRES_ATTENTION` (`0.0`) | `REQUIRES_ATTENTION` | **`1/1` (`0`)** | **`84.0` / `6/10`** | `ABSTAINED` (`CONTRACT_UNVERIFIED`) *(correct abstention)* | `10` | `3,295 / 384 / 3,679` | `15,483` | `VERIFIED` (`hash_match=true`) |

---

## 2. Aggregate V7 vs V8 Comparison Summary

| Metric (Across 6 Identical Real Incidents) | Approved V7 | Candidate DRAFT V8 | Delta / Observation |
| :--- | :---: | :---: | :--- |
| **Real LLM Dispatches Completed** | `6 / 6` | `6 / 6` | `100%` real Server 2 GPU (`is_simulated = false`) |
| **Prompt Capture Hash Verification (`hash_match`)** | `6 / 6` (`100%`) | `6 / 6` (`100%`) | Cryptographic SHA-256 parity maintained |
| **Grounded Canonical Claims (`EV-*` cited & verified)** | `0 / 0` | **`16 / 16` (`100%`)** | **+16 verified grounded claims; `0` unsupported claims** |
| **Hallucinations ("raw event count is zero" on 100-event logs)** | `2 / 5` (`#176011`, `#167157`) | **`0 / 5`** | **100% eliminated on V8** |
| **`INVALID_MODEL_OUTPUT` Failures** | `1 / 6` (`#164575`) | **`0 / 6`** | **100% eliminated on V8** |
| **False `network.tcp_flags` / `detection.threshold` Complaints** | Present pre-alignment | **`0 / 6`** | **100% eliminated on V8** |
| **Mean Raw Trust Score (Rich Incidents)** | `60.0 / 100` | **`81.0 / 100`** | **+21.0 points** (`6/10` cap on all 6/6) |
| **Correct Abstention on Header-Only (`#176122`) & Mixed Internal (`#167157`)** | `2 / 2` | **`2 / 2`** | Preserved cleanly (`#167157` explicitly cited `internal=2, external=30`) |
| **Decisive TP/FP Decision Coverage** | `0 / 6` (`0.0%`) | **`0 / 6` (`0.0%`)** | **Unchanged — see exact empirical diagnosis below** |
| **Total Tokens Consumed (6 runs)** | `21,301` | `22,726` | `+1,425` tokens (`512`-token completion cap reached on 5/5 rich v8 runs) |

---

## 3. Exact Empirical Diagnosis: Why V8 Still Abstained on Rich External-Browsing Incidents (`#176011`, `#175129`, `#164575`)

Inspecting all 6 verbatim V8 captures revealed **two concrete empirical bottlenecks** — proving why V8 MUST NOT be prematurely approved yet:

1. **Server 2 `4,096`-Token Context Ceiling Caused Two Bottlenecks Simultaneously:**
   - **Input Budget Squeeze:** V8's slightly richer system prompt + 3-tier `evidence_contract` used `3,286`–`3,336` prompt tokens (vs. `3,207`–`3,227` on v7), leaving room for `11` canonical fields on `#176011`, `#164575`, `#167157`, `#173449` (dropping `scan.policy_and_service`, `scan.window_seconds`, `scan.rate_per_second`) and `12` fields on `#175129` (keeping `scan.policy_and_service`).
   - **Output Truncation at `max_tokens = 512`:** Because V8 instructed the model to emit full structured `supporting_claims` objects, all 5 rich-log V8 runs hit `completion_tokens = 512/512`, truncating after the 4th claim (cleanly repaired by `_repair_truncated_json` with 3/3 grounded claims intact, zero hallucinations).
2. **Zero Verified RAG Precedents (`retrieved_precedents_count = 0`) + Strict Anti-FP Baseline:**
   - Even on `#175129` (where `scan.policy_and_service = policy=Cybersecurity; service=Browsing` WAS present in the prompt and the model explicitly wrote *"The scan targets public external destinations and shows predominantly closed connections"*), `Qwen/Qwen2.5-7B-Instruct-AWQ` conservatively abstained (`"no verifiable authorization"`) rather than risking an unverified FP without verified historical examples in `<VERIFIED_HISTORICAL_PRECEDENTS>`.

**Conclusion:** Candidate V8 demonstrably improved **grounding (`0 → 16/16` claims), hallucination elimination (`2 → 0`), schema reliability (`1 → 0` invalid outputs), and raw trust (`60.0 → 81.0`)**, while preserving safe abstentions on `#176122` and `#167157`. However, decisive TP/FP coverage remained `0%` due to Server 2's `4,096`-token limit and `0` verified analyst precedents. **Candidate v8 stays in `DRAFT`; Approved v7 remains active.**
