# Deterministic Verdict Guardrails (AIS 2.1)

## 1. Core Purpose and Philosophy

Language models are probabilistic generators that frequently generate decisive classifications (`TRUE_POSITIVE` or `FALSE_POSITIVE`) even when evidence is missing, contradictory, or unverifiable.

The **Verdict Guardrails Engine** (`backend/app/services/verdict_guardrails_engine.py`) serves as the deterministic circuit breaker in the decision loop. It enforces strict, non-negotiable safety rules (G1–G7) that intercept the model's suggested verdict and demote it to `REQUIRES_ANALYST_ATTENTION` whenever safety or evidentiary thresholds are violated.

---

## 2. Guardrails Architecture (G1–G7)

```
                            [ Local LLM Output ]
                                     |
                                     v
                       +---------------------------+
                       | G1: Missing Mandatory?    |----(Yes)----> [ REQUIRES_ANALYST_ATTENTION ]
                       +---------------------------+
                                     | (No)
                                     v
                       +---------------------------+
                       | G2: Unsupported Claims?   |----(Yes)----> [ REQUIRES_ANALYST_ATTENTION ]
                       +---------------------------+
                                     | (No)
                                     v
                       +---------------------------+
                       | G3: Contradictions?       |----(Yes)----> [ REQUIRES_ANALYST_ATTENTION ]
                       +---------------------------+
                                     | (No)
                                     v
                       +---------------------------+
                       | G4: Blanket FP Attempt?   |----(Yes)----> [ REQUIRES_ANALYST_ATTENTION ]
                       +---------------------------+
                                     | (No)
                                     v
                       +---------------------------+
                       | G5: Phantom Threshold?    |----(Yes)----> [ REQUIRES_ANALYST_ATTENTION ]
                       +---------------------------+
                                     | (No)
                                     v
                       +---------------------------+
                       | G6: 3-Way Normalization   |
                       +---------------------------+
                                     |
                                     v
                       +---------------------------+
                       | G7: Audit Trail & Logging |
                       +---------------------------+
                                     |
                                     v
                       [ Final Enforced Verdict ]
```

---

## 3. The Guardrail Specifications

### G1: Mandatory Evidence Deficiency Gate
- **Trigger**: `EvidenceSufficiencyAssessmentResult.is_sufficient == False` or `len(missing_mandatory_fields) > 0`.
- **Enforcement**: Overrides any suggested verdict to `REQUIRES_ANALYST_ATTENTION`.
- **Rationale**: An AI verdict cannot be accepted as definitive if core evidentiary building blocks (such as flow direction or source IP) are absent.

### G2: Factual Grounding & Hallucination Gate
- **Trigger**: `VerdictClaimValidator.unsupported_claims_count > 0` or presence of unverified IP addresses, domains, or user accounts.
- **Enforcement**: Overrides any suggested verdict to `REQUIRES_ANALYST_ATTENTION`.
- **Rationale**: If the model fabricated an artifact (e.g., citing a C2 IP not present in the firewall logs), its verdict logic is tainted and must be reviewed by a human analyst.

### G3: Contradiction & Directional Inversion Gate
- **Trigger**: Telemetry contains conflicting data points (e.g., traffic classified as outbound when headers specify inbound, or zero bytes transferred when payload claims exfiltration).
- **Enforcement**: Overrides any suggested verdict to `REQUIRES_ANALYST_ATTENTION`.
- **Rationale**: Automated systems must never dismiss or escalate incidents that contain fundamental internal paradoxes without human adjudication.

### G4: Blanket / Unsubstantiated False Positive Gate
- **Trigger**: The model proposes `FALSE_POSITIVE` but the incident contains elevated severity flags or high-volume metrics without investigating mandatory contract criteria (e.g., claiming "normal business traffic" without verifying destination domain ownership).
- **Enforcement**: Overrides suggested `FALSE_POSITIVE` to `REQUIRES_ANALYST_ATTENTION`.
- **Rationale**: Prevents catastrophic False Negatives where the AI dismisses genuine intrusions due to superficial plausibility.

### G5: Phantom Threshold Assertion Gate
- **Trigger**: The model asserts that an unverified telemetry value (such as `sentBytes64: 2130499380` in `PH_RULE_LARGE_OUTBOUND_XFER`) represents an authorized or configured SIEM threshold when no authoritative baseline is provided.
- **Enforcement**: Demotes verdict to `REQUIRES_ANALYST_ATTENTION` and attaches a warning:
  `"Model asserted unverified metadata as configured SIEM threshold."`
- **Rationale**: Enforces strict epistemic honesty. Observed values must never be conflated with authorized thresholds.

### G6: Strict 3-Way Normalization Gate
- **Trigger**: Model outputs non-standard strings (e.g., `"SUSPICIOUS"`, `"PROBABLE_THREAT"`, `"BENIGN_ACTIVITY"`, `"ESCALATE"`).
- **Enforcement**: Deterministically normalizes every output into one of exactly three canonical values:
  1. `TRUE_POSITIVE`
  2. `FALSE_POSITIVE`
  3. `REQUIRES_ANALYST_ATTENTION`
- **Rationale**: Prevents ambiguous intermediate classifications from degrading downstream reporting or breaking API schemas.

### G7: Audit Trail Preservation Gate
- **Enforcement**: The engine preserves:
  - `original_suggested_verdict`: What the LLM initially outputted.
  - `final_enforced_verdict`: What the guardrails approved.
  - `is_demoted`: Boolean indicating whether a safety downgrade occurred.
  - `demotion_reasons`: Detailed list of triggered guardrail rules and telemetry discrepancies.
- **Rationale**: Complete operational transparency for SOC auditability and model retraining.
