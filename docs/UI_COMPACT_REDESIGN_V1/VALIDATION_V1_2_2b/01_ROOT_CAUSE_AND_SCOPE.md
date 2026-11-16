# Verdictum AI — Validation V1.2.2b
## 01: Root Cause Analysis and Acceptance Scope

### 1. Executive Summary & Purpose
The **Validation V1.2.2b** engagement addresses critical evidence-integrity blockers and residual security gaps surfaced during Validation V1.2.2a. Specifically, prior validation artifacts contained false `status: PASS` claims despite underlying HTTP 404 responses from non-canonical API routes. Furthermore, formal mathematical and cryptographic verification was required to prove that Blind Review redaction never mutates persistent database rows, that cross-tenant boundaries are strictly enforced across all primary and secondary routes, and that ambiguous UI status badges do not conflate SIEM activation with AI policy readiness.

This document records the definitive root cause analysis, architecture boundaries, and comprehensive scope of fixes implemented and validated under V1.2.2b.

---

### 2. Verified Root Causes

#### Root Cause 1: Non-Canonical Readiness Route & DOM-Only Runner Conjunction (P0)
- **Defect:** In Validation V1.2.2a evidence, Scenarios 6, 7, and 8 recorded `actualBackendStatus: 404` with `readiness: undefined`, yet the overall outcome was falsely stamped `status: PASS`.
- **Mechanism:** The test runner `scripts/run_v1_2_2a_validation.mjs` formulated an invalid URL:
  `${BACKEND_URL}/api/prompts/readiness/${rule_id}`
  However, the canonical FastAPI route mounted in `backend/app/api/prompts.py` is:
  `GET /api/prompts/rule/{rule_id}/readiness`
  Because the previous runner script evaluated outcome solely via `scenarioPassed = domResult.isValid`, it completely disregarded the HTTP 404 response returned by the backend.
- **Resolution:**
  1. Updated test runners and frontend consumers to target canonical route `GET /api/prompts/rule/{rule_id}/readiness`.
  2. Implemented strict boolean conjunction fail-fast logic in `scripts/run_v1_2_2b_validation.mjs`:
     `scenarioPassed = apiValid && domResult.isValid`
     where `apiValid = (actualStatus === expectedStatus) && payloadValidationPassed`.

#### Root Cause 2: Verification of Database Immutability during Blind Review (P0)
- **Defect:** Concern that ORM entity retrieval during Blind Review masking might mark attributes dirty or flush redacted strings (`[Hidden - Blind Review]`) into persistent SQLite storage.
- **Mechanism:** In earlier iterations, unmasked `ai_verdict` dicts were retrieved directly from `Incident` model instances attached to active SQLAlchemy sessions. If an uncareful route or helper mutated `incident.ai_verdict` in place without creating a deep copy or detaching from the session, `session.flush()` or `session.commit()` could overwrite ground-truth data.
- **Resolution:**
  1. Enforced session detachment via `session.expunge(incident)` and explicit copy construction across all service retrieval routines.
  2. Implemented `test_04_blind_review_db_immutability_byte_for_byte` asserting exact byte-for-byte SHA-256 identity of database rows before and after unreviewed analyst requests.

#### Root Cause 3: Cross-Tenant Boundary Gaps in Incident & Investigation APIs (P1)
- **Defect:** The `Incident` model contained a `customer` column, but `User` lacked customer scoping. Cross-tenant incident access was not uniformly blocked across timeline, investigation queue, review submission, and prompt export endpoints.
- **Mechanism:** Non-admin analysts from Customer Alpha could query incident identifiers belonging to Customer Beta, potentially disclosing alert telemetry, source IPs, and analyst notes.
- **Resolution:**
  1. Added `customer` column to `users` table and updated authentication JWT tokens with customer tenant affiliation.
  2. Implemented strict tenant filtering across `IncidentService.list_incidents_with_rule_summary`, `get_incident`, `InvestigationService.list_queue`, `TelemetryTimelineService.get_incident_timeline`, `ActualPromptCaptureService`, and `AnalystReviewService.submit_analyst_review`.
  3. Raised `HTTP 403 Forbidden` with `"Access denied"` whenever non-admin users attempt cross-tenant access.

#### Root Cause 4: Ambiguous "Production Active" Studio Badge & Baseline Status Header (P1)
- **Defect:** The Studio header displayed an ambiguous `<CheckCircle2 /> Production Active` badge for candidate versions, and the Detection Intelligence table used the misleading column header `Baseline Status`.
- **Mechanism:** SOC analysts frequently confused SIEM rule activation with AI policy production eligibility.
- **Resolution:**
  1. Renamed Studio badge to `Active Policy v{selectedVersion.version_number}` in `frontend/src/app/agent-intelligence-studio/page.tsx`.
  2. Renamed column header in `frontend/src/app/detection-intelligence/page.tsx` from `Baseline Status` to `SIEM Status` with `SIEM ACTIVE` badge text.
  3. Preserved clear 4-part status indicators in `AgentIntelligenceStudioOverview.tsx`: SIEM Rule, Policy Version, Current Readiness, and AI Execution.

---

### 3. V1.2.2b Implementation & Acceptance Scope
The scope of V1.2.2b encompasses:
1. **Backend Routing & Integrity:** Canonical `/api/prompts/rule/{rule_id}/readiness` routing and API response schema alignment.
2. **Database Immutability Engine:** Proven non-mutating Blind Review serialization with regression test coverage.
3. **Tenant Isolation Architecture:** Multi-tenant customer scoping across all incident, investigation, timeline, and export endpoints.
4. **UI Clarity & Disambiguation:** Precision labeling across Studio and Detection Intelligence surfaces.
5. **Headless E2E Validation:** 10 comprehensive scenarios across 2 viewports (1440x900 and 1920x1080) producing 20 high-fidelity screenshots and machine-verifiable `VALIDATION_EVIDENCE.json`.
