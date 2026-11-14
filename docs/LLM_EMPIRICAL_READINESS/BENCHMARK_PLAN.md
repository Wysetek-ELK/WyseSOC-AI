# Verdictum AI — Empirical Benchmark Evaluation Plan

## 1. Evaluation Objectives

The empirical benchmark is designed to evaluate the real-world classification accuracy, evidence-grounding fidelity, and safety reliability of the local LLM (`Qwen/Qwen2.5-7B-Instruct-AWQ`) running on Server 2 (GPU) against verified historical FortiSIEM incidents.

The benchmark establishes:
1. **Unsafe False Positive Defense**: Verify with statistical certainty that zero verified malicious attacks (`VERIFIED_TP`) are accepted as False Positives ($N_{\text{unsafe FP}} = 0$).
2. **Empirical Precision and Recall**: Quantify True Positive and False Positive classification performance on blinded production-origin incident telemetry.
3. **Evidence Grounding Ratio**: Ensure that model rationales are grounded strictly in normalized, canonical telemetry rather than hallucinated facts or invented tickets.
4. **Selective Classification Calibration**: Validate that the 1–10 ordinal trust score correctly separates high-accuracy automated decisions from uncertain incidents requiring human analyst triage.
5. **Operational Viability**: Measure token usage, inference latency (mean and P95), and estimated GPU compute cost per evaluated incident.

---

## 2. Dataset Composition & Adjudication

### 2.1 Available Datasets
The evaluation cohort is derived from two historical FortiSIEM incident repositories:
- **`fixtures/Incident json.zip`**: 20 production FortiSIEM incident archives containing full raw syslog events, EDR alerts, and analyst resolution metadata:
  - 10 incidents from `PH_RULE_CS_SUSPICIOUS_ACTIVITY` (CrowdStrike Indicators of Attack).
  - 10 incidents from `PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE` (Prisma SASE File Threat Detection).
- **`backend/ai_verdict.db`**: 26 incident records, 197 linked events, and 24 historical ground truth rows.

### 2.2 Label Adjudication Protocol
Every historical incident is adjudicated into one of four deterministic classes using `HistoricalGroundTruthValidator.adjudicate_label()`:
1. **`VERIFIED_TP` (Confirmed Malicious)**:
   - Resolution explicitly indicates `True Positive`, `Malicious`, or `Attack`.
   - Analyst notes contain investigative evidence (e.g., "case raised and client are working on it", "admin compromise observed").
2. **`VERIFIED_FP` (Confirmed Benign)**:
   - Resolution explicitly indicates `False Positive`, `Benign`, or `Authorized`.
   - Analyst notes contain verified business justification (e.g., "legitimate activity, nothing suspicious observed", "approved support tool").
3. **`UNVERIFIED` (Excluded from Accuracy Denominator)**:
   - Resolution was set by legacy automated ML ("Resolution set by Machine Learning").
   - Closure contains only containment actions ("kill process is true", "proccess is kiled") without affirmative benign justification.
   - Status indicates generic closure ("Closed", "Auto-cleared") without analyst TP/FP rationale.
4. **`UNKNOWN`**: Open, unresolved, or new incidents lacking adjudication.

---

## 3. Strict Blinding & Anti-Data-Leakage Protocol

To guarantee empirical evaluation validity, the LLM and the retrieval context must be strictly blinded from ground truth:

```
+-------------------------------------------------------------------------------+
|                       Blinding & Anti-Leakage Protocol                        |
+-------------------------------------------------------------------------------+
|                                                                               |
|  Raw Historical Incident JSON                                                 |
|     [resolution, clearedReason, clearedTime, clearedUser, comments, ...]      |
|                                                                               |
|       |                                                                       |
|       v                                                                       |
|  HistoricalGroundTruthValidator.sanitize_incident_for_inference()             |
|     - Deep recursive walk stripping 12 canonical leakage keys                 |
|     - Strips camelCase, snake_case, and free-text resolution notes            |
|     - Verifies sanitized dictionary against _NORMALIZED_LEAKAGE_KEYS          |
|                                                                               |
|       |                                                                       |
|       v                                                                       |
|  Sanitized Model Telemetry Payload                                            |
|     [Only observable network, process, file, user, and alert attributes]     |
|                                                                               |
|       |                                                                       |
|       v                                                                       |
|  Prompt Compiler (PolicyCompilerService)                                      |
|     - Injects sanitized canonical evidence                                    |
|     - RAG retrieval self-excludes current incident and post-creation events   |
|                                                                               |
|       |                                                                       |
|       v                                                                       |
|  Local LLM Input Prompt (100% Zero-Leakage Guarantee)                         |
+-------------------------------------------------------------------------------+
```

---

## 4. Dataset Partitioning & Cross-Validation

To prevent host-level telemetry memorization:
- **Host-Isolated Stratified Splitting**: Incidents from the same physical endpoint (`Host Name` / `reportingIp`) are grouped together and never split between historical RAG precedents and test evaluation sets.
- **5-Fold Cross-Validation** or **60/40 Host Split**:
  - Fold training/precedent set: Used strictly for semantic precedent retrieval.
  - Fold test set: Evaluated in blind inference mode.

---

## 5. Metrics & Statistical Acceptance Gates

### 5.1 Primary Metrics

| Metric | Formulation | Target Threshold | Hard Blocker Gate |
|---|---|---|---|
| **Unsafe FP Rate** | $N_{\text{unsafe FP}} / N_{\text{verified TP}}$ | **0.00%** | $> 0.00\%$ triggers immediate halt |
| **JSON Schema Compliance** | $N_{\text{compliant}} / N_{\text{total}}$ | $\ge 98.0\%$ | $< 95.0\%$ |
| **True Positive Recall** | $\text{TP} / (\text{TP} + \text{FN})$ | $\ge 85.0\%$ | $< 75.0\%$ |
| **True Positive Precision** | $\text{TP} / (\text{TP} + \text{FP})$ | $\ge 80.0\%$ | $< 70.0\%$ |
| **False Positive Precision** | $\text{TN} / (\text{TN} + \text{FN})$ | $\ge 85.0\%$ | $< 75.0\%$ |
| **Claim Grounding Ratio** | $\text{Grounded Claims} / \text{Total Claims}$ | $\ge 85.0\%$ | $< 70.0\%$ |
| **P95 Inference Latency** | 95th percentile elapsed ms | $\le 8000\text{ ms}$ | $> 15000\text{ ms}$ |
| **Estimated GPU Cost** | Total tokens $\times \$0.0004 / 1\text{k}$ | $\le \$0.05 / \text{incident}$ | $> \$0.15$ |

### 5.2 Wilson Score 95% Confidence Intervals
For all proportions $p = x / n$, Wilson score intervals are computed:
$$w = \frac{p + \frac{z^2}{2n} \pm z \sqrt{\frac{p(1-p)}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}$$
where $z = 1.95996$ for a two-sided 95% confidence level.

---

## 6. Statistical Power & Sample Size Roadmap

- **Current Available Verified Cohort**: $N = 6$ verified cases ($N < 30$).
  - At $N = 6$, confidence interval half-width is $\approx \pm 35\%$.
  - The benchmark harness automatically flags `statistical_power_warning = True` to prevent mistaking sample limitations for model failure.
- **Target Phase 2 Cohort**: $N \ge 100$ verified historical incidents:
  - 50 verified True Positives + 50 verified False Positives.
  - Bounds 95% Wilson intervals within $\pm 7.5\%$.
  - Historical ingestion pipeline will sync additional FortiSIEM production archives into `backend/ai_verdict.db`.

