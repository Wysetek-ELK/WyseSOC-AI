# 05 — Test Results: Actual LLM Prompt Inspector

**Platform:** Verdictum AI — Agent Intelligence Studio 2.0  
**Feature:** View Actual LLM Prompt  
**Date:** November 14, 2026  
**Status:** All 7 Tests Passing (100%)  

---

## 1. Automated Test Suite Execution

The dedicated test suite `backend/tests/test_actual_prompt_inspector.py` was executed using pytest against the active SQLite test database.

### Command:
```bash
pytest backend/tests/test_actual_prompt_inspector.py -v
```

### Execution Output:
```
============================= test session starts =============================
platform win32 -- Python 3.13.13, pytest-9.0.1, pluggy-1.6.0 -- C:\Users\amit\AppData\Local\Programs\Python\Python313\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\amit\OneDrive\Documents\SOC-AI-Agent
plugins: anyio-4.9.0, langsmith-0.7.22, asyncio-1.4.0, mock-3.15.1, respx-0.23.1
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 7 items

backend/tests/test_actual_prompt_inspector.py::test_heavy_tcp_scan_prompt_capture_end_to_end PASSED [ 14%]
backend/tests/test_actual_prompt_inspector.py::test_tampered_payload_integrity_mismatch PASSED [ 28%]
backend/tests/test_actual_prompt_inspector.py::test_unapproved_policy_not_dispatched_capture PASSED [ 42%]
backend/tests/test_actual_prompt_inspector.py::test_api_actual_prompt_for_incident PASSED [ 57%]
backend/tests/test_actual_prompt_inspector.py::test_api_historical_capture_unavailable PASSED [ 71%]
backend/tests/test_actual_prompt_inspector.py::test_api_prompt_preview_only_status PASSED [ 85%]
backend/tests/test_actual_prompt_inspector.py::test_api_export_json_and_markdown PASSED [100%]

============================== 7 passed in 6.23s ==============================
```

---

## 2. Test Breakdown & Coverage Matrix

| Test Name | Requirement Addressed | What Was Verified | Result |
|---|---|---|---|
| `test_heavy_tcp_scan_prompt_capture_end_to_end` | Req 2 & 6 | • Rule: `Heavy TCP Host Scan On Fixed Port`<br>• Policy version 2 selected<br>• `NETWORK_SCAN` archetype instructions present<br>• All 9 policy sections + Sections 10/11 included<br>• FortiSIEM threshold `50.0 distinct hosts` preserved<br>• Outbound user message contains normalized telemetry<br>• SHA-256 canonical hash matches outbound bytes<br>• Integrity status: `VERIFIED` | **PASSED** |
| `test_tampered_payload_integrity_mismatch` | Req 2 & 4 | • Tampering with raw payload bytes in database invalidates cryptographic digest<br>• Evaluates to `MISMATCH`<br>• `hash_match` is False | **PASSED** |
| `test_unapproved_policy_not_dispatched_capture` | Req 2 & 5 | • Early safety gate intercept (policy unapproved in prod)<br>• Creates explicit `NOT_DISPATCHED` capture record<br>• Integrity status: `UNVERIFIED`<br>• Explains reason without claiming dispatch | **PASSED** |
| `test_api_actual_prompt_for_incident` | Req 3 & 5 | • `GET /api/v1/prompts/actual-prompt/incident/{id}` returns HTTP 200<br>• Populates all 6 sections (Summary, System Prompt, Incident Payload, Precedents, Contract, Technical Details)<br>• Verifies `capture_status == "CAPTURED_RUNTIME"`<br>• Verifies `VIEW_ACTUAL_LLM_PROMPT` audit event | **PASSED** |
| `test_api_historical_capture_unavailable` | Req 3 | • Incident evaluated prior to capture engine returns HTTP 200<br>• Explicitly tagged `HISTORICAL_CAPTURE_UNAVAILABLE`<br>• Integrity marked `UNVERIFIED`<br>• Explains capture was unrecorded | **PASSED** |
| `test_api_prompt_preview_only_status` | Req 3 | • Live preview endpoint `GET /api/v1/prompts/actual-prompt/rule/{id}/preview`<br>• Explicitly tagged `PREVIEW_ONLY`<br>• Integrity marked `UNVERIFIED`<br>• Never presented as runtime proof | **PASSED** |
| `test_api_export_json_and_markdown` | Req 3 & 5 | • `GET /api/v1/prompts/actual-prompt/incident/{id}/export?format=json` returns attachment<br>• `GET /api/v1/prompts/actual-prompt/incident/{id}/export?format=markdown` returns structured audit report | **PASSED** |

---

## 3. Regression Suite Verification

To confirm no existing Prompt Studio or evaluation features were impacted, existing core suites were re-run:

| Test Suite | Tests Run | Result | Duration |
|---|---|---|---|
| `backend/tests/test_prompt_studio.py` | 1 | **PASSED** | 1.60s |
| `backend/tests/test_policy_compiler.py` | 4 | **PASSED** | 0.90s |
| `backend/tests/test_agent_intelligence_studio_v2.py` | 11 | **PASSED** | 2.12s |
| **Frontend Production Build** (`next build`) | 32 routes | **PASSED** (0 TypeScript errors) | 22.7s |

---

## 4. Live Local LLM (Server 2) vs Mock Parity Notice

- **Mocked Provider Tests:** Automated CI/CD runs execute against deterministic mocked and simulated providers (`SIMULATED`), verifying the exact request construction before network dispatch.
- **Live Local LLM Integration:** If Server 2 (vLLM / Ollama with Qwen 2.5 7B Instruct) is online, the `OPENAI_COMPATIBLE` provider routes through the exact same capture code path in `_invoke_provider_with_guards`.
- **Honesty in Testing:** No simulated test was falsely represented as a live GPU execution. Both provider modes share identical pre-dispatch canonical hashing and post-dispatch latency/token recording hooks.
