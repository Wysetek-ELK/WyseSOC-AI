# Phase 8.1 Policy Quality Gates Report (`G1`–`G8`) (Stage 8)

- **Status:** **`PASSED`** *(`P8.1-DEF-004` 3-tier eligibility separation verified across all 5 seeded policy versions and FastAPI API/UI)*
- **Primary Evidence:** [`stage8_quality_gates.json`](./evidence/quality-gates/stage8_quality_gates.json)

## 1. Three-Tier Eligibility Separation (`P8.1-DEF-004`)

[`PolicyQualityAssessmentResponse`](../../backend/app/schemas/policy_quality.py), [`validate_policy_quality`](../../backend/app/api/prompts.py), and [`agent-intelligence-studio/page.tsx`](../../frontend/src/app/agent-intelligence-studio/page.tsx) now explicitly distinguish:
1. **`structural_approval_eligible`:** True if static/contract/security/consistency gates (`G1`–`G7`) have zero blocking issues (permits cold-start human review & shadow approval before empirical history accumulates).
2. **`empirical_validation_eligible`:** True ONLY when Gate `G8` (`Simulation & Regression Validation`) is `PASSED` with `simulation_status == "EVALUATED_PASSED"` matching the current `policy_digest` and `policy_version_id`.
3. **`autonomous_operation_eligible`:** True ONLY when **both** `structural_approval_eligible` and `empirical_validation_eligible` are True.

## 2. G1–G8 Assessment Across All `5` Seeded Policy Versions

| Rule Code | Ver | Status | Overall / Structural Score | G8 Status | `structural_approval_eligible` | `empirical_validation_eligible` | `autonomous_operation_eligible` | Blockers |
|---|---|---|---:|---|---|---|---|---:|
| `PH_RULE_CS_SUSPICIOUS_ACTIVITY` | v1 | `APPROVED` | `77.0` / `90.6` | `WARNING` (`INSUFFICIENT_DATA`, `0/15`) | `true` | `false` | `false` | 0 |
| `Prisma_SASE_Suspicious_File_Threat_Detection_` | v1 | `APPROVED` | `70.0` / `82.4` | `WARNING` (`INCONCLUSIVE`, `0/15`) | `true` | `false` | `false` | 0 |
| `PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT` | v2 | `DRAFT` | `85.0` / `100.0` | `WARNING` (`INSUFFICIENT_DATA`, `0/15`) | `true` | `false` | `false` | 0 |
| `PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT` | v1 | `ARCHIVED` | `67.0` / `78.8` | `WARNING` (`NOT_EVALUATED`, `0/15`) | **`false`** | `false` | `false` | 2 (`G5` RFC-1918 + confidence range) |
| `PH_RULE_DEBUG_FUNNEL` | v1 | `DRAFT` | `35.0` / `41.2` | `WARNING` (`INSUFFICIENT_DATA`, `0/15`) | **`false`** | `false` | `false` | 4 (`G1`, `G4`, `G6`, `G7`) |

Paired regression check (`PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT` v1 -> v2) reported `INSUFFICIENT_DATA` (`0` matched incidents), and [`test_p8_1_def_004_quality_gates_three_tier_eligibility_separation`](../../backend/tests/test_phase8_1_validation.py) confirmed `policy_version_id`-bound balanced `EVALUATED_PASSED` runs transition `empirical_validation_eligible` and `autonomous_operation_eligible` cleanly to `True`.

