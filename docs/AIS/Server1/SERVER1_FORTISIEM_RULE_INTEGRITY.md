# Verdictum AI — FortiSIEM Rule Integrity & G1 Validation Report

**Report Date:** 2026-11-12T04:30:00Z  
**Target Scope:** All 35 Detection Rules in PostgreSQL (`rules.pattern_logic`)  
**Validator Engine:** `RuleIntelligenceAnalyzer` & `PolicyQualityValidator` (Gate 1 Integrity)  
**Integrity Outcome:** **8 Rules VERIFIED, 27 Rules INCOMPLETE (XML Export Required)**

---

## 1. Rule Definition Integrity Architecture (Gate 1)

Gate 1 (`G1_RULE_INTEGRITY`) enforces that an AI triage policy must be anchored to authoritative vendor correlation logic rather than inferred runtime telemetry.

```
+-----------------------------------------------------------------------------------+
| Gate 1 Rule Definition Integrity Spectrum                                         |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  [Tier A: Authoritative SIEM XML]  --->  [VERIFIED STATUS]                        |
|  - Complete vendor XML conditions        - Authoritative thresholds & windows     |
|  - Vendor Boolean expressions (AND/OR)   - Deterministic grouping keys            |
|  - Explicit grouping & time windows      - Eligible for G1 10.0 / 10.0 Pass       |
|                                                                                   |
|  [Tier B: Incident-Derived Metadata]  ->  [INCOMPLETE STATUS]                     |
|  - Derived from cache-miss sync          - Missing vendor correlation XML         |
|  - Contains incidentCount, sentBytes64   - Fictitious/heuristic thresholds        |
|  - Runtime counters only                 - BLOCKS policy autonomous approval      |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

### Mandatory Non-Substitution Constraint
> [!CAUTION]
> Runtime incident counters (such as `incidentCount`, `incidentDetail`, or observed incident packet sizes) **MUST NEVER** be substituted as authoritative correlation thresholds. Inferred counters lead to brittle policies and hallucinations in LLM reasoning.

---

## 2. Comprehensive Per-Rule Integrity Analysis

All 35 detection rules were analyzed for definition status, source provenance, authoritative conditions, and threshold presence:

| # | Rule Identifier | Rule Name | Provenance | Def Status | Threshold | G1 Result |
| :-: | :--- | :--- | :--- | :--- | :-: | :-: |
| 1 | `PH_RULE_CS_SUSPICIOUS_ACTIVITY` | Crowdstrike: Suspicious Activity | `VENDOR_RULE_FILE` | **VERIFIED** | 1.0 | **PASSED** |
| 2 | `PH_RULE_UNAUTH_DNS_QUERY` | Unauthorized DNS Query | `VENDOR_RULE_FILE` | INCOMPLETE | None | WARNING |
| 3 | `PH_RULE_EXCESS_DENY_EXT_COUNTRY` | Excessive Denied from Ext Country | `VENDOR_RULE_FILE` | INCOMPLETE | None | WARNING |
| 4 | `PH_RULE_EXCESS_DENY_SRC` | Excessive Denied from Source IP | `AUTO_SYNCED_FROM_INCIDENT` | INCOMPLETE | None | WARNING |
| 5 | `PH_RULE_EXCESS_DNS_QUERY` | Excessive DNS Queries | `VENDOR_RULE_FILE` | INCOMPLETE | None | WARNING |
| 6 | `PH_RULE_FGT_Config_Change` | FortiGate Configuration Change | `VENDOR_RULE_FILE` | **VERIFIED** | None | **PASSED** |
| 7 | `PH_RULE_FSM_AGENT_OP_ERROR` | FortiSOC Collector Error | `AUTO_SYNCED_FROM_INCIDENT` | INCOMPLETE | None | WARNING |
| 8 | `PH_RULE_HEAVY_TCP_HOST_SCAN` | Heavy TCP Host Scan | `VENDOR_RULE_FILE` | INCOMPLETE | None | WARNING |
| 9 | `PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT` | Heavy TCP Host Scan Fixed Port | `VENDOR_RULE_FILE` | INCOMPLETE | None | WARNING |
| 10 | `PH_RULE_LARGE_OUTBOUND_XFER` | Large Outbound Data Transfer | `AUTO_SYNCED_FROM_INCIDENT` | INCOMPLETE | None | WARNING |
| 11 | `PH_RULE_LARGE_OUTBOUND_XFER_OUTSIDE_COUNTRY` | Large Outbound Transfer Foreign | `AUTO_SYNCED_FROM_INCIDENT` | INCOMPLETE | None | WARNING |
| 12 | `PH_RULE_EXCESS_FAILED_LOGON_2_NET_DEV` | Multiple Login Failures: Net Dev | `AUTO_SYNCED_FROM_INCIDENT` | INCOMPLETE | None | WARNING |
| 13 | `PH_RULE_NO_LOGS_FROM_DEVICE` | No Logs From Device | `VENDOR_RULE_FILE` | **VERIFIED** | None | **PASSED** |
| 14 | `No_logs_from_a_device_testing` | No Logs From Device (Testing) | `VENDOR_RULE_FILE` | **VERIFIED** | None | **PASSED** |
| 15 | `PH_Rule_MISP_MalwareIP_Inbound` | Permitted Traffic MISP Inbound | `VENDOR_RULE_FILE` | INCOMPLETE | None | WARNING |
| 16 | `Permitted_Traffic_from_MISP_Malware_IP_List_3_27_2026` | Permitted MISP Malware IP List | `VENDOR_RULE_FILE` | INCOMPLETE | None | WARNING |
| 17 | `Prisma_SASE_Suspicious_File_Threat_Detection_` | Prisma SASE Suspicious File Threat | `VENDOR_RULE_FILE` | **VERIFIED** | None | **PASSED** |
| 18 | `PH_RULE_NON_RESPONSIVE_SERVER` | Server Down: No Ping Response | `AUTO_SYNCED_FROM_INCIDENT` | INCOMPLETE | None | WARNING |
| 19 | `PH_RULE_VPN_LOGON_SUCCESS_OUTSIDE_COUNTRY` | Successful VPN from Foreign Country | `VENDOR_RULE_FILE` | INCOMPLETE | None | WARNING |
| 20 | `PH_RULE_ANOMALY_DECREASING_EPS` | Traffic Anomaly: Decreasing EPS | `AUTO_SYNCED_FROM_INCIDENT` | INCOMPLETE | None | WARNING |
| 21 | `PH_RULE_ANOMALY_DNS_DEST` | Traffic Anomaly: DNS Destination | `VENDOR_RULE_FILE` | INCOMPLETE | None | WARNING |
| 22 | `PH_RULE_ANOMALY_TRAFFIC_DENIED_INBOUND_PORT` | Traffic Anomaly: Denied Inbound | `VENDOR_RULE_FILE` | **VERIFIED** | None | **PASSED** |
| 23 | `PH_RULE_ANOMALY_TRAFFIC_DENIED_OUTBOUND_PORT` | Traffic Anomaly: Denied Outbound | `VENDOR_RULE_FILE` | **VERIFIED** | None | **PASSED** |
| 24 | `PH_RULE_ANOMALY_SUCCESSFUL_LOGON` | Traffic Anomaly: Successful Logon | `VENDOR_RULE_FILE` | **VERIFIED** | None | **PASSED** |
| 25 | `PH_RULE_USER_MON_SUDDEN_LOGIN_DISTRIBUTION_CHANGE` | User Login Distribution Change | `AUTO_SYNCED_FROM_INCIDENT` | INCOMPLETE | None | WARNING |
| 26 | `PH_Rule_MISP_MalwareIP_Outbound` | Traffic to MISP Malware Outbound | `VENDOR_RULE_FILE` | INCOMPLETE | None | WARNING |
| 27 | `PH_RULE_WEB_POL_VIOLATION_MANY_SRC_SAME_DEST` | Web Policy: Many-to-One | `VENDOR_RULE_FILE` | INCOMPLETE | None | WARNING |
| 28 | `PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST` | Web Policy: One-to-One | `VENDOR_RULE_FILE` | **VERIFIED** | None | **PASSED** |
| 29 | `PH_RULE_WEB_POL_VIOLATION_SAME_SRC_MANY_CATEGORIES` | Web Policy: Many Categories | `VENDOR_RULE_FILE` | INCOMPLETE | None | WARNING |
| 30 | `PH_RULE_DPAPI_Domain_Master_Key_Backup_Attempt` | Win: DPAPI Master Key Backup | `VENDOR_RULE_FILE` | INCOMPLETE | None | WARNING |
| 31 | `PH_RULE_WIN_GROUP_CHANGED` | Win: Group Changed | `VENDOR_RULE_FILE` | INCOMPLETE | None | WARNING |
| 32 | `PH_RULE_Locked_Workstation` | Win: Workstation Locked | `VENDOR_RULE_FILE` | INCOMPLETE | None | WARNING |
| 33 | `PH_RULE_WIN_SEC_LOG_SVC_SHUTDOWN_NO_RESTART` | Windows Log Svc Shutdown | `VENDOR_RULE_FILE` | INCOMPLETE | None | WARNING |
| 34 | `PH_RULE_Uncommon_Outbound_Kerberos_Connection_Security` | Windows Kerberos Anomaly | `VENDOR_RULE_FILE` | INCOMPLETE | None | WARNING |
| 35 | `PH_RULE_Windows_Update_Error` | Windows Update Error | `VENDOR_RULE_FILE` | INCOMPLETE | None | WARNING |

---

## 3. High-Priority Rules Requiring Authoritative XML Ingestion

27 rules are currently classified as `INCOMPLETE`. To achieve full G1 certification for autonomous operations, the following rules require authoritative XML exports from the FortiSIEM Supervisor:

1. **`PH_RULE_HEAVY_TCP_HOST_SCAN`:** Needs authoritative port scanning threshold (e.g. `dstPortCount >= 20 within 60s`).
2. **`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`:** Needs authoritative host scanning threshold on fixed destination port.
3. **`PH_RULE_EXCESS_DNS_QUERY`:** Needs authoritative query rate and domain diversity criteria.
4. **`PH_RULE_EXCESS_DENY_EXT_COUNTRY`:** Needs firewall deny threshold parameters.
5. **`PH_Rule_MISP_MalwareIP_Inbound` & `Outbound`:** Needs threat-feed matching criteria.

---

## 4. FortiSIEM Authoritative XML Export & Import Procedure

When administrative access to the FortiSIEM Supervisor is available:

### Step 1: Export Rule XML from FortiSIEM Supervisor
1. Log into FortiSIEM Web GUI -> **Analytics** -> **Rules**.
2. Locate the target rule (e.g., `Heavy TCP Host Scan`).
3. Click **Export** -> **XML Format**.
4. Save the resulting XML document (contains `<pattern>`, `<filter>`, `<groupBy>`, and `<window>`).

### Step 2: Import into Verdictum AI
Use the FortiSIEM Rule Import endpoint:
```http
POST /api/fortisiem/rules/import-xml
Content-Type: application/xml

<ruleDefinition name="Heavy TCP Host Scan">
  ...
</ruleDefinition>
```
The backend parser (`RuleParser`) automatically ingests the authoritative expressions into `Rule.pattern_logic`, upgrading the definition status to `VERIFIED` and unlocking G1 10.0 full pass.
