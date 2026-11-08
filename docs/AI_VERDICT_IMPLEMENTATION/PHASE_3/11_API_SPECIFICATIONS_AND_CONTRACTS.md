# 11. API SPECIFICATIONS & CONTRACTS

**Document Identifier:** `AV-P3-DOC-11`  
**Requirement Mapping:** `P3-REQ-01`, `P3-REQ-06`, `P3-REQ-07`  
**Implementation Modules:** `app/api/rules.py`, `app/api/investigations.py`  

---

## 1. Updated AI Verdict Response Payload

The `IncidentAiVerdictResponse` payload returned by `VerdictTriageAgent.evaluate_incident` contains complete Phase 3 metadata:

```json
{
  "incident_id": "INC-0001",
  "proposed_verdict": "TRUE_POSITIVE",
  "verdict": "TRUE_POSITIVE",
  "confidence": 94.0,
  "raw_model_confidence": 94.0,
  "reason": "Observed behavioral pattern matches adversary technique...",
  "supporting_evidence": ["process.cmdline: powershell.exe -enc ..."],
  "supporting_claims": [
    {
      "claim_type": "PROCESS_EXECUTION",
      "field": "process.command_line",
      "asserted_value": "powershell.exe -enc AAAA",
      "is_grounded": true,
      "grounding_status": "GROUNDED"
    }
  ],
  "missing_evidence": [],
  "analyst_questions": ["What is the parent process?"],
  "latency_ms": 420,
  "model_identifier": "qwen2.5-coder-14b-instruct",
  "prompt_tokens": 1820,
  "completion_tokens": 140,
  "total_tokens": 1960,
  "is_simulated": false,
  "validation_status": "VALIDATED",
  "validation_reason_codes": ["EVIDENCE_VALIDATED"],
  "is_decisive_accepted": true,
  "evidence_completeness": 1.0,
  "grounding_ratio": 1.0,
  "contract_id": "EC-RULE-CS-01-V1",
  "contract_version": 1,
  "validator_version": "v2.0.0",
  "compiler_version": "v3.0.0",
  "compilation_digest": "3a8b...9f12",
  "policy_sections_count": 9,
  "policy_status": "APPROVED",
  "calibration_status": "NOT_CALIBRATED",
  "is_calibrated": false,
  "rag_retrieval_status": "PRECEDENTS_FOUND",
  "retrieved_precedents_count": 1,
  "retrieved_precedents": [
    {
      "precedent_id": "lr-001",
      "incident_id": "INC-HIST-01",
      "incident_title": "Historical Encoded Script Attack",
      "rule_id": "RULE-CS-01",
      "verified_verdict": "TRUE_POSITIVE",
      "analyst_explanation": "Confirmed malicious stager.",
      "similarity_score": 0.84,
      "feedback_timestamp": "2026-06-01T10:00:00Z"
    }
  ],
  "token_budget_breakdown": {
    "max_context_tokens": 4096,
    "max_completion_tokens": 1024,
    "total_prompt_tokens": 1820,
    "rag_trimmed": false,
    "context_overflow_detected": false
  },
  "replay_signature": "7f8b9a2c3d4e5f60"
}
```

---

## 2. Rule Endpoints

- `GET /api/rules/{identifier}/compiled-policy`
- `GET /api/rules/{identifier}/calibration-report`

