# 03 — Ground Truth & Reference Integrity

- **Zero Mutated Labels**: All `20` locked human reviews remain untouched (`labels_modified=false`, `benchmark_learning_pollution_count=0`).
- **GT-2 vs GT-3 Distinction**: All 20 items are **GT-2 single-reviewer locked references** (`gt3_certified_count=0`), NOT independently dual-certified GT-3 truth.
- **Flagged Reference Audit**:
  - `132474210` (CrowdStrike TP): UltraViewer remote desktop execution blocked/killed by Falcon sensor; human confirms `TRUE_POSITIVE` (CrowdStrike rule fires on suspicious activity regardless of block).
  - `132501348` (CrowdStrike FP): **Human-only evidence dependency** — human performed external hash lookup identifying clean MEGAsync updater; telemetry alone lacks hash verdict or allowlist record.
  - `132596403` & `132599145` (Prisma SASE `INCONCLUSIVE`): Download-only cloud app activity lacks authentication/authorization telemetry, preventing automated TP/FP closure.
