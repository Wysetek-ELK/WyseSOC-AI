# AIS 2.5 — Stage 1: Mandatory AIS 2.4c Integrity Closeout & Provenance Audit

**Document ID:** `docs/AIS_2_5/01_AIS_2_4C_INTEGRITY_CLOSEOUT.md`  
**Phase:** AIS 2.5 (Certified Evidence, Controlled 8K Inference & Real LLM Accuracy Benchmark)  
**Author:** Principal SOC AI Architect, LLM/MLOps Engineer, Detection Engineer, Independent Empirical Evaluation Auditor  
**Date:** November 24, 2026  
**Status:** AUDITED, RECONCILED & CLOSED OUT  
**Hard Gate Evaluation:** RESOLVED (Integrity block cleared for controlled benchmark progression)

---

## 1. Executive Summary & Defect Remediation

Before progressing to the real GPU inference benchmark in AIS 2.5, this audit rigorously resolves the four core evidence-integrity defects identified in AIS 2.4c:

1. **Deployment Identity & Evidence Sequencing:** Reconciled Server 1 deployed Git SHA and UPLA execution metadata. Corrected premature evidence generation so that all reports and evidence capture strictly reflect post-deployment running state.
2. **Historical Cohort Provenance:** Recomputed 100% of authentic FortiSIEM records from `fixtures/Incident json.zip`. Identified the root cause of why AIS 2.4a and AIS 2.4c reports shared only 8 of 20 incident IDs (12 IDs were erroneously substituted in AIS 2.4c).
3. **Telemetry Clustering & Internal Contradiction:** Dissected the AIS 2.4c manifest contradiction (16 clusters vs. 15 clusters reported) and established the definitive 15-cluster / 5-duplicate distribution across the 20 authentic records.
4. **Ground-Truth Adjudication & FP Demotion for `132499023`:** Refuted the erroneous AIS 2.4c claim that `132499023` was identical to `132499009`. Restored its verified forensic classification to `UNVERIFIED` in accordance with double-blind standards.
5. **Token-Budget Invariant & Local Estimation Discrepancy:** Analyzed why prompts of 3,365 and 3,370 tokens were dispatched under a 4,096 context window despite a 768-token completion reserve requirement. Established the invariant `wire_prompt_tokens + reserved_completion_tokens <= active_max_model_len` and calibrated the tokenizer safety margin.
6. **Provenance Taxonomy Normalization:** Replaced ad-hoc execution provenance labels (`TOKEN_BUDGET_GUARD`) with standard `PREFLIGHT_ABSTENTION` and specific reason codes (`CONTEXT_WINDOW_EXCEEDED` / `TOKEN_BUDGET_GUARD`).

---

## 2. Section A: Deployment Identity & Running State Truth

### 2.1 Inspection of UPLA Execution `upla-20261124-034752-53f0bc`
A complete audit of UPLA execution `upla-20261124-034752-53f0bc` was conducted:
- **Execution ID:** `upla-20261124-034752-53f0bc`
- **Project ID:** `proj-98348ed9ed5e2ba1`
- **Workflow Mode:** `FULL_WORKFLOW` (Profile: `development`)
- **Approved & Deployed Git SHA:** `c9a2a172658dbc6661a7fe117a581d42684d3d5a` (`c9a2a17`)
- **Target Server:** Server 1 (`server-1`, `172.26.41.240`, staging/application)
- **Deployment Status:** `DEPLOYED_AND_VERIFIED`

### 2.2 Forensic Reconciliation of `FINAL_EVIDENCE.json`
In AIS 2.4c, `FINAL_EVIDENCE.json` was generated at timestamp `2026-11-24T09:07:00+05:30`. However, the remote deployment under UPLA execution `upla-20261124-034752-53f0bc` did not complete until `09:21:00+05:30`. Consequently, `FINAL_EVIDENCE.json` in AIS 2.4c recorded:
- `"deployed_server1_sha": "14fe8a48680029d5d0eaac206cd6cba62ce1dd8e"` (Stale SHA from previous execution `upla-20261123-170937-7fae60`)
- `"upla_execution_id": "upla-20261123-170937-7fae60"`

**Remediation Rule for AIS 2.5:**
Evidence recording must occur strictly **after** deployment verification is finalized, never before. The active running code identity across FastAPI (`ai-verdict-backend.service`), Next.js (`ai-verdict-frontend.service`), and Celery workers on Server 1 is certified at:
$$\mathbf{\text{Deployed SHA: }} \texttt{c9a2a172658dbc6661a7fe117a581d42684d3d5a}$$

---

## 3. Section B: Historical Cohort Provenance & Cryptographic Audit

### 3.1 Forensic Comparison of Cohort Populations
An audit of raw files was conducted against the authoritative archive `fixtures/Incident json.zip`. The archive contains exactly **22 files**:
- 2 Detection Rule documentation files (`Rule_info.txt`, `Rule info.txt`)
- Exactly **20 authentic FortiSIEM incident JSON records**:
  - 10 under `Crowdstrike Suspicious Activity/`
  - 10 under `Prisma SASE Suspicious File Threat Detection/`

When cross-referencing published reports from AIS 2.4a, AIS 2.4b, and AIS 2.4c:
- **AIS 2.4a:** Evaluated all 20 authentic incidents from `Incident json.zip` (100% genuine).
- **AIS 2.4b:** Introduced 14 synthetic placeholder incident IDs (`132439101`, `132440012`, `132501234`, etc.) generated in scratch reporting scripts.
- **AIS 2.4c:** Attempted to purge synthetic IDs, but authoring errors introduced 12 substituted/mutated incident IDs:
  - 5 CrowdStrike IDs were substituted (`132440003`, `132442470`, `132443093`, `132444005`, `132445657` in place of `132461368`, `132472498`, `132474210`, `132501348`, `132502453`).
  - 7 Prisma SASE IDs were mutated (typographical prefix error `132499145` instead of `132599145`, etc., and fabricated IDs `132500001`–`132503334`).

### 3.2 Explanation of the 8-of-20 Shared Incident IDs
This authoring error explains why AIS 2.4a and AIS 2.4c shared only 8 incident IDs:
- **Matching CrowdStrike IDs (5):** `132438483`, `132439932`, `132441815`, `132461358`, `132527297`
- **Matching Prisma SASE IDs (3):** `132499009`, `132499023`, `132499745`
- **Total Shared IDs:** $5 + 3 = \mathbf{8\text{ incident IDs}}$.

**Resolution:** The 12 erroneous IDs in AIS 2.4c are formally repudiated. The authoritative 20-incident population is restored directly from `fixtures/Incident json.zip` matching AIS 2.4a.

### 3.3 Recomputed Master Cryptographic & Telemetry Census (All 20 Incidents)

Below is the definitive, independently recomputed ledger of all 20 historical FortiSIEM incident records:

| Incident ID | Detection Rule Name & ID | SHA-256 Digest of Original JSON Payload | Raw Events | Original Resolution | Original Cleared Reason / Notes | Analyst / Cleared User | Certified Ground Truth | Ground Truth Basis |
|---|---|---|:---:|---|---|---|:---:|---|
| **132438483** | CrowdStrike: Suspicious Activity (`PH_RULE_CS_SUSPICIOUS_ACTIVITY`) | `d35c42f7d5931fa412d08bdebc2bc665fc1125d482689d5b325b633938570754` | 25 | False Positive | `kill process is true` (Comments: "Resolution set by Machine Learning") | *(None)* | **UNVERIFIED** | Automated ML label override; no affirmative benign evidence. |
| **132439932** | CrowdStrike: Suspicious Activity (`PH_RULE_CS_SUSPICIOUS_ACTIVITY`) | `224cf263774f7444d863eab155a99b7e3c7578e4464453b389c8c2079e134544` | 8 | False Positive | `kill process is true` | *(None)* | **UNVERIFIED** | Containment note only; no forensic attack/benign proof. |
| **132441815** | CrowdStrike: Suspicious Activity (`PH_RULE_CS_SUSPICIOUS_ACTIVITY`) | `19417728832489479058a942f3b71e4a8c71cc977e30a911d70dbafdcb47c764` | 16 | False Positive | `proccess is kiled` | *(None)* | **UNVERIFIED** | Containment note only; no forensic attack/benign proof. |
| **132461358** | CrowdStrike: Suspicious Activity (`PH_RULE_CS_SUSPICIOUS_ACTIVITY`) | `e6048c6f15f7bb950ef61a2d7d8d7c4ede1da37934ec573689b0c3def7371b2d` | 34 | False Positive | `hash value is clean` (Comments: "Resolution set by Machine Learning") | `shivamw` | **UNVERIFIED** | Machine Learning label override; lacks human adjudication notes. |
| **132461368** | CrowdStrike: Suspicious Activity (`PH_RULE_CS_SUSPICIOUS_ACTIVITY`) | `059dd10ae7e2c8d37de185b0cbedfd9795fca215ea2e1aa89ad2db7166586c73` | 19 | True Positive | `case raised and client are working on it` (Comments: "Resolution set by Machine Learning") | *(None)* | **UNVERIFIED** | Operational ticketing action; zero forensic compromise evidence. |
| **132472498** | CrowdStrike: Suspicious Activity (`PH_RULE_CS_SUSPICIOUS_ACTIVITY`) | `b12295c6d3cf6837720beeab280151bc6a7f3d241bc765f92b81617e30d496b6` | 30 | True Positive | `case raised and client are working on it` (Comments: "Resolution set by Machine Learning") | *(None)* | **UNVERIFIED** | Operational ticketing action; zero forensic compromise evidence. |
| **132474210** | CrowdStrike: Suspicious Activity (`PH_RULE_CS_SUSPICIOUS_ACTIVITY`) | `2e3bac14eeca1e6a57b097a2ea0f573d7c1769f7d9e1c2065e26e415fce18741` | 13 | False Positive | `legitimate activity, nothing suspicious observed.` | *(None)* | **VERIFIED_FP** | Certified human finding: legitimate activity confirmed on DC. |
| **132501348** | CrowdStrike: Suspicious Activity (`PH_RULE_CS_SUSPICIOUS_ACTIVITY`) | `0fcc5d60212c072f2beb88bade21b85be873ecfb01f025a7890064d108aba148` | 2 | True Positive | (Comments: "Resolution set by Machine Learning / Disable or Modify Tools") | `Yash Mungekar` | **UNVERIFIED** | ML-generated boilerplate; no forensic attack verification. |
| **132502453** | CrowdStrike: Suspicious Activity (`PH_RULE_CS_SUSPICIOUS_ACTIVITY`) | `e9881c404d63bab3ca93d81e0e2679b3379dbdb40b621bf63a96feb90df32880` | 24 | True Positive | `Informed to client, alert still generating` (Comments: "Resolution set by Machine Learning") | *(None)* | **UNVERIFIED** | Notification ticket only; alert persistence does not prove compromise. |
| **132527297** | CrowdStrike: Suspicious Activity (`PH_RULE_CS_SUSPICIOUS_ACTIVITY`) | `237a1245f83e5ee73ffefb8c8e24ace0ba2239e30e5082ba217008606edb54ee` | 2 | True Positive | `Endpoint security has blocked the ultraviewer.exe` (Comments: "Resolution set by Machine Learning") | *(None)* | **UNVERIFIED** | EDR blocking of dual-use software alone does not prove attack tradecraft. |
| **132499009** | Prisma SASE: Suspicious File (`PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE`) | `158717e0c0d4af0ac3210cf4aa9be1cd7358a0395eba89310babdf966509a95d` | 1 | False Positive | `No suspicious activity was identified during the analysis` | *(None)* | **VERIFIED_FP** | Certified human finding: SurveySensum feedback widget verified benign. |
| **132499023** | Prisma SASE: Suspicious File (`PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE`) | `7802374f11d163e0cd0324619a2b4046ff0dc08b32b185cc698dd72dce0c830f` | 1 | False Positive | `file does not found suspicious hence marking as fp` (Comments: "Resolution set by Machine Learning") | *(None)* | **UNVERIFIED** | Automated ML closure without human analyst provenance. |
| **132499745** | Prisma SASE: Suspicious File (`PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE`) | `52dc5477c0b58d04c5c367a53b5deee98d2ffed9d9089126cfda2a520ae02442` | 1 | False Positive | `file does not found suspicious hence marking as fp` (Comments: "Resolution set by Machine Learning") | *(None)* | **UNVERIFIED** | Automated ML closure without human analyst provenance. |
| **132578774** | Prisma SASE: Suspicious File (`PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE`) | `86a93736faec3e9db7410b0dc5b4e1d7108d718694d0f7cd61fd434ca3f4bcb0` | 1 | False Positive | `file observed is not suspicious` (Comments: "Resolution set by Machine Learning") | *(None)* | **UNVERIFIED** | Automated ML closure without human analyst provenance. |
| **132591888** | Prisma SASE: Suspicious File (`PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE`) | `709555d5633b425cb42bd9d705bdb4c765747774260e75a29723c9ea874c58e1` | 3 | False Positive | `file observed is not suspicious` (Comments: "Resolution set by Machine Learning") | *(None)* | **UNVERIFIED** | Automated ML closure without human analyst provenance. |
| **132595592** | Prisma SASE: Suspicious File (`PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE`) | `8ddcdb3471df3640aef3d575f4334a31ed64615950de1977cc9a35c7b380cb8f` | 1 | True Positive | `Mail has been sent already` (Comments: "Resolution set by Machine Learning") | *(None)* | **UNVERIFIED** | Notification email only; zero forensic evidence of malicious payload. |
| **132596403** | Prisma SASE: Suspicious File (`PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE`) | `ea718fcb802f1cfe59d84379f3d6f11d3751312dcf724fe3dfdf24fff9ba7a23` | 1 | True Positive | `Mail has been sent already` | *(None)* | **UNVERIFIED** | Notification email only; zero forensic evidence of malicious payload. |
| **132599145** | Prisma SASE: Suspicious File (`PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE`) | `4ce6aeaeba82dccd9c4a04ff6322e500d18ea506588cad20478d7d04591255f7` | 2 | True Positive | `Case has been raised for the similar incidents.` | *(None)* | **UNVERIFIED** | Ticketing action; `jquery.knob.js` open-source asset, no compromise. |
| **132599146** | Prisma SASE: Suspicious File (`PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE`) | `b4a6f242713d6a65e4773eb2ee2ee5f5eaee58063b2ca183a63ad39766d1b178` | 11 | True Positive | `Case has been raised for the similar incidents.` | *(None)* | **UNVERIFIED** | Ticketing action; Highcharts `exporting.js` asset, duplicate cluster. |
| **132599330** | Prisma SASE: Suspicious File (`PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE`) | `7ac1419a5bb5d0465519e0ba1b484e9b8a028571fdde71fab0ad32182d93d807` | 2 | True Positive | `Case has been raised for the similar incidents.` | *(None)* | **UNVERIFIED** | Ticketing action; Select2 dropdown JS asset, duplicate cluster. |

### 3.4 Telemetry Deduplication & Cluster Distribution
Computing cluster identity keys using deterministic telemetry hashing ($K_{\text{cluster}} = \text{SHA256}(\text{rule\_id} \mid \text{target} \mid \text{events\_count})$ reveals:
- **Total Unique Telemetry Clusters:** **15**
- **Total Duplicate Records:** **5**
  - **CrowdStrike:** 10 incidents fall into 10 distinct clusters (0 duplicates).
  - **Prisma SASE:** 10 incidents collapse into 5 clusters:
    - Cluster `3c65e7165bd72bd0` (Target `appName:web-browsing`, 1 event): 5 incidents (`132499023` [Primary], `132499745`, `132578774`, `132595592`, `132596403` [4 Duplicates]).
    - Cluster `4052a7e6ec6af5fd` (Target `appName:indonis`, 2 events): 2 incidents (`132599145` [Primary], `132599330` [1 Duplicate]).
    - Cluster `35bbeb588c5e2899` (Target `appName:indonis`, 11 events): 1 incident (`132599146`).
    - Cluster `76915202e84514d4` (Target `appName:surveysensum-base`, 1 event): 1 incident (`132499009`).
    - Cluster `0961ae145714e9db` (Target `appName:teamviewer-base`, 3 events): 1 incident (`132591888`).

**Root Cause of AIS 2.4c Cluster Discrepancy (16 vs 15):**  
In AIS 2.4c `02_BENCHMARK_COHORT_INTEGRITY.md`, the author copied the headline summary text ("15 unique clusters, 5 duplicates") from AIS 2.4a, but then constructed a manual table containing 10 CS clusters + 6 Prisma clusters = 16 clusters, with only 4 duplicates. This internal contradiction is now completely resolved: the authentic telemetry exhibits **15 unique clusters and 5 duplicates**.

### 3.5 Resolution of False Positive Classification for Incident `132499023`
In AIS 2.4c `FINAL_EVIDENCE.json` (line 170) and report `02_BENCHMARK_COHORT_INTEGRITY.md` (line 127), incident `132499023` was classified as `FALSE_POSITIVE` with the claim:
> *"PRISMA-CLUSTER-01 (Dup) | FALSE_POSITIVE | Identical hash/event to 132499009"*

**Forensic Audit Finding:**  
Direct payload inspection disproves this claim:
- `132499009`: Destination IP `108.159.61.117`, Destination Org `AMAZON-02`, Source User `emethre`, Application `surveysensum-base`, File `ss-widget.min.js`. Certified by human analyst finding: *"No suspicious activity was identified during the analysis"*.
- `132499023`: Destination IP `23.54.80.83`, Destination Org `AKAMAI-ASN1`, Source User `f8455`, Application `web-browsing`, File `clientlib-site.min.434edaea5200f31ba33eec0dd0b0cf19.js`. Resolution set by Machine Learning with empty analyst identity.

The two incidents share neither file hashes, destination IPs, usernames, applications, nor investigation findings. Promoting `132499023` to `FALSE_POSITIVE` was an invalid ground-truth substitution.  
**Adjudication:** Incident `132499023` is formally classified as **`UNVERIFIED`**. The authentic historical cohort contains exactly **2 Verified False Positives** (`132474210`, `132499009`) and **0 Verified True Positives**.

---

## 4. Section C: Token-Budget Invariant & Local Tokenizer Calibration

### 4.1 Root Cause of Over-Budget Dispatch under 4K Context
Under the 4,096 active context window, the architectural token budget invariant is:
$$\text{wire\_prompt\_tokens} + \text{reserved\_completion\_tokens} \le \text{active\_max\_model\_len}$$
With $\text{reserved\_completion\_tokens} = 768$ and $\text{active\_max\_model\_len} = 4{,}096$, the hard wire prompt ceiling is:
$$\text{Prompt Ceiling} = 4{,}096 - 768 = 3{,}328\text{ tokens}$$

In AIS 2.4c, CrowdStrike incidents were dispatched live to vLLM, consuming:
- `132438483`: Provider prompt tokens = **3,365** ($3{,}365 + 768 = 4{,}133 > 4{,}096$)
- `132527297`: Provider prompt tokens = **3,370** ($3{,}370 + 768 = 4{,}138 > 4{,}096$)

**Forensic Investigation:**  
Why did `TokenBudgetService` admit these incidents?
1. **Local Tokenizer Underestimation:** The local preflight estimation in `ModelTokenizerService._count_tokens_pure_python` estimated **3,307 tokens** for `132438483` and **3,310 tokens** for `132527297`. Because $3{,}307 \le 3{,}328$, preflight admission returned `can_proceed_to_inference = True`.
2. **Tokenizer Divergence:** vLLM's server-side Qwen2.5 BPE tokenizer counted 3,365 tokens (+58 tokens, a 1.75% divergence). This divergence occurred because Qwen's vocabulary tokenizes hex hashes, raw file paths, and JSON delimiters into more subwords than the pure-Python regex heuristic.
3. **Execution Invariant Violation:** Although vLLM did not abort because Qwen generated only 409 completion tokens ($3{,}365 + 409 = 3{,}774 \le 4{,}096$), the required 768 completion reserve was not physically available (only $4{,}096 - 3{,}365 = 731$ tokens remained).

### 4.2 Invariant Enforcement Specification
To prevent unbudgeted dispatch:
1. **Local Preflight Safety Headroom:** A minimum 5% safety margin ($1.05 \times \text{estimated\_prompt\_tokens}$) must be applied to local token estimates when comparing against prompt ceilings.
2. **Strict Invariant Equation:**
   $$\text{wire\_prompt\_tokens} + \text{reserved\_completion\_tokens} \le \text{active\_max\_model\_len}$$
3. **Context Ceiling Resolution:** Under 4,096 tokens, the prompt wire budget must be capped at 3,200 tokens. However, this causes all Prisma SASE incidents (3,701–3,747 tokens) to be halted. Expanding to an 8,192 context window expands the prompt budget to $8{,}192 - 768 = 7{,}424$ tokens, safely accommodating both rules with zero truncation.

---

## 5. Section D: Provenance Taxonomy Normalization

In AIS 2.4c `FINAL_EVIDENCE.json`, incidents halted by token budget exhaustion were tagged with:
`"execution_provenance": "TOKEN_BUDGET_GUARD"`
This created an ad-hoc 5th provenance category violating the standard 4-tier taxonomy.

### Authoritative 4-Tier Provenance Taxonomy

| Provenance Category | Definition | Allowed Field Values |
|---|---|---|
| **`LIVE_PROVIDER`** | Real GPU inference request dispatched and completed over network provider. | `prompt_tokens > 0`, `completion_tokens > 0`, `latency_ms > 0`, raw model response captured. |
| **`OFFLINE_SIMULATION`** | Deterministic local evaluation without network call (development/regression). | `prompt_tokens = null`, `completion_tokens = null`, `latency_ms = null`, `is_live_measurement = false`. |
| **`PREFLIGHT_ABSTENTION`** | Pre-inference guard halted execution before dispatch to prevent invalid token overflow or telemetry absence. | `prompt_tokens = null`, `completion_tokens = null`, `latency_ms = null`, reason code in `["TOKEN_BUDGET_GUARD", "CONTEXT_WINDOW_EXCEEDED", "CRITICAL_TELEMETRY_MISSING"]`. |
| **`PROVIDER_FAILURE`** | Network timeout, HTTP 5xx, or provider connection failure during live dispatch. | `prompt_tokens = null`, `finish_reason = "provider_error"`. |

**Remediation:** Token-budget halts are classified strictly as **`PREFLIGHT_ABSTENTION`** with `validation_status = "CONTEXT_WINDOW_EXCEEDED"` and `validation_reason_codes = ["TOKEN_BUDGET_GUARD", "CONTEXT_WINDOW_EXCEEDED"]`.

---

## 6. Stage 1 Hard Gate Disposition

| Verification Item | Requirement | Audit Result | Status |
|---|---|---|:---:|
| **Server 1 Deployed SHA** | Matches latest UPLA execution `upla-20261124-034752-53f0bc` | Verified exact SHA `c9a2a172658dbc6661a7fe117a581d42684d3d5a` | **PASS** |
| **Evidence Sequencing** | Evidence recorded post-deployment only | Verified policy in place; AIS 2.4c premature record reconciled | **PASS** |
| **Cohort Authenticity** | 20 authentic FortiSIEM records from `Incident json.zip` | 100% authentic records loaded; 12 mutated/synthetic IDs purged | **PASS** |
| **Cluster Manifest Truth** | Exactly 15 unique clusters and 5 duplicates | Telemetry keys verified; 16-cluster contradiction resolved | **PASS** |
| **Incident `132499023` Ground Truth** | Certified evidence grounding | Erroneous FP label revoked; correctly classified `UNVERIFIED` | **PASS** |
| **Token Budget Invariant** | Wire prompt + completion reserve $\le$ context capacity | Root cause traced to 1.75% tokenizer divergence; 5% buffer established | **PASS** |
| **Provenance Taxonomy** | Strict adherence to 4-tier model | Ad-hoc 5th tier eliminated; normalized to `PREFLIGHT_ABSTENTION` | **PASS** |

**Hard Gate Verdict:** **`PASS — PROCEED TO STAGE 2`**
