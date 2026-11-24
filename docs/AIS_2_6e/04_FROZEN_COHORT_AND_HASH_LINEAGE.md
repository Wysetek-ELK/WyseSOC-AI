# AIS 2.6e — Workstream 3: Frozen Cohort and Cryptographic Hash Lineage Report

**Phase:** AIS 2.6e  
**Evaluated At:** 2026-11-24T17:15:00Z  
**Document Identity:** `docs/AIS_2_6e/04_FROZEN_COHORT_AND_HASH_LINEAGE.md`  
**Referenced Manifests:**  
- [FROZEN_COHORT_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/FROZEN_COHORT_MANIFEST.json)
- [EVIDENCE_HASH_LINEAGE.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/EVIDENCE_HASH_LINEAGE.json)
- [RULE_DEFINITION_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/RULE_DEFINITION_MANIFEST.json)
- [COHORT_DUPLICATION_AUDIT.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/COHORT_DUPLICATION_AUDIT.json)

---

## 1. Frozen Experimental Cohort Integrity

In accordance with Non-Negotiable Requirements 6 and 7:
> *"No silent modification or replacement of the frozen benchmark cohort. No exclusion of difficult incidents merely to improve accuracy."*

The frozen evaluation cohort consists of exactly 20 real FortiSIEM security incidents:
- **10 Incidents:** `PH_RULE_CS_SUSPICIOUS_ACTIVITY` (CrowdStrike: Suspicious Activity)
- **10 Incidents:** `PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE` (Prisma SASE: Suspicious File Threat Detection)

### Customer Distribution & Scope
- **Forbes Marshall:** 10 incidents (all Prisma SASE)
- **Tosoh:** 8 incidents (CrowdStrike)
- **WSTPL:** 2 incidents (CrowdStrike)

---

## 2. Canonical Evidence Lineage Architecture

To guarantee absolute scientific reproducibility and eliminate historical serialization ambiguities, an unbroken 8-step cryptographic lineage is maintained:

```text
Original Incident Record (SQLite DB UUID)
        |
        v [Step 1: Compact UTF-8 JSON Serialization]
Raw Evidence SHA-256 Digest
        |
        v [Step 2: EvidenceNormalizationService.normalize_incident_evidence]
Canonical Normalized Evidence SHA-256 Digest
        |
        v [Step 3: TokenBudgetService.budget_prompt]
Budgeted Evidence Package SHA-256 Digest
        +
Triggered Rule Definition SHA-256 Digest [Step 4]
        +
Compiled Policy SHA-256 Digest [Step 5]
        |
        v [Step 6: Chat Template Serialization]
Exact Serialized Model Request SHA-256 Digest
        |
        v [Step 7: vLLM Live Execution]
Actual Model Provider Response SHA-256 Digest (Staged for Live GPU)
        |
        v [Step 8: IndependentVerdictValidator]
Independent Validator Evaluation SHA-256 Digest (Staged for Mode C)
```

All JSON digests enforce the uniform standard: `json.dumps(obj, sort_keys=True, separators=(',', ':')).encode('utf-8')`.

---

## 3. Cohort Duplication and Correlated Cluster Audit

A critical finding from our deep database audit is that the frozen cohort contains significant correlated entity clustering:

### 3.1 CrowdStrike Cluster Analysis
- **9 of 10 CrowdStrike incidents** (`132438483`, `132439932`, `132441815`, `132461358`, `132461368`, `132472498`, `132474210`, `132502453`, `132527297`) involve the identical binary:
  `"C:\Program Files (x86)\UltraViewer\UltraViewer_Service.exe"`
  flagged under IOC rule `Ultraviewer Block` for DNS/network connections to `update.ultraviewer.net`.
  - These events occurred across 5 distinct hosts (`DESKTOP-E0G2R49`, `TSI-IT-002-200`, `PC-TSI-DC`, `DESKTOP-KHU6454`, `TSI-IT-002-95`).
- **1 incident** (`132501348`) represents `MEGAsync.exe` (`C:\Users\admin\AppData\Local\MEGAsync\MEGAsync.exe`) on `DESKTOP-CQ4A60U`.

### 3.2 Prisma SASE Cluster Analysis
- **3 incidents** (`132599145`, `132599146`, `132599330`) originated from the same source IP (`172.25.14.157`) within a 45-second window on 2026-11-23, representing web script downloads (`jquery.knob.js`, `exporting.js`, `select2.min.js`).
- **2 incidents** (`132499009`, `132499745`) originated from host `172.25.14.80`.

### 3.3 Statistical Independence Limitation
In accordance with Non-Negotiable Requirement 23, these clustered incidents **must not be treated as independent identically distributed (i.i.d.) Bernoulli trials**. If the LLM has a systematic policy bias toward or against `UltraViewer_Service.exe`, that single bias will dictate 45% of the entire 20-incident benchmark. This limitation is formally accounted for in the evaluation metrics.
