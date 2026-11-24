# AIS 2.6c — Workstream 18: Model Capability and Configuration Decision Report

**Phase:** AIS 2.6c  
**Report ID:** `AIS-2.6c-REP-18`  
**Execution Timestamp:** 2026-11-24T15:25:00Z  
**Active Execution Git SHA:** `d854a5ef7471b74dab408473963a4511eab4dc66`  
**Evaluated Model:** `Qwen/Qwen2.5-7B-Instruct-AWQ` on AWS GPU Server 2  

---

## 1. Executive Summary

Workstream 18 synthesizes the empirical evidence from the Three-Mode evaluation to deliver an authoritative, data-driven decision on model retention versus model upgrade.

**Authoritative Decision:** **RETAIN CURRENT MODEL (`Qwen/Qwen2.5-7B-Instruct-AWQ`). Do NOT upgrade the GPU instance or replace the model at this time.**

---

## 2. Empirical Justification

### 2.1 Is the Model Incapable of Distinguishing Benign vs Malicious Activity?
**No.** In Mode A (Neutral Baseline), the current model achieved:
- **100% correct identification of static web assets:** Classified all 9 web assets (`.js`, `.css`, `surveysensum_widget`, `clientlib`, etc.) as `FALSE_POSITIVE`.
- **Zero false alarms on routine browsing:** Correctly identified these assets as benign client-side code executed during normal business web usage.
- **Appropriate abstention on ambiguous software:** Refrained from labeling commercial tools (UltraViewer, MEGAsync) as True Positives when no exploitation evidence existed.

### 2.2 Why Did the Model Propose 100% True Positives in AIS 2.6b?
The 100% TP proposal rate was caused by **CrowdStrike Policy v3**, not model intelligence:
- Policy v3 instructed: *"Execution of remote access software or administrative tools without verified enterprise change ticket is TRUE_POSITIVE."*
- Because FortiSIEM alerts do not contain corporate change ticket logs, the model strictly followed its instructions: missing ticket = True Positive.
- When tested under the identical telemetry in Mode A (Neutral Baseline), the model proposed `REQUIRES_ATTENTION`.
- A larger model (14B, 32B, or 70B) would follow the flawed policy instructions with even higher fidelity, producing the exact same 100% TP proposal rate.

### 2.3 The Role of Evidence Deficiencies
FortiSIEM alerts provide network and process telemetry, but zero enterprise context (employee rosters, approved maintenance windows, IT helpdesk tickets). When the system prompt equates missing authorization with guilt, false positives become inevitable.

---

## 3. Recommended Engineering Configuration

1. **Retain Current Infrastructure:** Keep `Qwen/Qwen2.5-7B-Instruct-AWQ` running on NVIDIA A10G with 8,192 context window.
2. **Revise Approved Policies:**
   - Modify CrowdStrike Policy to require affirmative proof of attack (e.g. credential dumping, lateral movement, unquoted service path abuse) before proposing True Positive.
   - Mandate `REQUIRES_ATTENTION` whenever telemetry is ambiguous.
3. **Restore Anti-Bias Guidelines in Prompt Compiler:** Re-inject the anti-bias warnings from `ENTERPRISE_SOC_BASELINE_V2` into compiled system prompts.
4. **Fix Trust Payload Construction:** Maintain the `canonical_evidence` attachment implemented in `EmpiricalBenchmarkHarness.py` to prevent ordinal clamping to 3/10.

---

## 4. Machine-Readable Decisions

- [MODEL_RETENTION_OR_UPGRADE_DECISION.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/MODEL_RETENTION_OR_UPGRADE_DECISION.json)
- [RECOMMENDED_CONFIGURATION.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/RECOMMENDED_CONFIGURATION.json)
