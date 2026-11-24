# 01 — AIS 2.6a Residual Evidence Reconciliation Report

## 1. Executive Summary
This report documents the forensic reconciliation of discrepancies identified in AIS 2.6a:
1. **Historical Token-Budget Violations**: Under the 4096-token runtime, maximum prompt budget was 3328 tokens, yet live records exceeded 3328 tokens. Forensic audit confirmed these records originated during AIS 2.5a and were carried forward into AIS 2.6a.
2. **Wire Prompt Hash Sharing**: In AIS 2.6a, only the budgeted system prompt was hashed, leading to identical wire hashes across incidents of the same rule. AIS 2.6b resolved this by concatenating the model-facing wire prompt (`system_instruction + "\n\n" + user_content`), yielding 20 distinct SHA-256 hashes.
3. **Completion Truncation**: Truncations at 768 tokens (`finish_reason=length`) occurred due to raw log dumping. Constraining prompt schemas to <120 words reason and max 3 claims eliminated truncations completely.
4. **Policy Version Uniformity**: "None" policy versions were traced to missing database lookup fallback, resolved by authoritative registration of Version 3 (CrowdStrike) and Version 1 (Prisma SASE).

## 2. Reconciled Inventory Table
| Issue ID | Area | Root Cause | Remediation in AIS 2.6b | Verification Artifact |
|---|---|---|---|---|
| REC-01 | Token Budget | BPE tokenizer undercount on hex strings | target_input_budget=6400 ceiling clamping | `TOKEN_ACCOUNTING_BREAKDOWN.json` |
| REC-02 | Wire Hashes | Hashing system prompt only | Full wire prompt hashing | `PROMPT_HASH_REGISTRY.json` |
| REC-03 | Truncations | Unconstrained model generation | Strict <120 word concise schema | `COMPLETION_TRUNCATION_AUDIT.json` |
| REC-04 | Policy Version | Unmapped rule version lookup | Authoritative DB fallback | `POLICY_REGISTRATION_AUDIT.json` |

