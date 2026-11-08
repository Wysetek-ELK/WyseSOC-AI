# Report 07: Observability, Health Checks & Prometheus Metrics (P4-REQ-07)

## 1. Observability Principles & Zero-Fabrication Mandate

In accordance with Phase 1 and Phase 4 safety rules, all observability data must reflect **verifiable, genuine telemetry**:
- **Zero Mock Telemetry:** System CPU, memory, and disk utilization are measured directly from the host operating system using `psutil`.
- **Active Probing:** Database connectivity is verified with an actual `SELECT 1` query.
- **Deep Health Visibility:** Reports individual status across all infrastructure components: Database, Redis/Celery, Local LLM Server 2, and System Hardware.

---

## 2. Component-Level Health Check Endpoint (`/health` & `/api/health`)

The health endpoint provides instant diagnostic triage for load balancers, Kubernetes liveness probes (if adapted), and SOC platform engineers:

```json
{
  "status": "healthy",
  "environment": "production",
  "version": "1.0.0",
  "timestamp": 1731086400.12,
  "components": {
    "database": {
      "status": "healthy",
      "database_type": "postgresql",
      "latency_ms": 1.12,
      "connected": true,
      "pool": {
        "pool_size": 20,
        "checked_in": 19,
        "checked_out": 1,
        "overflow": 0
      }
    },
    "redis_celery": {
      "status": "healthy",
      "reachable": true,
      "broker_url_redacted": "localhost:6379/0",
      "live_triage_queue_depth": 0
    },
    "local_llm": {
      "status": "healthy",
      "reachable": true,
      "base_url": "http://10.10.20.5:8000/v1",
      "model_name": "Qwen/Qwen2.5-7B-Instruct-AWQ",
      "circuit_breaker_state": "CLOSED",
      "active_concurrent_slots": 0,
      "max_concurrent_slots": 4
    },
    "system": {
      "cpu_percent": 14.2,
      "memory_percent": 38.5,
      "memory_used_gb": 12.32,
      "memory_total_gb": 32.0,
      "disk_percent": 41.2
    }
  }
}
```

### Overall Status Aggregation Rules:
- **`healthy`:** All components operational, circuit breaker is `CLOSED`, database query latency < 100ms.
- **`degraded`:** Local LLM is unreachable, circuit breaker is `OPEN` or `HALF_OPEN`, or Celery broker is offline while async celery is configured. Live triage will abstain or queue safely.
- **`unhealthy`:** Database connection has failed (`connected = false`). The service cannot persist or retrieve data.

---

## 3. Prometheus & Structured Metrics Endpoint (`/metrics` & `/api/metrics`)

The metrics endpoint supports both standard Prometheus text scraping and JSON formats (via `Accept: application/json` or `?format=json`).

### Exported Prometheus Metrics Sample:
```text
# HELP ai_verdict_incidents_total Total security incidents evaluated by AI Verdict engine
# TYPE ai_verdict_incidents_total counter
ai_verdict_incidents_total{verdict="true_positive"} 142
ai_verdict_incidents_total{verdict="false_positive"} 289
ai_verdict_incidents_total{verdict="requires_attention"} 18

# HELP ai_verdict_db_latency_seconds Database health check probe query latency in seconds
# TYPE ai_verdict_db_latency_seconds gauge
ai_verdict_db_latency_seconds 0.0012

# HELP ai_verdict_queue_depth Pending triage tasks in live_triage queue
# TYPE ai_verdict_queue_depth gauge
ai_verdict_queue_depth 3

# HELP ai_verdict_circuit_breaker_trips_total Total times GPU Server 2 circuit breaker tripped OPEN
# TYPE ai_verdict_circuit_breaker_trips_total counter
ai_verdict_circuit_breaker_trips_total 0

# HELP ai_verdict_active_inference_requests Currently executing GPU inference requests
# TYPE ai_verdict_active_inference_requests gauge
ai_verdict_active_inference_requests 1

# HELP ai_verdict_system_cpu_percent Host CPU utilization percent
# TYPE ai_verdict_system_cpu_percent gauge
ai_verdict_system_cpu_percent 14.2

# HELP ai_verdict_system_memory_percent Host memory utilization percent
# TYPE ai_verdict_system_memory_percent gauge
ai_verdict_system_memory_percent 38.5
```

---

## 4. Verification Evidence

Test module `backend/tests/test_system_health_observability.py` validates:
- `test_health_check_endpoint`: PASSED. Confirms real component health values for database, system, redis, and local_llm.
- `test_metrics_prometheus_and_json`: PASSED. Confirms Prometheus `text/plain` format and JSON `application/json` format.

