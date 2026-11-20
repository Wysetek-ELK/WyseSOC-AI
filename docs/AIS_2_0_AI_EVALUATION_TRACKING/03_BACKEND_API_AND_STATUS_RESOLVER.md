# Phase 3: Backend API & Status Resolver Implementation

## 1. Overview
The backend implementation introduces `AisEvaluationService` and registers RESTful endpoints in `backend/app/api/ais_evaluation.py`. All endpoints enforce tenant isolation, role-based access control (RBAC), and double-blind masking.

---

## 2. API Endpoints

### 2.1 List & Summary Endpoint
- **Route:** `GET /api/ais/rules/{rule_uuid}/evaluation-status`
- **Alternative:** `GET /api/v1/ais/rules/{rule_uuid}/evaluation-status`
- **Parameters:**
  - `rule_uuid` (path, UUID): Target detection rule.
  - `policy_version_id` (query, optional): UUID of prompt version.
  - `policy_version_number` (query, optional): Version integer (e.g. 7 or 8).
  - `status` (query, optional): Filter by `NOT_EVALUATED`, `EVALUATED_DECISIVE`, `ABSTAINED`, etc.
  - `search` (query, optional): Substring search against `incident_id`.
  - `start_date` / `end_date` (query, optional): ISO datetime window.
  - `limit` (query, default 50): Page size.
  - `offset` (query, default 0): Offset for pagination.
- **Response Structure:**
  - `summary`: Aggregate metrics (`total_incidents`, `not_evaluated`, `evaluated_decisive`, `abstained`, `validation_rejected`, `evaluation_failed`, `queued`, `running`, `mock_only_count`, `matched_verified_analyst_reviews`, `eligible_decisive_comparisons`, `missing_evaluations_among_reviewed`).
  - `items`: Array of `AisEvaluationItem` objects with evaluation metadata.
  - `total_items`: Total matching count.
  - `policy_version`: Information on resolved policy.

### 2.2 History Endpoint
- **Route:** `GET /api/ais/incidents/{incident_id}/evaluation-history`
- **Parameters:**
  - `incident_id` (path, string): Incident identifier (e.g., `INC-2026-0001`).
  - `policy_version_number` (query, optional): Filter history by specific version.
- **Response Structure:**
  - `incident_id`: Incident ID.
  - `history_count`: Number of historical attempts.
  - `latest_status`: Most recent canonical status.
  - `history`: Chronologically ordered array of evaluation attempts.

### 2.3 Controlled Batch Inference Endpoint
- **Route:** `POST /api/ais/rules/{rule_uuid}/evaluate-missing-batch`
- **RBAC:** Requires `ADMIN` role.
- **Body:**
  ```json
  {
    "policy_version_id": "c1f1e9c2-...",
    "policy_version_number": 7,
    "max_incidents": 50,
    "concurrency_limit": 2,
    "dry_run": false
  }
  ```
- **Response Structure:**
  - `queued_count`: Number of tasks enqueued.
  - `skipped_count`: Incidents already evaluated under this version.
  - `eligible_incident_ids`: Array of enqueued incident IDs.
  - `batch_id`: Unique tracking ID for the batch.
  - `status`: `QUEUED` or `DRY_RUN_COMPLETE`.

---

## 3. Double-Blind Review Masking Architecture
When an analyst has not completed an independent review for an incident, the resolver dynamically masks all AI outputs:
- `raw_verdict`: `"[Hidden - Blind Review]"`
- `effective_verdict`: `"[Hidden - Blind Review]"`
- `confidence`: `0.0`
- `ai_reasoning`: `"[Hidden - Blind Review]"`
- `comparison_outcome`: `"[Pending Analyst Review]"`

This prevents cognitive bias during pilot evaluation and ensures scientific validity.
