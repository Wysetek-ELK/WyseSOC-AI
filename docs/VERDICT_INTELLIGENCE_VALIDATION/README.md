# Verdict Intelligence Validation & Dry-Run Empirical Accuracy (AIS 2.1)

## Executive Overview

**Agent Intelligence Studio 2.1 — Dry-Run Intelligence Validation** introduces an auditable, evidence-grounded intelligence validation layer on top of Agent Intelligence Studio 2.0. 

While AIS 2.0 ensured that SIEM detection policies were structurally sound, detection-aware, and bound to machine-verifiable Evidence Contracts, **a high-quality policy alone does not guarantee that an AI verdict is correct**. 

AIS 2.1 bridges this gap by establishing:
1. **Evidence Sufficiency Engine**: Determines whether available telemetry satisfies contract requirements to support an automated decision (0–100 score). High scores can never override missing mandatory evidence.
2. **Claim-to-Evidence Validator**: Verifies model-asserted facts, entity references, and numeric thresholds against canonical incident telemetry, preventing hallucinations and detecting directional contradictions.
3. **Deterministic Verdict Guardrails**: Strictly gates output verdicts into three clear outcomes: `TRUE_POSITIVE`, `FALSE_POSITIVE`, or `REQUIRES_ANALYST_ATTENTION`.
4. **Verdict Trustworthiness Engine**: Computes an ordinal 1–10 Verdict Trust Score based on five explicit dimensions (35 claim support, 20 source reliability, 15 contradiction handling, 15 corroboration, 15 historical validation). Rules with fewer than 30 historical verification samples are capped at a maximum trust score of 6/10.
5. **Historical Ground Truth & Blind Evaluation**: Sanitizes incident payloads before inference to guarantee zero data leakage (stripping analyst verdicts, closure notes, and resolution strings), adjudicates historical labels, and partitions datasets into four deterministic hash-based splits.
6. **Empirical Accuracy & Calibration**: Evaluates classification performance (precision, recall, specificity, balanced accuracy) with Wilson score 95% confidence intervals, selective classification risk-coverage curves, Brier scores, and Expected Calibration Error (ECE).
7. **Simulation Lab & Paired Regression**: Evaluates candidate policies against historical benchmarks, automatically detecting regressions if accuracy drops or false negatives are introduced.
8. **Verdict Intelligence Dashboards (A–E)**: Interactive Next.js UI providing high-level trust metrics, accuracy/calibration curves, rule-level drill-downs, case explanations, and regression comparisons.

---

## Documentation Navigation Guide

| Document | Subject |
|---|---|
| [01_EXISTING_ARCHITECTURE_INTEGRATION.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/VERDICT_INTELLIGENCE_VALIDATION/01_EXISTING_ARCHITECTURE_INTEGRATION.md) | Integration with AIS 2.0, Rule Intelligence, Contracts & DB |
| [02_EVIDENCE_SUFFICIENCY_ENGINE.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/VERDICT_INTELLIGENCE_VALIDATION/02_EVIDENCE_SUFFICIENCY_ENGINE.md) | 4-Dimension Sufficiency Scoring & Infallible Missing Field Rule |
| [03_VERDICT_TRUSTWORTHINESS_ENGINE.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/VERDICT_INTELLIGENCE_VALIDATION/03_VERDICT_TRUSTWORTHINESS_ENGINE.md) | 5-Dimension Rubric, 1–10 Ordinal Scale & Calibration Capping |
| [04_VERDICT_GUARDRAILS.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/VERDICT_INTELLIGENCE_VALIDATION/04_VERDICT_GUARDRAILS.md) | G1–G7 Safety Gates & 3-Way Enforced Verdicts |
| [05_CLAIM_EVIDENCE_VALIDATION.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/VERDICT_INTELLIGENCE_VALIDATION/05_CLAIM_EVIDENCE_VALIDATION.md) | Fact Grounding, Entity Resolution & Threshold Assertion Defense |
| [06_HISTORICAL_GROUND_TRUTH.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/VERDICT_INTELLIGENCE_VALIDATION/06_HISTORICAL_GROUND_TRUTH.md) | Data Leakage Defense, Label Adjudication & 4-Way Splitting |
| [07_EMPIRICAL_ACCURACY_ENGINE.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/VERDICT_INTELLIGENCE_VALIDATION/07_EMPIRICAL_ACCURACY_ENGINE.md) | Confusion Matrix, Wilson 95% CIs & Risk-Coverage Curves |
| [08_CALIBRATION_AND_UNCERTAINTY.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/VERDICT_INTELLIGENCE_VALIDATION/08_CALIBRATION_AND_UNCERTAINTY.md) | Brier Score, ECE & Honest Small-Sample Reporting ($N < 30$) |
| [09_SIMULATION_AND_REGRESSION.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/VERDICT_INTELLIGENCE_VALIDATION/09_SIMULATION_AND_REGRESSION.md) | Paired Policy Regression & Statistical Significance Testing |
| [10_FRONTEND_AND_API.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/VERDICT_INTELLIGENCE_VALIDATION/10_FRONTEND_AND_API.md) | REST APIs, Dashboards A–E & Export Formats |
| [11_DATABASE_CHANGES.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/VERDICT_INTELLIGENCE_VALIDATION/11_DATABASE_CHANGES.md) | Alembic Migration 006 & SQLAlchemy Declarative Models |
| [12_TEST_RESULTS.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/VERDICT_INTELLIGENCE_VALIDATION/12_TEST_RESULTS.md) | Complete 36/36 Suite Results & 213/213 System Regression Pass |
| [13_DRY_RUN_USE_CASE_RESULTS.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/VERDICT_INTELLIGENCE_VALIDATION/13_DRY_RUN_USE_CASE_RESULTS.md) | 8 Reference Cases for `PH_RULE_LARGE_OUTBOUND_XFER` & Archetypes |
| [14_LIMITATIONS_AND_NEXT_STEPS.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/VERDICT_INTELLIGENCE_VALIDATION/14_LIMITATIONS_AND_NEXT_STEPS.md) | Operating Boundaries, Honest Assumptions & Future Work |
| [IMPLEMENTATION_STATUS.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/VERDICT_INTELLIGENCE_VALIDATION/IMPLEMENTATION_STATUS.md) | Master Audit Matrix & Verification Deliverables |

---

## Architecture Blueprint

```
+----------------------------------------------------------------------------------------------------+
|                                    HISTORICAL SIEM INCIDENT REPOSITORY                             |
+----------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
                     [ HistoricalGroundTruthValidator.sanitize_incident_for_inference ]
                         (Strips analyst notes, resolution strings, closure codes)
                                                  |
                 +--------------------------------+-------------------------------+
                 |                                                                |
                 v                                                                v
   +---------------------------+                                    +---------------------------+
   |   Local LLM Inference     |                                    | EvidenceSufficiencyEngine |
   |  (Candidate/Baseline Pol) |                                    |  (Contract & Archetype)   |
   +---------------------------+                                    +---------------------------+
                 |                                                                |
                 v                                                                |
   +---------------------------+                                                  |
   |   VerdictClaimValidator   |<-------------------------------------------------+
   | (Grounding, Contradiction)|
   +---------------------------+
                 |
                 v
   +---------------------------+
   |  VerdictGuardrailsEngine  |  (Deterministic Gates: missing mandatory -> ATTENTION;
   |  (3-Way Verdict Gate)     |   unsupported claim -> ATTENTION; blanket FP -> ATTENTION)
   +---------------------------+
                 |
                 v
   +---------------------------+
   | VerdictTrustworthinessEng |  (1-10 Ordinal Scale, 5-dim raw score, capped at 6 if uncalibrated)
   +---------------------------+
                 |
                 v
   +-------------------------------------------------------------------------------------+
   |                      EmpiricalAccuracyEvaluator & CalibrationEvaluator              |
   |              (Wilson 95% CIs, selective risk-coverage curves, ECE, Brier score)     |
   +-------------------------------------------------------------------------------------+
                 |
                 v
   +-------------------------------------------------------------------------------------+
   |                         VERDICT INTELLIGENCE DASHBOARD (A - E)                      |
   |             (Overview, Empirical Accuracy, Rule Trust, Incident Drilldown, Replay)  |
   +-------------------------------------------------------------------------------------+
```
