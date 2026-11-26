# 09 — Structured Output & Confidence Schema

- Standardized strict `0.0-100.0` numeric confidence across `PolicyCompilerService.MODEL_RESPONSE_SCHEMA`, `OpenAICompatibleProvider`, `_MODE_A_SCHEMA_SUFFIX`, and `ConfidenceNormalizer`.
- Ambiguous decimal confidence `(0.0 < c <= 1.0)` without explicit `confidence_scale` continues to fail closed (`INVALID_CONFIDENCE` -> `REQUIRES_ATTENTION`) rather than silent scaling, preserving raw model text alongside structured validation errors.
- Added optional `response_format={"type": "json_object"}` and `guided_json` pass-through support in `OpenAICompatibleProvider` and `AIS27BenchmarkRunner._dispatch_vllm`.
