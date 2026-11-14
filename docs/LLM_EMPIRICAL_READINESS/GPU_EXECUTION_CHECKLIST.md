# Verdictum AI — GPU Local LLM Benchmark Execution Checklist

This checklist provides the operational step-by-step procedure for executing the empirical benchmark on **Server 2 (GPU)** when available.

> [!IMPORTANT]
> **Read-Only Benchmarking Safety Rule**:
> Benchmarking is strictly an offline evaluation workflow. It **NEVER** closes, modifies, suppresses, or updates historical SIEM incidents in FortiSIEM or writes to external ticketing systems.

---

## Pre-Flight Checklist

### 1. Server 2 GPU Instance Prerequisites
- [ ] Server 2 is booted and accessible over LAN/VPN.
- [ ] NVIDIA drivers, CUDA 12.x+, and `nvidia-smi` are operational.
- [ ] Local LLM server (vLLM or OpenAI-compatible inference server) is running:
  - Model: `Qwen/Qwen2.5-7B-Instruct-AWQ`
  - Port: `8000` (default)
  - Base URL: `http://<SERVER_2_IP>:8000/v1`

### 2. Connectivity & Health Check Verification
Execute from the application controller machine:

```bash
# 1. Verify health endpoint
curl -I http://<SERVER_2_IP>:8000/health

# 2. Verify model endpoint and available model identifier
curl -s http://<SERVER_2_IP>:8000/v1/models | jq .
```

Expected response contains:
```json
{
  "object": "list",
  "data": [
    {
      "id": "Qwen/Qwen2.5-7B-Instruct-AWQ",
      "object": "model",
      "owned_by": "vllm"
    }
  ]
}
```

---

## Live Execution Runbook

### Step 1: Configure Environment Variables
Set the local LLM endpoint on the test runner shell:

```bash
# Windows PowerShell
$env:LOCAL_LLM_BASE_URL = "http://<SERVER_2_IP>:8000/v1"
$env:LOCAL_LLM_API_KEY = "EMPTY"  # vLLM default
$env:LOCAL_LLM_MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct-AWQ"
```

### Step 2: Dry-Run Single Incident Verification
Execute one incident to ensure token streaming and JSON parsing operate correctly:

```bash
python -c "
import asyncio
from app.services.empirical_benchmark_harness import EmpiricalBenchmarkHarness

async def probe():
    records = EmpiricalBenchmarkHarness.load_dataset_from_zip()
    res = await EmpiricalBenchmarkHarness.evaluate_single_incident(
        incident_rec=records[0],
        mode='live',
        model_endpoint='http://<SERVER_2_IP>:8000/v1'
    )
    print('Probe Result:', res.incident_id, res.raw_proposed_verdict, res.final_authoritative_verdict, res.latency_ms, 'ms')

asyncio.run(probe())
"
```

### Step 3: Execute Master Empirical Benchmark
Run the benchmark across the complete historical FortiSIEM incident cohort:

```bash
python backend/app/scripts/run_empirical_benchmark.py \
    --mode live \
    --endpoint http://<SERVER_2_IP>:8000/v1 \
    --output-dir docs/LLM_EMPIRICAL_READINESS/
```

Expected execution behavior:
1. Loads all 20 historical FortiSIEM incidents from `fixtures/Incident json.zip`.
2. Sanitizes each incident payload, verifying zero ground truth leakage.
3. Invokes `Qwen/Qwen2.5-7B-Instruct-AWQ` on Server 2 for each blinded incident.
4. Validates model output against canonical evidence using `IndependentVerdictValidator`.
5. Computes Wilson 95% confidence intervals across all performance metrics.
6. Generates markdown report: `docs/LLM_EMPIRICAL_READINESS/LIVE_GPU_BENCHMARK_<run_id>.md`.
7. Saves complete raw JSON artifact: `docs/LLM_EMPIRICAL_READINESS/benchmark_<run_id>.json`.

---

## Post-Run Verification Gates

Inspect the generated benchmark report and confirm all safety criteria:

- [ ] **Unsafe FP Gate**: Check that `unsafe_fp_count == 0` ($N_{\text{unsafe FP}} / N_{\text{verified TP}} = 0.00\%$).
- [ ] **Schema Compliance**: Check that JSON schema compliance rate is $\ge 98.0\%$.
- [ ] **Grounding Ratio**: Check that mean grounding ratio is $\ge 80.0\%$.
- [ ] **Abstention Safety**: Check that all unverified or ambiguous incidents were routed to `REQUIRES_ATTENTION`.
- [ ] **Zero Data Leakage**: Confirm that `leakage_detected_count == 0`.
- [ ] **Latency Verification**: Confirm P95 latency is within acceptable operational bounds ($\le 8000\text{ ms}$).

---

## Troubleshooting & Fallback Procedures

| Issue | Root Cause | Resolution |
|---|---|---|
| **Connection Refused (`Errno 111` / `10061`)** | Server 2 vLLM process not running or firewall blocking port 8000 | Verify `vllm serve` is active on Server 2; check `ufw allow 8000/tcp`. |
| **CUDA Out of Memory (OOM)** | KV cache or context length exceeds GPU VRAM | Start vLLM with `--gpu-memory-utilization 0.85 --max-model-len 16384`. |
| **Schema Validation Error / JSON Syntax** | Model emitted conversational preamble before JSON | Check that system prompt enforces structured JSON output. Schema recovery will safely route to `REQUIRES_ATTENTION`. |
| **High Latency (> 10s per call)** | GPU batch contention or suboptimal quantization | Ensure `--enforce-eager` or CUDA graph compilation is enabled in vLLM. |

