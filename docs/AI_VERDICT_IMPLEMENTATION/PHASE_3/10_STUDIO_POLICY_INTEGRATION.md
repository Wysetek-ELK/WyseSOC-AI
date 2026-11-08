# 10. STUDIO POLICY INTEGRATION

**Document Identifier:** `AV-P3-DOC-10`  
**Requirement Mapping:** `P3-REQ-01`, `P3-REQ-02` (Agent Intelligence Studio Policy Compilation)  
**Implementation Modules:** `app/services/prompt_studio_service.py`, `app/api/rules.py`  

---

## 1. Role of Agent Intelligence Studio

Agent Intelligence Studio serves as the human-in-the-loop governance control plane for enterprise SOC policies. Senior detection engineers author, test, and approve rule-specific prompts across the 9 sections:
- Common SOC Baseline Protocol
- Rule Directive
- Detection Conditions
- Required Evidence Checklist
- True Positive Indicators
- False Positive Indicators
- Abstention Criteria
- Escalation Conditions
- Analyst Questions

---

## 2. Integrated Compilation Method

In Phase 3, `PromptStudioService` (`AgentPolicyEngine`) incorporates `compile_active_policy(rule_id: str, execution_mode: str = "LIVE")`:

```python
compiled = await prompt_studio_service.compile_active_policy(
    rule_id=rule.id,
    execution_mode="LIVE"
)
```

The service retrieves the active prompt version, verifies its status, and compiles the 9 sections into the deterministic `CompiledPolicyPrompt` specification.

---

## 3. Dedicated API Endpoints

- `GET /api/rules/{identifier}/compiled-policy?execution_mode=LIVE`:
  - Returns the full 9-section compiled policy prompt, compiler version (`v3.0.0`), compilation digest, section breakdown, and JSON output schema.
- `GET /api/rules/{identifier}/calibration-report`:
  - Returns the empirical evaluation metrics (Precision, Recall, FNR, ECE, Brier score) and honest calibration status.

