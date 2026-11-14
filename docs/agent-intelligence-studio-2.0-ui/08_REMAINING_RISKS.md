# 08 - Remaining Operational Risks & Safeguards

## 1. Overview

While the Agent Intelligence Studio 2.0 UI and backend readiness engine resolve user confusion, status discrepancies, and false readiness claims, certain operational and architectural boundaries remain critical for production operation. This document enumerates those risks and documents the enforced safeguards.

---

## 2. Risk Matrix & Enforced Mitigations

| Risk Domain | Potential Impact | Enforced Safeguard & Architectural Mitigation |
|---|---|---|
| **1. Offline Inference Server** | If vLLM / Qwen server is unreachable, operators may assume live inference passed if simulated replay is mistaken for empirical validation. | **Non-Fabrication Enforcement:** The backend strictly distinguishes `OPENAI_COMPATIBLE` (live GPU inference) from `SIMULATED` replay. Simulated replay is explicitly flagged in simulation records and is prohibited from satisfying Gate G8 for production promotion. |
| **2. Cold-Start Detection Rules** | New SIEM rules imported with zero historical incidents cannot establish ground truth immediately, remaining in `LEARNING` state. | **Staged Progression:** The guided checklist clearly informs the analyst that reviews are pending. Minimum 30 reviews are required before Supervised Pilot, preventing premature autonomous automation on untested signatures. |
| **3. Detection Rule Drift** | If a SIEM administrator alters correlation thresholds or logic in FortiSIEM after a policy was approved, the policy may become stale. | **Drift Event Engine:** Any detected change in SIEM XML/JSON triggers an unacknowledged drift event, sets `revalidation_required = True`, pulses the `DRIFT` alert in rule catalogs, and downgrades candidate readiness to `BLOCKED`. |
| **4. Database Indexing on Large Rule Sets** | Evaluating readiness dynamically across hundreds of rules in table view could cause database latency if not optimized. | **Pre-fetching & Bulk Cache:** `/api/prompts/summary` and `/api/rules` pre-fetch all active snapshots, prompts, and latest quality assessment records in single batched SQL queries rather than N+1 queries. |
| **5. Human Bias in Ground Truth Labeling** | Analysts reviewing incidents could align their verdict with the AI's prediction if visible upfront. | **Double-Blind Review Queue:** The AI verdict and reasoning are cryptographically and visually masked until after the analyst submits their independent verdict. |
| **6. Critical Missed Attack (False Negative)** | If the AI erroneously closes a true positive attack as benign, the SOC could miss an active breach. | **Zero-Tolerance Gate:** A single Critical Missed TP ($\text{AI: FP}, \text{Analyst: TP}$) in ground truth immediately halts automation, triggers rule suspension, and blocks Gate G8. A Global Emergency Kill-Switch is available on the workbench. |

---

## 3. Operational Recommendations

1. **Maintain Dedicated GPU Worker for Benchmark Suite:**
   - Run the 100-sample empirical benchmark suite exclusively when the local or remote vLLM model service is confirmed healthy (`GET /api/infrastructure/llm/status` reports `is_healthy: true`).
2. **Review Dispute Queue Weekly:**
   - SOC Leads should review the adjudication queue on a weekly cadence to resolve divergent determinations and keep ground-truth datasets calibrated.
3. **Audit Readiness Prior to Major Maintenance Windows:**
   - Use the bulk audit tool (`handleStartBulkAudit`) to run chunked policy assessments across all monitored rules prior to quarterly SOC governance audits.
