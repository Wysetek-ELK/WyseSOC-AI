# 12 — GPU Execution Authorization & Preflight

- **Operator Authorization:** Granted via native approval gate (`YES - Run full head-to-head benchmark (Qwen3-14B and Qwen2.5-7B)`, up to 82 inference requests).
- **Server 1 Deployment:** Completed via UPLA (`upla-20261126-035712-a04d56`, commit `7fb6e53f405ba41b8d93ad2f0877fbdcc1512509`), verified healthy (`http://172.26.41.240/api/health` shows `Qwen/Qwen3-14B-AWQ`, `ONLINE`).
- **Remaining Preflight Prerequisite:** Supply an active Server 1 administrator JWT token for `http://172.26.41.240/api/ground-truth/ais27/*` and coordinate Server 2 `vllm-server.service` toggle between `Qwen/Qwen3-14B-AWQ` and `Qwen/Qwen2.5-7B-Instruct-AWQ`.
