# AIS 2.4c — Stage 4: Genuine Five-Incident Qwen Pilot Execution
**Document ID:** `docs/AIS_2_4c/04_REAL_GPU_FIVE_INCIDENT_PILOT.md`  
**Date:** 2026-11-24  
**Author:** Principal LLM Engineer, SOC Detection Engineer, MLOps Engineer, Independent AI Evaluation Auditor  
**Project:** Verdictum AI — Agent Intelligence Studio (AIS 2.4c)  
**Executed Git SHA:** `14fe8a48680029d5d0eaac206cd6cba62ce1dd8e`  
**Server 1 (App):** `172.26.41.240` | **Server 2 (GPU):** `13.204.214.64:8000`  
**Model:** `Qwen/Qwen2.5-7B-Instruct-AWQ`  

---

## 1. Executive Summary & Protocol Overview

In AIS 2.4c, live GPU execution was carried out across the five canonical pilot incidents using the operational production pipeline on Server 1 communicating with the real vLLM provider on Server 2.

### Critical Execution Rules Enforced:
1. **Live Evaluation Mode:** Evaluation mode set strictly to `live`. All heuristic, mock, and offline simulation fallbacks were disabled.
2. **Double-Blind Ground Truth Isolation:** Zero analyst labels or ground-truth classifications were injected into prompts.
3. **Fail-Closed Budget Guarding:** When wire prompts exceeded the strict 3,328-token budget ceiling under 4,096 context, `TokenBudgetService` halted dispatch rather than performing naive evidence truncation or triggering out-of-context crashes.
4. **Separation of Layers:** Raw LLM proposals were captured verbatim and independently evaluated by `IndependentVerdictValidator`.
5. **Zero Evidence Fabrication:** Actual token counts and latencies returned by vLLM were recorded. Incidents halted by preflight budget guards were explicitly recorded as `TOKEN_BUDGET_GUARD` / `CONTEXT_WINDOW_EXCEEDED` and not fabricated as successful GPU inferences.

---

## 2. Five-Incident Pilot Forensic Summary

| Incident ID | Rule / Target | Execution Provenance | Provider Prompt Tokens | Provider Completion Tokens | Total Tokens | Latency (ms) | Raw Qwen Proposed Verdict | Authoritative Final Verdict | Validation Status & Reason Codes |
|---|---|---|---|---|---|---|---|---|---|
| **132438483** | CrowdStrike / UltraViewer | `LIVE_PROVIDER` | 3,365 | 409 | 3,774 | 16,499 | `REQUIRES_ATTENTION` (50.0%) | `REQUIRES_ATTENTION` (0.0%) | `VALIDATED`: `EVIDENCE_CONTRADICTION`, `REASONING_CONTRADICTION` |
| **132527297** | CrowdStrike / UltraViewer | `LIVE_PROVIDER` | 3,370 | 450 | 3,820 | 18,144 | `TRUE_POSITIVE` (85.0%) | `REQUIRES_ATTENTION` (0.0%) | `REJECTED`: `UNSUPPORTED_PREDICATE`, `UNSUPPORTED_CLAIM`, `TP_CRITERIA_UNSATISFIED` |
| **132499009** | Prisma SASE / ss-widget.min.js | `TOKEN_BUDGET_GUARD` | *null* | *null* | *null* | *null* | *null* | `REQUIRES_ATTENTION` (0.0%) | `CONTEXT_WINDOW_EXCEEDED`: Wire prompt (3,709 tokens) exceeded 3,328 budget |
| **132499023** | Prisma SASE / clientlib-site.min.js | `TOKEN_BUDGET_GUARD` | *null* | *null* | *null* | *null* | *null* | `REQUIRES_ATTENTION` (0.0%) | `CONTEXT_WINDOW_EXCEEDED`: Wire prompt (3,747 tokens) exceeded 3,328 budget |
| **132499745** | Prisma SASE / scripts-QBOKETIS.js | `TOKEN_BUDGET_GUARD` | *null* | *null* | *null* | *null* | *null* | `REQUIRES_ATTENTION` (0.0%) | `CONTEXT_WINDOW_EXCEEDED`: Wire prompt (3,701 tokens) exceeded 3,328 budget |

---

## 3. Detailed Forensic Case Studies

### 3.1 Incident 132438483 — CrowdStrike Suspicious Activity (Live GPU)
- **Dataset Source:** `fixtures/Incident json.zip` (`132438483.json`)
- **Target Entity:** `DESKTOP-E0G2R49` (UltraViewer Service)
- **Policy Version ID:** `b6d9df2f-aad8-4208-89de-3e94e64e1b49` (Version 3)
- **Prompt SHA-256:** `e4a1e283fe1bb4ffcb6e96f2280786a72f0f238a7f1696054ec9d3b443a0dbe4`
- **vLLM Request Telemetry:**
  - Endpoint: `POST http://13.204.214.64:8000/v1/chat/completions`
  - HTTP Status: `200 OK`
  - Model: `Qwen/Qwen2.5-7B-Instruct-AWQ`
  - Provider Prompt Tokens: `3,365`
  - Provider Completion Tokens: `409`
  - Provider Total Tokens: `3,774` (<= 4,096 context limit)
  - Finish Reason: `stop`
  - Measured Latency: `16,499 ms` (16.5 seconds)
- **Raw Qwen Reasoning:**
  - Proposed Verdict: `REQUIRES_ATTENTION` (Confidence: 50.0%)
  - Rationale: Model recognized remote desktop execution (UltraViewer) on an endpoint, noted absence of change tickets, but mistakenly asserted that `file.hash_sha256` was missing from telemetry when it was present in canonical evidence records.
- **Independent Verdict Validation:**
  - Validation Status: `VALIDATED` (Abstention confirmed)
  - Reason Codes: `["EVIDENCE_CONTRADICTION", "REASONING_CONTRADICTION"]`
  - Authoritative Verdict: `REQUIRES_ATTENTION` (Safe display confidence: 0.0%)
  - Finding: Validator detected that Qwen contradicted canonical evidence by claiming hashes were absent, but agreed with the final classification (`REQUIRES_ATTENTION`) because dual-use tool activity without external C2 or credential access cannot confirm True Positive.

---

### 3.2 Incident 132527297 — CrowdStrike Suspicious Activity (Live GPU Overrule)
- **Dataset Source:** `fixtures/Incident json.zip` (`132527297.json`)
- **Target Entity:** `TSI-IT-002-95` (UltraViewer Service)
- **Policy Version ID:** `b6d9df2f-aad8-4208-89de-3e94e64e1b49` (Version 3)
- **Prompt SHA-256:** `83c4fed8da086cdaf1ca406e911b027814e650351418b1742362642bc37dc194`
- **vLLM Request Telemetry:**
  - Endpoint: `POST http://13.204.214.64:8000/v1/chat/completions`
  - HTTP Status: `200 OK`
  - Model: `Qwen/Qwen2.5-7B-Instruct-AWQ`
  - Provider Prompt Tokens: `3,370`
  - Provider Completion Tokens: `450`
  - Provider Total Tokens: `3,820` (<= 4,096 context limit)
  - Finish Reason: `stop`
  - Measured Latency: `18,144 ms` (18.1 seconds)
- **Raw Qwen Reasoning:**
  - Proposed Verdict: `TRUE_POSITIVE` (Confidence: 85.0%)
  - Rationale: Model claimed that UltraViewer running from `C:\Program Files (x86)\UltraViewer\UltraViewer_Desktop.exe` constituted malicious backdoor installation. It asserted an unsupported claim linking the binary to an ungrounded attacker entity.
- **Independent Verdict Validation:**
  - Validation Status: `REJECTED` (Decisive True Positive Overruled)
  - Reason Codes: `["UNSUPPORTED_PREDICATE", "UNSUPPORTED_CLAIM", "TP_CRITERIA_UNSATISFIED"]`
  - Authoritative Verdict: `REQUIRES_ATTENTION` (Safe display confidence: 0.0%)
  - Finding: **Demonstration of Validator Efficacy.** The raw LLM hallucinated that a remote administration tool installation was an active malicious compromise without verifying external C2 beaconing, persistence modifications, or malicious command lines. The independent validator intercepted the proposal, rejected the unsupported predicate, enforced `TP_CRITERIA_UNSATISFIED`, and prevented an ungrounded True Positive from reaching analysts.

---

### 3.3 Incidents 132499009, 132499023, 132499745 — Prisma SASE (Budget Preflight Abstention)

#### Incident 132499009:
- **Rule:** `Prisma SASE - An internal host attempted a suspicious connection`
- **Observed Entity:** `ss-widget.min.js` loaded over port 443
- **Wire Token Requirement:** 3,709 tokens (Exceeds 3,328 budget by 381 tokens)
- **Mandatory Security Constraint:** The contract enforces that asset filename and IP alone cannot justify accepted True Positive.
- **Runtime Outcome:** `TokenBudgetService` evaluated the 2,675-token system prompt and 39 canonical evidence records. Because safe compaction preserves all 39 records, wire dispatch would have forced total context to $3{,}709 + 768 = 4{,}477\text{ tokens} > 4{,}096$.
- **Action:** Halted with `CONTEXT_WINDOW_EXCEEDED` / `TOKEN_BUDGET_GUARD`. Zero wire request dispatched; zero provider tokens manufactured.

#### Incident 132499023:
- **Rule:** `Prisma SASE - An internal host attempted a suspicious connection`
- **Observed Entity:** `clientlib-site.min.js`
- **Wire Token Requirement:** 3,747 tokens (Exceeds 3,328 budget by 419 tokens)
- **Runtime Outcome:** Halted with `CONTEXT_WINDOW_EXCEEDED` / `TOKEN_BUDGET_GUARD`.

#### Incident 132499745:
- **Rule:** `Prisma SASE - An internal host attempted a suspicious connection`
- **Observed Entity:** `scripts-QBOKETIS.js`
- **Wire Token Requirement:** 3,701 tokens (Exceeds 3,328 budget by 373 tokens)
- **Mandatory Security Constraint:** A high-entropy or suspicious-looking JavaScript filename alone cannot prove malicious compromise.
- **Runtime Outcome:** Halted with `CONTEXT_WINDOW_EXCEEDED` / `TOKEN_BUDGET_GUARD`.

---

## 4. Failure Classification & Audit Integrity Policy

In strict accordance with audit guidelines:
- Real GPU execution was achieved for 2 of 5 pilot incidents (40%), capturing authentic tokens and latencies.
- The 3 Prisma SASE incidents were halted by `TOKEN_BUDGET_GUARD` because the 4K context baseline cannot accommodate 39 canonical records alongside the 2,675-token contract system prompt without sacrificing completion headroom.
- **Zero data was fabricated:** Neither mock proposals, estimated completions, nor simulated latencies were substituted for the Prisma SASE incidents.
- This boundary is transparently classified as `PARTIALLY_PASSED_BUDGET_BLOCKED`, establishing the definitive requirement for 8,192-token context expansion in AIS 2.5.
