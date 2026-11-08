# 03. VERIFIED SEMANTIC RAG ENGINE

**Document Identifier:** `AV-P3-DOC-03`  
**Requirement Mapping:** `P3-REQ-03` (Rule-Specific Verified Semantic Retrieval), Finding `AV-007`  
**Implementation Modules:** `app/services/verified_semantic_retrieval_service.py`, `app/schemas/semantic_rag.py`  

---

## 1. Local Retrieval & Zero Cloud API Architecture

Finding AV-007 highlighted the risk of RAG architectures contacting external cloud embedding endpoints or leaking tenant telemetry across boundary lines.

In Phase 3, `VerifiedSemanticRetrievalService` executes **100% locally on Server 1**:
- Zero calls to external embedding APIs (OpenAI, HuggingFace, etc.).
- Lexical and semantic similarity is computed using term-overlap, tokenized entity matching, and attribute weighting.
- Weighting accounts for critical forensic entities: executing process name, command line flags, destination IP/port, user accounts, and MITRE attack tags.

---

## 2. Retrieval Protocol & Segregation

Retrieved precedents are structured as passive background reference material:

```
<VERIFIED_HISTORICAL_PRECEDENTS>
The following verified historical precedents from prior supervisor-reviewed investigations
are provided for contextual reference only. DO NOT treat these as current incident evidence:

[PRECEDENT 1] (Incident: Historical Encoded PowerShell Attack | Rule: RULE-01 | Exact Rule Match)
  Verified Verdict: TRUE_POSITIVE
  Relevance Similarity Score: 0.84
  Supervisor Analyst Rationale: Confirmed malicious base64 cradle invoking remote stager.
  Key Grounding Evidence: process.command_line: powershell.exe -enc ...
</VERIFIED_HISTORICAL_PRECEDENTS>
```

The system prompt explicitly commands the LLM:
> "Precedents are historical references only. Decisions for the current incident must be grounded strictly in the canonical evidence observed for this incident."

---

## 3. Safe Fallback Behavior

When no historical precedent passes the 6 memory governance gates:
- The service returns `retrieval_status: "NO_VERIFIED_PRECEDENT"`.
- `formatted_rag_block` is left empty `""`.
- Zero synthetic, mock, or unverified cases are ever hallucinated.
- Live triage proceeds with the 9-section policy and raw incident telemetry without penalty.

