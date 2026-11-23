# AIS 2.3b.1 — Evidence Availability Reconciliation & Forensic Lifecycle

**Project:** Verdictum AI  
**Subsystem:** Agent Intelligence Studio (AIS)  
**Phase:** AIS 2.3b.1 (Wire Token Reservation & Semantic Verdict Grounding Integrity)  
**Date:** November 23, 2026  
**Status:** RECONCILED & DOCUMENTED  

---

## 1. Forensic Evidence Lifecycle Taxonomy

To resolve discrepancies where evidence is available in raw telemetry but hallucinated as "missing" by model reasoning or omitted during compaction, AIS 2.3b.1 establishes a seven-stage formal lifecycle:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      Seven-Stage Evidence Lifecycle                     │
│                                                                        │
│  [Stage 1] NOT_IN_RAW_SOURCE                                           │
│       │ (Attribute absent from raw SIEM/EDR log)                       │
│       ▼                                                                │
│  [Stage 2] PRESENT_IN_RAW_SOURCE                                       │
│       │ (Attribute physically exists in source event payload)          │
│       ▼                                                                │
│  [Stage 3] NORMALIZATION_MISSING                                       │
│       │ (Source has attribute, but normalizer lacks rule mapping)      │
│       ▼                                                                │
│  [Stage 4] PRESENT_IN_NORMALIZED_EVIDENCE (PRESENT_VALID)              │
│       │ (Mapped into CanonicalEvidenceRecord with integrity digest)    │
│       ▼                                                                │
│  [Stage 5] OMITTED_FROM_PROMPT                                         │
│       │ (Evicted during token budget compaction or secondary pruning)  │
│       ▼                                                                │
│  [Stage 6] PRESENT_IN_PROMPT                                           │
│       │ (Included in model-facing prompt payload)                      │
│       ▼                                                                │
│  [Stage 7] VERIFIED_CLAIM / UNSUPPORTED_CLAIM                          │
│         (Extracted and validated against canonical ground truth)       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. SHA256 Availability Reconciliation for Incidents `132438483` & `132527297`

### 2.1 The Discrepancy
In AIS 2.3b evaluation reports:
- Telemetry preflight validation recorded `file.hash_sha256 = PRESENT_VALID`.
- However, model reasoning for Incident `132438483` stated: *"Missing process.parent_command_line and file.hash_sha256. Additional evidence is required..."*
- This raised the question: Was the hash actually present, or was it lost between raw ingestion and model prompt?

### 2.2 Forensic Trace of `file.hash_sha256`

1. **Raw Event:**
   In raw FortiSIEM JSON `IncidnetId_132438483.json`, the CrowdStrike event payload contains:
   ```json
   "attribute": {
       "SHA256 Hash": "10ff43f2d4a991c83caefce1c4442fa95258d0d93f168dde339f52322aa371e9"
   }
   ```
   *Stage:* `PRESENT_IN_RAW_SOURCE`

2. **Normalized Evidence:**
   `EvidenceNormalizationService` aliased `"SHA256 Hash"` to canonical field `file.hash_sha256` with record ID `EV-132438483-6887129733007838820-file_hash_sha256`.
   *Stage:* `PRESENT_IN_NORMALIZED_EVIDENCE` (`validation_status = "PRESENT_VALID"`)

3. **Prompt Budgeting & Compaction:**
   In `TokenBudgetService`, `file.hash_sha256` is defined in `CORE_PROTECTED_FIELDS` and was **never evicted**. It was transmitted in `canonical_evidence` inside the user message.
   *Stage:* `PRESENT_IN_PROMPT`

4. **Model Rationale Discrepancy:**
   The model generated a hallucinated claim of missing evidence:
   *"Missing process.parent_command_line and file.hash_sha256."*
   The hash was present in `canonical_evidence[9]`, but the model overlooked it due to the length of the surrounding context.

---

## 3. Contradiction Detection Mechanism (Check 4e)

To catch such reasoning hallucinations, `IndependentVerdictValidator` implements **Check 4e: Cross-Examination of Model Assertions**:

```python
# Check 4e: Detect negative reasoning assertions contradicting available telemetry
negative_patterns = [
    r"(?:missing|lacks?|no|without|absence of)\s+(?:the\s+)?([a-z_0-9.]+)",
]
for pat in negative_patterns:
    for match in re.finditer(pat, model_reason.lower()):
        field_asserted_missing = match.group(1).strip()
        # If field is canonical and status is PRESENT_VALID, flag contradiction
        if field_asserted_missing in field_status:
            if field_status[field_asserted_missing] == "PRESENT_VALID":
                detected_contradictions.append(
                    f"Model rationale claims '{field_asserted_missing}' is missing, "
                    f"but telemetry confirms it is PRESENT_VALID."
                )
```

### Result:
When the model asserts that a critical field is missing, but canonical evidence proves it is present and valid, the validator flags `EVIDENCE_CONTRADICTION` and `REASONING_CONTRADICTION`, preventing unjustified escalation or false consensus.
