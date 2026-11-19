# 06 — Real Local LLM Blind Verdict Benchmark Report

**Status:** **`BENCHMARK COMPLETE — LIVE GPU INFERENCE ON SERVER 2 VERIFIED — ZERO TRUNCATIONS — 100% CONTRADICTIONS INTERCEPTED`**  
**Execution Timestamp (UTC):** `2026-11-19T04:14:01Z`  
**Server 1 (Verdictum Core):** `172.26.41.240` (deployed SHA `47a49510bed17fd94064d23ddfc912357a2d5cdf`)  
**Server 2 (Verdictum Cortex):** `13.204.214.64:8000` (`Qwen/Qwen2.5-7B-Instruct-AWQ`, `vLLM`)  
**Target Rule:** `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`, UUID `40498741-ee6b-4a71-9101-0d6d3f77154c`)  
**Active Baseline Policy:** **v7** (`d79fb576-c6b9-4f63-9167-3c7a2419b70a`, `APPROVED`)  
**Candidate Policy Evaluated:** **v8** (`20d4f788-85a5-437d-afbe-fe7fd80abca1`, `DRAFT`)  
**Evaluated Cohort:** 6 Canonical Real Incidents (`#176122`, `#176011`, `#167157`, `#175129`, `#173449`, `#164575`)  

---

## 1. Executive Summary & 3-Way Comparative Matrix

The blind benchmark was executed using live GPU inference against Server 2 (`Qwen/Qwen2.5-7B-Instruct-AWQ`), comparing Approved Policy v7 against Candidate Policy v8 and evaluating the prospective effect of RAG learning.

| Metric | Baseline A (Approved v7) | Baseline B (Candidate v8) | Experiment C (Candidate v8 + RAG) |
| :--- | :---: | :---: | :---: |
| **Model & Provider** | Real GPU `Qwen2.5-7B-AWQ` | Real GPU `Qwen2.5-7B-AWQ` | Real GPU `Qwen2.5-7B-AWQ` |
| **Execution Provenance** | `LIVE_PROVIDER` (Server 2) | `LIVE_PROVIDER` (Server 2) | `LIVE_PROVIDER` (Server 2) |
| **Eligible Ground-Truth Cases** | `0` (`NOT_MEASURABLE`) | `0` (`NOT_MEASURABLE`) | `0` (`NOT_MEASURABLE`) |
| **Real LLM Inferences** | `6 / 6` | `6 / 6` | `6 / 6` |
| **Output Truncations** | `0 / 6` (`0.0%`) | `0 / 6` (`0.0%`) | `0 / 6` (`0.0%`) |
| **Essential Scan Fields Preserved** | `14 / 14` (`100%`) | `14 / 14` (`100%`) | `14 / 14` (`100%`) |
| **Total Prompt Tokens (6 cases)** | `18,864` | `19,075` | `19,075` (0 precedents in DB) |
| **Total Completion Tokens (6 cases)** | `2,437` | `2,729` | `2,729` (0 precedents in DB) |
| **Total Tokens Consumed** | `21,301` | `21,804` | `21,804` |
| **Raw Model TP Proposals** | `0 / 6` (`0.0%`) | `4 / 6` (`66.7%`) | `4 / 6` (`66.7%`) |
| **Raw Model Abstentions** | `6 / 6` (`100.0%`) | `2 / 6` (`33.3%`) | `2 / 6` (`33.3%`) |
| **Confidence Scale Compliance** | `100%` | `100% PERCENT_0_100` | `100% PERCENT_0_100` |
| **Factual Contradictions Caught** | N/A (abstained) | **`4 / 4` (`100%`)** | **`4 / 4` (`100%`)** |
| **Effective Governed Verdicts** | **`6/6 REQUIRES_ATTENTION`** | **`6/6 REQUIRES_ATTENTION`** | **`6/6 REQUIRES_ATTENTION`** |
| **False Alarms Leaked to Live** | `0` | `0` | `0` |
| **Critical Missed TPs** | `0` | `0` | `0` |
| **Empirical TP/FP Accuracy** | **`NOT MEASURABLE` (0/0)** | **`NOT MEASURABLE` (0/0)** | **`NOT MEASURABLE` (0/0)** |

---

## 2. Per-Incident Real GPU Live Benchmark Results (Latest Run: 2026-11-19T04:14Z)

All 6 incidents were executed on the live Server 2 vLLM endpoint (`http://13.204.214.64:8000/v1`):

| Incident | Tenant | Raw Events | Prompt / Comp / Total Tokens | Raw Model Proposal (Conf & Scale) | Reasoning Integrity Validator Finding | Trust Score | Effective Governed Verdict | Prompt Execution ID |
| :--- | :--- | :---: | :---: | :---: | :--- | :---: | :---: | :--- |
| **`#176122`** | `GDC_NOC` | `0` | `3,129 / 273 / 3,402` | `REQUIRES_ATTENTION` (`50.0%`, `PERCENT_0_100`) | `ABSTAINED` (`EVIDENCE_CONTRACT_UNVERIFIED`); Header-only alert; model correctly noted lack of raw events. | `6/10` | `REQUIRES_ATTENTION` | `7b89263c...` |
| **`#176011`** | `GDC_NOC` | `100` | `3,186 / 589 / 3,775` | `TRUE_POSITIVE` (`95.0%`, `PERCENT_0_100`) | **`REASONING_CONTRADICTION`**: Model narrative claimed "predominantly unanswered/RST/denied flows" while telemetry observed `bidir=100, unans=0, denied=0`. Overruled. | **`3/10`** | **`REQUIRES_ATTENTION`** | `5895b463...` |
| **`#167157`** | `Demo-SOC` | `100` | `3,202 / 437 / 3,639` | `REQUIRES_ATTENTION` (`50.0%`, `PERCENT_0_100`) | `ABSTAINED`: Mixed destination scope (`internal=2, external=30`); 63% AppCtrl pass events; correctly abstained. | `6/10` | `REQUIRES_ATTENTION` | `4ef4fc14...` |
| **`#175129`** | `GDC_NOC` | `100` | `3,182 / 470 / 3,652` | `TRUE_POSITIVE` (`85.0%`, `PERCENT_0_100`) | **`REASONING_CONTRADICTION`**: Narrative claimed unanswered probe sweep vs observed `bidir=100, unans=0, denied=0`. Overruled. | **`3/10`** | **`REQUIRES_ATTENTION`** | `27a04755...` |
| **`#173449`** | `GDC_NOC` | `100` | `3,188 / 449 / 3,637` | `TRUE_POSITIVE` (`85.0%`, `PERCENT_0_100`) | **`REASONING_CONTRADICTION`**: Narrative claimed predominantly unanswered probes vs observed `bidir=97, unans=3`. Overruled. | **`3/10`** | **`REQUIRES_ATTENTION`** | `cc45d2df...` |
| **`#164575`** | `Demo-SOC` | `100` | `3,188 / 511 / 3,699` | `TRUE_POSITIVE` (`85.0%`, `PERCENT_0_100`) | **`REASONING_CONTRADICTION`**: Narrative claimed zero bidirectional sessions vs observed `bidir=100, unans=0`. Overruled. | **`3/10`** | **`REQUIRES_ATTENTION`** | `8e169f6b...` |

---

## 3. Detailed Incident Trace Analysis

### 1. Incident `#176122` (Header-Only Alert, 0 Raw Events)
- **Observed Telemetry:** `raw_events_count = 0`. Aggregation triggered on FortiSIEM rule condition alone.
- **Model Output:** `verdict: "REQUIRES_ATTENTION"`, `confidence: 50.0%`, `confidence_scale: "PERCENT_0_100"`.
- **Reasoning:** *"Critical evidence is missing. The raw connection events and port sweep telemetry are not available to confirm unauthorized horizontal scanning."*
- **Validator Outcome:** `ABSTAINED`, code `EVIDENCE_CONTRACT_UNVERIFIED`. Trust score `6/10`. Effective verdict: `REQUIRES_ATTENTION`.

### 2. Incident `#176011` (GDC_NOC, 100 Raw Events, 100% External Web Browsing)
- **Observed Telemetry:** Source `172.25.24.154` targeting 75 external destination IPs on port 443 across 108 seconds. `scan.tcp_behavior_summary: bidirectional_sessions=100, unanswered_probes=0, denied_flows=0`. Policy: `Cybersecurity`, Service: `Browsing`.
- **Model Output:** `verdict: "TRUE_POSITIVE"`, `confidence: 95.0%`, `confidence_scale: "PERCENT_0_100"`.
- **Narrative Contradiction:** The model asserted in its claim text: *"Single source probing many destination hosts on one fixed TCP port with predominantly unanswered/RST/denied flows"*, while asserting in its numerical telemetry fields: `"bidirectional_sessions=100, unanswered_probes=0, denied_flows=0"`.
- **Validator Outcome:** Caught by `Check 1` and `Check 2` of `ReasoningIntegrityEngine`. Overruled to `REQUIRES_ATTENTION`, trust score capped at `3/10`. Zero false alarm leakage to FortiSIEM.

### 3. Incident `#167157` (Demo-SOC, 100 Raw Events, Mixed Internal/External Scope)
- **Observed Telemetry:** Source `172.27.29.67` targeting 32 unique destination hosts (2 internal RFC-1918 IPs, 30 external public IPs). 63% AppCtrl pass events.
- **Model Output:** `verdict: "REQUIRES_ATTENTION"`, `confidence: 50.0%`, `confidence_scale: "PERCENT_0_100"`.
- **Reasoning:** Cleanly noted mixed destination scope and lack of verified administrative authorization, safely abstaining.
- **Validator Outcome:** `VALIDATED` safe abstention. Trust score `6/10`. Effective verdict: `REQUIRES_ATTENTION`.

### 4. Incident `#175129` (GDC_NOC, 100 Raw Events, External Browsing)
- **Observed Telemetry:** Source `172.25.24.147` targeting 49 external IPs on port 443. `bidirectional_sessions=100, unanswered_probes=0, denied_flows=0`.
- **Model Output:** `verdict: "TRUE_POSITIVE"`, `confidence: 85.0%`, `confidence_scale: "PERCENT_0_100"`.
- **Validator Outcome:** `REASONING_CONTRADICTION` (claimed unanswered probes on 100% bidirectional traffic). Overruled to `REQUIRES_ATTENTION`, trust score `3/10`.

### 5. Incident `#173449` (GDC_NOC, 100 Raw Events, Web Browsing with Server Resets)
- **Observed Telemetry:** Source `172.25.24.130` targeting 60 external IPs on port 443. `bidirectional_sessions=97, unanswered_probes=3, denied_flows=0`. 5 server-rst events.
- **Model Output:** `verdict: "TRUE_POSITIVE"`, `confidence: 85.0%`, `confidence_scale: "PERCENT_0_100"`.
- **Validator Outcome:** `REASONING_CONTRADICTION`. Verified V8.3 bug fix: diagnostic message correctly reported `"97/100 bidirectional sessions, 3 unanswered probes"` (repaired from V8.2 hardcoded 0). Overruled to `REQUIRES_ATTENTION`.

### 6. Incident `#164575` (Demo-SOC, 100 Raw Events, External HTTPS)
- **Observed Telemetry:** Source `172.27.29.53` targeting 53 external IPs on port 443. `bidirectional_sessions=100, unanswered_probes=0`. Policy: `Cyble-Internet-Access`, Service: `HTTPS`.
- **Model Output:** `verdict: "TRUE_POSITIVE"`, `confidence: 85.0%`, `confidence_scale: "PERCENT_0_100"`.
- **Validator Outcome:** `REASONING_CONTRADICTION`. Overruled to `REQUIRES_ATTENTION`, trust score `3/10`.

---

## 4. Benchmark Conclusions & Operational Insights

1. **Deterministic Guardrails Protect Live Production:**
   - 100% (4/4) of the invalid `TRUE_POSITIVE` model proposals were intercepted and neutralized.
   - Zero contradictory or ungrounded verdicts reached FortiSIEM.
2. **Token Window Stability:**
   - All 6 completions completed without truncation (`finish_reason = stop`).
   - Average prompt tokens: `3,179` (within the `3,328` prompt budget).
   - Average completion tokens: `455` (within the `768` reserved completion budget).
3. **Honest Empirical Status:**
   - Because no human analyst ground truth currently exists (`N = 0`), empirical TP/FP accuracy is honestly reported as **`NOT MEASURABLE`**.
   - No manufactured accuracy score has been claimed.
