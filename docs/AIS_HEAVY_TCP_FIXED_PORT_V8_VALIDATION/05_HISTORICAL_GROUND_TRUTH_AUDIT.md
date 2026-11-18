# 05 — Historical Ground Truth Audit & Double-Blind Review Backlog

**Audit Timestamp (UTC):** `2026-11-18T15:09:56Z`
**Target Rule:** `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`, UUID `40498741-ee6b-4a71-9101-0d6d3f77154c`)
**Total Historical Incidents Audited:** **69 / 69** (`100%` exhaustive inspection on Server 1 PostgreSQL via `/api/incidents?rule_id=40498741-ee6b-4a71-9101-0d6d3f77154c`)

---

## 1. Authoritative FortiSIEM Historical Resolution Audit Results

Every single one of the **69** canonical incidents was inspected for FortiSIEM resolution provenance (`incidentStatus`, `clearedReason`, `resolution`, `incidentComments`/`comments`, `owner`, and existing `analyst_verdict_reviews`):

| Ground-Truth Provenance Field | Observed Across All 69 Incidents | Eligible for Import? |
| :--- | :---: | :---: |
| `incidentStatus` | **`0` (Active / Open) on 69 / 69 (`100%`)** | No (0 closed/resolved incidents) |
| `clearedReason` | **Empty on 69 / 69 (`100%`)** | No |
| `resolution` | **Empty on 69 / 69 (`100%`)** | No |
| `incidentComments` / `comments` | **0 / 69** | No |
| `owner` / `assignedTo` | **0 / 69** | No |
| Existing `AnalystVerdictReview` records | **0 / 69** | N/A |
| **Reliable Independent Historical Labels Eligible to Import** | **`0 / 69`** | **0 imported (zero fabrication)** |

**Strict Data-Integrity Determination:** Zero historical FortiSIEM incidents contain evidence-backed analyst resolutions. No SIEM closure status, synthetic label, or LLM output was converted into ground truth. All **69** incidents remain cleanly pending in the double-blind Analyst Review Queue (`GET /api/reviews/pending?rule_id=40498741-ee6b-4a71-9101-0d6d3f77154c`, `ai_verdict_exposed: false`).

---

## 2. Prioritized Analyst Review Backlog (Grouped by Tenant, Evidence Completeness & Review Eligibility)

| Priority Tier | Tenant | Incident Count | Telemetry Characteristics | Review Eligibility & Action |
| :--- | :--- | :---: | :--- | :--- |
| **Tier 1A — Priority Rich-Log Review (Mixed Internal+External)** | `Demo-SOC` | **4** (`#167157`, `#160595`, `#158997`, `#158332`) | `100` raw FortiGate events each; `1–2` internal RFC-1918 destination IPs + VPN/AWS policies (`vpn_CDC-Bajaj_local_0`, `CDC-AWS-FG`, `GDC-AWS-BN`) | **HIGHEST PRIORITY** — verify whether internal targets represent authorized corporate VPN/AWS services or unauthorized internal reconnaissance. |
| **Tier 1B — Priority Rich-Log Review (100% External Outbound)** | `GDC_NOC` | **16** (`#176011`, `#175129`, `#175045`, `#175015`, `#174937`, `#174853`, `#174633`, `#174576`, `#174379`, `#174362`, `#174353`, `#173594`, `#173449`, `#171810`, `#168052`, `#167348`) | `97–100` raw FortiGate events each; `internal=0`, `external=42–76`, `bidir=97–100`, `denied=0`, policies `Cybersecurity`/`Internet-OUT`/`Cloud`, service `Browsing` | **HIGH PRIORITY** — immediately reviewable in double-blind workbench to establish initial verified ground truth & RAG precedents. |
| **Tier 1C — Priority Rich-Log Review (100% External Outbound / AppCtrl)** | `Demo-SOC` | **12** (`#164575`, `#164514`, `#164340`, `#159029`, `#158372`, `#159881`, `#158304`, `#158035`, `#158464`, `#157716`, `#157443`, `#158297`) | `100` raw FortiGate events each; `internal=0`, `external=33–62`, `denied=0`, policies `Cyble-Internet-Access`/`Full_Access`/`Analyst_Policy`/`Netskope_client-Bajaj`/`user Internet` | **HIGH PRIORITY** — reviewable in double-blind workbench (note: 9 of 12 carry heavy `FortiGate-appctrl-ips-pass` counts `57–94`, now explicitly surfaced via `appctrl_pass_events`). |
| **Tier 2 — Header-Only Backlog (Zero Raw Logs)** | `GDC_NOC` | **25** (incl. `#176122`) | `0` raw events (`scan.raw_events_count = 0`); header metadata only (`srcIpAddr`, `destIpPort=443`, `incidentCount`) | **LOW ELIGIBILITY** — cannot reliably establish TP/FP from SIEM payload alone without external firewall/EDR lookup; expected to resolve as `INSUFFICIENT_EVIDENCE` (excluded from TP/FP accuracy denominator). |
| **Tier 2 — Header-Only Backlog (Zero Raw Logs)** | `Demo-SOC` | **12** | `0` raw events (`scan.raw_events_count = 0`); header metadata only | **LOW ELIGIBILITY** — same as above; requires external log retrieval before TP/FP adjudication. |
| **Total Pending Queue** | **All** | **69** (`41 GDC_NOC` + `28 Demo-SOC`) | **32 rich-log** (`46.4%`) + **37 header-only** (`53.6%`) | **`32` directly reviewable today; `>= 68` additional rich-log incidents must still be ingested & independently reviewed to reach the `100`-sample minimum floor (`>= 25` TP, `>= 50` FP).** |
