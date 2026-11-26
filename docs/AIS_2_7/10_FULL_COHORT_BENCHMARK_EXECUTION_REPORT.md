# AIS 2.7 — Workstream 10: Full 20-Incident Benchmark Execution Report

**Phase:** AIS 2.7 | **Generated (UTC):** 2026-11-25T06:31:38.558775+00:00  
**Artifacts:** [LIVE_BENCHMARK_RESULTS.json](LIVE_BENCHMARK_RESULTS.json), [REQUEST_EXECUTION_LEDGER.json](REQUEST_EXECUTION_LEDGER.json), [LIVE_TOKEN_ACCOUNTING_RESULTS.json](LIVE_TOKEN_ACCOUNTING_RESULTS.json)

## 1. Execution Summary

All `20 / 20` frozen cohort incidents completed Mode A, Mode B, and Mode C live evaluation:

- **Total Successful GPU Calls:** `41 / 41` authorized baseline (`1` smoke + `20` Mode A + `20` Mode B)
- **Transport Retry Used:** `1 / 5` max allowed (`HTTP 504 Gateway Time-out` on initial combined Mode A+B call for `132499009` because Server 1 nginx `proxy_read_timeout` is `120s`)
- **Remediation Deployed:** Added `?mode=A` / `?mode=B` query filter to `ais27_benchmark_runner.py` and `ground_truth.py`, deployed via UPLA `upla-20261125-060404-fc45d8` (commit `1e099d5b5954f6921e154ce124d04e604f466d9e`), and completed the remaining `7` Prisma SASE incidents in single-mode calls without touching any of the `13` already completed incidents.
- **Total Live Tokens (All 41 Calls):** `186831` prompt + `21643` completion = `208474` tokens.
- **Maximum Total Tokens Observed:** `7197 / 8,192` (`132461358` Mode B: `6,724 + 473 = 7,197` tokens, leaving `995` tokens of headroom; `0` overflows).
