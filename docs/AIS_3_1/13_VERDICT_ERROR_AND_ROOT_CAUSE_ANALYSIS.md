# AIS 3.1 — Workstream 13: False Positive, False Negative & Failure Root-Cause Analysis

**Run ID:** `64253e31-4e75-4d51-9f54-cc80a62fa17c`  
**Machine-Readable Evidence:**
- [MISCLASSIFIED_INCIDENTS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_3_1/MISCLASSIFIED_INCIDENTS.json)
- [INCONCLUSIVE_INCIDENTS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_3_1/INCONCLUSIVE_INCIDENTS.json)

---

## 1. Failure & Abstention Breakdown (`N = 100`)

| Outcome Category | Raw LLM Count | Validated App Count | Primary Attribution |
|---|---:|---:|---|
| **Correct Conclusive Predictions** | **12** (all `TN`) | **1** (`FID 6016`, `TN`) | Web policy / Bogon / VPN rules |
| **False Negatives (`GT=TP`, Predicted `FP`)** | **6** | **0** *(6 overriden to abstain)* | Highest security risk: LLM reasoning + operational-vs-security semantic mismatch |
| **False Positive Overcalls (`GT=FP`, Predicted `TP`)** | **7** | **0** *(7 overridden to abstain)* | Internal/blocked scan overcalls + IPS blocked SQLi |
| **Abstentions (`REQUIRES_ATTENTION`) on GT TPs** | **12** | **18** | Excessive prompt conservatism / validator rules missing FortiSIEM telemetry |
| **Abstentions on GT FPs** | **61** | **79** | Missing IT allowlists / authorization context + validator rejections |
| **Appropriate Abstentions on GT `INCONCLUSIVE`** | **2** | **2** | Exact match (`FID 6552`, `FID 15811`) |
| **Technical Failures / Context Overflows** | **0** | **0** | Runtime & token pipeline 100% healthy |

---

## 2. Prioritized Root-Cause Analysis of All 6 False Negatives (Raw LLM)

> [!WARNING]
> **Critical Finding:** The Raw LLM produced **6 False Negatives** and **0 True Positives** across the 18 GT `TRUE_POSITIVE` incidents (`0.0%` recall). `IndependentVerdictValidator` blocked all 6 from passing into production verdicts (`0` App FNs), but via 99% abstention rather than accurate TP detection.

| FID | Rule ID | Human GT | Raw LLM -> Validated App | Root Cause & Category |
|---|---|---|---|---|
| `7301` | `PH_RULE_NO_LOGS_VIA_AO` | `TRUE_POSITIVE` | `FP` -> `REQUIRES_ATTENTION` (`INSUFFICIENT_EVIDENCE`) | **Prompt Policy Ambiguity & Semantic Mismatch:** LLM treated collector log outage as *"performance/configuration issue, not malicious attack"*; human SOC treated genuine collector failure alert as `TRUE_POSITIVE` rule hit. |
| `15482` | `PH_RULE_ACCELOPS_COLLECTOR_DELAY` | `TRUE_POSITIVE` | `FP` -> `REQUIRES_ATTENTION` (`INSUFFICIENT_EVIDENCE`) | **Prompt Policy Ambiguity:** Same operational-health vs cyber-attack definition mismatch (`TRUE_POSITIVE` collector delay). |
| `11002` | `PH_RULE_NO_LOGS_FROM_DEVICE` | `TRUE_POSITIVE` | `FP` -> `REQUIRES_ATTENTION` (`INSUFFICIENT_EVIDENCE`) | **Prompt Policy Ambiguity:** LLM dismissed device silence alert as operational benign; human confirmed `TRUE_POSITIVE`. |
| `11992` | `PH_RULE_FGT_Config_Change` | `TRUE_POSITIVE` | `FP` -> `REQUIRES_ATTENTION` (`REJECTED`) | **LLM Reasoning Error (Unsupported Authorization Assumption):** LLM claimed config update of `system.external-resource` was *"authorized"* without change-ticket evidence; validator rejected ungrounded FP. |
| `8777` | `PH_RULE_EXCESS_DENY_SRC` | `TRUE_POSITIVE` | `FP` -> `REQUIRES_ATTENTION` (`TRUNCATED_OUTPUT`) | **LLM Reasoning Error + Output Truncation (1 item):** LLM claimed denied connections from public IP implied firewall blocked it cleanly (missed sustained attack scan/deny escalation); raw JSON truncated mid-`supporting_claims` (though `verdict` + `reason` parsed). |
| `141` | `PH_RULE_EXCESS_DENY_EXT_COUNTRY` | `TRUE_POSITIVE` | `FP` -> `REQUIRES_ATTENTION` (`REJECTED`) | **LLM Reasoning Error:** LLM assumed high external-country firewall denies meant *"overly sensitive rule"* rather than active malicious probing; validator rejected FP. |

---

## 3. Root-Cause Analysis of All 7 False Positive Overcalls (`GT=FP`, Raw LLM=`TP`)

- **6 of 7** overcalls occurred on TCP scan rules (`5590`, `5563`, `12333` on `PH_RULE_HEAVY_TCP_PORT_SCAN`; `13218`, `4470`, `4660` on `PH_RULE_HEAVY_TCP_HOST_SCAN`). The LLM equated rule-triggering connection counts (`161–949` attempts from `172.26.x`/`172.27.x` RFC1918 hosts or external scans) directly with confirmed malicious reconnaissance, overlooking routine internal/blocked timeout scan patterns known to Demo-SOC / GDC_NOC analysts (**Missing Organizational Asset/Scanner Allowlist + LLM Reasoning Error**).
- **1 of 7** (`1107`, `PH_RULE_HIGH_SEV_SEC_IPS_OUT_DENY`): Outbound blocked SQLi signature (`15621`) treated by LLM as `TRUE_POSITIVE`; human reviewer marked `FALSE_POSITIVE`.

---

## 4. Why Decision Coverage Dropped to `25%` (Raw LLM) and `1%` (Validated App)

1. **Application Validator Scope Mismatch (`24 / 25` Decisive Predictions Overridden):**
   `IndependentVerdictValidator` enforces strict CrowdStrike/Prisma-derived requirements (endpoint process execution, binary hashes, or affirmative change tickets). When applied to FortiSIEM network/firewall/DNS/scan rules (`PH_RULE_*`), it rejected **100% (7/7)** of Raw `TRUE_POSITIVE` calls and **94.4% (17/18)** of Raw `FALSE_POSITIVE` calls, leaving `FID 6016` (`1/100`) as the sole validated conclusive verdict.
2. **Zero-Shot Neutral Baseline Prompt Under-Specification (`75 / 100` Raw Abstentions):**
   Compare AIS 2.9 on CrowdStrike/Prisma (`AIS_2_6E_FROZEN_20`): neutral `Mode A` ALSO had `0/3` TP recall (`0%`), whereas approved rule-aware `Mode B` policies reached `100%` TP recall (`9/9`) and `95%` validated agreement. On AIS 3.0's 30 unseen FortiSIEM rules (`10` draft-only, `16` unremediated v1), `NEUTRAL_SOC_BASELINE_V2` lacks rule-specific threat vs. benign criteria, forcing systematic abstention.
3. **Human Ground Truth Boundary Clarification Needed (Adjudication Candidate):**
   Operational health rules (`PH_RULE_NO_LOGS_VIA_AO`, `PH_RULE_ACCELOPS_COLLECTOR_DELAY`, `PH_RULE_NO_LOGS_FROM_DEVICE`) were marked `TRUE_POSITIVE` by reviewer #1 (rule fired accurately on real device/collector outage) while the LLM evaluates *"malicious security threat."* These GT-2 labels remain untouched here and are flagged for dual-reviewer GT-3 adjudication and SOC semantics clarification.

---

## 5. Independence & Improvement Policy Warning

Per Benchmark Integrity rules: **Do NOT tune prompts or validator logic on these 100 holdout failures and re-run `AIS_3_0_INDEPENDENT_HOLDOUT_100` as an acceptance claim.** All policy, rule-predicate, organizational-context, and validator improvements must be built on a **separate development dataset** and empirically validated on a **fresh untouched holdout cohort**.
