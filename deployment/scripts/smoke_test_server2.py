#!/usr/bin/env python3
"""
Repeatable Smoke Test for Server 2 Local LLM OpenAI-Compatible Endpoint (Stage 9).

Checks:
1. Health endpoint (/health)
2. Model listing (/v1/models)
3. Chat completion (/v1/chat/completions)
4. Structured JSON SOC verdict output schema check
5. Error handling on invalid model request
6. Runtime Prometheus metrics (/metrics)

Honesty Rule: Unreachable hosts produce status=NOT_EXECUTED (exit code 2), never PASS.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Tuple


def _http_call(url: str, method: str = "GET", payload: Dict[str, Any] | None = None, api_key: str = "EMPTY", timeout: float = 10.0) -> Tuple[int, str]:
    headers = {"Accept": "application/json"}
    if api_key and api_key != "EMPTY":
        headers["Authorization"] = f"Bearer {api_key}"
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as he:
        return he.code, he.read().decode("utf-8", errors="replace")


def run_smoke_test(base_url: str, model: str, api_key: str, timeout: float) -> Dict[str, Any]:
    clean_v1 = base_url.rstrip("/")
    root_url = re.sub(r"/v1$", "", clean_v1)
    report: Dict[str, Any] = {
        "base_url": clean_v1,
        "model": model,
        "overall_status": "NOT_EXECUTED",
        "checks": {},
    }

    # 1. Health
    try:
        t0 = time.monotonic()
        st, body = _http_call(f"{root_url}/health", timeout=min(timeout, 5.0), api_key=api_key)
        report["checks"]["health"] = {"status": "PASSED" if st == 200 else "FAILED", "http_status": st, "latency_ms": round((time.monotonic() - t0) * 1000, 1)}
    except Exception as exc:
        report["checks"]["health"] = {"status": "NOT_EXECUTED", "reason": f"Unreachable: {exc}"}
        report["overall_status"] = "NOT_EXECUTED"
        return report

    # 2. Model listing
    try:
        st, body = _http_call(f"{clean_v1}/models", timeout=timeout, api_key=api_key)
        models = [m.get("id") for m in json.loads(body).get("data", [])] if st == 200 else []
        report["checks"]["model_listing"] = {"status": "PASSED" if st == 200 and len(models) > 0 else "FAILED", "http_status": st, "models": models}
    except Exception as exc:
        report["checks"]["model_listing"] = {"status": "FAILED", "error": str(exc)}

    # 3. Chat completion
    try:
        t0 = time.monotonic()
        st, body = _http_call(
            f"{clean_v1}/chat/completions",
            method="POST",
            payload={"model": model, "messages": [{"role": "user", "content": "Reply with exactly: PONG"}], "max_tokens": 16, "temperature": 0.0},
            api_key=api_key,
            timeout=timeout,
        )
        ok = st == 200 and "choices" in json.loads(body)
        report["checks"]["chat_completion"] = {"status": "PASSED" if ok else "FAILED", "http_status": st, "latency_ms": round((time.monotonic() - t0) * 1000, 1)}
    except Exception as exc:
        report["checks"]["chat_completion"] = {"status": "FAILED", "error": str(exc)}

    # 4. Structured output
    try:
        prompt = (
            'Return strictly JSON with keys "verdict" (TRUE_POSITIVE|FALSE_POSITIVE|REQUIRES_ATTENTION), '
            '"confidence" (0-100), and "reason". Telemetry: src=192.0.2.10 missing dest_ip.'
        )
        st, body = _http_call(
            f"{clean_v1}/chat/completions",
            method="POST",
            payload={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 200, "temperature": 0.0},
            api_key=api_key,
            timeout=timeout,
        )
        raw_reply = json.loads(body)["choices"][0]["message"]["content"] if st == 200 else ""
        match = re.search(r"\{[\s\S]*\}", raw_reply)
        parsed = json.loads(match.group(0)) if match else {}
        valid_json = parsed.get("verdict") in ("TRUE_POSITIVE", "FALSE_POSITIVE", "REQUIRES_ATTENTION") and "reason" in parsed
        report["checks"]["structured_output"] = {"status": "PASSED" if valid_json else "FAILED", "parsed_keys": list(parsed.keys())}
    except Exception as exc:
        report["checks"]["structured_output"] = {"status": "FAILED", "error": str(exc)}

    # 5. Error handling
    try:
        st, _ = _http_call(
            f"{clean_v1}/chat/completions",
            method="POST",
            payload={"model": "nonexistent-model-smoke-check", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 8},
            api_key=api_key,
            timeout=timeout,
        )
        report["checks"]["error_handling"] = {"status": "PASSED" if st >= 400 else "FAILED", "http_status": st}
    except Exception as exc:
        report["checks"]["error_handling"] = {"status": "FAILED", "error": str(exc)}

    # 6. Runtime Prometheus metrics
    try:
        st, body = _http_call(f"{root_url}/metrics", timeout=timeout, api_key=api_key)
        has_vllm_metrics = st == 200 and ("vllm:" in body or "process_" in body or "python_" in body)
        report["checks"]["runtime_metrics"] = {"status": "PASSED" if has_vllm_metrics else "FAILED", "http_status": st}
    except Exception as exc:
        report["checks"]["runtime_metrics"] = {"status": "FAILED", "error": str(exc)}

    statuses = [v.get("status") for v in report["checks"].values()]
    report["overall_status"] = "PASSED" if all(s == "PASSED" for s in statuses) else "FAILED"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Server 2 vLLM Smoke Test")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct-AWQ")
    parser.add_argument("--api-key", default="EMPTY")
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()

    res = run_smoke_test(args.base_url, args.model, args.api_key, args.timeout)
    print(json.dumps(res, indent=2))
    if res["overall_status"] == "PASSED":
        return 0
    if res["overall_status"] == "NOT_EXECUTED":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

