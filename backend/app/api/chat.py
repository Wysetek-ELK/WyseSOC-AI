import time
import json
import uuid
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
import httpx

from app.config import settings
from app.database import AsyncSessionLocal, get_db
from app.models.user import User
from app.models.incident import Incident
from app.models.token_usage import TokenUsageRecord
from app.models.chat import SentinelConversation, SentinelMessage
from app.api.deps import get_current_user
from app.services.llm_config_service import LLMConfigService
from app.services.sentinel_token_budget import SentinelTokenBudgetService, SentinelBudgetDecision
from app.services.tokenizer_service import ModelTokenizerService
from app.services.gpu_manager import gpu_workload_manager, CircuitBreakerOpenException
from app.services.provenance import classify_endpoint_status
from app.utils.datetime_utils import utc_now
from app.schemas.chat import (
    ChatMessageItem,
    ChatRequest,
    ContinueChatRequest,
    ChatResponse,
    ChatStatusResponse,
    ChatConversationSummary,
    ChatConversationDetail,
)

logger = logging.getLogger("ai_verdict.chat")

router = APIRouter(prefix="/chat", tags=["Verdictum Sentinel (Verdictum Cortex)"])

STATUS_QUEUED = "QUEUED"
STATUS_GENERATING = "GENERATING"
STATUS_COMPLETED = "COMPLETED"
STATUS_TRUNCATED = "TRUNCATED"
STATUS_INTERRUPTED = "INTERRUPTED"
STATUS_TIMEOUT = "TIMEOUT"
STATUS_FAILED = "FAILED"
STATUS_CANCELLED = "CANCELLED"
STATUS_BUDGET_EXCEEDED = "CONTEXT_BUDGET_EXCEEDED"

MAX_CONTINUATION_ATTEMPTS = 3
STREAM_KEEPALIVE_INTERVAL_SEC = 10.0
SLOT_ACQUIRE_TIMEOUT_SEC = 15.0

DEFAULT_SOC_SYSTEM_PROMPT = """You are Verdictum Sentinel, an AI SOC Investigation Copilot and advanced cybersecurity assistant powered directly by Verdictum Cortex (on-premise inference engine).

Your mission is to assist SOC Tier 1/2/3 Analysts, Incident Responders, and Threat Hunters with:
- Incident triage and investigation (Security Alert Triage & Attack Vector Reconstruction)
- FortiSIEM detection rule analysis, correlation logic review, and false-positive vs true-positive adjudication
- MITRE ATT&CK Framework Mapping (Tactics, Techniques, and Sub-Techniques with explicit IDs e.g. T1059.001)
- Suspicious script and payload analysis (PowerShell, Base64, Bash, CMD, VBScript)
- Threat intelligence interpretation, IOC identification, and behavioral correlation
- Containment and response recommendations (host isolation, artifact preservation, eradication playbooks)

Guidelines:
1. Ground your analysis strictly in verified evidence, logs, and telemetry.
2. Clearly highlight indicators of compromise (IOCs), suspicious behaviors, and mitigation actions.
3. If an incident payload is attached, reference its specific IPs, ports, and event signatures.
4. Format responses cleanly with GitHub-flavored markdown, tables, and code blocks where helpful.
"""


def _is_test_runtime() -> bool:
    import sys
    return "pytest" in sys.modules or getattr(settings, "APP_ENV", "").lower() in ("testing", "test")


def _log_chat_event(**fields: Any) -> None:
    """Structured observability log strictly excluding secrets, credentials, and raw incident telemetry."""
    safe_payload = {k: v for k, v in fields.items() if v is not None}
    logger.info("sentinel_chat_event %s", json.dumps(safe_payload, default=str))


def _truncate_attributes(attrs: Any, limit: int = 1000) -> Dict[str, Any]:
    """Bounds per-event telemetry attributes so oversized raw payloads do not stall Server 2 prefill."""
    if not isinstance(attrs, dict):
        return {}
    serialized = json.dumps(attrs, default=str)
    if len(serialized) <= limit:
        return attrs
    return {"_truncated_preview": serialized[:limit] + "..."}


def _derive_conversation_title(messages: List[ChatMessageItem], incident_id: Optional[str]) -> str:
    first_user = next((m.content.strip() for m in messages if m.role == "user" and m.content.strip()), "")
    clean = " ".join(first_user.split())
    if incident_id and clean:
        return f"#{incident_id} · {clean[:80]}"
    if clean:
        return clean[:100]
    if incident_id:
        return f"Incident #{incident_id} Investigation"
    return "Sentinel Investigation"


def _classify_terminal_status(
    *,
    finish_reason: Optional[str],
    saw_done_marker: bool,
    completion_tokens: int,
    effective_max_tokens: int,
    error_kind: Optional[str] = None,
) -> Tuple[str, str]:
    """Determines explicit response lifecycle state and stream termination reason."""
    if error_kind == "timeout":
        return STATUS_TIMEOUT, "idle_or_read_timeout"
    if error_kind == "cancelled":
        return STATUS_CANCELLED, "client_cancelled"
    if error_kind == "error":
        return STATUS_FAILED, "upstream_error"

    norm_finish = (finish_reason or "").strip().lower() or None
    if norm_finish == "length":
        return STATUS_TRUNCATED, "finish_reason_length"
    if norm_finish in ("abort", "error"):
        return STATUS_INTERRUPTED, f"finish_reason_{norm_finish}"
    if not saw_done_marker:
        return STATUS_INTERRUPTED, "eof_without_done_marker"
    if norm_finish is None and effective_max_tokens > 0 and completion_tokens >= effective_max_tokens:
        return STATUS_TRUNCATED, "completion_budget_exhausted"
    if norm_finish in ("stop", "eos", None):
        return STATUS_COMPLETED, "done_marker"
    return STATUS_TRUNCATED, f"finish_reason_{norm_finish}"


@router.get("/status", response_model=ChatStatusResponse)
async def get_chat_llm_status(
    current_user: User = Depends(get_current_user),
):
    """Checks reachability, latency, model availability, and verified context capacity of Verdictum Cortex."""
    LLMConfigService.sync_runtime_settings()
    parsed = LLMConfigService.parse_llm_url(settings.LOCAL_LLM_BASE_URL)
    base_url = parsed["base_url"]
    models_url = f"{base_url}/models"
    available_models: List[str] = [settings.LOCAL_LLM_MODEL_NAME]
    is_online = False
    latency_ms: Optional[float] = None
    verified_max_len: Optional[int] = getattr(settings, "LOCAL_LLM_VERIFIED_MAX_MODEL_LEN", None)
    status_msg = "Verdictum Cortex (Server 2) offline"

    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=min(settings.LOCAL_LLM_TIMEOUT, 8.0)) as client:
            res = await client.get(
                models_url,
                headers={"Authorization": f"Bearer {settings.LOCAL_LLM_API_KEY}"},
            )
            latency_ms = round((time.perf_counter() - t0) * 1000, 1)
            if res.status_code == 200:
                is_online = True
                data = res.json()
                models_list = [m.get("id") for m in data.get("data", []) if m.get("id")]
                if models_list:
                    available_models = models_list
                extracted_len = LLMConfigService._extract_max_model_len(data, settings.LOCAL_LLM_MODEL_NAME)
                if extracted_len:
                    verified_max_len = extracted_len
                    settings.LOCAL_LLM_VERIFIED_MAX_MODEL_LEN = extracted_len
                    LLMConfigService._cached_verified_max_model_len = extracted_len
                status_msg = f"Connected to Verdictum Cortex (Server 2) ({latency_ms}ms)"
            else:
                status_msg = f"Verdictum Cortex (Server 2) returned HTTP {res.status_code}"
    except httpx.TimeoutException:
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        status_msg = f"Connection to Verdictum Cortex (Server 2) timed out after {latency_ms}ms"
    except Exception as exc:
        status_msg = f"Cannot reach Server 2 (Verdictum Cortex) ({type(exc).__name__}: {str(exc)})"

    effective_ctx = SentinelTokenBudgetService.resolve_effective_context_window(
        verified_max_model_len=verified_max_len,
        configured_context_budget=getattr(settings, "LOCAL_LLM_CONTEXT_BUDGET", 8192),
    )

    prov = classify_endpoint_status(
        is_healthy=is_online,
        raw_status="ONLINE" if is_online else "OFFLINE",
        base_url=base_url,
        metrics_available=False,
        configured_provider="OPENAI_COMPATIBLE",
    )
    return ChatStatusResponse(
        is_online=is_online,
        host=parsed["host"],
        port=parsed["port"],
        protocol=parsed["protocol"],
        base_url=base_url,
        model_name=settings.LOCAL_LLM_MODEL_NAME,
        available_models=available_models,
        latency_ms=latency_ms,
        status_message=status_msg,
        logical_hostname="verdictum-cortex-01",
        server_name="Verdictum Cortex",
        configured_provider=prov["configured_provider"],
        endpoint_provenance=prov["endpoint_provenance"],
        current_s2_health=prov["current_s2_health"],
        gpu_telemetry_verified=prov["gpu_telemetry_verified"],
        test_environment=prov["test_environment"],
        verified_max_model_len=verified_max_len,
        effective_context_window=effective_ctx,
        enable_thinking=bool(getattr(settings, "LOCAL_LLM_ENABLE_THINKING", False)),
    )


async def _build_system_prompt(
    req: ChatRequest,
    db: AsyncSession,
) -> Tuple[str, int, Optional[Dict[str, Any]]]:
    base_sys_prompt = (
        req.system_prompt.strip()
        if req.system_prompt and req.system_prompt.strip()
        else DEFAULT_SOC_SYSTEM_PROMPT
    )
    base_len_chars = len(base_sys_prompt)
    sys_prompt = base_sys_prompt
    attached_incident_data: Optional[Dict[str, Any]] = None

    if req.incident_id and req.incident_id.strip():
        inc_target = req.incident_id.strip()
        stmt = (
            select(Incident)
            .where((Incident.incident_id == inc_target) | (Incident.id == inc_target))
            .options(selectinload(Incident.events), selectinload(Incident.rule))
        )
        res = await db.execute(stmt)
        inc = res.scalar_one_or_none()

        if inc:
            raw = inc.raw_payload or {}
            attached_incident_data = {
                "incident_id": inc.incident_id,
                "title": inc.title,
                "event_type": inc.event_type,
                "severity": inc.severity,
                "status": inc.status_name,
                "source_ip": inc.source_ip,
                "destination_ip": raw.get("destIpAddr") or raw.get("targetIp") or inc.reporting_ip or "",
                "destination_port": raw.get("destPort") or raw.get("dstPort"),
                "description": (inc.description or "")[:800],
                "detail": (inc.detail or "")[:1200],
                "event_count": len(inc.events) if inc.events else 0,
                "ai_verdict": inc.ai_verdict.get("verdict") if inc.ai_verdict else "PENDING",
                "ai_verdict_reason": (inc.ai_verdict.get("reason") or "")[:600] if inc.ai_verdict else None,
                "sample_events": [
                    {
                        "event_type": ev.event_type,
                        "raw_log": (ev.raw_log or "")[:300],
                        "attributes": _truncate_attributes(ev.attributes),
                    }
                    for ev in (inc.events[:5] if inc.events else [])
                ],
            }
            context_block = f"\n\n### ATTACHED INCIDENT CONTEXT (ID: #{inc.incident_id}):\n" + json.dumps(
                attached_incident_data, indent=2
            )
            sys_prompt += context_block
        else:
            logger.warning("Chat request referenced incident '%s', but record was not found in DB.", inc_target)

    return sys_prompt, base_len_chars, attached_incident_data


async def _prepare_chat_upstream(
    req: ChatRequest,
    db: AsyncSession,
    *,
    allow_history_trim: bool = True,
) -> Tuple[str, Dict[str, Any], Dict[str, str], Optional[Dict[str, Any]], float, SentinelBudgetDecision]:
    """Builds context-budgeted OpenAI-compatible payload, URL, timeout, and budget decision."""
    sys_prompt, base_len_chars, attached_incident_data = await _build_system_prompt(req, db)

    normalized_msgs: List[Dict[str, str]] = []
    for m in req.messages[-40:]:
        role = m.role.lower().strip()
        if role not in ("user", "assistant", "system"):
            role = "user"
        normalized_msgs.append({"role": role, "content": m.content})

    if not normalized_msgs:
        raise HTTPException(status_code=400, detail="At least one chat message is required.")

    history_msgs = normalized_msgs[:-1]
    current_msg = normalized_msgs[-1]

    LLMConfigService.sync_runtime_settings()
    target_model = settings.LOCAL_LLM_MODEL_NAME
    parsed = LLMConfigService.parse_llm_url(settings.LOCAL_LLM_BASE_URL)
    completion_url = f"{parsed['base_url']}/chat/completions"

    is_test = _is_test_runtime()
    verified_max_len = getattr(settings, "LOCAL_LLM_VERIFIED_MAX_MODEL_LEN", None)
    if verified_max_len is None and not is_test:
        verified_max_len = await LLMConfigService.get_or_probe_verified_max_model_len()

    enable_thinking = bool(getattr(settings, "LOCAL_LLM_ENABLE_THINKING", False))
    budget = await SentinelTokenBudgetService.allocate_budget(
        system_prompt=sys_prompt,
        history_messages=history_msgs,
        current_user_message=current_msg,
        model_name=target_model,
        base_url=parsed["base_url"],
        api_key=settings.LOCAL_LLM_API_KEY,
        verified_max_model_len=verified_max_len,
        configured_context_budget=getattr(settings, "LOCAL_LLM_CONTEXT_BUDGET", 8192),
        requested_max_tokens=req.max_tokens,
        enable_thinking=enable_thinking,
        base_system_len_chars=base_len_chars,
        allow_history_trim=allow_history_trim,
        use_remote_tokenize=not is_test,
    )

    payload: Dict[str, Any] = {
        "model": target_model,
        "messages": budget.budgeted_messages,
        "temperature": req.temperature,
        "max_tokens": budget.effective_completion_budget,
    }
    if "qwen3" in target_model.lower():
        payload["chat_template_kwargs"] = {"enable_thinking": enable_thinking}

    read_timeout_sec = max(180.0, float(settings.LOCAL_LLM_TIMEOUT or 180.0))
    return completion_url, payload, parsed, attached_incident_data, read_timeout_sec, budget


async def _record_chat_token_usage(
    db: Optional[AsyncSession],
    *,
    request_id: str,
    incident_id: Optional[str],
    attached_incident_data: Optional[Dict[str, Any]],
    model_used: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    latency_ms: float,
    username: str,
    base_url: str,
    status_value: str,
    finish_reason: Optional[str],
) -> None:
    """Persists Server 2 chatbot token telemetry without interrupting chat delivery on ledger failure."""
    def _build_record() -> TokenUsageRecord:
        return TokenUsageRecord(
            process_type="CHATBOT",
            process_id=request_id,
            incident_id=incident_id,
            rule_id=attached_incident_data.get("event_type") if attached_incident_data else None,
            model_identifier=model_used,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=int(latency_ms),
            is_simulated=False,
            executed_by_user=username,
            timestamp=utc_now(),
            details={
                "role": "Verdictum Sentinel",
                "component": "Sentinel — AI SOC Investigation Copilot",
                "attached_incident": bool(attached_incident_data),
                "server_url": base_url,
                "logical_hostname": "verdictum-cortex-01",
                "status": status_value,
                "finish_reason": finish_reason,
            },
        )

    try:
        if db is not None and db.is_active:
            db.add(_build_record())
            await db.commit()
            return
    except Exception as tok_err:
        logger.warning("Primary session token ledger write failed, retrying standalone session: %s", tok_err)

    try:
        async with AsyncSessionLocal() as fallback_db:
            fallback_db.add(_build_record())
            await fallback_db.commit()
    except Exception as tok_err:
        logger.warning("Could not record token usage for chat: %s", tok_err)


async def _ensure_conversation_and_seed_turn(
    db: AsyncSession,
    *,
    current_user: User,
    req: ChatRequest,
    request_id: str,
    model_name: str,
    effective_ctx: int,
    requested_max_tokens: int,
) -> Tuple[Optional[str], Optional[str]]:
    if not req.persist:
        return None, None

    conv: Optional[SentinelConversation] = None
    if req.conversation_id:
        res = await db.execute(
            select(SentinelConversation).where(SentinelConversation.id == req.conversation_id)
        )
        conv = res.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        if conv.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied to conversation.")
        if req.incident_id and not conv.attached_incident_id:
            conv.attached_incident_id = req.incident_id
        conv.updated_at = utc_now()
    else:
        conv = SentinelConversation(
            user_id=current_user.id,
            customer=getattr(current_user, "customer", None),
            title=_derive_conversation_title(req.messages, req.incident_id),
            attached_incident_id=req.incident_id,
        )
        db.add(conv)
        await db.flush()

    last_user = next((m for m in reversed(req.messages) if m.role == "user"), req.messages[-1])
    user_msg = SentinelMessage(
        conversation_id=conv.id,
        user_id=current_user.id,
        role="user",
        content=last_user.content,
        status=STATUS_COMPLETED,
        attached_incident_id=req.incident_id,
        metadata_json={},
    )
    assistant_msg = SentinelMessage(
        conversation_id=conv.id,
        user_id=current_user.id,
        request_id=request_id,
        role="assistant",
        content="",
        status=STATUS_GENERATING,
        model_identifier=model_name,
        requested_max_tokens=requested_max_tokens,
        effective_context_window=effective_ctx,
        attached_incident_id=req.incident_id,
        metadata_json={},
    )
    db.add(user_msg)
    db.add(assistant_msg)
    await db.commit()
    return conv.id, assistant_msg.id


async def _finalize_assistant_message(
    db: Optional[AsyncSession],
    *,
    message_id: Optional[str],
    content: str,
    reasoning_content: Optional[str],
    status_value: str,
    finish_reason: Optional[str],
    stream_termination: Optional[str],
    model_used: str,
    prompt_tokens: int,
    completion_tokens: int,
    reasoning_tokens: Optional[int],
    total_tokens: int,
    requested_max_tokens: int,
    effective_context_window: int,
    latency_ms: float,
    metadata_extra: Optional[Dict[str, Any]] = None,
) -> None:
    if not message_id:
        return

    async def _apply(session: AsyncSession) -> None:
        res = await session.execute(select(SentinelMessage).where(SentinelMessage.id == message_id))
        msg = res.scalar_one_or_none()
        if not msg:
            return
        msg.content = content
        msg.reasoning_content = reasoning_content
        msg.status = status_value
        msg.finish_reason = finish_reason
        msg.stream_termination = stream_termination
        msg.model_identifier = model_used
        msg.prompt_tokens = prompt_tokens
        msg.completion_tokens = completion_tokens
        msg.reasoning_tokens = reasoning_tokens
        msg.total_tokens = total_tokens
        msg.requested_max_tokens = requested_max_tokens
        msg.effective_context_window = effective_context_window
        msg.latency_ms = latency_ms
        msg.metadata_json = metadata_extra or {}
        msg.updated_at = utc_now()
        await session.commit()

    try:
        if db is not None and db.is_active:
            await _apply(db)
            return
    except Exception as exc:
        logger.warning("Primary session message finalize failed, retrying standalone: %s", exc)

    try:
        async with AsyncSessionLocal() as fallback_db:
            await _apply(fallback_db)
    except Exception as exc:
        logger.warning("Failed to finalize assistant message %s: %s", message_id, exc)


def _extract_reasoning_tokens(usage: Dict[str, Any], reasoning_text: str, model_name: str) -> Optional[int]:
    details = usage.get("completion_tokens_details")
    if isinstance(details, dict) and details.get("reasoning_tokens") is not None:
        return int(details["reasoning_tokens"])
    if reasoning_text:
        return ModelTokenizerService.count_tokens(reasoning_text, model_name=model_name)
    return None


@router.get("/conversations", response_model=List[ChatConversationSummary])
async def list_conversations(
    limit: int = 25,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists Sentinel conversations belonging strictly to the authenticated user."""
    safe_limit = max(1, min(int(limit), 100))
    stmt = (
        select(SentinelConversation)
        .where(SentinelConversation.user_id == current_user.id)
        .order_by(desc(SentinelConversation.updated_at))
        .limit(safe_limit)
    )
    convs = (await db.execute(stmt)).scalars().all()
    if not convs:
        return []

    conv_ids = [c.id for c in convs]
    cnt_stmt = (
        select(SentinelMessage.conversation_id, func.count(SentinelMessage.id))
        .where(SentinelMessage.conversation_id.in_(conv_ids))
        .group_by(SentinelMessage.conversation_id)
    )
    counts = dict((await db.execute(cnt_stmt)).all())
    return [
        ChatConversationSummary(
            id=c.id,
            title=c.title,
            attached_incident_id=c.attached_incident_id,
            message_count=int(counts.get(c.id, 0)),
            created_at=c.created_at.isoformat() + "Z",
            updated_at=c.updated_at.isoformat() + "Z",
        )
        for c in convs
    ]


@router.get("/conversations/{conversation_id}", response_model=ChatConversationDetail)
async def get_conversation_detail(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Loads a persisted Sentinel conversation strictly enforcing owner isolation."""
    stmt = (
        select(SentinelConversation)
        .where(SentinelConversation.id == conversation_id)
        .options(selectinload(SentinelConversation.messages))
    )
    conv = (await db.execute(stmt)).scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    if conv.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied to conversation.")

    return ChatConversationDetail(
        id=conv.id,
        title=conv.title,
        attached_incident_id=conv.attached_incident_id,
        created_at=conv.created_at.isoformat() + "Z",
        updated_at=conv.updated_at.isoformat() + "Z",
        messages=[
            ChatMessageItem(
                id=m.id,
                role=m.role,
                content=m.content,
                reasoning_content=m.reasoning_content,
                timestamp=m.created_at.isoformat() + "Z",
                request_id=m.request_id,
                status=m.status,
                finish_reason=m.finish_reason,
                stream_termination=m.stream_termination,
                model=m.model_identifier,
                prompt_tokens=m.prompt_tokens,
                completion_tokens=m.completion_tokens,
                reasoning_tokens=m.reasoning_tokens,
                total_tokens=m.total_tokens,
                requested_max_tokens=m.requested_max_tokens,
                effective_context_window=m.effective_context_window,
                latency_ms=m.latency_ms,
                attached_incident_id=m.attached_incident_id,
                is_continuation=m.is_continuation,
                parent_message_id=m.parent_message_id,
                continuation_index=m.continuation_index,
                continuation_available=(
                    m.role == "assistant"
                    and m.status in (STATUS_TRUNCATED, STATUS_INTERRUPTED, STATUS_TIMEOUT)
                    and m.continuation_index < MAX_CONTINUATION_ATTEMPTS
                ),
                context_warning=(m.metadata_json or {}).get("context_warning"),
            )
            for m in conv.messages
        ],
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SentinelConversation).where(SentinelConversation.id == conversation_id)
    conv = (await db.execute(stmt)).scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    if conv.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied to conversation.")
    await db.delete(conv)
    await db.commit()
    return {"deleted": True, "conversation_id": conversation_id}


@router.get("/requests/{request_id}")
async def get_request_telemetry(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns execution telemetry for a Sentinel request strictly owned by current_user."""
    stmt = select(SentinelMessage).where(SentinelMessage.request_id == request_id)
    msg = (await db.execute(stmt)).scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Request not found.")
    if msg.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied to request telemetry.")
    return {
        "request_id": msg.request_id,
        "conversation_id": msg.conversation_id,
        "message_id": msg.id,
        "status": msg.status,
        "finish_reason": msg.finish_reason,
        "stream_termination": msg.stream_termination,
        "model": msg.model_identifier,
        "prompt_tokens": msg.prompt_tokens,
        "completion_tokens": msg.completion_tokens,
        "reasoning_tokens": msg.reasoning_tokens,
        "total_tokens": msg.total_tokens,
        "requested_max_tokens": msg.requested_max_tokens,
        "effective_context_window": msg.effective_context_window,
        "latency_ms": msg.latency_ms,
        "is_continuation": msg.is_continuation,
        "parent_message_id": msg.parent_message_id,
        "continuation_index": msg.continuation_index,
        "metadata": msg.metadata_json,
    }


@router.post("/message", response_model=ChatResponse)
async def send_chat_message(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Non-streaming conversational endpoint with context-aware token budgeting,
    explicit lifecycle status, finish_reason verification, and conversation persistence.
    """
    request_id = f"chat-{uuid.uuid4().hex[:12]}"
    completion_url, payload, parsed, attached_incident_data, read_timeout_sec, budget = await _prepare_chat_upstream(
        req, db
    )
    target_model = payload["model"]

    if not budget.can_proceed:
        _log_chat_event(
            request_id=request_id,
            model=target_model,
            effective_context_window=budget.effective_context_window,
            input_tokens=budget.actual_input_tokens,
            requested_max_tokens=req.max_tokens,
            effective_max_tokens=0,
            status=STATUS_BUDGET_EXCEEDED,
            error_type="context_budget_exceeded",
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=budget.context_warning,
        )

    conv_id, assistant_msg_id = await _ensure_conversation_and_seed_turn(
        db,
        current_user=current_user,
        req=req,
        request_id=request_id,
        model_name=target_model,
        effective_ctx=budget.effective_context_window,
        requested_max_tokens=budget.effective_completion_budget,
    )

    try:
        await asyncio.wait_for(gpu_workload_manager.acquire_inference_slot(), timeout=SLOT_ACQUIRE_TIMEOUT_SEC)
    except CircuitBreakerOpenException as cb_err:
        await _finalize_assistant_message(
            db,
            message_id=assistant_msg_id,
            content="",
            reasoning_content=None,
            status_value=STATUS_FAILED,
            finish_reason=None,
            stream_termination="circuit_breaker_open",
            model_used=target_model,
            prompt_tokens=budget.actual_input_tokens,
            completion_tokens=0,
            reasoning_tokens=None,
            total_tokens=budget.actual_input_tokens,
            requested_max_tokens=budget.effective_completion_budget,
            effective_context_window=budget.effective_context_window,
            latency_ms=0.0,
            metadata_extra={"error_detail": str(cb_err)},
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(cb_err))
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Verdictum Cortex inference queue is busy; retry shortly.",
        )

    t0 = time.perf_counter()
    timeout_cfg = httpx.Timeout(connect=10.0, read=read_timeout_sec, write=30.0, pool=10.0)
    infra_success = False
    infra_error = ""

    try:
        async with httpx.AsyncClient(timeout=timeout_cfg) as client:
            res = await client.post(
                completion_url,
                headers={
                    "Authorization": f"Bearer {settings.LOCAL_LLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            latency_ms = round((time.perf_counter() - t0) * 1000, 1)

            if res.status_code != 200:
                err_text = res.text[:400]
                infra_error = f"HTTP {res.status_code}"
                logger.error("Verdictum Cortex (Server 2) returned HTTP %s: %s", res.status_code, err_text)
                await _finalize_assistant_message(
                    db,
                    message_id=assistant_msg_id,
                    content="",
                    reasoning_content=None,
                    status_value=STATUS_FAILED,
                    finish_reason=None,
                    stream_termination="upstream_http_error",
                    model_used=target_model,
                    prompt_tokens=budget.actual_input_tokens,
                    completion_tokens=0,
                    reasoning_tokens=None,
                    total_tokens=budget.actual_input_tokens,
                    requested_max_tokens=budget.effective_completion_budget,
                    effective_context_window=budget.effective_context_window,
                    latency_ms=latency_ms,
                    metadata_extra={"status_code": res.status_code},
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Verdictum Cortex (Server 2) error ({res.status_code}): {err_text}",
                )

            data = res.json()
            choices = data.get("choices", [])
            if not choices:
                infra_error = "empty_choices"
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Verdictum Cortex (Server 2) returned an empty choices array.",
                )

            infra_success = True
            choice0 = choices[0]
            msg_obj = choice0.get("message") or {}
            reply_content = msg_obj.get("content") or ""
            reasoning_text = msg_obj.get("reasoning_content") or msg_obj.get("reasoning") or ""
            finish_reason = choice0.get("finish_reason")
            usage = data.get("usage") or {}
            model_used = data.get("model") or target_model

            prompt_tokens = int(usage.get("prompt_tokens") or budget.actual_input_tokens)
            completion_tokens = int(
                usage.get("completion_tokens")
                or ModelTokenizerService.count_tokens(reply_content, model_name=model_used)
            )
            reasoning_tokens = _extract_reasoning_tokens(usage, reasoning_text, model_used)
            total_tokens = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens))

            status_val, term_reason = _classify_terminal_status(
                finish_reason=finish_reason,
                saw_done_marker=True,
                completion_tokens=completion_tokens,
                effective_max_tokens=budget.effective_completion_budget,
            )

            await _finalize_assistant_message(
                db,
                message_id=assistant_msg_id,
                content=reply_content,
                reasoning_content=reasoning_text or None,
                status_value=status_val,
                finish_reason=finish_reason,
                stream_termination=term_reason,
                model_used=model_used,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                reasoning_tokens=reasoning_tokens,
                total_tokens=total_tokens,
                requested_max_tokens=budget.effective_completion_budget,
                effective_context_window=budget.effective_context_window,
                latency_ms=latency_ms,
                metadata_extra={
                    "history_trimmed_count": budget.history_trimmed_count,
                    "context_warning": budget.context_warning,
                    "token_count_source": budget.token_count_source,
                },
            )

            await _record_chat_token_usage(
                db,
                request_id=request_id,
                incident_id=req.incident_id,
                attached_incident_data=attached_incident_data,
                model_used=model_used,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                username=current_user.username,
                base_url=parsed["base_url"],
                status_value=status_val,
                finish_reason=finish_reason,
            )

            _log_chat_event(
                request_id=request_id,
                conversation_id=conv_id,
                model=model_used,
                effective_context_window=budget.effective_context_window,
                input_tokens=prompt_tokens,
                requested_max_tokens=req.max_tokens,
                effective_max_tokens=budget.effective_completion_budget,
                completion_tokens=completion_tokens,
                reasoning_tokens=reasoning_tokens,
                finish_reason=finish_reason,
                status=status_val,
                stream_termination=term_reason,
                duration_ms=latency_ms,
                history_trimmed_count=budget.history_trimmed_count,
            )

            now_iso = datetime.now(timezone.utc).isoformat()
            continuation_avail = status_val in (STATUS_TRUNCATED, STATUS_INTERRUPTED, STATUS_TIMEOUT) and bool(conv_id)
            return ChatResponse(
                message=ChatMessageItem(
                    id=assistant_msg_id,
                    role="assistant",
                    content=reply_content,
                    reasoning_content=reasoning_text or None,
                    timestamp=now_iso,
                    request_id=request_id,
                    status=status_val,
                    finish_reason=finish_reason,
                    stream_termination=term_reason,
                    model=model_used,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    reasoning_tokens=reasoning_tokens,
                    total_tokens=total_tokens,
                    requested_max_tokens=budget.effective_completion_budget,
                    effective_context_window=budget.effective_context_window,
                    latency_ms=latency_ms,
                    attached_incident_id=req.incident_id if attached_incident_data else None,
                    continuation_available=continuation_avail,
                    context_warning=budget.context_warning,
                ),
                conversation_id=conv_id,
                message_id=assistant_msg_id,
                request_id=request_id,
                status=status_val,
                finish_reason=finish_reason,
                stream_termination=term_reason,
                model=model_used,
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                reasoning_tokens=reasoning_tokens,
                total_tokens=total_tokens,
                requested_max_tokens=budget.effective_completion_budget,
                effective_context_window=budget.effective_context_window,
                history_trimmed_count=budget.history_trimmed_count,
                continuation_available=continuation_avail,
                context_warning=budget.context_warning,
                attached_incident_id=req.incident_id if attached_incident_data else None,
                server_url=parsed["base_url"],
                is_simulated=False,
            )

    except httpx.TimeoutException:
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        infra_error = "timeout"
        await _finalize_assistant_message(
            db,
            message_id=assistant_msg_id,
            content="",
            reasoning_content=None,
            status_value=STATUS_TIMEOUT,
            finish_reason=None,
            stream_termination="read_timeout",
            model_used=target_model,
            prompt_tokens=budget.actual_input_tokens,
            completion_tokens=0,
            reasoning_tokens=None,
            total_tokens=budget.actual_input_tokens,
            requested_max_tokens=budget.effective_completion_budget,
            effective_context_window=budget.effective_context_window,
            latency_ms=latency_ms,
        )
        _log_chat_event(
            request_id=request_id,
            conversation_id=conv_id,
            model=target_model,
            effective_context_window=budget.effective_context_window,
            input_tokens=budget.actual_input_tokens,
            requested_max_tokens=req.max_tokens,
            effective_max_tokens=budget.effective_completion_budget,
            status=STATUS_TIMEOUT,
            duration_ms=latency_ms,
            error_type="timeout",
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Inference request to Verdictum Cortex (Server 2) timed out after {latency_ms}ms ({read_timeout_sec}s limit). Check Verdictum Cortex GPU load or network connectivity.",
        )
    except httpx.ConnectError:
        infra_error = "connect_error"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cannot connect to Local LLM on Server 2 (Verdictum Cortex) at {completion_url}. Please ensure vLLM is running on Verdictum Cortex (verdictum-cortex-01) and firewall allows port {parsed['port']}.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        infra_error = type(exc).__name__
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error communicating with Local LLM: {str(exc)}",
        )
    finally:
        await gpu_workload_manager.release_inference_slot(success=infra_success, error_message=infra_error)


def _sse_event(payload: Dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _build_streaming_response(
    *,
    request: Optional[Request],
    db: Optional[AsyncSession],
    current_user: User,
    request_id: str,
    conv_id: Optional[str],
    assistant_msg_id: Optional[str],
    completion_url: str,
    base_payload: Dict[str, Any],
    parsed: Dict[str, Any],
    attached_incident_data: Optional[Dict[str, Any]],
    incident_id: Optional[str],
    read_timeout_sec: float,
    budget: SentinelBudgetDecision,
    requested_max_tokens_raw: Optional[int],
    is_continuation: bool = False,
    parent_message_id: Optional[str] = None,
    continuation_index: int = 0,
) -> StreamingResponse:
    stream_payload: Dict[str, Any] = {
        **base_payload,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    target_model = base_payload["model"]
    idle_timeout_sec = max(60.0, float(read_timeout_sec))

    async def event_generator():
        yield ": connected\n\n"
        t0 = time.perf_counter()
        yield _sse_event({
            "type": "status",
            "status": STATUS_QUEUED,
            "request_id": request_id,
            "conversation_id": conv_id,
            "message_id": assistant_msg_id,
        })

        slot_acquired = False
        infra_success = False
        infra_error = ""
        try:
            await asyncio.wait_for(gpu_workload_manager.acquire_inference_slot(), timeout=SLOT_ACQUIRE_TIMEOUT_SEC)
            slot_acquired = True
        except CircuitBreakerOpenException as cb_err:
            yield _sse_event({
                "type": "error",
                "status_code": 503,
                "status": STATUS_FAILED,
                "request_id": request_id,
                "detail": str(cb_err),
            })
            await _finalize_assistant_message(
                db,
                message_id=assistant_msg_id,
                content="",
                reasoning_content=None,
                status_value=STATUS_FAILED,
                finish_reason=None,
                stream_termination="circuit_breaker_open",
                model_used=target_model,
                prompt_tokens=budget.actual_input_tokens,
                completion_tokens=0,
                reasoning_tokens=None,
                total_tokens=budget.actual_input_tokens,
                requested_max_tokens=budget.effective_completion_budget,
                effective_context_window=budget.effective_context_window,
                latency_ms=0.0,
            )
            return
        except asyncio.TimeoutError:
            yield _sse_event({
                "type": "error",
                "status_code": 503,
                "status": STATUS_FAILED,
                "request_id": request_id,
                "detail": "Verdictum Cortex inference queue is busy; please retry shortly.",
            })
            return

        yield _sse_event({
            "type": "status",
            "status": STATUS_GENERATING,
            "request_id": request_id,
            "conversation_id": conv_id,
            "message_id": assistant_msg_id,
            "model": target_model,
            "requested_max_tokens": budget.effective_completion_budget,
            "effective_context_window": budget.effective_context_window,
            "prompt_tokens_estimated": budget.actual_input_tokens,
            "history_trimmed_count": budget.history_trimmed_count,
            "context_warning": budget.context_warning,
            "is_continuation": is_continuation,
            "parent_message_id": parent_message_id,
            "continuation_index": continuation_index,
        })

        timeout_cfg = httpx.Timeout(connect=10.0, read=read_timeout_sec, write=30.0, pool=10.0)
        line_queue: asyncio.Queue = asyncio.Queue()

        async def _produce_upstream_lines():
            try:
                async with httpx.AsyncClient(timeout=timeout_cfg) as client:
                    async with client.stream(
                        "POST",
                        completion_url,
                        headers={
                            "Authorization": f"Bearer {settings.LOCAL_LLM_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json=stream_payload,
                    ) as res:
                        if res.status_code != 200:
                            err_body = (await res.aread()).decode("utf-8", errors="ignore")[:400]
                            await line_queue.put(("error", 502, f"Local LLM (Server 2) error ({res.status_code}): {err_body}"))
                            return
                        ctype = (res.headers.get("content-type") or "").lower()
                        if "application/json" in ctype:
                            raw_bytes = await res.aread()
                            data_obj = json.loads(raw_bytes.decode("utf-8", errors="ignore"))
                            choices_list = data_obj.get("choices") or []
                            choice0 = choices_list[0] if choices_list else {}
                            msg0 = choice0.get("message") or {}
                            content_txt = msg0.get("content", "")
                            reasoning_txt = msg0.get("reasoning_content") or msg0.get("reasoning") or ""
                            synthetic_chunk = {
                                "model": data_obj.get("model"),
                                "usage": data_obj.get("usage"),
                                "choices": [
                                    {
                                        "delta": {
                                            "content": content_txt,
                                            **({"reasoning_content": reasoning_txt} if reasoning_txt else {}),
                                        },
                                        "finish_reason": choice0.get("finish_reason") or "stop",
                                    }
                                ],
                            }
                            await line_queue.put(("line", f"data: {json.dumps(synthetic_chunk)}", None))
                            await line_queue.put(("line", "data: [DONE]", None))
                        else:
                            async for raw_line in res.aiter_lines():
                                await line_queue.put(("line", raw_line, None))
                await line_queue.put(("eof", None, None))
            except httpx.TimeoutException:
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
                await line_queue.put((
                    "timeout",
                    504,
                    f"Inference request to Verdictum Cortex (Server 2) timed out after {elapsed_ms}ms ({read_timeout_sec}s limit). Check Verdictum Cortex GPU load or network connectivity.",
                ))
            except httpx.ConnectError:
                await line_queue.put((
                    "error",
                    503,
                    f"Cannot connect to Local LLM on Server 2 (Verdictum Cortex) at {completion_url}. Please ensure vLLM is running on Verdictum Cortex (verdictum-cortex-01) and firewall allows port {parsed['port']}.",
                ))
            except Exception as exc:
                await line_queue.put((
                    "error",
                    500,
                    f"Unexpected error communicating with Local LLM: {str(exc)}",
                ))

        producer_task = asyncio.create_task(_produce_upstream_lines())
        accumulated_chunks: List[str] = []
        accumulated_reasoning: List[str] = []
        model_used = target_model
        usage_stats: Dict[str, Any] = {}
        finish_reason: Optional[str] = None
        saw_done_marker = False
        error_kind: Optional[str] = None
        error_detail: Optional[str] = None
        error_status_code: int = 200
        last_activity = time.perf_counter()
        partial_json_buf = ""

        try:
            while True:
                if request is not None and await request.is_disconnected():
                    error_kind = "cancelled"
                    error_detail = "Client disconnected before stream completion."
                    break

                try:
                    kind, val, extra = await asyncio.wait_for(line_queue.get(), timeout=STREAM_KEEPALIVE_INTERVAL_SEC)
                    last_activity = time.perf_counter()
                except asyncio.TimeoutError:
                    if (time.perf_counter() - last_activity) >= idle_timeout_sec:
                        error_kind = "timeout"
                        error_status_code = 504
                        error_detail = f"Streaming idle timeout exceeded ({idle_timeout_sec}s with no upstream tokens)."
                        break
                    yield ": keepalive\n\n"
                    continue

                if kind == "eof":
                    break
                if kind == "timeout":
                    error_kind = "timeout"
                    error_status_code = int(val or 504)
                    error_detail = str(extra)
                    break
                if kind == "error":
                    error_kind = "error"
                    error_status_code = int(val or 500)
                    error_detail = str(extra)
                    break

                line = (val or "").strip()
                if not line or line.startswith(":"):
                    continue
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                elif partial_json_buf:
                    data_str = line
                else:
                    continue

                if data_str == "[DONE]":
                    saw_done_marker = True
                    break

                candidate_str = f"{partial_json_buf}{data_str}" if partial_json_buf else data_str
                try:
                    chunk = json.loads(candidate_str)
                    partial_json_buf = ""
                except json.JSONDecodeError:
                    # Buffer partial multi-line JSON chunk cleanly up to a safe cap
                    if len(candidate_str) < 65536:
                        partial_json_buf = candidate_str
                    else:
                        partial_json_buf = ""
                    continue

                if chunk.get("model"):
                    model_used = chunk["model"]
                if isinstance(chunk.get("usage"), dict):
                    usage_stats = chunk["usage"]

                choices = chunk.get("choices") or []
                if choices:
                    choice0 = choices[0]
                    if choice0.get("finish_reason") is not None:
                        finish_reason = str(choice0.get("finish_reason"))
                    delta = choice0.get("delta") or {}
                    reasoning_piece = delta.get("reasoning_content") or delta.get("reasoning")
                    if reasoning_piece:
                        accumulated_reasoning.append(reasoning_piece)
                        yield _sse_event({"type": "reasoning_delta", "content": reasoning_piece})
                    text_piece = delta.get("content")
                    if text_piece:
                        accumulated_chunks.append(text_piece)
                        yield _sse_event({"type": "delta", "content": text_piece})

            full_reply = "".join(accumulated_chunks)
            full_reasoning = "".join(accumulated_reasoning)
            latency_ms = round((time.perf_counter() - t0) * 1000, 1)

            prompt_tokens = int(usage_stats.get("prompt_tokens") or budget.actual_input_tokens)
            if usage_stats.get("completion_tokens") is not None:
                completion_tokens = int(usage_stats["completion_tokens"])
            elif full_reply or full_reasoning:
                completion_tokens = ModelTokenizerService.count_tokens(
                    f"{full_reasoning}{full_reply}", model_name=model_used
                )
            else:
                completion_tokens = 0
            reasoning_tokens = _extract_reasoning_tokens(usage_stats, full_reasoning, model_used)
            total_tokens = int(usage_stats.get("total_tokens") or (prompt_tokens + completion_tokens))

            status_val, term_reason = _classify_terminal_status(
                finish_reason=finish_reason,
                saw_done_marker=saw_done_marker,
                completion_tokens=completion_tokens,
                effective_max_tokens=budget.effective_completion_budget,
                error_kind=error_kind,
            )

            infra_success = status_val in (STATUS_COMPLETED, STATUS_TRUNCATED, STATUS_CANCELLED)
            if not infra_success:
                infra_error = error_detail or term_reason

            await _finalize_assistant_message(
                db,
                message_id=assistant_msg_id,
                content=full_reply,
                reasoning_content=full_reasoning or None,
                status_value=status_val,
                finish_reason=finish_reason,
                stream_termination=term_reason,
                model_used=model_used,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                reasoning_tokens=reasoning_tokens,
                total_tokens=total_tokens,
                requested_max_tokens=budget.effective_completion_budget,
                effective_context_window=budget.effective_context_window,
                latency_ms=latency_ms,
                metadata_extra={
                    "history_trimmed_count": budget.history_trimmed_count,
                    "context_warning": budget.context_warning,
                    "token_count_source": budget.token_count_source,
                    "error_detail": error_detail,
                },
            )

            if full_reply or total_tokens > budget.actual_input_tokens:
                await _record_chat_token_usage(
                    db,
                    request_id=request_id,
                    incident_id=incident_id,
                    attached_incident_data=attached_incident_data,
                    model_used=model_used,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    latency_ms=latency_ms,
                    username=current_user.username,
                    base_url=parsed["base_url"],
                    status_value=status_val,
                    finish_reason=finish_reason,
                )

            _log_chat_event(
                request_id=request_id,
                conversation_id=conv_id,
                model=model_used,
                effective_context_window=budget.effective_context_window,
                input_tokens=prompt_tokens,
                requested_max_tokens=requested_max_tokens_raw,
                effective_max_tokens=budget.effective_completion_budget,
                completion_tokens=completion_tokens,
                reasoning_tokens=reasoning_tokens,
                finish_reason=finish_reason,
                status=status_val,
                stream_termination=term_reason,
                duration_ms=latency_ms,
                error_type=error_kind,
                history_trimmed_count=budget.history_trimmed_count,
            )

            # If hard error occurred with ZERO streamed content, emit error SSE event for client error handling
            if error_kind in ("error", "timeout") and not full_reply:
                yield _sse_event({
                    "type": "error",
                    "status_code": error_status_code,
                    "status": status_val,
                    "request_id": request_id,
                    "conversation_id": conv_id,
                    "message_id": assistant_msg_id,
                    "detail": error_detail or "Verdictum Cortex inference failed.",
                })
                return

            continuation_avail = (
                status_val in (STATUS_TRUNCATED, STATUS_INTERRUPTED, STATUS_TIMEOUT)
                and bool(conv_id)
                and continuation_index < MAX_CONTINUATION_ATTEMPTS
            )

            yield _sse_event({
                "type": "done",
                "request_id": request_id,
                "conversation_id": conv_id,
                "message_id": assistant_msg_id,
                "status": status_val,
                "finish_reason": finish_reason,
                "stream_termination": term_reason,
                "model": model_used,
                "latency_ms": latency_ms,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "reasoning_tokens": reasoning_tokens,
                "total_tokens": total_tokens,
                "requested_max_tokens": budget.effective_completion_budget,
                "effective_context_window": budget.effective_context_window,
                "history_trimmed_count": budget.history_trimmed_count,
                "continuation_available": continuation_avail,
                "is_continuation": is_continuation,
                "parent_message_id": parent_message_id,
                "continuation_index": continuation_index,
                "context_warning": budget.context_warning,
                "error_detail": error_detail,
                "attached_incident_id": incident_id if attached_incident_data else None,
                "server_url": parsed["base_url"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        except asyncio.CancelledError:
            infra_success = True
            await _finalize_assistant_message(
                db,
                message_id=assistant_msg_id,
                content="".join(accumulated_chunks),
                reasoning_content="".join(accumulated_reasoning) or None,
                status_value=STATUS_CANCELLED,
                finish_reason=finish_reason,
                stream_termination="client_cancelled",
                model_used=model_used,
                prompt_tokens=budget.actual_input_tokens,
                completion_tokens=ModelTokenizerService.count_tokens("".join(accumulated_chunks), model_name=model_used),
                reasoning_tokens=None,
                total_tokens=budget.actual_input_tokens,
                requested_max_tokens=budget.effective_completion_budget,
                effective_context_window=budget.effective_context_window,
                latency_ms=round((time.perf_counter() - t0) * 1000, 1),
            )
            raise
        finally:
            if not producer_task.done():
                producer_task.cancel()
            if slot_acquired:
                await gpu_workload_manager.release_inference_slot(success=infra_success, error_message=infra_error)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/stream")
async def stream_chat_message(
    req: ChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Server-Sent Events (SSE) streaming endpoint with context-aware token budgeting,
    keepalives, partial-JSON tolerance, explicit completion/truncation status, and persistence.
    """
    request_id = f"chat-{uuid.uuid4().hex[:12]}"
    completion_url, base_payload, parsed, attached_incident_data, read_timeout_sec, budget = await _prepare_chat_upstream(
        req, db
    )
    target_model = base_payload["model"]

    if not budget.can_proceed:
        _log_chat_event(
            request_id=request_id,
            model=target_model,
            effective_context_window=budget.effective_context_window,
            input_tokens=budget.actual_input_tokens,
            requested_max_tokens=req.max_tokens,
            effective_max_tokens=0,
            status=STATUS_BUDGET_EXCEEDED,
            error_type="context_budget_exceeded",
        )

        async def budget_error_gen():
            yield ": connected\n\n"
            yield _sse_event({
                "type": "error",
                "status_code": 422,
                "status": STATUS_BUDGET_EXCEEDED,
                "request_id": request_id,
                "prompt_tokens": budget.actual_input_tokens,
                "effective_context_window": budget.effective_context_window,
                "detail": budget.context_warning,
            })

        return StreamingResponse(
            budget_error_gen(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    conv_id, assistant_msg_id = await _ensure_conversation_and_seed_turn(
        db,
        current_user=current_user,
        req=req,
        request_id=request_id,
        model_name=target_model,
        effective_ctx=budget.effective_context_window,
        requested_max_tokens=budget.effective_completion_budget,
    )

    return _build_streaming_response(
        request=request,
        db=db,
        current_user=current_user,
        request_id=request_id,
        conv_id=conv_id,
        assistant_msg_id=assistant_msg_id,
        completion_url=completion_url,
        base_payload=base_payload,
        parsed=parsed,
        attached_incident_data=attached_incident_data,
        incident_id=req.incident_id,
        read_timeout_sec=read_timeout_sec,
        budget=budget,
        requested_max_tokens_raw=req.max_tokens,
    )


@router.post("/continue")
async def continue_chat_response(
    req: ContinueChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Safely continues an incomplete (TRUNCATED / INTERRUPTED / TIMEOUT) Sentinel assistant message.
    Preserves original partial response, prevents duplicate text, enforces continuation cap,
    and rejects continuation when remaining context window is insufficient.
    """
    conv_stmt = (
        select(SentinelConversation)
        .where(SentinelConversation.id == req.conversation_id)
        .options(selectinload(SentinelConversation.messages))
    )
    conv = (await db.execute(conv_stmt)).scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    if conv.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied to conversation.")

    target_msg = next((m for m in conv.messages if m.id == req.message_id), None)
    if not target_msg or target_msg.role != "assistant":
        raise HTTPException(status_code=404, detail="Target assistant message not found.")
    if target_msg.status not in (STATUS_TRUNCATED, STATUS_INTERRUPTED, STATUS_TIMEOUT):
        raise HTTPException(
            status_code=400,
            detail=f"Message status '{target_msg.status}' does not require continuation.",
        )

    root_parent_id = target_msg.parent_message_id or target_msg.id
    next_cont_index = target_msg.continuation_index + 1
    if next_cont_index > MAX_CONTINUATION_ATTEMPTS:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum continuation limit ({MAX_CONTINUATION_ATTEMPTS}) reached for this response.",
        )

    # Assemble conversation up through target_msg without altering prior history
    prior_items: List[ChatMessageItem] = []
    for m in conv.messages:
        prior_items.append(ChatMessageItem(role=m.role, content=m.content))
        if m.id == target_msg.id:
            break

    tail_anchor = (target_msg.content or "")[-180:].strip()
    cont_instruction = (
        "Your previous response stopped before completing. Continue directly from where it ended "
        "without repeating any already-written headings, paragraphs, or sentences. Complete all remaining sections."
    )
    if tail_anchor:
        cont_instruction += f"\n\nResume immediately after this exact trailing text:\n\"\"\"{tail_anchor}\"\"\""

    prior_items.append(ChatMessageItem(role="user", content=cont_instruction))

    synthetic_req = ChatRequest(
        messages=prior_items,
        incident_id=target_msg.attached_incident_id or conv.attached_incident_id,
        conversation_id=conv.id,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        persist=False,
    )

    request_id = f"cont-{uuid.uuid4().hex[:12]}"
    # Disable silent history trimming for continuation so context overflow is explicitly surfaced
    completion_url, base_payload, parsed, attached_incident_data, read_timeout_sec, budget = await _prepare_chat_upstream(
        synthetic_req, db, allow_history_trim=False
    )
    target_model = base_payload["model"]

    if not budget.can_proceed:
        _log_chat_event(
            request_id=request_id,
            conversation_id=conv.id,
            model=target_model,
            effective_context_window=budget.effective_context_window,
            input_tokens=budget.actual_input_tokens,
            requested_max_tokens=req.max_tokens,
            effective_max_tokens=0,
            status=STATUS_BUDGET_EXCEEDED,
            error_type="continuation_context_exceeded",
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Insufficient remaining context window to safely continue this response. "
                "Start a new stage or summarize earlier findings."
            ),
        )

    cont_msg = SentinelMessage(
        conversation_id=conv.id,
        user_id=current_user.id,
        request_id=request_id,
        role="assistant",
        content="",
        status=STATUS_GENERATING,
        model_identifier=target_model,
        requested_max_tokens=budget.effective_completion_budget,
        effective_context_window=budget.effective_context_window,
        attached_incident_id=synthetic_req.incident_id,
        is_continuation=True,
        parent_message_id=root_parent_id,
        continuation_index=next_cont_index,
        metadata_json={"continued_from_message_id": target_msg.id},
    )
    conv.updated_at = utc_now()
    db.add(cont_msg)
    await db.commit()

    return _build_streaming_response(
        request=request,
        db=db,
        current_user=current_user,
        request_id=request_id,
        conv_id=conv.id,
        assistant_msg_id=cont_msg.id,
        completion_url=completion_url,
        base_payload=base_payload,
        parsed=parsed,
        attached_incident_data=attached_incident_data,
        incident_id=synthetic_req.incident_id,
        read_timeout_sec=read_timeout_sec,
        budget=budget,
        requested_max_tokens_raw=req.max_tokens,
        is_continuation=True,
        parent_message_id=root_parent_id,
        continuation_index=next_cont_index,
    )
