import time
import json
import re
from typing import List, Dict, Any, Optional, Tuple
import httpx

from app.services.model_provider.base import BaseModelProvider, ProviderHealthResponse, StructuredModelVerdict


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
    repaired = _repair_truncated_json(sanitized)
    if repaired:
        try:
            return json.loads(repaired, strict=False), None
        except json.JSONDecodeError:
            pass

    # 6. Fallback regex extraction of fields
    fallback_dict, fallback_err = _regex_fallback_extract(text)
    if fallback_dict:
        return fallback_dict, None

    return None, f"Failed to parse JSON: {decode_err}"


def _repair_truncated_json(text: str) -> Optional[str]:
    """Attempts to complete truncated strings, arrays, and dictionaries."""
    in_string = False
    escaped = False
    open_brackets = 0
    open_braces = 0

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
                    open_brackets += 1
                elif ch == ']':
                    open_brackets = max(0, open_brackets - 1)
                elif ch == '{':
                    open_braces += 1
                elif ch == '}':
                    open_braces = max(0, open_braces - 1)
            clean_chars.append(ch)
            escaped = False

    repaired = "".join(clean_chars)

    if in_string:
        repaired += '"'

    repaired = re.sub(r',\s*$', '', repaired)
    repaired = re.sub(r':\s*$', ': ""', repaired)

    if open_brackets > 0:
        repaired += ']' * open_brackets
    if open_braces > 0:
        repaired += '}' * open_braces

    return repaired


def _regex_fallback_extract(text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Heuristic extraction of key fields when JSON cannot be parsed syntactically."""
    verdict_match = re.search(r'"verdict"\s*:\s*"?(TRUE_POSITIVE|FALSE_POSITIVE|REQUIRES_ATTENTION)"?', text, re.IGNORECASE)
    if not verdict_match:
        return None, "No verdict found in model output"

    verdict = verdict_match.group(1).upper()

    conf_match = re.search(r'"confidence"\s*:\s*([0-9]+(?:\.[0-9]+)?)', text)
    confidence = float(conf_match.group(1)) if conf_match else 75.0

    reason_match = re.search(r'"reason"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)', text)
    reason = reason_match.group(1) if reason_match else "Extracted from model response"

    supporting = re.findall(r'"supporting_evidence"\s*:\s*\[(.*?)\]', text, re.DOTALL)
    evidence_list = []
    if supporting:
        evidence_list = [item.strip(' ",\'\n\r\t') for item in re.findall(r'"([^"]+)"', supporting[0])]

    return {
        "verdict": verdict,
        "confidence": confidence,
        "reason": reason,
        "supporting_evidence": evidence_list,
        "missing_evidence": [],
        "analyst_questions": [],
    }, None


class OpenAICompatibleProvider(BaseModelProvider):
    """
    Client for Server 2 local LLM inference engines (vLLM, Ollama, TGI, SGLang)
    serving an OpenAI-compatible API endpoint (e.g., http://10.x.x.x:8000/v1).
    STRICT RESTRICTION: Not called in production during Phase 3.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8001/v1",
        api_key: Optional[str] = None,
        model_name: str = "qwen3-8b-instruct",
        timeout_seconds: float = 60.0,
        max_tokens: int = 512,
        temperature: float = 0.1,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or "EMPTY"
        self.model_name = model_name
        self.timeout_seconds = max(0.1, float(timeout_seconds))
        self.max_tokens = max(64, min(int(max_tokens), 4096)) if max_tokens else 512
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

    async def analyze_incident(
        self,
        incident_payload: Dict[str, Any],
        rule_spec: Dict[str, Any],
        prompt_text: str,
        prompt_version_number: int = 1,
    ) -> StructuredModelVerdict:
        start_time = time.time()
        incident_id = str(incident_payload.get("incident_id", ""))
        rule_id = str(rule_spec.get("id", rule_spec.get("rule_id", "")))

        if "SECTION 11:" in prompt_text:
            system_instruction = (
                f"{prompt_text}\n\n"
                "Note: Populate supporting_claims[].evidence_ids strictly from incident.canonical_evidence[].evidence_id."
            )
        else:
            system_instruction = (
                f"{prompt_text}\n\n"
                "CRITICAL: Output must be a strictly valid JSON object matching this schema:\n"
                "{\n"
                '  "verdict": "TRUE_POSITIVE" | "FALSE_POSITIVE" | "REQUIRES_ATTENTION",\n'
                '  "confidence": <float 0-100>,\n'
                '  "reason": "<string>",\n'
                '  "supporting_claims": [\n'
                '    {\n'
                '      "claim_type": "PROCESS_EXECUTION" | "NETWORK_CONNECTION" | "FILE_HASH" | "USER_CONTEXT" | "OBSERVED_FACT",\n'
                '      "field": "<canonical source_field>",\n'
                '      "asserted_value": "<exact observed value>",\n'
                '      "claim_text": "<concise grounded observation>",\n'
                '      "evidence_ids": ["<canonical evidence_id from incident.canonical_evidence>"]\n'
                "    }\n"
                "  ],\n"
                '  "supporting_evidence": ["<string>"],\n'
                '  "contradictory_evidence": ["<string>"],\n'
                '  "missing_evidence": ["<string>"],\n'
                '  "analyst_questions": ["<string>"]\n'
                "}"
            )

        # Construct compact valid JSON prompt for local LLM (avoids indent bloat inside finite context window)
        user_content = json.dumps({
            "incident": incident_payload,
            "rule": rule_spec,
        }, separators=(",", ":"))

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

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
                    return StructuredModelVerdict(
                        incident_id=incident_id,
                        rule_id=rule_id,
                        verdict="REQUIRES_ATTENTION",
                        confidence=0.0,
                        reason=f"Inference HTTP error {res.status_code}: {res.text[:200]}",
                        supporting_evidence=[],
                        missing_evidence=["Complete API response"],
                        analyst_questions=["Check Server 2 inference engine status"],
                        latency_ms=latency_ms,
                        model_identifier=self.model_name,
                        prompt_version_number=prompt_version_number,
                        validation_status="HTTP_ERROR",
                        is_simulated=False,
                    )

                data = res.json()
                raw_reply = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                prompt_tokens = int(usage.get("prompt_tokens", 0))
                completion_tokens = int(usage.get("completion_tokens", 0))
                total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens))

                parsed, parse_err = robust_parse_model_verdict_json(raw_reply)

                if not parsed:
                    return StructuredModelVerdict(
                        incident_id=incident_id,
                        rule_id=rule_id,
                        verdict="REQUIRES_ATTENTION",
                        confidence=0.0,
                        reason=f"Model output format error: {parse_err}. Partial reply: {raw_reply[:200]}",
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
                    )

                # Defensive schema validation
                is_valid, status, err_msg = self.validate_verdict_schema(parsed)
                if not is_valid:
                    return StructuredModelVerdict(
                        incident_id=incident_id,
                        rule_id=rule_id,
                        verdict="REQUIRES_ATTENTION",
                        confidence=0.0,
                        reason=f"Model output schema validation failed: {err_msg}",
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
                    )

                raw_claims = parsed.get("supporting_claims") or parsed.get("claims") or []
                supporting_claims = [c for c in raw_claims if isinstance(c, dict)] if isinstance(raw_claims, list) else []
                raw_contra = parsed.get("contradictory_evidence") or []
                contradictory_ev = [str(c) for c in raw_contra] if isinstance(raw_contra, list) else []

                return StructuredModelVerdict(
                    incident_id=incident_id,
                    rule_id=rule_id,
                    verdict=parsed["verdict"].upper().strip(),
                    confidence=float(parsed.get("confidence", 90.0)),
                    reason=str(parsed.get("reason", "")),
                    supporting_evidence=parsed.get("supporting_evidence", []) if isinstance(parsed.get("supporting_evidence"), list) else [],
                    supporting_claims=supporting_claims,
                    contradictory_evidence=contradictory_ev,
                    missing_evidence=parsed.get("missing_evidence", []) if isinstance(parsed.get("missing_evidence"), list) else [],
                    analyst_questions=parsed.get("analyst_questions", []) if isinstance(parsed.get("analyst_questions"), list) else [],
                    latency_ms=latency_ms,
                    model_identifier=self.model_name,
                    prompt_version_number=prompt_version_number,
                    validation_status="VALID",
                    is_simulated=False,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                )

        except httpx.TimeoutException as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return StructuredModelVerdict(
                incident_id=incident_id,
                rule_id=rule_id,
                verdict="REQUIRES_ATTENTION",
                confidence=0.0,
                reason=f"Inference request timed out after {latency_ms/1000:.1f}s on Server 2",
                supporting_evidence=[],
                missing_evidence=["Inference response within timeout deadline"],
                analyst_questions=["Check Server 2 GPU load or increase timeout"],
                latency_ms=latency_ms,
                model_identifier=self.model_name,
                prompt_version_number=prompt_version_number,
                validation_status="CONNECTION_ERROR",
                is_simulated=False,
            )
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return StructuredModelVerdict(
                incident_id=incident_id,
                rule_id=rule_id,
                verdict="REQUIRES_ATTENTION",
                confidence=0.0,
                reason=f"Inference execution exception: {type(e).__name__} ({str(e) or 'connection failed'})",
                supporting_evidence=[],
                missing_evidence=["Successful API response"],
                analyst_questions=["Verify local LLM connectivity on Server 2"],
                latency_ms=latency_ms,
                model_identifier=self.model_name,
                prompt_version_number=prompt_version_number,
                validation_status="CONNECTION_ERROR",
                is_simulated=False,
            )

