# AIS 3.1 — Workstream 2: Human Ground Truth Reconciliation

**Cohort:** `AIS_3_0_INDEPENDENT_HOLDOUT_100`  
**Machine-Readable Evidence:** `docs/AIS_3_1/HUMAN_REVIEW_RECONCILIATION.json`  
**Data Mutation Guarantee:** Zero human reviews deleted, unlocked, modified, or re-requested (`100/100` preserved intact).

---

## 1. Cohort Population & Review Verification

| Metric | Verified Value | Audit Source |
|---|---:|---|
| Unique Cohort Members | **100** | Server 1 PostgreSQL (`benchmark_cohort_items`) |
| Unique Internal Incident UUIDs (`incident_db_id`) | **100** | Read-only backend audit |
| Unique FortiSIEM Incident IDs | **100** | Read-only backend audit |
| Overlap with `AIS_2_6E_FROZEN_20` | **0** | Cross-cohort set intersection |
| Locked Benchmark Certification Reviews | **100 / 100** (`is_locked=True`) | `analyst_verdict_reviews` (`BENCHMARK_CERTIFICATION`) |
| Distinct Reviewers per Incident | **1** on all 100 (`admin`) | Reviewer grouping check |
| Review Revisions (`revisions_count`) | **0** on all 100 | Audit trail check |
| Conflicts | **0** | Certification state check |
| Certification State | **100** `GT2_SINGLE_REVIEW`, **0** `GT3_CERTIFIED` | Cohort status check |
| Review Submission Window (UTC) | `2026-11-27T03:27:39Z` to `2026-11-28T09:00:56Z` | Timestamp audit |
| Blind Review Enforcement (`BLIND_ENFORCED`) | **100 / 100** | Server-side queue & detail API + blind attestations |
| Blind Attestations Verified (`evidence_reviewed`, `no_ai_or_historical_influence`, `independent_judgment`) | **100 / 100** all `True` | Review record audit |

---

## 2. Restricted Human Ground Truth Distribution

> [!NOTE]
> Ground truth verdict counts below are restricted to evaluation governance and **never** exposed to any LLM inference component, wire prompt, or `LearningRecord`.

| Locked Human Verdict | Count | Percentage |
|---|---:|---:|
| `FALSE_POSITIVE` | 80 | 80.0% |
| `TRUE_POSITIVE` | 18 | 18.0% |
| `INCONCLUSIVE` | 2 (`6552`, `15811`) | 2.0% |
| **Total** | **100** | **100.0%** |

- **Class Imbalance Warning:** With 80.0% `FALSE_POSITIVE` and 18.0% `TRUE_POSITIVE` (2.0% `INCONCLUSIVE`), an `ALWAYS_FALSE_POSITIVE` trivial baseline scores 80% accuracy while achieving **0% TRUE_POSITIVE recall**. Evaluation therefore emphasizes Recall, Precision, F1, Balanced Accuracy, and False Negative Rate alongside Conclusive Accuracy.

---

## 3. Vendor, Customer & Evidence Integrity Breakdown

- **Resolved Vendor Distribution** (after fixing hardcoded `"Prisma SASE"` fallback bug):
  - `FortiSIEM`: 89
  - `IPS / Firewall`: 4
  - `MISP Threat Intel`: 3
  - `FortiSIEM System`: 3
  - `FortiGate`: 1
- **Customer Distribution:** `Demo-SOC`: 59, `GDC_NOC`: 39, `Super`: 2.
- **Evidence Availability:** `100/100` incidents have non-empty raw logs (`1` to `100` raw events per incident) and canonical normalized evidence (`>= 1` `CanonicalEvidenceRecord`).
- **Cross-Rule Duplicate Raw Logs:** `3` pairs (`6` incidents total) share identical `raw_log_sha256` across `PH_RULE_LARGE_OUTBOUND_XFER` & `PH_RULE_LARGE_OUTBOUND_XFER_OUTSIDE_COUNTRY`:
  1. `('4871', '4872')` (`GDC_NOC`)
  2. `('12116', '12117')` (`Demo-SOC`)
  3. `('12542', '12543')` (`GDC_NOC`)
  - Because triggered detection rules differ between paired rules (`OUTSIDE_COUNTRY` vs general outbound), canonical evidence hashes (`canonical_evidence_sha256`) have **0** duplicates. Discrepancies between clustered and unclustered error rates are tracked in Workstream 12.

---

## 4. Reconciled Queue Table Reference

The complete per-incident reconciliation table containing internal incident ID, FortiSIEM ID, rule ID, resolved vendor, customer, human review status, certification state, reviewer count, evidence integrity state, exposure state, and benchmark eligibility for all 100 cohort members is stored in [HUMAN_REVIEW_RECONCILIATION.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_3_1/HUMAN_REVIEW_RECONCILIATION.json).
