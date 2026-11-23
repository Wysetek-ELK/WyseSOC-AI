# AIS 2.4 — Targeted Pilot Evaluation Results

**Project:** Verdictum AI  
**Subsystem:** Agent Intelligence Studio (AIS)  
**Phase:** AIS 2.4 (Scalable Multi-Rule Verdict Evaluation & Context Expansion)  
**Date:** November 23, 2026  
**Status:** COMPLETED & BENCHMARKED  

---

## 1. Executive Summary

Before evaluating the wider 20-incident multi-rule dataset, Stage 5 executed a targeted pilot across the 5 historical benchmark incidents:
- **Crowdstrike Suspicious Activity:** `132438483`, `132527297`
- **Prisma SASE Suspicious File Threat Detection:** `132499009`, `132499023`, `132499745`

The pilot's primary objectives were:
1. Confirm that 8,192-token context expansion eliminates preflight context blockage for Prisma SASE.
2. Confirm zero unexpected output truncation (`finish_reason = stop`).
3. Ensure exact token accounting with $\ge 768$ completion headroom.
4. Enforce clean separation between raw model proposals and authoritative independent verdicts.

---

## 2. Pilot Incident Detailed Results

| Incident ID | Rule Archetype | 8K Wire Prompt Tokens | Headroom Remaining | Model Proposed Verdict | Model Confidence | Authoritative Verdict | Validator Disposition | Validation Reason Codes | Grounding Ratio |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `132438483` | CrowdStrike | 4,853 | 3,339 | `FALSE_POSITIVE` | 85.0% | `REQUIRES_ATTENTION` | **REJECTED** | `["FP_CRITERIA_UNSATISFIED"]` | 1.00 |
| `132527297` | CrowdStrike | 3,896 | 4,296 | `FALSE_POSITIVE` | 85.0% | `REQUIRES_ATTENTION` | **REJECTED** | `["FP_CRITERIA_UNSATISFIED"]` | 1.00 |
| `132499009` | Prisma SASE | 3,110 | 5,082 | `TRUE_POSITIVE` | 88.0% | `TRUE_POSITIVE` | **VALIDATED** | `["EVIDENCE_VALIDATED"]` | 1.00 |
| `132499023` | Prisma SASE | 3,141 | 5,051 | `TRUE_POSITIVE` | 88.0% | `TRUE_POSITIVE` | **VALIDATED** | `["EVIDENCE_VALIDATED"]` | 1.00 |
| `132499745` | Prisma SASE | 3,098 | 5,094 | `TRUE_POSITIVE` | 88.0% | `TRUE_POSITIVE` | **VALIDATED** | `["EVIDENCE_VALIDATED"]` | 1.00 |

---

## 3. Analysis & Key Insights

### 3.1 Elimination of Technical Preflight Abstention
In AIS 2.3b, all 3 Prisma SASE incidents abstained at preflight (`CONTEXT_WINDOW_EXCEEDED`, 0 tokens). In AIS 2.4, all 3 incidents cleared preflight with over **5,000 tokens of available headroom**, completing inference without error.

### 3.2 CrowdStrike Safe Overruling
In incidents `132438483` and `132527297`, the model proposed `FALSE_POSITIVE` on the grounds that UltraViewer activity appeared administrative. However, the independent validator identified that:
1. No affirmative IT maintenance ticket, scheduled task, or change request was present in telemetry.
2. Under Guardrail G6 (*Negative FP Prohibition*), remote access tools cannot be declared benign without verifiable authorization.
3. The decisive FP proposal was fail-closed **REJECTED** and overruled to `REQUIRES_ATTENTION`.

### 3.3 Zero Fabricated Evidence & Zero Ground-Truth Leakage
- Telemetry blinding was strictly enforced (all `resolution`, `clearedReason`, `comments`, and `cmsClearUser` fields stripped prior to prompt compilation).
- Ground truth labels remained completely inaccessible to the model and validator until after final verdict determination.
