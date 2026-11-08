import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_health_check_endpoint(client: AsyncClient):
    """
    P4-REQ-07: Verifies comprehensive /health check endpoint.
    Checks components: database, redis_celery, local_llm, system.
    """
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert data["status"] in ("healthy", "degraded", "unhealthy")
    assert "components" in data

    components = data["components"]
    assert "database" in components
    assert components["database"]["connected"] is True
    assert "system" in components
    assert "cpu_percent" in components["system"]
    assert "memory_percent" in components["system"]
    assert "local_llm" in components
    assert "circuit_breaker_state" in components["local_llm"]


@pytest.mark.asyncio
async def test_metrics_prometheus_and_json(client: AsyncClient):
    """Verifies Prometheus text metrics format and JSON metrics format."""
    # 1. Prometheus text format
    resp_prom = await client.get("/metrics")
    assert resp_prom.status_code == 200
    assert "text/plain" in resp_prom.headers.get("content-type", "")
    assert "ai_verdict_incidents_total" in resp_prom.text
    assert "ai_verdict_db_latency_seconds" in resp_prom.text

    # 2. JSON format
    resp_json = await client.get("/metrics?format=json")
    assert resp_json.status_code == 200
    assert "application/json" in resp_json.headers.get("content-type", "")
    json_data = resp_json.json()
    assert "ai_verdict_incidents_total" in json_data
    assert "ai_verdict_db_latency_seconds" in json_data
