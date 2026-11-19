# Report 04: Verdictum AI — Manage Policy Version History & Safe Governance

**Platform**: Verdictum AI — Agent Intelligence Studio 2.0  
**Target Rule UUIDs Preserved**:
- `7bd13e89-0828-48e6-8cf5-f3cbf12d438c` (Website access policy violation: Same Source and Destination — Active v2 APPROVED, Candidate v3 DRAFT)
- `40498741-ee6b-4a71-9101-0d6d3f77154c` (Heavy TCP Host Scan On Fixed Port — Active v7 APPROVED, Candidate v8 DRAFT)  
**Status**: COMPLETED & VERIFIED

---

## 1. Governance Architecture & Objectives

The Manage Version History subsystem provides authorized SOC Administrators with full lifecycle management over investigation policy versions while maintaining strict referential integrity, historical audit provenance, and runtime production safeguards:

1. **Visibility & Inspection**: Display all policy versions with their lifecycle status (`APPROVED`, `DRAFT`, `VALIDATED`, `ARCHIVED`, `REVOKED`), author, timestamp, change summaries, and usage dependencies.
2. **Reversible Archival**: Hide obsolete drafts from daily operational selectors without data loss. Archived versions remain fully accessible to administrators in Manage Versions and can be restored at any time.
3. **Safe Deletion Engine**: Prevent accidental or malicious destruction of production baselines. Permanent deletion is permitted **only** for unreferenced, obsolete draft versions after an exhaustive 10-point referential dependency check.
4. **Permanent Active Protection**: Active approved policy versions can **never** be deleted or archived.

---

## 2. PostgreSQL Schema & Alembic Migration

### Migration: `014_policy_version_history_management.py`
To support reversible archival without overloading existing lifecycle status values, three dedicated auditing columns were added to the `prompt_versions` table:
- `archived_at` (`DateTime(timezone=True)`, nullable): Timestamp when the version was archived.
- `archived_by_user_id` (`String(100)`, nullable): Username of the administrator who executed the archival.
- `archival_reason` (`Text`, nullable): Mandatory explanation recorded in compliance audit trails.

### Model Integration (`backend/app/models/prompt.py`)
```python
class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    ...
    # Archival & version history management
    archived_at = Column(DateTime(timezone=True), nullable=True)
    archived_by_user_id = Column(String(100), nullable=True)
    archival_reason = Column(Text, nullable=True)
```

---

## 3. Strict Version Deletion Invariants

| Policy State | Physical Deletion | Reversible Archive | Restore | Invariant Enforcement |
|---|---|---|---|---|
| **Active Approved Version** | **PROHIBITED** | **PROHIBITED** | N/A | Current production baseline binding (`rule_prompts.active_version_id`). Deletion and archival are blocked server-side with HTTP 400. |
| **Historical Approved Version** | **PROHIBITED** (if referenced) | Allowed (if unreferenced) | Allowed | Immutable compliance audit trail. Physical deletion is strictly blocked if referenced by audit, learning, or pilot records. |
| **Draft Version (Referenced)** | **PROHIBITED** | Allowed | Allowed | Blocked from deletion if referenced by simulation runs, quality assessments, or actual LLM prompt captures. |
| **Draft Version (Unreferenced)** | **ALLOWED** | Allowed | Allowed | Eligible for permanent deletion only after explicit administrator typed confirmation (`DELETE v{N}`). |

---

## 4. Multi-Table Referential Dependency Verification

Before any version deletion preview or deletion transaction is executed, `policy_version_governance_service.py` runs `check_version_dependencies()`, verifying all database relationships:

1. **Active Rule Binding Check**: Verifies `rule_prompts.active_version_id != version_id`.
2. **Approved Status Guard**: Verifies `version.status != "APPROVED"` (approved policies must never be deleted).
3. **Foreign Key Child Tables**: Checks `actual_llm_prompt_captures.prompt_version_id`.
4. **Soft String Foreign Keys**: Checks `actual_llm_prompt_captures.policy_version_id == str(version_id)`.
5. **Pilot Verdict References**: Checks `pilot_verdicts.policy_version_id == str(version_id)`.
6. **Historical Evaluation Runs**: Checks `historical_evaluation_runs.policy_version_id == str(version_id)`.
7. **Rule Learning Profiles**: Checks `rule_learning_profiles.active_prompt_version_id == str(version_id)`.
8. **Simulation Lab Records**: Checks `rule_dry_runs` and `simulation_results` for version references.
9. **Production Governance Audit**: Checks `production_governance_records` for promotion sign-offs citing the version.
10. **Audit Log Provenance**: Checks `audit_logs` for historical action references.

If any check returns positive references, `is_eligible_for_deletion` evaluates to `False`, and the exact blocking reasons and dependency counts are returned in the deletion preview.

---

## 5. User Experience & Double-Confirmation Workflows

### Deletion Impact Preview Modal
Clicking `Delete` on an eligible version does not immediately delete it. Instead, the UI calls `GET /rule/{rule_id}/version/{version_id}/deletion-preview`, displaying:
- Rule Name and Version Number
- Current Status and Author
- Detailed dependency counts (FKs, Inferences, Simulations, Learning Profiles)
- Warning that the operation is **permanent and irreversible**
- **Typed Confirmation Requirement**: The administrator must type the exact version phrase `DELETE v{version_number}` into an input field before the destructive button is enabled.

### Bulk Cleanup Workflow
For rules accumulating multiple candidate drafts:
1. Administrator selects drafts via checkboxes.
2. UI displays live counts: `Selected: X | Eligible for Deletion: Y | Protected: Z`.
3. Protected versions (active baselines, approved versions, referenced drafts) are automatically excluded.
4. Bulk modal displays complete impact summary.
5. Administrator must type `PERMANENTLY DELETE` to authorize batch deletion.
6. Server-side transaction deletes only eligible drafts and returns `deleted_count` and `protected_count`.

### Comparison Modal
Administrators can click `Diff` on any version row to compare the full 9 policy sections against the active production baseline side-by-side with color-coded diff highlighting.
