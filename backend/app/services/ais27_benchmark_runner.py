"""
AIS 2.7 — Isolated Live GPU Benchmark Runner (Strictly Read-Only on Incidents & Ground Truth)

Executes:
1. Live Server 2 vLLM runtime verification (/v1/models, /health, /version)
2. Single non-benchmark connectivity smoke test
3. Strictly label-isolated Three-Mode Evaluation per frozen cohort incident:
   - Mode A: Neutral LLM baseline (NEUTRAL_SOC_BASELINE_V1 + JSON schema)
   - Mode B: Server 1 Approved Policy (active PromptVersion in PostgreSQL)
   - Mode C: Deterministic Validator (0 extra GPU calls)

Invariants enforced:
- NEVER queries AnalystVerdictReview, HistoricalGroundTruth, LearningRecord, or Incident.ai_verdict.
- NEVER writes to Incident, Investigation, LearningRecord, RulePrompt, or PromptVersion.
- NEVER enables RAG (rag_block="").
- NEVER enables mock fallback.
- Preserves Layer 1 (raw vLLM HTTP envelope + raw text), Layer 2 (parsed model prediction),
  and Layer 3 (deterministic Mode C validator result) separately.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.analyst_feedback import BenchmarkCohort, BenchmarkCohortItem
from app.models.incident import Incident
from app.models.prompt import PromptVersion, RulePrompt
from app.models.rule import Rule
from app.schemas.compiled_policy import CompilationExecutionMode
from app.services.confidence_normalizer import ConfidenceNormalizer
from app.services.empirical_benchmark_harness import EmpiricalBenchmarkHarness, IncidentAdapter
from app.services.evidence_normalization_service import EvidenceNormalizationService
from app.services.evidence_preflight_validator import EvidencePreflightValidator
from app.services.evidence_intelligence_service import EvidenceIntelligenceEngine, RuleDefinitionBuilder
from app.services.ais28_policy_candidates import get_experimental_candidate_policy
from app.services.historical_ground_truth_validator import HistoricalGroundTruthValidator
from app.services.independent_verdict_validator import IndependentVerdictValidator
from app.services.model_claim_extractor import ModelClaimExtractor
from app.services.model_payload_allowlist import build_model_facing_payload
from app.services.model_provider.openai_compatible import (
    OpenAICompatibleProvider,
    robust_parse_model_verdict_json,
)
from app.services.policy_compiler_service import PolicyCompilerService
from app.services.token_budget_service import TokenBudgetService
from app.services.tokenizer_service import ModelTokenizerService
from app.services.verdict_trustworthiness_engine import VerdictTrustworthinessEngine
from app.utils.datetime_utils import utc_now

_MODE_A_SCHEMA_SUFFIX = (
    "\n\nCRITICAL: Output must be a strictly valid JSON object matching this schema:\n"
    "{\n"
    '  "verdict": "TRUE_POSITIVE" | "FALSE_POSITIVE" | "REQUIRES_ATTENTION",\n'
    '  "confidence": <float 0-100>,\n'
    '  "reason": "<concise analytical summary under 120 words>",\n'
    '  "supporting_claims": [\n'
    "    {\n"
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
    "IMPORTANT: Output ONLY the compact JSON object. Keep 'reason' strictly under 120 words. "
    "Limit 'supporting_claims' to at most 3 factual items. Do NOT echo raw event logs or prompt text."
)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _redact_url(url: str) -> str:
    p = urlparse(url or "")
    if not p.scheme or not p.hostname:
        return "<unconfigured>"
    return f"{p.scheme}://{p.hostname}:{p.port or (443 if p.scheme == 'https' else 80)}{p.path}"


class AIS27BenchmarkRunner:
    """Isolated live GPU benchmark executor for AIS 2.7."""

    @classmethod
    async def verify_gpu_runtime(cls) -> Dict[str, Any]:
        """Probes Server 2 vLLM metadata endpoints (/v1/models, /health, /version) with zero generation."""
        base_url = str(getattr(settings, "LOCAL_LLM_BASE_URL", "") or "").rstrip("/")
        if not base_url:
            raise ValueError("LOCAL_LLM_BASE_URL is not configured.")
        root_url = base_url[:-3] if base_url.endswith("/v1") else base_url
        headers = {"Authorization": f"Bearer {settings.LOCAL_LLM_API_KEY}"}

        models_payload: Optional[Dict[str, Any]] = None
        models_status: Optional[int] = None
        health_status: Optional[int] = None
        version_payload: Optional[Any] = None
        errors: List[str] = []

        t0 = time.perf_counter()
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                r_mod = await client.get(f"{base_url}/models", headers=headers)
                models_status = r_mod.status_code
                if r_mod.status_code == 200:
                    models_payload = r_mod.json()
            except Exception as exc:
                errors.append(f"/v1/models error: {exc}")

            try:
                r_hp = await client.get(f"{root_url}/health", headers=headers)
                health_status = r_hp.status_code
            except Exception as exc:
                errors.append(f"/health error: {exc}")

            try:
                r_ver = await client.get(f"{root_url}/version", headers=headers)
                if r_ver.status_code == 200:
                    version_payload = r_ver.json()
            except Exception:
                pass

        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        return {
            "verified_at_utc": utc_now().isoformat(),
            "endpoint": _redact_url(base_url),
            "configured_model_name": settings.LOCAL_LLM_MODEL_NAME,
            "configured_context_budget": int(getattr(settings, "LOCAL_LLM_CONTEXT_BUDGET", 8192)),
            "configured_max_tokens": int(getattr(settings, "LOCAL_LLM_MAX_TOKENS", 768)),
            "models_http_status": models_status,
            "models_payload": models_payload,
            "health_http_status": health_status,
            "version_payload": version_payload,
            "probe_latency_ms": latency_ms,
            "errors": errors,
        }

    @classmethod
    async def verify_tokenize(cls, timeout_seconds: float = 10.0) -> Dict[str, Any]:
        """Verifies live Server 2 /tokenize endpoint across neutral, Mode B policy, Windows path, and near-limit prompts."""
        base_url = str(getattr(settings, "LOCAL_LLM_BASE_URL", "") or "").rstrip("/")
        model_name = str(getattr(settings, "LOCAL_LLM_MODEL_NAME", "Qwen/Qwen3-14B-AWQ"))
        api_key = str(getattr(settings, "LOCAL_LLM_API_KEY", "EMPTY") or "EMPTY")
        cs_cand = get_experimental_candidate_policy("PH_RULE_CS_SUSPICIOUS_ACTIVITY")
        mode_b_sys = (
            f"{cs_cand.common_prompt or ''}\n\n"
            f"{cs_cand.rule_specific_prompt or ''}\n\n"
            f"{cs_cand.tp_indicators or ''}\n\n"
            f"{cs_cand.fp_indicators or ''}\n\n"
            "Note: Populate supporting_claims[].cited_evidence_ids (or evidence_ids) strictly from incident.canonical_evidence[].evidence_id."
        )
        cases = {
            "small": ("You are a SOC analyst.", '{"incident_id":"SYNTH-1","action":"ping"}'),
            "medium": (
                EmpiricalBenchmarkHarness.NEUTRAL_SOC_BASELINE_V2 + _MODE_A_SCHEMA_SUFFIX,
                "<UNTRUSTED_INCIDENT_DATA>\n" + ("{\"event\":\"auth_check\",\"src\":\"192.0.2.10\"}," * 40) + "\n</UNTRUSTED_INCIDENT_DATA>",
            ),
            "mode_a_neutral": (
                EmpiricalBenchmarkHarness.NEUTRAL_SOC_BASELINE_V2 + _MODE_A_SCHEMA_SUFFIX,
                "<UNTRUSTED_INCIDENT_DATA>\n" + ("{\"source_field\":\"process.name\",\"observed_value\":\"tool.exe\"}," * 60) + "\n</UNTRUSTED_INCIDENT_DATA>",
            ),
            "mode_b_policy": (
                mode_b_sys,
                "<UNTRUSTED_INCIDENT_DATA>\n" + ("{\"source_field\":\"process.pid\",\"observed_value\":\"1234567890\"}," * 80) + "\n</UNTRUSTED_INCIDENT_DATA>",
            ),
            "escaped_windows_paths": (
                mode_b_sys,
                '<UNTRUSTED_INCIDENT_DATA>\n{"incident":{"canonical_evidence":[{"source_field":"process.command_line","observed_value":"\\"C:\\\\Program Files (x86)\\\\App\\\\svc.exe\\""},{"source_field":"process.file_path","observed_value":"\\\\Device\\\\HarddiskVolume3\\\\Program Files (x86)\\\\App\\\\svc.exe"}]}}\n</UNTRUSTED_INCIDENT_DATA>',
            ),
            "near_limit": (
                EmpiricalBenchmarkHarness.NEUTRAL_SOC_BASELINE_V2 + _MODE_A_SCHEMA_SUFFIX,
                "<UNTRUSTED_INCIDENT_DATA>\n" + ("{\"event\":\"telemetry_entry\",\"host\":\"SYNTH-HOST-01\",\"detail\":\"synthetic_padding_token_test\"}," * 220) + "\n</UNTRUSTED_INCIDENT_DATA>",
            ),
        }
        results: Dict[str, Any] = {}
        for label, (sys_p, user_p) in cases.items():
            results[label] = await ModelTokenizerService.count_wire_prompt_tokens_remote(
                base_url=base_url,
                api_key=api_key,
                model_name=model_name,
                system_prompt=sys_p,
                user_message=user_p,
                timeout_seconds=timeout_seconds,
                enable_thinking=False,
            )
        return {
            "verified_at_utc": utc_now().isoformat(),
            "endpoint": _redact_url(base_url),
            "model_name": model_name,
            "cases": results,
        }

    @classmethod
    async def run_smoke_test(cls, timeout_seconds: float = 90.0) -> Dict[str, Any]:
        """Executes exactly ONE small controlled non-benchmark smoke-test generation on Server 2."""
        base_url = str(getattr(settings, "LOCAL_LLM_BASE_URL", "") or "").rstrip("/")
        model_name = str(getattr(settings, "LOCAL_LLM_MODEL_NAME", "Qwen/Qwen3-14B-AWQ"))
        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a connectivity verification assistant. Reply ONLY with valid JSON.",
                },
                {
                    "role": "user",
                    "content": 'Return exact JSON: {"smoke_test":"OK","engine":"vllm"}',
                },
            ],
            "max_tokens": 64,
            "temperature": 0.0,
            "top_p": 1.0,
        }
        if "qwen3" in model_name.lower():
            payload["chat_template_kwargs"] = {"enable_thinking": False}
        req_body_str = json.dumps(payload, separators=(",", ":"))
        req_ts = utc_now().isoformat()
        t0 = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                res = await client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.LOCAL_LLM_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    content=req_body_str.encode("utf-8"),
                )
        except Exception as exc:
            resp_ts = utc_now().isoformat()
            latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            return {
                "ok": False,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "request_timestamp_utc": req_ts,
                "response_timestamp_utc": resp_ts,
                "endpoint": _redact_url(f"{base_url}/chat/completions"),
                "http_status": None,
                "latency_ms": latency_ms,
                "request_sha256": _sha256_text(req_body_str),
                "vllm_response_id": None,
                "model_returned": None,
                "finish_reason": None,
                "usage": {},
                "raw_response_text": "",
                "raw_response_sha256": _sha256_text(""),
                "raw_vllm_envelope": {},
            }

        resp_ts = utc_now().isoformat()
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        resp_json = res.json() if res.status_code == 200 else {"raw_text": res.text[:1000]}
        raw_reply = ""
        finish_reason = None
        usage = {}
        if res.status_code == 200 and isinstance(resp_json, dict):
            choices = resp_json.get("choices") or []
            if choices:
                raw_reply = str((choices[0].get("message") or {}).get("content") or "")
                finish_reason = choices[0].get("finish_reason")
            usage = resp_json.get("usage") or {}

        return {
            "ok": res.status_code == 200,
            "request_timestamp_utc": req_ts,
            "response_timestamp_utc": resp_ts,
            "endpoint": _redact_url(f"{base_url}/chat/completions"),
            "http_status": res.status_code,
            "latency_ms": latency_ms,
            "request_sha256": _sha256_text(req_body_str),
            "vllm_response_id": resp_json.get("id") if isinstance(resp_json, dict) else None,
            "model_returned": resp_json.get("model") if isinstance(resp_json, dict) else None,
            "finish_reason": finish_reason,
            "usage": usage,
            "raw_response_text": raw_reply,
            "raw_response_sha256": _sha256_text(raw_reply),
            "raw_vllm_envelope": resp_json,
        }

    @classmethod
    async def _resolve_approved_policy(
        cls, db: AsyncSession, rule_obj: Rule
    ) -> Tuple[Optional[RulePrompt], Optional[PromptVersion]]:
        rp = (
            await db.execute(select(RulePrompt).where(RulePrompt.rule_id == rule_obj.id))
        ).scalar_one_or_none()
        if not rp:
            return None, None
        pv: Optional[PromptVersion] = None
        if rp.active_version_id:
            pv = (
                await db.execute(
                    select(PromptVersion).where(
                        PromptVersion.id == rp.active_version_id,
                        PromptVersion.status == "APPROVED",
                    )
                )
            ).scalar_one_or_none()
        if not pv:
            pv = (
                await db.execute(
                    select(PromptVersion)
                    .where(
                        PromptVersion.prompt_id == rp.id,
                        PromptVersion.status == "APPROVED",
                    )
                    .order_by(PromptVersion.version_number.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
        return rp, pv

    @classmethod
    def _parse_raw_vllm_reply(
        cls,
        raw_reply: str,
        finish_reason: Optional[str],
        incident_id: str,
        rule_spec: Dict[str, Any],
        prompt_tokens: int,
        completion_tokens: int,
        requested_max_tokens: int,
    ) -> Dict[str, Any]:
        """Applies exact OpenAICompatibleProvider Layer-2 parsing without mutating Layer-1 raw output."""
        parsed, parse_err = robust_parse_model_verdict_json(raw_reply)
        if not parsed:
            return {
                "parse_success": False,
                "parse_error": parse_err,
                "schema_valid": False,
                "validation_status": "INVALID_SCHEMA",
                "parsed_verdict": None,
                "confidence": 0.0,
                "reason": f"Model output format error: {parse_err}",
                "supporting_claims": [],
                "supporting_evidence": [],
                "contradictory_evidence": [],
                "missing_evidence": [],
                "analyst_questions": [],
                "schema_recovery_applied": False,
                "truncated_output": finish_reason == "length",
                "confidence_scale": None,
            }

        is_valid, schema_status, schema_err = OpenAICompatibleProvider().validate_verdict_schema(parsed)
        if not is_valid:
            return {
                "parse_success": True,
                "parse_error": schema_err,
                "schema_valid": False,
                "validation_status": schema_status,
                "parsed_verdict": None,
                "confidence": 0.0,
                "reason": f"Model output schema validation failed: {schema_err}",
                "supporting_claims": [],
                "supporting_evidence": [],
                "contradictory_evidence": [],
                "missing_evidence": [],
                "analyst_questions": [],
                "schema_recovery_applied": bool(parsed.get("_schema_recovery_applied", False)),
                "truncated_output": bool(parsed.get("_truncated_output", False)) or (finish_reason == "length"),
                "confidence_scale": parsed.get("confidence_scale"),
            }

        raw_verdict_str = str(parsed.get("verdict", "REQUIRES_ATTENTION")).upper().strip()
        if raw_verdict_str in ("INSUFFICIENT_EVIDENCE", "ABSTAIN", "UNKNOWN", "UNCERTAIN"):
            raw_verdict_str = "REQUIRES_ATTENTION"

        returned_inc_id = str(parsed.get("incident_id") or "").strip()
        if returned_inc_id and str(incident_id).strip() and returned_inc_id != str(incident_id).strip():
            return {
                "parse_success": True,
                "parse_error": f"incident_id mismatch: returned={returned_inc_id}, expected={incident_id}",
                "schema_valid": False,
                "validation_status": "INVALID_INCIDENT_REF",
                "parsed_verdict": "REQUIRES_ATTENTION",
                "confidence": 0.0,
                "reason": str(parsed.get("reason") or ""),
                "supporting_claims": [],
                "supporting_evidence": [],
                "contradictory_evidence": [f"incident_id mismatch: {returned_inc_id}"],
                "missing_evidence": [],
                "analyst_questions": [],
                "schema_recovery_applied": bool(parsed.get("_schema_recovery_applied", False)),
                "truncated_output": bool(parsed.get("_truncated_output", False)) or (finish_reason == "length"),
                "confidence_scale": parsed.get("confidence_scale"),
            }

        returned_rule_ref = str(parsed.get("rule_id") or parsed.get("rule_reference") or "").strip()
        allowed_rule_refs = {
            str(v).strip()
            for v in (
                rule_spec.get("id"),
                rule_spec.get("rule_id"),
                rule_spec.get("event_type"),
                rule_spec.get("name"),
            )
            if v and str(v).strip()
        }
        if returned_rule_ref and allowed_rule_refs and returned_rule_ref not in allowed_rule_refs:
            return {
                "parse_success": True,
                "parse_error": f"rule_id mismatch: returned={returned_rule_ref}",
                "schema_valid": False,
                "validation_status": "INVALID_RULE_REF",
                "parsed_verdict": "REQUIRES_ATTENTION",
                "confidence": 0.0,
                "reason": str(parsed.get("reason") or ""),
                "supporting_claims": [],
                "supporting_evidence": [],
                "contradictory_evidence": [f"rule_id mismatch: {returned_rule_ref}"],
                "missing_evidence": [],
                "analyst_questions": [],
                "schema_recovery_applied": bool(parsed.get("_schema_recovery_applied", False)),
                "truncated_output": bool(parsed.get("_truncated_output", False)) or (finish_reason == "length"),
                "confidence_scale": parsed.get("confidence_scale"),
            }

        norm_conf = ConfidenceNormalizer.normalize(parsed.get("confidence"), parsed.get("confidence_scale"))
        is_truncated = (finish_reason == "length") or bool(parsed.get("_truncated_output", False))
        is_recovered = bool(parsed.get("_schema_recovery_applied", False))
        raw_claims = parsed.get("supporting_claims") or parsed.get("claims") or []
        supporting_claims = [c for c in raw_claims if isinstance(c, dict)] if isinstance(raw_claims, list) else []

        return {
            "parse_success": True,
            "parse_error": None,
            "schema_valid": bool(norm_conf.is_valid and not is_truncated and not is_recovered),
            "validation_status": (
                "INVALID_CONFIDENCE"
                if not norm_conf.is_valid
                else ("TRUNCATED_OUTPUT" if is_truncated else ("SCHEMA_RECOVERED" if is_recovered else "VALID"))
            ),
            "parsed_verdict": raw_verdict_str,
            "raw_confidence_value": parsed.get("confidence"),
            "confidence": float(norm_conf.normalized_percent or 0.0) if norm_conf.is_valid else 0.0,
            "confidence_scale": norm_conf.raw_scale,
            "confidence_valid": norm_conf.is_valid,
            "reason": str(parsed.get("reason") or ""),
            "supporting_claims": supporting_claims,
            "supporting_evidence": [str(x) for x in (parsed.get("supporting_evidence") or [])],
            "contradictory_evidence": [str(x) for x in (parsed.get("contradictory_evidence") or [])],
            "missing_evidence": [str(x) for x in (parsed.get("missing_evidence") or [])],
            "analyst_questions": [str(x) for x in (parsed.get("analyst_questions") or [])],
            "recommended_action": str(parsed.get("recommended_action") or ""),
            "schema_recovery_applied": is_recovered,
            "truncated_output": is_truncated,
            "parsed_json": parsed,
        }

    @classmethod
    async def _dispatch_vllm(
        cls,
        *,
        system_instruction: str,
        user_content: str,
        model_name: str,
        max_tokens: int,
        temperature: float,
        timeout_seconds: float,
        base_url: str,
        api_key: str,
        top_p: float = 1.0,
        enable_thinking: bool = False,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        }
        if "qwen3" in str(model_name or "").lower():
            payload["chat_template_kwargs"] = {"enable_thinking": bool(enable_thinking)}
        if response_format is not None:
            payload["response_format"] = response_format
        http_body_str = json.dumps(payload, separators=(",", ":"))
        req_ts = utc_now().isoformat()
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                res = await client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    content=http_body_str.encode("utf-8"),
                )
            resp_ts = utc_now().isoformat()
            latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            if res.status_code != 200:
                return {
                    "ok": False,
                    "error_type": "HTTP_ERROR",
                    "http_status": res.status_code,
                    "error_message": res.text[:500],
                    "request_timestamp_utc": req_ts,
                    "response_timestamp_utc": resp_ts,
                    "latency_ms": latency_ms,
                    "outbound_payload": payload,
                    "http_body_sha256": _sha256_text(http_body_str),
                }
            env = res.json()
            choice0 = (env.get("choices") or [{}])[0]
            raw_reply = str((choice0.get("message") or {}).get("content") or "")
            finish_reason = str(choice0.get("finish_reason") or "").lower().strip()
            usage = env.get("usage") or {}
            return {
                "ok": True,
                "http_status": 200,
                "request_timestamp_utc": req_ts,
                "response_timestamp_utc": resp_ts,
                "latency_ms": latency_ms,
                "outbound_payload": payload,
                "http_body_sha256": _sha256_text(http_body_str),
                "vllm_response_id": env.get("id"),
                "vllm_created": env.get("created"),
                "model_returned": env.get("model"),
                "finish_reason": finish_reason,
                "prompt_tokens": int(usage.get("prompt_tokens", 0)),
                "completion_tokens": int(usage.get("completion_tokens", 0)),
                "total_tokens": int(usage.get("total_tokens", 0)),
                "raw_response_text": raw_reply,
                "raw_response_sha256": _sha256_text(raw_reply),
                "raw_vllm_envelope": env,
            }
        except Exception as exc:
            resp_ts = utc_now().isoformat()
            latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            return {
                "ok": False,
                "error_type": type(exc).__name__,
                "http_status": None,
                "error_message": str(exc),
                "request_timestamp_utc": req_ts,
                "response_timestamp_utc": resp_ts,
                "latency_ms": latency_ms,
                "outbound_payload": payload,
                "http_body_sha256": _sha256_text(http_body_str),
            }

    @classmethod
    async def run_single_incident_three_mode(
        cls,
        db: AsyncSession,
        cohort_key: str,
        fortisiem_incident_id: str,
        max_context_tokens: int = 8192,
        max_completion_tokens: int = 768,
        target_input_budget: int = 7424,
        timeout_seconds: float = 180.0,
        temperature: float = 0.0,
        transport_override: Optional[Any] = None,
        mode: str = "ALL",
        neutral_prompt_version: str = "V2",
        include_complete_rule_def: bool = True,
        include_evidence_intelligence: bool = True,
        use_candidate_policy: bool = False,
        enable_thinking: bool = False,
        top_p: float = 1.0,
        use_structured_json: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes Mode A (Neutral), Mode B (Approved Policy), and Mode C (Deterministic Validator)
        for one frozen cohort incident without accessing or mutating ground truth or operational verdicts.
        Supports `mode` in {"ALL", "A", "B"} so callers can dispatch 1 GPU call per HTTP request.
        """
        run_mode = str(mode or "ALL").upper().strip()
        if run_mode not in ("ALL", "A", "B"):
            raise ValueError(f"Unsupported mode '{mode}'. Expected ALL, A, or B.")
        cohort = (
            await db.execute(select(BenchmarkCohort).where(BenchmarkCohort.cohort_key == cohort_key))
        ).scalar_one_or_none()
        if not cohort:
            raise ValueError(f"Benchmark cohort '{cohort_key}' not found.")

        item = (
            await db.execute(
                select(BenchmarkCohortItem)
                .where(
                    BenchmarkCohortItem.cohort_id == cohort.id,
                    BenchmarkCohortItem.fortisiem_incident_id == fortisiem_incident_id,
                )
                .options(
                    selectinload(BenchmarkCohortItem.incident).selectinload(Incident.events),
                    selectinload(BenchmarkCohortItem.incident).selectinload(Incident.rule),
                )
            )
        ).scalar_one_or_none()
        if not item or not item.incident:
            raise ValueError(f"Frozen incident '{fortisiem_incident_id}' not found in cohort '{cohort_key}'.")

        inc = item.incident
        rule_obj = inc.rule
        if not rule_obj:
            rule_obj = (
                await db.execute(
                    select(Rule).where(
                        or_(Rule.event_type == item.rule_id, Rule.rule_id == item.rule_id)
                    )
                )
            ).scalars().first()
        if not rule_obj:
            raise ValueError(f"Canonical Rule not found for incident '{fortisiem_incident_id}'.")

        rp, pv = await cls._resolve_approved_policy(db, rule_obj)
        if not pv:
            raise ValueError(f"No APPROVED PromptVersion found in DB for rule '{rule_obj.id}'.")

        # 1. Build strictly sanitized, blind incident payload
        raw_events = [
            {
                "eventId": ev.event_id,
                "eventType": ev.event_type or inc.event_type,
                "receiveTime": ev.event_receive_time,
                "rawMessage": ev.raw_log or "",
                "attribute": ev.attributes or {},
            }
            for ev in (inc.events or [])
        ]
        inc_dict = {
            "incidentId": item.fortisiem_incident_id,
            "title": inc.title or item.rule_name,
            "severity": inc.severity or "MEDIUM",
            "category": inc.category or "",
            "reportingDevice": inc.reporting_device or "",
            "reportingIp": inc.reporting_ip or inc.source_ip or "",
            "eventType": rule_obj.event_type,
            "firstSeen": inc.first_seen_epoch,
            "lastSeen": inc.last_seen_epoch,
            "createdAt": inc.created_at_epoch,
            "rawEvents": raw_events,
        }
        sanitized_payload = HistoricalGroundTruthValidator.sanitize_incident_for_inference(inc_dict)
        inc_adapter = IncidentAdapter(sanitized_payload, item.fortisiem_incident_id)
        norm_result = EvidenceNormalizationService.normalize_incident_evidence(
            incident=inc_adapter, events=None
        )
        from app.services.policy_governance import get_rule_semantics_and_contract
        _, contract, _ = await get_rule_semantics_and_contract(
            db, rule_obj, prompt_version=pv
        )
        preflight = EvidencePreflightValidator.validate_preflight(
            incident_id=item.fortisiem_incident_id,
            contract=contract,
            normalization_result=norm_result,
        )

        # 2. Compile policy (Approved DB policy OR isolated Experimental Candidate) & budget identical factual payload
        active_pv = get_experimental_candidate_policy(rule_obj.rule_id) if use_candidate_policy else pv
        compiled_policy = PolicyCompilerService.compile_policy(
            rule=rule_obj,
            prompt_version=active_pv,
            execution_mode=(
                CompilationExecutionMode.SIMULATION
                if use_candidate_policy
                else CompilationExecutionMode.LIVE
            ),
            raise_on_unapproved=(not use_candidate_policy),
            modular_optimization=False,
        )
        payload_dict = build_model_facing_payload(
            incident=inc_adapter, rule=rule_obj, events=inc_adapter.events, max_events=10
        )
        payload_dict["canonical_evidence"] = [r.model_dump() for r in norm_result.records]
        payload_dict["evidence_contract"] = {
            "contract_id": contract.contract_id,
            "version": contract.version_number,
            "required_fields": [r.field for r in contract.required_evidence],
        }
        if include_evidence_intelligence:
            payload_dict["evidence_intelligence"] = EvidenceIntelligenceEngine.enrich_incident_evidence(
                payload_dict, norm_result.records
            )

        if include_complete_rule_def:
            rule_spec = RuleDefinitionBuilder.build_complete_rule_spec(
                rule_obj=rule_obj,
                canonical_records=norm_result.records,
                incident_payload=payload_dict,
            )
        else:
            rule_spec = {
                "id": rule_obj.id,
                "rule_id": rule_obj.rule_id,
                "name": rule_obj.name,
                "event_type": rule_obj.event_type,
                "severity": rule_obj.severity,
                "description": rule_obj.description or "",
            }
        neutral_base = (
            EmpiricalBenchmarkHarness.NEUTRAL_SOC_BASELINE_V1
            if str(neutral_prompt_version or "").upper() == "V1"
            else EmpiricalBenchmarkHarness.NEUTRAL_SOC_BASELINE_V2
        )
        sys_a = neutral_base + _MODE_A_SCHEMA_SUFFIX
        sys_b = (
            f"{compiled_policy.compiled_system_prompt}\n\n"
            "Note: Populate supporting_claims[].cited_evidence_ids (or evidence_ids) strictly from incident.canonical_evidence[].evidence_id.\n"
            "IMPORTANT: Output ONLY compact JSON. Keep 'reason' concise (< 120 words). Limit 'supporting_claims' to max 3 factual items. Do NOT dump raw logs."
        )
        model_name_cfg = str(getattr(settings, "LOCAL_LLM_MODEL_NAME", "Qwen/Qwen3-14B-AWQ"))
        base_url = str(getattr(settings, "LOCAL_LLM_BASE_URL", "") or "").rstrip("/")
        model_name = model_name_cfg

        if run_mode == "A":
            wire_sys_for_budget = sys_a
        elif run_mode == "B":
            wire_sys_for_budget = sys_b
        else:
            sys_a_tok = ModelTokenizerService.count_tokens(sys_a, model_name=model_name_cfg)
            sys_b_tok = ModelTokenizerService.count_tokens(sys_b, model_name=model_name_cfg)
            wire_sys_for_budget = sys_b if sys_b_tok >= sys_a_tok else sys_a

        max_input_allowed = min(
            max(512, int(max_context_tokens) - int(max_completion_tokens)),
            int(target_input_budget),
        )
        rule_overhead = TokenBudgetService.estimate_tokens(rule_spec, model_name=model_name_cfg)
        safety_margin = 0
        rebudget_iterations = 0
        wire_token_audit: Dict[str, Any] = {}

        while True:
            budgeted = TokenBudgetService.budget_prompt(
                compiled_policy=compiled_policy,
                incident_payload=payload_dict,
                rag_block="",
                max_context_tokens=max_context_tokens,
                max_completion_tokens=max_completion_tokens,
                reserved_overhead_tokens=rule_overhead,
                model_name=model_name_cfg,
                target_input_budget=target_input_budget,
                wire_system_prompt=wire_sys_for_budget,
                wire_rule_spec=rule_spec,
                safety_margin_tokens=safety_margin,
            )
            if not budgeted.can_proceed_to_inference:
                raise ValueError(f"Budget overflow for {fortisiem_incident_id}: {budgeted.abstention_reason}")

            user_content = ModelTokenizerService.render_wire_user_message(
                budgeted.budgeted_incident_payload, rule_spec
            )

            if transport_override is None and base_url:
                remote_chk = await ModelTokenizerService.count_wire_prompt_tokens_remote(
                    base_url=base_url,
                    api_key=settings.LOCAL_LLM_API_KEY,
                    model_name=model_name,
                    system_prompt=wire_sys_for_budget,
                    user_message=user_content,
                    timeout_seconds=min(10.0, float(timeout_seconds)),
                    enable_thinking=enable_thinking,
                )
                wire_token_audit = {
                    **remote_chk,
                    "max_input_allowed": max_input_allowed,
                    "rebudget_iterations": rebudget_iterations,
                    "safety_margin_applied": safety_margin,
                }
                if remote_chk["token_count"] > max_input_allowed:
                    if rebudget_iterations < 2:
                        rebudget_iterations += 1
                        drift = max(0, int(remote_chk.get("drift_tokens") or 0))
                        excess = remote_chk["token_count"] - max_input_allowed
                        safety_margin += excess + max(64, drift // 2)
                        continue
                    raise ValueError(
                        f"CONTEXT_WINDOW_EXCEEDED: Rendered wire prompt ({remote_chk['token_count']} tokens via "
                        f"{remote_chk.get('source')}) exceeds safe input ceiling ({max_input_allowed}) preserving "
                        f"{max_completion_tokens} completion tokens for {max_context_tokens}-token limit."
                    )
            else:
                local_tok = ModelTokenizerService.count_wire_prompt_tokens(
                    wire_sys_for_budget, user_content, model_name
                )
                wire_token_audit = {
                    "token_count": local_tok,
                    "local_estimate": local_tok,
                    "drift_tokens": 0,
                    "source": "local_bpe_calibrated",
                    "tokenize_mode": "transport_override_or_no_base_url",
                    "max_input_allowed": max_input_allowed,
                    "rebudget_iterations": rebudget_iterations,
                    "safety_margin_applied": safety_margin,
                }
            break

        async def _call(sys_p: str) -> Dict[str, Any]:
            if transport_override is not None:
                return await transport_override(
                    system_instruction=sys_p,
                    user_content=user_content,
                    model_name=model_name,
                    max_tokens=max_completion_tokens,
                    temperature=temperature,
                )
            return await cls._dispatch_vllm(
                system_instruction=sys_p,
                user_content=user_content,
                model_name=model_name,
                max_tokens=max_completion_tokens,
                temperature=temperature,
                timeout_seconds=timeout_seconds,
                base_url=base_url,
                api_key=settings.LOCAL_LLM_API_KEY,
                top_p=top_p,
                enable_thinking=enable_thinking,
                response_format={"type": "json_object"} if use_structured_json else None,
            )

        # 3. Execute Mode A & Mode B live inference (selective per `run_mode`)
        raw_a: Optional[Dict[str, Any]] = None
        parsed_a: Optional[Dict[str, Any]] = None
        if run_mode in ("ALL", "A"):
            raw_a = await _call(sys_a)
            parsed_a = (
                cls._parse_raw_vllm_reply(
                    raw_reply=raw_a["raw_response_text"],
                    finish_reason=raw_a.get("finish_reason"),
                    incident_id=item.fortisiem_incident_id,
                    rule_spec=rule_spec,
                    prompt_tokens=raw_a.get("prompt_tokens", 0),
                    completion_tokens=raw_a.get("completion_tokens", 0),
                    requested_max_tokens=max_completion_tokens,
                )
                if raw_a.get("ok")
                else {"parse_success": False, "validation_status": raw_a.get("error_type", "PROVIDER_FAILURE"), "parsed_verdict": None}
            )

        raw_b: Optional[Dict[str, Any]] = None
        parsed_b: Optional[Dict[str, Any]] = None
        if run_mode in ("ALL", "B"):
            raw_b = await _call(sys_b)
            parsed_b = (
                cls._parse_raw_vllm_reply(
                    raw_reply=raw_b["raw_response_text"],
                    finish_reason=raw_b.get("finish_reason"),
                    incident_id=item.fortisiem_incident_id,
                    rule_spec=rule_spec,
                    prompt_tokens=raw_b.get("prompt_tokens", 0),
                    completion_tokens=raw_b.get("completion_tokens", 0),
                    requested_max_tokens=max_completion_tokens,
                )
                if raw_b.get("ok")
                else {"parse_success": False, "validation_status": raw_b.get("error_type", "PROVIDER_FAILURE"), "parsed_verdict": None}
            )

        def _validate_parsed_mode(parsed_mode: Optional[Dict[str, Any]], mode_label: str) -> Optional[Dict[str, Any]]:
            if not parsed_mode or not parsed_mode.get("parsed_verdict"):
                return {
                    f"input_{mode_label}_verdict": (parsed_mode or {}).get("parsed_verdict"),
                    "validated_verdict": "REQUIRES_ATTENTION",
                    "is_decisive_accepted": False,
                    "validation_status": (parsed_mode or {}).get("validation_status", f"{mode_label.upper()}_FAILED"),
                    "validation_reason_codes": ["MODEL_OUTPUT_INVALID"],
                    "action_directive": f"{mode_label} did not produce a valid parseable verdict.",
                    "grounding_ratio": 0.0,
                    "has_hallucinations": False,
                    "grounded_claims_count": 0,
                    "unsupported_claims_count": 0,
                    "unsupported_claim_details": [],
                    "validation_audit_trail": [],
                    "detected_contradictions": [],
                    "trust_score": 0,
                    "raw_trust_score": 0.0,
                    "effective_trust_verdict": "REQUIRES_ANALYST_ATTENTION",
                    "escalation_reason": f"{mode_label} invalid or failed response.",
                }
            if parsed_mode.get("truncated_output") or not parsed_mode.get("schema_valid"):
                trunc = bool(parsed_mode.get("truncated_output"))
                return {
                    f"input_{mode_label}_verdict": parsed_mode.get("parsed_verdict"),
                    "validated_verdict": "REQUIRES_ATTENTION",
                    "is_decisive_accepted": False,
                    "validation_status": "TRUNCATED_OUTPUT" if trunc else (parsed_mode.get("validation_status") or "INVALID_SCHEMA"),
                    "validation_reason_codes": ["OUTPUT_TRUNCATED" if trunc else "MODEL_OUTPUT_INVALID"],
                    "action_directive": (
                        "Model response hit completion limit (`finish_reason=length`) and was rejected safely to REQUIRES_ATTENTION."
                        if trunc
                        else "Model response failed structured schema validation."
                    ),
                    "grounding_ratio": 0.0,
                    "has_hallucinations": False,
                    "grounded_claims_count": 0,
                    "unsupported_claims_count": 0,
                    "unsupported_claim_details": [],
                    "validation_audit_trail": [],
                    "detected_contradictions": [],
                    "trust_score": 0,
                    "raw_trust_score": 0.0,
                    "effective_trust_verdict": "REQUIRES_ANALYST_ATTENTION",
                    "escalation_reason": "Truncated or schema-invalid response rejected from decisive operational acceptance.",
                }
            model_out = {
                "verdict": parsed_mode["parsed_verdict"],
                "confidence": parsed_mode.get("confidence", 0.0),
                "confidence_scale": parsed_mode.get("confidence_scale"),
                "reason": parsed_mode.get("reason", ""),
                "supporting_claims": parsed_mode.get("supporting_claims", []),
                "supporting_evidence": parsed_mode.get("supporting_evidence", []),
                "contradictory_evidence": parsed_mode.get("contradictory_evidence", []),
                "missing_evidence": parsed_mode.get("missing_evidence", []),
                "analyst_questions": parsed_mode.get("analyst_questions", []),
            }
            grounding = ModelClaimExtractor.extract_and_ground_claims(
                incident_id=item.fortisiem_incident_id,
                raw_verdict_output=model_out,
                normalization_result=norm_result,
            )
            val_res = IndependentVerdictValidator.validate_verdict(
                incident_id=item.fortisiem_incident_id,
                proposed_verdict=parsed_mode["parsed_verdict"],
                raw_model_confidence=float(parsed_mode.get("confidence", 0.0)),
                preflight=preflight,
                claim_grounding=grounding,
                normalization_result=norm_result,
                contract=contract,
                model_reason=str(parsed_mode.get("reason", "")),
                contradictory_evidence=parsed_mode.get("contradictory_evidence") or None,
                confidence_scale=parsed_mode.get("confidence_scale"),
            )
            trust_payload = dict(sanitized_payload)
            trust_payload["incident_id"] = item.fortisiem_incident_id
            trust_payload["rule_id"] = rule_obj.rule_id
            trust_payload["canonical_evidence"] = [r.model_dump() for r in norm_result.records]
            trust_res = VerdictTrustworthinessEngine.evaluate_verdict_trust(
                incident_payload=trust_payload,
                model_output=model_out,
                contract=contract,
            )
            return {
                f"input_{mode_label}_verdict": parsed_mode["parsed_verdict"],
                "validated_verdict": val_res.final_verdict,
                "is_decisive_accepted": bool(val_res.is_decisive_accepted),
                "validation_status": val_res.validation_status,
                "validation_reason_codes": list(val_res.validation_reason_codes),
                "action_directive": val_res.analyst_action_directive,
                "grounding_ratio": val_res.grounding_ratio,
                "has_hallucinations": grounding.has_hallucinations,
                "grounded_claims_count": grounding.grounded_claims,
                "unsupported_claims_count": grounding.unsupported_claims,
                "unsupported_claim_details": grounding.unsupported_claim_details,
                "validation_audit_trail": list(getattr(val_res, "validation_audit_trail", []) or []),
                "detected_contradictions": list(val_res.detected_contradictions),
                "trust_score": trust_res.trust_score,
                "raw_trust_score": trust_res.raw_trust_score,
                "effective_trust_verdict": trust_res.effective_verdict.value,
                "escalation_reason": trust_res.escalation_reason,
            }

        # 4. Execute Mode C deterministic validator on BOTH Mode A and Mode B (0 extra GPU calls)
        mode_a_validated = (
            _validate_parsed_mode(parsed_a, "mode_a")
            if (run_mode in ("ALL", "A") and raw_a and raw_a.get("ok"))
            else None
        )
        if run_mode in ("ALL", "B") and raw_b and raw_b.get("ok"):
            mode_c = _validate_parsed_mode(parsed_b, "mode_b")
        elif run_mode in ("ALL", "B"):
            mode_c = _validate_parsed_mode(None, "mode_b")
        else:
            mode_c = None

        return {
            "cohort_key": cohort.cohort_key,
            "fortisiem_incident_id": item.fortisiem_incident_id,
            "incident_db_uuid": inc.id,
            "priority_tier": "PRIORITY_5" if item.is_priority else "REMAINING_15",
            "priority_rank": item.priority_rank,
            "rule_identity": {
                "rule_uuid": rule_obj.id,
                "rule_id": rule_obj.rule_id,
                "rule_name": rule_obj.name,
                "approved_prompt_id": pv.prompt_id,
                "approved_prompt_version_id": pv.id,
                "approved_version_number": pv.version_number,
                "compiled_policy_digest": compiled_policy.compilation_digest,
            },
            "evidence_metadata": {
                "raw_evidence_sha256": item.raw_evidence_sha256,
                "canonical_evidence_sha256": item.canonical_evidence_sha256,
                "rule_definition_sha256": item.rule_definition_sha256,
                "preflight_status": preflight.preflight_status,
                "must_abstain_preflight": preflight.must_abstain_immediately,
                "canonical_evidence_ids": [r.evidence_id for r in norm_result.records],
                "budgeted_canonical_evidence_count": len(budgeted.budgeted_incident_payload.get("canonical_evidence") or []),
                "budgeted_events_count": len(budgeted.budgeted_incident_payload.get("events") or []),
                "offline_estimated_mode_a_tokens": ModelTokenizerService.count_wire_prompt_tokens(sys_a, user_content, model_name),
                "offline_estimated_mode_b_tokens": ModelTokenizerService.count_wire_prompt_tokens(sys_b, user_content, model_name),
                "wire_token_audit": wire_token_audit,
                "user_content_sha256": _sha256_text(user_content),
                "mode_a_system_sha256": _sha256_text(sys_a),
                "mode_b_system_sha256": _sha256_text(sys_b),
            },
            "experiment_config": {
                "neutral_prompt_version": neutral_prompt_version,
                "include_complete_rule_def": include_complete_rule_def,
                "include_evidence_intelligence": include_evidence_intelligence,
                "use_candidate_policy": use_candidate_policy,
                "policy_source_status": active_pv.status,
                "policy_version_id": active_pv.id,
                "policy_version_number": active_pv.version_number,
                "model_name": model_name,
                "temperature": temperature,
                "top_p": top_p,
                "enable_thinking": enable_thinking,
            },
            "mode_a": {"raw": raw_a, "parsed": parsed_a, "validated": mode_a_validated} if raw_a is not None else None,
            "mode_b": {"raw": raw_b, "parsed": parsed_b} if raw_b is not None else None,
            "mode_c": mode_c,
        }
