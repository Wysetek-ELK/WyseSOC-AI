# Report 05: Verdictum AI — API and RBAC Security Validation

**Platform**: Verdictum AI — Agent Intelligence Studio 2.0  
**Target Rule UUIDs Preserved**:
- `7bd13e89-0828-48e6-8cf5-f3cbf12d438c` (Website access policy violation: Same Source and Destination — Active v2 APPROVED, Candidate v3 DRAFT)
- `40498741-ee6b-4a71-9101-0d6d3f77154c` (Heavy TCP Host Scan On Fixed Port — Active v7 APPROVED, Candidate v8 DRAFT)  
**Status**: COMPLETED & VERIFIED

---

## 1. REST API Contract & Version Governance Endpoints

All new version governance endpoints were implemented in `backend/app/api/prompts.py` using FastAPI, Pydantic schemas, and SQLAlchemy transactional guards:

### 1.1 `GET /api/prompts/rule/{rule_id}/version-history`
- **Description**: Returns all historical versions of a rule with dependency counts, archival flags, and deletion eligibility.
- **Query Params**: `include_archived: bool = True`
- **Response**: `List[PolicyVersionHistoryItem]`
  - Fields: `id`, `version_number`, `status`, `created_at`, `created_by_user_id`, `approved_at`, `approved_by_user_id`, `is_active`, `is_eligible_for_deletion`, `blocking_reasons`, `is_archived`, `archived_at`, `archived_by_user_id`, `archival_reason`, `change_summary`, `reference_counts`.

### 1.2 `GET /api/prompts/rule/{rule_id}/version/{version_id}/deletion-preview`
- **Description**: Evaluates referential integrity and returns an impact preview before any destructive action is taken.
- **Response**: `VersionDeletionPreviewResponse`
  - Fields: `rule_id`, `rule_name`, `version_id`, `version_number`, `status`, `is_active`, `is_eligible_for_deletion`, `blocking_reasons`, `dependencies`, `affected_records_count`, `can_be_archived_instead`, `typed_confirmation_phrase`.

### 1.3 `DELETE /api/prompts/rule/{rule_id}/version/{version_id}`
- **Description**: Safely deletes an unreferenced draft version.
- **Payload**: `VersionDeleteRequest` (`reason: str`, `confirm_phrase: str`)
- **Guards**: Re-validates all 10 dependency checks inside an atomic transaction. Enforces `confirm_phrase == f"DELETE v{version.version_number}"`. Rejects active or approved versions with HTTP 400. Rejects unauthorized users with HTTP 403.

### 1.4 `POST /api/prompts/rule/{rule_id}/version/{version_id}/archive`
- **Description**: Archives a draft or historical version, hiding it from default selectors.
- **Payload**: `VersionArchiveRequest` (`reason: str`)
- **Guards**: Prohibits archival of the active baseline (`rule_prompts.active_version_id`). Updates `status="ARCHIVED"`, sets `archived_at=utcnow()`, `archived_by_user_id=current_user`, and records compliance reason.

### 1.5 `POST /api/prompts/rule/{rule_id}/version/{version_id}/restore`
- **Description**: Restores an archived version back to `DRAFT` status for further editing.
- **Guards**: Resets `status="DRAFT"`, clears archival metadata, and logs an audit entry.

### 1.6 `POST /api/prompts/rule/{rule_id}/versions/bulk-delete`
- **Description**: Deletes multiple eligible obsolete drafts in a single atomic transaction.
- **Payload**: `BulkVersionDeleteRequest` (`version_ids: List[UUID]`, `confirm_phrase: "PERMANENTLY DELETE"`)
- **Guards**: Filters out any active, approved, or referenced versions. Executes physical delete only on eligible drafts. Returns `deleted_count` and `protected_count`.

---

## 2. RBAC & Principle of Least Privilege

| Role | View Version History & Diff | Run Real AI Tests | Double-Blind Review | Archive / Restore Versions | Delete Eligible Drafts | Promote / Approve Policy |
|---|---|---|---|---|---|---|
| **SOC Administrator** | Allowed | Allowed | Allowed | **Allowed** | **Allowed** | **Allowed** |
| **SOC Lead** | Allowed | Allowed | Allowed | Restricted | Restricted | **Allowed** |
| **SOC Analyst** | Allowed | Allowed | **Allowed** | Restricted | Restricted | Restricted |
| **Read-Only Viewer** | Allowed | Restricted | Restricted | **LOCKED OUT** | **LOCKED OUT** | **LOCKED OUT** |

### Viewer Lockout Verification
- **Frontend**: Buttons for `Archive`, `Restore`, `Delete`, `Bulk Delete`, and `Submit Review` are disabled when `isViewer === true`. Hover tooltips explain `Read-Only Viewer cannot modify or delete policy versions`.
- **Backend**: FastAPI dependency `require_admin()` inspects the authenticated JWT session. Any viewer or unauthorized analyst attempting to hit `DELETE` or `POST .../archive` receives `HTTP 403 Forbidden`.

---

## 3. Data Integrity & Anti-Tampering Safeguards

1. **Zero Silent Cascade Deletion**: Deletion logic never cascades to `pilot_verdicts`, `actual_llm_prompt_captures`, `audit_logs`, or `rule_learning_profiles`. Historical AI inference provenance is completely preserved.
2. **Double-Confirmation Protection**: Individual deletions require `DELETE v{N}`; bulk deletions require `PERMANENTLY DELETE`. Empty, mismatched, or automated requests are rejected.
3. **Audit Trail Completeness**: All archival, restoration, and deletion operations record timestamp, actor, IP address, and mandatory compliance justifications in the system audit log.
