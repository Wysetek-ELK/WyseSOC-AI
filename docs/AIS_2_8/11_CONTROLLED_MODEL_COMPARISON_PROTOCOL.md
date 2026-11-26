# 11 — Controlled Model Comparison Protocol

Controlled experiments configured in `AIS27BenchmarkRunner.run_single_incident_three_mode`:
- **Invariant Controls:** `temperature=0.0`, `top_p=1.0`, `enable_thinking=false`, `max_context_tokens=8192`, `max_completion_tokens=768`, `target_input_budget=7424`, zero RAG, zero mock fallback, zero ground-truth leakage, identical `user_content` for Neutral and Policy arms.
- **Experiment A1 / A2:** Neutral V2 + Complete Rule Definition on `Qwen2.5-7B-Instruct-AWQ` vs `Qwen/Qwen3-14B-AWQ`.
- **Experiment B / C:** Fair context/rule/evidence intelligence ablation isolating deterministic enrichment impact.
- **Experiment D + Mode C:** Experimental Candidate Policy vs Approved Policy + Validator impact (0 extra GPU calls).
