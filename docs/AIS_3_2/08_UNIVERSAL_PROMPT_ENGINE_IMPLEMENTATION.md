# AIS 3.2 — 08: Universal Prompt Engine Implementation

Implemented `UniversalPromptEngine` (`backend/app/services/universal_prompt_engine.py`) shared by live triage (`verdict_pipeline.py`) and development evaluation (`ais32_benchmark_service.py`):
- Strips sensitive keys (`incidentReso`, `confidence`, `cleared_reason`, ground truth) across both `Incident.events` and `Incident.raw_payload` fallback.
- Escapes closing `</UNTRUSTED_INCIDENT_DATA>` tags against prompt injection.
- Runs Mode A (`NEUTRAL_SOC_BASELINE_V2`) and Mode B (`AIS32_UNIVERSAL_v3.2.0`) through identical preparation and structured JSON output verification (`validate_structured_output` with max 1 bounded repair retry).
