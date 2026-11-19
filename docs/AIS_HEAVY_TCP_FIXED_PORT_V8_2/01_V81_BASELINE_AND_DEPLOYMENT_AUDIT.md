# 01 — V8.1 Baseline Audit & V8.2 Deployment Reconciliation

**Audit Timestamp (UTC):** `2026-11-19T03:30:00Z` – `2026-11-19T03:40:00Z`  
**Target Rule:** `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`, UUID `40498741-ee6b-4a71-9101-0d6d3f77154c`)  
**Canonical Event Type:** `PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`  
**Active Approved Policy (UNCHANGED & PRESERVED):** **v7** (`d79fb576-c6b9-4f63-9167-3c7a2419b70a`, `APPROVED`, `ELIGIBLE`, Quality Score: `84.0/100`)  
**Candidate Policy (UNMODIFIED DIGEST, PRESERVED IN DRAFT):** **DRAFT v8** (`20d4f788-85a5-437d-afbe-fe7fd80abca1`, `policy_digest: c5e87a1ec6ac82c43ed07e62271850521456719da8800299256a897c91f8352b`, Quality Score: `85.0/100`, G1–G7 Passed, G8 Pending)  
**Sibling Rule Isolation (PRESERVED & UNMODIFIED):** `Heavy TCP Host Scan` (`PH_RULE_HEAVY_TCP_HOST_SCAN`, UUID `9839fa49-40ac-4676-abcc-4c5581ae9e09`, Active v2, `APPROVED`, Status `ELIGIBLE`)  
**Server 1 (Verdictum Core):** `172.26.41.240` (`verdictum-core-01`, non-Docker systemd in `/opt/wysesoc-ai`, PostgreSQL 16.4, Redis, nginx `:80`)  
**Server 2 (Verdictum Cortex):** `13.204.214.64:8000` (`verdictum-cortex-01`, GPU-hosted vLLM `Qwen/Qwen2.5-7B-Instruct-AWQ`, `max_model_len = 4096`, `ONLINE`, **DO NOT restart, stop, or modify**)  

---

## 1. Server 1 Deployment Reconciliation & Git History

All V8.2 code improvements have been compiled, verified, synchronized to GitHub (`origin/feature/phase3-compact-ui`), and deployed to Server 1:

| Milestone / Layer | Commit SHA | Scope & Components | Server 1 Status | Evidence / Verification |
| :--- | :--- | :--- | :---: | :--- |
| **V8 Baseline** | `10021a3ffcb8fe5af0e5b769d9d725b5e5745c3c` | Full FortiGate evidence contract, initial token compactor | Deployed | 23 passed unit/integration tests |
| **V8.1 Context & Output** | `8120d882bbcdf62389ce5053dd8e6565a9451d0e` | 4096/768 token budget, Section 4 deduplication, 14/14 scan fields preserved | Deployed | 0/6 truncations on real GPU run `a95cd268` |
| **V8.2 Reasoning & Confidence** | `47a49510bed17fd94064d23ddfc912357a2d5cdf` | `ReasoningIntegrityEngine`, `ConfidenceNormalizer`, Contradiction Checks 4c/4d, Schema updates | **LIVE on Server 1** | Pytest: **`25 passed in 6.45s`**; Next.js: `npm run build` PASS; Health: DB `2.16 ms`, Redis healthy, LLM `ONLINE` |

---

## 2. V8.1 Post-Deployment Audit & Root Cause Analysis

In the V8.1 benchmark (`run_id = a95cd268-7c2b-43c6-8355-1dd27770d6bf`), two distinct technical phenomena were identified:

### A. Solved in V8.1:
1. **Output Truncation:** 5/5 previous V8 runs were capped at 512 tokens with truncated JSON. Raising `LOCAL_LLM_MAX_TOKENS = 768` and streamlining prompt schema completely eliminated truncations (`0/6` clipped responses, completion lengths ranged from 262 to 561 tokens).
2. **Evidence Preservation:** Wire token optimizations ensured that all 14 canonical scan fields (`scan.connection_count`, `scan.raw_events_count`, `scan.unique_destination_hosts`, `scan.destination_scope`, `scan.firewall_action_summary`, `scan.tcp_behavior_summary`, `network.source_ip`, `network.destination_port`, `scan.policy_and_service`, `event.timestamp`, `network.protocol`, `scan.sample_context`, `scan.window_seconds`, `scan.rate_per_second`) were delivered intact to the model.

### B. The Core Problem Discovered: Semantic Contradiction & Factual Inversion
Despite receiving complete evidence, `Qwen/Qwen2.5-7B-Instruct-AWQ` produced decisive `TRUE_POSITIVE` proposals on 4 external browsing incidents (`#176011`, `#175129`, `#173449`, `#164575`) with a fatal semantic contradiction:
- **Observed Telemetry:** `bidirectional_sessions=100, unanswered_probes=0, denied_flows=0`, `destination_scope: internal=0, external=75`, `service=Browsing, policy=Cybersecurity`.
- **Model Free-Text Narrative:** Asserted *"predominantly unanswered probes and client-RST responses"* and claimed horizontal attack reconnaissance.
- **Model Structured Value:** Faithfully copied `"bidirectional_sessions=100, unanswered_probes=0"` into `asserted_value`.
- **Validation Gap:** Because string-matching checked only `asserted_value` against canonical evidence, the model achieved `100%` grounding (`3/3` grounded claims) despite writing a narrative that directly contradicted the underlying telemetry.

### C. The Secondary Problem: Uncalibrated & Ambiguous Confidence Scale
The model returned scalar confidence values of `0.9` or `0.95`. Under the enterprise contract (Section 11), confidence is specified on a `0.0–100.0` scale. Without an explicit `confidence_scale` field, an output of `0.9` is mathematically ambiguous: is it `0.9%` (low confidence) or `90.0%` (high confidence)? Multiplying silently by 100 risks misrepresenting model certainty.

---

## 3. V8.2 Architecture & Remediation Mandates

To solve both vulnerabilities without touching the candidate policy digest or retraining the model, AIS 2.0 V8.2 introduces two deterministic runtime validation layers:

1. **Reasoning Integrity Engine (`backend/app/services/reasoning_integrity_engine.py`):**
   - Implements automated semantic inspection comparing the model's claim prose (`claim_text`) and model reasoning (`reason`) against parsed numeric telemetry.
   - Detects when the model claims unanswered probes or denied flows while telemetry demonstrates bidirectional traffic.
   - Evaluates verdict-evidence consistency, rejecting `TRUE_POSITIVE` verdicts on benign external browsing traffic without corroborating lateral or exploit tradecraft.
   - Automatically overrules contradictory verdicts to `REQUIRES_ATTENTION` and caps the trust score at `<= 3/10`.

2. **Confidence Normalizer (`backend/app/services/confidence_normalizer.py`):**
   - Standardizes canonical confidence representation on a `0.0–100.0` percentage scale.
   - Enforces explicit `confidence_scale` declaration (`PERCENT_0_100` vs `PROBABILITY_0_1`).
   - Rejects ambiguous values in `(0.0, 1.0]` that lack explicit scale declaration as `AMBIGUOUS_SCALE_REJECTED`.
   - Strictly decouples confidence from empirical ground truth.

3. **Parity Between Live Triage and Simulation Lab:**
   - Both pipelines invoke `run_shared_verdict_pipeline`, ensuring identical execution of `IndependentVerdictValidator`, `ReasoningIntegrityEngine`, and `ConfidenceNormalizer`.
