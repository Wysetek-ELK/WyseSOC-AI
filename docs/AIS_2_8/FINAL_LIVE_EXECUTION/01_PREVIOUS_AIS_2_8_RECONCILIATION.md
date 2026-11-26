# 01 — Previous AIS 2.8 Execution Reconciliation

- **Previous Commit Reconciled**: `7fb6e53f405ba41b8d93ad2f0877fbdcc1512509` (`docs/AIS_2_8/FINAL_EVIDENCE.json`, `status=NOT_RUN`, `executed_requests=0`)
- **Current Deployed Commit**: `215f744c9e699aac97512505a1afb5fdca888732` (`upla-20261126-051201-6e3bf9`)
- **Reconciliation Findings**:
  - **BLK-28-01 (Admin JWT & live Server 1 benchmark access)**: **RESOLVED** — authenticated runs completed against `http://172.26.41.240/api`.
  - **BLK-28-02 (Model switching to Qwen2.5)**: **SUPERSEDED (`NOT_APPLICABLE_OPERATOR_SINGLE_MODEL_SCOPE`)** — explicit operator mandate keeps `Qwen/Qwen3-14B-AWQ` active exclusively.
  - **BLK-28-03 (Server 2 NVML/DCGM physical GPU exporter)**: **OPEN (Non-Blocking for Intelligence Benchmark)** — vLLM Prometheus metrics verified live (`kv_cache_usage_percent`, queues), while physical VRAM/utilization remains `Unavailable` without synthetic fabrication.
  - **BLK-28-04 (Server 1 -> Server 2 transport)**: **OPEN FOR PROD / WAIVED FOR UAT** — Server 1 reaches Server 2 at `http://13.204.214.64:8000/v1` under explicit operator UAT authorization (`Its a UAT, So test all`); private VPC or TLS required before production.
  - **Empty Frozen Cohort & Token Budgeting Gaps Fixed**: Reconciled `AIS_2_6E_FROZEN_20` from live Server 1 PostgreSQL (`20` items), fixed multi-worker FortiSIEM queue saturation (`fortisiem_scheduler.py`), added `/tokenize` verification endpoint, and reserved prompt wire overhead in `ais27_benchmark_runner.py`.
