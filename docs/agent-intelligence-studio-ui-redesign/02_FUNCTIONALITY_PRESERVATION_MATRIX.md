# Functionality Preservation Matrix: Agent Intelligence Studio 2.0
**Document ID:** `02_FUNCTIONALITY_PRESERVATION_MATRIX.md`  
**Date:** 2026-11-19  
**System:** Verdictum AI — Agent Intelligence Studio 2.0  
**Guarantee:** Zero Functional Regression across all operations, mutations, queries, permissions, and safeguards

---

## 1. Complete Functional Inventory & Mapping

| Feature / Action | Current Component Location | Underlying API / Action Handler | Redesigned UI Location | Preservation Status | Notes & Safeguards |
|---|---|---|---|---|---|
| **Synthesize Intelligent Draft** | AIS Studio Header & Editor tab | `api.generateIntelligentDraft(ruleId)` | Primary Action Button (Header & Action Strip) | **PRESERVED** | Guarded by `isViewer` (RBAC lockout) and `actionLoading`. |
| **Save Manual Draft** | Advanced -> Policy Editor | `api.createManualDraft(ruleId, payload)` | Policy Editor Workspace footer | **PRESERVED** | Preserves prompt text, reasoning schema, questions builder, strategy. |
| **Validate Quality Gates (G1–G8)** | Overview & Advanced -> Quality | `api.validatePolicyQuality(ruleId, versionId)` | Overview Action Strip & Quality Workspace | **PRESERVED** | Re-computes all 8 deterministic gates; updates quality score and blocking issues. |
| **Preview Quality (Dry)** | Studio header & Editor tab | `api.previewPolicyQuality(ruleId, versionId)` | Quality Workspace preview button | **PRESERVED** | Non-mutating fast preview calculation. |
| **Run Simulation Regression** | Overview & Advanced -> Simulation | `api.evaluatePolicySimulation(ruleId, versionId)` | Overview Action Strip & Simulation Workspace | **PRESERVED** | Guarded by `isViewer`. Evaluates policy on historical incident replay batch. |
| **Approve Policy Version** | Studio Header & Overview Action Strip | `api.approvePromptVersion(ruleId, versionId)` | Studio Header & Overview Primary Action | **PRESERVED** | Strictly requires `isApprovalEligible` (`passedGatesCount === 8`, `reviews >= 30`, `!hasHardGateFailure`, `!isViewer`). |
| **Rollback to Prior Version** | Advanced -> History & Rollback Modal | `api.rollbackPromptVersion(ruleId, targetVerId)` | Version History Drawer & Modal | **PRESERVED** | Rollback confirmation modal; preserves historical version lineage. |
| **Revoke Policy Version** | Advanced -> History & Revoke Modal | `api.revokePromptVersion(ruleId, verId, reason)` | Version History Drawer & Revoke Modal | **PRESERVED** | Requires mandatory reason string; updates status to `REVOKED`. |
| **View Actual LLM Prompt (Table)** | Table View Top Action Bar | `ActualPromptInspectorModal` | Table View Header Action Menu | **PRESERVED** | Reads exact captured prompt from Server 1 -> Server 2 LLM. |
| **View Actual LLM Prompt (Row)** | Table View Action Column | `ActualPromptInspectorModal` | Table View Sticky Row Action Menu | **PRESERVED** | Rule-scoped prompt inspection modal. |
| **View Actual LLM Prompt (Studio)**| Overview Action Strip | `ActualPromptInspectorModal` | Overview Secondary Action & Header Menu | **PRESERVED** | Scoped to active rule & selected policy version. |
| **Preview Prompt (Template)** | Advanced -> Policy Editor | Local state / Prompt preview toggle | Policy Editor Toolbar | **PRESERVED** | Distinguishes static template preview from live executed prompt. |
| **Acknowledge Drift Events** | Advanced -> Drift tab | `api.acknowledgeDriftEvents(ruleId)` | Drift & Monitoring Workspace | **PRESERVED** | Clears active drift alerts; records acknowledgment timestamp. |
| **Start Bulk Quality Audit** | Table View Top Action Bar | `api.startBulkQualityAudit()` | Table View Header More Actions dropdown | **PRESERVED** | Chunked in 100s; non-mutating batch audit across all SIEM rules. |
| **Export All Rule Prompts (JSON)** | Table View Top Action Bar | `api.exportRulePrompts("json")` | Table View Header More Actions dropdown | **PRESERVED** | Downloads `rule_prompts_export_{timestamp}.json`. |
| **Export All Rule Prompts (MD)** | Table View Top Action Bar | `api.exportRulePrompts("markdown")` | Table View Header More Actions dropdown | **PRESERVED** | Downloads `rule_prompts_export_{timestamp}.md`. |
| **Export Single Rule Prompt (JSON)**| Table View Row Action | `api.exportSingleRulePrompt(ruleId, "json")`| Row More Actions Menu & Header | **PRESERVED** | Scoped single rule download. |
| **Export Single Rule Prompt (MD)**| Table View Row Action | `api.exportSingleRulePrompt(ruleId, "markdown")`| Row More Actions Menu & Header | **PRESERVED** | Scoped single rule Markdown download. |
| **Export Quality Gates (JSON)** | Advanced -> Quality tab | `buildQualityGatesExportFile(..., "json")` | Quality Gates Header Export Menu | **PRESERVED** | Deterministic filename; exports G1–G8, digests, provenance. |
| **Export Quality Gates (MD)** | Advanced -> Quality tab | `buildQualityGatesExportFile(..., "markdown")`| Quality Gates Header Export Menu | **PRESERVED** | Clean Markdown report with gate tables and recommendations. |
| **Export Quality Gates (CSV)** | Advanced -> Quality tab | `buildQualityGatesExportFile(..., "csv")` | Quality Gates Header Export Menu | **PRESERVED** | Formula injection protected (CWE-1236) CSV output. |
| **Switch Detection Rule** | Studio Header Dropdown | `handleSwitchRuleInStudio(ruleId)` | Studio Header Rule Selector | **PRESERVED** | Updates URL `rule_id` query param without page reload. |
| **Switch Policy Version** | Studio Header / History | `handleSelectVersion(versionId)` | Studio Header Version Selector & History Drawer| **PRESERVED** | Updates URL `version_id`; immediately clears stale readiness data. |
| **Filter by Search Text** | Table View Toolbar | `searchFilter` state filter | Table View Search Bar | **PRESERVED** | Filters by rule name, event type, data source, archetype. |
| **Filter by Archetype** | Table View Toolbar | `archetypeFilter` state filter | Table View Filter Row | **PRESERVED** | Select all 12 archetypes. |
| **Filter by Completeness** | Table View Toolbar | `completenessFilter` state filter | Table View Filter Row | **PRESERVED** | VERIFIED vs INCOMPLETE. |
| **Filter by Severity** | Table View Toolbar | `severityFilter` state filter | Table View Filter Row | **PRESERVED** | CRITICAL, HIGH, MEDIUM, LOW. |
| **Filter by Baseline Status** | Table View Toolbar | `baselineFilter` state filter | Table View Filter Row | **PRESERVED** | APPROVED, DRAFT, NO_BASELINE. |
| **Filter by Production Readiness**| Table View Toolbar | `readinessFilter` state filter | Table View Filter Row | **PRESERVED** | READY, PILOT, INSUFFICIENT, BLOCKED, UNAVAILABLE. |
| **Table Pagination** | Table View Bottom | `page` state + `pageSize = 15` | Table View Bottom Pagination Bar | **PRESERVED** | Prev/Next page navigation and counter. |
| **Open Studio for Rule** | Table Row Click / Button | `handleOpenStudioForRule(ruleId)` | Table Row Click & Open Studio Button | **PRESERVED** | Navigates from Table to Studio view. |
| **Back to Rules Table** | Studio Header Back Button | `handleBackToTable()` | Studio Header "Rules List" Back Button | **PRESERVED** | Restores table view without losing filters. |
| **Double-Blind Review Queue** | Review & Learning -> Blind Review | `api.getPendingDoubleBlindReviews(ruleId)` | Review & Learning Workbench | **PRESERVED** | Conceals AI predicted verdict from analyst during determination. |
| **Submit Analyst Review** | Review & Learning -> Submit Review | `api.submitAnalystReview(incidentId, payload)`| Review & Learning Review Card | **PRESERVED** | Records TP/FP/NE ground-truth determination; updates accuracy. |
| **Adjudicate Disagreements** | Review & Learning -> Adjudicate | `api.adjudicateAnalystReview(...)` | Review & Learning Adjudication Workbench | **PRESERVED** | Resolves split verdicts; updates confusion matrix. |
| **Request Promotion** | Review & Learning -> Promote | `api.requestRulePromotion(...)` | Review & Learning Promotion Panel | **PRESERVED** | Strictly guarded by minimum verified review threshold. |
| **Decide Promotion (Approve/Reject)**| Review & Learning -> Decide | `api.decideRulePromotion(...)` | Review & Learning Governance Panel | **PRESERVED** | Admin authorization only; logs audit evidence. |
| **Emergency Kill Switch** | Review & Learning -> Kill Switch | `api.emergencyDisableAutomation(...)` | Review & Learning Safety Controls | **PRESERVED** | Destructive confirmation dialog; disables autonomous execution. |
| **Suggest Prompt Improvement** | Review & Learning -> Feedback | `api.suggestPromptImprovement(...)` | Review & Learning RAG Panel | **PRESERVED** | Synthesizes recommendations from analyst review notes. |
| **Toggle Legacy / Compact View** | Studio Header View Toggle | `setCompactUi(toggle)` + `localStorage` | Studio Header View Settings Menu | **PRESERVED** | Preserves user layout preference. |

---

## 2. API Endpoint Verification Summary

All 21 backend API contracts consumed by the Agent Intelligence Studio frontend remain 100% intact:
1. `GET /api/rules`
2. `GET /api/rules/prompts/summary`
3. `GET /api/policy-quality/summary`
4. `GET /api/rules/{id}/prompt`
5. `GET /api/rules/{id}/intelligence`
6. `GET /api/rules/{id}/drift`
7. `GET /api/rules/{id}/learning-profile`
8. `GET /api/rules/{id}/production-readiness`
9. `GET /api/rules/{id}/policy-eligibility`
10. `POST /api/rules/{id}/prompt/draft/intelligent`
11. `POST /api/rules/{id}/prompt/draft/manual`
12. `POST /api/rules/{id}/quality/validate`
13. `POST /api/rules/{id}/quality/preview`
14. `POST /api/rules/{id}/prompt/simulation`
15. `POST /api/rules/{id}/prompt/approve`
16. `POST /api/rules/{id}/prompt/rollback`
17. `POST /api/rules/{id}/prompt/revoke`
18. `POST /api/rules/{id}/drift/acknowledge`
19. `POST /api/rules/prompts/bulk-audit`
20. `GET /api/rules/prompts/export`
21. `GET /api/rules/{id}/prompt/export`

No payload schemas, parameter names, or HTTP verbs have been altered.

---
*Matrix verified. Proceed to UI/UX Design Specification (`03_UI_UX_DESIGN_SPECIFICATION.md`).*
