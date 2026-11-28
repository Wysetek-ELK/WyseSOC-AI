# AIS 3.1 — Workstream 19: Remaining Blockers & AIS 4.0 Readiness

**AIS 4.0 Readiness Decision:** **NOT READY (`NO` — Hold AIS 4.0 Enterprise Transition)**

---

## 1. Exact Remaining Blockers Preventing AIS 4.0 Transition

1. **Core Multi-Rule Verdict Intelligence Deficit (`FAIL_INTELLIGENCE`):**
   - Under frozen zero-shot neutral prompt (`NEUTRAL_SOC_BASELINE_V2`), `Qwen/Qwen3-14B-AWQ` achieved `48.0%` conclusive accuracy (`12/25`), `25.0%` decision coverage (`25/100`), `12.0%` end-to-end correct rate (`12/100`), **`0.0%` TRUE_POSITIVE recall** (`0/6` conclusive; `6` False Negatives + `12` Raw abstentions across `18` GT TPs), and **lost to the `81.63%` majority-class (`ALWAYS_FALSE_POSITIVE`) baseline**.
2. **Application Validator Multi-Rule Incompatibility (`99%` Abstention):**
   - `IndependentVerdictValidator` overrode `24/25` conclusive Raw LLM verdicts (`24.0%` override rate), reducing application decision coverage to **`1.0%` (`1/100`, FID `6016`)** because its deterministic TP/FP rules require endpoint/file/change-ticket structures calibrated to CrowdStrike/Prisma rather than FortiSIEM firewall/scan/IPS/operational rules (`PH_RULE_*`).
3. **Unremediated Per-Rule Detection Policies Across Holdout Rules:**
   - `10/30` holdout rules still have only `DRAFT v1` policies and `16/20` approved rules carry legacy un-remediated v1 templates (`AIS 2.9` proved on CrowdStrike/Prisma that `Mode A` neutral scored `0/3` TP recall while rule-aware `Mode B` scored `9/9` `100%` TP recall).
4. **Operational Health Rules vs. Security Threat Semantics (`PH_RULE_NO_LOGS_*`, `PH_RULE_ACCELOPS_COLLECTOR_DELAY`, `PH_RULE_FGT_Config_Change`):**
   - `4/6` Raw LLM False Negatives stemmed from semantic ambiguity between *"the rule accurately fired on a genuine operational/config event"* (`TRUE_POSITIVE` per SOC reviewer) vs. *"malicious cyber intrusion"* (`FALSE_POSITIVE` per neutral LLM prompt).
5. **Independent Dual-Reviewer GT-3 Certification Pending (`0/100 GT-3`):**
   - All `100` holdout reviews are genuine single-reviewer locks (`GT2_SINGLE_REVIEW` by `admin`), making AIS 3.1 empirically `PROVISIONAL_SINGLE_REVIEW_BENCHMARK` until a second distinct qualified analyst reviews & adjudicates conflicts.
6. **Fresh Untouched Holdout Required After Any Prompt/Validator Tuning:**
   - Because `AIS_3_0_INDEPENDENT_HOLDOUT_100` failure cases (`MISCLASSIFIED_INCIDENTS.json`) were analyzed here, **subsequent intelligence improvements MUST use a separate development dataset and be certified against a fresh untouched holdout cohort**.
7. **Carry-Forward Infrastructure & Hygiene Blockers:**
   - Formal numerical business acceptance thresholds not ratified.
   - Server 1 -> Server 2 transport runs over HTTP `:8000` (TLS proxy or VPC peering still pending for production).
   - Server 2 physical GPU telemetry (`NVML/DCGM`) not exposed (`gpu_telemetry_verified=false`).
   - Pre-existing frontend ESLint errors (`369` errors) & `ruff`/`pip-audit` missing in build toolchain.

---

## 2. Minimum Targeted Corrective Action Plan Before Re-Proposing AIS 4.0

1. **Author & Validate Rule-Family Policies (`Mode B`) & Asset/Allowlist Grounding on a Separate Dev Dataset:**
   - Clarify SOC verdict semantics for operational health / configuration monitoring rules vs. threat alerts (`TRUE_POSITIVE` = rule accurately detected genuine anomalous/unapproved condition).
   - Author & certify structured FortiSIEM rule policies (`Mode B`) + verified organizational scanner/asset allowlist context across firewall, scan, IPS, DNS, and operational rule families.
   - Extend `IndependentVerdictValidator` contracts modularly per FortiSIEM archetype so genuine FortiSIEM TP/FP signals are validated accurately without blanket rejections.
2. **Collect Second Independent Human Reviews (`GT-3`):**
   - Assign a second qualified human analyst to review incidents blind on `/human-review-queue` (preserving `admin`'s existing 100 locks) and resolve any disagreements via adjudication.
3. **Construct & Freeze a Fresh Untouched Multi-Rule Holdout Cohort:**
   - Validate the remediated `Mode B` pipeline + validator on a genuinely untouched post-fix cohort (`Qwen/Qwen3-14B-AWQ`) against ratified business acceptance thresholds.
