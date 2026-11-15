# VERDICTUM AI — VALIDATION V1.2.2
## 04. HEAVY TCP HOST SCAN VERSION CONSISTENCY REPORT

**Document Version:** 1.0.0  
**Rule Target:** Heavy TCP Host Scan On Fixed Port (`40498741-ee6b-4a71-9101-0d6d3f77154c`)  
**Status:** FULLY RECONCILED & AUDITED  

---

### 1. Version Comparison Matrix

| Attribute | Version 1 (Historical Baseline) | Version 3 (Candidate Draft) |
| :--- | :--- | :--- |
| **Version ID** | `8a460ab8-5f06-4a90-b2d4-db958199d644` | `ec0cc351-8dd1-4026-9dc3-586387bb324c` |
| **Version Status** | `APPROVED` (Historical Certification) | `DRAFT` (Synthesized Candidate) |
| **Quality Gates** | 2 / 8 Passed (Legacy format) | 6 / 8 Passed (G1, G8 failing) |
| **Authoritative Score** | 52.0 / 100 | **77.0 / 100** (Authoritative Assessment) |
| **Verified Analyst Reviews** | 0 / 30 (0 / 100 Production Target) | 0 / 30 (0 / 100 Production Target) |
| **Stage 1 (Define Detection)** | `BLOCKED` (Threshold unverified) | `BLOCKED` (Authoritative SIEM conditions unverified) |
| **Stage 2 (Verify Evidence)** | `BLOCKED` (Upstream Stage 1 unverified) | `BLOCKED` (Upstream Stage 1 blocked; Contract unverified) |
| **Stage 3 (Validate Policy)** | `NEEDS_ACTION` (Score 52 < 70) | `BLOCKED` (Score 77 >= 70, but 1 blocking issue) |
| **Stage 6 (Production Approval)** | `BLOCKED` (Revalidation Required) | `BLOCKED` (Ineligible Draft) |
| **AI Execution Status** | `Suspended` | `Suspended` |
| **Current Readiness** | `APPROVED BASELINE` (Revalidation Required) | `BLOCKED / INCOMPLETE` |
| **Approval Button State** | Disabled (`Approval Blocked`) | Disabled (`Approval Blocked`) |

---

### 2. Resolution of Checklist Contradictions

#### Contradiction 1: False "COMPLETED" Evidence Stage
- **Previous Defect:** Stage 2 showed `COMPLETED` based merely on checking that 8 core fields were defined in the candidate template.
- **Correction:** Stage 2 verification now enforces that Stage 1 upstream detection logic is verified and the contract status is `VERIFIED`. Because Stage 1 has unverified correlation thresholds, Stage 2 correctly evaluates to `BLOCKED`.

#### Contradiction 2: Text Mismatch on Quality Score
- **Previous Defect:** The UI displayed `"Quality score (77.0/100) below 70 requirement; 1 blocking findings detected"`.
- **Correction:** Updated string template to:
  `"Quality score (77.0/100) meets score threshold, but 1 blocking finding(s) must be resolved: RULE_DEFINITION_INCOMPLETE: Rule lacks authoritative SIEM detection logic."`

#### Contradiction 3: Score Value Reconciliation
- **Resolution:** The authoritative dynamic quality score is **77.0**. Stored database value 88.0 was an unverified placeholder draft score from initial synthesis.

#### Contradiction 4: Smart Next Action Priority
- **Resolution:** The Smart Next Action Card now points to the root blocker:
  - **Title:** `Verify FortiSIEM Detection Semantics`
  - **Target Tab:** `Advanced Configuration -> SIEM Semantics & Archetype`
  - **Impact:** Unblocks Stage 1, which subsequently unblocks Stage 2 Evidence Verification.
