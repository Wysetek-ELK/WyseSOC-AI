# AIS 2.6a — Report 13: Operational Runbook and GPU Cost Analysis

## 1. Server 2 Administrator Operational Runbook

### Service Inspection
```bash
# Check vLLM service status
systemctl status vllm-server.service --no-pager

# Verify active model context capacity from host
curl -s http://127.0.0.1:8000/v1/models | jq '.data[] | {id, max_model_len}'
```

### GPU Utilization and Memory Monitoring
```bash
# Monitor GPU memory and compute utilization
nvidia-smi --query-gpu=utilization.gpu,utilization.memory,memory.used,memory.total --format=csv -l 5
```

---

## 2. Server 1 Operational Verification

### Service Health
```bash
systemctl status ai-verdict-backend.service --no-pager
curl -s http://127.0.0.1:8000/api/health | jq .
```

---

## 3. GPU Token Consumption and Cost Accounting
- **Total GPU Tokens Consumed:** 102,726 tokens
  - Live Prompt Tokens: 92,214 tokens
  - Live Completion Tokens: 10,512 tokens
- **Hardware Instance:** AWS EC2 `g5.2xlarge` (NVIDIA A10G 24GB GPU)
  - Hourly on-demand rate: ~$1.212 / hr
  - Total benchmark inference wall-clock runtime: ~6.5 minutes (0.108 hours)
  - Estimated direct compute cost: **$0.131 USD**
