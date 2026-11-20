# Report 01 — Existing Analyst Review Workflow Audit
**Verdictum AI — AIS 2.0 Blind Review Integrity & SOC Analyst Pilot Activation**
**Date:** November 20, 2026  
**Status:** COMPLETE & AUDITED  
**Target Rule:** Website Access Policy Violation (`7bd13e89-0828-48e6-8cf5-f3cbf12d438c`)  

---

## 1. Executive Summary

This audit assesses the end-to-end human analyst review architecture in Verdictum AI, specifically focusing on Double-Blind Review integrity within the **Agent Intelligence Studio 2.0 (AIS 2.0)**. The goal is to ensure that a SOC analyst cannot observe any AI determination, confidence score, reasoning, or agreement classification before independently submitting their own evaluation for FortiSIEM incidents.

The audit examined all frontend components, FastAPI routers, SQLAlchemy data models, and network serialization boundaries.

---

## 2. Architecture & Component Inventory

| Component / Layer | Implementation File | Primary Responsibility | Audit Finding |
|:---|:---|:---|:---|
| **Workbench UI** | `frontend/src/components/compact/ReviewIncidentsWorkbench.tsx` | Tab 1 split-panel interface: incident selection, evidence display, independent verdict radio buttons, notes, and post-submission reveal. | **VERIFIED.** Pre-submission UI strictly renders only raw telemetry and normalized artifacts. Pre-submission "Inspect Payload" button removed to prevent LLM capture leakage. |
| **AIS 2.0 Host Page** | `frontend/src/app/agent-intelligence-studio/page.tsx` | Hosts ReviewIncidentsWorkbench in Tab 1, coordinates rule selection, and handles modal navigation. | **VERIFIED.** Wires `onOpenActualPrompt` exclusively for safe post-submission prompt capture inspection. |
| **API Endpoints** | `backend/app/api/rule_learning.py` | `GET /api/reviews/pending`, `POST /api/reviews/{incident_id}/submit`, `POST /api/reviews/{review_id}/adjudicate`. | **VERIFIED.** Enforces role-based access (`require_analyst`), validates submission payload, and masks AI determinations. |
| **Analyst Review Service** | `backend/app/services/analyst_review_service.py` | Orchestrates queue retrieval, double-blind masking, idempotent review submission, multi-analyst dispute handling, and learning profile synchronization. | **VERIFIED.** Strict server-side masking. Fixed `getattr(inc, "events", None)` to eliminate event count discrepancies. |
| **Incident Service** | `backend/app/services/incident_service.py` | `get_incidents`, `get_incident` with server-enforced `can_see_verdict` isolation. | **VERIFIED.** Multi-analyst role matching made case-insensitive; unreviewed incidents return `ai_verdict = None`. |
| **Data Models** | `backend/app/models/analyst_feedback.py` | `AnalystVerdictReview`, `AnalystReviewAdjudication`. | **VERIFIED.** Immutable audit trail with `blind_mode_active = True`. |

---

## 3. Exhaustive Exposure Path Analysis (11 Threat Vectors)

The audit evaluated all 11 possible exposure paths to answer the critical question:  
*Can a SOC analyst see any AI verdict, AI confidence, AI reasoning, or agreement-derived label before submitting an independent review?*

| Threat Vector | Exposure Path Evaluated | Backend / Frontend Protection Mechanism | Risk Status |
|:---|:---|:---|:---:|
| **1. Review Incidents Tab** | Direct inspection of `ReviewIncidentsWorkbench.tsx` DOM | Radio options restricted to `TRUE_POSITIVE`, `FALSE_POSITIVE`, `INSUFFICIENT_EVIDENCE`. AI determination elements are wrapped in `{revealedResult && (...)}` and do not exist in the DOM pre-submission. | **SECURE (PASSED)** |
| **2. Incident Details API** | `GET /api/incidents/{identifier}` | Server-side enforcement in `IncidentService.get_incident`: `can_see_verdict = has_analyst_review`. Unreviewed incidents return `ai_verdict: null` and sanitize raw event payloads. | **SECURE (PASSED)** |
| **3. AI Analysis Preview** | Other workbench pages (`/ai-triage-workbench`) | For users with analyst roles, `can_see_verdict` is False on unreviewed incidents. The AI badge renders `[Hidden - Blind Review]` without leaking the verdict. | **SECURE (PASSED)** |
| **4. Global Blind Review Toggle** | Header toggle in `AppContext.tsx` | In `ReviewIncidentsWorkbench.tsx`, `blind_review = true` is hardcoded in the API call and cannot be disabled by toggling client state. | **SECURE (PASSED)** |
| **5. Direct API Access** | Raw curl/Postman to `GET /api/reviews/pending` | `AnalystReviewService.get_pending_reviews` completely omits `ai_verdict`, `confidence`, and `reasoning` from the JSON response for all users. | **SECURE (PASSED)** |
| **6. Network Payloads** | DevTools Network Tab inspection | Payloads inspected: `GET /api/reviews/pending` contains zero model prediction keys. `GET /api/incidents/{id}/model-payload` contains only sanitized raw security telemetry. | **SECURE (PASSED)** |
| **7. Cached Frontend State** | React Query / local component state | `useEffect` resets `selectedIncident`, `incidentDetail`, and `revealedResult` to `null` whenever `ruleId` or selected incident changes. | **SECURE (PASSED)** |
| **8. Browser Refresh** | Hard refresh ($F5$) on active review | Resets local state; queries fresh pending review queue. Since the review was unsubmitted, the backend continues to serve the incident masked. | **SECURE (PASSED)** |
| **9. Deep Links** | Direct URL to `/agent-intelligence-studio?rule=...&incident=...` | Incident loading triggers `api.getIncidentDetail(..., true)`, enforcing server-side masking. | **SECURE (PASSED)** |
| **10. Browser Back Navigation** | History traversal after navigating away | Next.js state rehydrates cleanly; unsubmitted incidents remain masked on the server. | **SECURE (PASSED)** |
| **11. Exports & Captures** | Exporting raw prompt captures before review | Pre-submission "Inspect Payload" button removed from the workbench header. Prompt inspector can only be opened *after* review submission (`revealedResult !== null`). | **SECURE (PASSED)** |

---

## 4. Conclusion

True Double-Blind review isolation is enforced at the backend service layer, API serialization layer, and frontend rendering layer. Zero leakage vectors exist for SOC analysts evaluating unreviewed FortiSIEM incidents.
