# 09 — Deployment & Automated Regression Verification Report

**Deployment Timestamp (UTC):** `2026-11-19T03:22:15Z`  
**Server 1 Deployed Commit SHA:** `47a49510bed17fd94064d23ddfc912357a2d5cdf`  
**Git Branch:** `feature/phase3-compact-ui`  
**UPLA Deployment ID:** `upla-20261119-032142-a3784a`  
**Target Environment:** Server 1 (`172.26.41.240`, `Verdictum Core`) & Server 2 (`13.204.214.64:8000`, `Verdictum Cortex`)  

---

## 1. Automated Regression Test Suite Results

The comprehensive test suite was executed on Server 1 in `/opt/wysesoc-ai/backend` against the live deployed commit:

```bash
./venv/bin/pytest tests/test_ais_heavy_tcp_e2e.py tests/test_rule_learning_platform.py tests/test_api_422_remediation.py -q
```

### Execution Result:
```text
.........................                                                [100%]
25 passed in 6.45s
```

### Test Case Breakdown:

| Test File | Test Method | Functionality Verified | Status |
| :--- | :--- | :--- | :---: |
| `test_ais_heavy_tcp_e2e.py` | `test_01_canonical_rule_and_candidate_draft_exist` | Verified rule UUID `40498741` & draft v8 exist | **PASS** |
| `test_ais_heavy_tcp_e2e.py` | `test_02_evidence_contract_fortigate_scan_fields` | Verified 15 scan fields in evidence contract | **PASS** |
| `test_ais_heavy_tcp_e2e.py` | `test_03_fortisiem_raw_event_normalization` | Verified 100 raw FortiGate events normalization | **PASS** |
| `test_ais_heavy_tcp_e2e.py` | `test_04_token_budget_under_4096` | Verified token compactor preserves scan fields | **PASS** |
| `test_ais_heavy_tcp_e2e.py` | `test_05_claim_extraction_and_grounding` | Verified `ModelClaimExtractor` grounding logic | **PASS** |
| `test_ais_heavy_tcp_e2e.py` | `test_06_independent_validator_rejection` | Verified validator catches value fabrication | **PASS** |
| `test_ais_heavy_tcp_e2e.py` | `test_07_draft_v8_remains_draft` | Verified candidate v8 cannot auto-approve | **PASS** |
| `test_ais_heavy_tcp_e2e.py` | `test_08_sibling_rule_remains_approved_v2` | Verified sibling rule v2 APPROVED isolation | **PASS** |
| `test_ais_heavy_tcp_e2e.py` | `test_09_empirical_accuracy_not_measurable` | Verified empirical accuracy is NOT MEASURABLE | **PASS** |
| `test_ais_heavy_tcp_e2e.py` | `test_10_production_automation_disabled` | Verified production automation is DISABLED | **PASS** |
| `test_ais_heavy_tcp_e2e.py` | `test_11_v81_truncation_detection_sample_context` | Verified 768 max tokens and truncation status | **PASS** |
| `test_ais_heavy_tcp_e2e.py` | **`test_12_v82_deterministic_reasoning_integrity`** | **Verified Contradiction 1, 2, 3, Consistency & Confidence** | **PASS** |
| `test_rule_learning_platform.py` | `test_01` to `test_11` (11 tests) | Lifecycle, adjudication, promotion, and kill-switch | **PASS** |
| `test_api_422_remediation.py` | `test_01` to `test_02` (2 tests) | Schema compliance and error remediation | **PASS** |

---

## 2. Server 1 Production Health Check Verification

Direct HTTP health query against Server 1 (`http://172.26.41.240/api/health`):

```json
{
  "status": "healthy",
  "environment": "production",
  "version": "1.0.0",
  "components": {
    "database": {
      "status": "healthy",
      "database_type": "postgresql",
      "latency_ms": 2.16,
      "connected": true,
      "pool": {
        "pool_size": 20,
        "checked_in": 0,
        "checked_out": 1,
        "overflow": -19
      }
    },
    "redis_celery": {
      "status": "healthy",
      "reachable": true,
      "broker_url_redacted": "redis://127.0.0.1:6379/0",
      "live_triage_queue_depth": 0
    },
    "local_llm": {
      "status": "healthy",
      "reachable": true,
      "endpoint_configured": true,
      "base_url_redacted": "http://<configured>:8000/v1",
      "model_name": "Qwen/Qwen2.5-7B-Instruct-AWQ",
      "server_name": "Verdictum Cortex",
      "logical_hostname": "verdictum-cortex-01",
      "configured_provider": "OPENAI_COMPATIBLE",
      "endpoint_provenance": "LIVE_PROVIDER",
      "current_s2_health": "ONLINE",
      "gpu_telemetry_verified": false,
      "circuit_breaker_state": "CLOSED",
      "active_concurrent_slots": 0,
      "max_concurrent_slots": 4
    },
    "system": {
      "server_name": "Verdictum Core",
      "logical_hostname": "verdictum-core-01",
      "cpu_percent": 0.5,
      "memory_percent": 11.6,
      "memory_used_gb": 1.79,
      "memory_total_gb": 15.36,
      "disk_percent": 9.4
    }
  }
}
```

---

## 3. Server 2 GPU vLLM Integrity

- **Endpoint:** `http://13.204.214.64:8000/v1`
- **Model:** `Qwen/Qwen2.5-7B-Instruct-AWQ`
- **Context Length:** `4,096` tokens
- **Integrity Status:** **UNTOUCHED & ONLINE**. Zero restarts or reconfigurations performed.
