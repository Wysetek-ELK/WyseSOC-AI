# AIS 3.1 — Workstream 12: Empirical Accuracy & Statistical Integrity

**Run ID:** `64253e31-4e75-4d51-9f54-cc80a62fa17c` (`AIS31-FULL100-20261128`)  
**Benchmark Grade:** `PROVISIONAL_SINGLE_REVIEW_BENCHMARK` (`100 GT-2`, `0 GT-3`)  
**Positive Class:** `TRUE_POSITIVE`  
**Machine-Readable Evidence:**
- [ACCURACY_METRICS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_3_1/ACCURACY_METRICS.json)
- [CONFUSION_MATRIX.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_3_1/CONFUSION_MATRIX.json)
- [RULE_LEVEL_ACCURACY.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_3_1/RULE_LEVEL_ACCURACY.json)

---

## 1. Primary Empirical Metrics (Raw LLM vs. Validated Application)

| Metric | Raw LLM (`Qwen/Qwen3-14B-AWQ`) | Validated Application (`IndependentVerdictValidator`) | Denominator / Note |
|---|---:|---:|---|
| Original Cohort / Eligible Population | **100** / **100** | **100** / **100** | `98` binary GT (`18 TP, 80 FP`) + `2` human `INCONCLUSIVE` |
| Execution Success Rate | **100.0%** (`100/100`) | **100.0%** (`100/100`) | `0` failed, `0` skipped |
| **Decision Coverage (Original / Eligible)** | **25.0%** (`25/100`) | **1.0%** (`1/100`) | Conclusive binary verdicts (`25` vs `1`) / `100` |
| **Inconclusive Rate (`REQUIRES_ATTENTION`)** | **75.0%** (`75/100`) | **99.0%** (`99/100`) | Validator overrode `24/25` conclusive Raw predictions |
| **Correct / Incorrect Conclusive Verdicts** | **12** / **13** | **1** / **0** | `24/100` validator overrides, `20%` explicit rejections |
| **Conclusive Accuracy** | **48.0%** (`12/25`) | **100.0%** (`1/1`) *(degenerate N=1)* | Correct Conclusive / All Conclusive |
| **Conclusive Accuracy 95% Wilson CI** | `[30.03%, 66.50%]` | `[20.65%, 100.0%]` | Small sample (`N=25` / `N=1`) |
| **Eligible End-to-End Correct Rate** | **12.0%** (`12/100`) | **1.0%** (`1/100`) | Correct / All Eligible (`100`) |
| **Binary GT End-to-End Correct Rate** | **12.24%** (`12/98`) | **1.02%** (`1/98`) | Correct / `98` binary GT items |
| **Precision (`TRUE_POSITIVE`)** | **0.0%** (`0/7`, CI `[0.0%, 35.43%]`) | **N/A** (`tp=0, fp=0`) | `tp / (tp + fp)` |
| **Recall (`TRUE_POSITIVE`, conclusive)** | **0.0%** (`0/6`, CI `[0.0%, 39.03%]`) | **N/A** (`tp=0, fn=0`) | `tp / (tp + fn)`; **all 18 GT TPs missed** (`6` FN + `12` abstained raw) |
| **Specificity (TNR)** | **63.16%** (`12/19`, CI `[41.04%, 80.85%]`) | **100.0%** (`1/1`, CI `[20.65%, 100.0%]`) | `tn / (tn + fp)` |
| **F1 Score** | **N/A** | **N/A** | Undefined (`Precision=0, Recall=0`) |
| **Balanced Accuracy** | **31.58%** | **N/A** | `(Recall + Specificity) / 2` |
| **False Positive Rate** | **36.84%** (`7/19`) | **0.0%** (`0/1`) | `fp / (fp + tn)` |
| **False Negative Rate (conclusive)** | **100.0%** (`6/6`) | **N/A** | `fn / (tp + fn)`; plus `12` Raw / `18` App abstention-missed TPs |
| **Evidence-Grounding Pass Rate** | — | **64.0%** (`64/100`) | `ModelClaimExtractor` grounded claims w/o hallucinations |

---

## 2. Expanded & Binary Confusion Matrices

### Raw LLM (`Qwen/Qwen3-14B-AWQ`) Expanded Matrix (`N = 100`)
| Human GT \ Raw LLM | Predicted `TRUE_POSITIVE` | Predicted `FALSE_POSITIVE` | `REQUIRES_ATTENTION` (Abstained) | Failed |
|---|---:|---:|---:|---:|
| **`TRUE_POSITIVE` (18)** | **0** | **6** *(FN)* | **12** *(Abstention missed TP)* | 0 |
| **`FALSE_POSITIVE` (80)** | **7** *(FP overcall)* | **12** *(TN)* | **61** | 0 |
| **`INCONCLUSIVE` (2)** | 0 | 0 | **2** | 0 |

- **Raw Binary Matrix (`N = 25` valid TP/FP comparisons, 75 excluded):** `TP = 0, FP = 7, TN = 12, FN = 6`.

### Validated Application (`IndependentVerdictValidator`) Expanded Matrix (`N = 100`)
| Human GT \ Validated App | Predicted `TRUE_POSITIVE` | Predicted `FALSE_POSITIVE` | `REQUIRES_ATTENTION` (Abstained) | Failed |
|---|---:|---:|---:|---:|
| **`TRUE_POSITIVE` (18)** | **0** | **0** | **18** *(Abstention missed TP)* | 0 |
| **`FALSE_POSITIVE` (80)** | **0** | **1** *(FID 6016 TN)* | **79** | 0 |
| **`INCONCLUSIVE` (2)** | 0 | 0 | **2** | 0 |

- **Validated App Binary Matrix (`N = 1` valid comparison, 99 excluded):** `TP = 0, FP = 0, TN = 1, FN = 0`.

---

## 3. Baseline Comparisons (`N = 98` Binary GT: `18 TP`, `80 FP`)

| Baseline / Model | Conclusive Accuracy | End-to-End Binary Correct Rate | TRUE_POSITIVE Recall | Decision Coverage |
|---|---:|---:|---:|---:|
| **`ALWAYS_TRUE_POSITIVE`** | 18.37% | 18.37% (`18/98`) | 100.0% | 100.0% |
| **`ALWAYS_FALSE_POSITIVE` (Majority Class)** | **81.63%** | **81.63%** (`80/98`) | 0.0% | 100.0% |
| **Raw LLM (`Qwen/Qwen3-14B-AWQ`)** | **48.00%** | **12.24%** (`12/98`) | **0.0%** | **25.51%** (`25/98`) |
| **Validated App (`IndependentVerdictValidator`)** | 100.0% (`1/1`) | **1.02%** (`1/98`) | N/A (`0/18` all) | **1.02%** (`1/98`) |

- Because the holdout cohort is 81.63% `FALSE_POSITIVE` among binary labels, `ALWAYS_FALSE_POSITIVE` outperforms Raw LLM end-to-end correctness by `+69.39 pp` (`81.63%` vs `12.24%`).

---

## 4. Subpopulation & Cluster-Aware Breakdowns

1. **`VERIFIED_NO_DETECTED_EXPOSURE` (`N=25`):** Raw LLM predicted `REQUIRES_ATTENTION` on **25/25** (`0.0%` coverage, `0` correct, `4` GT TPs abstained).
2. **`HISTORICAL_LABEL_EXISTS_BUT_MASKED` (`N=75`):** All `25` conclusive Raw LLM calls occurred here (`conclusive_accuracy = 48.0%`, `12/25`, coverage `33.33%`), zero exposure leakage detected (`13/25` wrong).
3. **Deduplicated Raw-Log Clusters (`N=97` clusters across 3 pairs `('4871','4872')`, `('12116','12117')`, `('12542','12543')`):** All `6` paired large-outbound-transfer alerts abstained cleanly (`REQUIRES_ATTENTION`), so Raw LLM conclusive metrics remain identical (`conclusive_accuracy = 48.0% [12/25]`, `end_to_end = 12.37% [12/97]`).
4. **By Vendor (Raw LLM):** `FortiSIEM` (`n=66`, concl=`11`, acc=`63.64%`), `FortiGate / Firewall` (`n=23`, concl=`9`, acc=`55.56%`), `FortiSIEM System` (`n=3`, concl=`3`, acc=`0.0%`), `IPS / Firewall` (`n=4`, concl=`1`, acc=`0.0%`), `FortiGate` (`n=1`, concl=`1`, acc=`0.0%`), `MISP Threat Intel` (`n=3`, concl=`0`).
5. **By Customer (Raw LLM):** `GDC_NOC` (`n=39`, concl=`11`, acc=`72.73%`), `Demo-SOC` (`n=59`, concl=`14`, acc=`28.57%`), `Super` (`n=2`, concl=`0`).
6. **By Severity:** All `100` holdout incidents are `MEDIUM`.
7. **By Rule (Sample Highlights; see `RULE_LEVEL_ACCURACY.json`):** Strongest FP recognition on `PH_RULE_WEB_POL_VIOLATION_MANY_SRC_SAME_DEST` (`4/4`, 100%, including the sole `Validated App` accept `FID 6016`), `PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST` (`2/2`, 100%), `PH_RULE_BOGON_TRAFFIC` (`2/2`, 100%), `PH_RULE_VPN_LOGON_SUCCESS_OUTSIDE_COUNTRY` (`1/1`, 100%); systematic errors on `PH_RULE_HEAVY_TCP_PORT_SCAN` (`0/3`), `PH_RULE_HEAVY_TCP_HOST_SCAN` (`1/4`), and operational/config rules (`PH_RULE_ACCELOPS_COLLECTOR_DELAY`, `PH_RULE_NO_LOGS_VIA_AO`, `PH_RULE_NO_LOGS_FROM_DEVICE`, `PH_RULE_FGT_Config_Change`, `0/4`). Notice small per-rule `n=1..6` yields wide uncertainty intervals.
