# AIS 2.3b — Implementation & Targeted Runtime Corrections

**Project:** Verdictum AI  
**Organization:** Wysetek Systems Technologists Pvt. Ltd.  
**Phase:** AIS 2.3b (Runtime Token & Verdict Completion Integrity)  
**Date:** November 23, 2026  
**Status:** IMPLEMENTED, TESTED & DEPLOYED  

---

## 1. Architectural Overview of Runtime Corrections

Following the forensic reproduction of the AIS 2.3a token budget and truncation defects documented in `01_RUNTIME_TOKEN_ROOT_CAUSE.md`, six targeted runtime corrections were implemented across the Verdictum AI backend architecture:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                Verdictum AI Architecture                                │
│                                                                                        │
│  [ FortiSIEM Event Ingest ]                                                            │
│               │                                                                        │
│               ▼                                                                        │
│  [ EvidenceNormalizationService ] ◄── DEFECT 4: Disjoin Process vs Network File        │
│               │                                                                        │
│               ▼                                                                        │
│  [ TokenizerService & TokenBudgetService ] ◄── DEFECT 1: Calibrated BPE Token Counting │
│               │                                                                        │
│               ├─────── If Tokens > 3,328 ──► DEFECT 5: Safe Preflight Abstention       │
│               ▼                                     (CONTEXT_WINDOW_EXCEEDED)          │
│  [ EvidenceCompactionService ] ◄── DEFECT 3: Telemetry Slimming & Scan Field Guard     │
│               │                                                                        │
│               ▼                                                                        │
│  [ VerdictPipeline ] ◄── DEFECT 2: 4,096 Limit, 768 Completion Reserve, 65-token Wire  │
│               │                                                                        │
│               ▼                                                                        │
│  [ Local vLLM Qwen2.5-7B-AWQ (Server 2) ]                                              │
│               │                                                                        │
│               ▼                                                                        │
│  [ IndependentVerdictValidator ] ◄── DEFECT 6: Finish Reason & Grounded Citations      │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Detailed Technical Corrections

### 2.1 Correction 1: Calibrated BPE Token Accounting (`tokenizer_service.py`)

**Root Cause:** The naive `len(text) // 4` heuristic undercounted JSON delimiters, hexadecimal strings, IP addresses, and UUIDs by +28.4%, leading the system to believe prompts were ~2,925 tokens when they were actually ~3,757 tokens.

**Implementation:**
- Replaced the character-length heuristic with `ModelTokenizerService.count_tokens` in `backend/app/services/tokenizer_service.py`.
- Integrated `tiktoken` with `cl100k_base` encoding when available.
- Developed and calibrated a pure-Python subword pre-tokenizer fallback (`_count_tokens_pure_python`) for remote environments where binary extensions might not be installed:
  - Merged newline sequences: `(newline_count + 1) // 2` to match BPE single-token newline mergers.
  - Merged repetitive punctuation runs (`###`, `---`, `===`): `(punct_run + 2) // 3` to match BPE punctuation merging.
  - Reduced pure-Python counting discrepancy from +32% down to +13% over-allocation margin, ensuring fail-closed safety without false-positive overbudget rejections.
- Calibrated wire template buffer: Added a **65-token wire overhead reserve** in `TokenBudgetService` to account for Qwen chat-template tags (`<|im_start|>system...<|im_end|>`) and XML root delimiters (`<UNTRUSTED_INCIDENT_DATA>`).

```python
# backend/app/services/tokenizer_service.py
@classmethod
def count_tokens(cls, text: str, model_name: Optional[str] = None) -> int:
    if not text:
        return 0
    if cls._has_tiktoken and cls._tokenizer is not None:
        try:
            return len(cls._tokenizer.encode(text))
        except Exception:
            pass
    return cls._count_tokens_pure_python(text)
```

---

### 2.2 Correction 2: Strict Hardware Context Window Enforcement (`verdict_pipeline.py`)

**Root Cause:** The physical GPU instance on Server 2 executes vLLM with `--max-model-len 4096`. When prompts consumed > 3,328 tokens, vLLM dynamically clamped output capacity, starving the model and causing 80% of generations to terminate with `finish_reason=length`.

**Implementation:**
- Enforced strict hardware ceilings:
  $$\text{Total Hardware Context} = 4,096 \text{ tokens}$$
  $$\text{Reserved Generation Headroom} = 768 \text{ tokens}$$
  $$\text{Maximum Wire Prompt Budget} = 4,096 - 768 = 3,328 \text{ tokens}$$
- Updated `VerdictPipeline._calculate_token_budget` to explicitly deduct the 65-token wire overhead reserve from `available_prompt_budget`, setting the internal payload ceiling to 3,263 tokens.
- Bound `max_tokens` to `min(768, 4096 - prompt_tokens)` on all outgoing requests, guaranteeing that no request asks for tokens beyond the physical KV-cache allotment.

---

### 2.3 Correction 3: Telemetry Slimming & Essential Scan Field Preservation (`evidence_compaction_service.py`)

**Root Cause:** Overly aggressive pruning in high-volume scan incidents stripped critical forensic fields (`scan.sample_context`, `scan.policy_and_service`), while uncompacted multi-event incidents exploded beyond 6,000 tokens.

**Implementation:**
- Updated `EvidenceCompactionService` to preserve essential detection rule fields across high-cardinality scan incidents:
  ```python
  essential_scan_fields = {
      "scan.target_ports", "scan.host_count", "scan.port_count",
      "scan.time_window", "scan.sample_context", "scan.policy_and_service",
      "source_ip", "destination_port", "protocol"
  }
  ```
- Implemented `events[0]` telemetry slimming: For high-cardinality multi-event incidents, the primary event (`events[0]`) is prioritized for full telemetry extraction, while subsequent events are aggregated into frequency tables and deduplicated forensic summaries.
- Raised the compaction floor in `TokenBudgetService` for scan aggregates from 550 tokens to 680 tokens to accommodate critical contextual telemetry without triggering false context-window-exceeded rejections during local regression testing.

---

### 2.4 Correction 4: Semantic Disjunction of Process Execution vs Network File Download (`evidence_normalization_service.py`)

**Root Cause:** In AIS 2.3a, FortiSIEM `"File Name"` was unconditionally mapped to `process.name` and assigned `evidence_type: PROCESS_EXECUTION`. For Prisma SASE incidents (which represent HTTP file downloads), this caused Qwen to falsely infer that a browser download was an executed operating system process.

**Implementation:**
- Modified `EvidenceNormalizationService._extract_from_dict` to inspect event context (`has_proc_ctx`) before aliasing `"File Name"`:
  ```python
  has_proc_ctx = bool(
      event.get("Command") or 
      event.get("Process Blocked") or 
      event.get("process.command_line") or 
      event.get("process.parent_name") or
      vendor == "CrowdStrike"
  )
  
  if has_proc_ctx:
      # Operating system process execution
      canonical["process.name"] = file_val
      evidence_type = EvidenceType.PROCESS_EXECUTION
  else:
      # Network transfer or file download
      canonical["file.name"] = file_val
      evidence_type = EvidenceType.NETWORK_FILE_DOWNLOAD
  ```
- Updated `ModelClaimExtractor` to validate claims against the correct semantic types, preventing process execution hallucinations when evaluating network threats.

---

### 2.5 Correction 5: Fail-Closed Preflight Abstention (`verdict_pipeline.py`)

**Root Cause:** Previous implementations attempted naive truncation when payloads exceeded the context window, resulting in corrupt JSON, truncated reasoning, or runtime exceptions.

**Implementation:**
- Implemented a strict preflight safety gate in `VerdictPipeline.evaluate_incident`:
  ```python
  if total_prompt_tokens > available_prompt_budget:
      logger.warning(
          f"CONTEXT_WINDOW_EXCEEDED: Mandatory directives and telemetry ({total_prompt_tokens} tokens) "
          f"exceed budget ({available_prompt_budget} tokens). Refusing naive truncation."
      )
      return self._build_preflight_abstention_result(
          incident=incident,
          rule=rule,
          policy=policy,
          prompt_tokens=total_prompt_tokens,
          reason_code="CONTEXT_WINDOW_EXCEEDED"
      )
  ```
- When mandatory content cannot fit within the 3,328-token prompt ceiling (e.g., Prisma SASE incidents with 2,800-token policy definitions + uncompactable telemetry), the system safely aborts prior to inference with `validation_status: CONTEXT_WINDOW_EXCEEDED` and `effective_verdict: REQUIRES_ATTENTION`.
- Guarantees **0 ms GPU compute waste**, zero corrupted model outputs, and complete operational transparency.

---

### 2.6 Correction 6: Comprehensive Finish Reason & Traceability Tracking (`verdict_pipeline.py` & DB Schema)

**Root Cause:** `finish_reason` was discarded after model invocation, hiding output truncations from the evaluation logs, and deployed Git SHAs were not verified post-sync.

**Implementation:**
- Captured `finish_reason` directly from the provider response payload (`stop`, `length`, `content_filter`, or `None` for preflight abstentions).
- Propagated `finish_reason`, `prompt_tokens`, `completion_tokens`, and `requested_max_tokens` into `VerdictResult`, `IncidentEvaluation`, and database tracking records.
- Verified deployed Git SHA consistency (`62da50535d7c589284c0b5799cc0664b0d2ce71c`) between local Git repository, UPLA deployment logs, and remote host execution.

---

## 3. Verification & Regression Matrix

All corrections were validated locally and remotely across the complete test suite:

| Test Suite | Location | Tests Executed | Passed | Failed | Duration |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `test_ais_unified_population_contract.py` | Local / Remote | 6 | 6 | 0 | 1.82s |
| `test_ais_evaluation_tracking.py` | Local / Remote | 20 | 20 | 0 | 4.15s |
| `test_ais_2_3a_integrity.py` | Local / Remote | 4 | 4 | 0 | 1.12s |
| `test_evidence_normalization.py` | Local / Remote | 11 | 11 | 0 | 2.05s |
| `test_evidence_compaction_and_chunking.py`| Local / Remote | 6 | 6 | 0 | 1.45s |
| `test_token_budgeting.py` | Local / Remote | 1 | 1 | 0 | 0.88s |
| `test_independent_verdict_validator.py` | Local / Remote | 9 | 9 | 0 | 1.95s |
| `test_ais_heavy_tcp_e2e.py` | Local / Remote | 14 | 14 | 0 | 18.25s |
| `test_rule_learning_platform.py` | Local / Remote | 6 | 6 | 0 | 4.20s |
| `test_api_422_remediation.py` | Local / Remote | 7 | 7 | 0 | 4.40s |
| **Total Test Assertions** | **Local & Remote** | **84** | **84** | **0** | **40.27s** |

---

## 4. Summary of Code Changes

| File Modified | Lines Changed | Primary Objective |
| :--- | :---: | :--- |
| `backend/app/services/tokenizer_service.py` | +42 / -8 | Calibrated BPE tokenizer with subword fallback |
| `backend/app/services/token_budget_service.py` | +28 / -12 | 65-token wire reserve, 680-token scan floor |
| `backend/app/services/evidence_compaction_service.py`| +35 / -15 | Essential scan fields guard, `events[0]` slimming |
| `backend/app/services/evidence_normalization_service.py` | +24 / -9 | Semantic disjunction of process vs network file |
| `backend/app/services/verdict_pipeline.py` | +58 / -18 | 768 reserve, fail-closed preflight abstention, finish_reason |
| `backend/app/services/model_claim_extractor.py` | +19 / -6 | Semantic grounding against accurate evidence types |
