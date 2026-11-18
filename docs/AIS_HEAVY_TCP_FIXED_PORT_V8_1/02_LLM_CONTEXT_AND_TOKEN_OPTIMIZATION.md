# 02 — LLM Context & Token-Budget Optimization Report

**Target Rule:** `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`, UUID `40498741-ee6b-4a71-9101-0d6d3f77154c`)
**Model:** `Qwen/Qwen2.5-7B-Instruct-AWQ` on Server 2 (`Verdictum Cortex`, `13.204.214.64:8000`, **RUNNING & UNTOUCHED**)
**Verified Runtime Context:** `4,096` tokens (`available_prompt_budget: 3,328`, `reserved_comp_tokens: 768` in V8.1 vs `3,584 / 512` in V8)

---

## 1. Measured Token Usage Comparison (Real Server 2 vLLM `API_USAGE`: V8 vs V8.1)

| Incident ID | V8 Prompt / Comp / Total (`max=512`) | V8.1 Prompt / Comp / Total (`max=768`) | Prompt Delta | Truncation Status (V8 → V8.1) | Fields Kept (V8 → V8.1) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`#176011`** (100 raw) | `3,288` / `512` *(cap)* / `3,800` | **`3,167`** / **`492`** / `3,659` | **`-121` tok** | `TRUNCATED` → **`COMPLETE`** | `11` → **`14`** (+3) |
| **`#175129`** (100 raw) | `3,336` / `512` *(cap)* / `3,848` | **`3,163`** / **`561`** / `3,724` | **`-173` tok** | `TRUNCATED` → **`COMPLETE`** | `12` → **`14`** (+2) |
| **`#164575`** (100 raw) | `3,287` / `512` *(cap)* / `3,799` | **`3,169`** / **`545`** / `3,714` | **`-118` tok** | `TRUNCATED` → **`COMPLETE`** | `11` → **`14`** (+3) |
| **`#167157`** (100 raw) | `3,286` / `512` *(cap)* / `3,798` | **`3,183`** / **`370`** / `3,553` | **`-103` tok** | `TRUNCATED` → **`COMPLETE`** | `11` → **`14`** (+3) |
| **`#173449`** (100 raw) | `3,290` / `512` *(cap)* / `3,802` | **`3,169`** / **`534`** / `3,703` | **`-121` tok** | `TRUNCATED` → **`COMPLETE`** | `11` → **`14`** (+3) |
| **`#176122`** (0 raw) | `3,295` / `384` / `3,679` | **`3,110`** / **`262`** / `3,372` | **`-185` tok** | `COMPLETE` → **`COMPLETE`** | `10` → **`10`** |
| **6-Incident Total** | `19,782` P / `2,944` C / `22,726` T | **`18,961` P / `2,764` C / `21,725` T** | **`-821` P tok (`-1,001` total)** | **`5/6` truncated → `0/6` (`0%`)** | **`66` → `80` (+14 fields)** |

---

## 2. Lossless Context Optimizations Implemented Inside 4,096 Tokens

1. **Compact Section 10 & Section 11 ([policy_compiler_service.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/policy_compiler_service.py)):** Removed duplicate `evidence_ids` alias alongside `cited_evidence_ids`, bounded concise `supporting_claims` (max 3) and `analyst_questions` (max 2), and trimmed boilerplate while preserving 100% of untrusted-data security boundaries and mandatory schema fields.
2. **Lossless Header & Contract Wire Cleanup ([token_budget_service.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/token_budget_service.py)):** Stripped empty-string/`None` incident keys (`description`, `detail`, `category`, `subcategory`, `source_ip`, `reporting_device`, `reporting_ip`), omitted duplicate `rule_pattern` when Section 3 is compiled, and omitted duplicate `conditional_fields`/`optional_fields` wire arrays when Section 4 is compiled (preserving `_orig_conditional_fields` locally for compaction priority).
3. **Wire Evidence Record Compaction ([evidence_compaction_service.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/evidence_compaction_service.py)):** Under tight budget overflow, stripped redundant `"evidence_type"` wire key while preserving 100% of `evidence_id`, `source_field`, and `observed_value` for grounding.
4. **Completion Budget Allocation ([verdict_pipeline.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/verdict_pipeline.py) & [openai_compatible.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/model_provider/openai_compatible.py)):** Raised 4,096-context `reserved_comp_tokens` from `512` → `768` (`3,328` prompt + `768` completion = `4,096`) and allowed verified `max_tokens_override` up to `1,024`.

---

## 3. Server 2 Context Extension Feasibility Assessment (No Restart Performed)

- **Current Live State Observed via Server 1 `/api/health` & `/api/llm/config`:**
  - Model: `Qwen/Qwen2.5-7B-Instruct-AWQ` (`ONLINE`, `max_model_len = 4096`, `max_concurrent_slots = 4`, `circuit_breaker_state = CLOSED`).
  - **GPU Telemetry Status:** `gpu_telemetry_verified: false` (Server 1 does not have direct `nvidia-smi` access to Server 2 `13.204.214.64`; exact GPU SKU and free VRAM are **`NOT VERIFIED`** and MUST be checked via `nvidia-smi` on Server 2 prior to any change).
- **KV-Cache Memory Math for `Qwen/Qwen2.5-7B-Instruct-AWQ`** (`28` layers, `4` GQA KV heads, `head_dim = 128`, FP16 KV = `28 × 2 × 4 × 128 × 2 bytes = 57.3 KB/token`; 4-bit AWQ model weights ≈ `5.5 GB` + CUDA/activations ≈ `1.5–2.0 GB` = `~7.5 GB` base):

| Candidate `--max-model-len` | KV Cache per Seq | KV Cache @ 4 Concurrent Slots | Est. Total VRAM (Base + 4 Slots) | Operational Verdict |
| :---: | :---: | :---: | :---: | :--- |
| **`4,096` (Current)** | `~224 MB` | `~0.90 GB` | `~8.4 GB` | **Working now with V8.1 (`0%` truncation, `14/14` scan fields)**; tight once 2+ RAG precedents are added. |
| **`8,192` (Recommended Candidate)** | `~448 MB` | `~1.79 GB` | `~9.3 GB` | **Recommended** for any `>= 16 GB` GPU (T4 / L4 / A10G / RTX 4090); fits full scan evidence + verified RAG precedents + `1,024` completion tokens effortlessly. |
| **`16,384` (Optional)** | `~896 MB` | `~3.58 GB` | `~11.1 GB` | Feasible on `>= 16–24 GB` GPU (`L4`/`A10G`), subject to `nvidia-smi` verification; not required until multi-precedent RAG exceeds `8,192`. |

- **Maintenance Approval & Rollback Procedure (DO NOT Execute Automatically):**
  1. **Preflight on Server 2:** Run `nvidia-smi` to verify GPU SKU, total VRAM, and free VRAM (`>= 12 GB` free recommended for `8,192`).
  2. **Change:** Update vLLM systemd/launch argument `--max-model-len 4096` → `--max-model-len 8192` (keeping `--gpu-memory-utilization 0.85` and `--max-num-seqs 4`) during an approved maintenance window.
  3. **Verify:** Check `curl -s http://13.204.214.64:8000/v1/models` returns `max_model_len: 8192`, run 1 test inference + 4-slot concurrency smoke test, and monitor `nvidia-smi` stability.
  4. **Rollback:** Restore `--max-model-len 4096`, restart vLLM service, and confirm `/api/health` returns `local_llm.current_s2_health: ONLINE`.
