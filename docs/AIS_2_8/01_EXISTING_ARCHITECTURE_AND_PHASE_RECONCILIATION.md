# 01 — Existing Architecture & AIS 2.7 Reconciliation

**Execution Date (UTC):** `2026-11-26T04:18:05.032442+00:00`  
**Deployed Commit SHA:** `7fb6e53f405ba41b8d93ad2f0877fbdcc1512509` (`feature/phase3-compact-ui`)  
**UPLA Execution ID:** `upla-20261126-035712-a04d56`

## 1. Discovered Production vs Local Architecture

| Layer | Local Workspace State | Production Runtime (`172.26.41.240`) |
|---|---|---|
| Application Server | Windows dev (`backend/venv`, Next.js 16.4.5) | Ubuntu `server-1` (`/opt/wysesoc-ai`), `ai-verdict-backend.service`, `ai-verdict-frontend.service` |
| Database | SQLite (`backend/ai_verdict.db`) | PostgreSQL (`latency_ms: 1.53`, `pool_size: 20`) |
| Async Queue | Direct / in-memory tests | Redis + Celery (`status: healthy`, `live_triage_queue_depth: 0`) |
| Inference Server | Firewalled from workstation (`13.204.214.64:8000` unreachable directly) | Server 2 (`verdictum-cortex-01`, `vLLM 0.33.0`, `Qwen/Qwen3-14B-AWQ`, `ONLINE`) |

## 2. Reconciled AIS 2.7 Baseline Metrics (`EMPIRICAL_METRICS.json`)

| Metric | Mode A (Neutral Qwen2.5) | Mode B (Policy Qwen2.5) | Mode C (Validator) |
|---|---:|---:|---:|
| Overall 3-Class Agreement (N=20) | 1/20 (5.0%) | 2/20 (10.0%) | 9/20 (45.0%) |
| Binary End-to-End Correctness (N=10 TP/FP) | 1/10 (10.0%) | 2/10 (20.0%) | 1/10 (10.0%) |
| Conditional Binary Accuracy | 1/10 (10.0%) | 2/3 (66.7%) | 1/1 (100.0%) |
| Binary Decision Coverage | 10/10 (100.0%) | 3/10 (30.0%) | 1/10 (10.0%) |
| TP Recall (N=9 TP) | 0/9 (0.0%) | 2/9 (22.2%) | 1/9 (11.1%) |

- Mode A Qwen2.5-7B-Instruct-AWQ predicted `FALSE_POSITIVE` on **20/20** incidents (`confidence` uniform).
- Live Server 1 PostgreSQL rule UUIDs (`0974a66e...` CS / `14481ebd...` Prisma) differ from local SQLite UUIDs, confirming production DB policy inspection must happen against Server 1 evidence rather than assuming SQLite parity.
