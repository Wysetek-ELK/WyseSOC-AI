# AIS 2.3 LLM Context Budget Validation (`CONTEXT_WINDOW_EXCEEDED`)

## 1. Root Cause of `CONTEXT_WINDOW_EXCEEDED` at Default `4096`

Measured baseline before AIS 2.3 optimization on a representative nine-section generated policy (`PolicyGenerationService.generate_nine_section_draft`) paired with canonical evidence and RAG precedent:
- **Section 2–9 generated policy bloat:** `NETWORK_SCAN` and `NETWORK_EXFILTRATION` drafts consumed `1,529` tokens in Sections 2–9 alone (verbose headers, repeated archetype rationale, multi-sentence boilerplate), bringing the compiled system prompt to **2,910 tokens** (`Heavy TCP Host Scan`) and **2,755 tokens** (`Large Outbound Data Exfiltration`).
- **Canonical evidence & wire bloat:** Each normalized evidence item serialized full `integrity_digest` (64-char SHA-256 hex), `incident_id`, `source_system`, `source_event_id`, `observed_at`, `availability`, and `provenance_status`, plus `OpenAICompatibleProvider` appended a duplicate JSON schema block (~160 tokens) on top of compiled Section 11 and pretty-printed `user_content` with `indent=2`.
- **Result under default `4096` context (`512` reserved completion = `3,584` available):**
  - `Heavy TCP Host Scan`: **3,995 tokens > 3,584** -> `CONTEXT_WINDOW_EXCEEDED`
  - `Large Outbound Data Exfiltration`: **3,821 tokens > 3,584** -> `CONTEXT_WINDOW_EXCEEDED`

## 2. Implemented Prompt & Budgeting Improvements

1. **Concise High-Signal Sections 2–8 (`PolicyGenerationService`):** Eliminated repetitive prose boilerplate while preserving 100% of TP/FP indicators, critical evidence fields, `INCOMPLETE`/`UNVERIFIED` threshold warnings, and `RFC-1918`/`127.0.0.1` anti-assumption guardrails.
2. **Evidence-Preserving Canonical Compaction & Overhead Accounting (`TokenBudgetService`):**
   - Retains strict P7 (RAG) -> P6 (enrichment) -> P5 (secondary events) priority trimming.
   - Adds step `3b` (`_compact_canonical_evidence`) strictly preserving every `evidence_id`, `source_field`, `observed_value`, and `evidence_type` while stripping non-reasoning SHA-256 `integrity_digest` / `null` fields ONLY when tight budgets require it.
   - Adds `reserved_overhead_tokens` so `rule_spec` metadata passed on the wire is budgeted accurately inside `verdict_pipeline.py`.
   - Still enforces fail-closed `CONTEXT_WINDOW_EXCEEDED` abstention (`REQUIRES_ATTENTION`) whenever mandatory P1–P4 core exceeds available budget.
3. **Wire Deduplication (`OpenAICompatibleProvider`):** Skips duplicating the JSON schema when `SECTION 11:` is already present in `prompt_text`, and serializes `{"incident", "rule"}` payload cleanly with compact `separators=(",", ":")`.
4. **Validated `8192` Option Without Blind Assumption:**
   - Supports `4096` (default) and `8192` via `LOCAL_LLM_CONTEXT_BUDGET` (`LLMConfigUpdate.context_budget`), synchronized across workers.
   - `LLMConfigService.test_connection()` probes Server 2 `/v1/models` for `max_model_len`; `RuntimeConfigValidator` flags `UNVERIFIED_EXTENDED_CONTEXT_BUDGET` if `>4096` without live Server 2 confirmation, or `CONTEXT_BUDGET_EXCEEDS_SERVER_CAPACITY` if Server 2 reports a smaller `max_model_len`.
   - `verdict_pipeline.py` clamps effective max context to `min(configured_ctx, LOCAL_LLM_VERIFIED_MAX_MODEL_LEN)` whenever Server 2 capacity has been observed.

## 3. Post-Edit Measured Archetype Context Budget Results

Measured directly with `PolicyGenerationService` + `PolicyCompilerService` + `EvidenceNormalizationService` + `TokenBudgetService` (`max_completion_tokens=512`, `rag_block` + `rule_spec` overhead included):

| Rule | Archetype | Compiled System Tokens | Rule Spec Overhead | 4,096 Total Prompt Tokens | Fits 4,096 (`<=3,584`)? | 8,192 Total Prompt Tokens | Fits Validated 8,192 (`<=7,680`)? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Heavy TCP Host Scan | `NETWORK_SCAN` | 2,379 | 42 | 3,515 | **Yes (`can_proceed_to_inference=true`)** | 3,515 | **Yes** |
| Suspicious PowerShell Execution | `MALWARE_EXECUTION` | 1,783 | 46 | 2,743 | **Yes** | 2,743 | **Yes** |
| Large Outbound Data Exfiltration | `NETWORK_EXFILTRATION` | 2,280 | 49 | 3,404 | **Yes** | 3,404 | **Yes** |
| Repeated Brute Force Logon Failure | `AUTHENTICATION` | 1,755 | 48 | 2,589 | **Yes** | 2,589 | **Yes** |

