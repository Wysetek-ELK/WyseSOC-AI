# 03 — Candidate AIS Policy V8 Specification

**Target Rule:** `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`, UUID `40498741-ee6b-4a71-9101-0d6d3f77154c`)
**Active Approved Baseline (UNTOUCHED):** **v7** (`d79fb576-c6b9-4f63-9167-3c7a2419b70a`, `APPROVED`, `ELIGIBLE`)
**Candidate Policy Version Created:** **DRAFT v8** (`20d4f788-85a5-437d-afbe-fe7fd80abca1`, status **`DRAFT`** — NOT approved, NOT active in live triage)
**Compiler Version:** `v3.0.0` | **V8 Compilation Digest:** `a7e3c745e689c076c98c08ba07f6561cc3e84313c21f2b824b91d9a9bafe5460`
**V8 Policy Digest:** `c5e87a1ec6ac82c43ed07e62271850521456719da8800299256a897c91f8352b`

---

## 1. Governance Invariant Verification

- Generated via `POST /api/prompts/rule/40498741-ee6b-4a71-9101-0d6d3f77154c/generate-intelligent-draft` on Server 1 (`10021a3f`).
- Verified via `GET /api/prompts/rule/40498741-ee6b-4a71-9101-0d6d3f77154c/eligibility`:
  - `active_version_number`: **`7`** (`APPROVED`)
  - `selected_version_number`: **`8`** (`DRAFT`)
  - Approved **v7** was never overwritten, archived, or replaced.

---

## 2. G1–G8 Quality Validation Results on Candidate DRAFT v8

Executed live on Server 1 (`POST /api/prompts/rule/40498741-ee6b-4a71-9101-0d6d3f77154c/validate-quality?version_id=20d4f788-85a5-437d-afbe-fe7fd80abca1`):

| Gate | Name | Status | Score | Max | Verified Details |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **G1** | Rule Definition Integrity | **PASSED** | `10.0` | `10.0` | `VENDOR_RULE_FILE`, `Status: VERIFIED` (`COUNT(DISTINCT destIpAddr) >= 100 AND destIpPort IS NOT NULL AND ipProto = 6`, `180s`, `GroupBy: srcIpAddr,destIpPort`) |
| **G2** | Detection Archetype Relevance | **PASSED** | `10.0` | `10.0` | `NETWORK_SCAN` (`Network Scan & Host Reconnaissance`) |
| **G3** | Evidence Contract Feasibility | **PASSED** | `20.0` | `20.0` | `EC-40498741-ee6b-4a71-9101-0d6d3f77154c-V8`: `18` fields defined (`CORE` / `CONDITIONAL` / `OPTIONAL` / `RULE_METADATA`) |
| **G4** | TP Criteria Validity | **PASSED** | `10.0` | `10.0` | Objective fixed-port unauthorized horizontal TCP scan indicators |
| **G5** | FP Criteria & Benign Assumptions | **PASSED** | `10.0` | `10.0` | Zero unsafe RFC-1918 / common-port assumptions |
| **G6** | Abstention & Escalation Safety | **PASSED** | `15.0` | `15.0` | Explicit abstention triggers (`scan.raw_events_count == 0`, unverified internal targets, contradictory telemetry) and P1/P2 escalation paths |
| **G7** | Internal Policy & Contract Consistency | **PASSED** | `10.0` | `10.0` | 9 policy sections aligned 100% with Evidence Contract V8 |
| **G8** | Simulation & Regression Validation | **WARNING** | `0.0` | `15.0` | Empirical performance unverified (`0` verified analyst ground-truth labels) |
| **Total** | **G1–G7 Structural Total** | **7/8 PASS, 0 Blockers** | **`85.0`** | **`100.0`** | **Perfect `85.0 / 85.0` on all structural/safety gates** (`+1.0` over v6/v7 `84.0`) |

---

## 3. Key Intelligence Improvements in V8 Over V7

1. **FortiGate Telemetry Alignment (Section 2 & Section 4):** Explicitly informs the LLM that FortiGate session-end and `appctrl` logs omit raw `network.tcp_flags`, instructing it to evaluate `scan.tcp_behavior_summary` (`bidirectional_sessions`, `appctrl_pass_events`, `unanswered_probes`, `denied_flows`) and `scan.firewall_action_summary` without ever inventing TCP flags or abstaining solely for optional `network.tcp_flags` or rule metadata (`detection.threshold`).
2. **Tiered Section 4 Evidence Contract:** Clearly labels `Core`, `Conditional (when raw logs exist)`, and `Optional (do NOT abstain solely if absent)`.
3. **Sharper TP / FP / Abstention Decision Boundaries (Sections 5–7):**
   - **TP:** Predominantly `unanswered_probes` / `denied_flows` / RST-only failures, unauthorized internal horizontal sweeps (`internal > 0`) on admin/lateral ports (`22, 135, 139, 445, 3389, 5985, 1433, 3306`) or critical assets, external perimeter sweeps, or corroborating brute-force/exploit/IDS alerts.
   - **FP:** Verifiable authorized vulnerability scanner (`Nessus`/`Qualys`/`Rapid7`/`OpenVAS`) or approved scheduled admin/monitoring job with active ticket, **OR** evidence-backed outbound web/CDN/SaaS browsing requiring **all** of: `scan.raw_events_count >= 10`, `internal=0` (`100%` public external endpoints), `>= 80%` `bidirectional_sessions` with `denied_flows=0` and minimal `unanswered_probes`, AND explicit outbound browsing/internet firewall policy (`scan.policy_and_service`). Explicitly prohibits treating RFC-1918 source or port `443` alone as proof of benign activity.
   - **Insufficient Evidence:** Header-only (`scan.raw_events_count == 0`), missing core fields, mixed/internal targets (`internal > 0`) without verifiable authorization, high `appctrl_pass_events` with `< 80%` bidirectional confirmation, or contradictory telemetry.
4. **Structured Citation Enforcement:** Mandates exact `EV-*` canonical IDs in both `supporting_claims` and `supporting_evidence` — proven in Phase 4 to raise grounded claims from `0/0` (v7) to `16/16` (`100%`) on v8.
