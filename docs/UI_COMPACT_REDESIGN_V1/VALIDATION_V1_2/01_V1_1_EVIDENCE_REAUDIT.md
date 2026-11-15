# V1.1 Evidence Re-Audit & Defect Root-Cause Analysis

**Document:** `01_V1_1_EVIDENCE_REAUDIT.md`  
**Validation Phase:** Verdictum AI — Validation V1.2  
**Platform Version:** Agent Intelligence Studio 2.0 / VCDS 1.0  
**Evaluator:** Senior Full-Stack Engineer, SOC Platform QA Architect, Security Governance Auditor  
**Date:** November 15, 2026  

---

## 1. Executive Summary of V1.1 Evidence Re-Audit

The Validation V1.1 pass claimed to validate populated, authenticated UI behavior across Verdictum AI, producing 30 screenshots and an evidence summary. However, an independent technical re-audit of the V1.1 artifacts, test execution logs, and captured images revealed **two severe P1 integrity defects** that invalidated critical acceptance claims:

1. **Rule Detail Capture Bug (P1 Blocker):** Screenshots named `studio_rule_detail_approved.png` and `studio_rule_detail_blocked.png` actually captured the **Rules Directory catalog table** rather than the Rule Detail page. The test harness passed superficially because it merely checked for HTTP 200 without asserting DOM element presence (`[data-testid="compact-rule-detail"]`, primary tabs, or guided readiness stages).
2. **Production-Readiness Inconsistencies (P1 Blocker):** The V1.1 reports claimed that production readiness was fully governed by the 8-gate quality engine. In reality, rules were observed reporting `ACTIVE` readiness with only 7/8 gates passed (Scenario A), and rules with `UNKNOWN` archetype and incomplete semantics were reporting `ACTIVE` readiness (Scenario B).

This document presents the detailed root-cause analysis for both defects, explains how false confidence occurred, and documents the preventative controls enforced in V1.2.

---

## 2. Root-Cause Analysis: Rule Detail Screenshot Capture Bug

### 2.1 The Observed Defect
In V1.1, screenshots saved to `docs/UI_COMPACT_REDESIGN_V1/VALIDATION_V1_1/screenshots/studio_rule_detail_approved_*.png` and `studio_rule_detail_blocked_*.png` showed:
- The top header: "Agent Intelligence Studio 2.0 — Detection-Aware Policy Engine"
- The filter bars: Search, Severity, Archetype, Completeness, Readiness
- The 4-column summary metric cards: Monitored Rules, Approved, Drafts, Needs Attention
- The Rules Directory table with rows for FortiGate, CrowdStrike, and Palo Alto rules.

**The actual Rule Detail view**—including the compact 3-tab architecture (Overview, Analyst Learning, Advanced), the 6-stage guided readiness workflow (`define_detection` through `production_approval`), policy version selector, and prompt diff viewer—was **completely absent**.

### 2.2 Root-Cause Breakdown

#### Failure 1: Script Navigation & Selector Flaw
In `scripts/run_populated_validation.mjs` (V1.1), the test script executed:
```javascript
// V1.1 buggy implementation
await page.goto(`${BASE_URL}/agent-intelligence-studio`);
const select = await page.$('select');
if (select) {
  await select.select('RULE-NET-001'); // Attempted to select rule from a select element
}
await page.screenshot({ path: 'studio_rule_detail_approved.png' });
```
- In Agent Intelligence Studio, rule selection was **not** driven by a native HTML `<select>` tag on the main page. The page rendered a custom TanStack table with clickable action buttons (`Open in Studio` / `Manage Policy`).
- The first `<select>` element matched on the page was actually the **Archetype Filter** or **Page Size** dropdown in the catalog toolbar.
- Calling `.select()` on that dropdown changed a filter or did nothing, leaving the user on the catalog table.
- Because there was no assertion verifying that the URL changed or that the Studio view rendered, the script captured the catalog table and tagged it as `studio_rule_detail_approved.png`.

#### Failure 2: Client-Side Routing & Query Param Resolution
In Next.js, `AgentIntelligenceStudioPage` had support for `?rule_id=...`, but in `AgentIntelligenceStudioContent`:
1. `init()` checked `params.get("rule_id")` and attempted to find a match in `rules`. If `rules` had not finished fetching asynchronously, `matched` was `undefined`, and `viewMode` was never switched from `"table"` to `"studio"`.
2. Next.js Turbopack dev server blocked `127.0.0.1` cross-origin requests (`/_next/hmr`) unless explicitly configured in `allowedDevOrigins` in `next.config.ts`, causing client-side hydration to stall during headless automated runs.
3. No DOM assertions existed to fail the build when the catalog table was rendered instead of the detail container.

---

## 3. Root-Cause Analysis: Production-Readiness Inconsistencies

### 3.1 Scenario A: Rule Reporting `ACTIVE` with Only 7/8 Gates Passed
- **Observation:** In the rules directory and summary endpoints, rules were displayed with a green `ACTIVE` production readiness badge, despite only passing 7 of 8 quality gates.
- **Root Cause in Backend:** In `backend/app/api/rules.py` (lines 170–190) and `backend/app/api/prompts.py` (lines 160–185):
  ```python
  # Buggy V1.1 logic:
  has_approved = any(v.status == "APPROVED" for v in versions)
  if has_approved and rule.status == "ACTIVE":
      readiness_status = "ACTIVE"
  ```
- **The Defect:**
  1. The code checked `rule.status == "ACTIVE"`, which is the **SIEM deployment status** (whether the detection rule is running in FortiSIEM/Splunk).
  2. The code checked `any(v.status == "APPROVED")`, which evaluated whether **any historical version** was approved, even if the user was currently evaluating candidate Version 2 (a draft that had only passed 7 gates).
  3. This conflated SIEM operational deployment with AI Policy Candidate readiness, violating Quality Gate G8 and ISO/IEC 42001 governance.

### 3.2 Scenario B: Rule with `UNKNOWN` Archetype Reporting `ACTIVE` Readiness
- **Observation:** Rules with missing or unparseable SIEM pattern logic (`archetype == "UNKNOWN"` or `None`) were reporting `ACTIVE` readiness if they had an active status in SIEM.
- **Root Cause in Backend:**
  - `prompts.py` failed to enforce `is_def_incomplete = True` when `archetype in ("UNKNOWN", None, "")`.
  - In Agent Intelligence Studio 2.0, an `UNKNOWN` archetype means the AI cannot ground its reasoning in verified detection semantics (e.g. threshold, grouping, or sequence).
  - Reporting `ACTIVE` readiness for an ungrounded rule allowed untested LLM inference to execute in production.

---

## 4. Remediation Implemented in V1.2

| Area | V1.1 Defect | V1.2 Remediation | Verification Status |
| :--- | :--- | :--- | :--- |
| **Automation Harness** | Blind screenshot capture without DOM assertions | Integrated CDP automation with hard DOM assertions (`compact-rule-detail`, 3 primary tabs, 6 readiness stages). Fails test if catalog or loading state is visible. | **VERIFIED PASS (48/48 screenshots)** |
| **Client Routing** | Query param resolution failed when matching UUID vs Rule ID | Updated `page.tsx` to match either `r.id === ruleParam || r.rule_id === ruleParam`. Added `data-testid` hooks. | **VERIFIED PASS** |
| **Next.js Config** | Turbopack dev server blocked `127.0.0.1` cross-origin HMR | Added `allowedDevOrigins: ['127.0.0.1', 'localhost']` in `next.config.ts`. | **VERIFIED PASS** |
| **Status Separation (Scenario A)** | Conflated SIEM deployment status with AI Policy Candidate readiness | Refactored `rules.py` and `prompts.py`: `ACTIVE` readiness strictly requires `is_target_approved and gates_passed_count == 8 and rule.status == "ACTIVE" and not is_suspended`. | **VERIFIED PASS (pytest 5/5)** |
| **Archetype Guard (Scenario B)** | `UNKNOWN` archetype rules allowed `ACTIVE` readiness | Enforced `is_def_incomplete = True` when `archetype in ("UNKNOWN", None, "")`, forcing status to `INCOMPLETE`. | **VERIFIED PASS (pytest 5/5)** |

---

## 5. False Confidence Prevention: Mandatory Governance Rules

To prevent regressions and false confidence in future releases:
1. **Zero Blind Capture:** No UI test may save a screenshot as passing evidence without verifying the presence of target DOM containers and verifying the absence of error/loading/catalog fallback containers.
2. **Authoritative Status Decoupling:** SIEM Deployment Status, AI Policy Candidate Readiness, and Policy Version Lifecycle must remain strictly distinct fields in both backend schemas and UI badges.
3. **Automated Gate Enforcement:** The quality gate engine is authoritative. Frontend badges must reflect server-computed gate evaluations without client-side overrides.
