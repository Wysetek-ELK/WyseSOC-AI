# WyseSOC AI — False-Positive Criteria Validation Audit

**Document:** `07_FALSE_POSITIVE_VALIDATION_AUDIT.md`  
**Platform:** WyseSOC AI (Verdictum AI)  
**Target Incident ID:** 176061 (`68ec2d89-d8d3-4c5c-9aec-ec6ea77a1eff`)  
**Affected Service:** `IndependentVerdictValidator` (`backend/app/services/independent_verdict_validator.py`)  
**Status:** AUDITED, REMEDIATED & VERIFIED  

---

## 1. Incident 176061 Context and Observed Behavior

### 1.1 Observed AI Verdict
- **Model Determination:** `REQUIRES ATTENTION`
- **Effective Confidence:** `0.0%`
- **Proposed Verdict:** `FALSE_POSITIVE` (Model Confidence: `85.0%`)
- **Validation Codes:** `EVIDENCE_VALUE_MISMATCH`, `FP_CRITERIA_UNSATISFIED`
- **Reported Missing Evidence:** `network.source_ip`, `http.url`, `http.method`, `http.status_code`, `webCategory`

### 1.2 The Hallucinated Loopback Hypothesis
The detection rule triggering Incident #176061 was titled:
`Website access policy violation: Same Source and Destination`

When `Qwen/Qwen2.5-7B-Instruct-AWQ` processed this prompt:
1. The model was heavily biased by the title phrase `"Same Source and Destination"`.
2. It hypothesized that an endpoint was communicating with itself (internal loopback traffic or misconfigured local proxy).
3. Based on this hypothesis, it proposed a `FALSE_POSITIVE` verdict with 85.0% raw confidence, asserting that internal loopback traffic does not constitute a real security threat.
4. When citing supporting evidence for this claim, it referenced evidence ID `EV-176061-TOP-event_timestamp` instead of an actual IP address equality record.

### 1.3 Telemetry Reality
Examination of the raw event telemetry reveals that the traffic was **not** loopback:
- **Source IP:** `192.0.2.48` (Internal workstation on LAN `port2`).
- **Destination IP:** `198.51.100.32` (External public IP in the Netherlands, owned by Fastly/Giphy).
- **Target URL:** `https://media4.giphy.com/`
- **Category:** `Entertainment`
- **Action:** `blocked` (FortiGate webfilter dropped the connection).

The incident was an internal user attempting to browse an entertainment website that was blocked by corporate web-filtering policy. The FortiSIEM rule name `"Same Source and Destination"` was a misleading or generic rule description, but the model blindly treated the rule title as empirical truth rather than checking the verified IP fields.

---

## 2. Independent Verdict Validator Analysis

The system behaved with exceptional safety:
1. `ModelClaimExtractor` verified the cited evidence ID against the canonical store and detected that the model cited a timestamp to substantiate an IP identity claim $\to$ Flagged `EVIDENCE_VALUE_MISMATCH`.
2. `IndependentVerdictValidator` evaluated the proposed `FALSE_POSITIVE` verdict against required FP criteria. Because the loopback claim was ungrounded, it flagged `FP_CRITERIA_UNSATISFIED`.
3. The validator **neutralized the unverified false-positive proposal**, setting effective confidence to `0.0%` and downgrading the disposition to `REQUIRES_ATTENTION`.
4. This prevented an unvalidated security exception from being automatically approved or closed without human oversight.

---

## 3. Implemented Remediation

### 3.1 Loopback Contradiction Rule
Added an explicit telemetry contradiction check in `IndependentVerdictValidator`:
```python
# Contradiction: Loopback claimed when endpoints differ
if proposed_verdict == "FALSE_POSITIVE":
    reasoning_lower = (reason + " " + " ".join(supporting_evidence)).lower()
    if any(k in reasoning_lower for k in ["loopback", "same source and destination", "internal self-communication"]):
        src_ip = canonical_dict.get("network.source_ip")
        dst_ip = canonical_dict.get("network.destination_ip")
        if src_ip and dst_ip and src_ip != dst_ip:
            contradictions.append("LOOPBACK_CLAIMED_ON_EXTERNAL_TRAFFIC")
            validation_codes.append("CONTRADICTION_LOOPBACK_EXTERNAL")
```

### 3.2 Gating Criteria for False Positives
To accept a `FALSE_POSITIVE` verdict:
1. **Zero Contradictions:** No asserted claim may contradict verified telemetry.
2. **Grounding Ratio = 1.0:** Every factual assertion must be grounded in verified canonical evidence.
3. **Affirmative Benign Evidence:** The evidence must demonstrate an authorized activity (e.g., verified vulnerability scanner, scheduled administrative maintenance, authorized health check).
4. **No Assumption-Based Decisions:** If evidence is missing or ambiguous, the model must not infer benignity; it must abstain with `REQUIRES_ATTENTION`.

---

## 4. Automated Test Verification

| Test ID | Scenario | Verification Method | Status |
|---|---|---|---|
| **T08** | Validated false-positive scenario | Legitimate vulnerability scan with verified scanner IP $\to$ Accepted | PASS |
| **T09** | Hallucinated model evidence | Model invents unobserved log line $\to$ Neutralized | PASS |
| **T13** | Benign claim without supporting evidence | Model claims "benign routine traffic" without proof $\to$ Rejected with `REQUIRES_ATTENTION` | PASS |
| **T15** | Validated false-positive criteria | All criteria satisfied $\to$ Decisive FP approved | PASS |
