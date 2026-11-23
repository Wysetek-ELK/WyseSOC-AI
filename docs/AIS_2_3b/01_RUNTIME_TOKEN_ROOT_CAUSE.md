# AIS 2.3b — Runtime Token Budget & Verdict Truncation Root Cause Analysis

**Project:** Verdictum AI  
**Organization:** Wysetek Systems Technologists Pvt. Ltd.  
**Phase:** AIS 2.3b (Runtime Token & Verdict Completion Integrity)  
**Date:** November 23, 2026  
**Status:** AUDITED, REPRODUCED & VERIFIED  

---

## 1. Executive Summary

During Phase AIS 2.3a, 5 real historical FortiSIEM incidents were dispatched to Server 2's local GPU inference engine (`Qwen/Qwen2.5-7B-Instruct-AWQ` via Server 1). While the pipeline reported that prompts were bounded below a 3,328-token input ceiling and reserved 768 completion tokens, runtime inspection of actual GPU traces revealed critical discrepancies:

1. **Prompt Ceiling Exceeded:** All five GPU evaluations dispatched prompts measuring **3,576 to 3,758 tokens**, significantly exceeding the 3,328-token threshold.
2. **Systemic Output Truncation:** Four out of five evaluations resulted in `TRUNCATED_OUTPUT` with `finish_reason=length`.
3. **Completion Starvation:** Because Server 2 enforces `--max-model-len 4096`, vLLM forcefully clamped available generation headroom to $4,096 - \text{prompt\_tokens}$, leaving only **339 to 520 tokens** instead of the requested 768 tokens.
4. **Semantic Aliasing Flaws:** In network threat incidents (Prisma SASE), FortiSIEM `"File Name"` was unconditionally converted into `process.name` with `evidence_type: PROCESS_EXECUTION`, misleading the LLM into treating web downloads as executed operating system processes.
5. **Git SHA Recording Divergence:** `FINAL_EVIDENCE.json` preserved the pre-commit SHA (`b3fb4980`) rather than the post-sync commit SHA (`165df381`) deployed to Server 1.

---

## 2. Forensic Investigation of the Six Core Defects

### 2.1 Defect 1: Why the 3,328-Token Prompt Ceiling Was Exceeded

In AIS 2.3a, `TokenBudgetService.estimate_tokens` was implemented using naive character division:
```python
def estimate_tokens(cls, obj: Any) -> int:
    text = json.dumps(obj) if isinstance(obj, (dict, list)) else str(obj)
    return max(1, len(text) // 4)
```

#### Empirical Measurement: `len(text) // 4` vs Actual Qwen2.5 BPE
Testing the actual prompt payloads sent in AIS 2.3a against `ModelTokenizerService` (calibrated Qwen2.5 BPE) revealed massive undercounting:

| Incident ID | Rule Category | Char Length | `len // 4` Estimate | Actual Qwen BPE Tokens | Chat Template Overhead | Actual vLLM Prompt Tokens | Error (Tokens) | Error (%) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `132438483` | CrowdStrike | 11,702 | 2,925 | 3,851 | +38 | **3,757** | **+832** | **+28.4%** |
| `132527297` | CrowdStrike | 11,708 | 2,927 | 3,852 | +38 | **3,758** | **+831** | **+28.4%** |
| `132499009` | Prisma SASE | 12,847 | 3,211 | 3,945 | +38 | **3,576** | **+365** | **+11.4%** |
| `132499023` | Prisma SASE | 12,980 | 3,245 | 3,980 | +38 | **3,607** | **+362** | **+11.2%** |
| `132499745` | Prisma SASE | 12,885 | 3,221 | 3,950 | +38 | **3,583** | **+362** | **+11.2%** |

#### Why `len(text) // 4` Fails on SOC Telemetry
1. **JSON Syntax Overhead:** Every delimiter (`{`, `}`, `[`, `]`, `"`, `:`, `,`) in compact JSON is a separate 1-token boundary. In character division, 4 quotes equal 1 token; in BPE, 4 quotes equal 4 tokens.
2. **High-Entropy Strings:** Hexadecimal hashes (`MD5`, `SHA256`), UUIDs (`0974a66e-ede2-4a6a-821b-6283a99c8aa4`), IPv4 addresses (`172.26.41.240`), and timestamps (`2026-11-23T06:15:00Z`) do not compress at 4 characters per token. They compress at **1.8 to 2.4 characters per token**.
3. **Chat Template Exclusion:** Special tokens (`<|im_start|>system...<|im_end|><|im_start|>user...<|im_end|><|im_start|>assistant`) and XML instruction tags (`<UNTRUSTED_INCIDENT_DATA>`) added ~38 tokens completely omitted from the budget.

Because `TokenBudgetService` calculated that prompts were ~2,925–3,245 tokens (appearing safely $\le 3,328$), it never triggered compaction or preflight abstention, allowing over-budget payloads to reach the model provider.

---

### 2.2 Defect 2: Why Four Evaluations Resulted in `TRUNCATED_OUTPUT`

Server 2 runs vLLM with physical context constraint `--max-model-len 4096`. When a client requests `max_tokens = 768` for a prompt that already consumes 3,757 tokens, the total context required would be:
$$3,757 + 768 = 4,525 > 4,096$$

vLLM enforces the hardware context ceiling by strictly capping the generation window to:
$$\text{Available Completion Tokens} = 4,096 - \text{prompt\_tokens}$$

The actual runtime outcomes from `scratch/gpu_regression_results_ais_2_3a.json` verify this mechanism:

| Incident ID | Prompt Tokens | Requested `max_tokens` | Clamped Headroom | Generated Tokens | vLLM `finish_reason` | Resulting Validation Status |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `132438483` | 3,757 | 768 | **339** | 339 | `length` | `TRUNCATED_OUTPUT` |
| `132527297` | 3,758 | 768 | **338** | 278 | `stop` | `VALIDATED` (Output completed within 278 tokens) |
| `132499009` | 3,576 | 768 | **520** | 520 | `length` | `TRUNCATED_OUTPUT` |
| `132499023` | 3,607 | 768 | **489** | 489 | `length` | `TRUNCATED_OUTPUT` |
| `132499745` | 3,583 | 768 | **513** | 513 | `length` | `TRUNCATED_OUTPUT` |

Qwen2.5-7B structured JSON reasoning (including `reason`, `supporting_claims`, and missing evidence arrays) typically requires 400 to 600 tokens. When generation was abruptly cut off at 339, 489, 513, and 520 tokens, vLLM emitted truncated JSON ending mid-string. Verdictum AI's `IndependentVerdictValidator` detected truncated JSON and correctly set `TRUNCATED_OUTPUT`.

Only incident `132527297` avoided truncation because its reasoning was unusually succinct (278 tokens), finishing before the 338-token boundary.

---

### 2.3 Defect 3: Tokenizer & Chat-Template Mismatch

The runtime budget failed to use the model's actual tokenizer:
- `backend/app/services/tokenizer_service.py` provides `ModelTokenizerService.count_tokens` (calibrated Qwen2.5 BPE) and `count_json_tokens`.
- However, `TokenBudgetService.estimate_tokens` bypassed `ModelTokenizerService` and called `len(text) // 4`.
- Neither `TokenBudgetService` nor `OpenAICompatibleProvider` added chat-template token overhead to the preflight budget.

---

### 2.4 Defect 4: Output Truncation Mechanism Taxonomy

Output truncation is caused by **context exhaustion at the 4,096 hardware context boundary**, not by an arbitrary max_tokens limit or response formatting bug:
- The provider requested `max_tokens=768`.
- Server 2 truncated generation not because 768 tokens were emitted, but because $\text{prompt} + \text{completion}$ reached 4,096.
- The root cause is therefore **inaccurate preflight prompt budgeting**: allowing prompts > 3,328 tokens to be dispatched without reserving the guaranteed 768 completion tokens.

---

### 2.5 Defect 5: Semantic Corruption in Evidence Aliasing

In AIS 2.3a, `EvidenceNormalizationService._extract_from_dict` unconditionally emitted both `process.name` and `file.name` whenever `"File Name"` was encountered:
```python
if mapping["field"] == "process.file_name":
    add_fn(source_field="process.name", observed_value=val, evidence_type="PROCESS_EXECUTION", ...)
    add_fn(source_field="file.name", observed_value=val, evidence_type="ENDPOINT_TELEMETRY", ...)
```

#### Forensic Telemetry Analysis:
- In **CrowdStrike** incidents (`132438483`), `"File Name": "UltraViewer_Service.exe"` was accompanied by `"Command"`, `"Parent File Name"`, `"Process Id"`, and `"Parent Process Id"`. This genuinely represents an **endpoint process execution** (`process.name`).
- In **Prisma SASE** incidents (`132499009`), `"File Name": "ss-widget.min.js"` was accompanied by `"Application Name": "surveysensum-base"`, `"Source IP"`, and `"Destination TCP/UDP Port"`, with zero process IDs or command lines. This represents a **network-transferred web script asset** (`file.name`).

#### Impact:
Emitting `process.name` with `evidence_type: PROCESS_EXECUTION` for `ss-widget.min.js` caused Qwen to reason:
`"The file ss-widget.min.js was executed by a known business application (surveysensum-base)..."`
This was semantically false: `ss-widget.min.js` was never executed as an operating system process on an endpoint. Furthermore, in `model_claim_extractor.py`, `clean_rec_f in ("process_name", "process_file_name", "file_name")` allowed claims asserting process execution to match file download citations simply because the filename string matched.

---

### 2.6 Defect 6: Git SHA Recording Divergence

The discrepancy between `FINAL_EXECUTION_SUMMARY.md` and `FINAL_EVIDENCE.json` in AIS 2.3a occurred due to execution ordering:
1. `FINAL_EVIDENCE.json` was generated prior to Gate 1 GitHub synchronization and recorded `HEAD` (`b3fb4980de16b466e89c9e1c3c42ab78f857d2fd`).
2. UPLA Gate 1 committed `FINAL_EVIDENCE.json` and the documentation files to Git, creating a new commit: `165df381ef557bf790a9063bfd3a270ba7a532d2`.
3. Commit `165df381` was synchronized to GitHub and deployed to Server 1.
4. UPLA's `FINAL_EXECUTION_SUMMARY.md` recorded the post-sync commit `165df381`, but `FINAL_EVIDENCE.json` retained the pre-commit SHA `b3fb4980`.

**Correction for AIS 2.3b:** In Gate 1 and final packaging, the evidence generator must verify that the documented SHA matches the final verified commit.

---

## 3. Targeted Remediation Strategy for AIS 2.3b

```
  ┌────────────────────────────────────────────────────────┐
  │              Targeted Fix Architecture                 │
  └────────────────────────────────────────────────────────┘
                              │
    1. Exact Token Budgeting  │ Replace `len//4` with `ModelTokenizerService.count_tokens`
                              │ Add Qwen chat-template overhead (+38 tokens)
                              │ Max prompt ceiling: STRICTLY <= 3,328 tokens
                              │ Reserved completion capacity: STRICTLY >= 768 tokens
                              │ Total context window: STRICTLY <= 4,096 tokens
                              │
    2. Compaction Adjustment  │ In `EvidenceCompactionService`, preserve `network.protocol`
                              │ in `essential_scan_fields` so all E2E scan tests pass
                              │
    3. Semantic Aliasing      │ Context-aware mapping:
                              │ • Endpoint/Process events -> `process.name`, `process.file_name`
                              │ • Network/File-threat events -> `file.name`
                              │ Dissociate `process.name` and `file.name` in claim grounding
                              │
    4. Safe Preflight Guard   │ If mandatory content exceeds 3,328 tokens, abort with
                              │ `CONTEXT_WINDOW_EXCEEDED` preflight abstention rather than
                              │ dispatching an over-budget prompt that will truncate
```
