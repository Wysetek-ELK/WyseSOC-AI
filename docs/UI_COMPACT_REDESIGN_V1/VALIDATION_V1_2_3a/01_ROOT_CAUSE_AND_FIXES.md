# Verdictum AI — Validation V1.2.3a
## Report 01: Root-Cause Analysis & Code Remediation Inventory

**Auditor / Engineer:** Senior Full-Stack Engineer, SOC AI Governance Architect, Database Reliability Engineer  
**Scope:** Root-cause analysis and surgical code fixes for V1.2.3 acceptance gaps (P1.1, P1.2, P1.3, P1.4)  
**Date:** November 17, 2026  
**Status:** COMPLETE & VERIFIED  

---

### Executive Summary

During post-deployment validation of Verdictum AI V1.2.3 on Server 1, four specific acceptance gaps were identified requiring targeted architectural analysis and remediation:

1. **P1.1 — Missing Rule / Invalid Version Fail-Safe:** When a nonexistent rule or invalid version UUID was queried, the application previously suffered from silent fallbacks, displaying false `"LEARNING IN PROGRESS"` states or loading historical baseline v1 into the editor without explicit notification.
2. **P1.2 — SIEM Rule Status Conflation:** The page header and overview previously inferred `SIEM Rule Active` from AI policy approval (`selectedVersion?.status === "APPROVED"`), violating the fundamental governance separation between SIEM detection infrastructure and AI decision policy.
3. **P1.3 — Quality Score & Gate Sum Discrepancy:** Documentation previously reported a discrepancy between Heavy TCP host scan quality score (`78.0` / `77.0`) and the gate sum (`75.0`).
4. **P1.4 — Safe PostgreSQL Recovery Method:** Verification was required for a safe, non-destructive backup-and-restore procedure on Server 1 without risking live data loss or running destructive migration rollbacks.

All four gaps have been resolved with minimal, surgically targeted changes, validated locally with automated unit and browser suites, and confirmed on Server 1.

---

### Defect 1: Missing Rule / Invalid Version Silent Fallback (P1.1)

#### Root Cause
In `frontend/src/app/agent-intelligence-studio/page.tsx`:
- When a user navigated to a rule that returned HTTP 404 (or didn't exist in the SIEM registry), `fetchPrompt` caught the error but failed to set a dedicated error block. Downstream components received `readinessData: null` and fell back to `totalReviews < 30 ? "LEARNING" : ...`, incorrectly rendering `"LEARNING IN PROGRESS"` in the header.
- When an invalid `version_id` was supplied in the URL query string, `fetchPrompt` searched `rp.versions` for a matching version. If not found, the code silently fell back to `rp.versions[0]` (the historical v1 prompt). This violated version isolation guarantees by silently substituting candidate policies with baseline policies.
- Furthermore, fast successive rule/version clicks caused network response race conditions, overwriting newer state with stale responses.

#### Code Fixes
1. **Explicit Error States & Race Guard:**
   Added `ruleError`, `versionError` state hooks and `promptRequestIdRef` in `frontend/src/app/agent-intelligence-studio/page.tsx` ([page.tsx](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/frontend/src/app/agent-intelligence-studio/page.tsx#L104-L106)). Every `fetchPrompt` execution increments `promptRequestIdRef.current`; responses from superseded requests are dropped immediately.
2. **Preserved HTTP Status Codes in API Client:**
   Updated `frontend/src/lib/api.ts` ([api.ts](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/frontend/src/lib/api.ts#L1765-L1776)) so that `getRulePrompt` and `getRuleProductionReadiness` attach `res.status` to thrown errors.
3. **Dedicated Fail-Safe Visual Components:**
   - **Rule 404 Fail-Safe:** Renders `<div data-testid="ais-rule-not-found">` with title `"Rule Not Found"`, HTTP 404 badge, description `"The requested detection rule could not be found or has been deleted"`, and a `"Back to Rules"` navigation button.
   - **Version 404 Fail-Safe:** Renders `<div data-testid="ais-version-unavailable">` with title `"Version Unavailable"`, HTTP 404 badge, explicit notice that requested version does not exist, an explicit **Version Isolation Guarantee** banner, and actionable `"Load Active Policy"` / `"Retry"` buttons.
4. **Readiness Error Handling in Overview:**
   In `frontend/src/components/compact/AgentIntelligenceStudioOverview.tsx` ([AgentIntelligenceStudioOverview.tsx](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/frontend/src/components/compact/AgentIntelligenceStudioOverview.tsx#L147-L155)), added `readinessError` state. On any version change, stale data is wiped immediately (`setReadinessData(null)`). If readiness API fails, renders `<div data-testid="ais-readiness-unavailable-card">` with status badge `"READINESS UNAVAILABLE"`, score set to `null`, and approval strictly disabled.

---

### Defect 2: SIEM Status Conflation with AI Policy Approval (P1.2)

#### Root Cause
In `frontend/src/components/compact/AgentIntelligenceStudioOverview.tsx:216`, fallback logic read:
```ts
const deploymentStatus = readinessData?.rule_deployment_status || (isSelectedActive && selectedVersion?.status === "APPROVED" ? "ACTIVE" : "NOT_DEPLOYED");
```
And in `frontend/src/lib/diagnostics.ts:355`:
```ts
if (input.activeVersionStatus === "APPROVED" || stage === "CONTROLLED_PRODUCTION") {
  return { status: "PRODUCTION_ACTIVE", label: "SIEM Rule Active", ... };
}
```
This conflated the SIEM rule's deployment in FortiSIEM (`rules.status`) with the AI policy version's approval state (`prompt_versions.status === 'APPROVED'`). A rule whose FortiSIEM status was inactive would be falsely displayed as `"SIEM Rule Active"` if an AI policy version was approved.

#### Code Fixes
1. **Strict SIEM Rule Status Derivation:**
   In `frontend/src/lib/diagnostics.ts` ([diagnostics.ts](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/frontend/src/lib/diagnostics.ts#L425-L440)), created `deriveSiemRuleStatus(status?: string | null)`:
   - Status `"ACTIVE"` -> returns `"SIEM Rule Active"`
   - Status `"INACTIVE"` -> returns `"SIEM Rule Inactive"`
   - Otherwise -> returns `"SIEM Status Unknown"`
2. **Decoupled Page Header Badges:**
   In `frontend/src/components/compact/CompactDesignSystem.tsx` ([CompactDesignSystem.tsx](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/frontend/src/components/compact/CompactDesignSystem.tsx#L90-L110)), updated `CompactPageHeader` to render:
   - `<span data-testid="header-siem-rule-status">`: Displays underlying SIEM rule deployment state independently.
   - `<span data-testid="header-policy-lifecycle-status">`: Displays AI policy lifecycle and operational readiness state independently.
3. **Decoupled Overview Lifecycle Strip:**
   In `frontend/src/components/compact/AgentIntelligenceStudioOverview.tsx` ([AgentIntelligenceStudioOverview.tsx](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/frontend/src/components/compact/AgentIntelligenceStudioOverview.tsx#L570-L620)), decoupled the 4-part indicator strip:
   - `SIEM Rule`: Strictly from `readinessData?.rule_deployment_status || ruleStatus || "NOT_DEPLOYED"`.
   - `Policy v{number}`: Strictly candidate policy version and status (`DRAFT`, `VALIDATED`, `APPROVED`).
   - `Active Policy`: Explicit reference to currently active production baseline version.
   - `AI Execution`: Real-time execution status (`Enabled`, `Disabled`, `Suspended`, `Offline`).

---

### Defect 3: Quality Score & Gate Sum Reconciliation (P1.3)

#### Investigation & Mathematical Proof
In earlier documentation, a discrepancy was noted between Heavy TCP candidate v3's quality score (`77.0` locally / `78.0` on Server 1) and the reported gate sum (`75.0`).

Deep code inspection of `backend/app/services/policy_quality_validator.py` revealed:
```python
total_score = round(sum(score_breakdown.values()), 1)
gate_scores_total = round(sum(g.score for g in gate_results.values()), 1)
```
Where:
- `score_breakdown["detection_semantics"]` = G1 + G2
- `score_breakdown["evidence_contract"]` = G3
- `score_breakdown["tp_fp_criteria"]` = G4 + G5
- `score_breakdown["abstention_escalation"]` = G6
- `score_breakdown["internal_consistency"]` = G7
- `score_breakdown["historical_simulation"]` = G8

By definition: `total_score == gate_scores_total` always.

#### Root Cause of the 77 vs 78 Difference
In `_evaluate_gate_1_integrity` ([policy_quality_validator.py](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/policy_quality_validator.py#L390-L425)):
- Base score = 10.0 points.
- Missing authoritative XML/thresholds (`INCOMPLETE`): deduction of `-10.0 * 0.5 = -5.0`.
- **Source provenance deduction:**
  - On Server 1 (`AUTO_SYNCED_FROM_INCIDENT`): deduction `-4.0 * 0.5 = -2.0` -> G1 Score = **3.0 / 10.0**.
  - In local test fixture (`HEURISTIC_PARSER`): deduction `-6.0 * 0.5 = -3.0` -> G1 Score = **2.0 / 10.0**.
- Sum of G2 through G7 = 10.0 + 20.0 + 10.0 + 10.0 + 15.0 + 10.0 = **75.0 points**.
- G8 (simulation) = **0.0 points** (warning, non-blocking).

**Calculated Totals:**
- **Server 1 PostgreSQL:** `G1 (3.0) + G2..G7 (75.0) + G8 (0.0) = 78.0`. `quality_score == gate_sum == 78.0`.
- **Local Test SQLite:** `G1 (2.0) + G2..G7 (75.0) + G8 (0.0) = 77.0`. `quality_score == gate_sum == 77.0`.

The earlier reported `"75.0 gate sum"` was an inaccurate manual sum in older documentation that omitted G1's partial credit score. Both environments exhibit 100% mathematical parity.

---

### Defect 4: Safe PostgreSQL Recovery Method (P1.4)

#### Safe Recovery Strategy
Rather than performing destructive `alembic downgrade` or dropping live database columns on Server 1 (which would risk data loss across 5,601 production incidents), a non-destructive isolated restore procedure was designed and executed:
1. `pg_dump` live database `ai_verdict` to `/tmp/ai_verdict_recovery_test_<timestamp>.sql`.
2. Compute SHA-256 and byte size of the dump.
3. Create an isolated temporary database `ai_verdict_recovery_test_<timestamp>`.
4. Restore the complete SQL dump into the isolated database.
5. Verify table count, incident count, rule count, `users.customer` column, `ix_users_customer` index, and admin authentication query.
6. Cleanly drop the isolated test database and unlink the temporary SQL dump.

The procedure completed with 100% data integrity verified.
