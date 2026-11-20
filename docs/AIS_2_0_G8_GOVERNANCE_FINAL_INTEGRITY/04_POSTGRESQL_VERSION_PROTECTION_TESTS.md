# Report 04 — Comprehensive PostgreSQL Version Protection Test Suite
**Project**: Verdictum AI — Agent Intelligence Studio (AIS 2.0)  
**Task**: G8 Governance Integrity, Empirical Metrics & Final Deployment Verification  
**Date**: November 20, 2026  
**Status**: 17 Automated Deletion & Immutability Scenarios Verified  

---

## 1. Executive Summary

This report documents the expanded automated test suite:  
`backend/tests/test_postgresql_version_deletion_integrity.py`.  
The suite exercises 17 comprehensive scenarios covering referential integrity, concurrency row-locking, audit trail immutability, future approval persistence, database rollback safety, and failsafe provenance detection.

---

## 2. Test Execution Matrix (17 Scenarios)

| Test ID | Test Scenario | Description | Target Invariant | Result |
| :---: | :--- | :--- | :--- | :---: |
| **TC-01** | `test_unreferenced_draft_deletion_succeeds` | Safe deletion of obsolete unreferenced candidate draft | Draft and associated draft quality assessments pruned cleanly | **PASS** |
| **TC-02** | `test_active_approved_version_deletion_rejected` | Attempt deletion of active approved baseline | Deletion blocked with `HTTP 400 Bad Request` | **PASS** |
| **TC-03** | `test_historical_approved_version_deletion_rejected` | Attempt deletion of inactive historical approved baseline | Historical approved versions are permanently immutable | **PASS** |
| **TC-04** | `test_archived_approved_version_deletion_rejected` | Transition `APPROVED -> ARCHIVED -> DELETE` | Reversible archival does not strip approval immutability | **PASS** |
| **TC-05** | `test_restored_approved_version_deletion_rejected` | Transition `APPROVED -> ARCHIVED -> RESTORED -> DELETE` | Restored version returns as `APPROVED` (not `DRAFT`); delete blocked | **PASS** |
| **TC-06** | `test_revoked_approved_version_deletion_rejected` | Transition `APPROVED -> REVOKED -> DELETE` | Revoked policy maintains audit accountability; delete blocked | **PASS** |
| **TC-07** | `test_referenced_draft_deletion_rejected` | Draft referenced by `ActualLLMPromptCapture` | Referential integrity blocks deletion if inference capture exists | **PASS** |
| **TC-08** | `test_cross_rule_version_id_mismatch_rejected` | Attempt deletion of Rule B's version under Rule A | Returns `HTTP 404 Not Found` without cross-rule leak | **PASS** |
| **TC-09** | `test_bulk_deletion_excludes_approved_and_referenced_versions` | Bulk cleanup across mixed version array [v1–v5] | Prunes only eligible drafts; protects approved and referenced versions | **PASS** |
| **TC-10** | `test_archive_restore_preserves_approval_status` | Status restoration invariant on approved vs draft | Approved restores as `APPROVED`; draft restores as `DRAFT` | **PASS** |
| **TC-11** | `test_future_approval_flag_persistence_and_deletion_rejection` | Newly authored draft approved in future operation | `was_ever_approved=True` persisted transactionally; subsequent delete blocked | **PASS** |
| **TC-12** | `test_concurrent_approval_versus_deletion_row_locking` | Concurrent race condition: version approved during deletion | Row-level locking detects concurrent approval; delete aborts immediately | **PASS** |
| **TC-13** | `test_concurrent_archive_versus_deletion` | Concurrent race condition: version archived during deletion | Archival does not bypass `was_ever_approved` invariant | **PASS** |
| **TC-14** | `test_duplicate_delete_idempotent_rejection` | Subsequent duplicate delete call on already deleted draft | Returns clean `HTTP 404 Not Found` without 500 error or crash | **PASS** |
| **TC-15** | `test_missing_historical_approval_metadata_failsafe` | Corrupt or missing `was_ever_approved=False` with legacy metadata | Multi-layered provenance detects `previous_status` or `approved_at` and blocks delete | **PASS** |
| **TC-16** | `test_protected_learning_profile_active_version_rejection` | Unapproved draft bound to `RuleLearningProfile.active_prompt_version_id` | Bound to active inference; deletion blocked | **PASS** |
| **TC-17** | `test_protected_policy_drift_event_rejection` | Draft linked to unacknowledged `PolicyDriftEvent` | Active drift event blocks deletion until acknowledged | **PASS** |

---

## 3. Detailed Verification of Advanced Scenarios

### 1. Future Approval Persistence (TC-11)
To ensure that approval immutability is not merely a one-time migration backfill:
- A new candidate draft `v1` was created with `was_ever_approved = False`.
- Approved via `PromptStudioService.approve_version()`.
- Verified that `new_candidate.was_ever_approved` was transactionally set to `True` and committed.
- Attempted deletion via `PolicyVersionGovernanceService.delete_version()`.
- Result: **Rejected with `HTTP 400 Bad Request: Version v1 has been historically approved and is permanently immutable. It cannot be deleted.`**

### 2. Multi-Layered Failsafe Provenance Detection (TC-15)
To protect against database flag corruption or legacy migration gaps:
- A version record was initialized with `was_ever_approved = False` but with `previous_status = "APPROVED"` and `approved_at = datetime.now()`.
- `PolicyVersionGovernanceService.is_version_ever_approved()` evaluated the secondary metadata layers and authoritative audit logs.
- Result: **Evaluated as approved (`True`), preventing deletion.**

### 3. Learning Profile & Drift Event Referential Protection (TC-16 & TC-17)
- In TC-16, an unapproved draft version ID was bound to `RuleLearningProfile.active_prompt_version_id`. The dependency checker verified that active runtime binding prohibits deletion.
- In TC-17, an unapproved draft version was referenced by an unacknowledged `PolicyDriftEvent`. The dependency checker prohibited deletion until the drift event is formally acknowledged.

---

## 4. Test Suite Conclusion
The 17 automated scenarios establish that approved policy versions cannot be physically deleted under any lifecycle transition, concurrency condition, or administrative operation.
