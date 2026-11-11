# Phase 8.2 — Stage G Deterministic Policy Quality Gates (`G1–G8`) Validation

**Evidence Source:** `docs/phase8.2/evidence/quality-gates/stage_g_policy_quality_gates.json`  
**Policies Evaluated:** All `5` seeded `PromptVersion` records across `4` rules (audited cleanly via read-only preview + cloned DB simulation)

## 1. Per-Version G1–G8 Gate & 3-Tier Eligibility Matrix

| Rule Code | Version | Overall / Structural Score | G1 | G2 | G3 | G4 | G5 | G6 | G7 | G8 (`INSUFFICIENT_DATA`) | Structural Approval (`G1–G7`) | Empirical Certification (`G8`) | Autonomous Ops Eligible |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `PH_RULE_CS_SUSPICIOUS_ACTIVITY` | `v1 APPROVED` | `77.0 / 90.6` | PASS `20` | PASS `20` | PASS `20` | WARN `7` | PASS `10` | WARN `12` | WARN `8` | WARN `0` (`3 < 5`) | `true` | `false` | `false` |
| `PH_RULE_DEBUG_FUNNEL` | `v1 DRAFT` | `35.0 / 41.2` | FAIL `4` | WARN `10` | PASS `20` | FAIL `0` | WARN `8` | FAIL `3` | FAIL `0` | WARN `0` (`0 < 5`) | `false` | `false` | `false` |
| `PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT` | `v1 ARCHIVED` | `67.0 / 78.8` | PASS `20` | PASS `20` | PASS `20` | PASS `10` | FAIL `0` | WARN `12` | WARN `5` | WARN `0` (`0 < 5`) | `false` | `false` | `false` |
| `PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT` | `v2 DRAFT` | `85.0 / 100.0` | PASS `20` | PASS `20` | PASS `20` | PASS `10` | PASS `10` | PASS `15` | PASS `10` | WARN `0` (`0 < 5`) | `true` | `false` | `false` |
| `Prisma_SASE_Suspicious_File_Threat_Detection_` | `v1 APPROVED` | `70.0 / 82.4` | PASS `20` | WARN `10` | PASS `20` | PASS `10` | PASS `10` | WARN `12` | WARN `8` | WARN `0` (`3 < 5`) | `true` | `false` | `false` |

## 2. Key Governance Observations

- Notice **`0/5` policies** pass `G8_SIMULATION_REGRESSION`, **`0/5` policies** have `empirical_certification_eligibility = true`, and **`0/5` policies** have `autonomous_operation_eligibility = true`.
- Unsafe policy `PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT v1 (ARCHIVED)` is hard-blocked (`G5 FAILED` due to RFC-1918 blanket FP assumption and prescriptive confidence range); remediated `v2 (DRAFT)` achieves `100.0` structural score (`G1–G7 PASSED`) while honestly remaining `autonomous_operation_eligibility = false` pending empirical `G8` certification (`>= 5` verified cases).
- Incomplete `PH_RULE_DEBUG_FUNNEL v1 (DRAFT)` is hard-blocked with 4 blocking issues (`RULE_DEFINITION_INCOMPLETE`, `INADEQUATE_TP_CRITERIA`, `MISSING_CRITICAL_ABSTENTION`, `G7_CONTRACT_EVIDENCE_OMITTED`).

