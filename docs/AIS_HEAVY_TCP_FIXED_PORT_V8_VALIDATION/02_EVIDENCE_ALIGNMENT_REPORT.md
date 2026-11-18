# 02 — Evidence Alignment & Telemetry Quality Report

**Target Rule:** `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT` / `40498741-ee6b-4a71-9101-0d6d3f77154c`)
**Implemented In:** [evidence_requirement_mapper.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/evidence_requirement_mapper.py), [evidence_normalization_service.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/evidence_normalization_service.py), [verdict_pipeline.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/verdict_pipeline.py), [evidence_compaction_service.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/evidence_compaction_service.py), [token_budget_service.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/token_budget_service.py)

---

## 1. Field-by-Field Telemetry Alignment Matrix (Audited Across All 69 Incidents / 3,197 Raw Events)

| Canonical Field | Exists in Raw FortiGate Logs? | Normalized & Mapped? | Survives 4,096 Compaction? | Classification for FortiGate `NETWORK_SCAN` | V8 Engineering Change |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **`network.source_ip`** | Yes (`srcip` / `incidentSrc`) | Yes | **100%** (6/6 v7 & v8) | **`CORE` (Required)** | Kept in 8-field ultra-essential scan core. |
| **`network.destination_port`** | Yes (`dstport` / `incidentTarget`) | Yes | **100%** (6/6 v7 & v8) | **`CORE` (Required)** | Kept in 8-field ultra-essential scan core. |
| **`security.event_type`** | Yes (incident header) | Yes | **100%** (6/6 v7 & v8) | **`CORE` (Required)** | Priority-packed immediately after 8-field scan core. |
| **`event.timestamp`** | Yes (`event_receive_time`) | Yes | **100%** (6/6 v7 & v8 — fixed!) | **`CORE` (Required)** | **Fixed V7 drop:** now priority `#0` in secondary packing + slimmed noisy `events[0]` upfront. |
| **`network.protocol`** | Yes (`proto=6` / `6 (TCP)` on rich logs) | Yes | **100%** (5/5 rich v7 & v8 — fixed!) | **`CONDITIONAL`** (when raw logs exist) | **Fixed V7 drop:** now priority `#1` in secondary packing. |
| **`scan.raw_events_count`** | Derived deterministically (`len(evts)`) | Yes | **100%** (6/6 v7 & v8) | **`CONDITIONAL`** (always emitted for scan rules) | Registered in `EvidenceRequirementMapper` + kept in 8-field core (`0` on header-only `#176122`). |
| **`scan.connection_count`** | Yes (`incidentDetail.incidentCount`) | Yes | **100%** (6/6 v7 & v8) | **`CONDITIONAL`** | Kept in 8-field ultra-essential scan core. |
| **`scan.unique_destination_hosts`** | Derived from distinct `dstip` | Yes | **100%** (5/5 rich v7 & v8) | **`CONDITIONAL`** | Registered in contract + kept in 8-field core. |
| **`scan.destination_scope`** | Derived (`internal=X, external=Y`) | Yes | **100%** (5/5 rich v7 & v8) | **`CONDITIONAL`** | Registered in contract + kept in 8-field core. |
| **`scan.firewall_action_summary`** | Derived from `action` counts | Yes | **100%** (5/5 rich v7 & v8) | **`CONDITIONAL`** | Registered in contract + kept in 8-field core. |
| **`scan.tcp_behavior_summary`** | Derived from `sentbyte`/`rcvdbyte`/`action` | Yes | **100%** (5/5 rich v7 & v8) | **`CONDITIONAL`** | **Enhanced:** now includes deterministic `appctrl_pass_events` count for `FortiGate-appctrl-ips-pass` logs (`63/100` on `#167157`), with zero fabrication. |
| **`scan.policy_and_service`** | Derived from `policyname` / `service` | Yes | 5/5 (v7), 1/5 (v8 under 4,096 ceiling) | **`CONDITIONAL`** | Registered in contract; priority `#3` in secondary packing (note: 4,096 context ceiling still tight when v8 system prompt is +75 tokens longer). |
| **`scan.window_seconds` & `scan.rate_per_second`** | Derived from min/max event timestamps | Yes | 5/5 (v7), 0/5 (v8 under 4,096 ceiling) | **`CONDITIONAL`** | Registered in contract; priority `#4`/`#5` (fits cleanly if Server 2 context >= `6,144`–`8,192`). |
| **`network.destination_ip` & `network.destination_ip_list`** | Yes (`dstip` across raw logs) | Yes | Summarized via `unique_destination_hosts` + `destination_scope` | **`CONDITIONAL`** | Kept out of 8-field core to avoid 100-IP token explosion; sample 5 IPs packed when budget permits. |
| **`network.tcp_flags`** | **NO (`0 / 3,197` FortiGate events)** | Unavailable in source | N/A (never invented) | **`OPTIONAL` / UNAVAILABLE for FortiGate** | **Fixed V7 defect:** downgraded from `CONDITIONAL` to `OPTIONAL` with explicit instruction never to infer unobserved TCP flags and never to abstain solely for their absence. |
| **`detection.threshold`** | Rule XML metadata (NOT event field) | Rule Section 3 | N/A | **`RULE_METADATA`** | **Fixed V7 defect:** reclassified from `CORE [CRITICAL]` to `RULE_METADATA` and excluded from `evidence_contract.required_fields`. |

---

## 2. Structured Evidence Contract Wire Format (`verdict_pipeline.py`)

Previously, `verdict_pipeline.py` sent one flat list `evidence_contract.required_fields` containing all `11` fields (including `network.tcp_flags` and `detection.threshold`). In commit `10021a3f`, it now sends three explicit tiers:
- `required_fields`: `["security.event_type", "event.timestamp", "network.source_ip", "network.destination_port"]` (true mandatory CORE telemetry only).
- `conditional_fields`: `scan.*` aggregates, `network.destination_ip`, `network.destination_ip_list`, `network.protocol`, `scan.rate_per_second`, `scan.connection_count`.
- `optional_fields`: `["network.tcp_flags"]` (explicitly optional; never triggers false abstention).

---

## 3. Preserved Protections & Reusable Architecture

- **Zero Fabrication:** Unobserved TCP flags are never inferred; `appctrl_pass_events` is counted strictly from `action == "pass"` / `appctrl` events lacking `sentbyte`/`rcvdbyte`.
- **Header-Only Protection Preserved:** Header-only incidents (`scan.raw_events_count == 0`, e.g. `#176122`) continue to abstain cleanly (`REQUIRES_ATTENTION`, `1/1` grounded claim).
- **Reusable Across FortiSIEM Rules:** Structured `evidence_contract` tiers (`required_fields` / `conditional_fields` / `optional_fields`), `RULE_METADATA` classification for `detection.threshold`, `events[0]` upfront noise slimming for aggregated scans, and `appctrl_pass_events` apply cleanly to all `NETWORK_SCAN` and FortiGate rules.
