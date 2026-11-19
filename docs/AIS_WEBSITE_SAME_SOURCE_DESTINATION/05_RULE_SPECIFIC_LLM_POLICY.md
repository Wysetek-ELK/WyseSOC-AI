# 05 — Rule-Specific AI Investigation Policy & Prompt Architecture
**Target Rule:** `Website access policy violation: Same Source and Destination`  
**Rule UUID:** `7bd13e89-0828-48e6-8cf5-f3cbf12d438c`  
**Active Approved Policy:** Version 2 (`ccb9dffa-e29e-49b6-b945-4359829272b6`, Status: `APPROVED`)  
**Candidate Draft Policy:** Version 3 (`6559b1e7-55ac-4f15-8699-aabf251f997a`, Status: `DRAFT`)  
**Target Model:** `Qwen/Qwen2.5-7B-Instruct-AWQ` on Verdictum Cortex (Server 2)  

---

## 1. 9-Section AIS Policy Architecture

The AI investigation policy is compiled dynamically by the `PolicyCompilerService` into a 9-section prompt adhering to strict token budgets and deterministic schema constraints:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   AIS 2.0 POLICY PROMPT STRUCTURE                     │
├────────────────────────────────────────────────────────────────────────┤
│ Section 1: System Persona, Safety Directives, Prompt-Injection Defense │
│ Section 2: Rule-Specific Investigation Directives (Policy Violation)   │
│ Section 3: Authoritative Detection Logic & GroupBy Semantics           │
│ Section 4: Evidence Contract & Mandatory Field References              │
│ Section 5: True Positive Criteria (Policy Violations)                  │
│ Section 6: False Positive Criteria (Authorized Exceptions & Over-block)│
│ Section 7: Mandatory Abstention Rules (Header-Only & Missing Telemetry)│
│ Section 8: Severity Escalation & Emergency IR Directives               │
│ Section 9: Guided SOC Analyst Review Questions                         │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Rule-Specific Directives for `PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST`

The compiled policy provides explicit guidance to the Local LLM:

1. **FortiSIEM GroupBy Semantics:** "Same Source and Destination" defines the SIEM correlation aggregation boundary (`srcIpAddr` and `destName`/`destIpAddr`), **NOT** loopback traffic (`127.0.0.1`) or source IP equals destination IP. The model is forbidden from inferring loopback when client source IP and destination IP/domain are distinct.
2. **Policy Enforcement Verification:** The model must evaluate whether the perimeter FortiGate web filter actively blocked the request (`eventType` in `FortiGate-web-ftgd-cat-blk` / `FortiGate-webfilter-block`, `action` in `blocked`, `denied`).
3. **Decisive Classification Criteria:**
   - **TRUE_POSITIVE:** Concrete telemetry confirms repeated attempts to access restricted, non-business, or prohibited web categories in violation of enterprise policy without documented exemption.
   - **FALSE_POSITIVE:** Concrete telemetry confirms an authorized business requirement backed by an approved ticket/exception, a miscategorized enterprise application, or verified loopback reflection on local interfaces.
   - **REQUIRES_ATTENTION:** Header-only alerts (`event_count == 0`), ambiguous policy categories, missing raw UTM logs, or contradictory evidence.

---

## 3. Policy Version Governance & Comparison

| Parameter | Active Policy (v2 APPROVED) | Candidate Policy (v3 DRAFT) |
| :--- | :--- | :--- |
| **Version ID** | `ccb9dffa-e29e-49b6-b945-4359829272b6` | `6559b1e7-55ac-4f15-8699-aabf251f997a` |
| **Status** | `APPROVED` (Active in Production) | `DRAFT` (Awaiting Empirical Certification) |
| **Compilation Digest** | `ded12f4ca157da4483cdbed266bc418697be04bf4...` | `10f277ca4e6015b39922e49c71676605e7ba1e31...` |
| **Archetype Alignment** | `POLICY_VIOLATION` | `POLICY_VIOLATION` (Fully Specialized) |
| **Token Budget Compliance** | Passed ($\le 4,096$ context) | Passed ($\le 4,096$ context) |
| **Governance Status** | Approved for Advisory Operation | Candidate draft retained in Draft mode |

---

## 4. Quality Gates Evaluation (G1–G8)

Validation was executed against candidate policy Version 3 via `POST /api/prompts/rule/7bd13e89-0828-48e6-8cf5-f3cbf12d438c/validate-quality?version_id=6559b1e7-55ac-4f15-8699-aabf251f997a`:

| Gate | Description | Threshold | Candidate Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **G1** | Structural & Schema Completeness | All 9 sections present, valid schema | 9 / 9 sections present | **PASS** |
| **G2** | Evidence Contract Binding | Valid EV-* evidence bindings | Canonical schema mapped | **PASS** |
| **G3** | Token Budget & Truncation Guard | Total tokens $\le 4,096$, output $\le 768$ | Max total: 4,096, comp $\le 768$ | **PASS** |
| **G4** | Prompt-Injection & Jailbreak Defense | Delimiter isolation, strict JSON output | Triple-backtick JSON, zero injection | **PASS** |
| **G5** | Hallucination & Grounding Rules | Claims bound to canonical digests | Grounding ratio validator active | **PASS** |
| **G6** | Abstention & Safety Criteria | Header-only forces REQUIRES_ATTENTION | Abstention directives enforced | **PASS** |
| **G7** | SIEM Correlation Drift Check | Policy logic aligned with rule XML | Logic verified against imported XML | **PASS** |
| **G8** | Empirical Accuracy on Real Ground Truth | $\ge 95\%$ accuracy on verified reviews | 0 reviews on fresh dataset | **WARNING** (`NOT_EVALUATED`) |

### Summary Score:
- **Overall Quality Score:** **85 / 100**
- **Structural Quality Score:** **100% (85 / 85)**
- **Approval Eligibility:** `structural_approval_eligible: true`, `empirical_validation_eligible: false`.
- **Governance Action:** Candidate policy Version 3 is preserved as **DRAFT**. Production continues to execute under Version 2 APPROVED in `ADVISORY_ANALYST_REVIEW_REQUIRED` mode.
