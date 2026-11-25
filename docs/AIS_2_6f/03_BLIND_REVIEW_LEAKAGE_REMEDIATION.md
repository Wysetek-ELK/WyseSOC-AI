# 03 — Blind Review Leakage Remediation

## Fixed Channels
1. **Handover Note Contamination (`ai_verdict_service.py`)**: Stopped writing `[AI Verdict (...)]: ...` into `Investigation.analyst_notes`; added `strip_ai_notes_from_handover` scrubbing on read whenever blind review applies.
2. **Server-Side Blind Bypass (`investigation_service.py`, `telemetry_timeline_service.py`, `ais_evaluation_service.py`, `prompts.py`)**: Administrators now respect `?blind_review=true` via `can_reveal_protected_verdict_info`; Analysts never bypass blind review via URL flags before reviewing.
3. **Frontend Prefill & Matrix Masking (`human-review-queue/page.tsx`, `IncidentVerdictMatrix.tsx`, `ai-triage-workbench/[id]/page.tsx`)**: Removed fallback from `ai_assurance.validated_verdict`, hid `AI:` badges when Blind Review is ON, separated pre-submission verdict buttons from post-review actions, cleared `aiVerdict` React state on blind toggle, and masked Dimensions 1-3 in `IncidentVerdictMatrix`.
4. **Dedicated Ground Truth Certification API (`/api/ground-truth/...`)**: Omits AI verdicts and historical FortiSIEM labels from response schemas until `GT3_CERTIFIED`.
