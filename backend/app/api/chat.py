import time
import json
import asyncio
import logging
from datetime import datetime, timezone
from app.utils.datetime_utils import utc_now
from typing import Optional, List, Dict, Any, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import httpx

from app.config import settings
from app.database import AsyncSessionLocal, get_db
from app.models.user import User
from app.models.incident import Incident
from app.models.token_usage import TokenUsageRecord
from app.api.deps import get_current_user
from app.services.llm_config_service import LLMConfigService
from app.services.provenance import classify_endpoint_status
from app.schemas.chat import (
    ChatMessageItem,
    ChatRequest,
    ChatResponse,
    ChatStatusResponse,
)

logger = logging.getLogger("ai_verdict.chat")

router = APIRouter(prefix="/chat", tags=["SOC AI Chatbot (Local LLM Server 2)"])

DEFAULT_SOC_SYSTEM_PROMPT = """You are Verdictum AI SOC Copilot, an advanced agentic cybersecurity assistant powered directly by the on-premise Local LLM running on Server 2.

Your mission is to assist SOC Tier 1/2/3 Analysts, Incident Responders, and Threat Hunters with:
- Security Alert Triage & Attack Vector Reconstruction
- MITRE ATT&CK Framework Mapping (Tactics, Techniques, and Sub-Techniques with explicit IDs e.g. T1059.001)
- Log and Command-Line Deobfuscation (PowerShell, Base64, Bash, CMD, VBScript)
- FortiSIEM correlation rules, detection logic review, and false-positive vs true-positive adjudication
- Practical containment, host isolation, artifact preservation, and eradication guidance

Guidelines:
1. Ground your analysis strictly in verified evidence, logs, and telemetry.
2. Clearly highlight indicators of compromise (IOCs), suspicious behaviors, and mitigation actions.
3. If an incident payload is attached, reference its specific IPs, ports, and event signatures.
4. Format responses cleanly with GitHub-flavored markdown, tables, and code blocks where helpful.
"""


@router.get("/status", response_model=ChatStatusResponse)
async def get_chat_llm_status(
    current_user: User = Depends(get_current_user),
):
    """
    Checks reachability, latency, and model availability of Local LLM Server 2 for the Chatbot.
    """
    cfg = await LLMConfigService.get_config()
    parsed = LLMConfigService.parse_llm_url(settings.LOCAL_LLM_BASE_URL)
    base_url = parsed["base_url"]
    models_url = f"{base_url}/models"
    available_models: List[str] = [settings.LOCAL_LLM_MODEL_NAME]
    is_online = False
    latency_ms: Optional[float] = None
    status_msg = "Server 2 offline"

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
                status_msg = f"Connected to Local LLM on Server 2 ({latency_ms}ms)"
            else:
                status_msg = f"Server 2 returned HTTP {res.status_code}"
    except httpx.TimeoutException:
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        status_msg = f"Connection to Server 2 timed out after {latency_ms}ms"
    except Exception as exc:
        status_msg = f"Cannot reach Server 2 ({type(exc).__name__}: {str(exc)})"

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
        configured_provider=prov["configured_provider"],
        endpoint_provenance=prov["endpoint_provenance"],
        current_s2_health=prov["current_s2_health"],
        gpu_telemetry_verified=prov["gpu_telemetry_verified"],
        test_environment=prov["test_environment"],
    )


def _truncate_attributes(attrs: Any, limit: int = 1000) -> Dict[str, Any]:
    """Bounds per-event telemetry attributes so oversized raw payloads do not stall Server 2 prefill."""
    if not isinstance(attrs, dict):
        return {}
    serialized = json.dumps(attrs, default=str)
    if len(serialized) <= limit:
        return attrs
    return {"_truncated_preview": serialized[:limit] + "..."}


async def _prepare_chat_upstream(
    req: ChatRequest,
    db: AsyncSession,
) -> Tuple[str, Dict[str, Any], Dict[str, str], Optional[Dict[str, Any]], float]:
    """Builds bounded system context, OpenAI-compatible payload, URL, and timeout configuration."""
    sys_prompt = (
        req.system_prompt.strip()
        if req.system_prompt and req.system_prompt.strip()
        else DEFAULT_SOC_SYSTEM_PROMPT
    )
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
            context_block = f"\n\n### ATTACHED INCIDENT CONTEXT (ID: #{inc.incident_id}):\n" + json.dumps(attached_incident_data, indent=2)
            sys_prompt += context_block
        else:
            logger.warning(f"Chat request referenced incident '{inc_target}', but record was not found in DB.")

    messages_payload: List[Dict[str, str]] = [{"role": "system", "content": sys_prompt}]
    for m in req.messages[-20:]:
        role = m.role.lower().strip()
        if role not in ("user", "assistant", "system"):
            role = "user"
        messages_payload.append({"role": role, "content": m.content})

    LLMConfigService.sync_runtime_settings()
    target_model = settings.LOCAL_LLM_MODEL_NAME
    parsed = LLMConfigService.parse_llm_url(settings.LOCAL_LLM_BASE_URL)
    completion_url = f"{parsed['base_url']}/chat/completions"

    payload: Dict[str, Any] = {
        "model": target_model,
        "messages": messages_payload,
        "temperature": req.temperature,
        "max_tokens": req.max_tokens,
    }
    read_timeout_sec = max(180.0, float(settings.LOCAL_LLM_TIMEOUT or 60.0))
    return completion_url, payload, parsed, attached_incident_data, read_timeout_sec


async def _record_chat_token_usage(
    db: Optional[AsyncSession],
    *,
    incident_id: Optional[str],
    attached_incident_data: Optional[Dict[str, Any]],
    model_used: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    latency_ms: float,
    username: str,
    base_url: str,
) -> None:
    """Persists Server 2 chatbot token telemetry without interrupting chat delivery on ledger failure."""
    def _build_record() -> TokenUsageRecord:
        return TokenUsageRecord(
            process_type="CHATBOT",
            process_id=f"chat-{int(time.time())}",
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
                "role": "SOC AI Chatbot",
                "attached_incident": bool(attached_incident_data),
                "server_url": base_url,
            },
        )

    try:
        if db is not None and db.is_active:
            db.add(_build_record())
            await db.commit()
            return
    except Exception as tok_err:
        logger.warning(f"Primary session token ledger write failed, retrying standalone session: {tok_err}")

    try:
        async with AsyncSessionLocal() as fallback_db:
            fallback_db.add(_build_record())
            await fallback_db.commit()
    except Exception as tok_err:
        logger.warning(f"Could not record token usage for chat: {tok_err}")


@router.post("/message", response_model=ChatResponse)
async def send_chat_message(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Conversational interface connecting directly to Local LLM on Server 2 (Qwen 2.5 7B AWQ).
    Optionally enriches the conversation with real FortiSIEM / database incident context.
    Records token consumption in the Server 1 persistent audit ledger.
    """
    completion_url, payload, parsed, attached_incident_data, read_timeout_sec = await _prepare_chat_upstream(
        req, db
    )
    sys_prompt = payload["messages"][0]["content"]
    target_model = payload["model"]

    t0 = time.perf_counter()
    timeout_cfg = httpx.Timeout(connect=10.0, read=read_timeout_sec, write=30.0, pool=10.0)

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
                logger.error(f"Server 2 returned HTTP {res.status_code}: {err_text}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Local LLM (Server 2) error ({res.status_code}): {err_text}",
                )

            data = res.json()
            choices = data.get("choices", [])
            if not choices:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Server 2 returned an empty choices array.",
                )

            reply_content = choices[0].get("message", {}).get("content", "")
            usage = data.get("usage", {})
            prompt_tokens = int(usage.get("prompt_tokens", len(sys_prompt) // 4))
            completion_tokens = int(usage.get("completion_tokens", len(reply_content) // 4))
            total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens))
            model_used = data.get("model") or target_model

            await _record_chat_token_usage(
                db,
                incident_id=req.incident_id,
                attached_incident_data=attached_incident_data,
                model_used=model_used,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                username=current_user.username,
                base_url=parsed["base_url"],
            )

            now_iso = datetime.now(timezone.utc).isoformat()
            return ChatResponse(
                message=ChatMessageItem(
                    role="assistant",
                    content=reply_content,
                    timestamp=now_iso,
                ),
                model=model_used,
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                attached_incident_id=req.incident_id if attached_incident_data else None,
                server_url=parsed["base_url"],
                is_simulated=False,
            )

    except httpx.TimeoutException:
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Inference request to Server 2 timed out after {latency_ms}ms ({read_timeout_sec}s limit). Check Server 2 GPU load or network connectivity.",
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cannot connect to Local LLM on Server 2 at {completion_url}. Please ensure vLLM is running on Server 2 and firewall allows port {parsed['port']}.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error communicating with Local LLM: {str(exc)}",
        )


def _sse_event(payload: Dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@router.post("/stream")
async def stream_chat_message(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Server-Sent Events (SSE) streaming conversational endpoint for Server 2 Local LLM.
    Emits immediate connection and periodic keepalive frames during prefill so reverse proxies
    never terminate slow generation with 504 Gateway Timeout, then streams deltas token-by-token.
    """
    completion_url, base_payload, parsed, attached_incident_data, read_timeout_sec = await _prepare_chat_upstream(
        req, db
    )
    sys_prompt = base_payload["messages"][0]["content"]
    stream_payload = {
        **base_payload,
        "stream": True,
    }

    async def event_generator():
        yield ": connected\n\n"
        t0 = time.perf_counter()
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
                            content_txt = choices_list[0].get("message", {}).get("content", "") if choices_list else ""
                            synthetic_chunk = {
                                "model": data_obj.get("model"),
                                "usage": data_obj.get("usage"),
                                "choices": [{"delta": {"content": content_txt}}],
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
                    "error",
                    504,
                    f"Inference request to Server 2 timed out after {elapsed_ms}ms ({read_timeout_sec}s limit). Check Server 2 GPU load or network connectivity.",
                ))
            except httpx.ConnectError:
                await line_queue.put((
                    "error",
                    503,
                    f"Cannot connect to Local LLM on Server 2 at {completion_url}. Please ensure vLLM is running on Server 2 and firewall allows port {parsed['port']}.",
                ))
            except Exception as exc:
                await line_queue.put((
                    "error",
                    500,
                    f"Unexpected error communicating with Local LLM: {str(exc)}",
                ))

        producer_task = asyncio.create_task(_produce_upstream_lines())
        accumulated_chunks: List[str] = []
        model_used = base_payload["model"]
        usage_stats: Dict[str, Any] = {}

        try:
            while True:
                try:
                    kind, val, extra = await asyncio.wait_for(line_queue.get(), timeout=12.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue

                if kind == "eof":
                    break
                if kind == "error":
                    yield _sse_event({"type": "error", "status_code": val, "detail": extra})
                    return

                line = (val or "").strip()
                if not line or line.startswith(":"):
                    continue
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                else:
                    continue

                if data_str == "[DONE]":
                    break

                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                if chunk.get("model"):
                    model_used = chunk["model"]
                if isinstance(chunk.get("usage"), dict):
                    usage_stats = chunk["usage"]

                choices = chunk.get("choices") or []
                if choices:
                    delta = choices[0].get("delta") or {}
                    text_piece = delta.get("content")
                    if text_piece:
                        accumulated_chunks.append(text_piece)
                        yield _sse_event({"type": "delta", "content": text_piece})

            full_reply = "".join(accumulated_chunks)
            latency_ms = round((time.perf_counter() - t0) * 1000, 1)
            prompt_tokens = int(usage_stats.get("prompt_tokens", len(sys_prompt) // 4))
            completion_tokens = int(usage_stats.get("completion_tokens", max(1, len(full_reply) // 4) if full_reply else 0))
            total_tokens = int(usage_stats.get("total_tokens", prompt_tokens + completion_tokens))

            await _record_chat_token_usage(
                db,
                incident_id=req.incident_id,
                attached_incident_data=attached_incident_data,
                model_used=model_used,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                username=current_user.username,
                base_url=parsed["base_url"],
            )

            yield _sse_event({
                "type": "done",
                "model": model_used,
                "latency_ms": latency_ms,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "attached_incident_id": req.incident_id if attached_incident_data else None,
                "server_url": parsed["base_url"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        finally:
            if not producer_task.done():
                producer_task.cancel()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
