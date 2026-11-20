# Phase 7: Security, Double-Blind Protection & RBAC

## 1. Double-Blind Review Protection Architecture

To ensure scientific integrity during SOC analyst evaluation of the AI model, double-blind review must be enforced server-side. Omitting fields in the frontend alone is insufficient because network inspection could reveal the AI prediction.

### Server-Side Masking Rules:
In `backend/app/services/ais_evaluation_service.py`:
- Before an analyst submits a review for an incident:
  - If user is not `ADMIN`:
    - `raw_verdict` $\rightarrow$ `"[Hidden - Blind Review]"`
    - `effective_verdict` $\rightarrow$ `"[Hidden - Blind Review]"`
    - `confidence` $\rightarrow$ `0.0`
    - `ai_reasoning` $\rightarrow$ `"[Hidden - Blind Review]"`
    - `comparison_outcome` $\rightarrow$ `"[Pending Analyst Review]"`
  - Once the analyst records a verdict in `analyst_verdict_reviews`, the server unmasks the fields on subsequent reads.

---

## 2. Role-Based Access Control (RBAC) Matrix

| Action / Capability | `ANALYST` | `ADMIN` | `VIEWER` | Enforcing Layer |
|---|---|---|---|---|
| View Double-Blind Review Queue | Yes (Masked) | Yes (Unmasked) | Yes (Masked) | Backend API & UI |
| Switch to AI Evaluation Tracking View | No | Yes | No | UI Mode Toggle |
| Inspect Evaluation Details & Reasoning | Only after review | Yes (Always) | Only after review | Backend & Modal |
| Run Single AI Test | Yes | Yes | No | Backend API |
| Trigger Controlled Batch Inference | **Denied (403)** | **Allowed** | **Denied (403)** | Backend Endpoint |
| Cancel Batch Inference | **Denied (403)** | **Allowed** | **Denied (403)** | Backend Endpoint |
| Export Evaluation Audit Log | No | Yes | No | Backend API |

---

## 3. Multi-Tenant Isolation
Every evaluation query is scoped by `tenant_id` extracted from the authenticated user's JWT session.
- Incidents belonging to Tenant A can never be evaluated, listed, or aggregated under Tenant B.
- All database queries join on `incidents.tenant_id == current_user.tenant_id`.
- Test Case 16 (`test_16_tenant_isolation_enforced`) asserts that cross-tenant queries return 0 results.
