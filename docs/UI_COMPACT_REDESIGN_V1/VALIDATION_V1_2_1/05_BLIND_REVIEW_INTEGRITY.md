# VERDICTUM AI — VALIDATION V1.2.1
## 05. BLIND REVIEW INTEGRITY & API MASKING AUDIT

**Document Version:** 1.0.0  
**Scope:** AI Triage Workbench, Incident Endpoints, Ground-Truth Isolation  
**Status:** COMPLETE & VERIFIED  

---

### 1. Objective & Threat Model

In an Agentic SOC platform, human analyst evaluation is used as the ground truth for training, reinforcement learning, and production gate qualification. If an analyst can observe the AI's predicted verdict before rendering their independent assessment, confirmation bias contaminates the ground truth dataset:

$$\text{Observed Ground Truth} = f(\text{Actual Malice}, \text{AI Suggestion Bias})$$

To prevent this contamination, the platform operates a **Double-Blind Review Protocol**:
- The analyst must evaluate raw telemetry without knowledge of the model's recommendation.
- The AI's verdict must not be transmitted over the network in plaintext before the human verdict is recorded.
- Redundant or misleading client-side toggles must not create an illusion of protection while leaking data in HTTP payloads.

---

### 2. Verified Server-Side Sanitization

#### Implementation in `backend/app/services/incident_service.py`
Both list and detail endpoints (`/api/incidents` and `/api/incidents/{id}`) inspect whether a verified human analyst review exists for each requested incident:

```python
is_blind_mode = getattr(settings, "BLIND_REVIEW_MODE", True)

if is_blind_mode:
    # Query database for submitted analyst reviews
    existing_review = await db.execute(
        select(AnalystVerdictReview).filter_by(incident_id=incident.id)
    )
    if not existing_review.scalars().first():
        # Mask on the wire prior to serialization
        incident.ai_verdict = None
        incident.ai_confidence = None
        incident.ai_reasoning = "[Hidden - Blind Review active until analyst submits verdict]"
```

#### Automated API Test Evidence (`test_blind_review_sanitizes_ai_verdict_over_api`)
- **Query:** `GET /api/incidents?page=1&page_size=10`
- **Result:**
  - For unreviewed incidents:
    - `incident["ai_verdict"] == None`
    - `incident["ai_confidence"] == None`
    - `incident["ai_reasoning"] == "[Hidden - Blind Review active until analyst submits verdict]"`
  - For reviewed incidents:
    - `incident["ai_verdict"]` contains the model verdict for retrospective comparison.

---

### 3. UI Implementation in AI Triage Workbench

In `frontend/src/app/ai-triage-workbench/page.tsx`:
- The redundant local toolbar toggle was removed in V1.1 to avoid conflicting with the platform-wide governance setting.
- When an incident has not yet been reviewed, the verdict column renders:
  ```tsx
  <span className="text-[10px] font-mono text-slate-500 italic bg-slate-900/60 px-2 py-0.5 rounded border border-slate-800">
    [Hidden - Blind Review]
  </span>
  ```
- Submitting an analyst verdict writes the review to `analyst_verdict_reviews` table and immediately unlocks the comparison view for that specific analyst.

---

### 4. Verification Evidence
- Scenario `SCN-BLIND-REVIEW-ACTIVE` passed DOM validation across all 4 target viewports:
  - `hasHiddenMask: true`
  - Zero unmasked `ai_verdict` leaks in HTTP responses.
