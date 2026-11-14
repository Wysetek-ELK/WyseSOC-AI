# 02 — Implementation Report: Actual LLM Prompt Inspector

**Platform:** Verdictum AI — Agent Intelligence Studio 2.0  
**Feature:** View Actual LLM Prompt  
**Date:** November 14, 2026  
**Status:** Successfully Implemented & Verified  

---

## 1. Overview of Changes

The Actual LLM Prompt Inspector implementation introduces full-stack visibility into the exact instructions and evidence dispatched from Server 1 (Verdictum AI) to Server 2 (Local LLM).

### Key Files Created & Modified:

| File | Type | Description |
|---|---|---|
| `backend/app/models/actual_prompt_capture.py` | New Model | SQLAlchemy model `ActualLLMPromptCapture` for immutable runtime records |
| `backend/alembic/versions/010_actual_llm_prompt_inspector.py` | New Migration | Database migration creating `actual_llm_prompt_captures` table with indices |
| `backend/app/services/actual_prompt_capture_service.py` | New Service | SHA-256 canonical hashing, dispatch recording, integrity verification, RBAC redaction |
| `backend/app/schemas/prompt_inspector.py` | New Schema | Pydantic response models for 6 inspector tabs, banners, integrity status, and L1 summary |
| `backend/app/services/model_provider/base.py` | Modified | Extended `StructuredModelVerdict` with capture metadata fields |
| `backend/app/services/model_provider/openai_compatible.py` | Modified | Integrated pre-dispatch and post-dispatch hooks at HTTP boundary |
| `backend/app/services/model_provider/simulated.py` | Modified | Added identical capture hooks to ensure simulation/mock parity |
| `backend/app/services/verdict_pipeline.py` | Modified | Wired `ActualPromptCaptureService` into `_invoke_provider_with_guards`, early safety gates, and verdict return |
| `backend/app/api/prompts.py` | Modified | Added 3 authenticated endpoints for incident prompt retrieval, live preview, and exports |
| `backend/app/main.py` | Modified | Mounted prompts router with `/api` and `/api/v1` prefixes |
| `frontend/src/lib/api.ts` | Modified | Added TypeScript interfaces and API client functions (`getActualPromptForIncident`, `getPromptPreviewForRule`, `exportActualPrompt`) |
| `frontend/src/components/prompt-inspector/ActualPromptInspectorModal.tsx` | New Component | Full-featured modal with 3 banners, L1 summary card, 6 tabbed views, copy/export controls |
| `frontend/src/app/agent-intelligence-studio/page.tsx` | Modified | Added "View Actual LLM Prompt" triggers in header action bar, simulation table, and modal integration |
| `backend/tests/test_actual_prompt_inspector.py` | New Tests | 7 automated tests validating end-to-end capture, tampering detection, intercepts, and API behavior |

---

## 2. Capture Engine Details

### 2.1 Canonical Payload Hashing
To prevent whitespace variations from invalidating integrity verification:
```python
@staticmethod
def canonical_hash(payload: Dict[str, Any]) -> str:
    canonical_bytes = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()
```

### 2.2 Provider Boundary Capture Workflow
1. **Immediately Before Dispatch:**
   - Compiled system prompt, user telemetry message, generation settings, model name, and execution metadata are assembled into the canonical outbound payload dictionary.
   - `ActualPromptCaptureService.record_dispatch(...)` commits an initial record with status `DISPATCHED` and the computed `request_sha256`.
2. **Immediately After Response:**
   - When the LLM responds, `ActualPromptCaptureService.record_completed(...)` updates the record with prompt tokens, completion tokens, latency ms, raw JSON string, and final status `COMPLETED`.
3. **If Network or Inference Fails:**
   - `ActualPromptCaptureService.record_failed(...)` records the error message, exception type, and status `FAILED`.
4. **If Safety Gate Intercepts Before Dispatch:**
   - `ActualPromptCaptureService.record_non_dispatch(...)` creates an explicit record with status `NOT_DISPATCHED`, preserving the exact reason (e.g. `POLICY_NOT_APPROVED`, `INSUFFICIENT_EVIDENCE`) and marking integrity as `UNVERIFIED`.

---

## 3. Frontend Inspector Architecture

### 3.1 Banners (Strict Truth in Labeling)
- **Captured Runtime Prompt (Green):** Displays when `capture_status === "CAPTURED_RUNTIME"`. Confirms that the displayed prompt was extracted from an authoritative outbound capture record.
- **Historical Capture Unavailable (Amber):** Displays when `capture_status === "HISTORICAL_CAPTURE_UNAVAILABLE"`. Indicates that the incident verdict was produced prior to capture engine deployment.
- **Preview Only (Sky/Indigo):** Displays when `capture_status === "PREVIEW_ONLY"`. Clarifies that the prompt is a live-compiled specification and NOT proof of past execution.

### 3.2 L1 Engineer Plain-Language Summary
Headline:
> **"This is the investigation instruction and incident evidence that Verdictum AI sent to the Local LLM to generate this verdict."**

Displays 5 key highlight badges:
1. **Policy Version Used:** e.g. `Version 2 (APPROVED)`
2. **Mandatory Evidence Available:** `Available` or `Missing / Incomplete`
3. **Historical Precedents Included:** e.g. `None (Zero RAG)` or `1 Included`
4. **Verdict Returned:** e.g. `TRUE_POSITIVE`, `FALSE_POSITIVE`, `REQUIRES_ATTENTION`
5. **Policy Approval Match:** `Approved Match` or `Unapproved Policy`

### 3.3 Prompt Integrity Indicator
- **Verified:** Green badge with `ShieldCheck`. Verifies SHA-256 payload match, active policy approval, untrusted data boundary delimiters, and matching incident telemetry.
- **Mismatch:** Red pulsing badge with `ShieldAlert`. Triggered when payload content does not match the canonical hash, or policy version diverged.
- **Unverified:** Gray badge with `Shield`. Applied to previews, historical uncaptured runs, or aborted non-dispatched safety exits.

### 3.4 Six Specialized Perspectives
1. **Execution Summary:** Incident ID, rule name, model, provider, capture timestamp, policy version/source, dispatch status, latency.
2. **System Prompt:** Complete 11-section prompt text including common SOC baseline, rule directive, detection conditions, TP/FP indicators, and JSON schema requirements.
3. **Incident Payload:** Formatted user message showing FortiSIEM normalized telemetry wrapped in `<UNTRUSTED_INCIDENT_DATA>`.
4. **Historical Precedents:** Exact RAG precedents provided during inference (or empty state explaining zero RAG usage).
5. **Output Contract:** Formatted JSON schema enforced on the LLM output.
6. **Technical Details:** Token metrics (Prompt/Completion/Total), generation settings, canonical SHA-256 hash, and raw payload inspect view.

---

## 4. RBAC, Security, and Non-Disruption Guarantees

- **Role-Based Redaction:** Administrators receive full unredacted payloads. SOC Analysts and Read-Only Viewers have sensitive credentials, tokens, and RFC1918 / public IP patterns automatically masked with `[REDACTED_IP]` or `[REDACTED_SECRET]`.
- **Read-Only Safety:** The inspector APIs and frontend modal are strictly read-only. Analysts cannot modify, approve, rollback, or activate policies through the inspector.
- **Audit Logging:** Every prompt inspection triggers an immutable `VIEW_ACTUAL_LLM_PROMPT` audit event recording the user, role, incident ID, and access timestamp.
- **Pipeline Fault Isolation:** Capture storage exceptions are caught and logged without disrupting incident triage. If database capture fails, the pipeline completes and records a visible capture failure rather than halting verdict generation.
