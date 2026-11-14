# VERDICTUM AI — PHASE 3
# 08. Agent Simulation Lab Simplification Specification

**Document Version:** 3.0.0  
**Phase:** Phase 3 — Unified Compact UI/UX Modernization  
**Page Implementation:** `frontend/src/app/agent-simulation-lab/page.tsx`  

---

## 1. Overview & Objectives

The Agent Simulation Lab provides controlled, offline replay benchmarking of synthesized detection policies against historical SIEM incidents without risking production automation or modifying live incident states.

The Phase 3 simplification achieves:
1. **Explicit Replay Engine Provenance:** Clear visual distinction between live local GPU LLM execution (`OPENAI_COMPATIBLE`) and deterministic heuristic simulation (`SIMULATED`).
2. **Compact Simulation KPI Row:** 4 high-density summary cards tracking Replay Engine, Active Batches, Scanned Incidents, and Empirical Accuracy.
3. **Honest Statistical Metrics:** Withholding misleading 0% accuracy displays when zero verified ground truth cases exist.
4. **Collapsible Diagnostics:** Progressive disclosure of missing telemetry gaps and clarification questions.

---

## 2. Replay Engine Provenance Clarity

Legacy simulations often confused analysts regarding whether an evaluation was produced by the local Qwen 2.5 7B LLM or heuristic code. The Phase 3 interface explicitly surfaces this distinction:
- **Server 2 LLM Status Indicator:** Surfaces real-time connection status (`Connected (Qwen 2.5 7B)`, `HTTP_MOCK Test Endpoint`, or `Disconnected - Heuristic Guard`).
- **Replay Engine Hero Card:** Displays `Local LLM` (in emerald) or `Heuristic Sim` (in neutral slate).
- **Per-Result Tag:** Individual results are stamped with either `OPENAI_COMPATIBLE` or `SIMULATED`.

---

## 3. High-Density KPI Header & Next Action Directive

Directly below the top banner, four compact summary cards provide instant context:
1. **Replay Engine:** Engine mode and model identifier.
2. **Replay Batches:** Total executed replay jobs and configuration count.
3. **Scanned Incidents:** Cumulative incidents processed across all partition splits.
4. **Empirical Accuracy:** Displays calculated accuracy percentage when verified cases exist, or `N/A (Pending Ground Truth)` when ground truth is absent.

The integrated `NextActionCard` guides the operator:
- When no job is selected: *"Configure and Launch Replay Batch: Select a detection rule and partition strategy to benchmark agent policies against historical incidents."*
- When inspecting a job: *"Inspecting Replay Batch [NAME]: Examine predicted verdicts and reasoning below, or open statistical evaluation reports in Verdict Intelligence."*

---

## 4. Result Inspector & Progressive Disclosure

When inspecting individual replay results from a batch:
- **Primary View:**
  - Incident ID, vendor event ID, rule name, latency ms, and model identifier.
  - Model predicted verdict vs historical ground truth verdict.
  - Full analytical reasoning and justification.
  - Supporting evidence attributes cited.
- **Advanced Diagnostics Accordion:**
  - Wraps Information Gaps / Missing Telemetry.
  - Wraps Recommended Analyst Clarification Questions.
  - Collapsed by default to prevent vertical sprawl during high-volume replay reviews.
