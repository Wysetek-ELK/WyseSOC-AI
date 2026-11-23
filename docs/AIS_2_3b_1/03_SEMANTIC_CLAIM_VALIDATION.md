# AIS 2.3b.1 — Semantic Claim Grounding Integrity

**Project:** Verdictum AI  
**Subsystem:** Agent Intelligence Studio (AIS)  
**Phase:** AIS 2.3b.1 (Wire Token Reservation & Semantic Verdict Grounding Integrity)  
**Date:** November 23, 2026  
**Status:** IMPLEMENTED & REGRESSION TESTED  

---

## 1. Problem Statement & Regression Case

In AIS 2.3b, the grounding engine suffered from a severe semantic loophole:
- **Model Claim:** *"The executing binary is not signed, and the process was blocked by the Crowdstrike agent, indicating potential malicious activity."*
- **Cited Evidence:** `EV-132527297-...-process_name` (`process.name = UltraViewer_Service.exe`)
- **Faulty Validation Outcome:** Marked as `GROUNDED` (`grounding_status = "GROUNDED"`).
- **Flaw:** The validator verified that the cited evidence ID existed and that `"UltraViewer_Service.exe"` matched the observed value. It failed to check whether the evidence proved the **factual predicate** (`"not signed"`). The telemetry contained NO signature information whatsoever.

---

## 2. Technical Architecture & Implementation

### 2.1 Complete Predicate Verification (`model_claim_extractor.py`)

A new semantic predicate validator `verify_semantic_predicate(claim, matched_record, all_records)` was added to `ModelClaimExtractor`. It enforces predicate-to-evidence compatibility across 5 distinct forensic domains:

```python
def verify_semantic_predicate(
    claim: ModelSupportingClaim,
    matched_record: Optional[CanonicalEvidenceRecord],
    all_records: List[CanonicalEvidenceRecord],
) -> Tuple[bool, str, Optional[str]]:
    # 1. Digital Signature Predicate
    # Claims asserting binary signing status (e.g. "not signed", "unsigned", "valid signature")
    # require explicit signature verification records (file.signature_status, digital_signature.*).
    if any(term in claim_lower for term in ("signed", "unsigned", "signature", "certificate", "signer")):
        has_sig = any(
            any(k in r.source_field.lower() for k in ("signature", "signed", "signer", "certificate"))
            for r in all_records
        )
        if not has_sig:
            return False, "UNSUPPORTED_PREDICATE", "Signature claim requires authentic digital signature record"

    # 2. Threat Intel & Reputation Predicate
    # Claims asserting malicious reputation require threat intelligence telemetry.
    if any(term in claim_lower for term in ("malicious", "blacklisted", "threat intel", "bad reputation")):
        has_ti = any(
            any(k in r.source_field.lower() for k in ("threat_intel", "reputation", "malicious_score"))
            for r in all_records
        )
        if not has_ti:
            return False, "UNSUPPORTED_PREDICATE", "Reputation claim requires threat intelligence record"

    # 3. Authorization & Administrative Maintenance Predicate
    # Claims asserting authorized maintenance require authorization evidence.
    if any(term in claim_lower for term in ("authorized", "legitimate tool", "maintenance", "admin approved")):
        has_auth = any(
            any(k in r.source_field.lower() for k in ("authorization", "change_request", "ticket"))
            for r in all_records
        )
        if not has_auth:
            return False, "UNSUPPORTED_PREDICATE", "Authorization claim requires authentic administrative record"

    # 4. Security Action Predicate
    # Control actions (block/quarantine/allow) must cite security.action or endpoint.*_blocked records.
    if any(term in claim_lower for term in ("blocked", "quarantined", "prevented", "terminated")):
        if not any(k in matched_field for k in ("action", "blocked", "quarantine")):
            return False, "UNSUPPORTED_PREDICATE", "Security action claim must cite security.action record"

    # 5. Evidence Type Compatibility
    # Claims asserting process execution cannot cite pure network IP or URL records.
    if "process" in matched_field and matched_record and matched_record.evidence_type == "NETWORK_CONNECTION":
        return False, "INCOMPATIBLE_EVIDENCE_TYPE", "Process execution claim cannot cite network connection record"

    return True, "GROUNDED", None
```

### 2.2 Hardened Validator Rules (`independent_verdict_validator.py`)

1. **Check 3 (Fail-Closed Rejection):** If any claim has `is_grounded is False` or `grounding_status == "UNSUPPORTED_PREDICATE"`, any model-proposed decisive verdict (`TRUE_POSITIVE` or `FALSE_POSITIVE`) is rejected and overruled to `REQUIRES_ATTENTION`.
2. **Check 5 (Control Actions Alone Do Not Prove Malice):** A security control block (`security.action = block`) indicates that a defense mechanism fired, but does not inherently prove that the binary was malicious. Decisive `TRUE_POSITIVE` verdicts require affirmative threat evidence (e.g. unauthorized execution, malicious payload, exfiltration).

---

## 3. Incident `132527297` Regression Re-Evaluation

When re-evaluated under the semantic grounding engine:
- **Claim 1:** *"Executing binary is not signed."* (cited: `process.name`)
  - `is_grounded`: `False`
  - `grounding_status`: `"UNSUPPORTED_PREDICATE"`
  - Reason: Process name alone does not prove signature status.
- **Claim 2:** *"Process was blocked by the Crowdstrike agent."* (cited: `security.action = block`)
  - `is_grounded`: `True`
  - `grounding_status`: `"GROUNDED"`
  - Note: Proves the block occurred, but does not prove malice.
- **Validator Decision:**
  - `proposed_verdict`: `TRUE_POSITIVE`
  - `effective_verdict`: `REQUIRES_ATTENTION`
  - `validation_status`: `REJECTED`
  - `validation_reason_codes`: `["UNSUPPORTED_PREDICATE", "UNSUPPORTED_CLAIM", "TP_CRITERIA_UNSATISFIED"]`
  - `is_decisive_accepted`: `False`

### Ground Truth Integrity:
Per project mandate: *"If the TP verdict for incident 132527297 changes after correcting the validator, record the actual outcome without forcing it to match historical ground truth."* The system faithfully records the rejected proposal rather than accepting an ungrounded claim.
