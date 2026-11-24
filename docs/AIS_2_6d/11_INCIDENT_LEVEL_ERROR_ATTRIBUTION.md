# AIS 2.6d — Workstream 11: Incident-Level Root Cause Error Attribution Report

**Phase:** AIS 2.6d  
**Evaluated At:** 2026-11-24T16:35:00Z  
**Document Identity:** `docs/AIS_2_6d/11_INCIDENT_LEVEL_ERROR_ATTRIBUTION.md`  
**Referenced Manifests:**  
- [ROOT_CAUSE_ATTRIBUTION_MATRIX.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/ROOT_CAUSE_ATTRIBUTION_MATRIX.json)
- [VERDICT_DISAGREEMENT_REGISTER.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/VERDICT_DISAGREEMENT_REGISTER.json)
- [HISTORICAL_DISCREPANCY_REGISTER.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/HISTORICAL_DISCREPANCY_REGISTER.json)

---

## 1. Discarding Unsupported Historical Percentages

In AIS 2.6c, error attributions reported specific numerical splits (e.g. "50% policy directive bias, 30% evidence omission, 10% prompt compiler bias"). As reconciled in Workstream 1, those numbers were derived from offline deterministic simulation models rather than empirical model behavior.

Under AIS 2.6d:
- All speculative percentage splits are expunged.
- Error taxonomy is formalized into 7 testable hypotheses (H1 through H7):
  1. **H1 (Policy Directive Bias):** Prompt instructions aggressively push standard administrative utilities (`whoami.exe`, `net.exe`) into False Positive verdicts regardless of network or host context.
  2. **H2 (Evidence Omission):** Critical telemetry fields (parent process, command-line arguments, user identity) are missing or trimmed by token budgets.
  3. **H3 (Prompt Truncation):** Evidence is placed past the effective attention horizon of the model.
  4. **H4 (Model Reasoning Failure):** The LLM hallucinates benign authorization or ignores malicious indicators despite full evidence.
  5. **H5 (Ground Truth Ambiguity):** Historical Level 1 labels are incorrect, conflicting, or poorly documented.
  6. **H6 (Validator Over-Rejection):** Programmatic validators incorrectly reject valid model True Positives due to brittle regex patterns.
  7. **H7 (Telemetry Inconsistency):** Log formats differ between SIEM collectors (e.g. FortiSIEM normalized vs raw JSON).

---

## 2. Live Attribution Status

Because live GPU inference has not yet run (blocked on GPU Server 2 activation) and human ground truth reviews are pending (Checkpoint A), no incident has been attributed to an empirical failure mode.

The register will record actual disagreements and error root causes once live inferences are compared against Level 2 human reviews.
