# Verdictum AI — Backend API Contracts Specification

**Document:** `13_BACKEND_API_CONTRACTS.md`  
**Platform:** Verdictum AI / WyseSOC AI  
**Scope:** RESTful API Contracts, Request/Response Schemas, Idempotency & Error Codes  
**Status:** DRAFTED & VERIFIED  

---

## 1. Overview & Architectural Conventions

All new and extended endpoints conform to the existing Verdictum AI API design standards:
- **Base Route:** `/api/v1`
- **Authentication:** Bearer JWT token validated via `deps.get_current_active_user`.
- **Tenant Scoping:** All operations scoped to the user's active tenant (`customer` attribute).
- **Error Format:** Standard RFC 7807 problem details with `detail` message and typed error codes.
- **Idempotency:** Mutations accept optional `Idempotency-Key` headers to prevent duplicate operations.

---

## 2. API Endpoint Matrix

| Method | Endpoint | Description | Role Required |
|---|---|---|---|
| `GET` | `/api/v1/learning/rules` | List rule learning profiles with metrics and lifecycle states | Analyst, Senior, Manager, Admin |
| `GET` | `/api/v1/learning/rules/{rule_id}` | Get detailed learning profile, error taxonomy, and metrics | Analyst, Senior, Manager, Admin |
| `POST` | `/api/v1/learning/rules/{rule_id}/transition` | Manually transition lifecycle state (e.g. suspend) | SOC Manager, Admin |
| `GET` | `/api/v1/reviews/pending` | Fetch pending double-blind incident review queue | Analyst, Senior, Manager, Admin |
| `POST` | `/api/v1/reviews/{incident_id}/submit` | Submit independent analyst verdict (blind mode supported) | Analyst, Senior, Manager, Admin |
| `GET` | `/api/v1/reviews/{incident_id}/history` | Get immutable history of all analyst reviews for an incident | Analyst, Senior, Manager, Admin |
| `POST` | `/api/v1/reviews/{incident_id}/adjudicate` | L2 / Manager binding dispute adjudication | Senior Analyst, SOC Manager, Admin |
| `POST` | `/api/v1/learning/prompts/candidate` | Create a candidate prompt template based on error feedback | SOC Manager, Admin |
| `POST` | `/api/v1/learning/prompts/evaluate` | Trigger historical simulation replay on a candidate prompt | SOC Manager, Admin |
| `POST` | `/api/v1/governance/promotion/request` | Submit a formal rule lifecycle promotion request | Senior Analyst, SOC Manager |
| `POST` | `/api/v1/governance/promotion/decide` | Approve or reject a promotion request | SOC Manager, Admin |
| `POST` | `/api/v1/governance/automation/emergency-disable` | Global kill-switch disabling all automated closures | SOC Manager, Admin |
| `GET` | `/api/v1/governance/automation/audits` | Query automated closure audit records | Senior Analyst, SOC Manager, Admin |

---

## 3. Detailed Request & Response Contracts

### 3.1 List Rule Learning Profiles
- **Route:** `GET /api/v1/learning/rules`
- **Query Params:** `lifecycle_stage` (optional), `customer` (optional), `limit` (default: 50), `offset` (default: 0).
- **Response `200 OK`:**
  ```json
  {
    "items": [
      {
        "id": "prof-9839fa49-40ac-4676-abcc-4c5581ae9e09",
        "rule_id": "PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST",
        "name": "Website access policy violation: Same Source and Same Destination",
        "customer": "DEFAULT",
        "primary_archetype": "POLICY_VIOLATION",
        "lifecycle_stage": "SUPERVISED_PILOT",
        "total_incidents_processed": 542,
        "total_analyst_reviews": 68,
        "verified_tp_count": 18,
        "verified_fp_count": 50,
        "empirical_accuracy": 0.9412,
        "fp_precision": 0.9804,
        "wilson_lower_bound": 0.8955,
        "tp_recall": 0.9444,
        "active_prompt_version": 3,
        "promotion_eligible": false,
        "eligibility_reasons": ["Wilson 95% lower bound (89.6%) below production threshold (96.0%)"]
      }
    ],
    "total": 1,
    "limit": 50,
    "offset": 0
  }
  ```

### 3.2 Submit Independent Analyst Review
- **Route:** `POST /api/v1/reviews/{incident_id}/submit`
- **Request Body:**
  ```json
  {
    "analyst_verdict": "FALSE_POSITIVE",
    "analyst_notes": "Verified source 192.0.2.48 accessing external Giphy media CDN. Firewall properly blocked dropped connection. Benign user web surfing, not an attack.",
    "correction_reason": "POLICY_EXCEPTION",
    "evidence_references": ["EVID-01", "EVID-04"],
    "blind_mode_active": true
  }
  ```
- **Response `200 OK`:**
  ```json
  {
    "review_id": "rev-68ec2d89-d8d3-4c5c-9aec-ec6ea77a1eff",
    "incident_id": "176061",
    "analyst_verdict": "FALSE_POSITIVE",
    "revealed_ai_verdict": "REQUIRES_ATTENTION",
    "comparison_outcome": "ANALYST_RESOLVED_ABSTENTION",
    "disagreement_reason": "AI safely abstained due to missing HTTP method; analyst confirmed benign from raw domain.",
    "ground_truth_status": "VERIFIED_FP",
    "review_version": 1,
    "reviewed_at": "2026-11-12T16:45:00Z"
  }
  ```

### 3.3 Rule Lifecycle Promotion Request & Decision
- **Route:** `POST /api/v1/governance/promotion/decide`
- **Request Body:**
  ```json
  {
    "request_id": "req-prom-9839fa49",
    "action": "APPROVED",
    "decision_notes": "Reviewed 100+ verified test cases; statistical lower bound exceeds 96%. Approved for Controlled Production.",
    "approval_signature": "SIG-SOCMGR-AMIT-20261112"
  }
  ```
- **Response `200 OK`:**
  ```json
  {
    "request_id": "req-prom-9839fa49",
    "status": "APPROVED",
    "rule_id": "PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST",
    "previous_stage": "SUPERVISED_PILOT",
    "new_stage": "CONTROLLED_PRODUCTION",
    "approved_at": "2026-11-12T16:50:00Z",
    "automation_policy_created": true
  }
  ```

### 3.4 Error Codes & RFC 7807 Responses
- `400 Bad Request`: `INVALID_TRANSITION_STATE`, `INSUFFICIENT_SAMPLE_SIZE`.
- `401 Unauthorized`: `TOKEN_EXPIRED`, `AUTHENTICATION_REQUIRED`.
- `403 Forbidden`: `INSUFFICIENT_PERMISSIONS`, `CROSS_TENANT_ACCESS_DENIED`.
- `404 Not Found`: `RULE_NOT_FOUND`, `INCIDENT_NOT_FOUND`.
- `409 Conflict`: `DISPUTED_REVIEW_EXISTS`, `DUPLICATE_PROMOTION_REQUEST`.
- `503 Service Unavailable`: `FORTISIEM_OFFLINE`, `INFERENCE_CIRCUIT_BREAKER_OPEN`.

