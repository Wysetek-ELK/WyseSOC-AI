# AIS 3.1 — Workstream 18: Final Acceptance Gate Matrix

**Primary Phase Classification:** **`FAIL_INTELLIGENCE`**  
**Execution Date (UTC):** `2026-11-28`  
**Machine-Readable Evidence:** [ACCEPTANCE_GATE_MATRIX.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_3_1/ACCEPTANCE_GATE_MATRIX.json)

---

## 1. Mandatory Integrity Gates (`G01–G18`) — ALL 18 PASSED

| Gate | Requirement | Status | Verified Evidence |
|---|---|---|---:|
| **G01** | Original 100 cohort members reconciled | **PASS** | `100` unique UUIDs & FortiSIEM IDs across `30` rules (`0` overlap with `AIS_2_6E_FROZEN_20`) |
| **G02** | Existing 100 locked human reviews preserved | **PASS** | `100/100` locked reviews (`admin`) intact; `0` deleted, unlocked, or mutated |
| **G03** | Certification state accurately represented | **PASS** | `100/100 GT2_SINGLE_REVIEW`, `0/100 GT3_CERTIFIED`, `0` conflicts; benchmark explicitly tagged `PROVISIONAL_SINGLE_REVIEW_BENCHMARK` |
| **G04** | Exposure assessment completed | **PASS** | Root cause of legacy `100` flag documented; `25 VERIFIED_NO_DETECTED_EXPOSURE`, `75 HISTORICAL_LABEL_EXISTS_BUT_MASKED`, `0 CONFIRMED_EXPOSURE` |
| **G05** | Frozen dataset integrity verified | **PASS** | Domain-separated manifest `sha256=5e856ff85f0008cee40dec45c2f9e560ed760dd0413dcb7b559f7ff70d293d27` |
| **G06** | No detected prohibited label leakage | **PASS** | `0` leakage in wire prompts; `incidentReso` / `reso` / ML `confidence` stripped in `HistoricalGroundTruthValidator`, `model_payload_allowlist`, and `AIS31BenchmarkService` |
| **G07** | Holdout excluded from RAG and learning | **PASS** | `0/100` holdout incidents in `LearningRecord` (`88` total platform rows); `rag_excluded=true`, `memory_excluded=true` |
| **G08** | Active policy and benchmark configuration frozen | **PASS** | `NEUTRAL_SOC_BASELINE_V2` (`sha256=3b09dd249e3fad38ac795f88e957b1b305bd04025cc8fb6cc4605584b461fb6c`), `temp=0.0`, `enable_thinking=false` |
| **G09** | Actual target model verified | **PASS** | Live Server 1 -> Server 2 `/v1/models` and all `100/100` responses returned `Qwen/Qwen3-14B-AWQ` (`vLLM 0.33.0`, `max_model_len=8192`) |
| **G10** | Real GPU execution provenance verified | **PASS** | `100/100` real `chatcmpl-*` vLLM completions (`LIVE_SERVER2_VLLM`, mock disabled) |
| **G11** | Token and evidence integrity verified | **PASS** | `100/100` live `/tokenize` `<= 7424` (`max=7317`, `0` overflows, `0` empty `events` after fallback fix) |
| **G12** | All original cohort members accounted for | **PASS** | `100/100` attempted, `100/100` succeeded, `0` failed, `0` unexecuted |
| **G13** | All eligible results accurately reconciled | **PASS** | Paired against `98` binary GT (`18 TP, 80 FP`) + `2` human `INCONCLUSIVE` |
| **G14** | Correct accuracy and coverage denominators | **PASS** | Conclusive (`25` / `1`), Eligible (`100`), Binary GT (`98`), Cluster-dedup (`97`) reported explicitly without inflating denominators |
| **G15** | Raw LLM and final application accuracy separated | **PASS** | Raw LLM (`48.0%` concl, `25.0%` cov, `0%` TP recall) vs Validated App (`100.0%` `1/1`, `1.0%` cov) |
| **G16** | Security and blind-review tests passed | **PASS** | `6/6` live unauthenticated endpoints `401`; blind review flags verified; RBAC 403/401 tests passed |
| **G17** | Regression and deployment acceptance verified | **PASS** | `84/84` core backend pytest passed, `72/72` frontend tests passed, Next.js build passed; Server 1 deployed (`8c760c3b9f7957ad4283678ff1f8d1a31dd5dd96`) & CDP screenshots verified |
| **G18** | No fabricated or misleading results | **PASS** | Zero mocked metrics counted as live GPU results; primary classification honestly reflects empirical intelligence deficit |

---

## 2. Proposed Intelligence Performance Targets (Not Met — Triggers `FAIL_INTELLIGENCE`)

> [!NOTE]
> **Governance Gap Note:** No prior AIS phase formally ratified cross-rule numerical production thresholds across the 30-rule FortiSIEM cohort; therefore, AIS 3.1 evaluates performance against the documented proposed engineering targets alongside the verified `ALWAYS_FALSE_POSITIVE` (`81.63%`) baseline.

| Performance Metric | Proposed Target | Raw LLM Actual | Validated App Actual | Gate Result |
|---|---:|---:|---:|---|
| Conclusive Accuracy | `>= 90%` | **48.0%** (`12/25`) | **100.0%** (`1/1`) *(N=1 degenerate)* | **FAIL** |
| Eligible End-to-End Correct Rate | `>= 85%` | **12.0%** (`12/100`) | **1.0%** (`1/100`) | **FAIL** |
| `TRUE_POSITIVE` Recall | `>= 95%` | **0.0%** (`0/6` concl; `0/18` all) | **N/A** (`0` concl TP/FN; `0/18` all) | **FAIL** |
| F1 Score | `>= 90%` | **N/A** (`TP=0`) | **N/A** (`TP=0`) | **FAIL** |
| Balanced Accuracy | `>= 85%` | **31.58%** | **N/A** | **FAIL** |
| Decision Coverage | `>= 90%` | **25.0%** (`25/100`) | **1.0%** (`1/100`) | **FAIL** |
| False Negative Rate (conclusive) | `<= 5%` | **100.0%** (`6/6`) | **N/A** | **FAIL** |
| Successful Eligible Inference | `100%` | **100.0%** (`100/100`) | **100.0%** (`100/100`) | **PASS** |
| Grounding Pass Rate (0 unsupported target) | `100%` / `0` | — | **64.0%** (`64/100` grounded cleanly) | **FAIL** |
| Confirmed Prohibited Data Leakage | `0` | **0** | **0** | **PASS** |

---

## 3. Primary & Secondary Decision Classification

- **Primary Status:** **`FAIL_INTELLIGENCE`** (all 18 integrity gates and live GPU execution succeeded reproducibly, and `Qwen/Qwen3-14B-AWQ` + `IndependentVerdictValidator` empirically failed the intelligence performance targets on the 30-rule FortiSIEM holdout).
- **Secondary Statuses:**
  - `PROVISIONAL_SINGLE_REVIEW_BENCHMARK`: Dual-reviewer GT-3 certification remains `0/100` (`100/100 GT2_SINGLE_REVIEW`).
  - `APPROVED_THRESHOLDS_UNRATIFIED`: Formal business acceptance thresholds remain unratified.
  - **Ready for AIS 4.0?** **`false`** | **Production Autonomy Approved?** **`false`**.
