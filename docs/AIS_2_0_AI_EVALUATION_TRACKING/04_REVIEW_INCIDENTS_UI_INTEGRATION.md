# Phase 4: Review Incidents UI Integration

## 1. User Interface Redesign & Mode Switch
The **Review Incidents** workbench (`frontend/src/components/compact/ReviewIncidentsWorkbench.tsx`) was enhanced to support dual operational workflows without introducing sidebar sprawl:

1. **Double-Blind Review Queue (Analyst Mode):**
   - Preserves original analyst workflow: raw evidence display, independent verdict selection (True Positive / False Positive / Insufficient Evidence), and post-submission AI comparison.
   - Enforces zero AI disclosure prior to submission.
2. **AI Evaluation Tracking (Admin Mode):**
   - Compact table for administrators and AI engineers.
   - Displays evaluation coverage, policy versions, execution provenance, and quick diagnostic actions.

---

## 2. Compact Incident Tracking Table

The tracking view renders a high-density, accessible table:

| Incident ID | Analyst Review | AI Evaluation | Policy Version | Actions |
|---|---|---|---|---|
| `INC-2026-1001` | <Badge variant="secondary">Verified FP</Badge> | <Badge variant="success">EVALUATED — DECISIVE</Badge> | `v7` | [Inspect] [History] |
| `INC-2026-1002` | <Badge variant="secondary">Verified FP</Badge> | <Badge variant="warning">ABSTAINED</Badge> | `v7` | [Inspect] [History] |
| `INC-2026-1003` | <Badge variant="secondary">Verified FP</Badge> | <Badge variant="outline">NOT EVALUATED</Badge> | — | [Test AI] |
| `INC-2026-1004` | <Badge variant="secondary">Verified FP</Badge> | <Badge variant="destructive">VALIDATION REJECTED</Badge> | `v7` | [Inspect Error] |

---

## 3. Modal Dialogs & Inspection

### 3.1 Evaluation Details Modal
- Displays:
  - Canonical Evaluation Status badge.
  - Policy Version (ID and Number).
  - Model Name & Execution ID.
  - Raw Model Output vs Governed Effective Verdict.
  - Evidence Grounding Score.
  - Validation Outcome & Deterministic Rejection Reason (if rejected).
  - Execution Duration & Token Usage.
  - Prompt Capture Reference.

### 3.2 Evaluation History Modal
- Chronological timeline of all evaluation attempts for the selected incident.
- Displays policy version, timestamp, execution status, and verdict for each attempt.
- Explicitly flags mock/simulated results.
