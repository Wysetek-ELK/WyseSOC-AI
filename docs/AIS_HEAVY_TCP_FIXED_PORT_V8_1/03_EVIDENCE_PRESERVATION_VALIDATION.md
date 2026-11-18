# 03 — Evidence Preservation & Compaction Integrity Validation

**Target Rule:** `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`, UUID `40498741-ee6b-4a71-9101-0d6d3f77154c`)
**Authoritative FortiSIEM Trigger:** `COUNT(DISTINCT destIpAddr) >= 100 AND destIpPort IS NOT NULL AND ipProto = 6` | Window: `180s` | GroupBy: `srcIpAddr,destIpPort`
**Live Run Verified:** V8.1 Re-Benchmark `run_id = a95cd268-7c2b-43c6-8355-1dd27770d6bf` (`8120d882b`)

---

## 1. Trigger vs. Full-Window Metadata vs. Sample Statistics Distinction

Implemented deterministically in [evidence_normalization_service.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/evidence_normalization_service.py):
- **Authoritative Rule Trigger:** Preserved in Section 3 (`COUNT(DISTINCT destIpAddr) >= 100`, `180s`, `ipProto = 6`).
- **Full-Window Aggregation Metadata:** Preserved via `scan.connection_count` (`incidentDetail.incidentCount`, e.g., `103` on `#176011`, `112` on `#167157`).
- **Sampled FortiGate Event Statistics:** Explicitly tagged via **`scan.sample_context`** (e.g., `sampled_events=100, sample_unique_dst_hosts=75, trigger_count=103 (subset of SIEM trigger)`), alongside `scan.raw_events_count`, `scan.unique_destination_hosts`, `scan.destination_scope`, `scan.tcp_behavior_summary` (including `appctrl_pass_events`), `scan.firewall_action_summary`, `scan.policy_and_service`, `scan.window_seconds`, and `scan.rate_per_second`.

---

## 2. Mandatory Field-Preservation Matrix (All 6 Live V8.1 Benchmarked Incidents)

`Available in source → Normalized → Included in prompt → Used in verdict → Correctly cited`

### A. Rich-Log Incidents (`#176011`, `#175129`, `#164575`, `#167157`, `#173449` — 100 Raw FortiGate Events Each)

| Evidence Field | Available in Source? | Normalized? | Included in V8.1 Prompt (`5/5` Rich)? | Used / Cited by `Qwen2.5-7B`? | Traceable Notes |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **`network.source_ip`** | Yes (`5/5`) | Yes (`5/5`) | **Yes (`5/5` = `100%`)** | Cited accurately on `#176011`, `#175129`, `#164575` | Exact `EV-*-TOP-network_source_ip` |
| **`network.destination_port`** | Yes (`443`, `5/5`) | Yes (`5/5`) | **Yes (`5/5` = `100%`)** | Used in all `5/5` rationales | Exact port `443` preserved |
| **`network.protocol`** | Yes (`TCP/6`, `5/5`) | Yes (`5/5`) | **Yes (`5/5` = `100%`)** | Used (`TCP` scan) | Preserved via secondary priority `#2` |
| **`event.timestamp`** | Yes (`5/5`) | Yes (`5/5`) | **Yes (`5/5` = `100%`)** | Available in prompt | Preserved via secondary priority `#1` |
| **`scan.raw_events_count`** | Derived (`100`, `5/5`) | Yes (`5/5`) | **Yes (`5/5` = `100%`)** | Cited accurately (`0` "zero raw events" hallucinations) | Exact `EV-*-SCAN_SUMMARY-scan_raw_events_count` |
| **`scan.connection_count`** | Yes (`103–113`, `5/5`) | Yes (`5/5`) | **Yes (`5/5` = `100%`)** | Available in prompt | Full-window SIEM count |
| **`scan.unique_destination_hosts`** | Derived (`32–75`, `5/5`) | Yes (`5/5`) | **Yes (`5/5` = `100%`)** | Cited accurately (`75`, `49`, `53`, `60`) | Sample unique host count |
| **`scan.sample_context`** | Derived (`5/5`) | Yes (`5/5`) | **Yes (`5/5` = `100%`)** | Eliminated `#167157` "below threshold" misinterpretation | Explicitly distinguishes 100-event sample vs SIEM trigger |
| **`scan.destination_scope`** | Derived (`5/5`) | Yes (`5/5`) | **Yes (`5/5` = `100%`)** | Cited accurately (`internal=0, external=75` on `#176011`; mixed on `#167157`) | Exact `EV-*-SCAN_SUMMARY-scan_destination_scope` |
| **`scan.firewall_action_summary`** | Derived (`5/5`) | Yes (`5/5`) | **Yes (`5/5` = `100%`)** | Used in reasoning (`client-rst`, `close`, `pass`) | Exact FortiGate action breakdown |
| **`scan.tcp_behavior_summary`** | Derived (`5/5`) | Yes (`5/5`) | **Yes (`5/5` = `100%`)** | **Model cited field, but inverted `unanswered_probes=0` on 4 runs**; validator caught `#164575` (`EVIDENCE_VALUE_MISMATCH`) | Proves prompt delivery was `100%` accurate; error was model-side semantic inversion |
| **`scan.policy_and_service`** | Yes (`5/5`) | Yes (`5/5`) | **Yes (`5/5` = `100%` — fixed from `1/5` in V8!)** | Available in prompt (`Cybersecurity/Browsing`, `Cyble-Internet-Access/HTTPS`, etc.) | Priority `#0` fix verified live across all `5/5` rich logs |
| **`scan.window_seconds`** | Derived (`108–179s`, `5/5`) | Yes (`5/5`) | **Yes (`5/5` = `100%`)** | Cited verbatim (`108s`, `141s`, `150s`, `179s`) | Preserved via secondary priority `#4` |
| **`scan.rate_per_second`** | Derived (`5/5`) | Yes (`5/5`) | **Yes (`5/5` = `100%`)** | Available in prompt | Preserved via secondary priority `#5` |
| **`network.destination_ip_list`** | Yes (`5/5`) | Yes (`5/5`) | Omitted under `4,096` (`#6` priority) | Traceable reason: summarized by `scan.unique_destination_hosts` + `scan.destination_scope` to protect `768` completion headroom | Fits immediately under `8,192` extended context (`test_11` verified) |
| **`network.tcp_flags`** | **No (`0/3,197` FortiGate logs)** | Unavailable | Not synthesized (marked `OPTIONAL`) | `0/6` runs complained about missing `network.tcp_flags` | Never invented |

### B. Header-Only Control Incident (`#176122` — `0` Raw FortiGate Events)

- **Available & Preserved (`10/10` = `100%`):** `event.timestamp`, `network.source_ip` (`172.25.24.153`), `network.destination_port` (`443`), `security.event_type`, `security.alert_title`, `scan.connection_count` (`102`), `telemetry.incidentrptip`, `mitre.technique`, `mitre.tactic`, `scan.raw_events_count` (`0`).
- **Unavailable in Source (`6` fields):** `network.protocol`, `scan.unique_destination_hosts`, `scan.destination_scope`, `scan.firewall_action_summary`, `scan.tcp_behavior_summary`, `scan.policy_and_service`.
- **Outcome:** Model safely abstained (`REQUIRES_ATTENTION`, `confidence: 0.0`, `262/768` tokens, `reason: "Insufficient evidence due to missing raw logs and scan details."`).
