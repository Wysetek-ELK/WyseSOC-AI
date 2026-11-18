# 05 — Real Local LLM Re-Benchmark Report (V7 vs V8 vs V8.1)

**Executed At:** `2026-11-18T16:45:40Z`  
**Server 1 Deployed SHA (Live During Benchmark):** `8120d882bbcdf62389ce5053dd8e6565a9451d0e`  
**Server 2 Real Local LLM:** `Qwen/Qwen2.5-7B-Instruct-AWQ` (`OPENAI_COMPATIBLE`, `is_simulated = false`, `execution_provenance = REAL_LOCAL_LLM`, `max_model_len = 4096`)  
**Rule:** `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`, UUID `40498741-ee6b-4a71-9101-0d6d3f77154c`)  
**Policies Evaluated:**
- Historical Baseline **v7** (`d79fb576-c6b9-4f63-9167-3c7a2419b70a`, `APPROVED`, `run_id = ca113d0a-114d-4322-99fd-2519bb21a5b5`)
- Historical Candidate **v8** (`20d4f788-85a5-437d-afbe-fe7fd80abca1`, `DRAFT`, `run_id = 9e2ebd30-e039-440a-89fd-0b37700c87c2`)
- Optimized Runtime **v8.1** on **unmodified** DRAFT v8 (`20d4f788-85a5-437d-afbe-fe7fd80abca1`, `policy_digest = c5e87a1ec6ac82c43ed07e62271850521456719da8800299256a897c91f8352b`, `run_id = a95cd268-7c2b-43c6-8355-1dd27770d6bf`)

---

## 1. Executive Summary — Controlled 3-Way Real GPU Benchmark

All three runs executed on the exact same 6 real canonical FortiSIEM incidents (`#176011`, `#175129`, `#164575`, `#167157`, `#173449`, `#176122`: 5 rich-log incidents with `100` raw FortiGate events each + 1 header-only control incident `#176122` with `0` raw events).

| Metric | Historical V7 (`ca113d0a`) | Historical V8 (`9e2ebd30`) | Optimized V8.1 (`a95cd268`) | V8 → V8.1 Delta |
| :--- | :---: | :---: | :---: | :---: |
| **Provider / Provenance** | Real GPU `Qwen2.5-7B-AWQ` | Real GPU `Qwen2.5-7B-AWQ` | Real GPU `Qwen2.5-7B-AWQ` | Identical hardware |
| **Evaluated Ground-Truth Cases** | `0` (`INSUFFICIENT_DATA`) | `0` (`INSUFFICIENT_DATA`) | `0` (`INSUFFICIENT_DATA`) | Honest `NOT_CALCULABLE` |
| **Exploratory Real LLM Runs** | `6 / 6` | `6 / 6` | `6 / 6` | `100%` `hash_match = True` |
| **Output Truncations (`finish_reason=length`)** | `1 / 6` (`INVALID_MODEL_OUTPUT`) | **`5 / 6` (`83.3%`, 512/512)** | **`0 / 6` (`0.0%`, 262–561/768)** | **`-5` (`-100%` eliminated)** |
| **Rich-Log Evidence Fields Preserved** | `14 / 14` (unaligned v7) | `11–12 / 14` (dropped `policy_and_service`!) | **`14 / 14` on `5/5` (`100%`)** | **`+2` to `+3` critical fields/incident** |
| **`scan.policy_and_service` Preserved (Rich)** | `0 / 5` (missing in v7) | `0 / 5` (dropped under budget!) | **`5 / 5` (`100%`)** | **Fully restored** |
| **`scan.sample_context` Preserved (Rich)** | `0 / 5` (not emitted) | `0 / 5` (not emitted) | **`5 / 5` (`100%`)** | **New deterministic context** |
| **Total Prompt Tokens (6 incidents)** | `18,864` | `19,782` | **`18,961`** | **`-821` prompt tokens** |
| **Total Completion Tokens (6 incidents)** | `2,437` | `2,944` (5 capped at `512`) | **`2,764`** (`262–561 / 768`) | **0 clipped responses** |
| **Total Tokens (6 incidents)** | `21,301` | `22,726` | **`21,725`** | **`-1,001` total tokens** |
| **Raw LLM Decisive TP/FP Proposals** | `0 / 6` (`0.0%`) | `0 / 6` (`0.0%`) | **`4 / 6` (`66.7%`, all `TRUE_POSITIVE`)** | **See Section 3 Critical Finding!** |
| **Safe Abstention on Header-Only (`#176122`)** | `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` | **`REQUIRES_ATTENTION`** | **Preserved** |
| **Safe Abstention on Mixed Internal (`#167157`)** | `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` | **`REQUIRES_ATTENTION`** | **Preserved (`internal=2, external=30`)** |
| **Effective Governed Verdicts** | `6/6 REQUIRES_ATTENTION` | `6/6 REQUIRES_ATTENTION` | `6/6 REQUIRES_ATTENTION` | DRAFT v8 & validator guardrails held! |
| **Validator Hallucination Rejections** | `0` (abstained) | `0` (abstained) | **`1` (`#164575` `REJECTED`)** | **Validator caught live fabrication!** |
| **Empirical TP/FP Accuracy** | **`NOT MEASURABLE`** | **`NOT MEASURABLE`** | **`NOT MEASURABLE`** | **`0` human analyst reviews** |

---

## 2. Per-Incident V8.1 Real Local LLM Results (`run_id = a95cd268-7c2b-43c6-8355-1dd27770d6bf`)

| Incident | Tenant | Raw Logs | Kept Fields | Prompt / Comp / Total Tokens | Latency (ms) | Raw LLM Proposal (Conf) | Claims (Grounded/Total) | Validator Status & Codes | Trust (Raw) | Effective Verdict | Capture ID & Prompt SHA-256 (Prefix) |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- | :---: | :--- | :---: | :--- | :--- |
| **`#176122`** | `GDC_NOC` | `0` | `10` | `3,110 / 262 / 3,372` | `9,595` | `REQUIRES_ATTENTION` (`0.0`) | `0/0` (`1.0`) | `ABSTAINED` (`EVIDENCE_CONTRACT_UNVERIFIED`) | `6/10` (`84.0`) | `REQUIRES_ATTENTION` | `1289a418` (`f0fd5f5d...`, `hash_match=True`) |
| **`#176011`** | `GDC_NOC` | `100` | **`14`** | `3,167 / 492 / 3,659` | `15,142` | `TRUE_POSITIVE` (`0.9`) | `2/2` (`1.0`) | `ABSTAINED` (`EVIDENCE_CONTRACT_UNVERIFIED`) | `6/10` (`79.0`) | `REQUIRES_ATTENTION` | `27ca0371` (`8786bcea...`, `hash_match=True`) |
| **`#167157`** | `Demo-SOC` | `100` | **`14`** | `3,183 / 370 / 3,553` | `11,959` | `REQUIRES_ATTENTION` (`0.0`) | `0/0` (`1.0`) | `ABSTAINED` (`EVIDENCE_CONTRACT_UNVERIFIED`) | `3/10` (`79.0`) | `REQUIRES_ATTENTION` | `5661b6ec` (`7007789d...`, `hash_match=True`) |
| **`#175129`** | `GDC_NOC` | `100` | **`14`** | `3,163 / 561 / 3,724` | `17,007` | `TRUE_POSITIVE` (`0.95`) | `3/3` (`1.0`) | `ABSTAINED` (`EVIDENCE_CONTRACT_UNVERIFIED`) | `6/10` (`79.0`) | `REQUIRES_ATTENTION` | `ccb491fa` (`58a239b4...`, `hash_match=True`) |
| **`#173449`** | `GDC_NOC` | `100` | **`14`** | `3,169 / 534 / 3,703` | `16,344` | `TRUE_POSITIVE` (`0.9`) | `3/3` (`1.0`) | `ABSTAINED` (`EVIDENCE_CONTRACT_UNVERIFIED`) | `6/10` (`79.0`) | `REQUIRES_ATTENTION` | `e3b6d3b1` (`a8933707...`, `hash_match=True`) |
| **`#164575`** | `Demo-SOC` | `100` | **`14`** | `3,169 / 545 / 3,714` | `16,664` | `TRUE_POSITIVE` (`0.9`) | `2/3` (`0.667`) | **`REJECTED`** (`EVIDENCE_CONTRACT_UNVERIFIED`, **`EVIDENCE_VALUE_MISMATCH`**) | **`3/10`** (`79.0`) | `REQUIRES_ATTENTION` | `865c78c0` (`58388079...`, `hash_match=True`) |

Every single one of the 5 rich-log incidents (`#176011`, `#167157`, `#175129`, `#173449`, `#164575`) received all **14 essential canonical scan fields** verbatim:
`scan.connection_count`, `scan.raw_events_count`, `scan.unique_destination_hosts`, `scan.destination_scope`, `scan.firewall_action_summary`, `scan.tcp_behavior_summary`, `network.source_ip`, `network.destination_port`, `scan.policy_and_service`, `event.timestamp`, `network.protocol`, `scan.sample_context`, `scan.window_seconds`, `scan.rate_per_second`.

---

## 3. Critical Empirical Finding: 7B AWQ Factual Inversion & Guardrail Proof (Must Not Be Masked!)

> [!WARNING]
> **Higher raw LLM decisive proposal coverage (`4/6` vs `0/6`) is NOT proof of improved TP/FP accuracy.** Direct inspection of all 6 raw `Qwen/Qwen2.5-7B-Instruct-AWQ` JSON responses revealed a critical 7B reasoning defect that proves why AIS 2.0's independent validation and human ground-truth gates are essential.

### A. Observed 7B Model Factual Inversion on All 4 `TRUE_POSITIVE` Proposals
On all four external HTTPS/Browsing rich-log incidents (`#176011`, `#175129`, `#173449`, `#164575`), the actual observed FortiGate telemetry in the prompt was:
- `#176011`: `bidirectional_sessions=100, unanswered_probes=0, denied_flows=0`, `internal=0, external=75`, `policy=Cybersecurity, service=Browsing`
- `#175129`: `bidirectional_sessions=100, unanswered_probes=0, denied_flows=0`, `internal=0, external=49`, `policy=Cybersecurity, service=Browsing`
- `#173449`: `bidirectional_sessions=97, unanswered_probes=3, denied_flows=0`, `internal=0, external=60`, `policy=Cybersecurity, service=Browsing`
- `#164575`: `bidirectional_sessions=100, unanswered_probes=0, denied_flows=0`, `internal=0, external=53`, `policy=Cyble-Internet-Access, service=HTTPS`

Yet the 4-bit quantized `Qwen/Qwen2.5-7B-Instruct-AWQ` model produced **two distinct failure patterns** when attempting to apply the v8 TP/FP criteria:

1. **Direct Numeric Fabrication — Caught Live by `IndependentVerdictValidator` (`#164575`):**
   - Model emitted: `"asserted_value": "bidirectional_sessions=0, unanswered_probes=100, denied_flows=0"` (exact inversion of `bidirectional_sessions=100, unanswered_probes=0`).
   - **AIS 2.0 Defense Outcome:** `ModelClaimExtractor` + `IndependentVerdictValidator` immediately compared `asserted_value` against canonical evidence `EV-164575-SCAN_SUMMARY-scan_tcp_behavior_summary`, raised **`EVIDENCE_VALUE_MISMATCH`**, marked `validation_status = REJECTED`, dropped `grounding_ratio` to `0.667` (`2/3`), downgraded `trust_score` to `3/10`, and forced `effective_verdict = REQUIRES_ATTENTION`.

2. **Prose-vs-Value Contradiction (`#176011`, `#175129`, `#173449`):**
   - Model copied the **exact true telemetry** into `asserted_value` (e.g., `"bidirectional_sessions=100, unanswered_probes=0, denied_flows=0, sampled_events=100"`), passing string/numeric value matching (`grounded_claims = 2/2` or `3/3`), **yet simultaneously wrote the opposite in free-text prose**:
     - `#176011` `claim_text`: *"Single source probing many destination hosts on one fixed TCP port with predominantly unanswered probes."*
     - `#175129` `claim_text`: *"Single source probing many destination hosts on one fixed TCP port with predominantly unanswered RST responses."*
     - `#173449` `claim_text`: *"Single source probing many destination hosts on port 443 with predominantly unanswered probes and client-RST responses."*
   - **Why this happened:** Under a `4,096`-token context window with a 7B AWQ model and **0 verified RAG precedents** (`NO_VERIFIED_PRECEDENT`), the rule title (`Heavy TCP Host Scan On Fixed Port`) and TP section phrasing (`predominantly unanswered/RST/denied flows`) induced lexical prior bias over the numeric `bidirectional_sessions=100, unanswered_probes=0` counts.
   - **Why safety still held:** Because DRAFT v8 is unapproved (`EVIDENCE_CONTRACT_UNVERIFIED`), trust is capped `<= 6/10` (`< 7/10` automation threshold), and `automation_policy.is_enabled = False`, **zero** unverified or erroneous verdicts reached live triage or FortiSIEM.

### B. Additional Real-Model Observations
- **Safe Abstentions Worked Correctly:**
  - `#176122` (0 raw logs): Model cleanly abstained (`REQUIRES_ATTENTION`, `confidence = 0.0`) citing missing `scan.raw_events_count` and scan summaries.
  - `#167157` (`Demo-SOC`, `internal=2, external=30`, `63% appctrl_pass_events`): Model cleanly abstained (`REQUIRES_ATTENTION`, `confidence = 0.0`) and flagged `"internal=2, external=30, total_unique_hosts=32"` in `contradictory_evidence`.
- **Confidence Scale Drift:** On all 4 `TRUE_POSITIVE` outputs, `Qwen2.5-7B-Instruct-AWQ` returned `confidence` on a `0.0–1.0` scale (`0.9`, `0.95`) instead of `0–100` (`90.0`, `95.0`). Future V8.2 hardening should normalize or explicitly constrain the output scale while keeping raw confidence decoupled from empirical accuracy.

---

## 4. V8.1 Benchmark Verdict

- **Infrastructure, Context & Output Integrity Objectives:** **ACHIEVED** (`0/6` truncations, `14/14` fields preserved on `5/5` rich incidents, `-821` prompt tokens, `6/6` SHA-256 hash integrity, live `EVIDENCE_VALUE_MISMATCH` catch on `#164575`).
- **Empirical Verdict Accuracy Objective:** **`NOT MEASURABLE` (`0` human analyst reviews)** — and raw 7B reasoning quality on `bidirectional_sessions=100` vs `unanswered_probes=0` requires **verified human analyst precedents (RAG)** plus a **V8.2 deterministic prose-vs-telemetry contradiction check** before any candidate policy can be considered for approval or promotion.
