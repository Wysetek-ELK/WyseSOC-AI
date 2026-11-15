# VERDICTUM AI — COMPACT UI/UX REDESIGN 1.0
# 10. Operational Risks, Backend Safety & Compatibility Analysis

**Document Version:** 1.0.0  
**Phase:** Phase 6 — Functional Safety, Governance & Compatibility  
**Auditor:** Principal Enterprise UI/UX Architect & SOC Platform Systems Specialist  
**Safety Mandate:** Zero Backend Changes · Zero DB Migrations · Zero Security Degradation  

---

## 1. Zero Backend & API Modification Guarantee

A foundational mandate of this audit is that **no backend Python services, FastAPI endpoints, SQLite/PostgreSQL database schemas, or API signatures may be modified**. 

The forensic investigation confirmed that:
1. All layout cramps, text clippings, and dead space defects reside **exclusively within the frontend presentation layer** (`frontend/src/`).
2. The current backend APIs in `src/lib/api.ts` provide complete, robust data structures (including 12 detection archetypes, 8 quality gates, 6 readiness stages, dual-server live telemetry, and double-blind masking flags).
3. **No backend API or database migration is required or permitted.** Every improvement will be implemented via frontend React/Tailwind/TypeScript refactoring.

---

## 2. Functional Safety & SOC Governance Requirements

The visual redesign must strictly preserve the following 14 operational capabilities without alteration of their underlying semantics:

| Capability Domain | Preservation Requirement | Safety Mechanism |
|---|---|---|
| **1. Quality Gates (G1–G8)** | G1 (Definition), G2 (Telemetry), G3 (Indicators), G4 (Compilation), G5 (Abstention), G6 (Safety), G7 (Consistency), G8 (Simulation) must calculate identically. | Gate evaluation formulas in `api.ts` and `diagnostics.ts` remain untouched. |
| **2. Production Approval Governance** | Rules with hard blockers or scores < 70 must be strictly blocked from production deployment. | Approval button disabling logic (`!isApprovalEligible`) preserved 100%. |
| **3. Ground Truth Isolation** | Telemetry ingestion must isolate historical closure verdicts from model prompts to prevent data leakage. | `PayloadSanitizationGuard` protections remain completely untouched. |
| **4. Double-Blind Review Mode** | In double-blind mode, historical resolutions and AI proposed verdicts must be masked until analyst submission. | Blind mode masking logic in `IncidentVerdictMatrix.tsx` and `AppContext.tsx` preserved. |
| **5. Canonical Rule Disambiguation** | Triage filtering must never mix incidents across distinct SIEM rules. | Filtering strictly by `exact_rule_id` (`rule_uuid` / `logical_rule_id`) maintained. |
| **6. FortiSIEM Continuous Sync** | Background polling every 180 seconds, checkpoint epoch tracking, and batch pull reconciliation must continue. | Poller triggers and scheduler endpoints in `telemetry-hub` preserved. |
| **7. Inference Provenance Accuracy** | The platform must never misrepresent an offline or mock LLM as a live GPU inference engine. | `formatServer2HealthSummary` and provenance badges retained exactly. |
| **8. Audit Logging & Non-Repudiation** | Policy approvals, version creations, rollbacks, and analyst reviews must produce persistent audit log entries. | All mutating API calls (`api.approvePolicy`, `api.createManualDraft`, etc.) preserved. |
| **9. RBAC & Role Enforcement** | `Administrator`, `SOC Analyst`, and `Read-Only Viewer` permissions must be strictly respected in UI controls. | `canMutate` and role-based disabling logic retained on all action buttons. |
| **10. Simulation Replay Integrity** | Accuracy replay simulations must evaluate against historical datasets using identical statistical metrics. | Precision, recall, and Wilson score calculation structures preserved. |
| **11. Policy Version Immutability** | Approved policy versions must remain immutable; changes must generate new candidate drafts. | Version creation and draft promotion workflows preserved. |
| **12. Policy Revocation & Fallback** | Revoked policies must immediately disengage Local LLM verdict execution and engage safe fallback. | `PolicyEligibilityResponse.is_eligible` checks retained in overview. |
| **13. LLM Prompt Transparency** | The exact captured prompt payload sent between Server 1 and Server 2 must remain inspectable. | `ActualPromptInspectorModal` preserved with full cryptographic verification. |
| **14. Dual-Theme Persistence** | User preference for `obsidian` vs `classic` theme must persist across browser sessions. | `localStorage.getItem("ai_verdict_theme")` logic maintained. |

---

## 3. Operational Risk Analysis & Mitigation Matrix

| Identified Risk | Probability | Severity | Operational Impact | Mitigation Strategy |
|---|---|---|---|---|
| **R-01: Accidental Test Breakage** | Medium | High | Automated CI/CD pipelines fail if DOM structures or test IDs change. | Retain all existing `data-testid` attributes and run `npm test` after every phase. |
| **R-02: Operator Layout Confusion** | Low | Medium | Tier 1 analysts accustomed to legacy 7-tab layout struggle to find advanced sub-tabs. | Retain the `VERDICTUM_COMPACT_UI_ENABLED` rollout toggle in `localStorage`. |
| **R-03: Double-Blind Mask Leakage** | Low | Critical | Compromises scientific validity of analyst ground truth reviews. | Keep masking logic centralized in `AppContext.tsx` and verify with automated tests. |
| **R-04: Accidental CSS Bleed** | Medium | Medium | Removing global CSS overrides disrupts legacy pages not yet refactored. | Execute Phase A cleanly, replace overrides with explicit component classes, and test all 17 routes. |
| **R-05: Sticky Action Column Clipping** | Low | Low | Table horizontal scroll on mobile viewports obscures the sticky column. | Apply `@media (max-width: 768px)` fallback to unstick action column on mobile devices. |

---

## 4. Rollback Plan & Emergency Recovery

In the event that an unexpected regression is detected during deployment:

### 4.1 Client-Side Instant Rollback (Zero Downtime)
- Operators can immediately revert to the legacy 7-tab interface by clicking **"Legacy 7-Tab View"** in the Agent Intelligence Studio header.
- This immediately writes `VERDICTUM_COMPACT_UI_ENABLED = "false"` to `localStorage`, restoring the legacy view without redeploying code.

### 4.2 Git Branch Rollback Procedure
Because all redesign commits are isolated on `feature/compact-ui-redesign-v1`:
```powershell
# 1. Revert to stable baseline commit
git checkout main

# 2. Re-verify clean build
npm run build --prefix frontend

# 3. Re-verify automated tests
npm test --prefix frontend
```
Because no database tables, schemas, or server environments were modified, a Git revert returns the application to its exact baseline state in under 60 seconds with **zero data loss risk**.
