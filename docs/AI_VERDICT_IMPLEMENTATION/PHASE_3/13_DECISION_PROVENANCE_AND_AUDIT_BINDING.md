# 13. DECISION PROVENANCE & AUDIT BINDING

**Document Identifier:** `AV-P3-DOC-13`  
**Requirement Mapping:** `P3-REQ-01`, `P3-REQ-08`  
**Implementation Modules:** `app/services/independent_verdict_validator.py`, `app/services/policy_compiler_service.py`  

---

## 1. Audit Verification Token Hardening

In the Phase 2 implementation, the audit replay signature was formulated as:
`f"{incident_id}:{contract.contract_id}:{proposed_verdict}:{final_verdict}:{validator_version}"`

While effective for contract tracking, it did not cryptographically bind the policy prompt digest.

Phase 3 upgrades the formula into a hardened **Audit Verification Token**:

$$\text{Token Data} = \text{incident\_id} : \text{contract\_id} : \text{proposed\_verdict} : \text{final\_verdict} : \text{validator\_version} : \text{compilation\_digest}$$

$$\text{Replay Token} = \text{SHA256}(\text{Token Data})[:16]$$

---

## 2. Provenance Chain

Every decisive or abstained verdict emitted by the AI Verdict Engine can now be audited back through an unbroken chain of cryptographic proofs:

1. **Incident Telemetry Snapshot:** Normalized canonical evidence records with SHA-256 field digests (`EV-01`, `EV-02`).
2. **Evidence Contract Revision:** Contract ID and revision number bound to rule archetype.
3. **Compiled Policy Specification:** 9-section deterministic SHA-256 digest (`compilation_digest`).
4. **Independent Validation Result:** Validation reason codes, grounding ratio, and decisive status.
5. **Audit Verification Token:** Cryptographically binds all components into the immutable incident record.

