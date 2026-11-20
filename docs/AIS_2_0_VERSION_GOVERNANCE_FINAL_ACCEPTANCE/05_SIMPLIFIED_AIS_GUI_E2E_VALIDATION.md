# Report 05 — Simplified AIS 2.0 GUI End-to-End Validation
**Project**: Verdictum AI — Agent Intelligence Studio (AIS 2.0)  
**Execution Context**: Version Governance Safety & Final GUI Acceptance  
**Environment**: Production Server 1 (`172.26.41.240`) & Local Engineering Replica  
**Date**: November 20, 2026  

---

## 1. Executive Summary

This report documents the end-to-end GUI validation of the redesigned Agent Intelligence Studio 2.0 (`frontend/src/app/agent-intelligence-studio/page.tsx`). The workspace simplifies complex SOC engineering workflows into three primary tabs for day-to-day operations and a modular fourth tab for advanced configuration.

---

## 2. Global Rule Header & Action Banner

### Decoupled Status Badges
The top header provides decoupled, unambiguous indicators:
- **SIEM Rule Identity**: Rule Name, Rule UUID, Severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
- **SIEM Active Badge**: Green/gray indicator showing whether the rule is active in the SIEM engine.
- **Active Policy Version**: Shows approved production baseline (e.g. `Approved: v2` or `No Active Version`).
- **Candidate Policy Draft**: Shows candidate draft if present (e.g. `Draft: v3`).
- **Supervised Learning Stage**: Shows progression (`STAGE 1: UNCALIBRATED`, `STAGE 2: SUPERVISED`, `STAGE 3: PRODUCTION READY`).

### Authoritative Next Recommended Action Banner
A prominent action card informs the analyst of the exact next step required to advance the rule:
- `Create Draft Policy` (when no policy exists)
- `Validate Draft Policy` (when draft has rework required)
- `Start Analyst Review` (when fewer than 10 ground truth reviews exist)
- `Evaluate Accuracy` (when unverified accuracy prevents production release)
- `Run AI Simulation / Verification` (when candidate policy is ready for dry-run testing)
- `Request Administrator Approval` (when all quality gates G1–G8 are satisfied)

---

## 3. Tab 1: Review Incidents (`ReviewIncidentsWorkbench.tsx`)

**Default tab for SOC tier-1 and tier-2 analysts.**

### Key Components & Capabilities
1. **Incident Metrics Row**:
   - `Pending Incidents` (incidents awaiting analyst ground-truth review)
   - `Reviewed Incidents` (analyst reviewed count)
   - `Verified Ground-Truth` (verified true/false positives count)
   - `Double-Blind Status` (indicates whether analyst review is masked from AI verdict)
2. **Double-Blind Review Queue**:
   - Displays real SIEM incidents mapped to the rule.
   - Masks AI verdict and confidence until analyst submits their independent assessment.
3. **Analyst Ground-Truth Verdict Selection**:
   - `TRUE_POSITIVE`: Confirmed security threat matching detection logic.
   - `FALSE_POSITIVE`: Benign activity or misconfiguration.
   - `INSUFFICIENT_EVIDENCE`: Incident lacks requisite logs to determine truth.
4. **Investigation Reasoning**: Mandatory analyst justification field.
5. **Workflow Actions**:
   - `Submit Review`: Commits immutable analyst review to PostgreSQL `analyst_feedback` table.
   - `Next Incident`: Automatically loads the next pending incident in the queue.

---

## 4. Tab 2: Test AI (`AiTestWorkbench.tsx`)

**Interactive testing workbench for security engineers.**

### Key Components & Capabilities
1. **Model Architecture Indicator**:
   - Prominently displays the active Local AWQ model: `Qwen/Qwen2.5-7B-Instruct-AWQ` running on Server 2 (`172.26.41.241`).
   - Verified temperature: `0.01` (deterministic execution).
2. **Real AI Test Execution**:
   - Executes real inference against candidate or active policy using actual SIEM incident telemetry.
3. **Verdict Results Display**:
   - **Effective Verdict**: `TRUE_POSITIVE`, `FALSE_POSITIVE`, `SUSPICIOUS`, or `REQUIRES_ATTENTION`.
   - **Verdict Confidence**: Percentage confidence derived by the Local AWQ model.
   - **Evidence Grounding Score**: Percentage of claims grounded in verified incident raw telemetry.
   - **Token Telemetry**: Prompt token count, completion token count, and total latency in milliseconds.
4. **Policy Differences**:
   - If candidate draft is tested, compares candidate verdict against active baseline verdict side-by-side.

---

## 5. Tab 3: Accuracy & Learning (`AccuracyLearningSummary.tsx`)

**Performance analytics and calibration dashboard.**

### Key Components & Capabilities
1. **Accuracy Measurability Status**:
   - If fewer than 10 verified ground-truth incidents exist, explicitly displays:
     `Accuracy: NOT MEASURABLE`
   - Recommends: `"Begin Independent Analyst Reviews in Tab 1 to build statistically valid ground truth."`
2. **Performance Metrics (When Verified)**:
   - Overall Classification Accuracy (%)
   - True Positive (TP) Recall (%)
   - False Positive (FP) Precision (%)
   - Ground Truth Sample Size ($N$)
3. **Confusion Matrix**:
   - Visual 2x2 matrix comparing Analyst Ground Truth vs AI Verdict:
     - True Positives (TP)
     - False Positives (FP)
     - True Negatives (TN)
     - False Negatives (FN)

---

## 6. Tab 4: Advanced Settings (9 Modular Collapsible Sections)

For administrators and advanced SOC engineers, secondary configurations are structured into 9 collapsible modules:
1. `1. Investigation Policy`: Full prompt templates, detection conditions, and escalation criteria.
2. `2. Quality Gates`: Interactive breakdown of G1–G8 validation gates with blocking issue details.
3. `3. Evidence Contract`: Machine-verifiable contract mapping rule event types to required fields.
4. `4. Rule XML & Logic`: Canonical SIEM XML definition, severity, and event type.
5. `5. Prompt Inspector`: Real-time outbound LLM prompt capture viewer.
6. `6. Model Diagnostics`: Hardware, GPU, context window, and latency diagnostics.
7. `7. Simulation History`: Historical pilot and dry-run execution runs.
8. `8. Production Governance`: Formal sign-off records, approver identities, and drift history.
9. `9. Manage Versions`: Authoritative policy version governance, preview, and safe cleanup table.

---

## 7. GUI Acceptance Conclusion
The simplified AIS 2.0 interface eliminates clutter, prevents analyst confusion, accelerates triage workflows, and provides seamless access to deep governance controls when needed.
