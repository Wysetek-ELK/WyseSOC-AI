# Report 08 — SOC Analyst Pilot Readiness & Operational Handoff
**Verdictum AI — AIS 2.0 Pilot Cohort & Double-Blind Review Protocol**
**Date:** November 20, 2026  
**Status:** READY FOR OPERATIONAL PILOT  
**Target Rule:** Website Access Policy Violation (`7bd13e89-0828-48e6-8cf5-f3cbf12d438c`)  

---

## 1. Executive Summary

This document establishes the operational pilot protocol and SOC analyst workflow for **Website Access Policy Violation** (`7bd13e89-0828-48e6-8cf5-f3cbf12d438c`). Following the simplification of the Agent Intelligence Studio 2.0 and the mathematical reconciliation of G8 governance metrics, the rule is fully primed for **Tier 2: Supervised Pilot** ground-truth data collection.

Zero FortiSIEM production incidents have been modified or deleted. The local AWQ LLM configuration on Server 2 remains completely untouched.

---

## 2. Rule Governance & Baseline Profiles

| Attribute | Website Access Policy Violation | Heavy TCP Host Scan On Fixed Port |
|:---|:---|:---|
| **Rule ID** | `7bd13e89-0828-48e6-8cf5-f3cbf12d438c` | `40498741-ee6b-4a71-9101-0d6d3f77154c` |
| **Rule Code** | `PH_RULE_WEBSITE_ACCESS_POLICY_VIOLATION` | `PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT` |
| **Active Approved Version** | **v2** (`APPROVED`, Immutable Baseline) | **v7** (`APPROVED`, Immutable Baseline) |
| **Candidate Draft Version** | **v3** (`DRAFT`, Under Pilot Evaluation) | **v8** (`DRAFT`, Under Pilot Evaluation) |
| **Current Readiness Stage** | Tier 2: Supervised Pilot | Tier 2: Supervised Pilot |
| **Target Certification** | Tier 3: Production Eligible | Tier 3: Production Eligible |

---

## 3. Pilot Cohort Selection Criteria (Website Access Policy)

To achieve statistical validity under G8 Tier 2 requirements, the pilot cohort must adhere to the following selection criteria:

1. **Cohort Size:** 10 to 15 unreviewed real-world incidents from the incident pool.
2. **Category Diversity:**
   - At least 4 known benign corporate access events (e.g., standard internal portals, authorized cloud apps, CDN static assets).
   - At least 4 high-risk or suspicious category events (e.g., newly registered domains, adult content, gaming, uncategorized IP destinations).
   - At least 2 potential data exfiltration or paste-site access attempts.
3. **Temporal Distribution:** Incidents spanning multiple working shifts (Day, Swing, Night) to capture varied user browsing patterns.
4. **Data Isolation:** Incidents must be processed as read-only references; no underlying FortiSIEM logs may be altered.

---

## 4. Double-Blind Review Workflow for SOC Analysts

To eliminate confirmation bias and establish statistically rigorous ground truth, analysts must follow the Double-Blind review workflow:

```
[ Step 1: Select Incident ] ──> [ Step 2: Double-Blind Masking ON ] ──> [ Step 3: Independent Review ]
                                                                                   │
[ Step 5: Metric Update ] <── [ Step 4: Submit Verdict & Unmask ] <──────────────┘
```

### Detailed Operational Steps:
1. **Navigate to Workspace:** Access `/agent-intelligence-studio` and select **Website Access Policy Violation**.
2. **Verify Double-Blind Mode:** Ensure the **Blind Review** toggle in the top-right header is **ENABLED**. In this mode:
   - The AI verdict (`TRUE_POSITIVE` / `FALSE_POSITIVE`) is hidden.
   - The AI confidence score and reasoning are obscured.
   - Raw observables (Destination Domain, Category, User, Request URI, HTTP Status, Bytes Transferred) are displayed unskewed.
3. **Conduct Independent Triage:** Analyst evaluates evidence against organizational acceptable use policy and assigns a human disposition:
   - `AGREE_TP`: Legitimate policy violation requiring SOC escalation or user remediation.
   - `AGREE_FP`: Benign traffic, false alarm, authorized business exception, or legitimate redirect.
4. **Submit Feedback:** Click **Submit Verdict**. The system will unmask the AI prediction side-by-side with the analyst verdict:
   - *Agreement ($TP$ or $TN$):* Concordance is logged; telemetry feeds the confusion matrix.
   - *Disagreement ($FP$ False Alarm or $FN$ Missed TP):* System prompts analyst for a mandatory one-click root-cause tag (e.g., `Ambiguous Category`, `Business Exception`, `Misleading Host Header`, `Malicious Payload Hidden`).
5. **Real-time Recalculation:** The backend `RuleLearningService` dynamically recomputes overall accuracy, FP precision, specificity, Wilson lower bound, and G8 qualification progress.

---

## 5. Escalation & Quality Safety Thresholds

During the pilot phase, the system enforces the following safety controls:

- **Critical Missed TP Limit:** Exactly **0** allowed. If the candidate policy fails to identify a confirmed malicious or severe policy violation, candidate v3 is immediately blocked from promotion.
- **Minimum Pilot Accuracy:** Must maintain $\ge 90.0\%$ overall accuracy across the initial 30 pilot incidents.
- **Drift Detection:** If the ratio of False Alarms exceeds 10% in any rolling window of 10 reviews, an automated drift warning is logged to `PolicyDriftEvent` for administrative review.

---

## 6. Operational Handoff Checklist for SOC Lead

- [x] **Verified Active Version:** Confirm v2 is serving production inference.
- [x] **Verified Candidate Version:** Confirm v3 is designated as candidate draft for simulation.
- [x] **Verified Analyst Roles:** Ensure participating analysts have `ANALYST` or `ADMIN` roles in Verdictum AI.
- [x] **Verified Telemetry Logging:** Ensure audit records populate `analyst_reviews` and `actual_llm_prompt_captures`.
- [x] **Pilot Launch Date:** Immediate upon user acceptance.
