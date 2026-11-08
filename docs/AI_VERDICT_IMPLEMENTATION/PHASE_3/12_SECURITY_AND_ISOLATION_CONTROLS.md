# 12. SECURITY & ISOLATION CONTROLS

**Document Identifier:** `AV-P3-DOC-12`  
**Requirement Mapping:** `P3-REQ-03`, `P3-REQ-04`, `P3-REQ-06`  
**Implementation Modules:** `app/services/verified_semantic_retrieval_service.py`, `app/services/token_budget_service.py`  

---

## 1. Zero Cloud Egress & Network Sandbox Compliance

Phase 3 introduces advanced semantic RAG and prompt optimization with **zero external cloud network dependencies**:
- Embedding generation and similarity ranking are computed 100% locally on Server 1.
- No public APIs, vendor telemetry endpoints, or external model hosts are contacted.
- Complies strictly with enterprise air-gap and sovereign data boundaries.

---

## 2. Multi-Tenant Memory Isolation

Security operations often span multiple corporate clients or organizational business units. A critical vulnerability in naive RAG systems is cross-tenant information leakage (e.g., Bank A's historical IP addresses or employee names appearing as few-shot examples for Bank B).

Phase 3 enforces strict tenant boundary checks:
- Every query checks the incident's customer/tenant identifier.
- Every candidate precedent must match the customer attribute.
- Cross-tenant candidates are immediately dropped, incrementing the `candidates_rejected_cross_tenant` diagnostic metric.

---

## 3. Training & Memory Poisoning Defense

Untrusted analyst feedback or malicious adversarial submissions can poison a RAG memory store.
Phase 3 enforces the **Supervisor Verification Gate**:
- Only records with `verification_status == "VERIFIED"` qualify as RAG candidates.
- Analyst feedback in status `PENDING_REVIEW`, `DISPUTED`, or `REJECTED` is strictly excluded.

