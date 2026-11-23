# AIS 2.2 Report 03: Historical Dataset Readiness

**Project:** Verdictum AI  
**Organization:** Wysetek Systems Technologists Pvt. Ltd.  
**Phase:** AIS 2.2 (Core Verdict Accuracy Baseline & Real LLM Benchmark)  
**Date:** 2026-11-23  
**Status:** COMPLETE & AUDITED  

---

## 1. Dataset Population Overview

An audit of available historical FortiSIEM incident datasets was conducted across three distinct storage tiers:
1. **Production Operational Inventory (Server 1 PostgreSQL):** 35 operational incidents for target rule `Heavy TCP Host Scan On Fixed Port`.
2. **Cumulative Historical Reviews (Server 1 PostgreSQL):** 65 verified analyst reviews for target rule `Heavy TCP Host Scan On Fixed Port`.
3. **Historical Raw Log Fixtures (`fixtures/Incident json.zip`):** 20 comprehensive FortiSIEM incident JSON payloads with full event structures and closure histories.

---

## 2. Target Rule: One-Class Dataset Characterization

Target Detection Rule:
- **Rule Name:** Heavy TCP Host Scan On Fixed Port
- **Canonical UUID:** `40498741-ee6b-4a71-9101-0d6d3f77154c`
- **FortiSIEM Event Type:** `PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`

### Authoritative Distribution

```
+-------------------------------------------------------------------------------+
| POPULATION COHORT                  | TOTAL | VERIFIED FP | VERIFIED TP | RATIO |
+------------------------------------+-------+-------------+-------------+-------+
| Operational Incident Inventory     |   35  |     33      |      0      | 0% TP |
| Cumulative Historical Reviews      |   65  |     65      |      0      | 0% TP |
| Evaluated Operational Verdicts     |   33  |     33      |      0      | 0% TP |
+-------------------------------------------------------------------------------+
```

### Empirical Ground Truth Analysis
1. Every reviewed historical incident for this rule in the production environment corresponds to authorized security scanners, vulnerability assessments, or internal IT discovery tools hitting fixed ports (e.g. port 80, 443, 8080).
2. Human analysts independently classified 100% of these incidents as False Positives (`VERIFIED_FP`).
3. In actual operational security telemetry, zero confirmed True Positive malicious attacks have been recorded for this specific rule in this environment.
4. **Conclusion:** The target rule represents an authentic **One-Class Dataset**.

---

## 3. Multi-Rule Dataset Audit (`fixtures/Incident json.zip`)

To satisfy the Stage B class-balance requirement without fabricating synthetic data for the target rule, an audit of other detection rules in `fixtures/Incident json.zip` was performed:

| Incident ID | Rule Name | Events | Verified Ground Truth | Analyst Rationale / Provenance |
|---|---|---|---|---|
| `165233` | CrowdStrike Falcon Malicious Activity | 8 | `VERIFIED_TP` | Confirmed lateral movement, isolated host, ticket #SEC-8911 |
| `165234` | CrowdStrike Falcon Malicious Activity | 12 | `VERIFIED_TP` | Cobalt Strike beaconing pattern confirmed |
| `165235` | CrowdStrike Falcon Malicious Activity | 6 | `VERIFIED_TP` | Credential dumping via mimikatz confirmed |
| `165236` | CrowdStrike Falcon Malicious Activity | 15 | `VERIFIED_TP` | Ransomware staging detected and blocked |
| `172101` | Prisma SASE Suspicious Inbound Connection | 4 | `VERIFIED_FP` | Authorized vendor VPN connection from known IP |
| `172102` | Prisma SASE Suspicious Inbound Connection | 5 | `VERIFIED_FP` | Scheduled maintenance failover test |
| Other (14) | Various FortiSIEM Rules | 1-22 | `UNVERIFIED` | Auto-cleared by bot/system or lacked written rationale |

**Total in Zip Fixtures:**
- 20 Incidents evaluated.
- 4 Verified True Positives (`VERIFIED_TP`).
- 2 Verified False Positives (`VERIFIED_FP`).
- 14 Unverified (`UNVERIFIED` - excluded from primary ground truth).

---

## 4. Evaluation Tracks Architecture

To ensure strict scientific integrity, two evaluation tracks are enforced:

### Track A — Real Historical Benchmark (Authoritative)
- Operates exclusively on real historical security telemetry and verified analyst decisions.
- Evaluates the target Heavy TCP Host Scan rule against its 35 operational incidents and 65 historical reviews.
- Maintains honest, transparent reporting: because True Positives = 0, TP Recall and Balanced Accuracy are reported as `NOT_MEASURABLE` (null). Zero fabrication is permitted.

### Track B — Controlled / Diagnostic Benchmark (Supplementary)
- Evaluates multi-rule incidents (e.g. CrowdStrike and Prisma SASE) to test model behavior on genuine multi-class distributions.
- Demonstrates that the model and pipeline can identify True Positives when presented with verified attack telemetry.
- **Strict Isolation:** Track B diagnostic results are never merged into target-rule production metrics or learning profiles.
