# 12 — Experiment C: Qwen3 Rule-Policy Results (`QWEN3_RULE_AWARE`)

- **Technical Completion**: `20/20` (`ok=True`), `19/20` `finish_reason=stop` & `schema_valid=True`, `1` `finish_reason=length` (`132474210` at `8088+104=8192`).
- **Raw Parsed Model Intelligence (`mode_b.parsed`)**:
  - **Three-Class Accuracy**: **20/20 (100.0%)**
  - **CrowdStrike TP Recall**: **9/9 (100.0%)** (`+100.0 pp` jump from Exp B's `0/9`!)
  - **CrowdStrike FP Recall**: **1/1 (100.0%)** (`132501348` parsed `FALSE_POSITIVE`)
  - **Prisma SASE Inconclusive Agreement**: **10/10 (100.0%)** (`0` false decisive closures)
  - **Binary End-to-End Correctness**: **10/10 (100.0%)**
