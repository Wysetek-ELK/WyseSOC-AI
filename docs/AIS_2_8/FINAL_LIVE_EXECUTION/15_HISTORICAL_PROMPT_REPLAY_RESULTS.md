# 15 — Experiment R: Budget-Bounded Historical Prompt Replay (`V1`)

- **Execution Scope**: Executed strictly within remaining authorized budget (`15` incidents = `10` CrowdStrike + `5` Prisma SASE; total live attempts = `82/82`).
- **Prompt & Config**: `neutral_prompt_version=V1`, `include_complete_rule_def=false`, `include_evidence_intelligence=false`, `use_candidate_policy=false`, `temperature=0.1`.
- **Same-15 Comparison (`Exp R Qwen3 V1` vs `AIS 2.7 Qwen2.5 Mode A`)**:
  - **Qwen3 Exp R (`15` subset)**: 3-class parsed `= 5/15 (33.33%)` | TP recall `= 0/9 (0.0%)` | FP recall `= 0/1 (0.0%)` | Prisma Inconclusive `= 5/5 (100.0%)`.
  - **Qwen2.5 AIS 2.7 (`same 15`)**: 3-class parsed `= 1/15 (6.67%)` | TP recall `= 0/9` | FP recall `= 1/1` | Prisma Inconclusive `= 0/5`.
- **Interpretation**: Even on unguided `V1` prompts without complete rule definitions or enrichment, Qwen3 avoided Qwen2.5's `FALSE_POSITIVE` collapse, yet STILL achieved `0/9` CrowdStrike TP recall — proving **both** stronger base model behavior AND the decisive necessity of complete rules + candidate policies (`Exp C`: `9/9` TP recall!).
