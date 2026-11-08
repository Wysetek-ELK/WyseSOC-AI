# AI VERDICT — PHASE 2: CONFIDENCE & ABSTENTION
## 07. CONFIDENCE, COMPLETENESS & ABSTENTION (P2-REQ-06)

---

### 1. The Confidence Fallacy in LLM Decisions
A core finding from the Phase 0 audit was that LLM confidence scores were presented to analysts as if they represented empirical accuracy. In reality:
- LLM confidence scores are uncalibrated probabilistic estimates.
- A model can express 98% confidence in a completely hallucinated verdict.
- High model confidence in the presence of missing telemetry is an indicator of **overconfidence**, not accuracy.

Phase 2 decouples model confidence from system authority.

---

### 2. Dual Confidence Handling

AI Verdict implements a bifurcated confidence model:

```
+-------------------------------------------------------------------------+
| Raw LLM Confidence Score (e.g. 95%)                                     |
| -> Uncalibrated heuristic estimate produced by the model                |
| -> Stored as raw_model_confidence for research & calibration analysis   |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| Independent Deterministic Evidence Validation Pipeline                  |
| -> Checks contract compliance, critical telemetry, claim grounding     |
+-------------------------------------------------------------------------+
       |                                                   |
       | If Validation Fails                               | If Validation Passes
       v                                                   v
+-------------------------------+       +---------------------------------+
| Effective Confidence: 0%      |       | Effective Confidence: Raw Score |
| Status: ABSTAINED / REJECTED  |       | Status: VALIDATED ACCEPTED      |
| Reason: Safety Override       |       | Replay Signature Generated      |
+-------------------------------+       +---------------------------------+
```

1. **`raw_model_confidence`**: Preserves what the model generated (e.g. 95.0%). In UI, clearly labeled as `Raw LLM Score: 95% (Uncalibrated)`.
2. **`validated_confidence_display` / `confidence`**:
   - If deterministic validation passes (`is_decisive_accepted == True`): displays the verified score.
   - If deterministic validation fails or abstains: **strictly forced to 0%** (`validated_confidence_display = 0.0`).

This prevents an analyst from seeing a dangerous UI presentation like *"REQUIRES_ATTENTION (Confidence: 95%)"*.

---

### 3. Evidence Completeness Metric
Evidence completeness is computed objectively against the approved contract:
$$\text{Evidence Completeness} = \frac{\text{Satisfied Required Fields}}{\text{Total Contract Required Fields}}$$

- **Range:** $0.0$ to $1.0$ ($0\%$ to $100\%$).
- **Color Coding in UI:**
  - $\ge 80\%$: Green (High Completeness)
  - $40\% - 79\%$: Amber (Partial Completeness)
  - $< 40\%$: Rose (Critical Incompleteness)

---

### 4. Deterministic Abstention Directives
When validation forces an abstention to `REQUIRES_ATTENTION`, the validator generates an explicit `analyst_action_directive`:

| Validation Reason | Action Directive Generated |
|---|---|
| `EVIDENCE_MISSING` | *"Collect missing mandatory telemetry ({missing_fields}) before closing incident."* |
| `CLAIM_NOT_VERIFIABLE` | *"Model fabricated or asserted unverified evidence claims. Human Tier 2 investigation required."* |
| `EVIDENCE_CONTRACT_UNVERIFIED` | *"Please review and approve the investigation policy in Agent Intelligence Studio before automated triage."* |
| `EVIDENCE_CONTRADICTION` | *"Activity occurs strictly on internal/loopback stack. Verify if local proxy reflection or healthcheck."* |
| `TP_CRITERIA_UNSATISFIED` | *"Insufficient corroborating evidence to confirm malicious attack. Manual triage required."* |
| `FP_CRITERIA_UNSATISFIED` | *"Missing telemetry prevents confirming false positive. Human verification required."* |

