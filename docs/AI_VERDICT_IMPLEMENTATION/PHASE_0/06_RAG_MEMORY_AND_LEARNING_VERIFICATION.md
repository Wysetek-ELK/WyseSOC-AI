# 06. RAG, Memory, and Learning Verification (Task F)

## 1. Executive Summary

This report verifies the adaptive memory, feedback, and Retrieval-Augmented Generation (RAG) subsystem in AI Verdict. Governed by [`learning_service.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/learning_service.py) (`AgentMemoryEngine`) and [`learning.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/api/learning.py), the subsystem captures analyst feedback on AI verdicts and injects historical precedent cases into live LLM prompts.

Our source-code verification confirms severe context contamination, cross-rule leakage, and zero-gate memory poisoning risks.

---

## 2. Learning Records Data Architecture

Precedent cases and analyst corrections are stored in the `learning_records` table ([`backend/app/models/learning.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/models/learning.py#L12-L55)):

| Field Name | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | Integer | Primary Key | Autoincrement record ID. |
| `rule_id` | Integer | Foreign Key (`rules.id`) | Associated detection rule. |
| `incident_id` | Integer | Foreign Key (`incidents.id`) | Evaluated incident. |
| `verified_verdict` | String(32) | Not Null | Human ground-truth determination (`TRUE_POSITIVE`, `FALSE_POSITIVE`). |
| `analyst_explanation`| Text | Nullable | Natural language rationale entered by the analyst. |
| `tp_indicators` | JSON | Default: `[]` | List of confirmed malicious indicators. |
| `fp_indicators` | JSON | Default: `[]` | List of confirmed benign indicators. |
| `missing_evidence` | JSON | Default: `[]` | Telemetry attributes that were missing during investigation. |
| `evidence_references`| JSON | Default: `[]` | Explicit references to event IDs or telemetry attributes. |
| `answered_questions` | JSON | Default: `[]` | Question-and-answer pairs extracted from analyst notes. |
| `verification_status`| String(32) | Indexed | State: `PENDING_REVIEW`, `VERIFIED`, `REJECTED`. |
| `feedback_timestamp` | DateTime | Not Null | Timestamp of submission. |

---

## 3. Discrepancy: Standalone Similarity Matcher vs. Live RAG Query

The codebase contains two completely distinct RAG retrieval implementations:

### 3.1 Sophisticated Offline Case Matcher (`find_similar_cases`)
In [`learning_service.py#L85-L165`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/learning_service.py#L85-L165), `AgentMemoryEngine.find_similar_cases()` implements a multi-metric deterministic matcher:
- Filters records by `rule_id`.
- Computes Jaccard similarity across extracted IOC sets (IPs, hashes, usernames).
- Computes string similarity across event process names.
- Ranks cases and returns top-$k$ matches with similarity percentages.

### 3.2 Actual Live Inference Query (`AV-007`)
In [`ai_verdict_service.py#L149-L180`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/ai_verdict_service.py#L149-L180), the live triage engine **does not call `find_similar_cases()`**. Instead, it executes:

```python
# ai_verdict_service.py lines 149-168
lr_q = await self.db.execute(
    select(LearningRecord)
    .where(
        LearningRecord.rule_id == rule.id,
        LearningRecord.verification_status == "VERIFIED"
    )
    .options(selectinload(LearningRecord.incident))
    .order_by(desc(LearningRecord.feedback_timestamp))
    .limit(1)
)
learning_records = lr_q.scalars().all()
if not learning_records:
    # Cross-Rule Fallback Injection!
    lr_fallback = await self.db.execute(
        select(LearningRecord)
        .where(LearningRecord.verification_status == "VERIFIED")
        .options(selectinload(LearningRecord.incident))
        .order_by(desc(LearningRecord.feedback_timestamp))
        .limit(1)
    )
    learning_records = lr_fallback.scalars().all()
```

```mermaid
flowchart TD
    Req[Incident Triage Request] --> RuleQ{Query LearningRecord<br/>rule_id == incident.rule_id<br/>status == VERIFIED}
    
    RuleQ -->|Record Found| RulePrec[Single Most Recent Record<br/>Limit 1 - NO Similarity Check]
    RuleQ -->|None Found| CrossQ{Cross-Rule Fallback Query<br/>status == VERIFIED<br/>Any rule across DB! AV-007}
    
    CrossQ -->|Found| CrossPrec[Arbitrary Unrelated Precedent<br/>e.g. EDR precedent injected into Web alert]
    CrossQ -->|None Found| NoRAG[Proceed Without Few-Shot RAG]
    
    RulePrec & CrossPrec --> Trunc[Slice analyst_explanation[:150]<br/>Discard all telemetry, IOCs & event data]
    Trunc --> Inject[Append to Prompt under ### VERIFIED HISTORICAL PRECEDENT]
```

---

## 4. RAG Verification Findings & Attack Scenarios

### 4.1 Cross-Rule Context Contamination (`AV-007`)
- **Condition:** An incident arrives for a newly created or seldom-triggered rule that has no historical feedback records.
- **Outcome:** The system queries the newest `VERIFIED` record in the entire database. An analyst's justification for closing an administrative PowerShell alert will be injected as a precedent into an SQL injection or brute-force authentication alert.

### 4.2 Immediate Few-Shot Poisoning via Self-Verification (`AV-008`)
- **Condition:** In [`investigation_service.py#L303-L343`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/investigation_service.py#L303-L343), when an analyst submits feedback with the checkbox `is_independently_verified = True`:
  ```python
  verification_status = "VERIFIED" # Assigned immediately
  ```
- **Outcome:** Bypasses supervisor review. The analyst's notes immediately become the active few-shot prompt for all subsequent incidents under that rule. If an analyst misidentifies a malware outbreak as a false positive, subsequent attacks are biased toward false positive classification.

### 4.3 Total Absence of Tenant Isolation
- **Condition:** Multi-tenant SOC environments.
- **Finding:** The `learning_records` table lacks a `customer_id` or `tenant_id` foreign key. Precedents learned from Customer A's private infrastructure (e.g. internal server names, proprietary script names) can be injected into prompts evaluating Customer B's alerts.

### 4.4 Discarded Precedent Telemetry
- **Finding:** In line 177, the injection only includes `lr.incident.title`, `lr.verified_verdict`, and `lr.analyst_explanation[:150]`.
- **Impact:** The LLM receives the human verdict and explanation, but **none of the underlying event logs or telemetry** that justified that verdict. The model is forced to make associative leaps without grounded comparative evidence.

