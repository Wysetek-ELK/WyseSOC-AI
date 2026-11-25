# 01 — Historical Evidence & ID Reconciliation

- **Phase**: AIS 2.6f
- **Deployed Commit SHA**: `dfe4e6e59aefddd29347f3103c5c59832e386e9f`

## Summary of Reconciled Discrepancies
1. **Frozen Cohort Incident IDs**: Authoritative 20 frozen incidents in `fixtures/Incident json.zip` and DB are the `132xxxxxx` IDs (`10` CrowdStrike + `10` Prisma SASE). Prior narrative IDs (`10476-10485`, `10496-10505`) were historical text artifacts only and have been retired cleanly.
2. **Approved Policy Identities**:
   - `PH_RULE_CS_SUSPICIOUS_ACTIVITY` -> Rule `271b0831-f6f5-4d86-9e0b-d53aee948cf0`, RulePrompt `08c59656-c002-4a76-b100-3c8d6d645eb2`, Approved v1 `bd751fac-9bfb-4994-b150-8850bb94dd6c`.
   - `PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE` -> Rule `b2f1f1e4-117b-4b0e-87ca-65869898630b`, RulePrompt `1fe4e834-bd52-4571-95ca-ee329e40e1b2`, Approved v1 `8ae7beaa-626a-4061-a0c4-8500f7e6a69d`.
3. **AIS 2.6e Gate Count**: Structured `ACCEPTANCE_GATE_MATRIX.json` recorded `29` passed gates vs prose `28`; reconciled directly to structured manifest evidence.
