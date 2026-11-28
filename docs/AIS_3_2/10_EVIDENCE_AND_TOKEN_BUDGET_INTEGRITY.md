# AIS 3.2 — 10: Evidence & Token Budget Integrity

- Rule-aware prioritization (`prioritize_evidence_records`) ranks contract-mandatory fields (`priority 0`) and structured entity/metric records (`priority 1`) above verbose raw logs (`priority 4`).
- Tracks `original_evidence_count`, `available_evidence_count`, `included_evidence_count`, `excluded_evidence_count`, `exclusion_reason`, `critical_evidence_retained`, `actual_wire_token_count`, `reserved_completion_tokens` (`1024`), and `evidence_completeness_state` (`COMPLETE` vs `PARTIAL_NON_CRITICAL_TRIMMED` vs `CRITICAL_EVIDENCE_BUDGET_LIMITATION`) within `Qwen/Qwen3-14B-AWQ`'s `8192` token limit.
