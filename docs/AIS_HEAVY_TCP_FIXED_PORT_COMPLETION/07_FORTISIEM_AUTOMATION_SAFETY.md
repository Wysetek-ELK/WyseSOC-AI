# 07 — Controlled FortiSIEM Automation Safety & Monitoring

**Target Rule:** `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT` / `40498741-ee6b-4a71-9101-0d6d3f77154c`)
**Live FortiSIEM Closures Executed:** **`0`** (strictly `dry_run=true` during all live tests; zero live SIEM mutations)
**Emergency Kill-Switch & Drift Monitoring:** Implemented, tested, and active in [automation_governor.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/automation_governor.py)

---

## 1. Twelve-Barrier Pre-Closure Safety Architecture

`AutomationGovernor.execute_governed_incident_decision` enforces 12 non-bypassable safety barriers before any FortiSIEM FP closure can occur:

| Verdict Path | Governed Behavior |
| :--- | :--- |
| **`TRUE_POSITIVE`** | **NEVER auto-closed.** Immediately routes to SOC escalation (`ESCALATED_TRUE_POSITIVE`), keeps FortiSIEM incident **OPEN**, and writes immutable audit record. |
| **`INSUFFICIENT_EVIDENCE` / `REQUIRES_ATTENTION`** | **NEVER auto-closed.** Routes to manual SOC review (`ROUTED_INSUFFICIENT_EVIDENCE`), keeps FortiSIEM incident **OPEN**, and records missing evidence fields. |
| **`FALSE_POSITIVE`** | Evaluated sequentially against all **12 barriers**: (1) Rule in `CONTROLLED_PRODUCTION`, (2) Automation policy explicitly `is_enabled=True`, (3) `emergency_disable=False`, (4) Verdict in `allowed_verdicts` (`FALSE_POSITIVE` only), (5) Zero `contradictory_evidence`, (6) `trust_score >= min_trust_score (8)`, (7) Exact active `APPROVED` `policy_version_id` match & `ai_execution_suspended=False`, (8) `empirical_accuracy >= 95%`, `fp_precision >= 99%`, `wilson_lower_bound >= 96%`, `tp_recall >= 95%`, `critical_missed_tp == 0`, (9) Daily closure cap not exceeded (`current_day_closure_count < 50`), (10) Idempotency check (no prior successful closure for `incident_id`), (11) Dry-run flag (`dry_run=True` simulates without external SIEM write-back), (12) Explicit FortiSIEM write-back with transaction/response-code audit logging. |

---

## 2. Live Server 1 Dry-Run Verification Results (`dry_run=true` ONLY)

Executed live against Server 1 PostgreSQL (`POST /api/governance/automation/decide/{id}` with `{"dry_run": true}`) immediately after real Server 2 GPU LLM inference:

| Incident ID | Customer | AI Verdict | Action Taken | Execution Status | `incident_closed` | Immutable PostgreSQL `audit_id` | Timestamp (UTC) |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| **`#176011`** | `GDC_NOC` | `INSUFFICIENT_EVIDENCE` | `ROUTE_TO_MANUAL_REVIEW` | `ROUTED_INSUFFICIENT_EVIDENCE` | **`false`** | `d3dccf33-61ab-4453-aeee-4d96313b29bc` | `2026-11-18T14:51:22Z` |
| **`#167157`** | `Demo-SOC` | `INSUFFICIENT_EVIDENCE` | `ROUTE_TO_MANUAL_REVIEW` | `ROUTED_INSUFFICIENT_EVIDENCE` | **`false`** | `df36735f-8df0-4cd8-bbca-2238f317d4f5` | `2026-11-18T14:51:37Z` |
| **`#175129`** | `GDC_NOC` | `INSUFFICIENT_EVIDENCE` | `ROUTE_TO_MANUAL_REVIEW` | `ROUTED_INSUFFICIENT_EVIDENCE` | **`false`** | `5f153cb3-4d2f-4f0d-bf19-5da34b0faf03` | `2026-11-18T14:51:57Z` |
| **`#176122`** | `GDC_NOC` | `INSUFFICIENT_EVIDENCE` | `ROUTE_TO_MANUAL_REVIEW` | `ROUTED_INSUFFICIENT_EVIDENCE` | **`false`** | `5d4cab65-5013-4de2-9b76-ed3cb60081d5` | `2026-11-18T14:52:06Z` |

All 4 records persisted cleanly in PostgreSQL `incident_automation_audits` (confirming the `VARCHAR(32)` `ROUTED_INSUFFICIENT_EVIDENCE` fix in production) with `siem_response_code: null`, `siem_transaction_id: null`, and `auto_closure_attempted: false`.

---

## 3. Automated Branch, Idempotency & Emergency Kill-Switch Verification

Verified in automated integration tests `test_05` and `test_08` ([test_ais_heavy_tcp_e2e.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/tests/test_ais_heavy_tcp_e2e.py)) on isolated SQLite with mocked FortiSIEM write-back:
- **TP Escalation (`#700001`):** `incident_closed == False`, `action_taken == ESCALATE_TRUE_POSITIVE`.
- **Insufficient Evidence (`#700002`):** `incident_closed == False`, `execution_status == ROUTED_INSUFFICIENT_EVIDENCE`.
- **Contradictory Evidence (`#700099`):** Even when rule is in `CONTROLLED_PRODUCTION` and enabled, `barrier_05_zero_contradictions == False` blocks closure (`incident_closed == False`).
- **Eligible FP Dry-Run & Mocked Write-Back (`#700003`):** Dry-run simulates cleanly without closing; mocked live call records `siem_transaction_id` and blocks duplicate closure on replay (idempotency barrier).
- **Automatic Missed-TP Emergency Suspension:** Recording a single confirmed `CRITICAL_MISSED_TP` immediately flips `emergency_disable = True` and transitions lifecycle stage to `SUSPENDED`, blocking all subsequent FP auto-closures until Administrator remediation.
