# 11 — Experiment B: Qwen3 Evidence Enrichment Results (`QWEN3_ENRICHED`)

- **Technical Completion**: `20/20` (`ok=True`, `finish_reason=stop`, `schema_valid=20/20`, `0` overflows; `1` transient `WinError 10054` socket reset during `task-443` before resumptive completion).
- **Ablation Finding (`Exp A -> Exp B`)**:
  - Adding deterministic `evidence_intelligence` WITHOUT `AIS28-CS-CANDIDATE-V1` kept 3-class parsed accuracy at `11/20 (55.0%)`: `10/10` Prisma `REQUIRES_ATTENTION`, `1/1` CrowdStrike FP, `0/9` CrowdStrike TP recall.
  - **Crucial Diagnostic Discovery**: Without the rule-specific CrowdStrike candidate policy explaining that Falcon `action=block` / `process_killed=True` confirms a real IoA detection rather than benign negation, highlighting `process_killed` in `evidence_intelligence` caused `3` more CrowdStrike TPs to shift from `REQUIRES_ATTENTION` to `FALSE_POSITIVE` (`3/9 -> 6/9` raw FP!). Deterministic validation caught and rejected all of them into `REQUIRES_ATTENTION`.
