import time
import json
import re
from typing import List, Dict, Any, Optional, Tuple
import httpx

from app.config import settings
from app.services.model_provider.base import BaseModelProvider, ProviderHealthResponse, StructuredModelVerdict
from app.services.confidence_normalizer import ConfidenceNormalizer
from app.services.tokenizer_service import ModelTokenizerService


def robust_parse_model_verdict_json(raw_text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Robustly parses and self-heals model JSON output from local LLMs.
    Handles:
    - Markdown code fences (```json ... ```)
    - Preamble / postamble conversation text
    - Unescaped raw newlines/tabs inside JSON strings
    - Truncated strings / unterminated quotes
    - Missing closing brackets and braces
    - Fallback regex field extraction
    """
    if not raw_text or not raw_text.strip():
        return None, "Empty response from model"

    text = raw_text.strip()

    # 0. Strip Qwen3 reasoning <think>...</think> blocks if emitted (raw text remains preserved separately)
    if "<think>" in text.lower():
        text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE).strip()

    # 1. Strip markdown fences if present
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            text = match.group(1).strip()
        else:
            text = re.sub(r"^```[a-zA-Z]*\n?", "", text).strip()
            text = re.sub(r"\n?```$", "", text).strip()

    # 2. Locate outermost JSON object
    start_idx = text.find("{")
    if start_idx == -1:
        return _regex_fallback_extract(text)

    end_idx = text.rfind("}")
    candidate = text[start_idx : end_idx + 1] if end_idx > start_idx else text[start_idx:]

    # 3. Direct parse attempt with strict=False (allows unescaped control chars like \n, \t)
    try:
        return json.loads(candidate, strict=False), None
    except json.JSONDecodeError as err:
        decode_err = str(err)

    # 4. Clean unescaped newlines/tabs inside string values
    def escape_raw_newlines(s: str) -> str:
        in_string = False
        escaped = False
        res = []
        for ch in s:
            if ch == '"' and not escaped:
                in_string = not in_string
                res.append(ch)
            elif ch == '\\' and not escaped:
                escaped = True
                res.append(ch)
            else:
                if in_string:
                    if ch == '\n':
                        res.append('\\n')
                    elif ch == '\r':
                        res.append('\\r')
                    elif ch == '\t':
                        res.append('\\t')
                    else:
                        res.append(ch)
                else:
                    res.append(ch)
                escaped = False
        return "".join(res)

    sanitized = escape_raw_newlines(candidate)
    try:
        return json.loads(sanitized, strict=False), None
    except json.JSONDecodeError:
        pass

    # 5. Self-healing for truncated JSON (unterminated strings, unclosed brackets/braces)
    # Explicitly tag _truncated_output=True so downstream validators NEVER treat a syntactically
    # repaired truncation as an unconditionally valid complete model response.
    repaired = _repair_truncated_json(sanitized)
    if repaired:
        try:
            repaired_obj = json.loads(repaired, strict=False)
            if isinstance(repaired_obj, dict):
                repaired_obj["_truncated_output"] = True
                repaired_obj["_schema_recovery_applied"] = True
                return repaired_obj, None
        except json.JSONDecodeError:
            pass

    # 6. Fallback regex extraction of fields
    fallback_dict, fallback_err = _regex_fallback_extract(text)
    if fallback_dict:
        return fallback_dict, None

    return None, f"Failed to parse JSON: {decode_err}"


def _repair_truncated_json(text: str) -> Optional[str]:
    """Attempts to complete truncated strings, arrays, and dictionaries in LIFO nesting order."""
    in_string = False
    escaped = False
    stack: List[str] = []

    clean_chars = []
    for ch in text:
        if ch == '"' and not escaped:
            in_string = not in_string
            clean_chars.append(ch)
        elif ch == '\\' and not escaped:
            escaped = True
            clean_chars.append(ch)
        else:
            if not in_string:
                if ch == '[':
                    stack.append(']')
                elif ch == '{':
                    stack.append('}')
                elif ch in (']', '}') and stack and stack[-1] == ch:
                    stack.pop()
            clean_chars.append(ch)
            escaped = False

    repaired = "".join(clean_chars)

    if in_string:
        repaired += '"'

    repaired = re.sub(r',\s*$', '', repaired)
    repaired = re.sub(r':\s*$', ': ""', repaired)

    if stack:
        repaired += "".join(reversed(stack))

    return repaired


def _regex_fallback_extract(text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Heuristic extraction of key fields when JSON cannot be parsed syntactically."""
    verdict_match = re.search(
        r'["\']?verdict["\']?\s*:\s*["\']?(TRUE_POSITIVE|FALSE_POSITIVE|REQUIRES_ATTENTION|INSUFFICIENT_EVIDENCE)["\']?',
        text,
        re.IGNORECASE,
    )
    if not verdict_match:
        return None, "No verdict found in model output"

    verdict = verdict_match.group(1).upper()

    reason_match = re.search(r'["\']?reason["\']?\s*:\s*["\']([^"\'\\]*(?:\\.[^"\'\\]*)*)', text)
    reason = reason_match.group(1) if reason_match else ""

    supporting = re.findall(r'["\']?supporting_evidence["\']?\s*:\s*\[(.*?)\]', text, re.DOTALL)
    evidence_list = []
    if supporting:
        evidence_list = [item.strip(' ",\'\n\r\t') for item in re.findall(r'["\']([^"\']+)["\']', supporting[0])]

    stripped = (text or "").strip()
    looks_truncated = ("{" in stripped and not stripped.endswith("}")) or (stripped.count("{") > stripped.count("}")) or (stripped.count("[") > stripped.count("]"))

    return {
        "verdict": verdict,
        "confidence": 0.0,
        "reason": reason,
        "supporting_evidence": evidence_list,
        "supporting_claims": [],
        "missing_evidence": [],
        "analyst_questions": [],
        "_schema_recovery_applied": True,
        "_truncated_output": bool(looks_truncated),
    }, None


class OpenAICompatibleProvider(BaseModelProvider):
    """
    Client for Server 2 local LLM inference engines (vLLM, Ollama, TGI, SGLang)
    serving an OpenAI-compatible API endpoint (e.g., http://10.x.x.x:8000/v1).
    STRICT RESTRICTION: Not called in production during Phase 3.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.0,
    ):
        self.base_url = (base_url or getattr(settings, "LOCAL_LLM_BASE_URL", "http://127.0.0.1:8000/v1")).rstrip("/")
        self.api_key = api_key or getattr(settings, "LOCAL_LLM_API_KEY", "EMPTY") or "EMPTY"
        self.model_name = (model_name or getattr(settings, "LOCAL_LLM_MODEL_NAME", "Qwen/Qwen3-14B-AWQ") or "Qwen/Qwen3-14B-AWQ").strip()
        raw_timeout = timeout_seconds if timeout_seconds is not None else getattr(settings, "LOCAL_LLM_TIMEOUT", 180.0)
        self.timeout_seconds = max(0.1, float(raw_timeout))
        raw_max_tok = max_tokens if max_tokens is not None else getattr(settings, "LOCAL_LLM_MAX_TOKENS", 768)
        self.max_tokens = max(64, min(int(raw_max_tok), 16384)) if raw_max_tok else 768
        self.temperature = temperature

    async def get_health(self) -> ProviderHealthResponse:
        start_time = time.time()
        # Derive root host:port without /v1 for fast vLLM /health endpoint
        clean_base = self.base_url.rstrip("/")
        root_url = re.sub(r"/v1$", "", clean_base)
        health_endpoints = [
            f"{root_url}/health",
            f"{clean_base}/models",
        ]
        
        last_error = None
        probe_timeout = httpx.Timeout(connect=1.5, read=2.5, write=2.0, pool=1.5)
        for endpoint in health_endpoints:
            try:
                async with httpx.AsyncClient(timeout=probe_timeout) as client:
                    res = await client.get(
                        endpoint,
                        headers={"Authorization": f"Bearer {self.api_key}"}
                    )
                    latency = int((time.time() - start_time) * 1000)
                    if res.status_code == 200:
                        return ProviderHealthResponse(
                            status="HEALTHY",
                            provider_name="OpenAICompatibleProvider",
                            is_simulated=False,
                            latency_ms=latency,
                            message=f"Connected to local inference endpoint at {self.base_url}",
                            details={"endpoint": self.base_url, "model": self.model_name},
                        )
                    elif res.status_code != 404:
                        return ProviderHealthResponse(
                            status="DEGRADED",
                            provider_name="OpenAICompatibleProvider",
                            is_simulated=False,
                            latency_ms=latency,
                            message=f"Endpoint returned HTTP {res.status_code}",
                            details={"status_code": res.status_code},
                        )
            except (httpx.ConnectTimeout, httpx.ConnectError) as e:
                # Host/port is unreachable; avoid repeating full connect timeout on sibling URL
                last_error = e
                break
            except Exception as e:
                last_error = e
                continue

        return ProviderHealthResponse(
            status="OFFLINE",
            provider_name="OpenAICompatibleProvider",
            is_simulated=False,
            latency_ms=None,
            message=f"Could not connect to inference server at {self.base_url}: {str(last_error)}",
            details={"error": str(last_error)},
        )

    async def list_models(self) -> List[str]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                if res.status_code == 200:
                    data = res.json()
                    return [m["id"] for m in data.get("data", [])]
        except Exception:
            pass
        return [self.model_name]

    @staticmethod
    def build_system_instruction(prompt_text: str) -> str:
        """Constructs the exact wire system instruction matching analyze_incident."""
        if "SECTION 11:" in prompt_text:
            return (
                f"{prompt_text}\n\n"
                "Note: Populate supporting_claims[].cited_evidence_ids (or evidence_ids) strictly from incident.canonical_evidence[].evidence_id.\n"
                "IMPORTANT: Output ONLY compact JSON. Keep 'reason' concise (< 120 words). Limit 'supporting_claims' to max 3 factual items. Do NOT dump raw logs."
            )
        return (
            f"{prompt_text}\n\n"
            "CRITICAL: Output must be a strictly valid JSON object matching this schema:\n"
            "{\n"
            '  "verdict": "TRUE_POSITIVE" | "FALSE_POSITIVE" | "REQUIRES_ATTENTION",\n'
            '  "confidence": <float 0-100>,\n'
            '  "reason": "<concise analytical summary under 120 words>",\n'
            '  "supporting_claims": [\n'
            '    {\n'
            '      "claim_type": "OBSERVED_FACT" | "TELEMETRY_OBSERVATION" | "PROCESS_EXECUTION" | "NETWORK_CONNECTION" | "FILE_HASH" | "USER_CONTEXT",\n'
            '      "field": "<canonical source_field>",\n'
            '      "asserted_value": "<exact observed value>",\n'
            '      "claim_text": "<concise grounded observation>",\n'
            '      "cited_evidence_ids": ["<canonical evidence_id from incident.canonical_evidence>"],\n'
            '      "evidence_ids": ["<canonical evidence_id from incident.canonical_evidence>"]\n'
            "    }\n"
            "  ],\n"
            '  "supporting_evidence": ["<concise string>"],\n'
            '  "contradictory_evidence": ["<concise string>"],\n'
            '  "missing_evidence": ["<concise string>"],\n'
            '  "analyst_questions": ["<concise string>"]\n'
            "}\n"
            "IMPORTANT: Output ONLY the compact JSON object. Keep 'reason' strictly under 120 words. Limit 'supporting_claims' to at most 3 factual items. Do NOT echo raw event logs or prompt text."
        )

    async def analyze_incident(
        self,
        incident_payload: Dict[str, Any],
        rule_spec: Dict[str, Any],
        prompt_text: str,
        prompt_version_number: int = 1,
        **kwargs,
    ) -> StructuredModelVerdict:
        start_time = time.time()
        incident_id = str(incident_payload.get("incident_id", ""))
        rule_id = str(rule_spec.get("id", rule_spec.get("rule_id", "")))
        system_instruction = self.build_system_instruction(prompt_text)

        # Construct compact valid JSON prompt for local LLM (avoids indent bloat inside finite context window)
        user_content = ModelTokenizerService.render_wire_user_message(incident_payload, rule_spec)

        # Pre-dispatch Wire Token Verification & Capacity Headroom Enforcement (AIS 2.4 Context Expansion)
        wire_prompt_tokens = ModelTokenizerService.count_wire_prompt_tokens(
            system_prompt=system_instruction,
            user_message=user_content,
            model_name=self.model_name,
        )

        configured_max_context = getattr(self, "context_budget", None) or getattr(settings, "LOCAL_LLM_CONTEXT_BUDGET", 4096)
        if kwargs.get("max_context_tokens"):
            try:
                configured_max_context = int(kwargs["max_context_tokens"])
            except Exception:
                pass

        effective_max_tokens = 768
        max_tokens_override = kwargs.get("max_tokens_override")
        if max_tokens_override is not None:
            try:
                override_int = int(max_tokens_override)
                if override_int >= 768:
                    effective_max_tokens = override_int
            except Exception:
                pass

        # If context budget is 4,096 or less, enforce the 3,328-token wire ceiling
        # If context budget is expanded (e.g. 8,192), wire ceiling is max_context - effective_max_tokens
        if configured_max_context <= 4096:
            effective_max_tokens = 768
            wire_prompt_ceiling = 3328
        else:
            wire_prompt_ceiling = configured_max_context - effective_max_tokens

        # Invariant: Complete model-facing prompt <= wire_prompt_ceiling, completion reserve >= 768 tokens
        if wire_prompt_tokens > wire_prompt_ceiling:
            err_msg = (
                f"CONTEXT_WINDOW_EXCEEDED: Wire prompt ({wire_prompt_tokens} tokens) exceeds "
                f"maximum wire prompt ceiling ({wire_prompt_ceiling} tokens) for {configured_max_context}-token context limit with "
                f"{effective_max_tokens} reserved completion tokens. Refusing naive truncation."
            )
            return StructuredModelVerdict(
                incident_id=incident_id,
                rule_id=rule_id,
                verdict="REQUIRES_ATTENTION",
                confidence=0.0,
                reason=err_msg,
                supporting_evidence=[],
                missing_evidence=["Reduced prompt size within wire limit"],
                analyst_questions=["Review raw incident logs in SIEM"],
                latency_ms=0,
                model_identifier=self.model_name,
                prompt_version_number=prompt_version_number,
                validation_status="CONTEXT_WINDOW_EXCEEDED",
                is_simulated=False,
                prompt_tokens=wire_prompt_tokens,
                completion_tokens=0,
                total_tokens=wire_prompt_tokens,
                finish_reason=None,
                requested_max_tokens=effective_max_tokens,
                prompt_integrity_status="UNVERIFIED",
                raw_model_response="",
            )

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": effective_max_tokens,
            "temperature": kwargs.get("temperature", self.temperature),
        }
        if kwargs.get("top_p") is not None:
            payload["top_p"] = float(kwargs["top_p"])
        if kwargs.get("seed") is not None:
            payload["seed"] = int(kwargs["seed"])
        if kwargs.get("response_format") is not None:
            payload["response_format"] = kwargs["response_format"]
        if kwargs.get("guided_json") is not None:
            payload["guided_json"] = kwargs["guided_json"]
        if "qwen3" in self.model_name.lower() or kwargs.get("enable_thinking") is not None:
            enable_thinking = (
                bool(kwargs["enable_thinking"])
                if kwargs.get("enable_thinking") is not None
                else bool(getattr(settings, "LOCAL_LLM_ENABLE_THINKING", False))
            )
            payload["chat_template_kwargs"] = {"enable_thinking": enable_thinking}

        # Authoritative Provider-Boundary Prompt Capture Hook (immediately prior to dispatch)
        capture_cb = kwargs.get("capture_callback")
        post_capture_cb = kwargs.get("post_capture_callback")
        capture_meta = None
        if capture_cb:
            try:
                capture_meta = await capture_cb(
                    payload=payload,
                    compiled_system_prompt=system_instruction,
                    user_message=user_content,
                    generation_settings={
                        "model": self.model_name,
                        "max_tokens": effective_max_tokens,
                        "temperature": self.temperature,
                        "timeout_seconds": self.timeout_seconds,
                        "endpoint": self.base_url,
                    },
                )
            except Exception:
                pass

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                res = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                latency_ms = int((time.time() - start_time) * 1000)

                if res.status_code != 200:
                    err_msg = f"Inference HTTP error {res.status_code}: {res.text[:200]}"
                    if post_capture_cb and capture_meta:
                        try:
                            await post_capture_cb(
                                capture_meta=capture_meta,
                                status="FAILED",
                                error_message=err_msg,
                                latency_ms=latency_ms,
                            )
                        except Exception:
                            pass
                    return StructuredModelVerdict(
                        incident_id=incident_id,
                        rule_id=rule_id,
                        verdict="REQUIRES_ATTENTION",
                        confidence=0.0,
                        reason=err_msg,
                        supporting_evidence=[],
                        missing_evidence=["Complete API response"],
                        analyst_questions=["Check Server 2 inference engine status"],
                        latency_ms=latency_ms,
                        model_identifier=self.model_name,
                        prompt_version_number=prompt_version_number,
                        validation_status="HTTP_ERROR",
                        is_simulated=False,
                        finish_reason=None,
                        requested_max_tokens=effective_max_tokens,
                        prompt_capture_id=getattr(capture_meta, "id", None) if capture_meta else None,
                        prompt_request_sha256=getattr(capture_meta, "request_sha256", None) if capture_meta else None,
                        prompt_integrity_status="UNVERIFIED",
                        outbound_payload=payload,
                    )

                data = res.json()
                choice0 = data["choices"][0]
                raw_reply = choice0["message"]["content"]
                finish_reason = str(choice0.get("finish_reason") or "").lower().strip()
                usage = data.get("usage", {})
                prompt_tokens = int(usage.get("prompt_tokens", 0))
                completion_tokens = int(usage.get("completion_tokens", 0))
                total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens))

                parsed, parse_err = robust_parse_model_verdict_json(raw_reply)

                if not parsed:
                    err_schema = f"Model output format error: {parse_err}. Partial reply: {raw_reply[:200]}"
                    if post_capture_cb and capture_meta:
                        try:
                            await post_capture_cb(
                                capture_meta=capture_meta,
                                status="FAILED",
                                error_message=err_schema,
                                latency_ms=latency_ms,
                            )
                        except Exception:
                            pass
                    return StructuredModelVerdict(
                        incident_id=incident_id,
                        rule_id=rule_id,
                        verdict="REQUIRES_ATTENTION",
                        confidence=0.0,
                        reason=err_schema,
                        supporting_evidence=[],
                        missing_evidence=["Valid schema output"],
                        analyst_questions=["Review raw LLM output format"],
                        latency_ms=latency_ms,
                        model_identifier=self.model_name,
                        prompt_version_number=prompt_version_number,
                        validation_status="INVALID_SCHEMA",
                        is_simulated=False,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        finish_reason=finish_reason,
                        requested_max_tokens=effective_max_tokens,
                        prompt_capture_id=getattr(capture_meta, "id", None) if capture_meta else None,
                        prompt_request_sha256=getattr(capture_meta, "request_sha256", None) if capture_meta else None,
                        prompt_integrity_status="UNVERIFIED",
                        raw_model_response=raw_reply,
                        outbound_payload=payload,
                    )

                # Defensive schema validation
                is_valid, status, err_msg = self.validate_verdict_schema(parsed)
                if not is_valid:
                    schema_fail = f"Model output schema validation failed: {err_msg}"
                    if post_capture_cb and capture_meta:
                        try:
                            await post_capture_cb(
                                capture_meta=capture_meta,
                                status="FAILED",
                                error_message=schema_fail,
                                latency_ms=latency_ms,
                            )
                        except Exception:
                            pass
                    return StructuredModelVerdict(
                        incident_id=incident_id,
                        rule_id=rule_id,
                        verdict="REQUIRES_ATTENTION",
                        confidence=0.0,
                        reason=schema_fail,
                        supporting_evidence=[],
                        missing_evidence=["Valid schema output"],
                        analyst_questions=[],
                        latency_ms=latency_ms,
                        model_identifier=self.model_name,
                        prompt_version_number=prompt_version_number,
                        validation_status=status,
                        is_simulated=False,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        finish_reason=finish_reason,
                        requested_max_tokens=effective_max_tokens,
                        prompt_capture_id=getattr(capture_meta, "id", None) if capture_meta else None,
                        prompt_request_sha256=getattr(capture_meta, "request_sha256", None) if capture_meta else None,
                        prompt_integrity_status="UNVERIFIED",
                        raw_model_response=raw_reply,
                        outbound_payload=payload,
                    )

                raw_claims = parsed.get("supporting_claims") or parsed.get("claims") or []
                supporting_claims = [c for c in raw_claims if isinstance(c, dict)] if isinstance(raw_claims, list) else []
                raw_contra = parsed.get("contradictory_evidence") or []
                contradictory_ev = [str(c) for c in raw_contra] if isinstance(raw_contra, list) else []

                raw_verdict_str = str(parsed.get("verdict", "REQUIRES_ATTENTION")).upper().strip()
                if raw_verdict_str in ("INSUFFICIENT_EVIDENCE", "ABSTAIN", "UNKNOWN", "UNCERTAIN"):
                    raw_verdict_str = "REQUIRES_ATTENTION"
                is_recovered = bool(parsed.get("_schema_recovery_applied", False))

                # Reject mismatched incident_id returned by LLM (prevents cross-incident hallucination)
                returned_inc_id = str(parsed.get("incident_id") or "").strip()
                if returned_inc_id and str(incident_id).strip() and returned_inc_id != str(incident_id).strip():
                    mismatch_msg = f"Model returned mismatched incident_id '{returned_inc_id}' (expected '{incident_id}'); verdict rejected and routed to manual review."
                    if post_capture_cb and capture_meta:
                        try:
                            await post_capture_cb(capture_meta=capture_meta, status="FAILED", error_message=mismatch_msg, latency_ms=latency_ms)
                        except Exception:
                            pass
                    return StructuredModelVerdict(
                        incident_id=incident_id,
                        rule_id=rule_id,
                        verdict="REQUIRES_ATTENTION",
                        confidence=0.0,
                        reason=mismatch_msg,
                        supporting_evidence=[],
                        supporting_claims=[],
                        contradictory_evidence=[f"incident_id mismatch: returned={returned_inc_id}, expected={incident_id}"],
                        missing_evidence=["Valid incident_id match in model response"],
                        analyst_questions=["Re-run inference or review incident manually"],
                        recommended_action="Route incident to manual SOC analyst review due to incident_id reference mismatch.",
                        latency_ms=latency_ms,
                        model_identifier=self.model_name,
                        prompt_version_number=prompt_version_number,
                        validation_status="INVALID_INCIDENT_REF",
                        is_simulated=False,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        finish_reason=finish_reason,
                        requested_max_tokens=effective_max_tokens,
                        prompt_capture_id=getattr(capture_meta, "id", None) if capture_meta else None,
                        prompt_request_sha256=getattr(capture_meta, "request_sha256", None) if capture_meta else None,
                        prompt_integrity_status="UNVERIFIED",
                        raw_model_response=raw_reply,
                        outbound_payload=payload,
                    )

                # Reject mismatched rule_id / rule reference returned by LLM
                returned_rule_ref = str(parsed.get("rule_id") or parsed.get("rule_reference") or "").strip()
                allowed_rule_refs = {
                    str(v).strip()
                    for v in (
                        rule_id,
                        rule_spec.get("id"),
                        rule_spec.get("rule_id"),
                        rule_spec.get("event_type"),
                        rule_spec.get("name"),
                    )
                    if v and str(v).strip()
                }
                if returned_rule_ref and allowed_rule_refs and returned_rule_ref not in allowed_rule_refs:
                    rule_err_msg = f"Model returned mismatched rule reference '{returned_rule_ref}' (expected one of {sorted(allowed_rule_refs)}); verdict rejected and routed to manual review."
                    if post_capture_cb and capture_meta:
                        try:
                            await post_capture_cb(capture_meta=capture_meta, status="FAILED", error_message=rule_err_msg, latency_ms=latency_ms)
                        except Exception:
                            pass
                    return StructuredModelVerdict(
                        incident_id=incident_id,
                        rule_id=rule_id,
                        verdict="REQUIRES_ATTENTION",
                        confidence=0.0,
                        reason=rule_err_msg,
                        supporting_evidence=[],
                        supporting_claims=[],
                        contradictory_evidence=[f"rule_id mismatch: returned={returned_rule_ref}"],
                        missing_evidence=["Valid rule reference match in model response"],
                        analyst_questions=["Verify rule mapping and review incident manually"],
                        recommended_action="Route incident to manual SOC analyst review due to rule reference mismatch.",
                        latency_ms=latency_ms,
                        model_identifier=self.model_name,
                        prompt_version_number=prompt_version_number,
                        validation_status="INVALID_RULE_REF",
                        is_simulated=False,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        finish_reason=finish_reason,
                        requested_max_tokens=effective_max_tokens,
                        prompt_capture_id=getattr(capture_meta, "id", None) if capture_meta else None,
                        prompt_request_sha256=getattr(capture_meta, "request_sha256", None) if capture_meta else None,
                        prompt_integrity_status="UNVERIFIED",
                        raw_model_response=raw_reply,
                        outbound_payload=payload,
                    )

                # V8.2: Deterministic Confidence Normalization & Ambiguous Scale Rejection
                raw_conf_val = parsed.get("confidence")
                raw_conf_scale = parsed.get("confidence_scale")
                norm_conf = ConfidenceNormalizer.normalize(raw_conf_val, raw_conf_scale)
                if not norm_conf.is_valid:
                    conf_err_msg = f"Model confidence validation failed ({norm_conf.interpretation}): {norm_conf.error_message}"
                    if post_capture_cb and capture_meta:
                        try:
                            await post_capture_cb(capture_meta=capture_meta, status="FAILED", error_message=conf_err_msg, latency_ms=latency_ms)
                        except Exception:
                            pass
                    return StructuredModelVerdict(
                        incident_id=incident_id,
                        rule_id=rule_id,
                        verdict="REQUIRES_ATTENTION",
                        confidence=0.0,
                        confidence_scale=norm_conf.raw_scale,
                        confidence_interpretation=norm_conf.interpretation,
                        normalized_confidence_percent=None,
                        reason=conf_err_msg,
                        supporting_evidence=[],
                        supporting_claims=[],
                        contradictory_evidence=[],
                        missing_evidence=["Valid confidence score (0-100)"],
                        analyst_questions=["Review raw LLM output for invalid or ambiguous confidence value"],
                        recommended_action="Route incident to manual SOC analyst review due to invalid confidence score.",
                        latency_ms=latency_ms,
                        model_identifier=self.model_name,
                        prompt_version_number=prompt_version_number,
                        validation_status="INVALID_CONFIDENCE",
                        is_simulated=False,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        finish_reason=finish_reason,
                        requested_max_tokens=effective_max_tokens,
                        prompt_capture_id=getattr(capture_meta, "id", None) if capture_meta else None,
                        prompt_request_sha256=getattr(capture_meta, "request_sha256", None) if capture_meta else None,
                        prompt_integrity_status="UNVERIFIED",
                        raw_model_response=raw_reply,
                        outbound_payload=payload,
                    )

                is_truncated = (finish_reason == "length") or bool(parsed.get("_truncated_output", False))
                # If output was truncated (finish_reason='length' or required JSON truncation repair),
                # NEVER silently accept a decisive TP/FP verdict or mark the response VALID.
                if is_truncated:
                    trunc_note = (
                        f"TRUNCATED_OUTPUT (finish_reason={finish_reason or 'repaired'}, "
                        f"completion_tokens={completion_tokens}/{effective_max_tokens}): "
                        "Incomplete model response routed safely to manual analyst review."
                    )
                    base_reason = str(parsed.get("reason") or "").strip()
                    combined_reason = f"{trunc_note} {base_reason}".strip() if base_reason else trunc_note
                    if post_capture_cb and capture_meta:
                        try:
                            await post_capture_cb(
                                capture_meta=capture_meta,
                                status="COMPLETED",
                                response_raw=raw_reply,
                                response_verdict="REQUIRES_ATTENTION",
                                response_confidence=0.0,
                                prompt_tokens=prompt_tokens,
                                completion_tokens=completion_tokens,
                                total_tokens=total_tokens,
                                latency_ms=latency_ms,
                                error_message=trunc_note,
                            )
                        except Exception:
                            pass
                    return StructuredModelVerdict(
                        incident_id=incident_id,
                        rule_id=rule_id,
                        verdict="REQUIRES_ATTENTION",
                        confidence=0.0,
                        reason=combined_reason,
                        supporting_evidence=parsed.get("supporting_evidence", []) if isinstance(parsed.get("supporting_evidence"), list) else [],
                        supporting_claims=supporting_claims,
                        contradictory_evidence=contradictory_ev,
                        missing_evidence=list(dict.fromkeys(
                            (parsed.get("missing_evidence", []) if isinstance(parsed.get("missing_evidence"), list) else [])
                            + ["Complete untruncated LLM JSON response"]
                        )),
                        analyst_questions=parsed.get("analyst_questions", []) if isinstance(parsed.get("analyst_questions"), list) else [],
                        recommended_action="Route incident to manual SOC analyst review due to truncated LLM output.",
                        latency_ms=latency_ms,
                        model_identifier=self.model_name,
                        prompt_version_number=prompt_version_number,
                        validation_status="TRUNCATED_OUTPUT",
                        is_simulated=False,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        finish_reason=finish_reason,
                        requested_max_tokens=effective_max_tokens,
                        prompt_capture_id=getattr(capture_meta, "id", None) if capture_meta else None,
                        prompt_request_sha256=getattr(capture_meta, "request_sha256", None) if capture_meta else None,
                        prompt_integrity_status="VERIFIED" if capture_meta else "UNVERIFIED",
                        raw_model_response=raw_reply,
                        outbound_payload=payload,
                    )

                # If output required regex recovery from malformed non-JSON response,
                # decisive TP/FP classifications must NEVER be accepted as valid.
                if is_recovered and raw_verdict_str in ("TRUE_POSITIVE", "FALSE_POSITIVE"):
                    rec_err_msg = f"Model output required regex recovery from malformed non-JSON response; decisive {raw_verdict_str} rejected: {parsed.get('reason', '')}"
                    if post_capture_cb and capture_meta:
                        try:
                            await post_capture_cb(capture_meta=capture_meta, status="FAILED", error_message=rec_err_msg, latency_ms=latency_ms)
                        except Exception:
                            pass
                    return StructuredModelVerdict(
                        incident_id=incident_id,
                        rule_id=rule_id,
                        verdict="REQUIRES_ATTENTION",
                        confidence=0.0,
                        reason=rec_err_msg,
                        supporting_evidence=[],
                        supporting_claims=[],
                        contradictory_evidence=[],
                        missing_evidence=["Valid structured JSON response"],
                        analyst_questions=["Review raw LLM output for syntax defects"],
                        recommended_action="Route incident to manual SOC analyst review due to malformed LLM response.",
                        latency_ms=latency_ms,
                        model_identifier=self.model_name,
                        prompt_version_number=prompt_version_number,
                        validation_status="INVALID_SCHEMA",
                        is_simulated=False,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        finish_reason=finish_reason,
                        requested_max_tokens=effective_max_tokens,
                        prompt_capture_id=getattr(capture_meta, "id", None) if capture_meta else None,
                        prompt_request_sha256=getattr(capture_meta, "request_sha256", None) if capture_meta else None,
                        prompt_integrity_status="UNVERIFIED",
                        raw_model_response=raw_reply,
                        outbound_payload=payload,
                    )

                val_status = "INVALID_SCHEMA" if is_recovered else "VALID"
                resolved_confidence = norm_conf.normalized_percent if norm_conf.is_valid and norm_conf.normalized_percent is not None else 0.0
                rec_action = parsed.get("recommended_action")
                if not rec_action:
                    if raw_verdict_str == "TRUE_POSITIVE":
                        rec_action = "Escalate to SOC L2 analyst for investigation and containment verification; keep incident OPEN."
                    elif raw_verdict_str == "FALSE_POSITIVE":
                        rec_action = "Verify supporting benign/authorization evidence; eligible for closure only under approved governance."
                    else:
                        rec_action = "Route to manual SOC analyst investigation to collect missing telemetry."

                if post_capture_cb and capture_meta:
                    try:
                        await post_capture_cb(
                            capture_meta=capture_meta,
                            status="COMPLETED",
                            response_raw=raw_reply,
                            response_verdict=raw_verdict_str,
                            response_confidence=resolved_confidence,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            total_tokens=total_tokens,
                            latency_ms=latency_ms,
                        )
                    except Exception:
                        pass

                return StructuredModelVerdict(
                    incident_id=incident_id,
                    rule_id=rule_id,
                    verdict=raw_verdict_str,
                    confidence=resolved_confidence,
                    confidence_scale=norm_conf.raw_scale,
                    confidence_interpretation=norm_conf.interpretation,
                    normalized_confidence_percent=norm_conf.normalized_percent,
                    reason=str(parsed.get("reason", "")),
                    supporting_evidence=parsed.get("supporting_evidence", []) if isinstance(parsed.get("supporting_evidence"), list) else [],
                    supporting_claims=supporting_claims,
                    contradictory_evidence=contradictory_ev,
                    missing_evidence=parsed.get("missing_evidence", []) if isinstance(parsed.get("missing_evidence"), list) else [],
                    analyst_questions=parsed.get("analyst_questions", []) if isinstance(parsed.get("analyst_questions"), list) else [],
                    recommended_action=str(rec_action),
                    latency_ms=latency_ms,
                    model_identifier=self.model_name,
                    prompt_version_number=prompt_version_number,
                    validation_status=val_status,
                    is_simulated=False,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    finish_reason=finish_reason,
                    requested_max_tokens=effective_max_tokens,
                    prompt_capture_id=getattr(capture_meta, "id", None) if capture_meta else None,
                    prompt_request_sha256=getattr(capture_meta, "request_sha256", None) if capture_meta else None,
                    prompt_integrity_status="VERIFIED" if val_status == "VALID" else "UNVERIFIED",
                    raw_model_response=raw_reply,
                    outbound_payload=payload,
                )

        except httpx.TimeoutException as e:
            latency_ms = int((time.time() - start_time) * 1000)
            timeout_msg = f"Inference request timed out after {latency_ms/1000:.1f}s on Server 2"
            if post_capture_cb and capture_meta:
                try:
                    await post_capture_cb(
                        capture_meta=capture_meta,
                        status="FAILED",
                        error_message=timeout_msg,
                        latency_ms=latency_ms,
                    )
                except Exception:
                    pass
            return StructuredModelVerdict(
                incident_id=incident_id,
                rule_id=rule_id,
                verdict="REQUIRES_ATTENTION",
                confidence=0.0,
                reason=timeout_msg,
                supporting_evidence=[],
                missing_evidence=["Inference response within timeout deadline"],
                analyst_questions=["Check Server 2 GPU load or increase timeout"],
                latency_ms=latency_ms,
                model_identifier=self.model_name,
                prompt_version_number=prompt_version_number,
                validation_status="CONNECTION_ERROR",
                is_simulated=False,
                prompt_capture_id=getattr(capture_meta, "id", None) if capture_meta else None,
                prompt_request_sha256=getattr(capture_meta, "request_sha256", None) if capture_meta else None,
                prompt_integrity_status="UNVERIFIED",
                outbound_payload=payload,
            )
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            exc_msg = f"Inference execution exception: {type(e).__name__} ({str(e) or 'connection failed'})"
            if post_capture_cb and capture_meta:
                try:
                    await post_capture_cb(
                        capture_meta=capture_meta,
                        status="FAILED",
                        error_message=exc_msg,
                        latency_ms=latency_ms,
                    )
                except Exception:
                    pass
            return StructuredModelVerdict(
                incident_id=incident_id,
                rule_id=rule_id,
                verdict="REQUIRES_ATTENTION",
                confidence=0.0,
                reason=exc_msg,
                supporting_evidence=[],
                missing_evidence=["Successful API response"],
                analyst_questions=["Verify local LLM connectivity on Server 2"],
                latency_ms=latency_ms,
                model_identifier=self.model_name,
                prompt_version_number=prompt_version_number,
                validation_status="CONNECTION_ERROR",
                is_simulated=False,
                prompt_capture_id=getattr(capture_meta, "id", None) if capture_meta else None,
                prompt_request_sha256=getattr(capture_meta, "request_sha256", None) if capture_meta else None,
                prompt_integrity_status="UNVERIFIED",
                outbound_payload=payload,
            )

