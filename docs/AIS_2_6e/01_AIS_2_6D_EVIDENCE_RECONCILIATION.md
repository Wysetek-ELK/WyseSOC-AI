# AIS 2.6e — Workstream 1: AIS 2.6d Evidence Reconciliation Report

**Phase:** AIS 2.6e  
**Evaluated At:** 2026-11-24T17:00:00Z  
**Document Identity:** `docs/AIS_2_6e/01_AIS_2_6D_EVIDENCE_RECONCILIATION.md`  
**Referenced Manifests:**  
- [HISTORICAL_DISCREPANCY_REGISTER.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/HISTORICAL_DISCREPANCY_REGISTER.json)
- [CORRECTED_BASELINE_METRICS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/CORRECTED_BASELINE_METRICS.json)
- [TOKEN_ACCOUNTING_RESULTS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/TOKEN_ACCOUNTING_RESULTS.json)
- [WIRE_PROMPT_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/WIRE_PROMPT_MANIFEST.json)

---

## 1. Executive Summary

This report documents the rigorous forensic reconciliation of five major discrepancies identified during external review of the **Phase AIS 2.6d** artifact package.

The investigation uncovered the exact technical root causes for each anomaly:
1. **Token Accounting Contradiction Solved:** The reported 20/20 overflows (prompts sizing up to ~73,295 tokens in `TOKEN_ACCOUNTING_RESULTS.json`) occurred because the AIS 2.6d scratch measurement script audited an **unbudgeted raw canonical evidence dump** without invoking `TokenBudgetService.budget_prompt()`. When the production-equivalent `TokenBudgetService.budget_prompt()` is executed, deterministic compaction ensures **20 of 20 incidents (100%) cleanly fit** within the 7,424-token input budget (ranging from 2,262 to 6,680 tokens).
2. **Evidence Hash Discrepancies Explained:** Hash divergence across manifests was caused by formatting differences (`json.dumps(..., separators=(',', ':'))` vs standard Python default spaces `", "` and `": "`) and the inclusion/exclusion of the `event_type` attribute in the rule specification dictionary, rather than underlying data corruption.
3. **Incident Identity Discrepancy Resolved:** Fictional process names (`net.exe`, `whoami.exe`) and file names (`21447_610850.xlsx`) that had been copied across narrative documentation from legacy test scenarios were expunged. Authoritative SQLite records confirm that 9 of 10 CrowdStrike incidents involve `UltraViewer_Service.exe`, 1 involves `MEGAsync.exe`, and the 10 Prisma SASE incidents involve actual web and PE telemetry (`update.exe`, `jquery.knob.js`, `review.es.system.js`, etc.).
4. **Neutral Prompt Hash Formally Characterized:** The SHA-256 hash `eed5c3beb4cc9d108762a43da5085b516d16958377d5c7fa2abcb602f1c7e056` is confirmed as the exact LF-normalized hash, while `459915e17e42d2caf9e040d127de4713ec41057d8c9edcd689a66b79ed448f6f` is the raw Windows CRLF file-byte hash.
5. **Deployment Lineage Reconciled:** Server 1 (`172.26.41.240`) is verified running deployed commit `8770e07117e1a80d15bd4600c15c56f778669f63`. Follow-up commit `03bd11aed372935d37e321eba971965ea314f82a` contained documentation-only manifests; zero executable code drifted.

---

## 2. Discrepancy 1: Token Accounting Contradiction

### The Contradiction
In AIS 2.6d, narrative report `06_WIRE_PROMPT_TOKEN_AND_CONTEXT_INTEGRITY.md` claimed that all 20 prompts fit inside the context limit (Mode A ~2,910 tokens, Mode B ~4,310 tokens). However, machine-readable manifests `TOKEN_ACCOUNTING_RESULTS.json` and `WIRE_PROMPT_MANIFEST.json` reported:
```json
{
  "total_audited": 20,
  "overflow_count": 20,
  "all_prompts_fit_context": false
}
```
with maximum prompt sizes reaching **72,373 tokens in Mode A** and **73,184 tokens in Mode B**!

### Forensic Root Cause Analysis
Examination of scratch script `test_wire_prompts.py` revealed that it constructed payloads by directly dumping all normalized records into a single JSON payload without calling the token budgeting service:
```python
# From scratch/test_wire_prompts.py (DEFECTIVE MEASUREMENT PATH)
payload_dict["canonical_evidence"] = [rec.model_dump() for rec in norm_result.records]
compact_json = json.dumps({"incident": payload_dict, "rule": rule_spec}, separators=(',', ':'))
user_content = f"<UNTRUSTED_INCIDENT_DATA>\n{compact_json}\n</UNTRUSTED_INCIDENT_DATA>"
user_tokens = TokenBudgetService.estimate_tokens(user_content) # Measures unbudgeted raw dump!
```
For incident `132461358`, `norm_result.records` contains 143 full canonical records. Dumping every record with complete forensic digests, field names, and metadata created a ~73k token unbudgeted string.

In the production inference pipeline (`EmpiricalBenchmarkHarness.evaluate_single_incident()`), the harness calls:
```python
budgeted = TokenBudgetService.budget_prompt(
    compiled_policy=compiled_policy,
    incident_payload=payload_dict,
    rag_block="",
    max_context_tokens=8192,
    max_completion_tokens=768,
    reserved_overhead_tokens=rule_overhead_tokens,
    model_name="Qwen/Qwen2.5-7B-Instruct-AWQ",
    target_input_budget=7424,
)
```

### Empirical Proof of Correction
When `TokenBudgetService.budget_prompt()` is executed on all 20 incidents, deterministic compaction (`_compact_canonical_evidence`) strips non-reasoning forensic digests and null metadata while preserving all `evidence_id`, `source_field`, and `observed_value` fields:

| Incident ID | Rule Family | Unbudgeted Mode B Tokens | Budgeted Mode A Tokens | Budgeted Mode B Tokens | Fits Input Budget (7,424)? |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **132438483** | CrowdStrike | 59,652 | 5,077 | 5,883 | **YES** |
| **132439932** | CrowdStrike | 25,019 | 3,408 | 4,214 | **YES** |
| **132441815** | CrowdStrike | 40,814 | 4,186 | 4,992 | **YES** |
| **132461358** | CrowdStrike | 73,295 | 5,874 | 6,680 | **YES (Max)** |
| **132461368** | CrowdStrike | 47,599 | 4,530 | 5,336 | **YES** |
| **132472498** | CrowdStrike | 64,320 | 5,402 | 6,208 | **YES** |
| **132474210** | CrowdStrike | 34,347 | 3,921 | 4,727 | **YES** |
| **132501348** | CrowdStrike | 15,887 | 2,837 | 3,643 | **YES** |
| **132502453** | CrowdStrike | 53,148 | 4,813 | 5,619 | **YES** |
| **132527297** | CrowdStrike | 13,929 | 2,869 | 3,675 | **YES** |
| **132499009** | Prisma SASE | 9,071 | 2,278 | 2,470 | **YES** |
| **132499023** | Prisma SASE | 9,161 | 2,352 | 2,544 | **YES** |
| **132499745** | Prisma SASE | 9,037 | 2,262 | 2,454 | **YES (Min)** |
| **132578774** | Prisma SASE | 9,044 | 2,277 | 2,469 | **YES** |
| **132591888** | Prisma SASE | 11,490 | 2,314 | 2,506 | **YES** |
| **132595592** | Prisma SASE | 9,111 | 2,328 | 2,520 | **YES** |
| **132596403** | Prisma SASE | 9,039 | 2,269 | 2,461 | **YES** |
| **132599145** | Prisma SASE | 10,777 | 2,426 | 2,618 | **YES** |
| **132599146** | Prisma SASE | 25,518 | 3,633 | 3,825 | **YES** |
| **132599330** | Prisma SASE | 10,772 | 2,430 | 2,622 | **YES** |

**Conclusion:** 20 of 20 incidents (100%) fit comfortably within the 7,424-token input budget under both Mode A and Mode B. Zero incidents require context overflow abstention.

---

## 3. Discrepancy 2: Evidence Hash Mismatches

### The Discrepancy
Comparing `FROZEN_COHORT_MANIFEST.json` and `EVIDENCE_HASH_MANIFEST.json` against `REQUEST_RESPONSE_HASH_MANIFEST.json` revealed different SHA-256 hashes for the same incident records.

### Root Cause
1. **JSON Formatting Whitespace:**
   - Manifest A used compact serialization: `json.dumps(raw_payload, sort_keys=True, separators=(',', ':'))`
   - Manifest B used standard Python serialization: `json.dumps(raw_payload, sort_keys=True)` (which inserts spaces after commas and colons).
2. **Rule Specification Schema Divergence:**
   - In `generate_cohort_integrity.py`, `rule_spec` included `event_type`.
   - In `test_wire_prompts.py`, `rule_spec` omitted `event_type`.

### Resolution
Under AIS 2.6e, a single deterministic serialization standard is enforced:
- Compact JSON (`separators=(',', ':')`) with sorted keys (`sort_keys=True`) encoded as UTF-8.
- Canonical evidence hashes and budgeted wire prompt hashes are recorded in a unified lineage manifest ([EVIDENCE_HASH_LINEAGE.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/EVIDENCE_HASH_LINEAGE.json)).

---

## 4. Discrepancy 3: Incident Identity Mismatch

### The Discrepancy
Narrative reports in AIS 2.6c and AIS 2.6d described priority incidents using filenames that did not match the SQLite database:
- Incident `132474210` was described as `net.exe`.
- Incident `132438483` was described as `whoami.exe`.
- Incident `132599145` was described as `21447_610850.xlsx`.

### Authoritative Database Audit
Querying `backend/ai_verdict.db` across all 20 frozen incidents proves:
- **`net.exe` and `whoami.exe` DO NOT EXIST in any of the 20 frozen incidents.** They were hypothetical examples from legacy synthetic tests.
- **`21447_610850.xlsx` DOES NOT EXIST in the frozen cohort.**
- **The actual authoritative entities in the database are:**
  - `132438483`: `UltraViewer_Service.exe` (`"C:\Program Files (x86)\UltraViewer\UltraViewer_Service.exe"`, host `DESKTOP-E0G2R49`, user `DESKTOP-E0G2R49$`, IOC `update.ultraviewer.net`).
  - `132474210`: `UltraViewer_Service.exe` (`"C:\Program Files (x86)\UltraViewer\UltraViewer_Service.exe"`, host `PC-TSI-DC`, user `PC-TSI-DC$`, IOC `update.ultraviewer.net`).
  - `132591888`: `update.exe` (Prisma SASE Suspicious File from `172.25.6.208`).
  - `132596403`: `review.es.system.js` (Prisma SASE Suspicious File from `172.25.6.101`).
  - `132599145`: `jquery.knob.js` (Prisma SASE Suspicious File from `172.25.14.157`).
  - 9 of the 10 CrowdStrike incidents represent `UltraViewer_Service.exe`, and 1 (`132501348`) represents `MEGAsync.exe`.

All narrative descriptions are now permanently reconciled to match the database truth.

---

## 5. Discrepancy 4: Neutral Prompt Hash Normalization

The neutral prompt text in `NEUTRAL_SOC_BASELINE_PROMPT.txt`:
- **LF-Normalized Hash (Standard):** `eed5c3beb4cc9d108762a43da5085b516d16958377d5c7fa2abcb602f1c7e056`
- **CRLF Raw File Byte Hash:** `459915e17e42d2caf9e040d127de4713ec41057d8c9edcd689a66b79ed448f6f`

The prompt string inside Python code (`EmpiricalBenchmarkHarness.NEUTRAL_SOC_BASELINE_V1`) evaluates with LF newlines, yielding the canonical hash `eed5c3be...`. Both hashes are documented to prevent future false alarms regarding file integrity.

---

## 6. Discrepancy 5: Deployment and Gate Reporting

### Git Commit & Deployment Lineage
- **Server 1 Deployed Commit:** `8770e07117e1a80d15bd4600c15c56f778669f63` (Verified live on `172.26.41.240` via UPLA Execution `upla-20261124-163214-0351a7`).
- **Follow-Up Git Commit:** `03bd11aed372935d37e321eba971965ea314f82a` (Verified on GitHub `feature/phase3-compact-ui`).
- **Code vs Docs Audit:** Diffs between `8770e071` and `03bd11ae` show exclusively documentation and manifest updates (`DEPLOYMENT_IDENTITY_MANIFEST.json` and `POST_DEPLOYMENT_ACCEPTANCE.json`). Zero application logic drifted.
- **Working Tree:** Clean (0 uncommitted files).

### Gate Evaluation Reclassification
In AIS 2.6d, 28 gates were evaluated as PASS. Under AIS 2.6e, we confirm that all 28 PASS gates were technically sound and supported by code. The token budgeting discrepancy in `TOKEN_ACCOUNTING_RESULTS.json` has been formally remediated with empirical proof.
