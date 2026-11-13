# Verdictum AI — Version Comparison & Release History

**Document:** `28_VERSION_COMPARISON_AND_RELEASE_HISTORY.md`  
**Platform:** Verdictum AI / WyseSOC AI  
**Scope:** Detailed Feature & Schema Diff Between v1.0.0 Baseline and v1.1.0-rule-learning.1  
**Status:** COMPLETE & VERIFIED  

---

## 1. Version Comparison Matrix

| Capability / Feature | v1.0.0 (Baseline) | v1.1.0-rule-learning.1 (New Release) |
|---|---|---|
| **Incident Ingestion & Normalization** | FortiSIEM REST & Syslog KV Tokenizer | Identical (100% preserved) |
| **Evidence Validation & Contradiction Guard** | Deterministic Value Matcher & Loopback Guard | Identical (100% preserved) |
| **Agent Intelligence Studio 2.0** | 9-Section Policy Compiler & G1–G8 Gates | Extended with Tab 7: Rule Learning & Governance |
| **Rule Learning Profiles** | Not Available (Generic rule rows only) | `RuleLearningProfile` with per-tenant accuracy & lifecycle |
| **Analyst Feedback Workflow** | Single-reviewer with visible AI verdict | **Double-Blind Review** with post-submission reveal & comparison |
| **Ground Truth Store** | Unstructured `historical_ground_truth` | Immutable `AnalystVerdictReview` + L2 Adjudication |
| **Statistical Accuracy Gating** | Uncalibrated sample checks | **Wilson 95% Confidence Interval** with $\ge 96\%$ lower bound gate |
| **Simulation Lab Reporting** | Generic `INSUFFICIENT_DATA` error | **Granular 6-Stage Funnel Diagnostics** with exclusion breakdown |
| **Production Promotion Governance** | Manual unversioned state | **5-Stage State Machine** (`LEARNING` $\to$ `PROD`) with dual-key approval |
| **Automated FP Closure Safety** | Gated in PilotService | **12-Barrier Safety Interlock Checklist** with emergency kill-switch |
| **Database Schema** | 23 Operational Tables | 31 Tables (8 new non-destructive tables added) |
| **Automated Test Coverage** | 43 Unit Tests | **74 Automated Tests** (43 regression + 25 integrity + 6 learning) |

---

## 2. Backward Compatibility Verification

1. **Schema Non-Destructive:** The 8 new tables do not modify existing column types or constraints in `incidents`, `rules`, or `investigations`.
2. **API Non-Breaking:** All previous endpoints (`/api/v1/incidents`, `/api/v1/rules`, `/api/v1/verdict/evaluate`) retain identical request/response contracts.
3. **Database Dual-Compatibility:** Fully operational across both SQLite (development/testing) and PostgreSQL (production).

