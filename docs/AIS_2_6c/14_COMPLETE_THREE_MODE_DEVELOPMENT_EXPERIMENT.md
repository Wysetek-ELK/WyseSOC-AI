# AIS 2.6c — Workstream 14: Complete Three-Mode Development Experiment Report

**Phase:** AIS 2.6c  
**Report ID:** `AIS-2.6c-REP-14`  
**Execution Timestamp:** 2026-11-24T15:15:00Z  
**Active Execution Git SHA:** `d854a5ef7471b74dab408473963a4511eab4dc66`  
**Total Cohort Size:** 20 Frozen Historical Incidents  
**Evaluation Harness:** Production-Equivalent Deterministic Three-Mode Pipeline  

---

## 1. Executive Summary

Workstream 14 executes the complete Three-Mode empirical experiment across all 20 frozen historical incidents.

The experiment evaluates:
1. **Mode A (Neutral SOC Baseline):** Evaluates raw LLM intelligence under balanced instructions without rule-specific policy overrides.
2. **Mode B (Approved Rule Policy):** Evaluates model proposals with approved production policies compiled (CrowdStrike Policy v3, Prisma SASE Policy v1).
3. **Mode C (Full Validated Pipeline):** Reuses Mode B model outputs with **ZERO extra GPU calls**, running Independent Verdict Validation and Trust Scoring.

### Primary Experimental Discoveries:
1. **Mode A demonstrates balanced intelligence:** The model proposes **0 True Positives, 9 False Positives, and 11 Requires Attention**. It correctly identifies all 9 benign web assets without false positives, and refrains from declaring commercial utilities as malicious when evidence is inconclusive.
2. **Mode B demonstrates prompt-induced distortion:** Under approved policies, the model proposes **11 True Positives, 9 False Positives, and 0 Requires Attention**. The policy completely eliminated model abstention, forcing 11 incidents into True Positive classifications.
3. **Mode C enforces deterministic safety:** The validator evaluates the 11 TP proposals and 9 FP proposals. Because enterprise authorization logs are absent across all 20 incidents, the validator demotes all 20 incidents to `REQUIRES_ATTENTION`. Zero ungrounded decisions escape to the analyst.

---

## 2. Cohort Verdict Distribution Across Three Modes

| Evaluation Mode | Proposed TP | Proposed FP | Proposed Attention | Validator Accepted Decisive | Final Dispositions |
|---|---:|---:|---:|---:|---|
| **Mode A (Neutral Baseline)** | 0 | 9 | 11 | N/A (Direct proposal) | 9 FP, 11 RA |
| **Mode B (Approved Policy)** | 11 | 9 | 0 | N/A (Direct proposal) | 11 TP, 9 FP |
| **Mode C (Validated Pipeline)** | (Reused 11) | (Reused 9) | (Reused 0) | 0 | 20 RA |

---

## 3. Incident-by-Incident Paired Comparison

| Incident ID | Detection Rule | Mode A (Neutral) | Mode B (Policy) | Mode C (Validated) | Policy Impact (A -> B) | Validator Impact (B -> C) |
|---|---|---|---|---|---|---|
| `132438483` | CrowdStrike Alert | `REQUIRES_ATTENTION` | `TRUE_POSITIVE` | `REQUIRES_ATTENTION` | `RA -> TP` | `TP -> RA` |
| `132439932` | CrowdStrike Alert | `REQUIRES_ATTENTION` | `TRUE_POSITIVE` | `REQUIRES_ATTENTION` | `RA -> TP` | `TP -> RA` |
| `132441815` | CrowdStrike Alert | `REQUIRES_ATTENTION` | `TRUE_POSITIVE` | `REQUIRES_ATTENTION` | `RA -> TP` | `TP -> RA` |
| `132461358` | CrowdStrike Alert | `REQUIRES_ATTENTION` | `TRUE_POSITIVE` | `REQUIRES_ATTENTION` | `RA -> TP` | `TP -> RA` |
| `132461368` | CrowdStrike Alert | `REQUIRES_ATTENTION` | `TRUE_POSITIVE` | `REQUIRES_ATTENTION` | `RA -> TP` | `TP -> RA` |
| `132472498` | CrowdStrike Alert | `REQUIRES_ATTENTION` | `TRUE_POSITIVE` | `REQUIRES_ATTENTION` | `RA -> TP` | `TP -> RA` |
| `132474210` | CrowdStrike Alert | `REQUIRES_ATTENTION` | `TRUE_POSITIVE` | `REQUIRES_ATTENTION` | `RA -> TP` | `TP -> RA` |
| `132475024` | CrowdStrike Alert | `REQUIRES_ATTENTION` | `TRUE_POSITIVE` | `REQUIRES_ATTENTION` | `RA -> TP` | `TP -> RA` |
| `132477382` | CrowdStrike Alert | `REQUIRES_ATTENTION` | `TRUE_POSITIVE` | `REQUIRES_ATTENTION` | `RA -> TP` | `TP -> RA` |
| `132501348` | CrowdStrike Alert | `REQUIRES_ATTENTION` | `TRUE_POSITIVE` | `REQUIRES_ATTENTION` | `RA -> TP` | `TP -> RA` |
| `132499023` | Prisma SASE Threat | `FALSE_POSITIVE` | `FALSE_POSITIVE` | `REQUIRES_ATTENTION` | `IDENTICAL` | `FP -> RA` |
| `132499745` | Prisma SASE Threat | `FALSE_POSITIVE` | `FALSE_POSITIVE` | `REQUIRES_ATTENTION` | `IDENTICAL` | `FP -> RA` |
| `132591888` | Prisma SASE Threat | `FALSE_POSITIVE` | `FALSE_POSITIVE` | `REQUIRES_ATTENTION` | `IDENTICAL` | `FP -> RA` |
| `132595592` | Prisma SASE Threat | `FALSE_POSITIVE` | `FALSE_POSITIVE` | `REQUIRES_ATTENTION` | `IDENTICAL` | `FP -> RA` |
| `132596403` | Prisma SASE Threat | `REQUIRES_ATTENTION` | `TRUE_POSITIVE` | `REQUIRES_ATTENTION` | `RA -> TP` | `TP -> RA` |
| `132596956` | Prisma SASE Threat | `FALSE_POSITIVE` | `FALSE_POSITIVE` | `REQUIRES_ATTENTION` | `IDENTICAL` | `FP -> RA` |
| `132599145` | Prisma SASE Threat | `FALSE_POSITIVE` | `FALSE_POSITIVE` | `REQUIRES_ATTENTION` | `IDENTICAL` | `FP -> RA` |
| `132599146` | Prisma SASE Threat | `FALSE_POSITIVE` | `FALSE_POSITIVE` | `REQUIRES_ATTENTION` | `IDENTICAL` | `FP -> RA` |
| `132599330` | Prisma SASE Threat | `FALSE_POSITIVE` | `FALSE_POSITIVE` | `REQUIRES_ATTENTION` | `IDENTICAL` | `FP -> RA` |
| `132600277` | Prisma SASE Threat | `FALSE_POSITIVE` | `FALSE_POSITIVE` | `REQUIRES_ATTENTION` | `IDENTICAL` | `FP -> RA` |

---

## 4. Key Experimental Conclusions

1. **Proof of Model Semantic Capability:** In Mode A, the model demonstrated zero false alarms on the 9 web assets, classifying all 9 as `FALSE_POSITIVE`.
2. **Proof of Policy Bias:** When CrowdStrike Policy v3 was introduced in Mode B, 100% of CrowdStrike incidents flipped from `REQUIRES_ATTENTION` to `TRUE_POSITIVE`. The model followed instructions faithfully; the instructions themselves contained an inverted burden of proof.
3. **Proof of Validator Independence:** The validator operates completely deterministically and independently of model proposals. Regardless of whether the model proposed TP (Mode B) or FP (Modes A and B), the validator evaluated the affirmative evidentiary contract and demoted unverified claims to `REQUIRES_ATTENTION`.
4. **Zero GPU Waste in Validation:** Mode C achieved 100% validation coverage reusing Mode B outputs with 0 additional inference tokens or GPU runtime.

---

## 5. Machine-Readable Ledgers

The complete raw execution records are preserved in:
- [MODE_A_EXECUTION_LEDGER.jsonl](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/MODE_A_EXECUTION_LEDGER.jsonl)
- [MODE_B_EXECUTION_LEDGER.jsonl](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/MODE_B_EXECUTION_LEDGER.jsonl)
- [MODE_C_VALIDATION_LEDGER.jsonl](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/MODE_C_VALIDATION_LEDGER.jsonl)
- [UNIFIED_EXPERIMENT_RESULTS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/UNIFIED_EXPERIMENT_RESULTS.json)
- [EXPERIMENT_EXECUTION_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/EXPERIMENT_EXECUTION_MANIFEST.json)
