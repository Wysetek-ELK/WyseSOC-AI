# Phase 8 Verdict Accuracy, Grounding & Decision Correctness Report

**Stage Covered:** Stage 4 (End-to-End Incident-to-Verdict Pipeline & Safety Guardrails)

## 1. Critical Defect Discovered & Remediated During Stage 4 (`P8-DEF-08`)

During Stage 4 execution against `PH_RULE_PHASE8_EXFIL` (`NETWORK_EXFILTRATION`), legitimate `TRUE_POSITIVE` and `FALSE_POSITIVE` incidents carrying all observed network exfiltration fields (`network.source_ip`, `network.destination_ip`, `network.bytes_out`, `network.direction`) received `evidence_completeness = 0.333` (`4 / 12`) in [`EvidencePreflightValidator`](../../backend/app/services/evidence_preflight_validator.py) and were downgraded to `REQUIRES_ATTENTION` (`TP_CRITERIA_UNSATISFIED`).

- **Root Cause:** `EvidencePreflightValidator.validate_preflight` divided satisfied fields by `len(contract.required_evidence)`, which included non-mandatory `CONDITIONAL` enrichment fields (`user.name`, `network.destination_port`, `network.destination_domain`, `network.protocol`, `dlp.findings`, `process.name`) and rule-level `detection.*` threshold metadata emitted by [`EvidenceRequirementMapper`](../../backend/app/services/evidence_requirement_mapper.py). Note also that `"detection.threshold"` (marked `critical=True`) does not originate from event normalization, risking blanket abstention on rules with parsed thresholds.
- **Remediation:** Updated `EvidencePreflightValidator.validate_preflight` to compute completeness over mandatory event-level `CORE` / `critical` / `required_for_*` requirements (excluding `detection.*` rule metadata and `CONDITIONAL`/`OPTIONAL`/`UNVERIFIED` enrichments) while retaining missing optional context in `missing_evidence_fields`. With all 26 existing preflight/validator/audit tests still passing, Stage 4 `S01` completeness rose from `0.333` (`4/12`) to `0.80` (`4/5`), enabling validated `TRUE_POSITIVE` and `FALSE_POSITIVE` decisions.

## 2. Stage 4 Pipeline Execution Matrix (Observed Traces)

All pipeline traces were persisted to [`stage4_e2e_traces.json`](./evidence/traces/stage4_e2e_traces.json) by [`test_phase8_stage4_complete_13_scenario_matrix_and_trace_export`](../../backend/tests/test_phase8_integration.py):

| Scenario | Proposed | Authoritative Verdict | Validation Status | Trust Score | Calibration Status | GT Leaked | Outcome |
|---|---|---|---|---:|---|---|---|
| `S01_VERIFIED_MALICIOUS_TP_AND_S13_GT_ISOLATION` | `TRUE_POSITIVE` | `TRUE_POSITIVE` (`92.0%`) | `VALIDATED` | `6` | `NOT_CALIBRATED` | `false` | Decisive TP + DB assessments persisted |
| `S02_VERIFIED_AUTHORIZED_FP` | `FALSE_POSITIVE` | `FALSE_POSITIVE` (`89.0%`) | `VALIDATED` | `6` | `NOT_CALIBRATED` | `false` | Decisive benign authorization accepted |
| `S03_MISSING_MANDATORY_EVIDENCE` | `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` (`0.0%`) | `INSUFFICIENT` (`PREFLIGHT_GUARD`) | `null` | `null` | `false` | Abstained prior to inference |
| `S04_CONTRADICTORY_EVIDENCE` | `TRUE_POSITIVE` | `REQUIRES_ATTENTION` (`0.0%`) | `REJECTED` | `6` | `NOT_CALIBRATED` | `false` | Contradiction (`Process Blocked=true`) overruled TP |
| `S05_HALLUCINATED_CLAIMS` | `TRUE_POSITIVE` | `REQUIRES_ATTENTION` (`0.0%`) | `REJECTED` | `4` | `NOT_CALIBRATED` | `false` | Unverified IP `203.0.113.250` blocked |
| `S06_EMPTY_CLAIMS_BYPASS_BLOCKED` | `FALSE_POSITIVE` | `REQUIRES_ATTENTION` (`0.0%`) | `INSUFFICIENT_EVIDENCE` | `4` | `NOT_CALIBRATED` | `false` | Empty `supporting_claims` blocked FP bypass |
| `S07_MISSING_OR_DRAFT_POLICY` | `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` (`0.0%`) | `POLICY_NOT_APPROVED` | `null` | `null` | `false` | Unapproved policy blocked (`reevaluation_eligible=true`) |
| `S08_CONTEXT_OVERFLOW_ABSTENTION` | `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` (`0.0%`) | `CONTEXT_WINDOW_EXCEEDED` | `null` | `NOT_CALIBRATED` | `false` | Budget overflow triggered safe abstention |
| `S09_MALFORMED_MODEL_OUTPUT_ABSTENTION` | `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` (`0.0%`) | `VALIDATED` | `4` | `NOT_CALIBRATED` | `false` | Invalid label `"MALICIOUS_MAYBE"` coerced safely |
| `S10_LOCAL_LLM_UNAVAILABLE_FAIL_SAFE` | `null` | `FAIL_CLOSED_NO_FAKE_VERDICT` | `LLM_UNAVAILABLE` | `null` | `null` | `false` | `LocalLLMUnavailableError` raised; `ai_verdict=None` |
| `S11_RECOVERABLE_ABSTENTION_REEVALUATED` | `TRUE_POSITIVE` | `TRUE_POSITIVE` (`91.0%`) | `VALIDATED` | `6` | `NOT_CALIBRATED` | `false` | Reevaluated via `reconcile_pending_triage` (`attempt=2`) after approval |
| `S12_BOUNDED_RETRY_CAP` | `null` | `REQUIRES_ATTENTION` | `POLICY_NOT_APPROVED` | — | — | `false` | Skipped at `reevaluation_attempts=3` (`max=3` enforced) |

*(Note: Live unmocked Qwen 2.5 AWQ accuracy vs. human ground truth on production incidents remains unmeasured because Server 2 GPU inference was offline.)*

