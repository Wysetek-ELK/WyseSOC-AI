import pytest
from httpx import AsyncClient
import respx
import httpx

from app.config import settings
from app.services.llm_config_service import LLMConfigService
from app.schemas.llm_config import LLMConfigUpdate, LLMTestConnectionRequest


def test_parse_llm_url_formats():
    # Plain IP (using RFC 5737 TEST-NET documentation range)
    p1 = LLMConfigService.parse_llm_url("192.0.2.10")
    assert p1["host"] == "192.0.2.10"
    assert p1["port"] == 8000
    assert p1["protocol"] == "http"
    assert p1["base_url"] == "http://192.0.2.10:8000/v1"

    # IP with custom port (RFC 5737 TEST-NET)
    p2 = LLMConfigService.parse_llm_url("192.0.2.10:8080")
    assert p2["host"] == "192.0.2.10"
    assert p2["port"] == 8080
    assert p2["base_url"] == "http://192.0.2.10:8080/v1"

    # Full HTTP URL with path
    p3 = LLMConfigService.parse_llm_url("http://192.0.2.20:8000/v1")
    assert p3["host"] == "192.0.2.20"
    assert p3["port"] == 8000
    assert p3["base_url"] == "http://192.0.2.20:8000/v1"

    # HTTPS with RFC 2606 domain
    p4 = LLMConfigService.parse_llm_url("https://vllm.example.org:8443")
    assert p4["host"] == "vllm.example.org"
    assert p4["port"] == 8443
    assert p4["protocol"] == "https"
    assert p4["base_url"] == "https://vllm.example.org:8443/v1"


@pytest.mark.asyncio
async def test_get_llm_config_api(client: AsyncClient, admin_token: str):
    res = await client.get(
        "/api/llm/config",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "host" in data
    assert "port" in data
    assert "base_url" in data
    assert "model_name" in data
    assert "timeout" in data
    assert "allow_mock_fallback" in data


@pytest.mark.asyncio
async def test_update_llm_config_api(client: AsyncClient, admin_token: str):
    orig_url = settings.LOCAL_LLM_BASE_URL
    try:
        update_payload = {
            "host": "192.0.2.50",
            "port": 8000,
            "protocol": "http",
            "model_name": "Qwen/Qwen2.5-7B-Instruct-AWQ",
            "timeout": 25.0,
            "allow_mock_fallback": True,
        }
        res = await client.post(
            "/api/llm/config",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=update_payload,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["host"] == "192.0.2.50"
        assert data["port"] == 8000
        assert data["base_url"] == "http://192.0.2.50:8000/v1"
        assert settings.LOCAL_LLM_BASE_URL == "http://192.0.2.50:8000/v1"
    finally:
        # Restore original URL
        settings.LOCAL_LLM_BASE_URL = orig_url


@pytest.mark.asyncio
async def test_update_llm_config_requires_admin(client: AsyncClient, analyst_token: str):
    res = await client.post(
        "/api/llm/config",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"host": "192.0.2.99"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
@respx.mock
async def test_test_llm_connection_success(client: AsyncClient, admin_token: str):
    # Mock the LLM /models endpoint using RFC 5737 TEST-NET address
    respx.get("http://192.0.2.1:8000/v1/models").respond(
        status_code=200,
        json={"data": [{"id": "Qwen/Qwen2.5-7B-Instruct-AWQ"}]},
    )

    res = await client.post(
        "/api/llm/test-connection",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"host": "192.0.2.1", "port": 8000, "timeout": 2.0},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "Qwen/Qwen2.5-7B-Instruct-AWQ" in data["message"]
    assert "Qwen/Qwen2.5-7B-Instruct-AWQ" in data["models"]


@pytest.mark.asyncio
@respx.mock
async def test_test_llm_connection_failure(client: AsyncClient, admin_token: str):
    respx.get("http://192.0.2.2:8000/v1/models").respond(
        status_code=500,
        text="Internal Server Error in vLLM engine",
    )

    res = await client.post(
        "/api/llm/test-connection",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"host": "192.0.2.2", "port": 8000, "timeout": 2.0},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert "500" in data["message"]
