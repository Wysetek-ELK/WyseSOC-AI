# Report 03 — Safe Policy Version Governance & Lifecycle Architecture

## 1. Policy Lifecycle Framework

Verdictum AI enforces an immutable, stateful policy versioning lifecycle designed to ensure complete accountability, auditability, and safety before autonomous LLM triage:

```
               ┌───────────┐
               │   DRAFT   │
               └─────┬─────┘
                     │ (Static Validation Gates G1-G8)
                     ▼
               ┌───────────┐
               │ VALIDATED │
               └─────┬─────┘
                     │ (Admin Sign-off & Contract Sync)
                     ▼
               ┌───────────┐
               │ APPROVED  │
               └─────┬─────┘
                     │ (Atomically Assigned as Active Baseline)
                     ▼
               ┌───────────┐
               │  ACTIVE   │
               └─────┬─────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
    ┌───────────┐         ┌───────────┐
    │  REVOKED  │         │ ARCHIVED  │
    └───────────┘         └───────────┘
```

### Lifecycle States
- **DRAFT:** Work-in-progress synthesized or edited prompt specification. Cannot be executed in production.
- **VALIDATED:** Passed static quality gates (G1–G8) with a score ≥70 and 0 blocking issues.
- **APPROVED:** Formally verified and signed off by an authorized SOC Lead or Administrator.
- **ACTIVE:** The single authoritative baseline selected for production inference.
- **REVOKED:** A previously approved policy that was found to be flawed, defective, or untrusted. Permanently ineligible for runtime dispatch, rollback, or silent reactivation.
- **ARCHIVED:** A historical approved baseline replaced by a newer version. Retained for audit and eligible for rollback subject to re-validation.

---

## 2. Revocation Protocol & Audit Traceability

### 2.1 Administrator-Only Revocation Endpoint
- **Method:** `POST /api/prompts/rule/{rule_id}/version/{version_id}/revoke`
- **Authorization:** `require_admin` dependency (strictly enforces Administrator role; SOC Analysts and Viewers receive `403 Forbidden`).
- **Request Body:**
  ```json
  {
    "revocation_reason": "Contains endpoint malware directives incompatible with network scan correlation criteria."
  }
  ```
- **Validation:** Minimum 5 substantive characters required; whitespace-only strings rejected with `400 Bad Request`.

### 2.2 Revocation Side-Effects
When an approved policy is revoked:
1. `PromptVersion.status` transitions to `REVOKED`.
2. `PromptVersion.previous_status` records the prior status (`APPROVED`).
3. `PromptVersion.revoked_at` records the UTC timestamp.
4. `PromptVersion.revoked_by_user_id` records the acting administrator's UUID.
5. `PromptVersion.revocation_reason` persists the mandatory justification.
6. If the revoked version was currently active (`rule_prompt.active_version_id == target_version.id`):
   - `rule_prompt.active_version_id` is atomically cleared (`None`).
   - `rule_prompt.ai_execution_suspended` is set to `True`.
   - `rule_prompt.suspension_reason` records the revocation details.
7. An immutable `AuditLog` entry with action `PROMPT_VERSION_REVOKED` is written to the audit database.

---

## 3. Rollback Guardrails

In `PromptStudioService.rollback_version`:
1. **Revocation Check:** If `source_version.status == "REVOKED"`, rollback is hard-rejected:
   ```python
   raise ValueError(f"Cannot rollback to Version {source_version.version_number}: Policy is REVOKED. Revoked policies cannot be reactivated.")
   ```
2. **Draft Check:** If `source_version.status not in ("APPROVED", "ARCHIVED")`, rollback is hard-rejected:
   ```python
   raise ValueError(f"Cannot rollback to Version {source_version.version_number}: Status is {source_version.status}. Only approved policy versions can be restored.")
   ```
3. **Semantic Mismatch Check:** Candidate is evaluated against `PolicyEligibilityService.detect_semantic_mismatch`. If mismatch is detected, rollback is blocked.
4. **Quality Gates Check:** Candidate must pass `PolicyQualityValidator` gates before a new approved version can be instantiated.

---
*Report Completed on 2026-11-15.*
