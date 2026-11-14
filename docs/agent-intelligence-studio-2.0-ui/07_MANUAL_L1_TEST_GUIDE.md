# 07 - Manual L1 Test Guide

## 1. Introduction

This guide provides Level 1 (L1) SOC Analysts, SOC Leads, and Quality Engineers with an actionable walkthrough for verifying the simplified Agent Intelligence Studio 2.0 interface and production readiness workflow.

---

## 2. Test Scenario 1: Rule Discovery & Catalog Readiness

**Objective:** Verify that the detection rule catalog clearly displays readiness status without confusing it with SIEM deployment status.

1. Navigate to **Detection Intelligence** (`/detection-intelligence`) or **Rules** (`/rules`).
2. Observe the rules table:
   - Notice the **Baseline Status** column displaying whether FortiSIEM alert ingestion is `ACTIVE` or `INACTIVE`.
   - Notice the new **Production Readiness** column displaying:
     - The AI policy readiness badge (`ACTIVE`, `APPROVED`, `READY FOR APPROVAL`, `VALIDATING`, `LEARNING`, `BLOCKED`, `INCOMPLETE`).
     - The completed gates count (e.g. `1/8`).
     - Any missing requirements count (e.g. `(1 missing)` in amber).
3. Test the filter dropdown:
   - Select `Blocked / Incomplete` from the **All Production Readiness** dropdown.
   - Verify that only rules with unverified logic, contract gaps, or quality blockers appear.
4. Click on the rule **"Heavy TCP Host Scan On Fixed Port"** (or click the **Studio** button in its row).
5. Verify that the browser seamlessly transitions into the simplified Studio Overview.

---

## 3. Test Scenario 2: Guided Overview & Next Action Navigation

**Objective:** Verify that an L1 analyst can immediately understand what a rule does, its readiness progress, and the exact next step.

1. On the **Overview** tab:
   - **Check Rule Identity:**
     - Rule Name: `"Heavy TCP Host Scan On Fixed Port"`
     - Archetype: `"NETWORK_SCAN"` (Never `UNKNOWN`)
     - Plain-English Description: Clearly explains that the rule detects port scan activity across fixed TCP ports.
     - Baseline Status: `"Deployment: ACTIVE"`
   - **Check Readiness Summary:**
     - Readiness Status: Large readable banner showing `BLOCKED / INCOMPLETE`.
     - Quality Gates: `1 / 8 Passed`
     - Rule Quality: `48 / 100`
     - Verified Reviews: `0 / 30`
     - Empirical Accuracy: Displays `N/A` (never falsely claiming PASS or 0%).
   - **Check Smart Next Action Card:**
     - Verify only one primary action is presented: `"Verify FortiSIEM Detection Semantics"`.
     - Click the action button `"Inspect Semantics"`.
     - Verify it navigates directly to Tab 3 -> SIEM Semantics subsection.
2. Return to the **Overview** tab and review the **6 Guided Checklist Stages**:
   - Stage 1: Define Detection -> Shows `NEEDS_ACTION` or `BLOCKED`.
   - Stage 2: Verify Evidence -> Shows `PENDING` or `BLOCKED`.
   - Stage 3: Validate AI Policy -> Shows `NEEDS_ACTION`.
   - Stage 4: Analyst Learning -> Shows `PENDING` (0/30 reviews).
   - Stage 5: Test AI Accuracy -> Shows `PENDING` (Awaiting ground truth).
   - Stage 6: Production Approval -> Shows `PENDING` (Awaiting gate completion).
3. Expand a stage's technical details:
   - Click `"Show Technical Details (G1–G8 / Evidence)"` on any stage.
   - Verify that individual gate diagnostics and raw telemetry appear without cluttering the main screen.

---

## 4. Test Scenario 3: Double-Blind Analyst Review Workbench

**Objective:** Verify that an analyst can conduct an independent, double-blind review to build verified ground truth.

1. Click on **Tab 2: Analyst Review & Learning**.
2. Select an incident from the **Pending Review Queue** on the left.
3. Verify that the incident appears in **Double-Blind Mode**:
   - The AI Model Verdict is masked with a purple lock shield to prevent confirmation bias.
   - Source IP, reporting device, and incident details are visible.
4. Select a determination:
   - Click `FALSE POSITIVE` (Benign / Expected) or `TRUE POSITIVE` (Malicious / Attack).
   - Enter investigation notes (e.g., *"Authorized network vulnerability scan conducted by SecOps"*).
   - Enter evidence references (e.g., `approved_change_ticket_CHG-8912`).
5. Click **Submit Review**:
   - Verify that the AI Model Verdict and confidence are revealed post-submission.
   - Verify that agreement/disagreement comparison is recorded.
   - Observe that Verified Reviews count increments by 1.
6. Review the **Educational Explanation Box** at the bottom:
   - Confirm the 4 clear explanations distinguishing *Reviews Collected*, *Verified Ground Truth*, *Sufficient Statistical Evidence*, and *Production Accuracy Eligibility*.

---

## 5. Test Scenario 4: Advanced Configuration & Production Gating

**Objective:** Verify that technical capabilities are organized cleanly in Tab 3 and approval gating is enforced.

1. Click on **Tab 3: Advanced Configuration**.
2. Notice the horizontal sub-navigation:
   - `Policy Editor (9 Sections)`
   - `Quality Gates (G1–G8)`
   - `SIEM Semantics`
   - `Evidence Contract`
   - `Simulation Lab`
   - `Drift & Monitoring`
3. Click `Quality Gates (G1–G8)`:
   - Review each of the 8 gate cards.
   - Note which gates are passing and which have blockers.
4. Attempt Production Approval on a blocked rule:
   - If logged in as an Analyst or Viewer, verify the Approval button is disabled or hidden.
   - If logged in as Admin, clicking Approve on a blocked rule triggers a validation rejection explaining that approval is blocked by mandatory Quality Gates.
