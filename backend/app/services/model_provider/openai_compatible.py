import time
import json
from typing import List, Dict, Any, Optional
import httpx

from app.services.model_provider.base import BaseModelProvider, ProviderHealthResponse, StructuredModelVerdict


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
        timeout_seconds: float = 30.0,
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or "EMPTY"
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens
        self.temperature = temperature

    async def get_health(self) -> ProviderHealthResponse:
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(
                    f"{self.base_url}/models",
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
                else:
                    return ProviderHealthResponse(
                        status="DEGRADED",
                        provider_name="OpenAICompatibleProvider",
                        is_simulated=False,
                        latency_ms=latency,
                        message=f"Endpoint returned HTTP {res.status_code}",
                        details={"status_code": res.status_code},
                    )
        except Exception as e:
            return ProviderHealthResponse(
                status="OFFLINE",
                provider_name="OpenAICompatibleProvider",
                is_simulated=False,
                latency_ms=None,
                message=f"Could not connect to inference server at {self.base_url}: {str(e)}",
                details={"error": str(e)},
            )

    async def list_models(self) -> List[str]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
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

        system_instruction = (
            f"{prompt_text}\n\n"
            "CRITICAL: Output must be a strictly valid JSON object matching this schema:\n"
            "{\n"
            '  "verdict": "TRUE_POSITIVE" | "FALSE_POSITIVE" | "REQUIRES_ATTENTION",\n'
            '  "confidence": <float 0-100>,\n'
            '  "reason": "<string>",\n'
            '  "supporting_evidence": ["<string>"],\n'
            '  "missing_evidence": ["<string>"],\n'
            '  "analyst_questions": ["<string>"]\n'
            "}"
        )

        user_content = json.dumps({
            "incident": incident_payload,
            "rule": rule_spec,
        }, indent=2)

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
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
                        validation_status="INVALID_SCHEMA",
                        is_simulated=False,
                    )

                data = res.json()
                raw_reply = data["choices"][0]["message"]["content"]
                parsed = json.loads(raw_reply)

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
                    )

                return StructuredModelVerdict(
                    incident_id=incident_id,
                    rule_id=rule_id,
                    verdict=parsed["verdict"].upper().strip(),
                    confidence=float(parsed.get("confidence", 90.0)),
                    reason=str(parsed.get("reason", "")),
                    supporting_evidence=parsed.get("supporting_evidence", []),
                    missing_evidence=parsed.get("missing_evidence", []),
                    analyst_questions=parsed.get("analyst_questions", []),
                    latency_ms=latency_ms,
                    model_identifier=self.model_name,
                    prompt_version_number=prompt_version_number,
                    validation_status="VALID",
                    is_simulated=False,
                )

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return StructuredModelVerdict(
                incident_id=incident_id,
                rule_id=rule_id,
                verdict="REQUIRES_ATTENTION",
                confidence=0.0,
                reason=f"Inference execution exception: {str(e)}",
                supporting_evidence=[],
                missing_evidence=["Successful API response"],
                analyst_questions=["Verify local LLM connectivity on Server 2"],
                latency_ms=latency_ms,
                model_identifier=self.model_name,
                prompt_version_number=prompt_version_number,
                validation_status="INVALID_SCHEMA",
                is_simulated=False,
            )

