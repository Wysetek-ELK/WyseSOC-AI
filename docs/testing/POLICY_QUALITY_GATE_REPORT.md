# Policy Quality Gate Report (Gates G1–G8)

- **Updated At:** 2026-11-10T19:55:00+05:30
- **Repository Commit:** `0148142` (`0148142f3abd6dad87a903b90f7b25edb8d41def`)
- **Primary Implementation:** [`policy_quality_validator.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/policy_quality_validator.py), [`prompt_studio_service.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/prompt_studio_service.py), [`api/prompts.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/api/prompts.py)

---

## 1. Eight-Gate Framework Overview

`PolicyQualityValidator.validate_policy_quality()` scores candidate `PromptVersion` policies across 100 total points split between **85 structural points (G1–G7)** and **15 empirical simulation points (G8)**. **Zero blocking issues** are mandatory for `approval_eligible = True` — high total scores never override a blocking gate failure.

| Gate ID | Name | Weight | Structural / Empirical | Hard Blockers Enforced |
|---|---|---:|---|---|
| **G1** | `G1_RULE_INTEGRITY` | 20.0 | Structural | Missing authoritative SIEM rule definition on threshold-dependent rules; invented numeric thresholds without SIEM backing. |
| **G2** | `G2_ARCHETYPE_RELEVANCE` | 20.0 | Structural | Unclassified/inadequate telemetry mappings; cross-domain copy-paste malware/process pollution on network rules. |
| **G3** | `G3_EVIDENCE_FEASIBILITY` | 15.0 | Structural | Unbound `RuleEvidenceContract`; critical archetype telemetry left unmapped. |
| **G4** | `G4_TP_CRITERIA_VALIDITY` | 10.0 | Structural | Missing, tautological, or purely alert-repeating True Positive criteria. |
| **G5** | `G5_FP_CRITERIA_VALIDITY` | 10.0 | Structural | Blanket RFC-1918 or loopback (`127.0.0.1`, `::1`) benign assumptions; prescriptive hardcoded confidence ranges (`80-98%`). |
| **G6** | `G6_ABSTENTION_ESCALATION` | 15.0 | Structural | Undefined mandatory abstention (`REQUIRES_ATTENTION`) criteria; unsafe internal-target escalation carve-outs. |
| **G7** | `G7_POLICY_CONSISTENCY` | 10.0 | Structural | Blank Section 4 `required_evidence` when contract defines critical fields; identical contradictory Section 5 (`tp_indicators`) vs Section 6 (`fp_indicators`). *(Partial field omissions emit WARNING.)* |
| **G8** | `G8_SIMULATION_REGRESSION` | 15.0 | Empirical | `REGRESSION_DETECTED` or `critical_false_negatives > 0` blocks approval (`FAILED`). Sample count `< 5`, no simulation run, or stale `policy_digest` yields `WARNING` (0/15 empirical score). |

---

## 2. Root Causes Identified & Remediated

1. **G5 Dilution by Shared Common Baseline (`policy_quality_validator.py:546`):**
   - *Root Cause:* `_evaluate_gate_5_fp_criteria` concatenated `fp_indicators + common_prompt` before searching for `"not"` and `"verify"`. Because `ENTERPRISE_SOC_BASELINE_V2` in `common_prompt` naturally contains `"not"` and `"verify"`, blanket `"Internal RFC-1918 traffic is benign"` rules in `fp_indicators` escaped blocking!
   - *Fix & Verification:* G5 now checks `fp_indicators` directly (`fp_lower`) without common-baseline dilution. Verified by `test_quality_gates_g5_baseline_dilution_g7_blockers_and_g8_stale_digest`.
2. **G7 Inability to Emit Hard Blockers (`policy_quality_validator.py:618`):**
   - *Root Cause:* `_evaluate_gate_7_consistency` only produced warnings regardless of whether Section 4 completely ignored critical contract requirements or contradicted TP/FP sections.
   - *Fix & Verification:* Added blocking conditions (`G7_CONTRACT_EVIDENCE_OMITTED`, `G7_TP_FP_SELF_CONTRADICTION`) while preserving existing warning behavior on minor field naming variances (`test_policy_remediation_and_ground_truth.py` `res_v1` / `res_v2` 100.0 structural score preserved).
3. **G8 Digest Staleness, Approval Bypass & Rollback Bypass (`prompt_studio_service.py`, `api/prompts.py`):**
   - *Root Cause:* `PromptStudioService.approve_version` invoked `validate_policy_quality` without loading `HistoricalEvaluationRunRecord` simulation results; edited policies reused stale G8 runs without `policy_digest` validation; `rollback_version` activated legacy policies with zero gate checks; `/api/prompts/summary` hardcoded `simulation_status="NOT_EVALUATED"`.
   - *Fix & Verification:* `approve_version` queries the latest completed run and enforces G8 regression blockers; `_evaluate_gate_8_simulation` invalidates stale `policy_digest` runs; `rollback_version` enforces G1–G7 validation before activation; `/summary` reports live persisted statuses. Verified in `test_audit_remediations.py`.

---

## 3. Unresolved Gate & Empirical Constraints

- **Insufficient Historical Data (`G8_INSUFFICIENT_DATA`):** Rules lacking at least **5 independently verified, rule-matched human ground-truth incidents** legitimately remain `WARNING` (0/15 empirical points, overall max structural-only score 85/100) rather than fabricating simulated accuracy.
- **Simulated vs. Live LLM Evaluation in G8:** Unless historical evaluation runs are executed with `provider_type="OPENAI_COMPATIBLE"` against a live GPU node, G8 historical simulation measures deterministic pipeline safety/policy responsiveness under `SimulatedModelProvider`.

