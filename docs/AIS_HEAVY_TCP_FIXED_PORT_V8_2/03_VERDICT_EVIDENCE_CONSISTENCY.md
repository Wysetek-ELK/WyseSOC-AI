# 03 — Verdict-Evidence Consistency & Criteria Validation

**Module:** `backend/app/services/reasoning_integrity_engine.py` (`evaluate_verdict_consistency`)  
**Validator Check:** Check 4d in `backend/app/services/independent_verdict_validator.py`  
**Status:** Operational and Validated Live on Server 1  

---

## 1. Context & Motivation

Even when a model's free-text claims do not contain direct verbal contradictions (such as asserting "unanswered" vs "bidirectional"), the model's overall verdict (`TRUE_POSITIVE` vs `FALSE_POSITIVE` vs `REQUIRES_ATTENTION`) can still be logically inconsistent with the incident's holistic evidence profile.

In SOC environments, classifying routine outbound web browsing as a `TRUE_POSITIVE` horizontal network scan creates severe alert fatigue and analyst distrust. Conversely, reflexively dismissing internal host scanning as a `FALSE_POSITIVE` merely because the source IP is internal violates Core Principle 3 (*No Universal Benign Assumptions*), leaving internal adversary lateral movement undetected.

`evaluate_verdict_consistency` provides deterministic guardrails evaluating whether the proposed verdict meets the evidentiary threshold defined by the rule's approved investigation protocol.

---

## 2. True Positive Criteria Validation (`TP_CRITERIA_UNSATISFIED`)

### The External Browsing Anti-Pattern
Under FortiSIEM rule `PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`, when an enterprise workstation opens a rich web application (such as news portals, collaboration suites, or cloud dashboards), the browser establishes concurrent TCP/443 connections to dozens or hundreds of distinct CDN and web endpoints. When this exceeds the SIEM threshold (`COUNT(DISTINCT destIpAddr) >= 100`), an alert fires.

However, the underlying telemetry shows:
- Destination port: `443` (HTTPS) or `80` (HTTP).
- Firewall service/policy: `service=Browsing` or `service=HTTPS`, matching standard outbound web policies (`policy=Cybersecurity`, `policy=Cyble-Internet-Access`).
- Session state: `100%` bidirectional sessions with full 3-way handshakes (`bidirectional_sessions=100, unanswered_probes=0, denied_flows=0`).
- Scope: `100%` external routable IP addresses (`internal=0, external>0`).
- Attack tradecraft: Zero exploit alerts, zero brute-force attempts, zero lateral movement, zero C2 beacons.

### Enforcement Rule
If the model proposes `TRUE_POSITIVE` on an incident meeting all of the above conditions, `evaluate_verdict_consistency` raises a conflict:
> *"Verdict Conflict: Proposed TRUE_POSITIVE contradicts observed telemetry showing 100% external bidirectional browsing (bidirectional={B}, unanswered={U}, denied={D}, internal={I}, policy={P}; service={S}) without corroborating scan indicators, probe timeouts, or lateral attack tradecraft."*

**Outcome:**
- Validation Status: `REASONING_CONTRADICTION`
- Validation Reason Codes: `[VERDICT_EVIDENCE_CONFLICT, TP_CRITERIA_UNSATISFIED]`
- Trust Score: Capped at `<= 3/10`
- Effective Verdict: `REQUIRES_ATTENTION`

---

## 3. False Positive Criteria Validation (`FP_CRITERIA_UNSATISFIED`)

### The "Internal Traffic is Benign" Anti-Pattern
A frequent error in amateur triage is assuming that because a host has an RFC-1918 address (e.g. `10.x`, `172.16-31.x`, `192.168.x`), any port sweep it performs must be benign network administration or an authorized scanner. Adversaries routinely perform horizontal internal port sweeps (e.g. searching for vulnerable SMB `445`, SSH `22`, or WinRM `5985` ports) following initial access.

### Enforcement Rule
If the model proposes `FALSE_POSITIVE` for an incident with internal or mixed destination scope (`internal > 0`) without verified change management tickets, vulnerability scanner asset registration, or explicit administrative authorization cited in the telemetry:
> *"Verdict Conflict: Proposed FALSE_POSITIVE on internal/mixed host sweep without verified change ticket or scanner authorization."*

**Outcome:**
- Validation Status: `REASONING_CONTRADICTION`
- Validation Reason Codes: `[VERDICT_EVIDENCE_CONFLICT, FP_CRITERIA_UNSATISFIED]`
- Trust Score: Capped at `<= 3/10`
- Effective Verdict: `REQUIRES_ATTENTION`

---

## 4. Benchmark Verification Summary

In the real Local LLM V8.2 benchmark (`run_id = 2074b011-9fe8-46fb-9937-ff5ead18fc61`), this check fired with 100% precision:
- **`#176011`:** External browsing on port 443 (`bidirectional=100, internal=0, service=Browsing`) → Model proposed `TRUE_POSITIVE` → **Flagged `TP_CRITERIA_UNSATISFIED`**, overruled to `REQUIRES_ATTENTION`.
- **`#175129`:** External browsing on port 443 (`bidirectional=100, internal=0, service=Browsing`) → Model proposed `TRUE_POSITIVE` → **Flagged `TP_CRITERIA_UNSATISFIED`**, overruled to `REQUIRES_ATTENTION`.
- **`#164575`:** External browsing on port 443 (`bidirectional=100, internal=0, service=HTTPS`) → Model proposed `TRUE_POSITIVE` → **Flagged `TP_CRITERIA_UNSATISFIED`**, overruled to `REQUIRES_ATTENTION`.
- **`#167157`:** Mixed scope (`internal=2, external=30`) → Model proposed `REQUIRES_ATTENTION` → **Cleanly accepted as ABSTAINED**.
