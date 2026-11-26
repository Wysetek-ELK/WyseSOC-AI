# 07 — Complete Rule Definition & Deterministic Evidence Validation

- **Complete Rule Definition (`RuleDefinitionBuilder`)**: Verified `pattern_logic`, `raw_rule_text`, `conditions`, `threshold`, `triggered_attributes`, and `predicate_evaluations` serialized identically in `Exp A`, `Exp B`, and `Exp C`.
- **Deterministic Evidence Intelligence Parity**:
  - Verified `20/20` Exp A prompts excluded `evidence_intelligence` and `20/20` Exp B prompts included `evidence_intelligence`.
  - Verified `0` instances of human verdict or AI history leakage in outbound payloads.
- **Experimental Candidate Policy Isolation**:
  - `ais28-exp-candidate-cs-v1` and `ais28-exp-candidate-prisma-v1` executed ONLY in isolated `Exp C` (`use_candidate_policy=true`); approved production policies in PostgreSQL were NOT altered.
