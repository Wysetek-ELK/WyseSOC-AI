# 03 — Fresh Incident Dataset Verification & Reconciliation
**Target Rule:** `Website access policy violation: Same Source and Destination`  
**Dataset Evaluation Window:** November 19, 2026 (Post-Purge Cohort)  
**Dataset Source:** FortiSIEM Supervisor (`172.26.26.31`) synced to Verdictum Core (`172.26.41.240`)  

---

## 1. Context of the Post-Purge Evaluation Dataset

Prior to this onboarding execution, the FortiSIEM administrator purged historical test and operational incidents. The current incident repository represents a **fresh evaluation cohort** generated under real network conditions across internal client subnets.

In accordance with Phase 2 safeguards:
- Zero historical incidents were restored from stale archives.
- No historical analyst resolutions were fabricated or assumed.
- The dataset was ingested through the supported FortiSIEM Continuous Sync pipeline, preserving original incident IDs, event timestamps, reporting devices, and tenant boundaries.

---

## 2. Quantitative Inventory & Reconciliation

A comprehensive audit of the Verdictum AI PostgreSQL database and the FortiSIEM supervisor verified the following inventory:

| Metric | Verified Value | Notes |
| :--- | :--- | :--- |
| **Total Ingested SIEM Incidents** | **210** | Continuous synchronization active |
| **Target Rule Incidents** | **210** (100%) | All matching `PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST` |
| **Incident Status Distribution** | 210 Open (100%) | Zero closed, zero auto-resolved |
| **Historical Ground-Truth Labels** | **0** (0.0%) | Completely clean baseline; zero prior human verdicts |
| **Existing Human Reviews** | **0** (0.0%) | Ready for double-blind human pilot |
| **Tenant / Customer Distribution** | - `HOST-45.64.199.219` (GDC_NOC): 102<br>- `HOST-172.26.31.254` (Demo-SOC): 82<br>- `HOST-172.27.31.254` (Demo-SOC): 26 | Proper multi-tenant separation maintained |

---

## 3. Raw Event Completeness & Telemetry Stratification

Each incident was inspected for raw event availability from the FortiGate UTM log stream:

```
Total Incidents: 210
├── Rich Raw Events (≥ 1 raw log): 184 incidents (87.6%)
│     ├── 1 event:   42 incidents (20.0%)
│     ├── 2 events:  26 incidents (12.4%)
│     ├── 3 events:  18 incidents (8.6%)
│     ├── 4–10 events: 28 incidents (13.3%)
│     ├── 11–50 events: 41 incidents (19.5%)
│     └── 51–100 events: 29 incidents (13.8%)
│
└── Header-Only Alerts (0 raw logs): 26 incidents (12.4%)
      └── Correlated alert headers without captured UTM event payloads
```

### Telemetry Quality Classification

1. **RICH_EVIDENCE (87.6% of cohort):** Contains complete FortiGate UTM event logs, including `srcip`, `dstip`, `destName`, `user`, `group`, `webCategory`, `action`, `policyid`, and `service`. Sufficient for thorough LLM policy evaluation and grounding verification.
2. **HEADER_ONLY (12.4% of cohort):** Incidents where FortiSIEM generated the correlation alert header, but raw child event logs were either dropped, not yet indexed, or aged out in the collector. Under AIS 2.0 guardrails, header-only incidents force **Safe Model Abstention (`REQUIRES_ATTENTION`)** because critical policy attributes cannot be verified without raw logs.

---

## 4. Reporting Device and Network Topology Breakdown

Telemetry originates from three primary FortiGate firewall clusters guarding corporate subnets:

| Reporting Device | IP Subnet / Cluster | Incident Count | Primary Log Types |
| :--- | :--- | :--- | :--- |
| **HOST-45.64.199.219** | `172.25.x.x` (Public Gateway / DMZ) | 102 | `FortiGate-web-ftgd-cat-blk`, `webfilter` |
| **HOST-172.26.31.254** | `172.26.x.x` (Headquarters LAN) | 82 | `FortiGate-web-ftgd-cat-blk`, `appctrl` |
| **HOST-172.27.31.254** | `172.27.x.x` (Regional Office LAN) | 26 | `FortiGate-web-ftgd-cat-blk` |

---

## 5. Dataset Provenance & Safeguards Summary

1. **No Duplicate Ingestion:** All 210 incidents have unique FortiSIEM `incident_id` values and unique system UUIDs.
2. **Temporal Integrity:** Ingestion timestamps strictly align with FortiSIEM event occurrence timestamps (`created_at_epoch`).
3. **Ground Truth Purity:** Zero synthetic labels were injected. Accuracy metrics report `NOT MEASURABLE` until verified SOC analyst determinations are recorded.
