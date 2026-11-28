import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import httpx

from app.config import settings
from app.services.tokenizer_service import ModelTokenizerService


@dataclass
class SentinelBudgetDecision:
    can_proceed: bool
    status: str  # OK | CONTEXT_BUDGET_EXCEEDED
    effective_context_window: int
    verified_max_model_len: Optional[int]
    configured_context_budget: int
    actual_input_tokens: int
    safety_margin_tokens: int
    available_completion_budget: int
    requested_max_tokens: Optional[int]
    effective_completion_budget: int
    min_usable_completion_tokens: int
    history_trimmed_count: int = 0
    token_count_source: str = "local_bpe_calibrated"
    context_warning: Optional[str] = None
    breakdown: Dict[str, int] = field(default_factory=dict)
    budgeted_messages: List[Dict[str, str]] = field(default_factory=list)


class SentinelTokenBudgetService:
    """
    Context-aware token budget manager for Verdictum Sentinel Chat.

    Accounts for:
    - Verified runtime context capacity on Server 2 (never hardcoding theoretical limits)
    - System prompt & attached incident context tokens (immutable)
    - Latest user prompt tokens (immutable)
    - Conversation history tokens (progressively trimmable oldest-first with disclosure)
    - Chat template & Qwen3 thinking-mode overhead
    - Safety margin to prevent prompt+completion overflow errors
    """

    DEFAULT_SAFETY_MARGIN_REMOTE = 32
    DEFAULT_SAFETY_MARGIN_LOCAL = 64
    MIN_USABLE_COMPLETION_TOKENS = 256
    ABSOLUTE_MIN_COMPLETION_TOKENS = 64
    PER_MESSAGE_OVERHEAD_TOKENS = 4
    GENERATION_PRIME_TOKENS = 3
    QWEN3_THINK_PRIME_TOKENS = 5

    @classmethod
    def resolve_effective_context_window(
        cls,
        verified_max_model_len: Optional[int] = None,
        configured_context_budget: Optional[int] = None,
    ) -> int:
        cfg_ctx = int(
            configured_context_budget
            if configured_context_budget is not None
            else (getattr(settings, "LOCAL_LLM_CONTEXT_BUDGET", 8192) or 8192)
        )
        if verified_max_model_len is not None and int(verified_max_model_len) > 0:
            # Never exceed verified Server 2 runtime max_model_len
            return max(1024, min(int(verified_max_model_len), cfg_ctx))
        # Without live verification, never blindly exceed 8192
        return max(1024, min(cfg_ctx, 8192) if cfg_ctx > 8192 else cfg_ctx)

    @classmethod
    def estimate_messages_tokens_local(
        cls,
        messages: List[Dict[str, str]],
        model_name: Optional[str] = None,
        enable_thinking: bool = False,
        base_system_len_chars: Optional[int] = None,
    ) -> Dict[str, Any]:
        target_model = str(model_name or getattr(settings, "LOCAL_LLM_MODEL_NAME", "Qwen/Qwen3-14B-AWQ"))
        is_qwen3 = "qwen3" in target_model.lower()

        sys_tokens = 0
        incident_tokens = 0
        history_tokens = 0
        user_tokens = 0

        last_user_idx = -1
        for idx in range(len(messages) - 1, -1, -1):
            if messages[idx].get("role") == "user":
                last_user_idx = idx
                break

        for idx, msg in enumerate(messages):
            role = msg.get("role", "user")
            content = msg.get("content", "") or ""
            if idx == 0 and role == "system":
                if base_system_len_chars is not None and len(content) > base_system_len_chars:
                    base_part = content[:base_system_len_chars]
                    inc_part = content[base_system_len_chars:]
                    sys_tokens = ModelTokenizerService.count_tokens(base_part, model_name=target_model)
                    incident_tokens = ModelTokenizerService.count_tokens(inc_part, model_name=target_model)
                else:
                    sys_tokens = ModelTokenizerService.count_tokens(content, model_name=target_model)
            elif idx == last_user_idx:
                user_tokens += ModelTokenizerService.count_tokens(content, model_name=target_model)
            else:
                history_tokens += ModelTokenizerService.count_tokens(content, model_name=target_model)

        template_overhead = (
            len(messages) * cls.PER_MESSAGE_OVERHEAD_TOKENS
            + cls.GENERATION_PRIME_TOKENS
            + (cls.QWEN3_THINK_PRIME_TOKENS if (is_qwen3 and not enable_thinking) else 0)
        )
        total = sys_tokens + incident_tokens + history_tokens + user_tokens + template_overhead
        return {
            "total_input_tokens": total,
            "source": "local_bpe_calibrated",
            "breakdown": {
                "system_prompt_tokens": sys_tokens,
                "incident_context_tokens": incident_tokens,
                "history_tokens": history_tokens,
                "current_user_tokens": user_tokens,
                "chat_template_overhead_tokens": template_overhead,
            },
        }

    @classmethod
    async def count_messages_tokens(
        cls,
        messages: List[Dict[str, str]],
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        enable_thinking: bool = False,
        base_system_len_chars: Optional[int] = None,
        use_remote_tokenize: bool = True,
    ) -> Dict[str, Any]:
        local_res = cls.estimate_messages_tokens_local(
            messages=messages,
            model_name=model_name,
            enable_thinking=enable_thinking,
            base_system_len_chars=base_system_len_chars,
        )
        if not use_remote_tokenize or not base_url:
            return local_res

        target_model = str(model_name or getattr(settings, "LOCAL_LLM_MODEL_NAME", "Qwen/Qwen3-14B-AWQ"))
        root_url = re.sub(r"/v1/?$", "", base_url.rstrip("/"))
        tokenize_url = f"{root_url}/tokenize"
        req_body: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "add_generation_prompt": True,
        }
        if "qwen3" in target_model.lower():
            req_body["chat_template_kwargs"] = {"enable_thinking": bool(enable_thinking)}

        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.post(
                    tokenize_url,
                    headers={"Authorization": f"Bearer {api_key or 'EMPTY'}"},
                    json=req_body,
                )
                if res.status_code == 200:
                    data = res.json()
                    remote_count = int(data.get("count") or len(data.get("tokens") or []))
                    if remote_count > 0:
                        local_res["total_input_tokens"] = remote_count
                        local_res["source"] = "vllm_tokenize_api"
                        local_res["breakdown"]["local_estimate"] = sum(local_res["breakdown"].values())
                        return local_res
        except Exception:
            pass
        return local_res

    @classmethod
    async def allocate_budget(
        cls,
        *,
        system_prompt: str,
        history_messages: List[Dict[str, str]],
        current_user_message: Dict[str, str],
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        verified_max_model_len: Optional[int] = None,
        configured_context_budget: Optional[int] = None,
        requested_max_tokens: Optional[int] = None,
        enable_thinking: bool = False,
        base_system_len_chars: Optional[int] = None,
        allow_history_trim: bool = True,
        use_remote_tokenize: bool = True,
    ) -> SentinelBudgetDecision:
        cfg_ctx = int(
            configured_context_budget
            if configured_context_budget is not None
            else (getattr(settings, "LOCAL_LLM_CONTEXT_BUDGET", 8192) or 8192)
        )
        effective_ctx = cls.resolve_effective_context_window(
            verified_max_model_len=verified_max_model_len,
            configured_context_budget=cfg_ctx,
        )

        # If caller explicitly asked for a tiny probe (e.g. 64..255), honor that as minimum floor;
        # otherwise require at least MIN_USABLE_COMPLETION_TOKENS (256) so responses aren't crippled.
        if requested_max_tokens is not None and int(requested_max_tokens) < cls.MIN_USABLE_COMPLETION_TOKENS:
            min_required_output = max(cls.ABSOLUTE_MIN_COMPLETION_TOKENS, int(requested_max_tokens))
        else:
            min_required_output = cls.MIN_USABLE_COMPLETION_TOKENS

        working_history = [dict(m) for m in history_messages]
        history_trimmed_count = 0

        def _assemble(hist: List[Dict[str, str]]) -> List[Dict[str, str]]:
            return [{"role": "system", "content": system_prompt}, *hist, dict(current_user_message)]

        assembled = _assemble(working_history)
        token_info = await cls.count_messages_tokens(
            messages=assembled,
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
            enable_thinking=enable_thinking,
            base_system_len_chars=base_system_len_chars,
            use_remote_tokenize=use_remote_tokenize,
        )
        safety_margin = (
            cls.DEFAULT_SAFETY_MARGIN_REMOTE
            if token_info["source"] == "vllm_tokenize_api"
            else cls.DEFAULT_SAFETY_MARGIN_LOCAL
        )
        available_completion = effective_ctx - int(token_info["total_input_tokens"]) - safety_margin

        # Progressively trim oldest conversation turns (never touching system prompt, incident context, or latest user query)
        if allow_history_trim and available_completion < min_required_output and working_history:
            while working_history and available_completion < min_required_output:
                working_history.pop(0)
                history_trimmed_count += 1
                assembled = _assemble(working_history)
                local_recheck = cls.estimate_messages_tokens_local(
                    messages=assembled,
                    model_name=model_name,
                    enable_thinking=enable_thinking,
                    base_system_len_chars=base_system_len_chars,
                )
                available_completion = effective_ctx - int(local_recheck["total_input_tokens"]) - cls.DEFAULT_SAFETY_MARGIN_LOCAL
                token_info = local_recheck
                safety_margin = cls.DEFAULT_SAFETY_MARGIN_LOCAL

            # Re-verify exact remote count once trimmed
            if use_remote_tokenize and base_url and available_completion >= min_required_output:
                token_info = await cls.count_messages_tokens(
                    messages=assembled,
                    model_name=model_name,
                    base_url=base_url,
                    api_key=api_key,
                    enable_thinking=enable_thinking,
                    base_system_len_chars=base_system_len_chars,
                    use_remote_tokenize=True,
                )
                safety_margin = (
                    cls.DEFAULT_SAFETY_MARGIN_REMOTE
                    if token_info["source"] == "vllm_tokenize_api"
                    else cls.DEFAULT_SAFETY_MARGIN_LOCAL
                )
                available_completion = effective_ctx - int(token_info["total_input_tokens"]) - safety_margin

        actual_input = int(token_info["total_input_tokens"])
        if available_completion < min_required_output:
            return SentinelBudgetDecision(
                can_proceed=False,
                status="CONTEXT_BUDGET_EXCEEDED",
                effective_context_window=effective_ctx,
                verified_max_model_len=verified_max_model_len,
                configured_context_budget=cfg_ctx,
                actual_input_tokens=actual_input,
                safety_margin_tokens=safety_margin,
                available_completion_budget=max(0, available_completion),
                requested_max_tokens=requested_max_tokens,
                effective_completion_budget=0,
                min_usable_completion_tokens=min_required_output,
                history_trimmed_count=history_trimmed_count,
                token_count_source=token_info["source"],
                context_warning=(
                    "The request exceeds the available model context. "
                    "Reduce the input or divide the investigation into smaller stages."
                ),
                breakdown=token_info["breakdown"],
                budgeted_messages=assembled,
            )

        if requested_max_tokens is not None:
            effective_completion = max(cls.ABSOLUTE_MIN_COMPLETION_TOKENS, min(int(requested_max_tokens), available_completion))
        else:
            effective_completion = available_completion

        warning_parts: List[str] = []
        if history_trimmed_count > 0:
            warning_parts.append(
                f"Trimmed {history_trimmed_count} older conversation message(s) to preserve current incident evidence and output headroom."
            )
        if requested_max_tokens is not None and int(requested_max_tokens) > available_completion:
            warning_parts.append(
                f"Requested output budget ({requested_max_tokens}) capped to available context headroom ({effective_completion} of {effective_ctx} tokens)."
            )

        return SentinelBudgetDecision(
            can_proceed=True,
            status="OK",
            effective_context_window=effective_ctx,
            verified_max_model_len=verified_max_model_len,
            configured_context_budget=cfg_ctx,
            actual_input_tokens=actual_input,
            safety_margin_tokens=safety_margin,
            available_completion_budget=available_completion,
            requested_max_tokens=requested_max_tokens,
            effective_completion_budget=effective_completion,
            min_usable_completion_tokens=min_required_output,
            history_trimmed_count=history_trimmed_count,
            token_count_source=token_info["source"],
            context_warning=" ".join(warning_parts) if warning_parts else None,
            breakdown=token_info["breakdown"],
            budgeted_messages=assembled,
        )
