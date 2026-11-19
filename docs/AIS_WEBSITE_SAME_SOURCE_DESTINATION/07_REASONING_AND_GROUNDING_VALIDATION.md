# 07 — Reasoning Integrity & Grounding Validation
**Target Rule:** `Website access policy violation: Same Source and Destination`  
**Rule UUID:** `7bd13e89-0828-48e6-8cf5-f3cbf12d438c`  
**Subsystems:** `IndependentVerdictValidator`, `ReasoningIntegrityEngine`, `ModelClaimExtractor`, `ConfidenceNormalizer`  

---

## 1. Architectural Safeguards for `POLICY_VIOLATION`

AIS 2.0 incorporates deterministic guardrails to prevent AI hallucinations, factual inversions, and ungrounded claims from reaching production analysts or automating actions. 

Crucially, **scan-specific heuristics (developed for `Heavy TCP Host Scan`) are decoupled from web access policy rules**:
- Heuristics such as `scan.tcp_behavior_summary`, `scan.destination_scope`, and horizontal port sweep metrics apply strictly to `NETWORK_SCAN`.
- For `POLICY_VIOLATION`, specialized reasoning validation rules enforce web filtering and acceptable use invariants.

---

## 2. Specialized Guardrail Checks

### Check A: Loopback Inversion Defense (`LOOPBACK_CLAIMED_ON_EXTERNAL_TRAFFIC`)
- **Vulnerability:** Uncalibrated models frequently interpret the FortiSIEM rule name *"Same Source and Destination"* as meaning that source IP equals destination IP (loopback `127.0.0.1` or localhost reflection).
- **Enforcement Logic:**
  ```python
  if loopback_claim_pattern.search(narrative_lower):
      if src_ip and dst_ip and src_ip != dst_ip and not dst_ip.startswith("127."):
          contradictions.append(
              f"Contradiction: Model asserted identical source and destination IP / loopback traffic, "
              f"but observed telemetry confirms distinct source ({src_ip}) and destination ({dst_ip}). "
              f"Rule grouping 'Same Source and Destination' reflects FortiSIEM correlation aggregation criteria, not loopback."
          )
          reason_codes.append("LOOPBACK_CLAIMED_ON_EXTERNAL_TRAFFIC")
  ```
- **Validation Outcome:** Validated; any narrative attempting to close an alert as a "benign loopback" when destination is external is immediately overruled to `REQUIRES_ATTENTION`.

### Check B: Firewall Action Semantics Inversion (`FIREWALL_ACTION_CONTRADICTION`)
- **Vulnerability:** Models claiming that web requests were "allowed", "successfully accessed", or "sessions established" despite perimeter firewall block telemetry.
- **Enforcement Logic:**
  ```python
  is_blocked_action = any(term in action_val for term in ("blocked", "denied", "dropped")) or "cat-blk" in event_type_val
  if asserts_allowed_pattern.search(narrative_lower) and is_blocked_action:
      contradictions.append(
          f"Contradiction: Model asserted traffic was allowed or session successfully established, "
          f"but observed telemetry confirms action='{action_val}' and eventType='{event_type_val}'."
      )
      reason_codes.append("REASONING_CONTRADICTION")
  ```
- **Validation Outcome:** Validated; prevents models from confusing blocked attempts with successful connections.

### Check C: Evidence-Backed Policy Exception Verification
- **Vulnerability:** Models asserting that a user had an "approved business exemption" or "authorized change ticket" without any canonical record of approval.
- **Enforcement Logic:** Under `clean_prop == "FALSE_POSITIVE"`, `ReasoningIntegrityEngine.verify_authorization` inspects canonical records for verified change management tickets (`CHG-*`, `RFC-*`) or affirmative approval flags. Narrative claims unsupported by evidence are rejected with `FP_CRITERIA_UNSATISFIED`.
- **Validation Outcome:** Validated in live benchmark on Incident `#4176`, where a raw FP proposal lacking affirmative authorization records was overruled to `REQUIRES_ATTENTION`.

---

## 3. Grounding Verification & Claim Extraction

`ModelClaimExtractor` parses each sentence of the model narrative and extracts factual assertions:
1. **Assertion Types:** `OBSERVED_FACT`, `NETWORK_CONNECTION`, `POLICY_ASSERTION`, `ACTION_ASSERTION`.
2. **Grounding Status:** Each assertion is matched against normalized canonical evidence records (`EV-*`). If an assertion cites an unobserved IP, non-existent user, or unverified URL, it is classified as `UNGROUNDED` or `FABRICATED`.
3. **Completeness Threshold:** If grounded claims ratio $< 0.60$ or critical security tradecraft claims are missing, decisive verdicts are suppressed.

---

## 4. Rejection & Overruling Matrix

| Validation Test Case | Injected / Observed Condition | Guardrail Triggered | Outcome |
| :--- | :--- | :--- | :--- |
| **Unsupported Loopback Claim** | Client `172.26.29.74` -> `151.101.131.42`; Model claims "internal loopback" | `LOOPBACK_CLAIMED_ON_EXTERNAL_TRAFFIC` | **REJECTED** $\to$ Overruled to `REQUIRES_ATTENTION` |
| **Firewall Action Inversion** | Action is `blocked`; Model claims "user accessed website successfully" | `FIREWALL_ACTION_CONTRADICTION` | **REJECTED** $\to$ Overruled to `REQUIRES_ATTENTION` |
| **Invented Change Ticket** | Model asserts ticket `CHG-99882` not in canonical records | `verify_authorization` ticket check | **REJECTED** $\to$ Overruled to `REQUIRES_ATTENTION` |
| **Routine Traffic as False Positive** | Blocked request to LinkedIn/Skype; Model claims "routine browsing" | `FP_CRITERIA_UNSATISFIED` | **REJECTED** $\to$ Overruled to `REQUIRES_ATTENTION` (Verified in #4176) |
| **Header-Only Alert** | Zero raw logs (`event_count == 0`); Model proposes decisive TP/FP | `INSUFFICIENT_EVIDENCE` check | **ABSTAINED** $\to$ Governed to `REQUIRES_ATTENTION` (Verified in #4148, #4145) |
