# 06. POLICY QUALITY VALIDATOR

## Overview

The `PolicyQualityValidator` (`backend/app/services/policy_quality_validator.py`) is the deterministic safety checkpoint of Agent Intelligence Studio 2.0. Before any policy (whether auto-generated or manually edited) can be saved as an approval candidate, it must be evaluated against **8 Mandatory Quality Gates**.

---

## The 8 Mandatory Quality Gates

Each gate verifies a distinct dimension of policy soundness, safety, and operational feasibility:

```text
+-------------------------------------------------------------------------+
|                  THE 8 MANDATORY POLICY QUALITY GATES                   |
|                                                                         |
|  [ G1 ] Structural Integrity & Completeness Gate (HARD GATE)            |
|         - Verifies presence and substantive length of all 9 sections.   |
|         - Blocks approval if definition_status is INCOMPLETE.           |
|                                                                         |
|  [ G2 ] Archetype Relevance & Contradiction Gate (HARD GATE)            |
|         - Checks for prohibited concepts (e.g. malware in exfiltration).|
|         - Detects contradiction rules defined in the archetype registry.|
|                                                                         |
|  [ G3 ] Evidence Contract Feasibility Gate                              |
|         - Verifies that policy instructions only demand fields that     |
|           the Evidence Contract and data source actually support.       |
|                                                                         |
|  [ G4 ] True Positive Specificity Gate                                  |
|         - Ensures TP criteria require concrete observable evidence      |
|           rather than vague intuition or tautological statements.       |
|                                                                         |
|  [ G5 ] False Positive Benign Justification Gate                        |
|         - Verifies realistic benign business operations criteria.      |
|         - Rejects blanket whitelists (e.g. RFC-1918 automatic benign).  |
|                                                                         |
|  [ G6 ] Abstention & Escalation Boundary Gate                           |
|         - Ensures unambiguous guidance on when the model must ABSTAIN   |
|           due to missing telemetry, and when it must ESCALATE to human. |
|                                                                         |
|  [ G7 ] Internal Consistency & Non-Contradiction Gate                   |
|         - Detects conflicting instructions between TP and FP criteria   |
|           or between common baseline and rule-specific guidance.       |
|                                                                         |
|  [ G8 ] Historical Simulation & Regression Check Gate                   |
|         - Evaluates candidate policy against historical incident cases. |
|         - Blocks approval if accuracy degrades or regression occurs.    |
+-------------------------------------------------------------------------+
```

---

## Hard-Gate Failure Rule

Gates **G1** and **G2** are designated as **Hard Gates**:
- **G1 Failure:** If any required section is empty, if placeholders exist, or if the underlying detection semantics definition is `INCOMPLETE` (meaning authoritative SIEM conditions are unverified), G1 fails.
- **G2 Failure:** If an exfiltration policy instructs the model to inspect malware hashes, LOLBins, or parent processes without EDR correlation, G2 fails with `ARCHETYPE_RELEVANCE_MISMATCH`.

### Infallible Gating Rule:
$$\text{If } (\text{status}(G_1) = \text{FAIL} \lor \text{status}(G_2) = \text{FAIL}) \implies \text{approval\_eligible} = \text{False}$$

Even if a policy receives a quality score of 95/100 across other dimensions, a failure in G1 or G2 **immediately revokes approval eligibility**. The API will reject any attempt to promote the policy to `APPROVED` with HTTP 400 Bad Request.

---

## Gate Assessment Response Schema

Validation results are structured using `PolicyQualityAssessmentResponse` (`backend/app/schemas/policy_quality.py`):

```python
class PolicyQualityAssessmentResponse(BaseModel):
    rule_id: str
    version_id: Optional[str] = None
    overall_score: float                          # 0.0 to 100.0 inspection index
    validation_status: str                        # "PASSED" | "FAILED" | "WARNING"
    hard_gate_failure: bool                       # True if G1 or G2 failed
    approval_eligible: bool                       # True only if all gates pass / no hard fail
    gate_results: Dict[str, QualityGateResult]    # Detailed breakdown for G1 through G8
    blocking_findings: List[str]                  # Critical blockers that must be resolved
    warning_findings: List[str]                   # Non-blocking improvement recommendations
    sha256_digest: str                            # Cryptographic hash of evaluated policy
    evaluated_at: datetime
```

---

## Cryptographic Digest Tracking

To prevent race conditions and "bait-and-switch" approvals (where a policy is validated, edited, and approved without re-validation), `PolicyQualityValidator` computes a SHA-256 digest over the concatenated policy sections:

$$\text{digest} = \text{SHA256}(S_1 \parallel S_2 \parallel \dots \parallel S_9)$$

When `AgentPolicyEngine.approve_version()` is called, it recomputes the SHA-256 digest of the draft. If the digest does not match an active passing validation record, the approval transaction is aborted.
