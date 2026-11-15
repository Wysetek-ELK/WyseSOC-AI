# VERDICTUM AI — VALIDATION V1.2.1
## 01. ROOT CAUSE AUDIT & INCONSISTENCY INVENTORY

**Document Version:** 1.0.0  
**Audit Target:** Verdictum AI Agent Intelligence Studio 2.0 & Production Readiness Engine  
**Status:** COMPLETE & VERIFIED  

---

### 1. Executive Summary

During the Validation V1.2 audit, several critical visual, semantic, and security governance inconsistencies were identified in Agent Intelligence Studio 2.0 and the AI Triage Workbench. These inconsistencies arose from the conflation of four distinct lifecycle dimensions:
1. **SIEM Deployment Status:** Whether a rule definition is active/enabled in the SIEM collector/FortiSIEM (`ACTIVE` vs `DISABLED`).
2. **AI Policy Approval Status:** Whether a candidate prompt template version has been formally reviewed and approved by an authorized administrator (`APPROVED` baseline vs `DRAFT` / `ARCHIVED`).
3. **Empirical Production Readiness:** Whether a prompt version meets all 8 automated quality gates, possesses >= 30 verified ground-truth analyst reviews, and satisfies Wilson confidence bounds (`ACTIVE` / `READY_FOR_APPROVAL` vs `VALIDATING` / `LEARNING` / `BLOCKED`).
4. **Runtime AI Execution Status:** Whether runtime LLM inference and automated decision dispatch are enabled for this rule (`Enabled` vs `Suspended` / `Blocked`).

This report provides the exhaustive root-cause investigation for Scenarios A, B, and C, RBAC UI button exposure, Blind Review data leakage, and statistical fabrication.

---

### 2. Detailed Root-Cause Analyses

#### Scenario A: Approved Version Displaying Blocked Readiness
- **Observed Behavior in V1.2:** Rule `PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT` (`40498741-ee6b-4a71-9101-0d6d3f77154c`), Version 1 displayed Version Status `APPROVED`, AI Execution `Enabled`, Readiness `BLOCKED`, and Quality Gates `4/8` (or `2/8` in actual DB evaluation).
- **Source Code Locations:**
  - `backend/app/services/production_readiness_service.py:300-330`
  - `frontend/src/app/agent-intelligence-studio/page.tsx:1890-1925`
  - `frontend/src/components/compact/AgentIntelligenceStudioOverview.tsx:470-515`
- **Root Cause:**
  Version 1 was approved historically as a baseline prompt template. However, upon re-evaluation against the rigorous G1–G8 validation engine and empirical review dataset, Gate 1 failed (`RULE_DEFINITION_INCOMPLETE`) and the rule possessed zero verified analyst reviews (`0/30`).
  The UI header evaluated `selectedVersion.status === "APPROVED"` and blindly displayed an `ACTIVE PRODUCTION` badge while the readiness card reported `BLOCKED`.
  Furthermore, the header conflated version approval with production readiness.
- **Remediation Implemented:**
  - Decoupled `activePolicyLabel` and `readiness_label`.
  - Added new state `APPROVED BASELINE (REVALIDATION REQUIRED)`: When a version is historically approved but current automated evaluation fails gates or lacks required empirical reviews, it is explicitly flagged for revalidation.
  - The Readiness stage explicitly explains that the prompt is a certified baseline requiring re-evaluation, not an unverified draft.

---

#### Scenario B: Candidate Version Incomplete Definition False Readiness
- **Observed Behavior in V1.2:** Version 3 (Draft) with missing definitions or failing hard quality gates displayed `READY_FOR_APPROVAL` in catalog summaries and allowed the `Approve` button to remain enabled.
- **Source Code Locations:**
  - `backend/app/api/prompts.py:68-85`
  - `backend/app/api/rules.py:112-140`
  - `backend/app/services/production_readiness_service.py:280-295`
- **Root Cause:**
  In `get_rule_prompts_summary` and `list_rules`, the backend calculated readiness status using a naive fallback: if `quality_score >= 80`, it assigned `READY_FOR_APPROVAL` without checking if hard gates G1–G8 passed or if analyst reviews were completed.
  In the frontend (`page.tsx`), the `Approve` button check inspected only `qualityAssessment?.approval_eligible` without verifying `passedGatesCount === 8` and `total_reviews >= 30`.
- **Remediation Implemented:**
  - Updated `production_readiness_service.py`: `approval_eligible` strictly requires `passed_gates_count == 8`, `rule_def_verified`, `evidence_contract_verified`, `policy_structural_passed`, `pilot_reviews_passed`, `sim_passed`, `fp_precision_passed`, `wilson_passed`, `tp_recall_passed`, and `len(blocking_issues) == 0`.
  - Updated catalog endpoints: A rule cannot be `READY_FOR_APPROVAL` if `passed_gates < 8` or `total_analyst_reviews < 30`. If below 30 reviews, it is classified as `LEARNING`. If gates are incomplete, it is classified as `VALIDATING` or `BLOCKED`.

---

#### Scenario C: Draft Version with Partial Gates Enabled Approve Button
- **Observed Behavior in V1.2:** A newly synthesized Draft version with 6/8 gates passed and 0 reviews displayed an active green `Approve` button in the UI.
- **Source Code Locations:**
  - `frontend/src/app/agent-intelligence-studio/page.tsx:2005-2025`
  - `frontend/src/components/compact/AgentIntelligenceStudioOverview.tsx:720-755`
  - `frontend/src/components/compact/AgentIntelligenceStudioOverview.tsx:853-863`
- **Root Cause:**
  1. The Overview quick-action toolbar and stage action buttons did not evaluate `total_reviews >= 30` or `passedGates === 8`.
  2. The action button in Stage 6 ("Production Approval") remained clickable with the label `"Approve Policy"` even when Stage 6 was in `BLOCKED` status.
  3. When navigating with `version_id`, `page.tsx` previously fell back to `rp.active_version_id`, ignoring the candidate version URL parameter.
- **Remediation Implemented:**
  - Button state in Overview and Stage 6 is hard-disabled (`disabled={actionLoading || !effectiveApprovalEligible || isViewer}`).
  - When blocked, the button explicitly renders `"Approval Blocked"` with a tooltip enumerating the incomplete checks (`"Approval blocked — X mandatory checks incomplete"`).
  - An inline `"View Requirements"` action button scrolls directly to `#guided-readiness-checklist`.

---

#### Scenario D: RBAC Viewer Privilege Leakage
- **Observed Behavior in V1.2:** A user logged in with the `Read-Only Viewer` role (`viewer`) could see active mutation buttons (`Synthesize Intelligent Draft`, `Validate Quality`, `Approve Policy`).
- **Source Code Locations:**
  - `frontend/src/app/agent-intelligence-studio/page.tsx:1930-1960`
  - `frontend/src/components/compact/AgentIntelligenceStudioOverview.tsx:700-750`
  - `backend/app/api/prompts.py:approve_prompt_version`
- **Root Cause:**
  The frontend checked `user.role === 'Administrator'` only for the final modal confirmation, but left top-level toolbar buttons active.
  Furthermore, `backend/app/api/prompts.py` endpoint `approve_prompt_version` allowed any authenticated user because it lacked `require_roles(["Administrator"])`.
- **Remediation Implemented:**
  - Added `require_roles(["Administrator"])` to `approve_prompt_version` in `backend/app/api/prompts.py`.
  - Added `isViewer` guards across all action buttons in `AgentIntelligenceStudioOverview.tsx` and `page.tsx`.
  - Buttons for viewers are disabled, with clear tooltips: `"Read-Only Viewer cannot synthesize drafts (requires SOC Analyst or Administrator role)"` and `"Read-Only Viewer cannot approve policies (requires Administrator role)"`.

---

#### Scenario E: Blind Review Ground-Truth Leakage Over API
- **Observed Behavior in V1.2:** While the frontend had a Blind Review toggle, the backend `/api/incidents` and `/api/incidents/{id}` endpoints returned `ai_verdict` in the JSON payload even when `blind_review=True` was active on the tenant/profile before an analyst reviewed the incident.
- **Source Code Locations:**
  - `backend/app/services/incident_service.py:165-220`
  - `backend/app/api/incidents.py:45-80`
- **Root Cause:**
  Masking was performed purely client-side via CSS or React state. An analyst inspecting browser DevTools Network tab could observe the unmasked `ai_verdict`, invalidating the double-blind testing protocol.
- **Remediation Implemented:**
  - Updated `IncidentService.list_incidents_with_rule_summary` and `IncidentService.get_incident`:
    When `blind_review=True` (or incident review is pending), the service checks if an `AnalystVerdictReview` has been submitted for this incident. If unreviewed, `ai_verdict` is sanitized to `None` on the wire before JSON serialization.

---

#### Scenario F: Fabricated Statistical Metrics with Zero Evaluated Samples
- **Observed Behavior in V1.2:** When a rule had `total_fp_pred == 0` or `total_analyst_reviews == 0`, the UI and API reported `FP Precision: 100.0%` and `Wilson Lower Bound: 96.0%`.
- **Source Code Locations:**
  - `backend/app/services/rule_learning_service.py:145-180`
- **Root Cause:**
  Default math assumed zero false positive errors equaled 100% precision with $n=0$:
  `precision = (tp / (tp + fp)) if (tp + fp) > 0 else 1.0` -> defaulted to `1.0`.
- **Remediation Implemented:**
  - Zero evaluated samples returns `None` (rendered as `N/A (Insufficient Data)`).
  - Wilson confidence lower bound returns `None` when sample size is insufficient.
  - Strict mathematical formula enforced: to achieve a 96% Wilson lower bound at $\alpha=0.05$ with zero errors, a minimum of $n=93$ consecutive error-free samples is mathematically required.
