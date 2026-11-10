import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.incident import Incident
from app.models.token_usage import TokenUsageRecord


@pytest.mark.asyncio
async def test_chat_status_online_and_offline(client: AsyncClient, admin_token: str):
    """
    Verifies GET /api/chat/status returns live status and models when Server 2 is online,
    and cleanly reports offline when Server 2 cannot be reached.
    """
    # 1. Mock Server 2 Online
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {"data": [{"id": "Qwen/Qwen2.5-7B-Instruct-AWQ"}]}

    mock_http_client = MagicMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)
    mock_http_client.get = AsyncMock(return_value=mock_res)

    with patch("app.api.chat.httpx.AsyncClient", return_value=mock_http_client):
        res = await client.get(
            "/api/chat/status",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["is_online"] is True
        assert "Qwen/Qwen2.5-7B-Instruct-AWQ" in data["available_models"]
        assert "Connected" in data["status_message"]

    # 2. Mock Server 2 Offline
    mock_http_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
    with patch("app.api.chat.httpx.AsyncClient", return_value=mock_http_client):
        res = await client.get(
            "/api/chat/status",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["is_online"] is False
        assert "Cannot reach Server 2" in data["status_message"]


@pytest.mark.asyncio
async def test_chat_message_with_incident_context_and_token_logging(
    client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """
    Verifies POST /api/chat/message sends conversation + optional incident context to Server 2,
    returns the LLM reply cleanly, and logs TokenUsageRecord on Server 1.
    """
    # Seed a test incident
    inc = Incident(
        incident_id="INC_CHAT_TEST_999",
        title="Heavy TCP Host Scan Fixed Port",
        event_type="PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT",
        severity="HIGH",
        source_ip="198.51.100.42",
        reporting_ip="203.0.113.10",
        raw_payload={"src": "198.51.100.42", "destIpAddr": "203.0.113.10", "destPort": 22},
    )
    db_session.add(inc)
    await db_session.commit()

    # Mock Server 2 chat completion response
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "model": "Qwen/Qwen2.5-7B-Instruct-AWQ",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Based on incident #INC_CHAT_TEST_999, 198.51.100.42 attempted heavy TCP scanning on port 22.",
                }
            }
        ],
        "usage": {
            "prompt_tokens": 210,
            "completion_tokens": 45,
            "total_tokens": 255,
        },
    }

    mock_http_client = MagicMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)
    mock_http_client.post = AsyncMock(return_value=mock_res)

    with patch("app.api.chat.httpx.AsyncClient", return_value=mock_http_client):
        res = await client.post(
            "/api/chat/message",
            json={
                "messages": [{"role": "user", "content": "Analyze this scan alert"}],
                "incident_id": "INC_CHAT_TEST_999",
                "temperature": 0.2,
                "max_tokens": 512,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["message"]["role"] == "assistant"
        assert "198.51.100.42" in data["message"]["content"]
        assert data["model"] == "Qwen/Qwen2.5-7B-Instruct-AWQ"
        assert data["prompt_tokens"] == 210
        assert data["completion_tokens"] == 45
        assert data["total_tokens"] == 255
        assert data["attached_incident_id"] == "INC_CHAT_TEST_999"

        # Verify incident context was injected into the system prompt sent to Server 2
        sent_payload = mock_http_client.post.call_args.kwargs["json"]
        system_msg = sent_payload["messages"][0]["content"]
        assert "INC_CHAT_TEST_999" in system_msg
        assert "198.51.100.42" in system_msg

    # Verify token consumption logged as CHATBOT in DB
    q = await db_session.execute(
        select(TokenUsageRecord).where(TokenUsageRecord.process_type == "CHATBOT")
    )
    tok_rec = q.scalars().first()
    assert tok_rec is not None
    assert tok_rec.total_tokens == 255
    assert tok_rec.incident_id == "INC_CHAT_TEST_999"


@pytest.mark.asyncio
async def test_chat_message_offline_returns_503(client: AsyncClient, admin_token: str):
    """Verifies HTTP 503 with helpful diagnostic message when Server 2 is unreachable."""
    mock_http_client = MagicMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)
    mock_http_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

    with patch("app.api.chat.httpx.AsyncClient", return_value=mock_http_client):
        res = await client.post(
            "/api/chat/message",
            json={"messages": [{"role": "user", "content": "Hello"}]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 503
        assert "Cannot connect to Local LLM on Server 2" in res.json()["detail"]


@pytest.mark.asyncio
async def test_chat_message_uses_extended_read_timeout_and_returns_504_detail(
    client: AsyncClient, admin_token: str
):
    """Verifies /api/chat/message configures >= 180s read timeout and returns actionable 504 detail on upstream timeout."""
    mock_http_client = MagicMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)
    mock_http_client.post = AsyncMock(side_effect=httpx.ReadTimeout("Read timed out"))

    with patch("app.api.chat.httpx.AsyncClient", return_value=mock_http_client) as client_cls:
        res = await client.post(
            "/api/chat/message",
            json={"messages": [{"role": "user", "content": "Analyze slow payload"}]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 504
        assert "180.0s limit" in res.json()["detail"]
        timeout_arg = client_cls.call_args.kwargs["timeout"]
        assert isinstance(timeout_arg, httpx.Timeout)
        assert timeout_arg.read >= 180.0


@pytest.mark.asyncio
async def test_chat_stream_emits_sse_deltas_and_logs_tokens(
    client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """Verifies POST /api/chat/stream emits SSE keepalive/deltas/done chunks and logs TokenUsageRecord."""
    sse_lines = [
        'data: {"model":"Qwen/Qwen2.5-7B-Instruct-AWQ","choices":[{"delta":{"content":"Hello "}}]}',
        'data: {"choices":[{"delta":{"content":"SOC team!"}}]}',
        'data: {"choices":[],"usage":{"prompt_tokens":20,"completion_tokens":5,"total_tokens":25}}',
        "data: [DONE]",
    ]

    class _MockStreamResp:
        status_code = 200
        headers = {"content-type": "text/event-stream"}

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aiter_lines(self):
            for item in sse_lines:
                yield item

    class _MockStreamClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, *args, **kwargs):
            return _MockStreamResp()

    with patch("app.api.chat.httpx.AsyncClient", _MockStreamClient):
        res = await client.post(
            "/api/chat/stream",
            json={"messages": [{"role": "user", "content": "Say hello"}]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]
        body = res.text
        assert ": connected" in body
        assert '"type": "delta"' in body
        assert '"content": "Hello "' in body
        assert '"content": "SOC team!"' in body
        assert '"type": "done"' in body
        assert '"total_tokens": 25' in body

    q = await db_session.execute(
        select(TokenUsageRecord).where(TokenUsageRecord.process_type == "CHATBOT")
    )
    rec = q.scalars().first()
    assert rec is not None
    assert rec.total_tokens == 25
