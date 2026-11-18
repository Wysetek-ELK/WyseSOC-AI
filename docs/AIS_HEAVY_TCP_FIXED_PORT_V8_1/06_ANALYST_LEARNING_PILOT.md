# 06 — Independent Human Analyst Learning Pilot Plan & Readiness

**Rule:** `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`, UUID `40498741-ee6b-4a71-9101-0d6d3f77154c`)  
**Pilot Queue Status:** **`READY FOR HUMAN REVIEW`** (`69` pending incidents in Double-Blind Workbench, `blind_mode_active = true`, **`0` fabricated/synthetic reviews created**)

---

## 1. Strict Ground-Truth Integrity Policy

Per AIS 2.0 governance and V8.1 zero-fabrication rules:
- **0 synthetic, heuristic, or AI-generated labels** were created during V8 or V8.1.
- All **69** canonical incidents currently have FortiSIEM `status = 0` (Open), `clearedReason = ""`, `resolution = ""`, `comments = ""`, and `owner = ""` — meaning **0** historical tickets contain trustworthy SIEM closure ground truth.
- Therefore, empirical accuracy (`G8`) and verified RAG precedent learning can **only** begin once real SOC analysts independently label incidents via the **Double-Blind Analyst Review Workbench** (`GET /api/learning/pending-reviews` → `POST /api/learning/feedback`).

---

## 2. Prioritized Pilot Cohort (32 Rich-Log Incidents First, 37 Header-Only Deferred)

### Priority A — High-Risk Mixed Internal/External Targets (4 Incidents — Review FIRST)
These 4 `Demo-SOC` incidents each have `100` raw FortiGate events, touch **`1–2` internal RFC-1918 destination hosts** alongside external HTTPS/SSL targets via VPN/AWS policies, and include `31%–63%` `FortiGate-appctrl-ips-pass` (`pass`) events. They are the highest-value cases to test lateral-reconnaissance vs authorized-VPN classification and establish high-signal TP or justified-FP precedents.

| Priority | Incident ID | Tenant | Raw Logs | Unique Dst (Int / Ext) | Bidir / AppCtrl-Pass / Unans / Denied | FortiGate Policies | Services |
| :---: | :---: | :--- | :---: | :---: | :---: | :--- | :--- |
| **A1** | **`167157`** | `Demo-SOC` | `100` | `32` (`2` int / `30` ext) | `37 / 63 / 0 / 0` | `user Internet`, `CDC-AWS-FG`, `vpn_CDC-Bajaj_local_0` | `Browsing`, `SSL`, `HTTPS` |
| **A2** | **`160595`** | `Demo-SOC` | `100` | `54` (`1` int / `53` ext) | `69 / 31 / 0 / 0` | `user Internet`, `vpn_CDC-Bajaj_local_0` | `Browsing`, `HTTPS`, `SSL` |
| **A3** | **`158997`** | `Demo-SOC` | `100` | `52` (`1` int / `51` ext) | `40 / 60 / 0 / 0` | `Analyst_Policy`, `GDC-AWS-BN` | `Browser`, `SSL`, `HTTPS` |
| **A4** | **`158332`** | `Demo-SOC` | `100` | `46` (`1` int / `45` ext) | `48 / 52 / 0 / 0` | `user Internet`, `vpn_CDC-Bajaj_local_0` | `Browsing`, `HTTPS`, `SSL` |

### Priority B1 — Pure External Bidirectional HTTPS/Browsing (`GDC_NOC`, 16 Rich-Log Incidents)
All 16 `GDC_NOC` rich-log incidents (`97–100` raw events) target **`0` internal hosts** (`42–76` unique external hosts on TCP/443) with `97–100` bidirectional sessions, `0–3` unanswered probes, `0` denied flows, and `0` appctrl-pass events under `Cybersecurity`, `Internet-OUT`, or `Cloud` policies (`Browsing` service). Reviewing these establishes whether corporate workstation browsing over port 443 is verified `FALSE_POSITIVE` (or unauthorized proxy/scanner `TRUE_POSITIVE`).

| # | Incident ID | Raw Logs | Unique Dst (Int / Ext) | Bidir / Unans / Denied | Policies | Benchmark Cohort? |
| :---: | :---: | :---: | :---: | :---: | :--- | :---: |
| 1 | **`176011`** | `100` | `75` (`0` / `75`) | `100 / 0 / 0` | `Cybersecurity` | **Yes (V7/V8/V8.1)** |
| 2 | **`175129`** | `100` | `49` (`0` / `49`) | `100 / 0 / 0` | `Cybersecurity` | **Yes (V7/V8/V8.1)** |
| 3 | **`173449`** | `100` | `60` (`0` / `60`) | `97 / 3 / 0` | `Cybersecurity` | **Yes (V7/V8/V8.1)** |
| 4 | `175045` | `97` | `63` (`0` / `63`) | `97 / 0 / 0` | `Cybersecurity` | — |
| 5 | `175015` | `100` | `58` (`0` / `58`) | `99 / 1 / 0` | `Internet-OUT` | — |
| 6 | `174937` | `100` | `64` (`0` / `64`) | `100 / 0 / 0` | `Cybersecurity` | — |
| 7 | `174853` | `100` | `65` (`0` / `65`) | `100 / 0 / 0` | `Internet-OUT` | — |
| 8 | `174633` | `100` | `61` (`0` / `61`) | `100 / 0 / 0` | `Internet-OUT` | — |
| 9 | `174576` | `100` | `56` (`0` / `56`) | `100 / 0 / 0` | `Internet-OUT` | — |
| 10 | `174379` | `100` | `42` (`0` / `42`) | `100 / 0 / 0` | `Cybersecurity` | — |
| 11 | `174362` | `100` | `67` (`0` / `67`) | `100 / 0 / 0` | `Cybersecurity` | — |
| 12 | `174353` | `100` | `59` (`0` / `59`) | `100 / 0 / 0` | `Cloud` | — |
| 13 | `173594` | `100` | `63` (`0` / `63`) | `100 / 0 / 0` | `Cybersecurity` | — |
| 14 | `171810` | `100` | `53` (`0` / `53`) | `100 / 0 / 0` | `Cybersecurity` | — |
| 15 | `168052` | `100` | `58` (`0` / `58`) | `99 / 1 / 0` | `Cybersecurity` | — |
| 16 | `167348` | `100` | `76` (`0` / `76`) | `100 / 0 / 0` | `Cybersecurity` | — |

### Priority B2 — Pure External HTTPS/Browsing & AppCtrl-Pass (`Demo-SOC`, 12 Rich-Log Incidents)
Four have `99–100` bidirectional sessions (`164575`, `164340`, `158372`, `158464`), while eight contain `57%–94%` `appctrl-ips-pass` events (`164514`, `159029`, `159881`, `158304`, `158035`, `157716`, `157443`, `158297`).

| # | Incident ID | Raw Logs | Unique Dst (Int / Ext) | Bidir / AppCtrl-Pass / Unans / Denied | Policies | Benchmark Cohort? |
| :---: | :---: | :---: | :---: | :---: | :--- | :---: |
| 1 | **`164575`** | `100` | `53` (`0` / `53`) | `100 / 0 / 0 / 0` | `Cyble-Internet-Access` | **Yes (V7/V8/V8.1)** |
| 2 | `164340` | `100` | `62` (`0` / `62`) | `99 / 0 / 1 / 0` | `Full_Access` | — |
| 3 | `158372` | `100` | `53` (`0` / `53`) | `99 / 0 / 1 / 0` | `Full_Access` | — |
| 4 | `158464` | `100` | `49` (`0` / `49`) | `100 / 0 / 0 / 0` | `Netskope_client-Bajaj`, `Engineer_Policy` | — |
| 5 | `164514` | `100` | `46` (`0` / `46`) | `17 / 83 / 0 / 0` | `Analyst_Policy`, `Netskope_client-Bajaj` | — |
| 6 | `159029` | `100` | `54` (`0` / `54`) | `23 / 77 / 0 / 0` | `Netskope_client-Bajaj`, `Analyst_Policy` | — |
| 7 | `159881` | `100` | `47` (`0` / `47`) | `21 / 79 / 0 / 0` | `Netskope_client-Bajaj`, `user Internet` | — |
| 8 | `158304` | `100` | `42` (`0` / `42`) | `6 / 94 / 0 / 0` | `user Internet` | — |
| 9 | `158035` | `100` | `42` (`0` / `42`) | `40 / 60 / 0 / 0` | `Analyst_Policy` | — |
| 10 | `157716` | `100` | `52` (`0` / `52`) | `43 / 57 / 0 / 0` | `user Internet`, `Netskope_client-Bajaj` | — |
| 11 | `157443` | `100` | `34` (`0` / `34`) | `32 / 68 / 0 / 0` | `Analyst_Policy` | — |
| 12 | `158297` | `100` | `33` (`0` / `33`) | `18 / 82 / 0 / 0` | `Analyst_Policy` | — |

### Tier 2 — Deferred Header-Only Incidents (37 Incidents: 25 `GDC_NOC` + 12 `Demo-SOC`)
Includes benchmark control `#176122` plus 36 other `raw_events_count = 0` incidents (`175382`, `175156`, `175059`, `175048`, `174944`, `174945`, `174907`, `174828`, `174799`, `174719`, `174583`, `174562`, `174498`, `174497`, `174476`, `174456`, `174455`, `174444`, `174022`, `173049`, `172425`, `172364`, `172328`, `172287`, `160911`, `160156`, `158417`, `158413`, `158397`, `159148`, `158380`, `159822`, `158032`, `158317`, `159073`, `158877`). Unless analysts recover raw logs out-of-band in FortiSIEM/FortiAnalyzer, these should be marked `INCONCLUSIVE` / abstention controls rather than forced TP/FP labels.

---

## 3. Double-Blind Analyst Workflow & Evidence Verification Checklist

1. **Open AIS 2.0 → Rule `Heavy TCP Host Scan On Fixed Port` → Double-Blind Review Workbench.**
   - Verified live on Server 1: `GET /api/learning/pending-reviews?rule_id=40498741-...` returns `total = 69`, `blind_mode_active = true`, `analyst_verdict = null`, and **zero AI verdict leakage** prior to submission.
2. **Verify telemetry independently for each Priority A / B incident before selecting `TRUE_POSITIVE`, `FALSE_POSITIVE`, or `INCONCLUSIVE`:**
   - **Source asset identity:** Confirm via CMDB/EDR whether `network.source_ip` (e.g., `172.25.24.154`, `172.27.29.67`) is an employee workstation, proxy/NAT gateway, authorized vulnerability scanner, or unauthorized host.
   - **Destination scope:** For Priority A (`#167157`, `#160595`, `#158997`, `#158332`), inspect the exact `1–2` internal RFC-1918 destination IPs and VPN/AWS firewall policies (`CDC-AWS-FG`, `vpn_CDC-Bajaj_local_0`, `GDC-AWS-BN`) to confirm authorized internal app access vs unauthorized lateral scanning.
   - **Session behavior:** Confirm whether `bidirectional_sessions` + `close`/`client-rst`/`server-rst` reflect normal HTTPS/TLS browser sessions or probe sweeps (`unanswered_probes`, `denied_flows`).
   - **Corroboration:** Check EDR/IPS/auth logs for follow-on exploitation or credential access from the same source IP.
3. **Submit rationale & trigger automatic post-submission governance:**
   - Upon submission, AIS 2.0 reveals the AI's blind verdict, computes agreement/disagreement, flags disputes for Senior/Admin adjudication (`POST /api/learning/adjudicate`), indexes verified `TRAINING`/`VALIDATION` precedents (strictly excluding `LOCKED_TEST` holdout rows and enforcing tenant isolation), and updates the empirical confusion matrix + G8 readiness counters automatically.
4. **Target Pilot Milestones:**
   - **Milestone 1 (Immediate Pilot — First 10–15 verified rich-log reviews):** Unlocks first measurable G8 empirical simulation (`>= 5` verified cases) and initial verified RAG precedents (`TRAINING` split).
   - **Milestone 2 (Calibration — `>= 30` verified reviews):** Unlocks empirical trust-score calibration (`>= 30` labeled cases).
   - **Milestone 3 (Full G8 & Production Eligibility — `>= 100` verified reviews, `>= 25` TP, `>= 50` FP):** Required before any production autonomy proposal (see `07_G8_AND_ACCURACY_READINESS.md`).
