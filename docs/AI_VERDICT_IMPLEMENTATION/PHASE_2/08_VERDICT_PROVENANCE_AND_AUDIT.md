# AI VERDICT — PHASE 2: VERDICT PROVENANCE & AUDIT
## 08. VERDICT PROVENANCE, REPLAY & AUDITABILITY (P2-REQ-07)

---

### 1. The Auditability Imperative
In enterprise SOC operations and regulatory compliance (e.g. NIST CSF, SOC 2, ISO 27001), automated triage systems must provide complete forensic auditability. When an incident is closed as a `FALSE_POSITIVE` or escalated as a `TRUE_POSITIVE`, auditors must be able to prove:
1. What exact telemetry existed at the moment of evaluation.
2. What investigation contract was active and approved at that time.
3. What factual claims the AI made.
4. Whether the deterministic validation engine accepted or modified the proposal.
5. That replaying the evaluation produces the exact same outcome.

---

### 2. Bifurcated Verdict Persistence
To ensure forensic transparency, the incident model stores both perspectives:

```python
{
    "incident_id": "INC-1001",
    "proposed_verdict": "TRUE_POSITIVE",   # What the model proposed
    "verdict": "REQUIRES_ATTENTION",        # Authoritative verdict accepted by platform
    "confidence": 0.0,                      # Effective display confidence (zeroed on abstention)
    "raw_model_confidence": 95.0,           # Original uncalibrated LLM score
    "validation_status": "REJECTED",        # VALIDATED, ABSTAINED, REJECTED, INSUFFICIENT_EVIDENCE
    "validation_reason_codes": [
        "CLAIM_NOT_VERIFIABLE"
    ],
    "is_decisive_accepted": False,
    "evidence_completeness": 0.67,
    "grounding_ratio": 0.50,
    "total_claims_count": 2,
    "grounded_claims_count": 1,
    "unsupported_claims_count": 1,
    "unsupported_claims": [
        {
            "claim_type": "NETWORK_CONNECTION",
            "field": "network.destination_ip",
            "asserted_value": "203.0.113.199",
            "grounding_status": "CLAIM_NOT_VERIFIABLE"
        }
    ],
    "analyst_action_directive": "Model fabricated or asserted unverified evidence claims. Human Tier 2 investigation required.",
    "contract_id": "EC-RULE-101-V1",
    "contract_version": 1,
    "validator_version": "2.0.0",
    "replay_signature": "a7b3c9d1e2f4a5b6",
    "evaluated_at": "2026-11-08T15:30:00.000000",
    "evaluated_by_user": "analyst_bob"
}
```

---

### 3. Cryptographic Replay Signature
Every evaluated verdict is signed with a deterministic SHA-256 digest:
$$\text{Replay Token} = \text{incident\_id} : \text{contract\_id} : \text{proposed\_verdict} : \text{final\_verdict} : \text{validator\_version}$$
$$\text{Replay Signature} = \text{SHA-256}(\text{Replay Token})[:16]$$

This 16-character hexadecimal signature allows instant verification that the stored record has not been altered post-evaluation.

---

### 4. Deterministic Replay Engine
The backend provides `IndependentVerdictValidator.replay_validation()`:
- Rehydrates the saved canonical evidence snapshot.
- Reconstructs the exact contract state.
- Re-executes the 8-check deterministic pipeline.
- Compares the re-derived signature against the original stored signature.

If any field in the evidence snapshot was modified, the replay signature diverges, exposing the tamper event.

