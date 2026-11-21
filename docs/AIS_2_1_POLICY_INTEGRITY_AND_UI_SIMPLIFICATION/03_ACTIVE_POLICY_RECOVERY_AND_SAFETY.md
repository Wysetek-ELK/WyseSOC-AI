# Report 03 — Active Policy Recovery Plan, Safety Invariants & Regression Hardening
**Project:** Verdictum AI — Agent Intelligence Studio 2.1 (AIS 2.1)  
**Target Rule:** Heavy TCP Host Scan On Fixed Port (`40498741-ee6b-4a71-9101-0d6d3f77154c`)  
**Date:** November 21, 2026  

---

## 1. Safety Invariants & Guardrails

In strict adherence to the ANTIGRAVITY MASTER PROMPT:
1. **Never Automatically Reactivate or Reapprove Without Authorization:** The system must not silently mutate `active_version_id` during application startup or migration.
2. **Preserve Approval Provenance:** The original `approved_at`, `approved_by_user_id`, and `was_ever_approved = True` attributes on v7 (`d79fb576-c6b9-4f63-9167-3c7a2419b70a`) must be preserved without alteration.
3. **Preserve Draft v8:** Candidate draft v8 must remain intact in `DRAFT` status and must not be promoted or overwritten.
4. **Distinguish Policy States in UI & Backend:**
   - `APPROVED_ACTIVE`: Historically approved and bound as the active production runtime policy.
   - `APPROVED_INACTIVE`: Historically approved, but not currently the active runtime policy.
   - `NO_ACTIVE_BINDING`: No policy version is actively bound to the rule. Execution is paused (awaiting policy binding/approval), not suspended.
   - `RULE_SUSPENDED`: Explicit administrative or automated safety hold (`ai_execution_suspended = True`).
   - `POLICY_REVOKED`: Authoritative revocation recorded with mandatory justification.
   - `DRAFT_CANDIDATE`: Unapproved draft under evaluation.

---

## 2. Non-Destructive Active Binding Recovery Endpoint

To ensure authorized, auditable recovery, an explicit administrator endpoint is introduced:
- **Route:** `POST /api/prompts/rule/{rule_id}/activate-approved/{version_id}`
- **Security:** Requires `Administrator` role via `require_admin`.
- **Preconditions:**
  1. Rule exists and resolves to canonical UUID.
  2. Target version exists and belongs to the rule.
  3. Target version status is `APPROVED` or `was_ever_approved == True`.
  4. Target version is NOT `REVOKED`.
  5. Target version passes semantic compatibility check (`detect_semantic_mismatch == False`).
  6. Explicit confirmation payload provided: `{"confirm": true, "reason": "Restoring verified v7 active baseline"}`.
- **Actions:**
  1. Sets `rule_prompt.active_version_id = target_version.id`.
  2. Resets `rule_prompt.ai_execution_suspended = False` and clears `suspension_reason` if it was an artifact of the lost binding.
  3. Writes append-only audit log: `ACTION = "ACTIVATE_APPROVED_POLICY_VERSION"`.
  4. Preserves all other versions, timestamps, and quality assessment records.

---

## 3. Test Fixture Hardening to Prevent Recurrence

In `backend/tests/test_ais_evaluation_tracking.py`:
1. The test suite is updated to capture the pre-test `active_version_id` and `ai_execution_suspended` state in `setup_test_environment`.
2. In `teardown`, the original `active_version_id` is restored completely before committing.
3. Automated test versions use isolated prefixes and cannot delete or orphan production policy bindings.
4. Tests run against isolated transactional scopes whenever possible.

---

## 4. UI Status Normalization Correction

In `frontend/src/components/compact/AgentIntelligenceStudioOverview.tsx`:
- Fixed `activePolicyLabel`:
  ```typescript
  const activePolicyLabel = activeVersion
    ? (activeVersion.status === "REVOKED"
      ? `V${activeVersion.version_number} — REVOKED`
      : `V${activeVersion.version_number} — ${activeVersion.status}`)
    : (rulePrompt?.ai_execution_suspended
      ? "Suspended (Administrative Hold)"
      : "None (No Active Policy Bound)");
  ```
- Fixed banner rendering:
  - If `rulePrompt?.ai_execution_suspended`: Render red `AI Execution Suspended: {rulePrompt.suspension_reason}`.
  - If `eligibilityData?.reason_code === "POLICY_NOT_APPROVED"` and NOT suspended: Render amber `AI Execution Paused: Awaiting Active Policy Approval`.
  - Explains the exact remediation: *"Click 'Manage Version History' in Settings to bind the approved v7 baseline."*
