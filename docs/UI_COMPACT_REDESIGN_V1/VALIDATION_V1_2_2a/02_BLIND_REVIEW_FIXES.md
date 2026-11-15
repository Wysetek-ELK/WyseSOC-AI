# VERDICTUM AI — VALIDATION V1.2.2a
## 02. Blind Review Fixes & Isolation Architecture

### 1. Architectural Principles

Under the V1.2.2a security model, double-blind review isolation is **server-enforced, role-gated, and reviewer-scoped**:
1. **Server-Enforced Authority**: A client request cannot bypass masking by setting `?blind_review=false` or omitting the parameter. If the user is authenticated with role `SOC Analyst` or `Read-Only Viewer`, protected fields are automatically masked by the backend.
2. **Reviewer-Scoped Isolation**: Blind review protection is evaluated on a per-user, per-incident basis. When Analyst A submits a review for an incident, the verdict is revealed **only to Analyst A**. It remains strictly masked for Analyst B until Analyst B independently submits their own review.
3. **Safe DTO Sanitization**: Redaction occurs strictly in the outbound response serialization layer (Response DTOs). In-memory SQLAlchemy entities and database records are never modified or purged during read operations.
4. **Authorized Post-Submission Reveal**: Once a reviewer submits an independent determination, the server permits them to see the historical resolution and AI verdict to facilitate learning, model comparison, and ground-truth audit.

---

### 2. Implementation Details

#### 2.1 Backend Endpoint & Service Updates

- **`backend/app/services/incident_service.py`**:
  ```python
  # Server-Enforced Isolation Logic:
  if current_user and getattr(current_user, "role", "") == "SOC Analyst":
      user_id = str(getattr(current_user, "id", ""))
      username = str(getattr(current_user, "username", ""))
      rev_q = select(AnalystVerdictReview.id).where(
          AnalystVerdictReview.incident_id.in_([str(inc.id), str(inc.incident_id)]),
          AnalystVerdictReview.reviewer_id.in_([user_id, username])
      )
      has_reviewed = (await db.execute(rev_q)).scalar_one_or_none() is not None
      if not has_reviewed:
          inc.ai_verdict = None
          inc.historical_resolution = "[Hidden - Blind Review]"
  ```
  Read-Only Viewers are unconditionally masked: `ai_verdict = None`, `historical_resolution = "[Hidden - Blind Review]"`.

- **`backend/app/services/analyst_review_service.py`**:
  ```python
  # Reviewer-scoped lookup to prevent review record overwrites:
  rev_stmt = select(AnalystVerdictReview).where(
      AnalystVerdictReview.incident_id == incident.id,
      AnalystVerdictReview.reviewer_id == str(reviewer_id)
  )
  ```

- **`backend/app/services/investigation_service.py`**:
  - `list_queue`: Accepts `current_user`. If the current user has not submitted an `AnalystVerdictReview` for the incident, `ai_validated_verdict` and `ai_trust_score` are sanitized to `None`.
  - `build_ai_assurance`: Sanitizes `verdict`, `confidence`, and `trust_score` to `None` for unreviewed analysts.

- **`backend/app/services/telemetry_timeline_service.py`**:
  - `get_incident_timeline`: Accepts `current_user`. Redacts Milestone 6 (`Verdict Triage Agent`) and Milestone 7 (`SIEM Ticket Resolved`) to `[Hidden - Blind Review]` for unreviewed analysts.

- **`backend/app/api/incidents.py`**:
  - `POST /{identifier}/ai-verdict`: If `current_user.role == "SOC Analyst"` and the incident has not been reviewed by that user, the request is rejected with `HTTP 403 Forbidden` (`"Direct AI verdict generation is restricted during Blind Review"`).

---

### 3. Frontend UI Reflection

- **Header Preference**:
  When `blindReviewMode` is enabled, the global header shows:
  `Blind Review: ON` (amber tag).
  When toggled off, it displays:
  `Blind Review: OFF`.
- **Server Isolation Banner in Workbench**:
  When `!blindReviewMode`, the frontend displays an informative banner:
  > **Blind Review UI Preference: OFF** — Server-enforced double-blind isolation remains active for unreviewed incidents.
- **Row Badge Rendering**:
  Whenever the backend returns `ai_verdict: null`, the incident row renders:
  `AI: [Hidden - Blind Review]` (slate badge with eye icon and tooltip).
  When the backend returns an authorized verdict, the row renders:
  `AI: TP` / `AI: FP` (with sparkles indicator).

---

### 4. Security Verification Summary

| Vector | Before Fix | After Fix | Verified Test |
| :--- | :--- | :--- | :--- |
| `?blind_review=false` | AI verdict & resolution returned | Sanitized to `None` & `[Hidden - Blind Review]` | `test_01_unreviewed_analyst_cannot_bypass_via_query_param` |
| Analyst B Isolation | Analyst B saw Analyst A's review | Analyst B receives masked `None` | `test_04_analyst_b_isolated_from_analyst_a_review` |
| Investigation Queue | Exposed `ai_validated_verdict` | Sanitized to `None` | `test_05_investigation_queue_redacted_for_unreviewed_analyst` |
| Incident Timeline | Emitted Milestone 6 & 7 text | Masked to `[Hidden - Blind Review]` | `test_06_incident_timeline_redacted_for_unreviewed_analyst` |
| Direct AI Triage API | Executed and returned verdict | Blocked with `HTTP 403 Forbidden` | `test_07_direct_ai_verdict_post_blocked_in_blind_review` |
| Read-Only Viewer | Exposed historical resolution | Masked to `[Hidden - Blind Review]` | `test_03_read_only_viewer_masked` |
