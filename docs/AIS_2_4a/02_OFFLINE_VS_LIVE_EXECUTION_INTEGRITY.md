# AIS 2.4a — Offline vs. Live Execution Integrity

**Project:** Verdictum AI  
**Subsystem:** Agent Intelligence Studio (AIS)  
**Document:** `02_OFFLINE_VS_LIVE_EXECUTION_INTEGRITY.md`  
**Phase:** AIS 2.4a (Live Inference Provenance & TP Verdict Integrity)  
**Date:** November 23, 2026  
**Status:** IMPLEMENTED & ENFORCED  

---

## 1. Executive Summary

In AIS 2.4, an empirical integrity defect was identified: offline deterministic heuristic simulations were not clearly separated from real GPU inference in benchmark reporting, creating potential ambiguity around whether measurements reflected real vLLM execution or offline testing.

Under AIS 2.4a, a strict, auditable execution provenance taxonomy is implemented and enforced across all evaluation harnesses, services, and reporting pipelines. Offline mock proposals can never be represented as real GPU inference, and missing runtime measurements cannot be filled with plausible synthetic defaults.

---

## 2. Four-Tier Execution Provenance Taxonomy

The benchmark harness now strictly categorizes every single incident execution into one of four mutually exclusive, non-overlapping provenance states:

| Execution Mode / Provenance | Definition & Eligibility | Recorded Fields & Behavior |
|---|---|---|
| `LIVE_PROVIDER` | Genuine, completed model-provider response via network inference API (e.g., vLLM / OpenAI-compatible endpoint). Only these count toward live GPU latency, throughput, and wire accuracy. | `is_live_measurement = true`, measured `latency_ms`, actual wire `prompt_tokens`, `completion_tokens`, `total_tokens`, `finish_reason` (`stop` or `length`), `prompt_hash`, `policy_version`, `raw_model_response_id`. |
| `PREFLIGHT_ABSTENTION` | Pre-inference gating: execution was halted before dispatching inference because either critical evidence was missing (`preflight.must_abstain_immediately`) or the prompt exceeded context budgeting (`CONTEXT_WINDOW_EXCEEDED`). Zero GPU compute consumed. | `is_live_measurement = false`, `latency_ms = 0`, `prompt_tokens = 0`, `completion_tokens = 0`, `total_tokens = 0`, `finish_reason = "abstained_preflight"`, `raw_proposed_verdict = None`. |
| `PROVIDER_FAILURE` | An attempted live network inference call to the model provider failed due to network connection refusal, timeout, HTTP 5xx error, or unparseable payload. | `is_live_measurement = false`, `finish_reason = "provider_error"`, measured timeout/elapsed latency, error diagnostics recorded, decisive accepted = false. |
| `OFFLINE_SIMULATION` | Offline deterministic heuristic proposal used in development, testing, and CI/CD environments without live GPU connectivity. | `is_live_measurement = false`, `latency_ms = null`, `prompt_tokens = null`, `completion_tokens = null`, `total_tokens = null`, `finish_reason = null`. |

---

## 3. Auditable Verification Fields on Every Incident Record

In `backend/app/services/empirical_benchmark_harness.py`, `BenchmarkIncidentResult` has been upgraded with eight cryptographic and provable audit fields:

```python
@dataclass
class BenchmarkIncidentResult:
    # Core Verdict & Ground Truth
    incident_id: str
    rule_id: str
    rule_name: str
    ground_truth_label: str
    raw_proposed_verdict: Optional[str]
    raw_proposed_confidence: float
    raw_proposed_reason: str
    final_authoritative_verdict: str
    is_decisive_accepted: bool
    validation_status: str
    validation_reason_codes: List[str]
    trust_score: int
    raw_trust_score: float
    schema_compliant: bool
    grounding_ratio: float

    # Execution Provenance
    execution_provenance: str  # LIVE_PROVIDER, OFFLINE_SIMULATION, PREFLIGHT_ABSTENTION, PROVIDER_FAILURE
    is_live_measurement: bool
    finish_reason: Optional[str]
    requested_max_tokens: Optional[int]

    # Stage 2 Provable Audit Fields (AIS 2.4a)
    evaluation_run_id: Optional[str]
    model_name: Optional[str]
    provider_name: Optional[str]
    prompt_hash: Optional[str]
    policy_version: Optional[str]
    raw_model_response_id: Optional[str]
    executed_at_utc: Optional[str]
    execution_git_sha: Optional[str]
```

---

## 4. Prohibition of Mock and Default Fabrication

The codebase strictly enforces the following invariant rules:
1. **No Synthetic Latency or Tokens:** If an incident is evaluated in `OFFLINE_SIMULATION`, `latency_ms`, `prompt_tokens`, `completion_tokens`, and `total_tokens` MUST remain `None`. They must never be populated with estimated or simulated numbers.
2. **Distinct Accounting Denominators:** `BenchmarkMetrics` calculates separate counts for:
   - `live_provider_count`
   - `real_gpu_dispatched_count`
   - `successful_complete_responses_count`
   - `offline_simulation_count`
   - `preflight_abstained_count`
   - `provider_failure_count`
3. **Transparent Live Gating:** If the model server is unreachable, the system must declare `BLOCKED_GPU_UNAVAILABLE` or `NOT_MEASURED` rather than silently degrading to simulated responses while presenting them as live.

---

## 5. Verification & Regression Coverage

The provenance taxonomy is unit-tested in `backend/tests/test_ais_2_4a_tp_grounding.py::test_provenance_taxonomy_types` and verified across both pilot and full benchmark evaluations.
