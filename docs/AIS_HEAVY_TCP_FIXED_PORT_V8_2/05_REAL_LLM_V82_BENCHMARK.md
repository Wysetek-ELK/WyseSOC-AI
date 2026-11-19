# 05 — Real Local LLM V8.2 Benchmark Report

**Executed At (UTC):** `2026-11-19T03:35:04Z`  
**Server 1 Deployed SHA:** `47a49510bed17fd94064d23ddfc912357a2d5cdf`  
**Server 2 GPU Model:** `Qwen/Qwen2.5-7B-Instruct-AWQ` on `13.204.214.64:8000` (`OPENAI_COMPATIBLE`, `is_simulated = false`, `execution_provenance = LIVE_PROVIDER`, `max_model_len = 4096`)  
**Target Rule:** `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`, UUID `40498741-ee6b-4a71-9101-0d6d3f77154c`)  
**Active Policy:** v7 (`d79fb576-c6b9-4f63-9167-3c7a2419b70a`, `APPROVED`)  
**Candidate Policy Evaluated:** DRAFT v8 (`20d4f788-85a5-437d-afbe-fe7fd80abca1`, `policy_digest: c5e87a1ec6ac82c43ed07e62271850521456719da8800299256a897c91f8352b`)  
**Simulation Run ID:** `2074b011-9fe8-46fb-9937-ff5ead18fc61` (and `86468327-4774-4183-800a-a3a31306d47f`)  

---

## 1. Executive Summary — 4-Way Historical & Evolutionary Benchmark

All four benchmark runs were executed on the exact same 6 real canonical FortiSIEM incidents (`#176011`, `#175129`, `#164575`, `#167157`, `#173449`, `#176122`).

| Metric | Historical V7 (`ca113d0a`) | Historical V8 (`9e2ebd30`) | Optimized V8.1 (`a95cd268`) | Validated V8.2 (`2074b011`) |
| :--- | :---: | :---: | :---: | :---: |
| **Provider / Provenance** | Real GPU `Qwen2.5-7B-AWQ` | Real GPU `Qwen2.5-7B-AWQ` | Real GPU `Qwen2.5-7B-AWQ` | Real GPU `Qwen2.5-7B-AWQ` |
| **Evaluated Ground-Truth Cases** | `0` (`INSUFFICIENT_DATA`) | `0` (`INSUFFICIENT_DATA`) | `0` (`INSUFFICIENT_DATA`) | `0` (`INSUFFICIENT_DATA`) |
| **Exploratory Real LLM Inferences** | `6 / 6` | `6 / 6` | `6 / 6` | `6 / 6` |
| **Output Truncations (`finish_reason=length`)** | `1 / 6` | **`5 / 6` (`83.3%`)** | **`0 / 6` (`0.0%`)** | **`0 / 6` (`0.0%`)** |
| **Rich-Log Evidence Fields Preserved** | `14 / 14` (unaligned) | `11–12 / 14` (dropped) | **`14 / 14` (`100%`)** | **`14 / 14` (`100%`)** |
| **Total Prompt Tokens (6 incidents)** | `18,864` | `19,782` | `18,961` | `19,075` |
| **Total Completion Tokens (6 incidents)** | `2,437` | `2,944` (clipped) | `2,764` (clean) | `3,217` (clean) |
| **Total Tokens (6 incidents)** | `21,301` | `22,726` | `21,725` | `22,292` |
| **Raw Model TP Proposals** | `0 / 6` | `0 / 6` | `4 / 6` (`66.7%`) | `4 / 6` (`66.7%`) |
| **Confidence Scale Compliance** | Uncalibrated | Uncalibrated | `0.0–1.0` (ambiguous) | **`100% PERCENT_0_100`** |
| **Factual Inversions Caught by Validator** | `0` (abstained) | `0` (abstained) | `1` (`#164575` value mismatch) | **`4 / 4` (`100%`) caught & neutralized** |
| **Effective Governed Verdicts** | `6/6 REQUIRES_ATTENTION` | `6/6 REQUIRES_ATTENTION` | `6/6 REQUIRES_ATTENTION` | **`6/6 REQUIRES_ATTENTION`** |
| **Contradictory Verdicts Leaked to Live** | `0` | `0` | `0` | **`0`** |
| **Empirical TP/FP Accuracy** | **`NOT MEASURABLE`** | **`NOT MEASURABLE`** | **`NOT MEASURABLE`** | **`NOT MEASURABLE`** |

---

## 2. Per-Incident V8.2 Real Local LLM Results (`run_id = 2074b011-9fe8-46fb-9937-ff5ead18fc61`)

| Incident | Tenant | Raw Logs | Prompt / Comp / Total Tokens | Raw Model Proposal (Conf & Scale) | Grounding Ratio | Validator Status & Reason Codes | Trust Score | Effective Governed Verdict | Prompt SHA-256 (Prefix) & Capture ID |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- | :---: | :---: | :--- |
| **`#176122`** | `GDC_NOC` | `0` | `3,129 / 273 / 3,402` | `REQUIRES_ATTENTION` (`0.0%`, `PERCENT_0_100`) | `0/0` (`1.0`) | `ABSTAINED` (`EVIDENCE_CONTRACT_UNVERIFIED`) | `6/10` | `REQUIRES_ATTENTION` | `400efa4f...` (`895d3523`) |
| **`#176011`** | `GDC_NOC` | `100` | `3,186 / 552 / 3,738` | `TRUE_POSITIVE` (`95.0%`, `PERCENT_0_100`) | `3/3` (`1.0`) | **`REASONING_CONTRADICTION`** (`EVIDENCE_CONTRACT_UNVERIFIED`, `REASONING_CONTRADICTION`, `VERDICT_EVIDENCE_CONFLICT`, `TP_CRITERIA_UNSATISFIED`) | **`3/10`** | **`REQUIRES_ATTENTION`** | `b7764e13...` (`c471e494`) |
| **`#167157`** | `Demo-SOC` | `100` | `3,202 / 439 / 3,641` | `REQUIRES_ATTENTION` (`0.0%`, `PERCENT_0_100`) | `2/2` (`1.0`) | `ABSTAINED` (`EVIDENCE_CONTRACT_UNVERIFIED`) | `6/10` | `REQUIRES_ATTENTION` | `68626d3c...` (`7bd22a3e`) |
| **`#175129`** | `GDC_NOC` | `100` | `3,182 / 683 / 3,865` | `TRUE_POSITIVE` (`95.0%`, `PERCENT_0_100`) | `3/3` (`1.0`) | **`REASONING_CONTRADICTION`** (`EVIDENCE_CONTRACT_UNVERIFIED`, `REASONING_CONTRADICTION`, `VERDICT_EVIDENCE_CONFLICT`, `TP_CRITERIA_UNSATISFIED`) | **`3/10`** | **`REQUIRES_ATTENTION`** | `6f6252ab...` (`b99e97d8`) |
| **`#173449`** | `GDC_NOC` | `100` | `3,188 / 557 / 3,745` | `TRUE_POSITIVE` (`95.0%`, `PERCENT_0_100`) | `2/2` (`1.0`) | **`REASONING_CONTRADICTION`** (`EVIDENCE_CONTRACT_UNVERIFIED`, `REASONING_CONTRADICTION`) | **`3/10`** | **`REQUIRES_ATTENTION`** | `ea5e100e...` (`a1659236`) |
| **`#164575`** | `Demo-SOC` | `100` | `3,188 / 713 / 3,901` | `TRUE_POSITIVE` (`95.0%`, `PERCENT_0_100`) | `3/3` (`1.0`) | **`REASONING_CONTRADICTION`** (`EVIDENCE_CONTRACT_UNVERIFIED`, `REASONING_CONTRADICTION`, `VERDICT_EVIDENCE_CONFLICT`, `TP_CRITERIA_UNSATISFIED`) | **`3/10`** | **`REQUIRES_ATTENTION`** | `912c3118...` (`31be1d1a`) |

---

## 3. In-Depth Analysis of Individual Incident Behaviors

### 1. Incident `#176122` (GDC_NOC, 0 Raw Events — Header-Only Baseline)
- **Model Behavior:** Cleanly abstained (`REQUIRES_ATTENTION`, `confidence: 0.0%`). Correctly noted absence of raw connection events and port sweep telemetry.
- **Validator Outcome:** `ABSTAINED`, code `EVIDENCE_CONTRACT_UNVERIFIED`. Trust score `6/10`. Effective verdict `REQUIRES_ATTENTION`.

### 2. Incident `#176011` (GDC_NOC, 100 Raw Events — External Web Browsing)
- **Telemetry:** `bidirectional_sessions=100, unanswered_probes=0, denied_flows=0`, `destination_scope: internal=0, external=75`, `service=Browsing, policy=Cybersecurity`.
- **Model Proposal:** Proposed `TRUE_POSITIVE` with `confidence: 95.0, confidence_scale: PERCENT_0_100`. Claimed *"predominantly unanswered/RST/denied flows"*.
- **Contradiction Caught:**
  1. Narrative claims unanswered probes vs observed `bidirectional_sessions=100` and `unanswered_probes=0`.
  2. Narrative asserts denied/blocked flows vs observed `denied_flows=0`.
  3. Verdict conflict: `TRUE_POSITIVE` on 100% external bidirectional browsing without lateral or exploit tradecraft (`TP_CRITERIA_UNSATISFIED`).
- **Validator Outcome:** `REASONING_CONTRADICTION`. Trust score capped at `3/10`. Overruled to `REQUIRES_ATTENTION`.

### 3. Incident `#167157` (Demo-SOC, 100 Raw Events — Mixed Scope)
- **Telemetry:** `internal=2, external=30, total=32`, `63% appctrl_pass_events`.
- **Model Proposal:** Correctly recognized mixed scope and abstained (`REQUIRES_ATTENTION`, `confidence: 0.0%`).
- **Validator Outcome:** `ABSTAINED`. Trust score `6/10`. Effective verdict `REQUIRES_ATTENTION`.

### 4. Incident `#175129` (GDC_NOC, 100 Raw Events — External Web Browsing)
- **Telemetry:** `bidirectional_sessions=100, unanswered_probes=0, denied_flows=0`, `destination_scope: internal=0, external=49`, `service=Browsing`.
- **Model Proposal:** Proposed `TRUE_POSITIVE` (`95.0%`). Claimed unanswered RST responses.
- **Contradiction Caught:**
  1. Narrative claims unanswered probes vs observed `bidirectional_sessions=100` and `unanswered_probes=0`.
  2. Verdict conflict: `TRUE_POSITIVE` on 100% external bidirectional browsing (`TP_CRITERIA_UNSATISFIED`).
- **Validator Outcome:** `REASONING_CONTRADICTION`. Trust score capped at `3/10`. Overruled to `REQUIRES_ATTENTION`.

### 5. Incident `#173449` (GDC_NOC, 100 Raw Events — Web Browsing with Client Resets)
- **Telemetry:** `bidirectional_sessions=97, unanswered_probes=3, denied_flows=0`, `destination_scope: internal=0, external=60`, `service=Browsing`.
- **Model Proposal:** Proposed `TRUE_POSITIVE` (`95.0%`). Claimed predominantly unanswered probes and denied flows.
- **Contradiction Caught:**
  1. Narrative claims predominantly unanswered probes vs observed `bidirectional_sessions=97` (97% bidirectional).
  2. Narrative claims denied flows vs observed `denied_flows=0`.
- **Validator Outcome:** `REASONING_CONTRADICTION`. Trust score capped at `3/10`. Overruled to `REQUIRES_ATTENTION`.

### 6. Incident `#164575` (Demo-SOC, 100 Raw Events — External HTTPS Traffic)
- **Telemetry:** `bidirectional_sessions=100, unanswered_probes=0, denied_flows=0`, `destination_scope: internal=0, external=53`, `service=HTTPS, policy=Cyble-Internet-Access`.
- **Model Proposal:** Proposed `TRUE_POSITIVE` (`95.0%`). Claimed zero bidirectional sessions and unanswered probes.
- **Contradiction Caught:**
  1. Narrative claims unanswered probes vs observed `bidirectional_sessions=100`.
  2. Asserted zero bidirectional sessions vs observed `bidirectional_sessions=100`.
  3. Verdict conflict: `TRUE_POSITIVE` on 100% external HTTPS browsing (`TP_CRITERIA_UNSATISFIED`).
- **Validator Outcome:** `REASONING_CONTRADICTION`. Trust score capped at `3/10`. Overruled to `REQUIRES_ATTENTION`.

---

## 4. Benchmark Conclusion

The V8.2 deployment achieves total deterministic reasoning integrity:
1. **Zero Hallucination Leakage:** 100% of the 4 invalid `TRUE_POSITIVE` model proposals were intercepted and neutralized by `ReasoningIntegrityEngine`.
2. **Mathematical Confidence Rigor:** The model returned 100% explicit `PERCENT_0_100` scales without decimal ambiguity.
3. **Safety Protection Held:** Zero erroneous automated actions were executed.
4. **Empirical Ground-Truth Status:** Remains **`NOT MEASURABLE`** until independent human analyst ground truth is established in the database.
