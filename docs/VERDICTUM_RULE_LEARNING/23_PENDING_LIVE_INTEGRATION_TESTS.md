# Verdictum AI — Pending Live Integration Tests

**Document:** `23_PENDING_LIVE_INTEGRATION_TESTS.md`  
**Platform:** Verdictum AI / WyseSOC AI  
**Scope:** Specification of Tests Deferred to Live Infrastructure Availability  
**Status:** DRAFTED & DOCUMENTED  

---

## 1. Overview & Operational Boundary

While offline unit, integration, simulation, and regression testing are 100% complete and passing, specific integration tests require live external connectivity to the FortiSIEM appliance and the dedicated Server 2 GPU inference daemon. 

In accordance with engineering safety rules, these live tests are documented here and will be executed only after formal deployment authorization.

---

## 2. Inventory of Pending Live Integration Tests

| Test ID | Target System | Objective & Verification Criteria | Prerequisites |
|---|---|---|---|
| **LIT-01** | FortiSIEM API | Real-time incident synchronization via background poller (`FortiSIEMService.pull_incidents`). Assert new incidents ingest without dropping attributes. | Live FortiSIEM cluster reachable via HTTPS; valid API credentials. |
| **LIT-02** | Server 2 vLLM | Live OpenAI-compatible REST inference (`POST /v1/chat/completions`) for `Qwen/Qwen2.5-7B-Instruct-AWQ`. Assert JSON schema compliance and token latency $<2000$ms. | Server 2 vLLM daemon online on port 8000; TCP reachable. |
| **LIT-03** | Server 2 Context | Validate dynamic context clamping under real model launch arguments (`--max-model-len 4096` vs `16384`). | Server 2 GPU initialized with sufficient VRAM. |
| **LIT-04** | FortiSIEM Write-back | Test automated incident closure write-back on an approved `CONTROLLED_PRODUCTION` rule in dry-run mode. Assert FortiSIEM returns HTTP 200 with transaction ID. | FortiSIEM writeback permissions enabled in test tenant. |
| **LIT-05** | GPU Concurrency | Measure GPU manager semaphore bounds under 5 concurrent analyst evaluation requests. Assert no circuit-breaker tripping or VRAM OOM exceptions. | Server 2 GPU monitoring active (`nvidia-smi`). |
| **LIT-06** | End-to-End Live Pilot | Execute 24-hour Supervised Pilot on live ingested incidents with human analyst confirmation. Measure empirical precision against live ground truth. | Active SOC shift analyst participation. |

---

## 3. Safe Execution Protocol

When live infrastructure is restored:
1. Run preflight connectivity probe:
   ```powershell
   python C:\Users\amit\.gemini\config\repo_deploy_governor\scripts\governor_cli.py probe-siem
   ```
2. Test single-incident live inference:
   ```powershell
   python C:\Users\amit\.gemini\config\repo_deploy_governor\scripts\governor_cli.py test-inference --incident-id 176061
   ```
3. Audit remote database and services before initiating write-back tests:
   ```powershell
   python C:\Users\amit\.gemini\config\repo_deploy_governor\scripts\governor_cli.py audit-remote
   ```

