# 04 — Pilot Cohort Specification & SOC Analyst Operational Guide

**Target Rule:** `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`)  
**Canonical UUID:** `40498741-ee6b-4a71-9101-0d6d3f77154c`  
**Dataset Scope:** 69 historical incidents (32 rich FortiGate telemetry, 37 header-only)  
**Initial Pilot Target:** 14 prioritized rich-log incidents across `GDC_NOC` and `Demo-SOC`  

---

## 1. Prioritized Pilot Cohort Specification

The initial 14-incident pilot cohort is structured into two focused investigation tiers to systematically evaluate model decision boundaries:

### Priority A Cohort: Mixed Destination Scope & Administrative Administration (4 Incidents)
*Focus: Differentiating legitimate VPN/AWS/bastion administration from lateral reconnaissance.*

| Incident ID | Tenant | Raw Events | Source IP | Dest Scope Summary | Telemetry / Service Context | Investigation Objective |
| :---: | :---: | :---: | :---: | :--- | :--- | :--- |
| **`#167157`** | `Demo-SOC` | `100` | `172.27.29.67` | 2 Internal, 30 External (total 32) | 63% AppCtrl pass events; port 443 | Verify if internal RFC-1918 connections represent authorized admin sweep or lateral reconnaissance. |
| **`#160595`** | `Demo-SOC` | `100` | `172.27.29.56` | Mixed Internal / AWS Public | VPN gateway & cloud management | Check CMDB asset role and verify whether administrative workstation has maintenance approval. |
| **`#158997`** | `Demo-SOC` | `100` | `172.26.27.61` | Mixed Subnets | FortiGate session teardowns | Inspect destination port targeting and determine if traffic is benign multi-cloud admin. |
| **`#158332`** | `Demo-SOC` | `100` | `172.26.27.60` | Internal Core / External CDN | Application control pass logs | Evaluate whether internal subnet scan was authorized by scheduled security assessment ticket. |

---

### Priority B Cohort: External HTTPS / High-Volume Web Browsing (10 Incidents)
*Focus: Differentiating benign concurrent browsing from automated external reconnaissance.*

| Incident ID | Tenant | Raw Events | Source IP | Destination Summary | TCP Behavior Summary | Investigation Objective |
| :---: | :---: | :---: | :---: | :--- | :--- | :--- |
| **`#176011`** | `GDC_NOC` | `100` | `172.25.24.154` | 75 External IPs on Port 443 | `bidir=100, unans=0, denied=0` | Verify destination domains (CDNs/Google) and confirm lack of threat intel corroboration. |
| **`#175129`** | `GDC_NOC` | `100` | `172.25.24.147` | 49 External IPs on Port 443 | `bidir=100, unans=0, denied=0` | Inspect firewall policy (`Cybersecurity`, `Browsing`) and verify absence of port sweep tradecraft. |
| **`#173449`** | `GDC_NOC` | `100` | `172.25.24.130` | 60 External IPs on Port 443 | `bidir=97, unans=3, denied=0` | Analyze 3 server-rst events; verify whether destination resets represent dead web servers or scanner probes. |
| **`#164575`** | `Demo-SOC` | `100` | `172.27.29.53` | 53 External IPs on Port 443 | `bidir=100, unans=0, denied=0` | Check enterprise policy (`Cyble-Internet-Access`) and confirm user web browser activity. |
| **`#173266`** | `GDC_NOC` | `100` | `172.25.24.120` | 42 External IPs on Port 443 | `bidir=100, unans=0, denied=0` | Verify destination categorization and check for threat intelligence alerts. |
| **`#173199`** | `GDC_NOC` | `100` | `172.25.24.119` | 51 External IPs on Port 443 | `bidir=100, unans=0, denied=0` | Confirm endpoint process lineage (e.g. `chrome.exe` vs python scanner). |
| **`#172901`** | `GDC_NOC` | `100` | `172.25.24.110` | 64 External IPs on Port 443 | `bidir=99, unans=1, denied=0` | Investigate single unanswered probe and evaluate session duration. |
| **`#171804`** | `GDC_NOC` | `100` | `172.25.24.95` | 38 External IPs on Port 443 | `bidir=100, unans=0, denied=0` | Check application control classification and bandwidth utilization. |
| **`#170211`** | `GDC_NOC` | `100` | `172.25.24.88` | 45 External IPs on Port 443 | `bidir=100, unans=0, denied=0` | Confirm whether source host is an employee laptop or server workload. |
| **`#169420`** | `GDC_NOC` | `100` | `172.25.24.79` | 55 External IPs on Port 443 | `bidir=100, unans=0, denied=0` | Validate destination context and confirm absence of brute-force tradecraft. |

---

## 2. SOC Analyst Step-by-Step Investigation Guide

### Step 1: Access the Double-Blind Workbench
1. Log into Verdictum AI Web UI (`http://172.26.41.240`).
2. Navigate to: **Agent Intelligence Studio 2.0** &rarr; **Learning & Optimization** &rarr; Select Rule **`Heavy TCP Host Scan On Fixed Port`**.
3. Select the **Double-Blind Review Workbench** tab (`/learning/rules/40498741-ee6b-4a71-9101-0d6d3f77154c?tab=workbench`).

### Step 2: Select Incident & Review Telemetry
1. Select an incident from the **Pending Review Queue** (start with Priority A: `#167157`).
2. Verify the **Double-Blind Mode Active** shield is displayed (AI verdict is strictly masked).
3. Review the **Incident Telemetry Summary**: Source IP, Target Port, Raw Events Count, Reporting Device.
4. Expand the **Observed Canonical Evidence** table to inspect canonical records (`EV-*`):
   - `scan.destination_scope`: Internal vs external destination host count.
   - `scan.tcp_behavior_summary`: Count of bidirectional sessions vs unanswered probes vs denied flows.
   - `scan.firewall_action_summary`: Breakdown of `client-rst`, `server-rst`, `close`, `deny`.
   - `scan.policy_and_service`: Firewall policy applied and service classification.

### Step 3: Execute Independent Verification Checks
Analysts must evaluate the four mandatory verification dimensions:

1. **Destination Scope & Context:**
   - Are destination hosts internal private subnets (`10.x`, `172.16-31.x`, `192.168.x`) or external public internet IPs?
   - Internal subnet sweeps require verified scanner authorization before being classified as benign.
2. **Session Directionality & Teardown Behavior:**
   - Are sessions bidirectional (`sentbyte > 0` and `rcvdbyte > 0`) indicating full TLS/TCP handshakes?
   - `client-rst` indicates normal browser/client session teardown.
   - `server-rst` indicates destination port rejection or host drop.
   - Unanswered probes (`sentbyte > 0`, `rcvdbyte = 0`) indicate SYN sweeps or unreachable targets.
3. **Corroborating Threat Telemetry:**
   - Are destination IPs cited in threat intelligence feeds, C2 botnet lists, or URL reputation blacklists?
   - Do events contain exploit payloads, directory brute-force indicators, or known scanner tool user-agents?
4. **Administrative / Scanner Authorization:**
   - Is the source IP a registered vulnerability scanner (e.g. Tenable, Qualys)?
   - Was an active change management ticket (`CHG-*`, `RFC-*`) or scheduled maintenance window open at the time of the event?

### Step 4: Record Independent Verdict & Submit
1. Select one of the three radio options:
   - **`FALSE_POSITIVE`** (Benign / Expected Activity): Use when evidence confirms legitimate web browsing, CDN content distribution, or authorized administrative/scanner sweeps.
   - **`TRUE_POSITIVE`** (Confirmed Malicious Reconnaissance / Unauthorized Scan): Use when evidence confirms unauthorized horizontal scanning, reconnaissance tooling, or threat intel matches.
   - **`INSUFFICIENT_EVIDENCE`** (Inconclusive): Use when critical logs are missing (e.g. header-only alerts with 0 raw events) or when source intent cannot be determined from available telemetry.
2. Enter **Investigation Rationale**: Provide clear, factual reasoning explaining your decision.
3. Enter **Evidence References**: Cite the specific canonical evidence IDs (e.g. `EV-176011-TOP-scan_tcp_behavior_summary`) supporting your rationale.
4. Click **Submit Independent Determination**.

### Step 5: Post-Submission Comparison Review
- Once submitted, the workbench will instantly reveal the **Stored AI Model Determination**:
  - Model proposed verdict (`TRUE_POSITIVE`, `FALSE_POSITIVE`, `REQUIRES_ATTENTION`).
  - Model confidence score and calibrated probability.
  - Model reasoning summary and grounding status.
  - Comparison outcome (`AGREEMENT` or `DISAGREEMENT`).
- If an analyst disagreement occurs, the review is automatically routed to the **Dispute Adjudication Queue** for Lead Investigator review.
