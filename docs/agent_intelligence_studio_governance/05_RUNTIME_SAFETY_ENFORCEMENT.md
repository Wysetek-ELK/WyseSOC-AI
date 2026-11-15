# Report 05 — Runtime Safety & Pipeline Enforcement

## 1. Authoritative Eligibility Engine

To prevent flawed or unapproved policies from reaching Server 2 (Local LLM), runtime eligibility evaluation was centralized in `PolicyEligibilityService` (`backend/app/services/policy_eligibility_service.py`).

### Evaluation Flow
Before compiling a prompt or constructing an outbound LLM request, `PolicyEligibilityService.evaluate_eligibility` executes a hierarchical check:

1. **Rule Suspension Check:**
   - If `rule_prompt.ai_execution_suspended == True`, return `is_eligible=False`, `status="RULE_SUSPENDED"`, `reason_code="RULE_AI_EXECUTION_SUSPENDED"`.
2. **Policy Revocation Check:**
   - If `target_version.status == "REVOKED"`, return `is_eligible=False`, `status="POLICY_REVOKED"`, `reason_code="POLICY_REVOKED"`.
3. **Approval Status Check (Production Mode):**
   - If `target_version.status == "DRAFT"` and `not is_simulation`, return `is_eligible=False`, `status="DRAFT_NOT_APPROVED"`, `reason_code="DRAFT_NOT_APPROVED"`.
4. **Semantic Mismatch Check:**
   - Evaluates `detect_semantic_mismatch(rule, target_version)`.
   - If a `NETWORK_SCAN` rule contains process/endpoint malware instructions, return `is_eligible=False`, `status="SEMANTIC_MISMATCH"`, `reason_code="SEMANTIC_MISMATCH"`.
5. **Quality Gates Check:**
   - Evaluates `target_version.quality_status` and gate results. If hard blockers exist, returns `is_eligible=False`.
6. **Pass:** Returns `is_eligible=True`, `status="ELIGIBLE"`.

---

## 2. Verdict Pipeline Interception

In `verdict_pipeline.py` (`run_shared_verdict_pipeline`):
```python
    # Phase 3 Governance & Eligibility Gate
    eligibility = await PolicyEligibilityService.evaluate_eligibility(
        db=db,
        rule=rule,
        candidate_version=prompt_version,
        active_approved_version=active_approved_version,
        is_simulation=is_simulation,
    )

    if not eligibility.is_eligible and not is_simulation:
        deferral_detail = f"{eligibility.reason_code}: {eligibility.explanation}"
        verdict_data = {
            "incident_id": incident.incident_id,
            "proposed_verdict": "REQUIRES_ATTENTION",
            "verdict": "REQUIRES_ATTENTION",
            "confidence": 0.0,
            "reason": deferral_detail,
            "missing_evidence": [eligibility.explanation],
            "analyst_questions": ["Please inspect policy status and governance gates in Agent Intelligence Studio."],
            "model_identifier": "POLICY_GUARD",
            "is_simulated": False,
            "execution_provenance": "POLICY_GUARD",
            "configured_provider": "POLICY_GUARD",
            "validation_status": eligibility.status,
            "is_decisive_accepted": False,
            "proposal_validation_outcome": eligibility.status,
            "final_disposition": "DEFERRED",
            "abstention_reason": deferral_detail,
        }
        await _record_intercept(verdict_data, deferral_detail)
        return VerdictPipelineResult(
            verdict_data=verdict_data,
            early_exit=True,
            early_exit_kind=eligibility.reason_code,
            norm_result=norm_result,
            certification=cert_empty,
            is_abstained=True,
            effective_verdict="REQUIRES_ATTENTION",
            proposed_verdict="REQUIRES_ATTENTION",
            escalation_reason=deferral_detail,
        )
```

### Safety Guarantees
- **Zero Local LLM Outbound Traffic:** Server 2 is never pinged or contacted when a rule is suspended, revoked, unapproved, or semantically mismatched.
- **Fail-Safe Abstention:** Incidents are marked `REQUIRES_ATTENTION` with `confidence: 0.0` and escalated to human L1/L2 analysts.
- **Uninterrupted SIEM Ingestion:** Syslog parsing, alert intake, and database persistence operate continuously without failure.

---
*Report Completed on 2026-11-15.*
