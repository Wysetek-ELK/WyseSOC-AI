# 07 — Checkpoint A: GPU-Off Preflight & Execution Authorization

**Phase:** AIS 2.7 (Workstream 7)  
**Preflight Status:** `READY_FOR_AUTHORIZED_GPU_BENCHMARK`  
**Execution Gate:** `PENDING_OPERATOR_AUTHORIZATION_AT_CHECKPOINT_A`

---

## 1. Stage 1 Preflight Checklist

| Check | Status | Evidence |
|---|---|---|
| Authoritative Server 1 DB accessible | **PASS** | PostgreSQL connected (`3.63 ms`), Alembic `016`, `10,440` incidents |
| 20 locked GT-2 reviews retrieved | **PASS** | `9 TP / 1 FP / 10 INCONCLUSIVE` (`0 GT-3`, `0` conflicts) |
| Frozen cohort & Priority 5 verified | **PASS** | All `20` `132xxxxxx` IDs verified on Server 1 |
| Reference labels frozen & isolated | **PASS** | [GROUND_TRUTH_REFERENCE_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_7/GROUND_TRUTH_REFERENCE_MANIFEST.json) |
| Approved policies verified on Server 1 | **PASS** | CS v3 (`b6d9df2f...`), Prisma v1 (`ed7ff3c7...`) |
| Offline token budget & label isolation | **PASS** | Max Mode A `5,411`, Max Mode B `6,357` (`<= 7,424`), `0` leaks |
| Regression & blind-review tests | **PASS** | `16 / 16` pytest cases passed |

---

## 2. Discovered Server 2 State & Execution Pathway

- **Server 2 Power State:** Probe via Server 1 `POST /api/llm/test-connection` confirms `http://13.204.214.64:8000/v1/models` is **ALREADY ONLINE** (`200 OK`, `12.4 ms`, `Qwen/Qwen2.5-7B-Instruct-AWQ`, `max_model_len=8192`).
- **Network Access Constraint:** Direct connection from the local workstation to `13.204.214.64:8000` timed out (port 8000 is firewalled to Server 1 `172.26.41.240`).
- **Execution Mechanism:** Because Server 1 currently lacks an isolated HTTP endpoint exposing `EmpiricalBenchmarkHarness` three-mode execution against `AIS_2_6E_FROZEN_20` with Server 1 PostgreSQL policies (`b6d9df2f` v3 / `ed7ff3c7` v1) and full raw-response/wire-prompt capture, Stage 2 requires operator authorization either to:
  1. Deploy a minimal, isolated, read-only benchmark execution endpoint/script on Server 1 via UPLA Gate 1/Gate 2 (or run directly on Server 1), **OR**
  2. Temporarily allow workstation access / execute via authorized SSH on Server 1.

---

## 3. Planned GPU Workload & Cost Estimate

| Activity | Planned GPU Calls |
|---|---:|
| Connectivity smoke test | 1 |
| Mode A priority pilot | 5 |
| Mode B priority pilot | 5 |
| Mode A remaining 15 | 15 |
| Mode B remaining 15 | 15 |
| Mode C deterministic validation | 0 |
| **Total Baseline Budget** | **41** |

- **Estimated Active Benchmark Compute Cost (ESTIMATED_ONLY):** ~5–15 minutes sequential execution on `g5.xlarge` (~`$0.10`–`$0.30` USD attributable compute; hourly EC2 rate continues while Server 2 remains running).
- **Operator Authorization Requested:**
  1. Confirm live benchmark execution authorization against currently running Server 2 (`13.204.214.64:8000`).
  2. Confirm maximum workload cap (`41` baseline calls + up to `5` infrastructure retries).
  3. Confirm execution pathway on Server 1 (UPLA-governed isolated benchmark script/endpoint vs direct Server 1 run).
  4. Confirm whether Server 2 should be stopped after completion or left for manual shutdown.

Artifacts: [CHECKPOINT_A_STATUS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_7/CHECKPOINT_A_STATUS.json), [GPU_GO_NO_GO.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_7/GPU_GO_NO_GO.json), [GPU_EXECUTION_BUDGET.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_7/GPU_EXECUTION_BUDGET.json).
