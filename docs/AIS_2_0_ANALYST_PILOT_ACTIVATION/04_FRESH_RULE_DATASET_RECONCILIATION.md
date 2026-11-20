# Report 04 — Fresh Rule Dataset Reconciliation
**Verdictum AI — AIS 2.0 Website Access Policy Dataset Audit & Reconciliation**
**Date:** November 20, 2026  
**Status:** RECONCILED & FACTUALLY VERIFIED  
**Target Rule:** Website Access Policy Violation (`7bd13e89-0828-48e6-8cf5-f3cbf12d438c`)  

---

## 1. Executive Summary

This report reconciles the quantitative incident counts, evidence availability, and rule semantics for **Website Access Policy Violation: Same Source and Destination** (`7bd13e89-0828-48e6-8cf5-f3cbf12d438c`). Prior documentation cited varying numbers across different operational contexts: 210 incidents, 220 pending reviews, and 226 processed records. This document clarifies the exact provenance of each figure, validates raw log completeness, and documents the authoritative FortiSIEM correlation logic.

---

## 2. Reconciliation of Incident Counts (210 vs 220 vs 226)

| Metric / Counter | Count | Exact Provenance & Query Definition | Operational Meaning |
|:---|:---:|:---|:---|
| **Raw Target Incidents** | **210** | `SELECT COUNT(*) FROM incidents WHERE event_type = 'PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST'` | Total original incidents ingested during the baseline FortiSIEM synchronization snapshot. All 210 were in `OPEN` state with zero historical resolutions. |
| **Pending Review Queue** | **220** | `GET /api/reviews/pending?rule_id=7bd13e89-0828-48e6-8cf5-f3cbf12d438c` | Includes alias expansion across `Rule.id`, `Rule.rule_id`, and `Rule.event_type`, plus 10 newly ingested live events captured by the background poller after the initial 210-incident snapshot. |
| **Cumulative Profile Iterations** | **226** | `rule_learning_profiles.total_incidents_processed` | Internal execution counter tracking total incident evaluation passes, including initial benchmark simulations (16 simulation iterations) and poller cycles. |

**Conclusion:** The three figures represent different timestamped snapshots and operational counters, rather than data corruption or duplication. The live review queue currently holds **220** pending unreviewed incidents.

---

## 3. Evidence Completeness & Event Count Resolution

### 3.1 Stratification of Raw Telemetry
Inspection of child event records (`incident_events`) across the 210 baseline incidents reveals:
```
Total Baseline Incidents: 210
├── Rich Raw Events (≥ 1 raw UTM event log): 184 incidents (87.6%)
│     ├── 1 event:   42 incidents (20.0%)
│     ├── 2 events:  26 incidents (12.4%)
│     ├── 3 events:  18 incidents (8.6%)
│     ├── 4–10 events: 28 incidents (13.3%)
│     ├── 11–50 events: 41 incidents (19.5%)
│     └── 51–100 events: 29 incidents (13.8%)
│
└── Header-Only Alerts (0 raw logs): 26 incidents (12.4%)
      └── Correlated alert headers without captured UTM child event payloads
```

### 3.2 Root-Cause Fix for `event_count = 0` Serialization Discrepancy
Earlier reports noted that some incidents possessing raw event child records were displayed in certain list endpoints with `event_count = 0`.
- **Root Cause:** In `AnalystReviewService.get_pending_reviews`, line 117 accessed child events using `evts = inc.__dict__.get("events") or []`. Because SQLAlchemy's `selectinload` populates relationships through instance descriptors, direct `__dict__` dictionary lookups bypassed the descriptor and returned empty lists if the internal state was un-flushed.
- **Remediation Implemented:** Line 117 was updated to `evts = getattr(inc, "events", None) or []`. This guarantees that the relationship descriptor is evaluated, returning accurate `raw_events_count` for all incidents.

---

## 4. Authoritative FortiSIEM Rule Semantics

### 4.1 Rule Name & Description
- **Rule Name:** `Website access policy violation: Same Source and Destination`
- **Rule Code:** `PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST`
- **Canonical Rule UUID:** `7bd13e89-0828-48e6-8cf5-f3cbf12d438c`

### 4.2 Correlation Logic: What "Same Source and Destination" Means
A common misconception is that "Same Source and Destination" implies that the Source IP equals the Destination IP ($SrcIP = DstIP$). **This is incorrect.**
In FortiSIEM correlation syntax, this rule triggers when multiple firewall or UTM web-filtering events occur involving the **same client source device communicating with the same destination web service or domain** within a tight correlation window:
- An internal client (`srcip`) establishes a session to an external web host or domain (`dstip` / `destName`).
- The FortiGate UTM web filter logs an access event with an associated web category (e.g., `Social.Networking`, `Gambling`, `Information.Technology`, `Advertising`).
- The firewall policy action records whether the session was `BLOCKED`, `PASSED`, or `DROPPED`.

### 4.3 Policy Violation vs Automated Blocking
- **Crucial Invariant:** Not every blocked web request is an actionable corporate policy violation. For example, background telemetry blocked by ad-blocker filters or CDN static assets do not necessarily warrant SOC incident escalation.
- **Analyst Role:** The human analyst must review the full URI, domain reputation, user context, and organizational acceptable-use policies to determine whether the event is a genuine **True Positive** or benign background **False Positive**.
