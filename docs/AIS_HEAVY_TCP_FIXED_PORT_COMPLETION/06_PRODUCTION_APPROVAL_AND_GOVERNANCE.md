# 06 — Production Approval Workflow & Governance Controls

**Target Rule:** `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT` / `40498741-ee6b-4a71-9101-0d6d3f77154c`)
**Current Live Lifecycle Stage:** **`LEARNING`** (`is_production_eligible: false`)
**Current Live Automation Policy (`b9845988-74c2-4a33-ae9b-5a7d67babdd7`):** `is_enabled: false`, `emergency_disable: false`

---

## 1. Lifecycle State Machine & Role-Based Governance

| Lifecycle Stage | Allowed Actions | Required Approver & Gates |
| :--- | :--- | :--- |
| **`LEARNING`** *(Current Live State)* | Advisory AI inference, double-blind SOC review, verified feedback collection, candidate draft creation | Approved policy version (`v7` APPROVED, G1–G7 PASS). Zero autonomous closures. |
| **`SUPERVISED_PILOT`** | Shadow/pilot tracking under human oversight; zero auto-closure | Authorized transition; accumulates independent verified TP/FP evaluations. |
| **`CONTROLLED_PRODUCTION`** | Eligible for **separate** explicit Administrator opt-in to enable FP-only automation | Requires: `>= 100` eligible evaluations (`>= 25` TP, `>= 50` FP), `>= 95%` accuracy, `>= 99%` FP precision, `>= 96%` Wilson 95% LB, `>= 95%` TP recall, **`0` critical missed TPs**, `0` unresolved disputes, **all G1–G8 PASS**, and **distinct Administrator approval**. |
| **`SUSPENDED`** | Emergency kill-switch; halts all automation immediately | Triggered manually by Administrator OR automatically on any confirmed `CRITICAL_MISSED_TP` or policy revocation. |

---

## 2. Two-Step Separation of Duties & Non-Auto-Enablement

Verified in [promotion_service.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/promotion_service.py), [rule_learning.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/api/rule_learning.py), and [RuleLearningDashboard.tsx](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/frontend/src/components/learning/RuleLearningDashboard.tsx):

1. **Formal Promotion Request:** Any authorized SOC analyst submits a promotion request (`POST /api/governance/promotions/request`), capturing an immutable snapshot of empirical accuracy, FP precision, Wilson LB, sample counts, approved policy version (`v7`), and active model (`Qwen/Qwen2.5-7B-Instruct-AWQ`).
2. **Separation of Duties Enforcement:** `PromotionService.decide_promotion_request` explicitly rejects self-approval (`ValueError("Separation of duties violation")`), requiring a **distinct `Administrator`** to approve (`test_04` verified).
3. **Explicit Two-Step Automation Opt-In:** Approving promotion to `CONTROLLED_PRODUCTION` **NEVER** auto-enables FortiSIEM closure (`automation_auto_enabled: false`, verified in `test_04`). An Administrator must separately enable FP automation via `POST /api/governance/automation/policy/{rule_id}` (and UI **Enable/Disable FP Automation** control in `RuleLearningDashboard.tsx`).
4. **Policy Change Re-Validation:** Any change to the approved prompt version (`v7` → `v8`) or active LLM model invalidates prior empirical certification and blocks autonomous actions until re-validated under G8 (`policy_version_id` barrier check).

---

## 3. Live Server 1 Governance State Verification

- **Policy Approval History:** Policy **v7** (`d79fb576-c6b9-4f63-9167-3c7a2419b70a`) is `APPROVED` for analyst-assisted triage (`policy_governance_mode: ADVISORY_ANALYST_REVIEW_REQUIRED`, `structural_approval_eligible: true`, `empirical_validation_eligible: false`, `autonomous_operation_eligible: false`).
- **Automation Policy Live Snapshot (`GET /api/governance/automation/policy/40498741-ee6b-4a71-9101-0d6d3f77154c?customer=GDC_NOC`):**
  - `policy_id`: `b9845988-74c2-4a33-ae9b-5a7d67babdd7`
  - `lifecycle_stage`: `LEARNING`
  - `is_enabled`: `false`
  - `emergency_disable`: `false`
  - `allowed_verdicts`: `["FALSE_POSITIVE"]`
  - `min_trust_score`: `8`
  - `daily_closure_limit`: `50`
  - `current_day_closure_count`: `0`
- **Frontend Governance UX Remediated:** Updated [RuleLearningDashboard.tsx](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/frontend/src/components/learning/RuleLearningDashboard.tsx) so "Request Production Approval" routes cleanly to the Governance tab (eliminating 403 direct-transition errors), displays `>= 99%` FP precision, Verified Rule Accuracy, G1–G8 gate status (`7/8`), Approved Policy (`v7`) & Active Model (`Qwen/Qwen2.5-7B-Instruct-AWQ`), coverage/abstention/false-alarm rates, and Administrator Enable/Disable FP Automation controls.
