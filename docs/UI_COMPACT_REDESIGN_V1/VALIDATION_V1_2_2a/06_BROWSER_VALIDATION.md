# VERDICTUM AI — VALIDATION V1.2.2a
## 06. Browser Validation Suite & Screenshot Matrix

### 1. Test Methodology

The browser validation suite was executed using headless Google Chrome controlled directly via Chrome DevTools Protocol (CDP):
- **Base URL**: `http://127.0.0.1:3000`
- **Backend URL**: `http://127.0.0.1:8000`
- **Runner Script**: `scripts/run_v1_2_2a_validation.mjs`
- **Target Viewports**:
  1. `1440x900` (Standard Desktop / SOC Analyst Workstation)
  2. `1920x1080` (Full HD Enterprise Display)
- **Assertion Strategy**: Conjunction fail-fast DOM evaluations (all assertions must evaluate to `true` before capturing screenshots).

---

### 2. Validation Matrix (8 Scenarios × 2 Viewports = 16 Screenshots)

| # | Scenario ID | Role | Target Page / View | Viewport | Screenshot File | Size | DOM Assertions | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `SCN-V122A-01-BLIND-ON` | SOC Analyst (Analyst A) | `/ai-triage-workbench` | 1440x900 | `workbench_blind_review_on_1440x900.png` | 437 KB | `hasHiddenMask`, `hasBlindOnHeader`, `hasBlindActiveBanner` | **PASS** |
| 2 | `SCN-V122A-01-BLIND-ON` | SOC Analyst (Analyst A) | `/ai-triage-workbench` | 1920x1080 | `workbench_blind_review_on_1920x1080.png` | 542 KB | `hasHiddenMask`, `hasBlindOnHeader`, `hasBlindActiveBanner` | **PASS** |
| 3 | `SCN-V122A-02-BLIND-OFF` | SOC Analyst (Analyst A) | `/ai-triage-workbench` | 1440x900 | `workbench_blind_review_off_1440x900.png` | 436 KB | `hasBlindOffHeader`, `hasServerIsolationBanner`, `hasHiddenMask` | **PASS** |
| 4 | `SCN-V122A-02-BLIND-OFF` | SOC Analyst (Analyst A) | `/ai-triage-workbench` | 1920x1080 | `workbench_blind_review_off_1920x1080.png` | 539 KB | `hasBlindOffHeader`, `hasServerIsolationBanner`, `hasHiddenMask` | **PASS** |
| 5 | `SCN-V122A-03-ANALYST-A-POST-SUBMISSION` | SOC Analyst (Analyst A) | `/ai-triage-workbench?search=132438483` | 1440x900 | `workbench_analyst_a_post_submission_1440x900.png` | 621 KB | `hasRevealedBadge`, `hasIncident132` | **PASS** |
| 6 | `SCN-V122A-03-ANALYST-A-POST-SUBMISSION` | SOC Analyst (Analyst A) | `/ai-triage-workbench?search=132438483` | 1920x1080 | `workbench_analyst_a_post_submission_1920x1080.png` | 972 KB | `hasRevealedBadge`, `hasIncident132` | **PASS** |
| 7 | `SCN-V122A-04-ANALYST-B-PRE-SUBMISSION` | SOC Analyst (Analyst B) | `/ai-triage-workbench?search=132438483` | 1440x900 | `workbench_analyst_b_pre_submission_1440x900.png` | 623 KB | `hasHiddenMask`, `hasIncident132` | **PASS** |
| 8 | `SCN-V122A-04-ANALYST-B-PRE-SUBMISSION` | SOC Analyst (Analyst B) | `/ai-triage-workbench?search=132438483` | 1920x1080 | `workbench_analyst_b_pre_submission_1920x1080.png` | 974 KB | `hasHiddenMask`, `hasIncident132` | **PASS** |
| 9 | `SCN-V122A-05-VIEWER-RESTRICTED` | Read-Only Viewer | `/ai-triage-workbench` | 1440x900 | `workbench_viewer_restricted_1440x900.png` | 436 KB | `hasHiddenMask` | **PASS** |
| 10 | `SCN-V122A-05-VIEWER-RESTRICTED` | Read-Only Viewer | `/ai-triage-workbench` | 1920x1080 | `workbench_viewer_restricted_1920x1080.png` | 539 KB | `hasHiddenMask` | **PASS** |
| 11 | `SCN-V122A-06-HEAVY-TCP-V1-HISTORICAL` | Administrator | `/agent-intelligence-studio?rule_id=40498741...&version_id=8a460ab8...` | 1440x900 | `studio_heavy_tcp_v1_historical_1440x900.png` | 626 KB | `hasRuleHeader`, `hasSiemActive`, `hasPolicyV1Approved`, `hasAiExecutionSuspended`, `hasReadinessBlocked`, `hasScore54` | **PASS** |
| 12 | `SCN-V122A-06-HEAVY-TCP-V1-HISTORICAL` | Administrator | `/agent-intelligence-studio?rule_id=40498741...&version_id=8a460ab8...` | 1920x1080 | `studio_heavy_tcp_v1_historical_1920x1080.png` | 942 KB | `hasRuleHeader`, `hasSiemActive`, `hasPolicyV1Approved`, `hasAiExecutionSuspended`, `hasReadinessBlocked`, `hasScore54` | **PASS** |
| 13 | `SCN-V122A-07-HEAVY-TCP-V3-CANDIDATE` | Administrator | `/agent-intelligence-studio?rule_id=40498741...&version_id=ec0cc351...` | 1440x900 | `studio_heavy_tcp_v3_candidate_1440x900.png` | 630 KB | `hasStage1Blocked`, `hasStage2Blocked`, `hasScore77`, `hasNoContradictionText`, `hasSmartNextAction`, `isApproveDisabled` | **PASS** |
| 14 | `SCN-V122A-07-HEAVY-TCP-V3-CANDIDATE` | Administrator | `/agent-intelligence-studio?rule_id=40498741...&version_id=ec0cc351...` | 1920x1080 | `studio_heavy_tcp_v3_candidate_1920x1080.png` | 956 KB | `hasStage1Blocked`, `hasStage2Blocked`, `hasScore77`, `hasNoContradictionText`, `hasSmartNextAction`, `isApproveDisabled` | **PASS** |
| 15 | `SCN-V122A-08-AI-EXECUTION-RUNTIME-OFFLINE` | Administrator | `/agent-intelligence-studio?rule_id=40498741...&version_id=8a460ab8...` | 1440x900 | `studio_ai_execution_runtime_offline_1440x900.png` | 639 KB | `hasAiExecutionOffline`, `hasPolicyV1Approved` | **PASS** |
| 16 | `SCN-V122A-08-AI-EXECUTION-RUNTIME-OFFLINE` | Administrator | `/agent-intelligence-studio?rule_id=40498741...&version_id=8a460ab8...` | 1920x1080 | `studio_ai_execution_runtime_offline_1920x1080.png` | 939 KB | `hasAiExecutionOffline`, `hasPolicyV1Approved` | **PASS** |

---

### 3. Visual Layout & Compact Design Acceptance

1. **Zero Text Truncation / Overlap**: All rule headers, multi-metric badge bars, and checklist stages render cleanly with proportional flex wrapping.
2. **Cozy Density**: Tables in `/ai-triage-workbench` render 10+ incidents comfortably per screen height with subtle hover contrasts.
3. **Responsive Consistency**: Both 1440x900 and 1920x1080 viewports display symmetric layout structures without accidental overflow horizontal scrollbars.
4. **Theme Fidelity**: Verified under the Obsidian theme (`#030712` base, slate card surfaces, cyan/emerald accents).
