# AIS 2.6d — Workstream 12: Controlled Policy Bias Remediation Report

**Phase:** AIS 2.6d  
**Evaluated At:** 2026-11-24T16:40:00Z  
**Document Identity:** `docs/AIS_2_6d/12_CONTROLLED_POLICY_BIAS_REMEDIATION.md`  
**Referenced Manifests:**  
- [POLICY_BASELINE_CANDIDATE_DIFF.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/POLICY_BASELINE_CANDIDATE_DIFF.json)
- [COUNTERFACTUAL_LIVE_EXECUTION_LEDGER.jsonl](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/COUNTERFACTUAL_LIVE_EXECUTION_LEDGER.jsonl)
- [POLICY_IMPACT_MATRIX.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/POLICY_IMPACT_MATRIX.json)

---

## 1. Approved Policy vs Candidate Remediated Policy

In AIS 2.6c, prompt policy `bd751fac-9bfb-4994-b150-8850bb94dd6c` (Version 1) was hypothesized to exert strong bias toward False Positive classifications for admin tools (`whoami.exe`, `net.exe`).

Under AIS 2.6d, a controlled counterfactual prompt candidate has been formulated:
- **Baseline Policy (Version 1):** Instructs model that standard admin commands without lateral movement flags are typically benign/routine IT tasks.
- **Remediated Policy Candidate (Version 1-Remediated):** Explicitly neutralizes the default assumption, requiring positive proof of authorized administrative change tickets, scheduled task credentials, or known IT operator context before classifying administrative reconnaissance as a False Positive.

---

## 2. Controlled Counterfactual Protocol

To rigorously test whether prompt directives cause the model to shift verdicts (Hypothesis H1):
1. Incident cohort is held constant ($N = 20$).
2. Telemetry evidence payload is identical (verified by SHA-256 evidence hash).
3. Only the policy instruction block is modified.
4. Model hyperparameters are frozen (Temperature: 0.0, Top_P: 1.0, Max Tokens: 768).

Execution is staged to run across 11 targeted counterfactual incidents once GPU Server 2 is operational.

---

## 3. Policy Impact Matrix

Pending live execution:
- Baseline Policy FP Count: `AWAITING_GPU`
- Remediated Policy FP Count: `AWAITING_GPU`
- Verdict Shift Rate: `AWAITING_GPU`
- Unsafe FP Suppression Rate: `AWAITING_GPU`
