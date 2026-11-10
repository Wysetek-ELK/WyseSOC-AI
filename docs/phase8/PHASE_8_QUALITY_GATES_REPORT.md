# Phase 8 Quality Gates (G1–G8) & Policy Governance Report

**Stage Covered:** Stage 6 (Agent Intelligence Studio Quality Gates G1–G8, Simulation Integrity & Stale Digest / Regression Gating)
**Raw Validation Output:** [`stage6_quality_gates.json`](./evidence/metrics/stage6_quality_gates.json)

## 1. Gate G8 Over-Credit Vulnerability Fixed (`P8-DEF-06`)

- **Defect Uncovered:** When [`PolicySimulationService`](../../backend/app/services/policy_simulation_service.py) executed replay on `Prisma_SASE_Suspicious_File_Threat_Detection_` (5 eligible cases, **0% decision coverage**, 100% abstention, `overall_accuracy=None`), Gate `G8` (`Simulation & Regression Validation`) previously treated any completed replay lacking explicit failures as passing and awarded `15.0 / 15.0 PASSED`, elevating `quality_score` from `70.0` to `85.0`.
- **Remediation:** Introduced `SimulationStatus.INCONCLUSIVE` in [`policy_quality.py`](../../backend/app/schemas/policy_quality.py) and updated [`PolicyQualityValidator`](../../backend/app/services/policy_quality_validator.py) so simulations with `decision_coverage == 0` or `overall_accuracy is None` emit `INCONCLUSIVE` / `G8 WARNING` (`G8_INCONCLUSIVE_SIMULATION`) with **`0.0 / 15.0`** empirical score.

## 2. G1–G8 Gate Evaluation Across Cloned Database Policy Versions

| Rule ID | Ver | Status | Quality Score | Empirical Score | G8 Status (`Sim Status`) | Approval Eligible | Key Gate Outcomes |
|---|---|---|---:|---:|---|---|---|
| `PH_RULE_CS_SUSPICIOUS_ACTIVITY` | v1 | `APPROVED` | `77.0` | `0.0` | `WARNING` (`INSUFFICIENT_DATA`) | `true` | `G1/G2/G3/G5 PASSED`; `G4/G6/G7/G8 WARNING` |
| `Prisma_SASE_Suspicious_File_Threat_Detection_` | v1 | `APPROVED` | `70.0` | `0.0` | `WARNING` (`INCONCLUSIVE`) | `true` | `G1/G3/G4/G5 PASSED`; `G8 WARNING (0.0/15)` |
| `PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT` | v2 | `DRAFT` | `85.0` | `0.0` | `WARNING` (`INSUFFICIENT_DATA`) | `true` | `G1–G7 PASSED`; `G8 WARNING (0.0/15)` |
| `PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT` | v1 | `ARCHIVED` | `67.0` | `0.0` | `WARNING` (`NOT_EVALUATED`) | `false` | **`G5 FAILED`** (hard block) |
| `PH_RULE_DEBUG_FUNNEL` | v1 | `DRAFT` | `35.0` | `0.0` | `WARNING` (`INSUFFICIENT_DATA`) | `false` | **`G1, G4, G6, G7 FAILED`** (`4/8` hard blocks) |

## 3. Stale Digest, Unapproved Baseline & Regression Protections Verified

Covered continuously by [`test_audit_remediations.py`](../../backend/tests/test_audit_remediations.py) (`test_quality_gates_g5_baseline_dilution_g7_blockers_and_g8_stale_digest`, `test_approve_version_blocks_regression_and_model_payload_exposes_canonical_evidence`) and [`test_phase8_integration.py`](../../backend/tests/test_phase8_integration.py):

- Approving a candidate policy with stale `policy_digest`, failing hard gates (`G1`, `G4`, `G5`, `G6`, `G7`), or worse empirical accuracy than the active approved baseline (`REGRESSION_DETECTED`) is rejected deterministically by [`PromptStudioService.approve_version`](../../backend/app/services/prompt_studio_service.py).
- Production evaluation against `OPENAI_COMPATIBLE` live models against a `DRAFT`-only policy forces `REQUIRES_ATTENTION` (`POLICY_NOT_APPROVED`, `reevaluation_eligible=true`) (`S07`).

