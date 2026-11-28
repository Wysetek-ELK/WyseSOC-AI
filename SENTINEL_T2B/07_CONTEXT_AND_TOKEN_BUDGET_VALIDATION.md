# 07 — Context & Token Budget Validation

- **Effective Context Window**: `8192` tokens (verified via Server 2 `/v1/models` and boundary probe).
- **Live Budget Allocation Results**:
  - **RT01 (Short)**: `prompt_tokens=295`, `requested_max_tokens=7865` (`295 + 7865 + 32 = 8192`), `completion_tokens=88`, `status=COMPLETED`.
  - **RT03 (Reconstructed T2)**: `prompt_tokens=662`, `requested_max_tokens=7498` (`662 + 7498 + 32 = 8192`), `completion_tokens=1672`, `status=COMPLETED`.
  - **RT04 (Reconstructed T3.1)**: `prompt_tokens=772`, `requested_max_tokens=7388` (`772 + 7388 + 32 = 8192`), completions `982 / 1128 / 1154`, all `COMPLETED`.
  - **RT06 (Multi-turn)**: `prompt_tokens=2360`, `requested_max_tokens=5800` (`2360 + 5800 + 32 = 8192`), `completion_tokens=45`, `status=COMPLETED`.
  - **RT08 (Oversized 29,973 tokens)**: Fail-closed in `137.0ms` with `status=CONTEXT_BUDGET_EXCEEDED` (HTTP 422), zero Server 2 GPU dispatch.
  - **RT07 & RT15 (Unit tests)**: Oldest-history trimming near 8,192 and continuation insufficient-context rejection (`422`) passed.
