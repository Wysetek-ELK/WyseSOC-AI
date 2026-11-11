# Phase 9 — Performance & Scalability Validation

**Benchmark Mode:** `SYNTHETIC_LOCAL_THROUGHPUT_ONLY`  
**Evidence File:** `docs/phase9/evidence/performance/phase9_load_benchmark.json`  
**Script:** `scripts/run_phase9_load_benchmark.py`

> **CRITICAL HONESTY DISTINCTION:** This benchmark executes against an ephemeral local SQLite database and Windows workstation CPU to measure Server 1 application/ORM/eligibility overhead at target rule scale (`2,000` rules, `500` incidents). It **does NOT** measure real PostgreSQL 16 pooled I/O or live Server 2 vLLM GPU inference throughput. Live GPU tokens/sec remain **`NOT_TESTED`**.

---

## 1. Environment & Synthetic Workload

- **Host Environment:** Windows-11, Python `3.13.13`, `12` logical CPUs
- **Seeded Corpus:** `2,000` `Rule` records + `2,000` approved `RulePrompt`/`PromptVersion` policies + `500` `Incident` records (paired with `HistoricalGroundTruth`)
- **Daily Target Reference Rate:** `10,000 incidents/day` (~`6.94 incidents/min` average)

---

## 2. Observed Benchmark Measurements

| Benchmark Metric | Observed Measurement | Notes |
|---|---|---|
| Seed 2,000 Rules + 2,000 Approved Policies | `1.127s` | Initial SQLite write batch |
| Rule Lookup Latency (200 queries) | **p50:** `4.517 ms` • **p95:** `5.573 ms` • **p99:** `6.451 ms` | Indexed `rule_id` lookup |
| Incident Bulk Ingestion Throughput (500 records) | `3,038.4 incidents/sec` | Orders of magnitude above 6.94/min baseline |
| Evidence Normalization (200 incidents) | **p50:** `0.18 ms` • **p95:** `0.32 ms` • **p99:** `0.504 ms` | Canonical field extraction CPU overhead |
| Pilot Eligibility Evaluation (200 checks) | `6,573.3 checks/sec` | `PilotService.check_incident_eligibility` |
| API DB Pagination (50 rows/page) | **p50:** `41.332 ms` • **p95:** `65.899 ms` • **p99:** `65.899 ms` | Joined query pagination |
| Historical Eligibility Report Across 2,000 Rules | `3.703s` | Identified `200` eligible independent cases |
| HMAC-Ready Audit Log Inserts (500 rows) | `8,704.4 inserts/sec` | Synchronous batch insert measurement |
| Process RSS Memory Growth | `+24.83 MB` (`72.76 MB -> 97.59 MB`) | Error rate: `0.0` |

## 3. Production Bottleneck Note

Real-world SOC Pilot concurrency is bounded by Server 2 vLLM KV-cache / `MAX_NUM_SEQS` (default `8`) and `max_concurrent_inference` (default `2`) rather than Server 1 API/ORM logic. Live multi-worker throughput benchmarking must run against staging Server 1 + Server 2 hardware before raising budgets.

