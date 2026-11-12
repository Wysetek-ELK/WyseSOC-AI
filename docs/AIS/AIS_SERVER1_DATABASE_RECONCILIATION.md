# AIS Server 1 Database Reconciliation Report

**Audited Environment:** Production Server 1 (PostgreSQL 14+)  
**Database URL:** `postgresql+asyncpg://aiverdict_user:***@127.0.0.1:5432/ai_verdict` (Redacted)  
**Alembic Head Revision:** `008_soc_pilot` | **Current DB Revision:** `008_soc_pilot`  
**Generated At:** 2026-11-11T16:14:36Z  
**Access Mode:** Strictly Read-Only (Zero Database Mutations)

---

## 1. Overview & Database Health

A complete structural and data audit of the PostgreSQL database on Server 1 was executed via read-only SQL queries and SQLAlchemy metadata inspection.

### Summary Metrics
| Metric | Count | Notes |
| :--- | :---: | :--- |
| **Total Rules** | **34** | Active detection rules in `rules` table |
| **Total Incidents** | **3,107** | Historical SIEM incidents in `incidents` table |
| **Total Ground Truth Records** | **3,107** | 1:1 records in `historical_ground_truth` |
| **Total Investigations** | **3,107** | 1:1 records in `investigations` |
| **Total Rule Prompts** | **34** | Rule-associated policy records in `rule_prompts` |
| **Total Prompt Versions** | **39** | Versioned policy iterations in `prompt_versions` |
| **Policy Assessments** | **2** | Historical evaluation records in `policy_quality_assessments` |
| **Alembic Revision** | `008_soc_pilot` | Fully aligned with repository head revision |

---

## 2. Table & Column Structure Inspection

The database contains 35 active tables. All required AIS 2.0–2.3 tables are present.

### Key Table Schemas

#### 1. `historical_ground_truth`
Columns present on Server 1:
- `id` (UUID, PK)
- `incident_id` (UUID, FK -> incidents.id)
- `resolution` (VARCHAR: "True Positive", "False Positive", or empty)
- `cleared_reason` (VARCHAR)
- `comments` (TEXT)
- `cleared_user` (VARCHAR)
- `cleared_time_epoch` (BIGINT)
- `resolved_at_epoch` (BIGINT)
- `is_ml_generated` (BOOLEAN)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

> [!NOTE] Schema Observation: Local vs Remote Column Difference
> In Server 1 PostgreSQL, the column `hgt.resolved_by` does not exist. The platform tracks resolving identity via `cleared_user` and `comments`. Any local development queries referencing `hgt.resolved_by` fail with `UndefinedColumn` unless defensively checked or migrated.

#### 2. `investigations`
Columns present on Server 1:
- `id`, `incident_id`, `assigned_to_user_id`, `status`, `analyst_verdict`, `verdict_reason`, `analyst_notes`
- `is_disputed` (BOOLEAN)
- `is_independently_verified` (BOOLEAN)
- `insufficient_evidence_reason` (VARCHAR)
- `created_at`, `updated_at`

---

## 3. Target Rule Reconciliation: Heavy TCP Host Scan

### 3.1 The Two Distinct Detection Rules
The audit identified two separate rules in the database matching "Heavy TCP Host Scan":

| Field | Rule 1 (Target Under Audit) | Rule 2 (Fixed Port Variant) |
| :--- | :--- | :--- |
| **Rule UUID** | `9839fa49-40ac-4676-abcc-4c5581ae9e09` | `40498741-ee6b-4a71-9101-0d6d3f77154c` |
| **Logical Rule ID** | `PH_RULE_HEAVY_TCP_HOST_SCAN` | `PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT` |
| **Display Name** | Heavy TCP Host Scan | Heavy TCP Host Scan On Fixed Port |
| **Event Type** | `PH_RULE_HEAVY_TCP_HOST_SCAN` | `PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT` |
| **Pattern Logic** | `{"incidentCount":230}` | `{"incidentCount":161}` |
| **Canonical Incidents** | **2** | **31** |
| **Labeled Incidents** | **1** (Incident 165233: "False Positive") | **0** (All 31 unlabeled) |
| **Verified Independent GT** | **0** | **0** |

### 3.2 Reconciliation of AI Triage Workbench Search
When an analyst searches `"Heavy TCP Host Scan"` in the AI Triage Workbench:
```sql
SELECT COUNT(*) FROM incidents 
WHERE title ILIKE '%Heavy TCP Host Scan%' 
   OR event_type ILIKE '%Heavy TCP Host Scan%';
-- Result: Exactly 33
```
- **31 incidents** belong to `PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT` (`event_type = 'PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT'`).
- **2 incidents** belong to `PH_RULE_HEAVY_TCP_HOST_SCAN` (`event_type = 'PH_RULE_HEAVY_TCP_HOST_SCAN'`).
- Total: $31 + 2 = 33$ incidents.

**Conclusion:** The AI Triage Workbench was not broken; it was executing a substring text query that combined two distinct detection rules.

### 3.3 Reconciliation of AIS G8 Simulation Mismatches
When legacy AIS 2.0 evaluated `PH_RULE_HEAVY_TCP_HOST_SCAN`:
1. It queried `SELECT * FROM incidents ORDER BY created_at DESC LIMIT 50` without filtering by rule.
2. In that 50-incident batch, only **2 incidents** matched `PH_RULE_HEAVY_TCP_HOST_SCAN`.
3. The remaining **50 incidents** were rejected by the simulation matcher as `RULE_MISMATCH`.
4. Only **1 incident** (`165233`) had a resolution label ("False Positive").
5. Incident `165233` was not flagged `is_independently_verified = true`.
6. Result: Gate G8 reported `INSUFFICIENT_DATA` (1 sample < 5 required).

In AIS 2.1+, `PolicySimulationService` strictly scopes queries by canonical rule UUID and event type:
```sql
SELECT * FROM incidents 
WHERE rule_id = '9839fa49-40ac-4676-abcc-4c5581ae9e09' 
   OR (rule_id IS NULL AND event_type = 'PH_RULE_HEAVY_TCP_HOST_SCAN');
```
This returns exactly 2 incidents, 0 rule mismatches, and accurately declares `INSUFFICIENT_DATA` ($2 < 5$).

---

## 4. Cross-Rule Incident Distribution Across 34 Rules

The table below documents the top rules by incident volume on Server 1:

| # | Rule UUID | Logical Rule ID | Display Name | Incident Count | % of Corpus |
| - | :--- | :--- | :--- | :---: | :---: |
| 1 | `7bd13e89-0828-48e6-8cf5-f3cbf12d438c` | `PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST` | Website access policy violation: Same Source and Destination | **2,675** | 86.10% |
| 2 | `73fcfc63-2961-496a-bb73-0802dfcd57bf` | `PH_Rule_MISP_MalwareIP_Inbound` | Permitted Traffic from MISP Malware IP List | **153** | 4.92% |
| 3 | `2ab8850e-80f8-4f2e-8c09-539c70011f40` | `PH_RULE_FGT_Config_Change` | FortiGate: Config Change Detected | **64** | 2.06% |
| 4 | `d9eae951-1e54-4bb3-bbfc-5ae8ac5672b7` | `PH_Rule_MISP_MalwareIP_Outbound` | Traffic to MISP Malware IP List | **37** | 1.19% |
| 5 | `3aec4328-53e7-4dc6-9282-884ec225fb87` | `Permitted_Traffic_from_MISP_Malware_IP_List_3_27_2026` | Permitted Traffic from MISP Malware IP ListTest | **35** | 1.13% |
| 6 | `40498741-ee6b-4a71-9101-0d6d3f77154c` | `PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT` | Heavy TCP Host Scan On Fixed Port | **31** | 1.00% |
| 7 | `79e6a957-0013-44f9-b46c-6488b89a7f74` | `PH_RULE_WEB_POL_VIOLATION_SAME_SRC_MANY_CATEGORIES` | Website access policy violation: Same Source and Multiple Categories | **14** | 0.45% |
| 8 | `de93a7c3-ad22-4b9b-90cb-a842459fa443` | `PH_RULE_EXCESS_DENY_EXT_COUNTRY` | Excessive Denied Connections From An External Country | **11** | 0.35% |
| 9 | `148dbeff-7640-46dd-acb6-62b466356234` | `PH_RULE_EXCESS_DNS_QUERY` | Excessive End User DNS Queries | **10** | 0.32% |
| 10 | `0974a66e-ede2-4a6a-821b-6283a99c8aa4` | `PH_RULE_CS_SUSPICIOUS_ACTIVITY` | Crowdstrike: Suspicious Activity | **10** | 0.32% |
| 11 | `14481ebd-4e8c-421e-8579-b6ee7995b746` | `Prisma_SASE_Suspicious_File_Threat_Detection_` | Prisma SASE: Suspicious File Threat Detection | **10** | 0.32% |
| 12 | `e4753b27-f50f-4a2e-ae6d-383f0779b7ce` | `PH_RULE_USER_MON_SUDDEN_LOGIN_DISTRIBUTION_CHANGE` | Sudden Windows User Login Pattern Change | **8** | 0.26% |
| 13 | `57ddcf1c-ca79-4398-8aaf-e9fb18017cde` | `PH_RULE_ANOMALY_TRAFFIC_DENIED_OUTBOUND_PORT` | Sudden Increase In Firewall Denied Outbound Traffic To A Specific Port | **7** | 0.23% |
| 14 | `d6adbcd4-661b-4fe0-8247-8cbfd0402e62` | `PH_RULE_WEB_POL_VIOLATION_MANY_SRC_SAME_DEST` | Website access policy violation: Multiple Sources and Same Destination | **5** | 0.16% |
| 15 | `fb721f80-045c-40b3-b3bc-5e9f2bfe402a` | `PH_RULE_LARGE_OUTBOUND_XFER` | Large Outbound Transfer | **5** | 0.16% |
| 16 | `8f8338be-7606-4cc3-8598-a9ad8453647e` | `PH_RULE_LARGE_OUTBOUND_XFER_OUTSIDE_COUNTRY` | Large Outbound Transfer To Outside My Country | **5** | 0.16% |
| 17 | `7c1db6d0-a2d7-4f8e-ba28-5ea56f8a8a04` | `PH_RULE_ANOMALY_DECREASING_EPS` | Sudden Decrease in Reported Events From A Host | **5** | 0.16% |
| 18 | `bad47adc-9ed3-47d1-8c07-a07186c1b4e6` | `PH_RULE_VPN_LOGON_SUCCESS_OUTSIDE_COUNTRY` | Successful VPN Logon From Outside My Country | **3** | 0.10% |
| 19 | `6163620c-18c8-4664-b143-7da54bad7d9d` | `PH_RULE_Locked_Workstation` | Windows: Locked Workstation | **2** | 0.06% |
| 20 | `92fdfdc9-6cf9-4c53-93cb-dfecaa1e9f2c` | `PH_RULE_ANOMALY_TRAFFIC_DENIED_INBOUND_PORT` | Sudden Increase In Firewall Denied Inbound Traffic To Specific Port | **2** | 0.06% |
| 21 | `9839fa49-40ac-4676-abcc-4c5581ae9e09` | `PH_RULE_HEAVY_TCP_HOST_SCAN` | Heavy TCP Host Scan | **2** | 0.06% |
| 22–34 | *Other 13 Rules* | *Various* | *Low-volume/Zero-incident rules* | **23** | 0.74% |
| **Total** | | | | **3,107** | **100.0%** |

### Analysis of Corpus Imbalance
- A single rule (`PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST`) accounts for **86.1% of all historical incidents** in the platform.
- 16 rules have $\ge 5$ incidents (the minimum threshold for empirical G8 validation).
- 18 rules (including the audit target `PH_RULE_HEAVY_TCP_HOST_SCAN`) have $< 5$ incidents, making them ineligible for empirical G8 scoring unless cross-rule generalization or additional historical imports are performed.

