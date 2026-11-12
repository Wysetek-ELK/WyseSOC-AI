# Phase 9 — Server 2 Setup Runbook (Dedicated Local LLM GPU Node)

**Target OS:** Ubuntu 22.04/24.04 LTS with NVIDIA CUDA GPU (`>= 14 GiB` VRAM recommended for 7B/8B AWQ models)  
**Serving Engine:** Native `vLLM` OpenAI-Compatible API (`http://0.0.0.0:8000/v1`, restricted by UFW to Server 1)

---

## 1. Native Setup Procedure

Execute on Server 2 after provisioning GPU drivers (or let `install_llm_server.sh` install headless `nvidia-driver-535-server`):

```bash
cd /opt/ai-verdict/deployment/scripts
sudo MODEL_NAME="Qwen/Qwen2.5-7B-Instruct-AWQ" \
     MAX_MODEL_LEN="16384" \
     MAX_NUM_SEQS="8" \
     GPU_MEM_UTIL="0.90" \
     bash install_llm_server.sh <SERVER_1_PRIVATE_IP>
```

Key guarantees verified in `deployment/scripts/install_llm_server.sh` and `setup_server2_gpu.sh`:
- Dedicated unprivileged user `llmuser` and cache paths (`/opt/llm-server/hf_cache`, `/var/log/llm-server`).
- Systemd unit `/etc/systemd/system/vllm-server.service` configured with `--max-model-len`, `--max-num-seqs`, `--gpu-memory-utilization`, logrotate (`14` daily compressed rotations), and automatic restart on failure.
- UFW firewall restricts port `8000/tcp` ingress strictly to `<SERVER_1_PRIVATE_IP>` plus `22/tcp` SSH management.

## 2. Live Inference Smoke Validation

Once `vllm-server.service` reaches active ready state:

```bash
python3 /opt/ai-verdict/deployment/scripts/smoke_test_server2.py \
  --base-url "http://127.0.0.1:8000/v1" \
  --model "Qwen/Qwen2.5-7B-Instruct-AWQ" \
  --timeout 30
```

Expected exit codes:
- `0` (`overall_status: "PASSED"`): `/health`, `/v1/models`, `/v1/chat/completions`, structured JSON verdict schema, invalid-model `>= 400` error check, and `/metrics` Prometheus scrape all succeeded.
- `1` (`overall_status: "FAILED"`): Endpoint reachable, at least one check failed.
- `2` (`overall_status: "NOT_EXECUTED"`): Endpoint unreachable (`ConnectionRefusedError` / timeout). Never misreports PASS offline.

## 3. Server 1 Alignment Settings

Ensure Server 1 `/opt/ai-verdict/backend/.env` matches Server 2 `MAX_MODEL_LEN` and API key:
- `LOCAL_LLM_CONTEXT_BUDGET="16384"`
- `LOCAL_LLM_MAX_TOKENS="1024"`
- `LOCAL_LLM_TARGET_INPUT_BUDGET="8192"`
- `LOCAL_LLM_TIMEOUT="60.0"`
- `LOCAL_LLM_ALLOW_MOCK_FALLBACK="false"`

**Current Verification Status:** Wire contract and `smoke_test_server2.py` behavior were verified offline against an isolated local HTTP mock server (`test_smoke_test_server2_live_mock_and_unreachable_honesty`). Live vLLM GPU execution remains **`NOT_TESTED` / `NOT_DEPLOYED`**.

