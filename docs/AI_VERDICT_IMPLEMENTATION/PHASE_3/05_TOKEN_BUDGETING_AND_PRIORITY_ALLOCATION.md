# 05. TOKEN BUDGETING & PRIORITY ALLOCATION

**Document Identifier:** `AV-P3-DOC-05`  
**Requirement Mapping:** `P3-REQ-05` (Evidence-Preserving Prompt Optimization & Token Budgeting), Finding `AV-009`  
**Implementation Modules:** `app/services/token_budget_service.py`, `app/schemas/token_budget.py`  

---

## 1. Problem Statement & Finding AV-009 Review

In many naive LLM integrations, prompt truncation indiscriminately slices text when token limits are reached. In security triage, this results in catastrophic failure modes:
- Slicing off command lines midway through obfuscated parameters.
- Truncating SHA-256 file hashes or destination IP addresses.
- Dropping Evidence IDs (EV-01, EV-02), causing subsequent claim extraction to fail.
- Slicing off critical policy directives or safety instructions.

---

## 2. Seven-Tier Priority Hierarchy

`TokenBudgetService.budget_prompt` enforces a strict 7-tier allocation priority:

| Priority | Component | Mutability | Behavior During Budget Pressure |
| :--- | :--- | :--- | :--- |
| **P1** | System Safety & JSON Output Schema | **IMMUTABLE** | Never truncated or dropped under any circumstances. |
| **P2** | Approved Policy Directives (Sections 1-9) | **IMMUTABLE** | Never truncated or dropped. |
| **P3** | Mandatory Evidence Contract Criteria | **IMMUTABLE** | Never truncated or dropped. |
| **P4** | Critical Telemetry & Canonical Evidence IDs | **IMMUTABLE** | Never sliced or truncated. Raw command lines preserved. |
| **P5** | Correlated Secondary Events | **TRIMMABLE** | Pruned from oldest/secondary events, preserving primary trigger event. |
| **P6** | Optional Enrichment Fields | **TRIMMABLE** | Removed if context exceeds available budget. |
| **P7** | Historical RAG Precedents | **TRIMMED FIRST** | RAG block is dropped first if budget is constrained. |

---

## 3. Context Window Overrun Handling

When token budgeting operates:
1. Available budget = `max_context_tokens - max_completion_tokens`.
2. If `total_tokens > available_budget`:
   - Step 1: Drop P7 (RAG precedents).
   - Step 2: Drop P6 (Optional enrichment).
   - Step 3: Prune P5 (Secondary events, keeping primary event).
3. If after Steps 1-3, the mandatory core (P1 + P2 + P3 + P4) STILL exceeds the available budget:
   - **The service refuses naive truncation.**
   - Sets `can_proceed_to_inference = False`.
   - Flags `context_overflow_detected = True`.
   - Safely abstains to `REQUIRES_ATTENTION` with `validation_status: "CONTEXT_WINDOW_EXCEEDED"`.
   - Directs the analyst to inspect raw logs directly in the SIEM console.

