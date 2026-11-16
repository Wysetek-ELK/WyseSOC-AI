# Verdictum AI — Validation V1.2.2b
## 04: Tenant Isolation and Alternate Endpoint Security

### 1. Security Architecture & Threat Vectors
Verdictum AI operates as a multi-tenant platform where enterprise customers must remain strictly segregated. Two critical disclosure vectors were identified and remediated under V1.2.2b:

1. **Cross-Tenant Horizontal Escalation:**
   An analyst assigned to Tenant Alpha attempting to access incidents, investigation workflows, audit timelines, or reviews belonging to Tenant Beta.
2. **Alternate-Endpoint Blind Review Bypasses:**
   An unreviewed analyst attempting to bypass Blind Review masking on the primary workbench by querying secondary or export endpoints:
   - Investigation Queue (`/api/investigations/queue`)
   - Incident Timeline (`/api/incidents/{id}/timeline`)
   - Direct On-Demand AI Inference (`POST /api/incidents/{id}/ai-verdict`)
   - Actual Outbound LLM Prompt Export (`/api/prompts/actual-prompt/incident/{id}/export`)

---

### 2. Implementation Specifications

#### A. Multi-Tenant Data Model & Auth Scoping
- **Schema Migration:** Added `customer: Mapped[Optional[str]]` to `User` in `backend/app/models/user.py`.
- **Database Column:** Added `customer VARCHAR(128)` to `users` table via startup migration and SQLite schema update.
- **JWT Authentication:** Updated token generator and `TokenPayload` in `backend/app/api/auth.py` and `backend/app/schemas/auth.py` to embed `customer`.
- **Tenant Isolation Enforcement:**
  - `IncidentService.list_incidents_with_rule_summary`: Enforces `Incident.customer.in_([user_customer, "DEFAULT", ""]) | Incident.customer.is_(None)` for non-admin users.
  - `IncidentService.get_incident`: Raises `HTTP 403 Forbidden` with `"Access denied: Incident {id} belongs to customer '{other_inc.customer}', but user is restricted to '{user_customer}'"` on tenant mismatch.
  - `TelemetryTimelineService.get_incident_timeline`: Rejects cross-tenant timeline inspection with `access_denied: True` -> `HTTP 403 Forbidden`.
  - `AnalystReviewService.submit_analyst_review`: Rejects cross-tenant review submissions with `HTTP 403 Forbidden`.
  - `ActualPromptCaptureService.get_prompt_for_incident`: Rejects cross-tenant prompt views and exports with `HTTP 403 Forbidden`.

#### B. Alternate-Endpoint Redaction Controls
For unreviewed analysts within the permitted customer tenant:
1. **Investigation Queue (`/api/investigations/queue`):**
   `ai_validated_verdict` and `ai_trust_score` are sanitized to `None` for unreviewed incidents in `InvestigationService.list_queue`.
2. **Incident Timeline (`/api/incidents/{id}/timeline`):**
   Triage evaluation milestones (e.g., `AGENT_EVALUATED`) redact milestone titles to `"[Hidden - Blind Review]"` until independent analyst review is submitted.
3. **Direct Inference Invocation (`POST /api/incidents/{id}/ai-verdict`):**
   Explicitly gated: unreviewed analysts cannot invoke direct on-demand re-evaluations to obtain immediate model feedback without completing blind triage first (returns `HTTP 403 Forbidden`).
4. **Actual Outbound Prompt Export (`/api/prompts/actual-prompt/incident/{id}/export`):**
   Both JSON and Markdown exports strictly mask `raw_model_response` and `l1_explanation.verdict_returned` as `"[Hidden - Blind Review]"` and set `is_redacted = true`.

---

### 3. Automated Security Verification Results

Automated regression tests in `backend/tests/test_v1_2_2b_security_readiness.py`:
- `test_05_cross_tenant_access_denial`: **PASSED**
  - Incident detail query: `HTTP 403 Forbidden`
  - Timeline query: `HTTP 403 Forbidden`
  - Review submission: `HTTP 403 Forbidden`
  - Actual prompt export: `HTTP 403 Forbidden`
  - Incident list query: Excluded from items (count 0)
- `test_06_alternate_endpoint_and_export_redaction`: **PASSED**
  - Investigation queue: Sanitized to `None`
  - Timeline milestone: Masked as `[Hidden - Blind Review]`
  - Actual prompt export: `is_redacted = true`, `raw_model_response = [Hidden - Blind Review]`
  - Direct inference POST: `HTTP 403 Forbidden`

End-to-End validation scenario:
- `SCN-V122B-09-CROSS-TENANT-DENIAL`: API returned `HTTP 403 Forbidden`; UI rendered zero matching incidents (`Showing 0 of 0 incidents`).
- `SCN-V122B-10-ALTERNATE-ENDPOINT-PROTECTION`: JSON export confirmed redacted; UI rendered masked determinations.
