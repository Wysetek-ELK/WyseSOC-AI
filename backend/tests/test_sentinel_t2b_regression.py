import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.user import User
from app.models.incident import Incident, HistoricalGroundTruth
from app.models.prompt import RulePrompt, PromptVersion
from app.models.rule import Rule
from app.models.chat import SentinelConversation, SentinelMessage
from app.services.sentinel_token_budget import SentinelTokenBudgetService
from app.services.gpu_manager import gpu_workload_manager, CircuitState
from app.utils.security import get_password_hash, create_access_token


class _MockSseResp:
    def __init__(self, lines, status_code=200, headers=None):
        self._lines = lines
        self.status_code = status_code
        self.headers = headers or {"content-type": "text/event-stream"}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def aread(self):
        return b""

    async def aiter_lines(self):
        for item in self._lines:
            yield item


class _MockSseClient:
    def __init__(self, lines_or_exc, captured_payloads=None):
        self._lines_or_exc = lines_or_exc
        self._captured_payloads = captured_payloads

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def stream(self, method, url, **kwargs):
        if self._captured_payloads is not None:
            self._captured_payloads.append(kwargs.get("json"))
        if isinstance(self._lines_or_exc, Exception):
            raise self._lines_or_exc
        return _MockSseResp(self._lines_or_exc)


def _extract_sse_events(body: str):
    events = []
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            raw = line[5:].strip()
            if raw and raw != "[DONE]":
                events.append(json.loads(raw))
    return events


@pytest.mark.asyncio
async def test_rt01_rt02_rt05_rt13_context_aware_budget_and_completion(
    client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """RT01/RT02/RT05/RT13: Auto context-aware budget exceeds legacy 1024 limit and completes cleanly."""
    captured = []
    sse_lines = [
        'data: {"model":"Qwen/Qwen3-14B-AWQ","choices":[{"delta":{"content":"Section A: Complete. "}}]}',
        'data: {"choices":[{"delta":{"content":"Section I: Verdict TRUE_POSITIVE [COMPLETE]"}}]}',
        'data: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":310,"completion_tokens":1450,"total_tokens":1760}}',
        "data: [DONE]",
    ]
    old_verified = settings.LOCAL_LLM_VERIFIED_MAX_MODEL_LEN
    old_ctx = settings.LOCAL_LLM_CONTEXT_BUDGET
    settings.LOCAL_LLM_VERIFIED_MAX_MODEL_LEN = 8192
    settings.LOCAL_LLM_CONTEXT_BUDGET = 8192
    try:
        with patch("app.api.chat.httpx.AsyncClient", lambda *a, **kw: _MockSseClient(sse_lines, captured)):
            res = await client.post(
                "/api/chat/stream",
                json={"messages": [{"role": "user", "content": "Analyze Sections A through I."}]},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
    finally:
        settings.LOCAL_LLM_VERIFIED_MAX_MODEL_LEN = old_verified
        settings.LOCAL_LLM_CONTEXT_BUDGET = old_ctx

    assert res.status_code == 200
    assert len(captured) == 1
    sent = captured[0]
    assert sent["max_tokens"] > 7000
    assert sent["max_tokens"] + 310 <= 8192
    assert sent["stream_options"] == {"include_usage": True}

    events = _extract_sse_events(res.text)
    done_evt = next(e for e in events if e.get("type") == "done")
    assert done_evt["status"] == "COMPLETED"
    assert done_evt["finish_reason"] == "stop"
    assert done_evt["prompt_tokens"] == 310
    assert done_evt["completion_tokens"] == 1450
    assert done_evt["effective_context_window"] == 8192
    assert done_evt["continuation_available"] is False


@pytest.mark.asyncio
async def test_rt07_history_near_context_capacity_trims_oldest_with_disclosure():
    """RT07: History near 8192 capacity trims oldest turns while preserving system prompt & latest query."""
    history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": ("historical turn detail " * 80) + f"#{i}"}
        for i in range(30)
    ]
    decision = await SentinelTokenBudgetService.allocate_budget(
        system_prompt="Mandatory SOC System Policy.",
        history_messages=history,
        current_user_message={"role": "user", "content": "Latest critical question: verify threshold."},
        model_name="Qwen/Qwen3-14B-AWQ",
        verified_max_model_len=8192,
        configured_context_budget=8192,
        use_remote_tokenize=False,
    )
    assert decision.can_proceed is True
    assert decision.history_trimmed_count > 0
    assert decision.available_completion_budget >= SentinelTokenBudgetService.MIN_USABLE_COMPLETION_TOKENS
    assert decision.budgeted_messages[0]["content"] == "Mandatory SOC System Policy."
    assert decision.budgeted_messages[-1]["content"] == "Latest critical question: verify threshold."
    assert "Trimmed" in (decision.context_warning or "")


@pytest.mark.asyncio
async def test_rt08_input_exceeding_context_capacity_fails_closed(client: AsyncClient, admin_token: str):
    """RT08: Oversized single message exceeding 8192 fails closed with explicit 422 / CONTEXT_BUDGET_EXCEEDED."""
    huge_text = "192.168.1.10 -> 10.0.0.5 TCP port 443 SYN packet telemetry row.\n" * 900
    old_verified = settings.LOCAL_LLM_VERIFIED_MAX_MODEL_LEN
    old_ctx = settings.LOCAL_LLM_CONTEXT_BUDGET
    settings.LOCAL_LLM_VERIFIED_MAX_MODEL_LEN = 8192
    settings.LOCAL_LLM_CONTEXT_BUDGET = 8192
    try:
        res_msg = await client.post(
            "/api/chat/message",
            json={"messages": [{"role": "user", "content": huge_text}]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_msg.status_code == 422
        assert "exceeds the available model context" in res_msg.json()["detail"]

        res_stream = await client.post(
            "/api/chat/stream",
            json={"messages": [{"role": "user", "content": huge_text}]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_stream.status_code == 200
        events = _extract_sse_events(res_stream.text)
        err_evt = next(e for e in events if e.get("type") == "error")
        assert err_evt["status"] == "CONTEXT_BUDGET_EXCEEDED"
        assert err_evt["status_code"] == 422
    finally:
        settings.LOCAL_LLM_VERIFIED_MAX_MODEL_LEN = old_verified
        settings.LOCAL_LLM_CONTEXT_BUDGET = old_ctx


@pytest.mark.asyncio
async def test_rt09_rt14_rt15_truncation_detected_and_safe_continuation(
    client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """RT09/RT14/RT15: finish_reason=length marks TRUNCATED; continuation preserves original & rejects overflow."""
    trunc_lines = [
        'data: {"model":"Qwen/Qwen3-14B-AWQ","choices":[{"delta":{"content":"Section A complete. Section C partial"}}]}',
        'data: {"choices":[{"delta":{},"finish_reason":"length"}],"usage":{"prompt_tokens":300,"completion_tokens":128,"total_tokens":428}}',
        "data: [DONE]",
    ]
    old_verified = settings.LOCAL_LLM_VERIFIED_MAX_MODEL_LEN
    old_ctx = settings.LOCAL_LLM_CONTEXT_BUDGET
    settings.LOCAL_LLM_VERIFIED_MAX_MODEL_LEN = 8192
    settings.LOCAL_LLM_CONTEXT_BUDGET = 8192
    try:
        with patch("app.api.chat.httpx.AsyncClient", lambda *a, **kw: _MockSseClient(trunc_lines)):
            res1 = await client.post(
                "/api/chat/stream",
                json={"messages": [{"role": "user", "content": "Run T2 analysis"}], "max_tokens": 128},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
        assert res1.status_code == 200
        done1 = next(e for e in _extract_sse_events(res1.text) if e.get("type") == "done")
        assert done1["status"] == "TRUNCATED"
        assert done1["finish_reason"] == "length"
        assert done1["continuation_available"] is True
        conv_id = done1["conversation_id"]
        msg_id = done1["message_id"]

        # RT14: Continue safely
        cont_lines = [
            'data: {"model":"Qwen/Qwen3-14B-AWQ","choices":[{"delta":{"content":"... Section I: Final Verdict."}}]}',
            'data: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":400,"completion_tokens":45,"total_tokens":445}}',
            "data: [DONE]",
        ]
        with patch("app.api.chat.httpx.AsyncClient", lambda *a, **kw: _MockSseClient(cont_lines)):
            res2 = await client.post(
                "/api/chat/continue",
                json={"conversation_id": conv_id, "message_id": msg_id},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
        assert res2.status_code == 200
        done2 = next(e for e in _extract_sse_events(res2.text) if e.get("type") == "done")
        assert done2["status"] == "COMPLETED"
        assert done2["is_continuation"] is True
        assert done2["parent_message_id"] == msg_id
        assert done2["continuation_index"] == 1

        # Verify original partial response was preserved untouched
        conv_res = await client.get(
            f"/api/chat/conversations/{conv_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        msgs = conv_res.json()["messages"]
        assert len(msgs) == 3  # user + truncated assistant + continuation assistant
        assert msgs[1]["content"] == "Section A complete. Section C partial"
        assert msgs[1]["status"] == "TRUNCATED"
        assert msgs[2]["is_continuation"] is True

        # RT15: Insufficient context for continuation fails cleanly with 422
        settings.LOCAL_LLM_VERIFIED_MAX_MODEL_LEN = 1024
        settings.LOCAL_LLM_CONTEXT_BUDGET = 1024
        # Make original message very large so continuation cannot fit in 1024 context
        m_row = (await db_session.execute(select(SentinelMessage).where(SentinelMessage.id == msg_id))).scalar_one()
        m_row.content = "word " * 900
        await db_session.commit()

        res3 = await client.post(
            "/api/chat/continue",
            json={"conversation_id": conv_id, "message_id": msg_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res3.status_code == 422
        assert "Insufficient remaining context" in res3.json()["detail"]
    finally:
        settings.LOCAL_LLM_VERIFIED_MAX_MODEL_LEN = old_verified
        settings.LOCAL_LLM_CONTEXT_BUDGET = old_ctx


@pytest.mark.asyncio
async def test_rt10_rt11_stream_interruption_and_timeout_preserved(client: AsyncClient, admin_token: str):
    """RT10/RT11: EOF without [DONE] -> INTERRUPTED with partial text saved; timeout -> TIMEOUT."""
    # RT10: partial deltas then abrupt EOF (no [DONE])
    interrupted_lines = [
        'data: {"model":"Qwen/Qwen3-14B-AWQ","choices":[{"delta":{"content":"Partial evidence "}}]}',
        'data: {"choices":[{"delta":{"content":"extracted so far"}}]}',
    ]
    with patch("app.api.chat.httpx.AsyncClient", lambda *a, **kw: _MockSseClient(interrupted_lines)):
        res = await client.post(
            "/api/chat/stream",
            json={"messages": [{"role": "user", "content": "Run T3.1"}]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert res.status_code == 200
    done_evt = next(e for e in _extract_sse_events(res.text) if e.get("type") == "done")
    assert done_evt["status"] == "INTERRUPTED"
    assert done_evt["stream_termination"] == "eof_without_done_marker"
    assert done_evt["continuation_available"] is True

    # RT11: Timeout exception during stream
    with patch("app.api.chat.httpx.AsyncClient", lambda *a, **kw: _MockSseClient(httpx.ReadTimeout("read timed out"))):
        res_to = await client.post(
            "/api/chat/stream",
            json={"messages": [{"role": "user", "content": "Slow query"}]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    events_to = _extract_sse_events(res_to.text)
    err_evt = next(e for e in events_to if e.get("type") == "error")
    assert err_evt["status"] == "TIMEOUT"
    assert err_evt["status_code"] == 504


@pytest.mark.asyncio
async def test_qwen3_reasoning_delta_and_partial_json_unicode(client: AsyncClient, admin_token: str):
    """Phase G/H: Reasoning deltas are separated from visible content; partial JSON & Unicode survive."""
    lines = [
        'data: {"model":"Qwen/Qwen3-14B-AWQ","choices":[{"delta":{"reasoning_content":"Internal step 1"}}]}',
        'data: {"choices":[{"delta":{"content":"Verdict — "}}]}',
        'data: {"choices":[{"delta":{"content":"TRUE_POSITIVE ✅"}}]}',
        'data: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":100,"completion_tokens":20,"total_tokens":120,"completion_tokens_details":{"reasoning_tokens":12}}}',
        "data: [DONE]",
    ]
    with patch("app.api.chat.httpx.AsyncClient", lambda *a, **kw: _MockSseClient(lines)):
        res = await client.post(
            "/api/chat/stream",
            json={"messages": [{"role": "user", "content": "Check reasoning split"}]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    events = _extract_sse_events(res.text)
    deltas = "".join(e["content"] for e in events if e.get("type") == "delta")
    r_deltas = "".join(e["content"] for e in events if e.get("type") == "reasoning_delta")
    done_evt = next(e for e in events if e.get("type") == "done")
    assert deltas == "Verdict — TRUE_POSITIVE ✅"
    assert r_deltas == "Internal step 1"
    assert done_evt["reasoning_tokens"] == 12
    assert done_evt["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_rt17_rt18_rt19_rbac_isolation_and_circuit_breaker(
    client: AsyncClient, admin_token: str, analyst_token: str
):
    """RT17/RT18/RT19: Strict user isolation on conversations/requests/continuation & circuit breaker protection."""
    # Unauthenticated rejected
    unauth = await client.get("/api/chat/conversations")
    assert unauth.status_code == 401

    sse_lines = [
        'data: {"model":"Qwen/Qwen3-14B-AWQ","choices":[{"delta":{"content":"Admin private analysis"}}]}',
        'data: {"choices":[{"delta":{},"finish_reason":"length"}],"usage":{"prompt_tokens":50,"completion_tokens":10,"total_tokens":60}}',
        "data: [DONE]",
    ]
    with patch("app.api.chat.httpx.AsyncClient", lambda *a, **kw: _MockSseClient(sse_lines)):
        res = await client.post(
            "/api/chat/stream",
            json={"messages": [{"role": "user", "content": "Private admin chat"}]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    done = next(e for e in _extract_sse_events(res.text) if e.get("type") == "done")
    conv_id = done["conversation_id"]
    msg_id = done["message_id"]
    req_id = done["request_id"]

    # Analyst cannot list, view, delete, query telemetry, or continue Admin's conversation
    list_analyst = await client.get("/api/chat/conversations", headers={"Authorization": f"Bearer {analyst_token}"})
    assert list_analyst.status_code == 200
    assert all(c["id"] != conv_id for c in list_analyst.json())

    for ep_fn in [
        lambda: client.get(f"/api/chat/conversations/{conv_id}", headers={"Authorization": f"Bearer {analyst_token}"}),
        lambda: client.delete(f"/api/chat/conversations/{conv_id}", headers={"Authorization": f"Bearer {analyst_token}"}),
        lambda: client.get(f"/api/chat/requests/{req_id}", headers={"Authorization": f"Bearer {analyst_token}"}),
        lambda: client.post(
            "/api/chat/continue",
            json={"conversation_id": conv_id, "message_id": msg_id},
            headers={"Authorization": f"Bearer {analyst_token}"},
        ),
    ]:
        resp = await ep_fn()
        assert resp.status_code == 403

    # RT19: Normal truncation did NOT trip circuit breaker; manual OPEN circuit breaker returns 503
    assert gpu_workload_manager.circuit_breaker.state == CircuitState.CLOSED
    gpu_workload_manager.circuit_breaker.state = CircuitState.OPEN
    gpu_workload_manager.circuit_breaker.last_failure_time = 9999999999.0
    try:
        cb_res = await client.post(
            "/api/chat/message",
            json={"messages": [{"role": "user", "content": "Test CB"}]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert cb_res.status_code == 503
    finally:
        gpu_workload_manager.circuit_breaker.state = CircuitState.CLOSED
        gpu_workload_manager.circuit_breaker.consecutive_failures = 0
        gpu_workload_manager.circuit_breaker.last_failure_time = 0.0


@pytest.mark.asyncio
async def test_rt20_rt21_rt22_ais_policy_and_ground_truth_unchanged(
    client: AsyncClient, admin_token: str, db_session: AsyncSession
):
    """RT20/RT21/RT22: Sentinel chat operations never mutate Rules, PromptVersions, Incidents, or GroundTruth."""
    rule = Rule(
        rule_id="PH_RULE_TEST_SENTINEL",
        name="Test Rule",
        event_type="PH_RULE_TEST_SENTINEL",
        severity="MEDIUM",
        status="ACTIVE",
    )
    db_session.add(rule)
    await db_session.flush()

    inc = Incident(
        incident_id="INC_GUARD_1",
        rule_id=rule.id,
        title="Test Incident",
        event_type="PH_RULE_TEST_SENTINEL",
        severity="MEDIUM",
        source_ip="10.0.0.5",
    )
    db_session.add(inc)
    await db_session.flush()

    gt = HistoricalGroundTruth(
        incident_id=inc.id,
        resolution="True Positive",
        cleared_reason="Confirmed scan",
    )
    db_session.add(gt)
    await db_session.commit()

    sse_lines = [
        'data: {"model":"Qwen/Qwen3-14B-AWQ","choices":[{"delta":{"content":"Analysis complete."}}]}',
        'data: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":120,"completion_tokens":10,"total_tokens":130}}',
        "data: [DONE]",
    ]
    with patch("app.api.chat.httpx.AsyncClient", lambda *a, **kw: _MockSseClient(sse_lines)):
        res = await client.post(
            "/api/chat/stream",
            json={"messages": [{"role": "user", "content": "Analyze"}], "incident_id": "INC_GUARD_1"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert res.status_code == 200

    inc_after = (await db_session.execute(select(Incident).where(Incident.id == inc.id))).scalar_one()
    gt_after = (await db_session.execute(select(HistoricalGroundTruth).where(HistoricalGroundTruth.incident_id == inc.id))).scalar_one()
    assert inc_after.ai_verdict is None
    assert gt_after.resolution == "True Positive"
