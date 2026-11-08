# AI Verdict — Phase 1: Policy Approval Enforcement & Auto-Promotion Elimination

**Requirement:** REQ-03  
**Audit Findings:** AV-001 (Template Draft Auto-Promotion to Active Inference) & AV-002 (Absence of Policy Approval Gate)  
**Status:** **VERIFIED & IMPLEMENTED**  

---

### 1. Threat Model & Vulnerability Analysis

In the pre-Phase 1 audit baseline:
1. When a new incident arrived with an unknown `event_type`, or when rules were synced from FortiSIEM, the system created a `Rule` and an associated `RulePrompt`.
2. The system generated a template draft policy (`PromptVersion(status="DRAFT")`).
3. Immediately thereafter, `ingestion_service.py` and `fortisiem_service.py` executed:
   `rp.active_version_id = draft.id`
4. When `ai_verdict_service.py` evaluated the incident, it fetched `rp.active_version_id` without verifying whether `candidate.status == "APPROVED"`.
5. Consequently, auto-generated, unreviewed, unoptimized prompt drafts immediately governed production AI verdict decisions without human SOC lead review or approval.

---

### 2. Architecture of Implemented Solution

```mermaid
stateDiagram-v2
    [*] --> IngestRule: SIEM Rule Sync / Incident Ingestion
    IngestRule --> CreateDraft: generate_template_draft()
    CreateDraft --> DraftStatus: PromptVersion created with status='DRAFT'
    Note over DraftStatus: active_version_id remains NULL.<br/>No auto-promotion.

    state "Live Incident Triage" as LiveTriage {
        CheckActive: Resolve active_version_id
        CheckApproval: Verify version.status == 'APPROVED'
        CheckActive --> CheckApproval: Version ID present
        CheckApproval --> ExecuteInference: Yes (Approved)
        CheckApproval --> Abstain: No (Draft or None)
        CheckActive --> Abstain: No active version
    }

    state Abstain {
        SetVerdict: verdict = REQUIRES_ATTENTION
        SetStatus: validation_status = POLICY_NOT_APPROVED
        SetConfidence: confidence = 0.0
        SetReason: reason = DETECTION_POLICY_PENDING_APPROVAL
    }

    state "Simulation Lab Sandbox" as SimLab {
        AnalystTestsDraft: evaluate_incident(allow_simulated_fallback=True)
        LoadDraft: Load draft version for sandbox test
        ReturnLabVerdict: Render simulation result for analyst review
    }

    DraftStatus --> SimLab: Tested in Simulation Lab
    SimLab --> ApprovedStatus: SOC Lead Approves via Studio (POST /approve)
    ApprovedStatus --> LiveTriage: Active for Live Production Triage
```

---

### 3. Source Code Modifications

#### `backend/app/services/ingestion_service.py`
In `get_or_create_rule()`:
```python
# Auto-generate an initial draft prompt template with specialized criteria
draft = await prompt_service.generate_template_draft(rule_id=rule.id, user_id=None)

# REQ-03 (AV-001 & AV-002): In Phase 1, newly generated drafts remain strictly in DRAFT status.
# The active_version_id is NOT auto-promoted. An Administrator or SOC Lead must approve
# the prompt version in Agent Intelligence Studio before it governs live incident triage.
# (Auto-assignment rp.active_version_id = draft.id permanently removed)
```

#### `backend/app/services/fortisiem_service.py`
In `sync_rules_from_fortisiem()`:
```python
draft = await prompt_service.generate_template_draft(rule_id=rule.id, user_id=None)
# REQ-03 (AV-001 & AV-002): Auto-promotion permanently removed.
# Draft policy remains in DRAFT status pending human approval.
```

#### `backend/app/services/ai_verdict_service.py`
In `VerdictTriageAgent.evaluate_incident()`:
```python
if rule:
    rp = await prompt_service.get_or_create_rule_prompt(rule.id)
    active_v = None
    if rp and rp.active_version_id and rp.versions:
        candidate = next((v for v in rp.versions if v.id == rp.active_version_id), None)
        if candidate and candidate.status == "APPROVED":
            active_v = candidate

    # REQ-03 (AV-001 & AV-002): Refuse to evaluate with unapproved prompt drafts in live triage
    if not active_v:
        if not allow_simulated_fallback or is_prod:
            verdict_data = {
                "incident_id": incident.incident_id,
                "verdict": "REQUIRES_ATTENTION",
                "confidence": 0.0,
                "reason": "DETECTION_POLICY_PENDING_APPROVAL: No approved investigation policy exists for this detection rule. Triage deferred to human analyst.",
                "supporting_evidence": [],
                "missing_evidence": ["Approved detection rule investigation policy (Studio approval required)"],
                "analyst_questions": ["Please review and approve the detection policy in Agent Intelligence Studio."],
                "latency_ms": 0,
                "model_identifier": "POLICY_GUARD",
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "is_simulated": False,
                "validation_status": "POLICY_NOT_APPROVED",
                "rule_name": rule.name if rule else incident.title,
                "severity": incident.severity,
                "evaluated_at": datetime.utcnow().isoformat(),
                "evaluated_by_user": username,
            }
            incident.ai_verdict = verdict_data
            self.db.add(incident)
            ...
            return verdict_data
        else:
            # In simulation / test mode (Simulation Lab), allow testing with draft version if available
            if rp and rp.versions:
                active_v = rp.versions[0]
```

---

### 4. Verification & Testing

Tests implemented in `backend/tests/test_phase1_security_controls.py`:
- `test_req03_unapproved_prompt_draft_abstained_in_live_triage`:
  - Ingests a rule with a `RulePrompt` containing only a `DRAFT` version (`active_version_id = None`).
  - Calls `evaluate_incident(..., allow_simulated_fallback=False)`.
  - Asserts that the returned verdict is `REQUIRES_ATTENTION`.
  - Asserts `validation_status == "POLICY_NOT_APPROVED"`.
  - Asserts `confidence == 0.0`.
  - Asserts reason contains `"DETECTION_POLICY_PENDING_APPROVAL"`.
  - Asserts that model inference is bypassed safely.

