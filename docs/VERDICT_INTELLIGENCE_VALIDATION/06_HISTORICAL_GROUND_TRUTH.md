# Historical Ground Truth & Blind Evaluation (AIS 2.1)

## 1. Overview and Core Purpose

A fundamental hazard in evaluating LLM decision quality against historical incident data is **data leakage**. Historical SIEM records invariably contain analyst investigation notes, resolution codes, disposition tags, and ticket status strings (e.g., `"Resolution: Closed - False Positive: Authorized backup job"`).

If these fields are passed to the language model during historical replay, the model achieves artificial high accuracy by reading the analyst's conclusion rather than reasoning over raw telemetry.

The **Historical Ground Truth Validator** (`backend/app/services/historical_ground_truth_validator.py`) enforces strict sanitization boundaries, robust ground truth adjudication, and deterministic dataset splitting.

---

## 2. Deep Sanitization Pipeline (Zero Data Leakage)

Before an incident payload is delivered to any model prompt or inference pipeline, `sanitize_incident_for_inference` executes a recursive scrubbing pass:

### Stripped Fields & Metadata:
- **Analyst Comments & Resolution Strings**:
  `analyst_notes`, `investigation_summary`, `resolution`, `closure_reason`, `comments`, `work_notes`, `remediation_notes`.
- **Disposition & Verdict Tags**:
  `verdict`, `disposition`, `incident_status`, `state`, `ticket_state`, `analyst_decision`, `is_tp`, `is_fp`.
- **Analyst Attribution**:
  `assigned_analyst`, `closed_by`, `reviewer`, `auditor_id`.
- **Direct Semantic Keywords**:
  Payload text is scrubbed of leakage tokens such as `"true positive"`, `"false positive"`, `"benign"`, `"malicious"`, `"authorized activity"` when found in metadata headers.

```python
LEAKAGE_KEYS = {
    "analyst_verdict", "disposition", "resolution_notes", "closure_code",
    "analyst_notes", "closed_by", "investigation_verdict", "resolution",
    "ticket_status", "incident_disposition", "manual_classification"
}
```

The resulting sanitized payload contains exclusively raw SIEM telemetry (network flow records, process execution trees, authentication logs, host metadata) ensuring a genuine **blind test**.

---

## 3. Ground Truth Adjudication Framework

In real-world SOCs, historical tickets often contain inconsistent, free-text, or conflicting classifications from different analysts.

`HistoricalGroundTruthValidator.adjudicate_ground_truth` resolves heterogeneous historical outcomes into standard labels:

| Historical Resolution Code / Text | Adjudicated Canonical Label | Adjudication Confidence |
|---|---|---|
| `"closed_malicious"`, `"confirmed_incident"`, `"escalated_to_tier3"`, `"threat_mitigated"` | `TRUE_POSITIVE` | 0.95 |
| `"closed_benign"`, `"false_alarm"`, `"authorized_activity"`, `"authorized_scan"` | `FALSE_POSITIVE` | 0.95 |
| `"inconclusive"`, `"unresolved"`, `"pending_evidence"`, `"analyst_uncertain"` | `REQUIRES_ANALYST_ATTENTION` | 0.85 |
| Missing, contradictory, or unparsable resolution tags | `REQUIRES_ANALYST_ATTENTION` | 0.50 |

Adjudicated records are stored in `HistoricalGroundTruthRecord` (`backend/app/models/verdict_intelligence.py`) with explicit foreign keys to the original incidents and audit tracking of who adjudicated the outcome.

---

## 4. Deterministic 4-Way Hash Partitioning

To ensure reproducible benchmarks and prevent partition leakage across evaluation runs, datasets are split using a **deterministic cryptographic hash** of the `incident_id`:

$$\text{Hash Value} = \frac{\text{int}(\text{SHA256}(\text{incident\_id})[:8], 16)}{2^{32} - 1} \in [0.0, 1.0)$$

### Partition Distribution:
1. **Train Split ($0.0 \le \text{Hash} < 0.50$) [50%]**:
   Used for policy generation, prompt few-shot examples, and archetype calibration.
2. **Validation Split ($0.50 \le \text{Hash} < 0.70$) [20%]**:
   Used for threshold tuning and guardrail parameter optimization.
3. **Blind Benchmark Split ($0.70 \le \text{Hash} < 0.90$) [20%]**:
   Strictly held-out incidents used to compute published empirical accuracy, ECE, and Brier scores.
4. **Stress & Adversarial Split ($0.90 \le \text{Hash} \le 1.00$) [10%]**:
   Curated edge cases, truncated payloads, and synthetic evasion attempts used for robustness testing.

Because assignment relies on `SHA256(incident_id)`, incidents remain in their exact assigned partition indefinitely, regardless of execution order or system reboots.
