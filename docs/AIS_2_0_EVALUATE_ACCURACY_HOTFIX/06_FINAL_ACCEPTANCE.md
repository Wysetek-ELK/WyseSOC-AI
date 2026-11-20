# AIS 2.0 Evaluate Accuracy & Empirical Readiness — Final Acceptance Sign-Off

**System**: Verdictum AI — Agent Intelligence Studio 2.0  
**Target Rule**: `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`)  
**Rule UUID**: `40498741-ee6b-4a71-9101-0d6d3f77154c`  
**Active Baseline**: `v7 APPROVED` (`d79fb576-c6b9-4f63-9167-3c7a2419b70a`)  
**Candidate Revision**: `v8 DRAFT` (`20d4f788-85a5-437d-afbe-fe7fd80abca1`)  
**Acceptance Sign-Off Date**: November 20, 2026  

---

## 1. Primary Objectives Verification Matrix

| Acceptance Item | Required Standard | Status | Verified Evidence |
|:---|:---|:---:|:---|
| **Evaluate Accuracy Button** | Must invoke backend evaluation, show spinner, and update metrics | **PASSED** | Wires to `POST /api/learning/rules/{rule_id}/evaluate-accuracy` with toast feedback |
| **Why 31 Reviews Yield 0 Accuracy** | Factual mathematical reconciliation of database ground truth | **PASSED** | 31 FP reviews: 16 AI abstentions, 15 initial benchmarks, 0 decisive predictions; Selective Accuracy denominator is 0 |
| **Class Balance Governance** | Require $\ge 10$ TP and $\ge 10$ FP for Supervised Pilot baseline | **PASSED** | Deficit of 10 TP detected; Next Action directs analyst to collect True Positive cases |
| **No Metric Fabrication** | Strict suppression of false 100% or empty charts | **PASSED** | Metrics remain strictly `N/A` with clear diagnostic explanations |
| **Zero Version Invalidation** | Candidate v8 simulation must not alter active v7 production profile | **PASSED** | Active version v7 remains immutable in APPROVED state; v8 remains candidate DRAFT |
| **Zero Incident Deletion** | No database incidents, investigations, or reviews modified/deleted | **PASSED** | Verified: all 31 reviews intact in PostgreSQL |
| **Frontend Test Suite** | All frontend regression tests must pass | **PASSED** | 16 test suites, 72 tests passed |
| **Production Build** | Next.js Turbopack production compilation must succeed | **PASSED** | Exit code 0, 32/32 routes optimized |

---

## 2. Invariants Certified

1. **Deterministic Double-Blind Isolation**: Analyst verdicts remain strictly masked until submission; AI determinations are revealed only after submission.
2. **Selective Accuracy Mathematical Soundness**: Under no circumstances does the system fabricate 100% or 0% accuracy when decisive sample size is 0.
3. **Class-Balanced Empirical Baselines**: Analysts are prevented from promoting one-sided ground truth (e.g., 31 FP and 0 TP) to production.
4. **Local AWQ Offline Inference Integrity**: Local AWQ temperature is strictly preserved at `0.01` and AWQ quantization weights remain untouched. No silent GPU inference was triggered.
5. **UPLA Safe Delivery Pipeline**: Zero direct unapproved SSH mutations. All deployment steps flow through UPLA Human Gate 1 (GitHub sync) and Human Gate 2 (Remote deployment).
