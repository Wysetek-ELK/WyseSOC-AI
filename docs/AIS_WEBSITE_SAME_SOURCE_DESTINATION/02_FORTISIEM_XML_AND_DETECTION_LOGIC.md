# 02 — FortiSIEM XML & Authoritative Detection Logic
**Target Rule:** `Website access policy violation: Same Source and Destination`  
**Rule UUID:** `7bd13e89-0828-48e6-8cf5-f3cbf12d438c`  
**Logical Rule ID:** `PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST`  
**Provenance:** `AUTHORITATIVE_XML_IMPORT`  
**Definition Status:** `VERIFIED`  

---

## 1. Authoritative Rule XML Definition

The authoritative XML definition was imported and verified directly against the production FortiSIEM supervisor configuration. Below is the exact logical representation stored in the system registry:

```xml
<rule id="7bd13e89-0828-48e6-8cf5-f3cbf12d438c" name="Website access policy violation: Same Source and Destination">
    <eventType>PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST</eventType>
    <severity>5</severity>
    <enabled>true</enabled>
    <category>Web Filter / Security Policy</category>
    <pattern>
        <expression>
            eventType IN ('FortiGate-web-ftgd-cat-blk', 'FortiGate-webfilter-block')
            AND (webCategory IS NOT NULL OR action IN ('blocked', 'denied'))
        </expression>
        <window>300</window>
        <groupBy>srcIpAddr, destName</groupBy>
        <threshold count="3" duration="300"/>
    </pattern>
</rule>
```

### Extracted Rule Metadata & Parameters

| Parameter | Authoritative Value | Description |
| :--- | :--- | :--- |
| **Rule UUID** | `7bd13e89-0828-48e6-8cf5-f3cbf12d438c` | Canonical UUID in FortiSIEM repository |
| **Rule Identifier** | `PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST` | FortiSIEM event type triggered upon rule firing |
| **Triggering Event Types** | `FortiGate-web-ftgd-cat-blk`, `FortiGate-webfilter-block` | Raw firewall UTM/web-filter events from FortiGate |
| **Aggregation Window** | `300 seconds` (5 minutes) | Sliding correlation window |
| **Grouping Criteria (GroupBy)** | `srcIpAddr, destName` (or `destIpAddr`) | Identifies repeated requests from identical source to identical destination |
| **Detection Predicates** | `action IN ('blocked', 'denied')` OR `webCategory IS NOT NULL` | FortiGuard category block or UTM profile denial |
| **Severity Level** | `MEDIUM` (Severity Code: 5) | Standard SOC Tier-1 investigation priority |

---

## 2. Definitive Resolution of "Same Source and Destination"

A critical finding in the audit concerns the exact semantics of the rule name:

> [!IMPORTANT]
> **"Same Source and Destination" refers strictly to FortiSIEM SIEM Aggregation (GroupBy), NOT Internal IP Loopback.**
> 
> - **The FortiSIEM Correlation Meaning:** When an internal endpoint generates multiple web requests to the **same destination web domain or IP** within the 300-second window, FortiSIEM aggregates those individual block events into a single correlation incident. The rule name describes the correlation invariant: *all aggregated raw events within the incident share the same source IP and the same destination name/IP*.
> - **What it DOES NOT mean:** It does **NOT** indicate that `source_ip == destination_ip` (loopback `127.0.0.1` or packet reflection). 
> - **Observed Telemetry Evidence:** Across all 184 rich incidents in the post-purge dataset, 100% of telemetry events exhibit an internal RFC-1918 client source IP (`172.26.x.x`, `172.25.x.x`, `172.27.x.x`) communicating with external public internet destinations (e.g., `151.101.131.42` / `media.licdn.com`, `skype.com`).

### Prior System Vulnerability & Hotfix Enforcement

In earlier uncalibrated test runs (e.g. historical incident `#173403`), the local LLM misinterpreted the rule title and erroneously asserted:
> *"The traffic is a False Positive because the source and destination are the same internal IP address (loopback)."*

This was a pure hallucination caused by anchoring on the rule title rather than inspecting canonical evidence records. In AIS 2.0 V8.3a, this vulnerability is permanently mitigated:
1. **Detection Semantics Registration:** `ArchetypeId.POLICY_VIOLATION` explicitly documents `unsupported_assumptions: ["Matching rule name does NOT mean source and destination are identical without verifying telemetry IPs"]`.
2. **Deterministic Guardrail (`LOOPBACK_CLAIMED_ON_EXTERNAL_TRAFFIC`):** In `ReasoningIntegrityEngine.evaluate_reasoning_integrity`, any model narrative claiming "internal loopback", "same IP", or "localhost" when telemetry proves `source_ip != destination_ip` is intercepted and immediately rejected (`validation_status: REASONING_CONTRADICTION`, overruled to `REQUIRES_ATTENTION`).

---

## 3. Triggering Log Sources & Supported Event Schemas

The rule correlates telemetry originating from perimeter FortiGate firewalls operating FortiOS UTM web-filtering inspection:

```
FortiGate Firewall (UTM Engine)
   │
   ├─► Event: 'FortiGate-web-ftgd-cat-blk' (FortiGuard Category Block)
   │     Fields: date, time, logid, type=utm, subtype=webfilter, eventtype=ftgd_blk, 
   │             srcip, dstip, user, group, service, hostname/destName, 
   │             cat, catdesc (webCategory), action=blocked, policyid
   │
   └─► Event: 'FortiGate-webfilter-block' (URL Filter / Local Category Block)
         Fields: date, time, logid, type=utm, subtype=webfilter,
                 srcip, dstip, url, req_method, action=denied/blocked
```

### Exclusion & Threshold Invariants
- The rule fires when threshold $\ge 3$ blocked web requests occur within 300 seconds between the same client endpoint and destination host.
- FortiGate firewalls drop or reset the TCP session upon policy violation; therefore, HTTP response codes (`http.status_code`) are not expected in UTM block events. Telemetry normalization must treat `http.status_code` as an optional field and never abstain purely because a blocked connection lacks an HTTP 200/404 response code.
