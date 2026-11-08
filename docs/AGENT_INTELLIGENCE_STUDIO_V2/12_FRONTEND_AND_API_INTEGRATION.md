# 12. FRONTEND AND API INTEGRATION

## Overview

Agent Intelligence Studio 2.0 features an updated Next.js 16 frontend interface (`frontend/src/app/agent-intelligence-studio/page.tsx`) and FastAPI REST API (`backend/app/api/prompts.py`), engineered to deliver real-time policy inspection, quality gate diagnostics, and governance controls.

---

## REST API Specification

| Endpoint | Method | Role | Description |
| :--- | :--- | :--- | :--- |
| `/api/prompts/intelligence` | `GET` | Analyst / Lead | Returns full detection semantics, archetype, and input tier snapshot for a rule. |
| `/api/prompts/analyze` | `POST` | Analyst / Lead | Ingests authoritative SIEM definition (XML/JSON) and re-evaluates rule semantics. |
| `/api/prompts/generate-intelligent-draft` | `POST` | Analyst / Lead | Generates a tailored 9-section draft policy and synchronized Evidence Contract. |
| `/api/prompts/validate-quality` | `POST` | Analyst / Lead | Evaluates draft policy text against the 8 mandatory gates (G1–G8) and returns score. |
| `/api/prompts/evaluate-simulation` | `POST` | Analyst / Lead | Triggers historical Simulation Lab backtesting; returns regression metrics or insufficient data status. |
| `/api/prompts/drift` | `GET` | Analyst / Lead | Retrieves active drift events (SIEM modifications, schema changes, feedback divergence). |
| `/api/prompts/acknowledge-drift` | `POST` | SOC Lead | Acknowledges a drift event and clears the warning flag. |
| `/api/prompts/quality/summary` | `GET` | Analyst / Lead | Retrieves library-wide audit statistics, distribution, and top blockers. |
| `/api/prompts/quality/bulk-assess` | `POST` | SOC Lead | Initiates an asynchronous bulk audit job across the detection rule library. |
| `/api/prompts/quality/bulk-assess/{job_id}` | `GET` | Analyst / Lead | Polls status, progress, and interim results of an active bulk audit job. |
| `/api/prompts/rules/{id}/approve` | `POST` | SOC Lead | **Enforces validation:** Approves candidate version, synchronizes contract, logs audit record. |
| `/api/prompts/rules/{id}/rollback` | `POST` | SOC Lead | Non-destructively reverts to a previous version number. |

---

## Frontend Architecture (`page.tsx`)

The UI is architected into two primary views with intuitive visual feedback:

```text
+-------------------------------------------------------------------------+
|                  VIEW 1: DETECTION RULES DIRECTORY TABLE                |
|                                                                         |
|  [ Search & Filters: Search query | Archetype | Definition Status ]     |
|  [ Actions: "Bulk Audit Rules" Button ]                                 |
|                                                                         |
|  Table Columns:                                                         |
|  - Rule Name & ID                                                       |
|  - Archetype Badge (e.g. "Network Exfiltration" - purple)               |
|  - Definition Status Badge ("VERIFIED" - emerald | "INCOMPLETE" - red)  |
|  - Quality Score Badge (e.g. "88/100" - green | "40/100" - red)         |
|  - Drift Warning Flag (amber alert pill if unacknowledged drift exists) |
|  - Active Version Number & Status                                       |
|  - Action: "Open Studio" Button                                         |
+-------------------------------------------------------------------------+
|                  VIEW 2: STUDIO EDITOR & INSPECTION                     |
|                                                                         |
|  Header Bar:                                                            |
|  - Back to Directory button                                             |
|  - Quality Score Gauge (0-100) & Status (PASSED / BLOCKED / WARNING)    |
|  - "Validate Quality" & "Approve for Production" (disabled if blocked)  |
|                                                                         |
|  [!] INCOMPLETE DEFINITION WARNING BANNER                               |
|      (Rendered if definition_status === 'INCOMPLETE')                   |
|      "Authoritative SIEM definition missing. Threshold unverified..."    |
|                                                                         |
|  Sub-Navigation Tabs:                                                   |
|  1. [Policy Editor (9 Sections)]                                        |
|     - Rich textareas for each section; version selector; draft save.    |
|  2. [Quality Gates (G1–G8 Diagnostics)]                                 |
|     - Interactive cards for each gate showing PASS/FAIL, score, and     |
|       specific blocking findings (e.g., ARCHETYPE_RELEVANCE_MISMATCH).  |
|  3. [SIEM Semantics & Archetype]                                        |
|     - Authoritative XML ingestion editor, 7-tier provenance breakdown.  |
|  4. [Evidence Contract]                                                 |
|     - Visual table of Core, Conditional, and Optional required fields.  |
|  5. [Simulation Lab]                                                    |
|     - Replay backtesting controls, sample count, regression charts.     |
|  6. [Drift & Continuous Monitoring]                                     |
|     - Drift event timeline, diff viewers, and Acknowledge button.       |
+-------------------------------------------------------------------------+
```

---

## TypeScript Client Extensions (`frontend/src/lib/api.ts`)

The API client includes complete TypeScript interfaces:
- `DetectionSemantics`
- `QualityGateResult`
- `PolicyQualityAssessmentResponse`
- `QualitySummaryResponse`
- `PolicyDriftEvent`
- `BulkQualityAuditJob`

All API client methods include defensive error handling and fallbacks to ensure UI stability.
