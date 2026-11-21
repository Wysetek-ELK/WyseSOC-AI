# Report 04 — AI Evaluation Tracking Zero-Incident Root Cause Analysis
**Project:** Verdictum AI — Agent Intelligence Studio 2.1 (AIS 2.1)  
**Target Rule:** Heavy TCP Host Scan On Fixed Port (`40498741-ee6b-4a71-9101-0d6d3f77154c`)  
**Date:** November 21, 2026  

---

## 1. Observed Defect in Production GUI

The GUI showed:
- `32 analyst reviews`
- `32 verified ground-truth records`
- `5 pending analyst reviews`
- `AI Evaluation Tracking: 0 total incidents`
- `0 decisive`, `0 abstained`, `0 rejected`, `0 missing inference`

Despite 37 incidents existing in PostgreSQL for this rule (32 reviewed + 5 pending), the AI Evaluation Tracking view reported an entirely empty inventory.

---

## 2. Root Cause Analysis

Tracing the end-to-end request lifecycle:
`Frontend Request -> GET /api/ais/rules/{rule_uuid}/evaluation-status -> AisEvaluationService.get_rule_evaluation_tracking_overview -> Database Query -> Status Resolution -> Response -> GUI Table`

revealed **two root causes**:

### Root Cause 1: Tenant Scope Filter Discrepancy
In `backend/app/services/ais_evaluation_service.py`:
```python
user_cust = getattr(current_user, "customer", None)
effective_customer = user_cust or customer or "DEFAULT"
if effective_customer and effective_customer.upper() not in ("ALL", "GLOBAL"):
    if effective_customer == "DEFAULT":
        cust_filter = or_(
            Incident.customer == "DEFAULT",
            Incident.customer == "",
            Incident.customer.is_(None)
        )
    else:
        cust_filter = (Incident.customer == effective_customer)
    inc_stmt = inc_stmt.where(cust_filter)
```
1. In the database, the real 69 incidents for Heavy TCP Host Scan belong to tenants **`GDC_NOC`** (41 incidents) and **`Demo-SOC`** (28 incidents), as established in historical telemetry audits.
2. In `AnalystReviewService.get_pending_reviews`:
   ```python
   effective_customer = customer or (
       getattr(current_user, "customer", None)
       if getattr(current_user, "role", "") not in ("Administrator", "SuperAdmin", "SOC_Manager")
       else None
   )
   ```
   For administrators and SOC managers, `effective_customer` was set to `None`, which **bypassed customer filtering** and returned all 5 pending and 32 reviewed incidents across `GDC_NOC` and `Demo-SOC`.
3. In `AisEvaluationService`, however, if `customer` was omitted by the frontend, `effective_customer` defaulted to `"DEFAULT"` **even for administrators**!
4. The SQL query added `WHERE customer in ('DEFAULT', '', NULL)`. Since all 37 incidents belonged to `GDC_NOC` or `Demo-SOC`, **100% of the incidents were filtered out**.

### Root Cause 2: Dependency on Version ID When Active Version Binding Was Orphaned
When `selectedVersionId` in the frontend pointed to the orphaned test ID (or was undefined), `AisEvaluationService.resolve_target_policy_version()` could not find a matching `PromptVersion`.
While the query logic did not throw a 500 error, the frontend received `items: []` and rendered 0 incidents without diagnostic feedback.

---

## 3. Remediation & Implementation

1. **Role-Aware Tenant Scoping:**
   In `AisEvaluationService.get_rule_evaluation_tracking_overview`:
   - If `current_user` is an `Administrator`, `SuperAdmin`, or `SOC_Manager` and `customer` is not explicitly passed (or is `"ALL"`):
     Do NOT restrict the query to `customer == 'DEFAULT'`. Retrieve all scoped incidents for the rule across authorized tenants.
   - For tenant-restricted users, continue strictly enforcing tenant isolation.
2. **Canonical Rule Matching:**
   Use `resolve_canonical_rule()` and `build_rule_incident_sql_filter()` to guarantee identical incident discovery across `IncidentService`, `PolicySimulationService`, and `AisEvaluationService`.
3. **Decouple Version Binding from Incident Inventory:**
   If no policy version is active, `resolve_target_policy_version()` falls back to the requested version or latest version for evaluation history display, but the incident inventory is **always loaded**.
4. **Error State Handling:**
   If an API failure occurs, never render `0 incidents`. Render `Evaluation data unavailable — Retry` with diagnostic details.
