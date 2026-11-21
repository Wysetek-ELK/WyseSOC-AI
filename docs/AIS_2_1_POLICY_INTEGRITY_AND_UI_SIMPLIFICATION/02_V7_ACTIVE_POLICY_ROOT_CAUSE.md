# Report 02 — V7 Active Policy State Root Cause Analysis
**Project:** Verdictum AI — Agent Intelligence Studio 2.1 (AIS 2.1)  
**Target Rule:** Heavy TCP Host Scan On Fixed Port (`40498741-ee6b-4a71-9101-0d6d3f77154c`)  
**Audited Baseline Version:** v7 APPROVED (`was_ever_approved = True`)  
**Candidate Version:** v8 DRAFT  
**Date:** November 21, 2026  

---

## 1. Observed Defect in Production GUI

The production GUI displayed the following contradictory and confusing status indicators:
- Policy version selector: `v7 APPROVED` and `v8 Draft`
- Active version banner: `No Active Version`
- Readiness alert banner: `AI Execution Suspended: POLICY_NOT_APPROVED`
- Header card: `Active Policy: None (Revoked / Suspended)`

Historical engineering reports from AIS 2.0 (dated November 18 and November 20) explicitly recorded that v7 (`d79fb576-c6b9-4f63-9167-3c7a2419b70a`) was validated, passed Quality Gates G1–G7 with a score of 92.0/95.0, and was approved as the active baseline policy.

---

## 2. Root Cause Investigation & Finding

A systematic audit across backend services, test fixtures, and database records revealed **two distinct root causes**:

### Root Cause 1: Test Fixture Side-Effect Corrupting Active Version Binding
In commit `bb04b7a8` and `0e17e3d`, automated tests were implemented in `backend/tests/test_ais_evaluation_tracking.py`.
In `setup_test_environment`:
```python
V7_VERSION_ID = "pv-eval-v7-" + uuid.uuid4().hex[:8]
V8_VERSION_ID = "pv-eval-v8-" + uuid.uuid4().hex[:8]

# Seed temporary versions:
pv7 = PromptVersion(id=V7_VERSION_ID, prompt_id=rp.id, version_number=7, status="APPROVED", ...)
db.add(pv7)
rp.active_version_id = pv7.id  # <-- Overwrote the real active version binding!
await db.commit()
```
And in `teardown`:
```python
await db.execute(delete(PromptVersion).where(PromptVersion.id.in_([V7_VERSION_ID, V8_VERSION_ID])))
await db.commit()
```
**The Defect:** When `pytest` was run against the live database during deployment validation, the test fixture temporarily pointed `rp.active_version_id` to its ephemeral test ID (`pv-eval-v7-...`). In teardown, it deleted `V7_VERSION_ID` from `prompt_versions`, but **failed to restore `rp.active_version_id`** back to the real approved v7 ID (`d79fb576-c6b9-4f63-9167-3c7a2419b70a`).

As a result, `rule_prompts.active_version_id` held an **orphaned foreign reference** to a deleted test ID. When `PromptStudioService.get_rule_prompt()` queried versions:
```python
active_v = None
if prompt.active_version_id and prompt.versions:
    for v in prompt.versions:
        if v.id == prompt.active_version_id:
            active_v = PromptVersionResponse.model_validate(v)
            break
```
Because `prompt.active_version_id` matched none of the real versions in `prompt.versions`, `active_v` resolved to `None`!

### Root Cause 2: Status Normalization & UI Conflation Defects
When `active_version` resolved to `None`:
1. `PolicyEligibilityService.evaluate_eligibility()` evaluated `active_approved_version = None`. It correctly determined that no approved version was active for production triage and returned:
   - `is_eligible = False`
   - `reason_code = "POLICY_NOT_APPROVED"`
   - `explanation = "No approved policy version is active for rule '...'. Triage deferred to human analyst."`
2. **Frontend Mislabeling:**
   In `frontend/src/components/compact/AgentIntelligenceStudioOverview.tsx`:
   - Line 244: When `activeVersion` was null and `eligibilityData?.active_version_number` was null, the UI hardcoded:
     `activePolicyLabel = "None (Revoked / Suspended)"`
   - Line 743: When `!eligibilityData.is_eligible`, the UI rendered:
     `AI Execution Suspended: {eligibilityData.reason_code}`
   Even though `ai_execution_suspended` was `False` and neither v7 nor any active policy was `REVOKED`, the UI erroneously presented the rule as being under **security suspension** or **revocation**!

---

## 3. Authoritative Runtime Verification

| Attribute | Value in Current DB | Authoritative Classification |
| :--- | :--- | :--- |
| **Rule UUID** | `40498741-ee6b-4a71-9101-0d6d3f77154c` | Canonical target rule |
| **Rule Code** | `PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT` | Canonical FortiSIEM rule code |
| **Real Approved v7 ID** | `d79fb576-c6b9-4f63-9167-3c7a2419b70a` | Historically approved baseline (`was_ever_approved = True`) |
| **Real Candidate v8 ID** | `91542f74-63cf-41cb-8a4a-131e549da731` | Valid candidate draft (`status = DRAFT`) |
| **Current `active_version_id`** | Orphaned ID (`pv-eval-v7-...`) or NULL | **Accidental Disconnection Defect** |
| **`ai_execution_suspended`** | `False` (or 0) | **NO security governance suspension exists** |
| **Revocation Status** | Neither v7 nor v8 is REVOKED | **NO authoritative revocation exists** |

### Conclusion
v7 is **Historically approved and legitimately the intended active baseline**, but was **accidentally disconnected** due to a test fixture teardown defect and subsequently mislabeled in the UI due to a status normalization bug.

The historical v7 approval provenance is completely intact and must be preserved.
