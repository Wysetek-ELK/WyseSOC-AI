# 01 — V7 Root Cause Audit & Governance Reconciliation

**Audit Timestamp (UTC):** `2026-11-18T15:09:56Z` – `2026-11-18T16:12:16Z`
**Target Rule:** `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`, UUID `40498741-ee6b-4a71-9101-0d6d3f77154c`)
**Audited Baseline Policy:** Approved **v7** (`d79fb576-c6b9-4f63-9167-3c7a2419b70a`, **unmodified during audit and preserved as active policy**)
**Local LLM:** `Qwen/Qwen2.5-7B-Instruct-AWQ` on Server 2 (`Verdictum Cortex`, `13.204.214.64:8000`, `ONLINE`, `max_model_len = 4096`, **untouched**)

---

## 1. Deployed SHA & UPLA Governance Reconciliation

| Checkpoint | Verified Git SHA | UPLA Execution ID | Reconciliation Finding |
| :--- | :--- | :--- | :--- |
| **Pre-V8 Baseline on Server 1** | `889519f287865f00d82eaf427493318b652bdc3f` | `upla-20261118-145751-eea133` (`COMPLETED_FULL_WORKFLOW`) | Reconciled verbatim with `FINAL_EVIDENCE.json` (code SHA `800bc077` + 11 completion reports `889519f2`). |
| **Unresolved Governance Warnings Investigated** | — | `upla-20261118-144854-c645a7`, `upla-20261118-151625-9cfa67` | Two recurring UPLA `WARNING` items audited: (1) *"Security-sensitive files modified; manual review recommended"* — triggered automatically when editing pipeline/governance Python modules; reviewed manually (`0` blockers, `security: PASS`); (2) *"External scanners (gitleaks, semgrep, bandit, pip-audit, trivy) not installed locally"* — built-in UPLA secret/SAST/PS-AST scanners ran and passed (`0` secrets leaked). |
| **V8 Deployment SHA on Server 1** | `10021a3ffcb8fe5af0e5b769d9d725b5e5745c3c` | `upla-20261118-160649-86fcd5` (Gate 1 `SYNCED_AND_VERIFIED`; Gate 2 executed on Server 1 console after Windows OpenSSH stall) | Verified live on Server 1: `23 passed in 5.78s` (`pytest`), Next.js production build `PASS`, `GET /api/health` = `healthy`. |

---

## 2. Exact Root Cause Breakdown of V7 Abstentions (`#176011`, `#167157`, `#175129`, `#176122`)

Auditing the exact `ActualPromptCaptureService` payloads (`889519f2`) and all **69 real incidents / 3,197 raw FortiGate events** identified **4 distinct causes** behind the 4/4 v7 abstentions:

| Incident | Telemetry Profile | V7 Raw LLM Abstention Reason | Root Cause Classification |
| :--- | :--- | :--- | :--- |
| **`#176011`** (`GDC_NOC`) | `100` raw FortiGate events (`internal=0, external=75`, `bidir=100, unans=0, deny=0`, `Cybersecurity/Browsing`) | Claimed `network.destination_ip`, `network.destination_ip_list`, `network.protocol`, `scan.rate_per_second`, `scan.connection_count`, `network.tcp_flags`, and `detection.threshold` were missing. | **(1) Contract defect:** `detection.threshold` (rule metadata) & `network.tcp_flags` (0/3,197 FortiGate logs) were flattened into `evidence_contract.required_fields`. **(2) Compaction drop:** `event.timestamp` & `network.protocol` were dropped while noisy `events[0]` consumed `821` chars (~260 tokens). **(3) Model attention degradation** at `3,497/4,096` tokens. |
| **`#167157`** (`Demo-SOC`) | `100` raw FortiGate events (`internal=2, external=30`, `bidir=37, appctrl_pass=63`, `user Internet, CDC-AWS-FG, vpn_CDC-Bajaj_local_0`) | Claimed `network.destination_ip`, `network.destination_ip_list`, `network.protocol` missing. | **Same contract & compaction defects + legitimate caution:** `63` `FortiGate-appctrl-ips-pass` events lacked byte counters (previously unaccounted in `scan.tcp_behavior_summary`) AND `2` internal RFC-1918 destination IPs legitimately require authorization verification before FP. |
| **`#175129`** (`GDC_NOC`) | `100` raw FortiGate events (`internal=0, external=49`, `bidir=100, unans=0, deny=0`, `Cybersecurity/Browsing`) | Cited all 11 canonical `EV-*` IDs accurately, but abstained noting `network.tcp_flags` / missing verified scanner authorization. | **(1) Contract defect** (`network.tcp_flags` & `detection.threshold` in flat `required_fields`) + **(2) Compaction drop** (`event.timestamp`, `network.protocol`) + **(3) Strict 7B anti-FP conservatism** with `0` verified RAG precedents. |
| **`#176122`** (`GDC_NOC`) | **`0` raw events** (header-only; `scan.raw_events_count = 0`) | Explicitly abstained citing `scan.raw_events_count == 0`. | **LEGITIMATE ABSTENTION (Correct behavior — must be preserved in V8).** |

---

## 3. Empirical Audit of All 3,197 Raw FortiGate Events (Across All 32 Rich-Log Incidents)

- **Raw TCP Flags Presence (`network.tcp_flags`):** **`0 / 3,197` events (`0.0%`, `AnyTcpFlags = False`)** — FortiGate session-end and appctrl logs NEVER emit raw TCP flag bitmasks.
- **Observed FortiGate Event Types (3,197 total):**
  - `FortiGate-traffic-end-forward-close`: `983` (`30.7%`)
  - `FortiGate-appctrl-ips-pass`: `806` (`25.2%`) — application-control/IPS SSL pass logs with **no** `sentbyte`/`rcvdbyte` fields
  - `FortiGate-traffic-end-forward-client-rst`: `738` (`23.1%`)
  - `FortiGate-traffic-end-forward-allowed`: `313` (`9.8%`)
  - `FortiGate-traffic-forward`: `147` (`4.6%`)
  - `FortiGate-traffic-end-forward-server-rst`: `130` (`4.1%`)
  - `FortiGate-traffic-end-forward-timeout`: `80` (`2.5%`)
- **Observed Firewall Actions:** `close=1,144`, `client-rst=847`, `pass=806`, `server-rst=173`, `accept=147`, `timeout=80`, **`deny/drop/block=0`**.
