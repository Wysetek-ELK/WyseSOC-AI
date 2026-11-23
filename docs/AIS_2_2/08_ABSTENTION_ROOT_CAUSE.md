# AIS 2.2 Report 08: Abstention & 100% Abstention Root Cause Analysis

**Project:** Verdictum AI  
**Organization:** Wysetek Systems Technologists Pvt. Ltd.  
**Phase:** AIS 2.2 (Core Verdict Accuracy Baseline & Real LLM Benchmark)  
**Date:** 2026-11-23  
**Status:** COMPLETE & AUDITED  

---

## 1. Executive Summary

Across all 33 evaluated operational incidents under baseline policy v7, Verdictum AI's local Qwen2.5-7B model produced a **100.0% abstention rate** (`REQUIRES_ANALYST_REVIEW` / `REQUIRES_ATTENTION`). 

A rigorous diagnostic investigation revealed that this 100% abstention rate was **not** caused by model unresponsiveness or inference timeouts, but was the cumulative result of **four distinct structural and engineering constraints**.

---

## 2. Four Root Causes of 100% Abstention

### Cause 1: Evidence Contract Requirement Mismatch (Policy v7 Defect)
- In Policy v7, the evidence contract designated `network.tcp_flags` and `detection.threshold` as mandatory required fields.
- Analysis of FortiGate raw traffic logs (`events[]`) across 3,197 events demonstrated that FortiGate firewall logs **do not record raw TCP flags** (e.g. SYN, ACK, FIN, RST).
- Because these mandatory fields were absent in raw telemetry, the preflight validation engine and model claim extractor penalized evidence completeness, preventing the model from achieving decisive confidence.

### Cause 2: Event Compaction Truncation Bug
- In `EvidenceNormalizationService`, event compaction logic designed to fit multiple events into the prompt inadvertently truncated `events[0]`.
- Key fields including event timestamp, source port, and protocol name were dropped from the primary trigger event representation.
- Without protocol confirmation in the compiled prompt, the model correctly noted in its reasoning that protocol evidence was missing.

### Cause 3: Strict Anti-FP Conservatism in 7B Parameter Models
- Qwen2.5-7B-Instruct-AWQ exhibits strong safety conservatism. When evaluating network scan alerts (which frequently resemble malicious reconnaissance), the model refuses to declare an alert as a `FALSE_POSITIVE` unless it can cite positive proof of authorization (such as an approved vulnerability scanner IP or scheduled IT maintenance ticket).
- The prompt includes a `<VERIFIED_HISTORICAL_PRECEDENTS>` section intended to provide RAG context of previously cleared scanners.
- In the evaluated environment, the RAG retrieval pipeline returned **0 precedents** for authorized scanner IPs.
- Without authorization evidence, the model prudently concluded: *"Activity matches scanning pattern, but no authorized maintenance ticket was provided. Abstaining to analyst review."*

### Cause 4: 4096-Token Context Ceiling on Server 2
- Server 2's vLLM runtime is configured with a strict context length limit of `4,096 tokens`.
- With prompt templates, system instructions, rule contracts, and multi-event log dumps consuming ~3,000 tokens, only ~1,000 tokens remained for model generation.
- To prevent completion cut-off, the maximum generation tokens was capped at 512 tokens.
- This tight token budget constrained the 7B model from performing extended multi-step reasoning across large event tables, reinforcing conservative abstention.

---

## 3. Candidate Policy v8 Remediation Results

Candidate Policy v8 addressed Causes 1 and 2:
1. Made `network.tcp_flags` optional for firewall log sources.
2. Fixed primary trigger event normalization.
3. Added structured guidance on evaluating recurring internal scanner IP ranges.

**Measured Effect:**
- Grounded claims increased from **0% to 100%** (16/16 claims verifiable).
- Hallucinations dropped from **5 to 0**.
- Trust score increased from **60 to 81.2**.
- However, because Causes 3 and 4 (zero RAG maintenance precedents and 4096 token limit) remain in place on the infrastructure level, the model appropriately preserved 100% safe abstentions.

---

## 4. Key Takeaway

Abstention is a **safety feature**, not a failure. Under enterprise SOC conditions, deferring an ambiguous network scan alert to a human analyst is infinitely safer than making an ungrounded decisive false positive claim that might suppress a real cyber attack.
