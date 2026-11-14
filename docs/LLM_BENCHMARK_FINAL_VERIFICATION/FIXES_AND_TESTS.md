# Verdictum AI — Live Benchmark Integrity Verification: Fixes & Tests

**Document Version**: 2.0.0  
**Date**: November 2026  
**Status**: VERIFIED & GREEN  
**Regression Suite**: 97 Automated Tests Passing  

---

## 1. Summary of Code Changes

### 1.1 `backend/app/services/empirical_benchmark_harness.py`

#### A. Quarantining Synthetic Test Fixtures from Evaluation Denominators
- **Problem**: In `backend/ai_verdict.db`, synthetic test fixtures `INC-DEBUG-01` and `INC-DEBUG-02` had populated raw payloads and dummy resolutions (`True Positive`, `False Positive`), causing them to enter the empirical evaluation cohort and artificially inflate verified counts.
- **Fix**: Updated `load_dataset_from_db` and `load_dataset_unified` to accept `include_synthetic: bool = False`. By default, all incidents prefixed with `INC-DEBUG-`, `INC-TEST-`, or `SYNTHETIC-` are quarantined from empirical benchmarks. They remain accessible for functional unit testing when `include_synthetic=True`.

```python
# Exclude purely synthetic debug/test incidents from empirical accuracy evaluation cohorts
if not include_synthetic and (
    str(inc_id).startswith("INC-DEBUG-")
    or str(inc_id).startswith("INC-TEST-")
    or str(inc_id).startswith("SYNTHETIC-")
):
    continue
```

#### B. Context Window Overflow Fail-Closed Handling
- **Problem**: In live inference mode, if an incident's telemetry exceeded the model context window (e.g., 48,000 tokens for incidents with massive event bursts), `TokenBudgetService.budget_prompt` returned `can_proceed_to_inference=False`. The legacy harness lacked an early-exit check and attempted to call the provider with invalid arguments.
- **Fix**: Added explicit fail-closed guard matching production `verdict_pipeline.py`. If context budget is exceeded without naive truncation, the incident safely abstains with `validation_status="CONTEXT_WINDOW_EXCEEDED"`, `final_authoritative_verdict="REQUIRES_ATTENTION"`, and `is_decisive_accepted=False`.

#### C. Production Parity for Live Provider Invocation
- **Problem**: The live provider branch previously called `OpenAICompatibleModelProvider.generate_verdict(user_prompt=budgeted.final_prompt_text)`. `OpenAICompatibleModelProvider` was misspelled, and `final_prompt_text` was not an attribute on `BudgetedPromptResult`.
- **Fix**: Replaced with production-identical call to `OpenAICompatibleProvider.analyze_incident(...)`:
  - Passes `incident_payload=budgeted.budgeted_incident_payload`
  - Passes `rule_spec=rule_spec`
  - Passes `prompt_text=prompt_text` (incorporating Section 11 evidence citations and nine-section compiled policy)
  - Passes `prompt_version_number=compiled_policy.version_number`
  - Accurately captures real live token usage (`prompt_tokens`, `completion_tokens`, `total_tokens`) and live execution latency (`elapsed_ms`).

#### D. Guardrail G5 & Autonomous Action Gating Reconciliation
- **Problem**: Decisive `TRUE_POSITIVE` and `FALSE_POSITIVE` verdicts were recorded as decisive with `auto_closure_allowed=True` even when Trust Score was $< 7$ (uncalibrated, 5/10), violating Guardrail G5.
- **Fix**: Reconciled the distinction between **Advisory Decision Support** (analyst-assisted triage) and **Autonomous Execution**:
  1. `trust_res = VerdictTrustworthinessEngine.evaluate_verdict_trust(...)` evaluates multi-dimensional trust and applies deterministic guardrails.
  2. `is_autonomous_eligible` strictly requires `trust_score >= 7`, `raw_trust_score >= 70.0`, `is_calibrated is True`, and `"G5_LOW_TRUST_SCORE" not in guardrails_triggered`.
  3. `autonomous_verdict` is demoted to `REQUIRES_ATTENTION` whenever `is_autonomous_eligible` is False.
  4. `auto_incident_closure_allowed` is strictly blocked (`False`) unless `is_autonomous_eligible is True`, `val_res.final_verdict == "FALSE_POSITIVE"`, and `trust_res.effective_verdict == UserVisibleVerdict.FALSE_POSITIVE`.

```python
# Guardrail G5 strictly enforces trust_score >= 7 and empirical calibration for autonomous decisions
is_autonomous_eligible = bool(
    trust_res.trust_score is not None
    and trust_res.trust_score >= 7
    and trust_res.raw_trust_score >= 70.0
    and trust_res.is_calibrated
    and "G5_LOW_TRUST_SCORE" not in guardrails_triggered
)
autonomous_verdict = (
    val_res.final_verdict
    if (is_autonomous_eligible and val_res.is_decisive_accepted)
    else "REQUIRES_ATTENTION"
)

auto_closure_allowed = bool(
    is_autonomous_eligible
    and val_res.is_decisive_accepted
    and val_res.final_verdict == "FALSE_POSITIVE"
    and trust_res.effective_verdict == UserVisibleVerdict.FALSE_POSITIVE
)
```

#### E. Duplicate-Cluster Aware Metric Calculation
- **Problem**: Repetitive batch-closed alerts inflated sample size and statistical confidence.
- **Fix**: `calculate_cohort_metrics` computes both:
  1. Incident-level metrics ($N=20$).
  2. Cluster-level metrics ($N=15$ unique clusters, $N=4$ verified clusters).
  3. Autonomous decisive count vs advisory decisive count.

---

### 1.2 `backend/app/services/historical_ground_truth_validator.py`

#### A. Operational Escalation vs Forensic Adjudication Detection
- **Added**: `is_escalation_or_notification_only` class method to detect operational comments (*"Mail has been sent already"*, *"Case has been raised for the similar incidents."*, *"Informed to client"*).
- **Updated**: `adjudicate_label` to accept `strict_forensic_only: bool = False`. When `strict_forensic_only=True`, escalation notes without forensic confirmation are classified as `UNVERIFIED`. When `strict_forensic_only=False` (default), backward compatibility is preserved for operational triage ground truth.

```python
@classmethod
def is_escalation_or_notification_only(
    cls,
    raw_resolution: Optional[str] = None,
    cleared_reason: Optional[str] = None,
    analyst_comments: Optional[str] = None,
    cleared_user: Optional[str] = None,
) -> bool:
    combined = f"{raw_resolution or ''} {cleared_reason or ''} {analyst_comments or ''}".lower()
    notification_markers = (
        "mail has been sent", "mail sent", "email sent",
        "informed to client", "case has been raised", "case raised",
        "ticket raised", "ticket created", "notified client", "escalated to client"
    )
    forensic_confirmation_markers = (
        "confirmed attack", "malware confirmed", "malicious activity confirmed",
        "c2 connection", "compromised", "credential theft", "threat actor",
        "ransomware", "unauthorized access confirmed", "exploit confirmed", "lateral movement"
    )
    has_notification = any(m in combined for m in notification_markers)
    has_forensic = any(m in combined for m in forensic_confirmation_markers)
    return bool(has_notification and not has_forensic)
```

---

## 2. Automated Regression Test Suite

All 17 tests in `backend/tests/test_empirical_benchmark_harness.py` passed with zero errors or warnings:

| # | Test Function | Purpose & Validation Scope | Status |
|---|---|---|---|
| 1 | `test_load_dataset_from_zip` | Verifies loading 20 historical FortiSIEM incidents from zip fixtures, label adjudication, and zero data leakage. | **PASSED** |
| 2 | `test_load_dataset_from_db` | Verifies loading historical incidents from SQLite DB in read-only mode with synthetic fixtures quarantined. | **PASSED** |
| 3 | `test_load_dataset_unified` | Verifies cross-source merging, incident deduplication, and zero duplicate IDs. | **PASSED** |
| 4 | `test_blinding_integrity_blocks_all_leakage` | Verifies that `resolution`, `clearedReason`, `comments`, and `clearedUser` are completely stripped from sanitized payloads. | **PASSED** |
| 5 | `test_single_incident_offline_evaluation` | Verifies single-incident execution through production-equivalent pipeline, offline metrics unmeasured, trust score bounded [1, 10]. | **PASSED** |
| 6 | `test_deterministic_positive_tp_acceptance` | Positive test: Grounded TRUE_POSITIVE proposal with matching file and source IP telemetry is accepted as decisive TP. | **PASSED** |
| 7 | `test_deterministic_positive_fp_acceptance` | Positive test: Approved administrative management binary (`CcmExec.exe` in `C:\Windows\CCM`) is accepted as decisive FP, but auto-closure blocked by G5 (<30 samples). | **PASSED** |
| 8 | `test_deterministic_negative_unsupported_fp_rejection` | Negative test: FP asserted without maintenance ticket or approved administrative binary is strictly demoted to `REQUIRES_ATTENTION`. | **PASSED** |
| 9 | `test_deterministic_negative_fabrication_rejection` | Negative test: Hallucinated evidence citations not present in canonical evidence are rejected. | **PASSED** |
| 10 | `test_wilson_confidence_interval_calculation` | Validates mathematical correctness of 95% Wilson score interval calculation and edge case handling ($N=0$, $p=0$, $p=1$). | **PASSED** |
| 11 | `test_full_harness_run_and_report_generation` | Verifies master benchmark run across historical cohort, confusion matrix consistency, and GFM report generation. | **PASSED** |
| 12 | `test_production_and_benchmark_prompt_parity` | **PARITY PROOF**: Byte-for-byte matching of compiled system instructions, delimiter boundaries, token allocations, and compilation digests. | **PASSED** |
| 13 | `test_synthetic_fixtures_excluded_from_accuracy_denominators` | Confirms that `INC-DEBUG-*` fixtures in DB are excluded from empirical benchmarks by default, but available when `include_synthetic=True`. | **PASSED** |
| 14 | `test_guardrail_g5_blocks_autonomous_closure_when_trust_low` | Confirms that Guardrail G5 strictly blocks autonomous decisive actions and auto-closure when Trust Score $< 7$ / uncalibrated. | **PASSED** |
| 15 | `test_prohibition_of_fp_acceptance_solely_via_path_signature_system` | Confirms that signed binary in System32 running as `NT AUTHORITY\SYSTEM` CANNOT be accepted as FP without approved administrative binary or ITSM ticket. | **PASSED** |
| 16 | `test_duplicate_cluster_aware_evaluation` | Verifies 5 duplicate alerts across 4 duplicate clusters are correctly identified, leaving 15 unique clusters. | **PASSED** |
| 17 | `test_ground_truth_strict_forensic_adjudication` | Confirms operational escalation notes ("Mail sent", "Case raised") are recognized and demoted to `UNVERIFIED` under `strict_forensic_only=True`. | **PASSED** |

---

## 3. Comprehensive Multi-Suite Verification Results

Execution of the full regression suite confirmed zero regressions across all security, reliability, and intelligence modules:

```powershell
pytest backend/tests/test_verdict_reliability_1_1.py \
       backend/tests/test_verdict_reliability_1_2.py \
       backend/tests/test_verdict_reliability_1_3.py \
       backend/tests/test_empirical_safety_verification.py \
       backend/tests/test_empirical_benchmark_harness.py \
       backend/tests/test_verdict_intelligence_validation.py -v
```

### Result:
- **Total Test Cases**: **97 Passed, 0 Failed, 0 Warnings**
- **Execution Time**: **25.4 seconds**
- **Working Tree**: Clean, all tests green.
