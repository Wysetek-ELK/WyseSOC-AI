# VERDICTUM AI — PHASE 3
# 07. Human Review Queue Redesign Specification

**Document Version:** 3.0.0  
**Phase:** Phase 3 — Unified Compact UI/UX Modernization  
**Page Implementation:** `frontend/src/app/human-review-queue/page.tsx`  

---

## 1. Overview & Objectives

The Human Review Queue serves as the authoritative human-in-the-loop decision capture center. Analysts evaluate disputed, high-severity, or ungrounded incidents and record verified ground truth verdicts that power continuous rule learning and production promotion gating.

The Phase 3 modernization delivers:
1. **Double-Blind Review Safeguards:** Complete masking of AI recommendations prior to analyst verdict submission.
2. **Post-Submission Comparison Reveal:** Instant visual comparison showing whether the analyst agreed or disagreed with the AI's proposal.
3. **Evidence-First Investigation Drawer:** Streamlined review workspace with 1-click True Positive, False Positive, and Requires Attention buttons.
4. **Disputed Case Highlighting:** Prominent tracking of cases where the analyst disposition disagreed with legacy SIEM closure.

---

## 2. Double-Blind Review Enforcement

A critical governance vulnerability of the legacy interface was that opening an investigation drawer displayed the AI's predicted verdict and confidence score, inadvertently biasing the human reviewer.

In Phase 3:
- The page integrates a global **Double-Blind Review Toggle** (`blindReviewMode`) in the header toolbar, complete with an amber status banner.
- When `blindReviewMode` is enabled and an investigation has not yet been reviewed:
  - The AI Verdict Assurance & Provenance panel is completely replaced with a masked notice:
    > *"Double-Blind Review Active: AI model's proposed verdict, confidence score, and justification are withheld to prevent cognitive bias during independent analyst assessment."*
  - The analyst is guided to evaluate the telemetry and questions objectively.

---

## 3. Post-Submission Comparison Reveal

Once the analyst selects a verdict (`TRUE_POSITIVE`, `FALSE_POSITIVE`, or `REQUIRES_ATTENTION`), inputs their rationale, and submits the review:
- The drawer instantly unlocks the full AI assurance card.
- A high-contrast comparison banner appears:
  - **Agreement:** `✓ Analyst Agreed with AI Validated Verdict` (in emerald).
  - **Disagreement / Override:** `⚠ Analyst Overrode AI (TRUE_POSITIVE vs AI FALSE_POSITIVE)` (in amber/rose).
- The case is recorded in the verified learning repository and, if verified, becomes immediately eligible for the RAG historical precedent pool.

---

## 4. Compact Review Workspace Drawer

The review drawer layout is organized into a clean, logical 4-section flow:
1. **Quick Controls Bar:** Analyst assignment dropdown and workflow status selector (`PENDING_REVIEW`, `IN_PROGRESS`, `REVIEWED`, `CLOSED_DRY_RUN`).
2. **Incident Telemetry Summary:** Source IP, reporting device, severity, and deep-link to the full AI Triage Workbench dossier.
3. **Investigation Q&A & Evidence Artifacts:** Collapsible sections for asking investigative hypotheses and attaching decoded command payloads, registry keys, or process trees.
4. **Final Analyst Verdict Console:**
   - 1-click outcome buttons (`True Positive`, `False Positive`, `Attention`).
   - Mandatory insufficient evidence reason input when `Attention` is selected.
   - Definitive verdict rationale and handover notes textareas.
   - Quality checkboxes: `Mark as Disputed` and `Independently Verified`.
   - Single-click submit action with loading state spinner.
