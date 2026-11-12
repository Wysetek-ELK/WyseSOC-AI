# Verdictum AI — Server 2 GPU Startup & Integration Checklist

**Checklist Date:** 2026-11-12T04:45:00Z  
**Application Identity:** Verdictum AI  
**Prerequisite:** Server 1 Complete Readiness (Status: **GO**)  
**Target Node:** Server 2 (AWS EC2 GPU Instance / vLLM Inference Node)  
**Target Model:** `Qwen/Qwen2.5-7B-Instruct-AWQ`

---

## 1. Pre-Startup Verification (Server 1 Prerequisite Gate)

Before powering on Server 2, ensure Server 1 exhibits the following verified state:
- [x] Application code synchronized to commit `f37d244e`.
- [x] FastAPI backend running on `127.0.0.1:8000` (`ai-verdict-backend.service`).
- [x] Next.js frontend running on `127.0.0.1:3000` (`ai-verdict-frontend.service`).
- [x] Redis running on `127.0.0.1:6379` (`redis.service`).
- [x] Celery worker running 4 processes on `live_triage`, `simulation_replay`, and `maintenance` (`ai-verdict-worker.service`).
- [x] Fail-closed protections active: `LOCAL_LLM_ALLOW_MOCK_FALLBACK=false` and `FORTISIEM_MOCK_FALLBACK=false`.
- [x] `RuntimeConfigValidator` reports **0 blockers**.

---

## 2. Server 2 Startup & Activation Sequence

```
+-----------------------------------------------------------------------------------------+
| Server 2 Activation Sequence                                                            |
+-----------------------------------------------------------------------------------------+
|                                                                                         |
|  [Step 1: AWS Console / CLI]                                                            |
|  - Start EC2 GPU Instance (e.g. g5.xlarge / A10G)                                       |
|  - Verify public / private IP assignment                                                |
|                                                                                         |
|  [Step 2: Security Group & Port Check]                                                  |
|  - Verify TCP port 8000 open from Server 1 IP                                           |
|                                                                                         |
|  [Step 3: vLLM Service Telemetry]                                                       |
|  - Verify vLLM container / systemd service starts                                       |
|  - Probe: curl http://<server2_ip>:8000/v1/models                                       |
|  - Confirm model: Qwen/Qwen2.5-7B-Instruct-AWQ                                          |
|                                                                                         |
|  [Step 4: Server 1 IP Binding]                                                          |
|  - If Server 2 IP changed, update LOCAL_LLM_BASE_URL in backend .env                    |
|  - Restart ai-verdict-backend and ai-verdict-worker                                     |
|                                                                                         |
|  [Step 5: Health & Integration Validation]                                              |
|  - Check http://127.0.0.1:8000/api/health -> local_llm status: healthy                  |
|  - Execute single prompt probe via /api/chat                                            |
|                                                                                         |
|  [Step 6: Empirical G8 Simulation Replay]                                               |
|  - Run historical simulation in Simulation Lab                                          |
|  - Evaluate G8 empirical FP reduction rate                                              |
|                                                                                         |
+-----------------------------------------------------------------------------------------+
```

---

## 3. Step-by-Step Execution Checklist

### Step 1: Power On AWS GPU Instance
- [ ] Log into AWS Management Console (or run AWS CLI `aws ec2 start-instances --instance-ids <server2_instance_id>`).
- [ ] Note the allocated public IPv4 address and internal private IP.
- [ ] Confirm Security Group allows inbound traffic on port `8000` from Server 1's IP address.

### Step 2: Probe vLLM Health on Server 2
From Server 1, execute the following probe:
```bash
curl -s http://<server2_ip>:8000/v1/models | jq .
```
- [ ] Verify HTTP response code: `200 OK`.
- [ ] Verify model identifier: `"id": "Qwen/Qwen2.5-7B-Instruct-AWQ"`.
- [ ] Verify model context window capacity (`max_model_len >= 4096`).

### Step 3: Synchronize Server 1 Configuration (If IP Changed)
If the AWS GPU instance received a new dynamic IP address upon startup:
```bash
# On Server 1:
sed -i 's|LOCAL_LLM_BASE_URL=.*|LOCAL_LLM_BASE_URL="http://<new_server2_ip>:8000/v1"|g' /opt/wysesoc-ai/backend/.env

# Restart services:
systemctl restart ai-verdict-backend
systemctl restart ai-verdict-worker
```
- [ ] Backend restarted cleanly.
- [ ] Worker restarted cleanly.

### Step 4: Validate Live Backend Integration
Probe the unified health endpoint on Server 1:
```bash
curl -s http://127.0.0.1:8000/api/health | jq .components.local_llm
```
- [ ] `status`: `"healthy"`.
- [ ] `reachable`: `true`.
- [ ] `current_s2_health`: `"HEALTHY"`.
- [ ] `circuit_breaker_state`: `"CLOSED"`.
- [ ] Overall system status transitions from `"degraded"` to `"healthy"`.

### Step 5: Execute Single Live Inference Verification
Execute an authenticated test inference request to verify full token generation and JSON schema output:
```bash
curl -s -X POST http://127.0.0.1:8000/api/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_token>" \
  -d '{
    "messages": [{"role": "user", "content": "Respond with: VERDICTUM_AI_ONLINE"}],
    "max_tokens": 10
  }' | jq .
```
- [ ] Returns valid completion response containing `"VERDICTUM_AI_ONLINE"`.
- [ ] Confirms zero fallback to mock inference.

### Step 6: Execute AIS Simulation Lab G8 Historical Evaluation
In the Verdictum AI web interface (`http://<server1_ip>:3000`):
1. Navigate to **AIS Simulation Lab**.
2. Select target detection rule: `PH_RULE_CS_SUSPICIOUS_ACTIVITY` (Rule UUID: `0974a66e-ede2-4a6a-821b-6283a99c8aa4`).
3. Click **"Run Empirical Simulation"** with `provider_type="OPENAI_COMPATIBLE"`.
4. Monitor the task on Celery queue `simulation_replay`.
- [ ] Task dispatched to Celery `simulation_replay` queue.
- [ ] Worker processes batch of historical incidents using real vLLM inference.
- [ ] G8 gate evaluates empirical False Positive reduction and precision.
- [ ] Quality assessment card updates with empirical validation score.

### Step 7: Operating Mode Promotion (Optional / Post-Validation)
Once G8 empirical simulation and live inference are confirmed:
1. Update `/opt/wysesoc-ai/backend/.env`:
   ```ini
   PLATFORM_OPERATING_MODE="shadow"
   ```
2. Restart backend: `systemctl restart ai-verdict-backend`.
3. In `shadow` mode, all live incoming FortiSIEM incidents receive real-time AI triage evaluations recorded for audit and review, with autonomous closure and SIEM writebacks remaining disabled.

---

## 4. Emergency Contingency & Rollback Procedures

### If Server 2 Fails to Start or vLLM Crashes:
1. Server 1 remains 100% operational in degraded mode; frontend and backend continue serving analysts.
2. The circuit breaker automatically opens after 5 failed inference attempts, shedding LLM load without hanging HTTP requests.
3. Because fail-closed guards are active (`LOCAL_LLM_ALLOW_MOCK_FALLBACK=false`), the system will never fabricate mock triage verdicts.
4. Incidents remain in `PENDING_REVIEW` in the Investigation Workbench for manual analyst disposition.

