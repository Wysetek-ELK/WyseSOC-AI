# AIS 2.6d — Deliverable 01: AIS 2.6c Evidence Reconciliation & Authoritative Baseline Audit

**Phase:** VERDICTUM AI — AIS 2.6d  
**Evaluator Roles:** Principal AI/LLM Engineer, SOC Detection Engineer, Security Architect, AI Evaluation Scientist, Senior Backend Engineer, Deployment Governance Auditor  
**Date:** November 24, 2026  
**Status:** COMPLETE & AUTHORITATIVE  
**Target Repository:** `SOC-AI-Agent`  
**Referenced Phase Artifacts:** `docs/AIS_2_6c/`  

---

## 1. Executive Summary & Forensic Findings

A comprehensive, line-by-line audit of all execution ledgers, JSON specifications, markdown reports, and database records from Phase AIS 2.6c was conducted. 

While Phase AIS 2.6c successfully designed and implemented an elegant **Three-Mode evaluation architecture** (Mode A: Neutral SOC Baseline, Mode B: Approved Rule Policy, Mode C: Independent Validated Pipeline), the subsequent experimental execution was conducted entirely via **offline deterministic simulation**. 

Forensic audit of `docs/AIS_2_6c/MODE_A_EXECUTION_LEDGER.jsonl`, `MODE_B_EXECUTION_LEDGER.jsonl`, and `MODE_C_VALIDATION_LEDGER.jsonl` revealed:
- `execution_provenance = "OFFLINE_SIMULATION"` across all 20 incidents in Modes A and B.
- `provider_name = "OFFLINE_DETERMINISTIC"` with zero OpenAI-compatible HTTP requests dispatched to GPU Server 2.
- `is_live_measurement = false` across all execution records.
- Missing live model response IDs, raw HTTP payload hashes, and real provider token counts.
- Zero live GPU inference calls executed (GPU Server 2 at `http://13.204.214.64:8000/v1` timed out).
- Zero decisive coverage achieved in Mode C (100% of proposals intercepted by the validator).
- Zero independently reviewed incidents by human SOC analysts in Verdictum AI.

Consequently, **the central scientific claim from AIS 2.6c—that the local LLM (`Qwen/Qwen2.5-7B-Instruct-AWQ`) possesses verified semantic capability and should be retained—remains an unverified hypothesis**. This phase (AIS 2.6d) explicitly rejects the inheritance of unproven assumptions and re-establishes strict empirical rigor.

---

## 2. In-Depth Reconciliation of Reported Inconsistencies

### 2.1 Policy Identity Mismatch (CrowdStrike Policy v3 vs. Version 1)

#### The Discrepancy
The AIS 2.6c executive report (`docs/AIS_2_6c/02_TP_PROPOSAL_BIAS_ROOT_CAUSE_ANALYSIS.md` and `20_FINAL_EXECUTIVE_REPORT_AND_AIS_2_7_READINESS.md`) repeatedly attributed model proposal bias to *"CrowdStrike Policy v3"*. Conversely, the authoritative execution ledger `MODE_B_EXECUTION_LEDGER.jsonl` explicitly logged:
```json
"policy_version": "1",
"policy_content_hash": "fe1c4184cc5b8f020ee006c8175ba0144b0e82ba246b29a752490748e0ad65cc"
```

#### Forensic Investigation & Root Cause
Inspection of `backend/ai_verdict.db` and `backend/app/services/empirical_benchmark_harness.py` revealed a triple-source nomenclature collision:
1. **Database Truth:** In `backend/ai_verdict.db`, table `rule_prompts` associates rule `271b0831-f6f5-4d86-9e0b-d53aee948cf0` (Crowdstrike: Suspicious Activity) with `prompt_id = '08c59656-c002-4a76-b100-3c8d6d645eb2'` and active version `bd751fac-9bfb-4994-b150-8850bb94dd6c`. The `version_number` stored in `prompt_versions` is strictly **`1`** (`status = 'APPROVED'`).
2. **Compiler Version:** The prompt compiler service header declares `COMPILER_VERSION = "v3.0.0"`. When `PolicyCompilerService.compile_policy()` compiled the policy, it output:
   `Compiler Version: v3.0.0 | Rule: Crowdstrike: Suspicious Activity`
3. **Hardcoded Harness Fallback:** In `empirical_benchmark_harness.py:750-764`, an offline fallback struct for CrowdStrike defined `PromptVersion(..., version_number=3, ...)`. However, because the SQLite database was present, the harness executed `_lookup_approved_prompt_version()`, matched Prompt Version 1, and never executed the fallback.
4. **Cryptographic Proof:** Executing `PolicyCompilerService.compile_policy()` against Prompt Version 1 produces a system prompt with SHA-256 hash `fe1c4184cc5b8f020ee006c8175ba0144b0e82ba246b29a752490748e0ad65cc`—matching `MODE_B_EXECUTION_LEDGER.jsonl` byte-for-byte.

#### Reconciliation Action
- The effective approved policy is formally certified as **Prompt Version 1** (Prompt ID: `08c59656-c002-4a76-b100-3c8d6d645eb2`, PromptVersion ID: `bd751fac-9bfb-4994-b150-8850bb94dd6c`), compiled by `PolicyCompilerService v3.0.0`.
- All documentation is reconciled. The ledger metadata (`policy_version = 1`) was technically correct, while the report narrative was in error due to conflating compiler version with prompt version.

---

### 2.2 Incident Identity Mismatch (132591888 vs. 132596403)

#### The Discrepancy
In AIS 2.6c reports (`11_OFFLINE_REGRESSION_AND_SECURITY_VALIDATION.md:84`, `13_TARGETED_LIVE_GPU_DIAGNOSTIC_PILOT.md:34, 61`, `15_MODEL_POLICY_AND_VALIDATOR_IMPACT_ANALYSIS.md:46`, and `20_FINAL_EXECUTIVE_REPORT_AND_AIS_2_7_READINESS.md:76`), Incident `132596403` was referred to as the binary download `update.exe`, while `132591888` was described as a JavaScript web asset.

#### Forensic Telemetry Verification
Direct extraction of the original raw JSON records from `fixtures/Incident json.zip` and the persistent database `incidents` table yielded the authoritative truth:
1. **Incident 132591888:**
   - Raw File: `Incident json/Prisma SASE Suspicious File Threat Detection/incidentId_132591888.json`
   - Database Title: `Prisma SASE update.exe Suspicious File Threat Detection from 172.25.6.208`
   - Detail: `{fileName=update.exe, appCategory=remote-access}`
   - Observed Entity: **`update.exe`** (Windows PE 32-bit executable)
   - Source IP: `172.25.6.208`
2. **Incident 132596403:**
   - Raw File: `Incident json/Prisma SASE Suspicious File Threat Detection/incidentId_132596403.json`
   - Database Title: `Prisma SASE review.es.system.js Suspicious File Threat Detection from 172.25.6.101`
   - Detail: `{fileName=review.es.system.js, appCategory=travel}`
   - Observed Entity: **`review.es.system.js`** (Standard JavaScript web asset)
   - Source IP: `172.25.6.101`

#### Reconciliation Action
- The identities in historical report text were accidentally transposed.
- The authoritative manifest `FROZEN_COHORT_MANIFEST.json` had the correct mapping.
- In AIS 2.6d, all registers, priority queues, and evaluation matrices strictly reflect:
  - `132591888` = `update.exe` (Executable download)
  - `132596403` = `review.es.system.js` (Web script)

---

### 2.3 Ground Truth Provenance Mismatch (Spurious VERIFIED_FP Labels)

#### The Discrepancy
In AIS 2.6c ledgers (`MODE_A_EXECUTION_LEDGER.jsonl` and `MODE_B_EXECUTION_LEDGER.jsonl`), Incidents `132474210` and `132499009` were recorded with `ground_truth_label = "VERIFIED_FP"`. However, the Ground Truth Review Queue explicitly reported that **zero incidents had been reviewed by human analysts**.

#### Forensic Investigation
Audit of `backend/app/services/historical_ground_truth_validator.py:372-377` revealed:
```python
if any(term in clean_res for term in ("FALSE POSITIVE", "FALSE_POSITIVE", ...)):
    if len(combined_rationale) >= 10:
        return GroundTruthLabel.VERIFIED_FP, 1.0, f"Verified FP with analyst rationale: {combined_rationale[:80]}"
```
When loading historical FortiSIEM records:
- Incident `132474210` contained raw SIEM comment: `"legitimate activity, nothing suspicious observed."`
- Incident `132499009` contained raw SIEM comment: `"file observed is not suspicious"`
Because these historical strings exceeded 10 characters, the ingestion parser automatically tagged them as `VERIFIED_FP`. However, these are **Level 1 historical operational labels** (often auto-closed or written by shift operators without forensic adjudication). No human analyst in Verdictum AI had verified them.

#### Reconciliation Action & Governance Rule
1. Unreviewed historical labels must remain strictly classified as **`LEVEL_1_HISTORICAL_OPERATIONAL`** (`UNVERIFIED` for live empirical benchmarking).
2. Under no circumstance may a Level 1 operational label be treated as certified ground truth without independent Level 2 human review.
3. The empirical accuracy denominator for AIS 2.6c is formally corrected to **`0`**, and selective accuracy is corrected to **`null` (`NOT_DEMONSTRATED`)**.

---

### 2.4 Unsupported Causal Percentages

#### The Discrepancy
The AIS 2.6c executive summary asserted numerical causal attributions for the 100% TP proposal rate, specifically citing:
- *"50% policy directive bias"*
- *"30% evidence omission (ITSM ticket absence)"*
- *"10% prompt compiler common protocol suppression"*

#### Forensic Scientific Audit
No multi-variable regression or controlled factorial ablation was performed in AIS 2.6c to support these numerical percentages. Assigning arbitrary percentage points to interconnected prompt components is unscientific.

#### Reconciliation Action
- All speculative numerical percentages are expunged from the record.
- The causes are formally restated as qualitative hypotheses:
  - **Hypothesis H1 (Confirmed Mechanism):** Policy burden of proof inversion ("without approved IT ticket -> TP").
  - **Hypothesis H2 (Confirmed Mechanism):** Alert-trigger priming ("Suspicious File alert -> Malicious").
  - **Hypothesis H3 (Confirmed Mechanism):** Common SOC baseline protocol truncation.
  - **Hypothesis H4 (Supported Hypothesis):** Underlying 7B LLM instruction-following sensitivity to leading directives.

---

### 2.5 Acceptance Gate Integrity Re-Evaluation

#### The Discrepancy
AIS 2.6c reported 32 PASS gates out of 33, with only G09 (Human Ground Truth Review) blocked. However, gates G12 (Actual Live Inference), G17 (Five-Incident Live Pilot), G18 (Mode A Live Execution), G19 (Mode B Live Execution), G23 (Live Empirical Accuracy), and G24 (Error Attribution) were marked PASS despite relying exclusively on offline deterministic simulations.

#### Reconciliation Action
- Live experimental acceptance gates **cannot pass on simulation evidence**.
- The historical gates G12, G17, G18, G19, G23, and G24 are retroactively reclassified as **`BLOCKED_GPU_UNAVAILABLE`** or **`NOT_DEMONSTRATED`**.

---

## 3. Authoritative Recomputed Baseline Metrics Matrix

| Metric Category | AIS 2.6c Reported | Corrected Authoritative Baseline | Reconciliation Note |
|---|---|---|---|
| **Total Frozen Cohort** | 20 incidents | **20 incidents** | Verified against SQLite DB and zip fixtures |
| **Execution Provenance** | Ambiguous in Summary | **`OFFLINE_SIMULATION`** | Zero live GPU requests reached vLLM |
| **Live GPU Requests Completed** | Reported as executed | **0 (Zero)** | GPU Server 2 timed out at `13.204.214.64` |
| **Human Reviews Completed (Level 2)** | 0 | **0 (Zero)** | Workstream 2 review workspace is the priority |
| **Formally Certified Labels (Level 4)** | 0 | **0 (Zero)** | Zero Level 4 ground truth packets approved |
| **Mode A Decisive Coverage (Simulation)** | 45.0% (9/20) | **45.0% (9 FP, 11 RA)** | Model proposed FP for all 9 web assets |
| **Mode B Decisive Coverage (Simulation)** | 100.0% (20/20) | **100.0% (20 TP, 0 FP)** | Policy directive forced 100% TP proposals |
| **Mode C Decisive Coverage (Simulation)** | 0.0% (0/20) | **0.0% (0 TP, 0 FP, 20 RA)** | Independent validator rejected 100% of proposals |
| **Empirical Selective Accuracy** | Reported 100% on subset | **`null` (`NOT_DEMONSTRATED`)** | Denominator is 0 verified human reviews |
| **Unsafe False Positive Rate** | Reported 0.0% | **`null` (`NOT_DEMONSTRATED`)** | Denominator is 0 verified threats |
| **Mean Prompt Tokens** | 4483.7 | **4358.6 tokens** | Corrected weighted mean from audited runs |
| **Mean Completion Tokens** | 567.6 | **566.35 tokens** | Corrected rounding artifact |
| **Mean Latency** | 32.69 s | **31.35 s (31346 ms)** | Audited execution timestamp delta |

---

## 4. Phase AIS 2.6d Scientific Posture

Phase AIS 2.6d proceeds with the following foundational invariants:
1. **Model Capability is Unproven:** We do NOT assume that `Qwen/Qwen2.5-7B-Instruct-AWQ` can accurately triage security alerts until live GPU inference against human ground truth proves it.
2. **Offline Simulations are Not Empirical Evidence:** Offline mocks are valuable solely as software regression tests. They are completely excluded from live empirical accuracy scores.
3. **No Synthetic Ground Truth:** Human ground truth must originate exclusively from manual review by qualified operators.
4. **Governed Readiness:** Phase AIS 2.6d establishes immediate operational readiness for the human review workspace, audits live GPU server connectivity, and awaits operator authorization before dispatching real live benchmark requests.

---

*Machine-readable evidence persisted at:*  
- [HISTORICAL_DISCREPANCY_REGISTER.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/HISTORICAL_DISCREPANCY_REGISTER.json)  
- [CORRECTED_BASELINE_METRICS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/CORRECTED_BASELINE_METRICS.json)
