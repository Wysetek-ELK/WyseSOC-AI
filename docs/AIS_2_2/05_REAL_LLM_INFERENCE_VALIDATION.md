# AIS 2.2 Report 05: Real LLM Inference Pipeline Validation

**Project:** Verdictum AI  
**Organization:** Wysetek Systems Technologists Pvt. Ltd.  
**Phase:** AIS 2.2 (Core Verdict Accuracy Baseline & Real LLM Benchmark)  
**Date:** 2026-11-23  
**Status:** VALIDATED & AUDITED  

---

## 1. End-to-End Inference Architecture

The complete AI inference pipeline was validated from incident ingestion to final audit persistence:

```
[FortiSIEM Incident]
       │
       ▼
[Payload Sanitizer] ──> Strips closure metadata (0 data leaks)
       │
       ▼
[Evidence Extractor] ──> Normalizes fields into CanonicalEvidenceRecord
       │
       ▼
[Policy Resolver] ──> Resolves active v7 (APPROVED) vs draft v8 (DRAFT)
       │
       ▼
[Prompt Compiler] ──> Enforces dynamic token budget (2,048 prompt tokens max)
       │
       ▼
[Local Qwen Inference] ──> Qwen/Qwen2.5-7B-Instruct-AWQ via vLLM OpenAI API
       │
       ▼
[Structured Response] ──> JSON schema parsing (verdict, citations, reasoning)
       │
       ▼
[Independent Validator] ──> Grounding verification & hallucination checks
       │
       ▼
[Guardrails & Trust] ──> Trust score computation (0-100) & unsafe FP check
       │
       ▼
[Audit Persistence] ──> Saved in actual_prompt_captures & trust records
```

---

## 2. Response Schema & Structural Compliance

Every model response must conform to Verdictum AI's structured JSON contract:
- `verdict`: One of `TRUE_POSITIVE`, `FALSE_POSITIVE`, `REQUIRES_ANALYST_REVIEW`.
- `confidence`: Calibrated numeric float between `0.0` and `1.0`.
- `reasoning`: Chain-of-thought technical rationale referencing telemetry facts.
- `supporting_events`: Array of event sequence IDs directly backing the claim.
- `contradictory_evidence`: Telemetry indicating alternative hypotheses.
- `missing_evidence`: Telemetry required but missing (e.g. payload captures, packet dumps).

### Error & Timeout Differentiation
A critical safety invariant requires distinguishing technical inference failures from legitimate model abstentions:
- **Model Abstention (`REQUIRES_ANALYST_REVIEW`):** The model successfully generated structured reasoning concluding that evidence is ambiguous, incomplete, or requires human authorization.
- **Inference Failure (`EVALUATION_FAILED`):** HTTP 500, network connection timeout, socket hangup, or unparseable non-JSON output. These are explicitly tagged with `dispatch_status = "FAILED"` and `validation_status = "EVALUATION_FAILED"`.
- **Safety Invariant:** A failed inference is **never** silently converted into a False Positive or successful abstention.

---

## 3. Raw Prompt Capture & Audit Immutability

Verdictum AI implements full cryptographic auditing for every inference attempt in the `actual_prompt_captures` table:
- Full system prompt and compiled user message.
- Cryptographic hash (`request_sha256`) of the complete prompt text.
- Exact raw response text from the model.
- Model identifier (`Qwen/Qwen2.5-7B-Instruct-AWQ`).
- Policy version number and policy version UUID.
- Execution latency in milliseconds.
- Dispatch status (`COMPLETED` or `FAILED`).

This ensures 100% forensic auditability for enterprise compliance and security governance.
