# 09. POLICY LIFECYCLE AND GOVERNANCE

## Overview

Policy governance in Agent Intelligence Studio 2.0 enforces non-negotiable security controls:
- **Zero Direct Pushes:** Code and policy promotions are governed.
- **Role-Based Access Control (RBAC):** Only authenticated `SOC_LEAD` or `ADMIN` roles can approve production policies. Regular analysts cannot approve drafts.
- **Atomic Evidence Contract Activation:** Approving a policy version atomically transitions its associated Evidence Contract from `DRAFT` to `APPROVED`.
- **Immutable Version Lineage:** Drafts and approved versions are preserved with full audit logs and SHA-256 HMAC integrity.
- **Non-Destructive Rollback:** Rolling back to a prior version creates a new active version entry, preserving complete history.

---

## State Transition Diagram

```text
                  +---------------------------+
                  |  INGEST / ANALYZE RULE    |
                  +---------------------------+
                                |
                                v
                  +---------------------------+
                  |    GENERATE DRAFT (v1)    | <-----------+
                  |      (Status: DRAFT)      |             |
                  +---------------------------+             |
                                |                           |
                                v                           |
                  +---------------------------+             |
                  |  POLICY QUALITY VALIDATOR |             |
                  |     (Gates G1 to G8)      |             |
                  +---------------------------+             |
                     /                     \                |
           [FAILED] /                       \ [PASSED]      |
                   v                         v              |
       +-----------------------+   +-------------------+    |
       |     REWORK DRAFT      |   |  SIMULATION LAB   |    |
       | (approval_eligible=F) |   |  HISTORICAL TEST  |    |
       +-----------------------+   +-------------------+    |
                                             |              |
                                   [PASSED / WAIVED]        |
                                             |              |
                                             v              |
                                   +-------------------+    |
                                   |  SOC LEAD REVIEW  |    |
                                   |   (RBAC Gated)    |    |
                                   +-------------------+    |
                                      /             \       |
                            [REJECT] /               \ [APPROVE]
                                    v                 v     |
                        +----------------+  +---------------------+
                        | ARCHIVED DRAFT |  | ACTIVE POLICY (v1)  |
                        +----------------+  |  (Status: APPROVED) |
                                            +---------------------+
                                                       |
                                               [RULE DRIFT DETECTED]
                                                       |
                                                       v
                                            +---------------------+
                                            | CREATE DRAFT (v2)   |
                                            +---------------------+
```

---

## Atomic Contract Synchronization

In `AgentPolicyEngine.approve_version()` (`backend/app/services/prompt_studio_service.py`):
1. **Quality Pre-Check:** The engine runs `PolicyQualityValidator.validate_policy()`. If `approval_eligible` is `False`, the method raises an `HTTPException(400, "Policy cannot be approved: quality gates failed.")`.
2. **Version Promotion:** The target `PromptVersion` record status is set to `APPROVED`, `approved_by` is set to the authenticated user ID, and `approved_at` is set to UTC now.
3. **Evidence Contract Synchronization:** The system locates the associated `RuleEvidenceContract` record for this rule. Its status is updated from `DRAFT` to `APPROVED` within the **same atomic database transaction**.
4. **Audit Event Generation:** An immutable audit record is committed via `AuditService.log_event()` with SHA-256 HMAC signature.

---

## Non-Destructive Rollback Mechanics

When a SOC Lead triggers `rollback_version(rule_id, target_version_number)`:
1. The target historical version's content (all 9 sections) is retrieved.
2. A **new** version increment ($N+1$) is created containing the identical text of the rollback target.
3. The new version is immediately marked `APPROVED`.
4. The historical record is untouched, preserving an unbroken chronological record of all policy states.
