# 02 — AIS 2.0 Rule Intelligence & Policy Specification

**Target Rule:** `Heavy TCP Host Scan On Fixed Port`
**Canonical Event Type:** `PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`
**Canonical Rule UUID:** `40498741-ee6b-4a71-9101-0d6d3f77154c`
**Active Approved Policy Version on Server 1:** **v7** (`d79fb576-c6b9-4f63-9167-3c7a2419b70a`, `APPROVED`, `ELIGIBLE`)
**Compiler Version:** `v3.0.0` | **Compilation Digest:** `b44efd13f3eff2335be45bfacec24c46199dfe5b63558de66e61db80ea0657eb`
**Active Policy Digest:** `e4d388ee2693e442289ca56f4c349c30540bd2fff393be2a57851881ddcf116c`

---

## 1. Authoritative FortiSIEM Rule Definition (Verified on Server 1)

The authoritative FortiSIEM XML rule definition was imported on Server 1 (`def_status = VERIFIED`), replacing the incomplete header-only placeholder:

- **Detection Expression:** `COUNT(DISTINCT destIpAddr) >= 100 AND destIpPort IS NOT NULL AND ipProto = 6`
- **Aggregation Window:** `180s`
- **Group By:** `srcIpAddr,destIpPort`
- **Primary Archetype:** `NETWORK_SCAN` (distinct from multi-port `PH_RULE_HEAVY_TCP_HOST_SCAN`)
- **Rule Drift Events:** 2 drift events generated upon authoritative import were reviewed and explicitly acknowledged (`POST /api/prompts/rule/40498741-ee6b-4a71-9101-0d6d3f77154c/acknowledge-drift`) prior to Administrator policy approval.

---

## 2. Deterministic Evidence Normalization & Scan Aggregation

Implemented and verified in [evidence_normalization_service.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/evidence_normalization_service.py) and registered in [evidence_requirement_mapper.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/evidence_requirement_mapper.py):

1. **Header-Only Incidents (e.g., `#176122`):**
   - Extracts `network.source_ip` (`incidentSrc`), `network.destination_port` (`incidentTarget` → `destIpPort`), `scan.connection_count` (`incidentDetail.incidentCount`), MITRE tactics/techniques, and emits `scan.raw_events_count = 0` so the LLM can unambiguously detect header-only telemetry and abstain safely.
   - Strictly strips ground-truth and closure fields (`clearedReason`, `analyst_verdict`, `resolution`, etc.).
2. **Rich FortiGate Raw-Log Incidents (e.g., `#176011`, `#167157`, `#175129`):**
   - Parses up to 100 attached FortiGate raw logs and deterministically aggregates:
     - `scan.raw_events_count`
     - `scan.connection_count`
     - `scan.unique_destination_hosts`
     - `network.destination_ip_list` (first 5 distinct destination IPs + `(+N more)`)
     - `scan.destination_scope` (`internal=X, external=Y, total_unique_hosts=Z`)
     - `scan.firewall_action_summary` (exact counts per firewall action: `client-rst`, `server-rst`, `close`, `deny`, `timeout`, etc.)
     - `scan.tcp_behavior_summary` (`bidirectional_sessions`, `unanswered_probes`, `denied_flows`, `sampled_events`)
     - `scan.policy_and_service` (`policy=...; service=...`)
     - `scan.window_seconds` and `scan.rate_per_second`
   - Zero values are fabricated; every record carries a cryptographic `integrity_digest` and unique `EV-*` citation ID.

---

## 3. Nine-Section Compiled AIS 2.0 Policy (Approved v7)

Generated via `POST /api/prompts/rule/40498741-ee6b-4a71-9101-0d6d3f77154c/generate-intelligent-draft` from [policy_generation_service.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/policy_generation_service.py) and compiled via [policy_compiler_service.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/policy_compiler_service.py):

| Section | Specification Summary (v7) |
| :--- | :--- |
| **1. Common SOC Baseline** | `ENTERPRISE_SOC_BASELINE_V2`: Factual grounding, suspicion vs. confirmation, **no universal RFC-1918 benign assumption**, honest confidence scoring, mandatory abstention on deficient evidence. |
| **2. Rule-Specific Directive** | Explicitly scopes to single-fixed-port horizontal TCP host scanning (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`), mandates inspection of `network.source_ip`, `network.destination_port`, and `scan.*` aggregates, distinguishes `unanswered_probes`/`denied_flows` from `bidirectional_sessions`, forbids classifying FP merely because source is internal or port is common (`443/80/22/445`), and mandates abstention when `scan.raw_events_count == 0`. |
| **3. Detection Conditions** | Authoritative FortiSIEM threshold `COUNT(DISTINCT destIpAddr) >= 100`, `destIpPort IS NOT NULL`, `ipProto = 6`, window `180s`, `GroupBy: srcIpAddr,destIpPort`. |
| **4. Mandatory Evidence Contract** | `EC-40498741-ee6b-4a71-9101-0d6d3f77154c-V7`: `security.event_type`, `event.timestamp`, `network.source_ip`, `network.destination_port`, `network.destination_ip`, `network.destination_ip_list`, `network.protocol`, `scan.rate_per_second`, `scan.connection_count`, `network.tcp_flags`, `detection.threshold`. |
| **5. True-Positive Indicators** | Unauthorized fixed-port horizontal TCP recon with unanswered/RST/denied flows, internal sweeps on admin/lateral ports (`22, 135, 139, 445, 3389, 5985, 1433, 3306`) or critical servers, external perimeter sweeps, or corroborating brute-force/exploit/IDS alerts. |
| **6. False-Positive Indicators** | Verifiable authorized vulnerability scanner (`Nessus`/`Qualys`/`Rapid7`/`OpenVAS`) or scheduled admin/monitoring job with an active approved ticket/exception in telemetry, OR verified outbound web/CDN/SaaS browsing proving predominantly `bidirectional_sessions` (`sentbyte > 0` and `rcvdbyte > 0`) under an outbound browsing policy to public IPs with zero denied/internal sweep indicators. Explicitly warns: *internal RFC-1918 traffic is NOT automatically benign; verify explicit authorization.* |
| **7. Abstention Criteria** | Header-only (`scan.raw_events_count == 0`), missing critical fields, unverified scanner/admin claims lacking CMDB/ticket proof, or contradictory telemetry. |
| **8. Escalation & Safety Boundaries** | Immediate P1/P2 escalation on unauthorized internal lateral/admin scans, critical assets, or follow-on exploit/auth alerts; **NEVER** auto-close `TRUE_POSITIVE` or `INSUFFICIENT_EVIDENCE`. |
| **9. Analyst Investigation Questions** | 4 targeted L2 follow-up questions covering scanner/ticket verification, internal vs. public target scope, probe vs. bidirectional TLS behavior, and corroborating alerts. |
| **10. Untrusted Data Delimiters** | Strict `<UNTRUSTED_INCIDENT_DATA>` and `<VERIFIED_HISTORICAL_PRECEDENTS>` prompt-injection isolation boundaries (with tag-closing neutralization in `openai_compatible.py`). |
| **11. Structured Output Contract** | Compact JSON contract requiring `incident_id`, `rule_id`, `verdict`, `confidence`, `reason`, `supporting_claims`, `supporting_evidence`, `contradictory_evidence`, `missing_evidence`, `recommended_action`, and `analyst_questions`. |

---

## 4. Quality Gate Verification (G1–G8) on Policy v7

Live Server 1 validation (`POST /api/prompts/rule/40498741-ee6b-4a71-9101-0d6d3f77154c/validate-quality/d79fb576-c6b9-4f63-9167-3c7a2419b70a`) and learning readiness snapshot confirmed:

- **G1–G7 Structural, Safety, Contract & Governance Gates:** **7 / 8 PASSED**, `0` blocking issues, `structural_approval_eligible: true`, Administrator **APPROVED** (`v7`).
- **G8 Empirical Simulation Gate:** **NOT YET PASSED** (`empirical_validation_eligible: false`, `MISSING_EMPIRICAL_SIMULATION_RUN`) because live Server 1 currently has `0` verified independent analyst ground-truth labels. Autonomous actions remain strictly blocked (`policy_governance_mode: ADVISORY_ANALYST_REVIEW_REQUIRED`).
