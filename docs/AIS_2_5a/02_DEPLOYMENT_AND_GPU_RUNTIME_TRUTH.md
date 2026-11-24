# 02 — Deployment and GPU Runtime Truth Audit

## 1. Scope & Objective

Empirically verify the runtime configuration, network connectivity, application state, and GPU physical truth across Server 1 (Verdictum Core) and Server 2 (Verdictum Cortex).

---

## 2. Server 1 (Verdictum Core — 172.26.41.240)

- **Application Directory**: `/opt/wysesoc-ai`
- **UPLA Execution ID**: `upla-20261124-054604-f80e11`
- **Deployed Git Commit SHA**: `ff0a4c249dd05cc2f183ab10c8f29b1ee3437248`
- **GitHub Synced Ref**: `feature/phase3-compact-ui`
- **Host Resources**: 15.36 GB RAM (10.01 GB used, 5.35 GB free)
- **FastAPI Backend**: `ai-verdict-backend.service` (ACTIVE / RUNNING on port 8000, proxied on port 80)
- **Next.js Frontend**: `ai-verdict-frontend.service` (ACTIVE / RUNNING on port 3000, 32/32 routes compiled)
- **Database**: PostgreSQL 16 on `localhost:5432` (Health probe latency: 1.17ms, all migrations up to date)
- **Message Broker / Cache**: Redis on `localhost:6379` (Healthy)
- **Background Workers**: Celery worker pool active

---

## 3. Server 2 (Verdictum Cortex — 13.204.214.64:8000)

- **Physical Machine**: AWS EC2 `g5.xlarge` instance
- **GPU Accelerator**: NVIDIA A10G (24,576 MiB VRAM)
- **vLLM Process**: Running OpenAI-compatible API on port 8000
- **Model Name**: `Qwen/Qwen2.5-7B-Instruct-AWQ`
- **Quantization**: AWQ (4-bit activation-aware weight quantization)
- **Active Model Context Length (`--max-model-len`)**: **4,096 tokens** (CRITICAL AUDIT FINDING)
- **Completion Reserve**: 768 tokens
- **Available Input Budget**: **3,328 tokens** ($4096 - 768$)
- **API Endpoint Connectivity**: `http://13.204.214.64:8000/v1/models` (Verified reachable from Server 1 in 13.7ms)
- **Private IP (`172.26.41.241`)**: Connection refused (traffic routed over VPC elastic public IP)

### Hardware Context Window Finding
Prior documentation assumed an 8,192 context window was operational on Server 2. Empirical API probe via `GET /api/llm/test-connection` proved that vLLM was launched with `--max-model-len 4096`:
```json
{
  "status": "connected",
  "model": "Qwen/Qwen2.5-7B-Instruct-AWQ",
  "server_max_model_len": 4096,
  "available_input_tokens": 3328,
  "completion_reserve": 768
}
```
Modifying Server 2 requires GPU server restart which is governed by cost and maintenance controls. All evaluations in AIS 2.5a honor this physical reality.
