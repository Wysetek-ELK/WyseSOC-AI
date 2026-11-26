# 08 — Rule-Aware Policy Integrity

- AIS 2.8 `EXPERIMENTAL_CANDIDATE` policy remained unpromoted (`candidate_policy_promoted=false`) and active production rules remain protected (`automatic_closure_enabled=false`).
- Live ablation (`targeted4_mode_a` vs `targeted4_mode_b`) re-confirmed that complete triggered rule definitions + investigation policy (`mode=B`, `use_candidate_policy=true`) lift TP accuracy cleanly while deterministic validation enforces evidence grounding regardless of prompt mode.
