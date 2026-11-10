# Verdict Trustworthiness, Grounding & Calibration Audit

- **Updated At:** 2026-11-10T19:55:00+05:30
- **Repository Commit:** `0148142` (`0148142f3abd6dad87a903b90f7b25edb8d41def`)
- **Architecture Version:** `AIS 2.1 + Audit Remediation v2.2.1`
- **Audited Engines:** [`independent_verdict_validator.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/independent_verdict_validator.py), [`model_claim_extractor.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/model_claim_extractor.py), [`evidence_sufficiency_engine.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/evidence_sufficiency_engine.py), [`verdict_claim_validator.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/verdict_claim_validator.py), [`verdict_guardrails_engine.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/verdict_guardrails_engine.py), [`verdict_trustworthiness_engine.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/verdict_trustworthiness_engine.py), [`historical_ground_truth_validator.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/historical_ground_truth_validator.py), [`calibration_evaluator.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/calibration_evaluator.py)

---

## 1. Separation of Signals (Confidence vs. Validation vs. Trustworthiness vs. Empirical Calibration)

AI Verdict strictly separates four distinct signals so raw LLM overconfidence can never masquerade as validated accuracy:

1. **LLM Subjective Confidence (`raw_model_confidence`, 0–100):** Untrusted self-reported score emitted by the model. Masked to `0.0` (`validated_confidence_display`) whenever independent checks abstain or reject.
2. **Deterministic Contract Validation (`IndependentVerdictValidator`, `2.0.0`):** Verifies approved `RuleEvidenceContract`, preflight critical completeness, claim grounding, contradictions, and verdict-specific TP/FP criteria. Produces `TRUE_POSITIVE`, `FALSE_POSITIVE`, or `REQUIRES_ATTENTION`.
3. **Verdict Trustworthiness Score (`VerdictTrustworthinessEngine`, `v2.2.0`, 1–10 ordinal + `0–100` raw + `NOT_CALCULABLE`):** Aggregates 5 weighted dimensions:
   - Direct Claim-to-Evidence Support (`0–35`)
   - Evidence Source Reliability (`0–20`)
   - Contradiction & Counterevidence Handling (`0–15`)
   - Independent Corroboration (`0–15`)
   - Historical Empirical Validation Support (`0–15`)
4. **Empirical Calibration Status (`CalibrationEvaluator`):** Enforces `N >= 30` verified ground-truth cases with balanced class representation (`>= 3` verified samples per class). Below threshold, rule status remains `NOT_CALIBRATED` / `UNCALIBRATED` and Trust Score is capped at **6/10**.

---

## 2. Remediated Semantic & Grounding Vulnerabilities

### 2.1 Empty-Claim Decisive Verdict Bypass (Closed)
- **Prior Risk:** Both `IndependentVerdictValidator` and `VerdictTrustworthinessEngine` allowed decisive `TRUE_POSITIVE`/`FALSE_POSITIVE` classifications when `total_claims == 0` because `ModelClaimExtractor` sets `grounding_ratio = 1.0` when `total == 0` and dimension 1 awarded 20–25 free points for unclaimed verdicts.
- **Remediation:**
  - `IndependentVerdictValidator.validate_verdict()` strictly requires `claim_grounding.grounded_claims >= 1` for both `TRUE_POSITIVE` and `FALSE_POSITIVE`.
  - `VerdictGuardrailsEngine.apply_guardrails()` blocks empty decisive proposals (`G3_EMPTY_DECISIVE_CLAIMS`).
  - `VerdictTrustworthinessEngine` awards `0.0 / 35.0` claim support points if a decisive proposal provides zero claims.

### 2.2 V3 vs. P2 Claim Schema Drift & `OpenAICompatibleProvider` Drop (Closed)
- **Prior Risk:** `PolicyCompilerService.MODEL_RESPONSE_SCHEMA` requested `claim_text` + `cited_evidence_ids`, `OpenAICompatibleProvider` omitted `supporting_claims` entirely from its JSON schema prompt and response object, and `ModelClaimExtractor` / `VerdictClaimValidator` only read differing field keys (`field`/`asserted_value`/`evidence_ids` vs `claim`/`claim_text`).
- **Remediation:** `OpenAICompatibleProvider` instructs and forwards `supporting_claims` and `contradictory_evidence`; `ModelClaimExtractor` and `VerdictClaimValidator` parse both `supporting_claims` and `claims`, `evidence_ids` and `cited_evidence_ids`, and map canonical `evidence_id` records cleanly.

### 2.3 Observed Threshold Misuse, Blanket FP Exemptions & False Substring Grounding (Closed)
- **Remediation:**
  - Generalized `VerdictClaimValidator` beyond literal `"2130499380"` to reject any asserted telemetry byte/metric threshold when authoritative SIEM semantics are `INCOMPLETE` or unmatched.
  - Hardened `proc_blocked` detection for string values (`"true"`, `"yes"`, `"1"`, `"blocked"`).
  - Blocked bare low-signal tokens (`"high"`, `"low"`, `"rule"`, `"true"`, `"false"`, `"none"`, etc.) from falsely grounding claims via naive substring search.
  - Enforced rejection of blanket RFC-1918 / loopback / negative-evidence `FALSE_POSITIVE` rationales in `IndependentVerdictValidator`, `VerdictGuardrailsEngine` (G6), and `PolicyQualityValidator` (G5).

### 2.4 Ground-Truth Isolation, Replay Integrity & Calibration Honesty
- `HistoricalGroundTruthValidator` strips all closure/resolution keys recursively before model evaluation, discards ML-generated ground truth (`is_ml_generated=True`), and partitions deterministically into `TRAIN`, `TUNING`, `CALIBRATION`, and `LOCKED_TEST` via SHA-256 hashing.
- Removed hardcoded `historical_sample_count=10, historical_accuracy=85.0` from `api/verdict_intelligence.py` and `PolicySimulationService`, and removed hardcoded `NOT_CALIBRATED` bypass in `VerdictTriageAgent`. Live triage now reads persisted empirical rule stats and records both `VerdictTrustAssessmentRecord` and `EvidenceSufficiencyAssessmentRecord`.
- Fixed `is_calibrated` mismatch between `score_to_ordinal` and `apply_guardrails` inside `VerdictTrustworthinessEngine.evaluate_verdict_trust`.

---

## 3. Known Methodological Limitations
1. **Cold-Start Empirical Coverage:** In a fresh or low-volume database (`< 30` balanced human-adjudicated labels per rule), `is_calibrated` remains `False` and ordinal trust scores stay capped at `<= 6/10` (`PARTIALLY_VALIDATED` or `NOT_CALIBRATED`). Passing deterministic structural validation does **not** prove statistical production accuracy on unseen real-world SOC traffic.
2. **Heuristic Textual Grounding Limits:** While structured canonical ID citations are exact, unstructured fallback claims depend on normalized string and token matching rather than natural-language entailment models.
3. **Single-Process Async Lock:** Per-incident `asyncio.Lock` prevents duplicate writes within one FastAPI/uvicorn worker process; horizontal multi-process deployments require PostgreSQL advisory/row locks or Celery queue partitioning.

