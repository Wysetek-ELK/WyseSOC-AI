# Report 03 — Analyst Verdict and Ground Truth Integrity
**Verdictum AI — AIS 2.0 Verdict Taxonomy & Ground Truth Governance**
**Date:** November 20, 2026  
**Status:** VERIFIED & COMPLIANT  
**Target Rule:** Website Access Policy Violation (`7bd13e89-0828-48e6-8cf5-f3cbf12d438c`)  

---

## 1. Executive Summary

This report defines the authoritative taxonomy of analyst determinations, distinguishes independent human verdicts from derived comparison classifications, and formalizes ground-truth ingestion rules. To maintain empirical validity under G8 governance, derived comparison labels (`AGREE_TP`, `AGREE_FP`, `MISSED_TP`, `FALSE_ALARM`) can never be submitted directly by an analyst; they must be computed deterministically by the system after an independent verdict and an eligible model prediction are recorded.

---

## 2. Authorized Analyst Verdict Choices

When reviewing an unreviewed incident in Tab 1 (Review Incidents), the analyst is provided with exactly three mutually exclusive choices:

| Outcome Value | UI Label | Operational Definition & Criteria | Ground Truth Status |
|:---|:---|:---|:---:|
| `TRUE_POSITIVE` | **True Positive (TP)** | The incident represents a confirmed, genuine policy violation or malicious access attempt that warrants SOC escalation, user remediation, or firewall rule adjustment. | `VERIFIED` |
| `FALSE_POSITIVE` | **False Positive (FP)** | The incident represents authorized business operations, benign background noise, miscategorized CDN/SaaS traffic, or an established corporate exception. | `VERIFIED` |
| `INSUFFICIENT_EVIDENCE` | **Insufficient Evidence** | Crucial security telemetry (raw HTTP headers, destination URI, web category, or user identity) is absent, preventing a definitive determination. | `INSUFFICIENT_EVIDENCE` |

### Explicit Rejection of Derived Outcomes
If an external API client or automated script attempts to submit a derived comparison label (such as `AGREE_TP`, `AGREE_FP`, `MISSED_TP`, or `FALSE_ALARM`), the FastAPI endpoint `POST /api/reviews/{incident_id}/submit` rejects the payload immediately with **HTTP 400 Bad Request**:
```
"'{v}' is a derived post-comparison outcome and cannot be submitted as an independent analyst verdict. Allowed values are strictly: TRUE_POSITIVE, FALSE_POSITIVE, INSUFFICIENT_EVIDENCE."
```

---

## 3. Review Submission Data Contract

### Required Fields:
1. `incident_id`: Unique FortiSIEM incident ID or database UUID.
2. `analyst_verdict`: Normalized enum string (`TRUE_POSITIVE`, `FALSE_POSITIVE`, `INSUFFICIENT_EVIDENCE`).
3. `reviewer_id`: Authenticated username extracted securely from session JWT token (`current_user.username`).
4. `customer`: Multi-tenant customer identifier bound to user scope.
5. `blind_mode_active`: Boolean verification that double-blind masking was active.

### Optional Supporting Fields:
1. `analyst_notes`: Detailed investigative findings and rationale.
2. `evidence_references`: Comma-separated or array of cited telemetry IDs (e.g. `["EV-01: DestinationDomain", "EV-03: ActionBlocked"]`).
3. `correction_reason`: Remediation tag if overturning an AI recommendation (e.g., `Corporate Exception`, `Benign CDN`, `Hidden Payload`).

---

## 4. Multi-Layered Ground Truth Architecture

The system strictly differentiates between five operational concepts:

```
┌───────────────────────────────────┐     ┌───────────────────────────────────┐
│ 1. Analyst Submitted Determination│     │ 3. Raw Local LLM Model Verdict    │
│    (TRUE_POSITIVE / FP / INSUFF)  │     │    (Qwen2.5-7B Raw JSON Output)   │
└─────────────────┬─────────────────┘     └─────────────────┬─────────────────┘
                  │                                         │
                  │                       ┌─────────────────┴─────────────────┐
                  │                       │ 4. Governed Effective Verdict     │
                  │                       │    (Policy Guardrails Applied)    │
                  │                       └─────────────────┬─────────────────┘
                  ▼                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. Derived Comparison Outcome (Computed Deterministically)                 │
│    • AGREEMENT_TP: Analyst TP + AI TP                                       │
│    • AGREEMENT_FP: Analyst FP + AI FP                                       │
│    • AI_FALSE_ALARM: Analyst FP + AI TP (AI false alert)                    │
│    • CRITICAL_MISSED_TP: Analyst TP + AI FP (AI missed violation)           │
│    • ANALYST_INSUFFICIENT_EVIDENCE: Analyst marked INSUFFICIENT_EVIDENCE     │
│    • ANALYST_ONLY_INITIAL_BENCHMARK: Stored AI verdict missing/unsimulated   │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. Verified Ground Truth Record (LearningRecord & RuleLearningProfile)     │
│    • Only VERIFIED TP and FP enter the certified ground-truth dataset       │
│    • INSUFFICIENT_EVIDENCE and DISPUTED records are safely isolated         │
│    • Feeds confusion matrix and G8 Tier-2 / Tier-3 Wilson lower bounds      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Prevention of Synthetic and Test Data Pollution

1. **Zero Synthetic Labels:** Production ground truth is generated exclusively by authenticated human analysts reviewing real FortiSIEM incidents.
2. **Idempotent Single-Counting:** If an analyst submits an identical review for the same incident, the service returns the existing record idempotently (`"is_duplicate": True`) without double-counting metrics in `RuleLearningProfile`.
3. **Dispute Isolation:** If two analysts submit conflicting verdicts for the same incident, the incident status transitions to `DISPUTED`, and neither verdict enters the verified learning dataset until resolved by a Senior Analyst through `/api/reviews/{review_id}/adjudicate`.
