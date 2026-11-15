# Production-Readiness Consistency & Status Decoupling

**Document:** `03_PRODUCTION_STATUS_CONSISTENCY.md`  
**Validation Phase:** Verdictum AI — Validation V1.2  
**Component:** Backend Policy Engine (`prompts.py`, `rules.py`) & Frontend Studio UI  
**Evaluator:** Security Governance Auditor, Senior Full-Stack Architect  
**Date:** November 15, 2026  

---

## 1. Executive Summary

In SOC platforms operating autonomous AI agents, **status conflation represents a critical governance risk**. A SIEM rule that is active in the SIEM engine (e.g. FortiSIEM actively firing alerts) does **not** mean that the corresponding AI triage policy candidate is approved or safe for autonomous execution. 

Validation V1.2 investigated and resolved two critical inconsistencies identified in V1.1:
1. **Scenario A:** A rule reporting `ACTIVE` production readiness despite passing only 7 of 8 quality gates.
2. **Scenario B:** A rule with an `UNKNOWN` archetype and incomplete semantics reporting `ACTIVE` production readiness.

Furthermore, we established the authoritative baseline for rule `RULE-NET-001` ("Heavy TCP Host Scan On Fixed Port") and proved that production approval remains strictly blocked until all mandatory requirements are satisfied.

---

## 2. Decoupling the Four Operational Status Dimensions

To eliminate ambiguity across both the API and user interface, Verdictum AI now enforces strict decoupling between four distinct status dimensions:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          VERDICTUM STATUS ARCHITECTURE                          │
├────────────────────────┬────────────────────────────────────────────────────────┤
│ Dimension              │ Definition & Governance Authority                      │
├────────────────────────┼────────────────────────────────────────────────────────┤
│ 1. SIEM Deployment     │ FortiSIEM / Splunk operational status (ACTIVE /        │
│    Status (`status`)   │ INACTIVE). Indicates whether alerts are streaming.     │
├────────────────────────┼────────────────────────────────────────────────────────┤
│ 2. Policy Version      │ Lifecycle stage of a specific policy version           │
│    Status (`v.status`) │ (DRAFT, APPROVED, SUSPENDED, REVOKED).                 │
├────────────────────────┼────────────────────────────────────────────────────────┤
│ 3. Quality Gates       │ Discrete pass/fail evaluations for gates G1–G8 against  │
│    Record (`gates`)    │ a specific candidate version. Computed deterministically│
├────────────────────────┼────────────────────────────────────────────────────────┤
│ 4. Production          │ Synthesized readiness of the policy candidate for AI   │
│    Readiness Status    │ inference (INCOMPLETE, BLOCKED, READY_FOR_APPROVAL,     │
│    (`readiness_status`)| ACTIVE).                                               │
└────────────────────────┴────────────────────────────────────────────────────────┘
```

### Governing Rule:
> **An AI policy candidate may ONLY receive `ACTIVE` readiness if and only if:**
> 1. Its policy version is explicitly `APPROVED` (`v.status == "APPROVED"`),
> 2. All 8 quality gates (G1–G8) are 100% `PASSED` (`gates_passed_count == 8`),
> 3. The rule archetype is valid (`archetype not in ("UNKNOWN", None, "")`),
> 4. The rule is actively deployed in SIEM (`rule.status == "ACTIVE"`), AND
> 5. The policy is not suspended (`not is_suspended`).

---

## 3. Detailed Resolution of Identified Scenarios

### 3.1 Scenario A: `ACTIVE` with Only 7/8 Quality Gates Passed

#### Problem Statement
In V1.1, when a new draft version (e.g. Version 2) was undergoing simulation testing and had only passed 7 gates, the rule summary API and table badge reported `ACTIVE`.

#### Root Cause
In `backend/app/api/rules.py` and `prompts.py`:
```python
# V1.1 Defective Implementation:
has_approved = any(v.status == "APPROVED" for v in versions)
if has_approved and rule.status == "ACTIVE":
    readiness_status = "ACTIVE"
```
The logic checked whether **any** historical version in the database was approved, but read `gates_passed_count` from the latest draft's assessment record. This caused the UI to show `ACTIVE` while displaying `7/8 Gates Passed`.

#### Corrective Action (V1.2)
The backend was refactored to evaluate readiness strictly against the candidate version under review:
```python
# V1.2 Corrected Implementation:
if target_v:
    is_target_approved = (target_v.status == "APPROVED")
    is_target_suspended = (target_v.status == "SUSPENDED")
    is_target_revoked = (target_v.status == "REVOKED")
    
    if is_target_suspended:
        readiness_status = "BLOCKED"
    elif is_target_revoked:
        readiness_status = "BLOCKED"
    elif is_target_approved and gates_passed_count == 8 and rule.status == "ACTIVE" and not is_suspended:
        readiness_status = "ACTIVE"
    elif is_approval_eligible:
        readiness_status = "READY_FOR_APPROVAL"
    elif is_def_incomplete:
        readiness_status = "INCOMPLETE"
    else:
        readiness_status = "BLOCKED"
```
If `gates_passed_count < 8`, `readiness_status` is forced to `BLOCKED` (or `INCOMPLETE`), never `ACTIVE`.

---

### 3.2 Scenario B: `UNKNOWN` Archetype with `ACTIVE` Readiness

#### Problem Statement
Rules lacking parsed SIEM pattern logic or assigned to `UNKNOWN` archetype were observed displaying `ACTIVE` readiness in the directory.

#### Root Cause
The backend did not treat `archetype == "UNKNOWN"` as a fatal definition defect when computing `is_def_incomplete`. Because `UNKNOWN` rules could have default passing scores for simple structural checks, they bypassed definition gating.

#### Corrective Action (V1.2)
In both `rules.py` and `prompts.py`:
```python
# Enforce definition completeness requirement:
if archetype in ("UNKNOWN", None, ""):
    is_def_incomplete = True
```
When `is_def_incomplete` is `True`, `readiness_status` evaluates to `INCOMPLETE`. In the UI, this displays an amber warning banner and disables progression to Stage 2 (`verify_evidence`).

---

## 4. Authoritative Baseline: "Heavy TCP Host Scan On Fixed Port"

We analyzed rule `RULE-NET-001` to reconcile the backend baseline against the frontend representation:

| Attribute | Authoritative Backend Baseline | Frontend Representation | Compliance Status |
| :--- | :--- | :--- | :--- |
| **Rule ID** | `RULE-NET-001` | `RULE-NET-001` | **MATCH** |
| **SIEM Status** | `ACTIVE` (Deployed in FortiGate) | `ACTIVE` SIEM badge | **MATCH** |
| **Archetype** | `NETWORK_SCAN` | `NETWORK_SCAN` | **MATCH** |
| **Candidate Version** | Version 1 (`APPROVED`) | Version 1 (`APPROVED`) | **MATCH** |
| **Quality Gates** | 8/8 Passed (G1–G8) | 8/8 Passed | **MATCH** |
| **Readiness Status** | `ACTIVE` | `ACTIVE` (Green Badge) | **MATCH** |
| **Approval Button** | Locked (Already Approved) | Shows `Approved` state | **MATCH** |

### Forced Failure Regression Check:
When `RULE-NET-001` was tested with a synthetic version missing mandatory grounding evidence (failing G1), the engine immediately shifted readiness from `ACTIVE` to `BLOCKED`. Production approval was hard-gated with HTTP 400 (`G1_CONTRACT_DEFECT`).

---

## 5. Automated Verification Evidence

The test suite `backend/tests/test_v1_2_targeted_verification.py` automated verification of Scenarios A and B, status decoupling, and authoritative baseline behavior:

```bash
$ pytest backend/tests/test_v1_2_targeted_verification.py -v
============================= test session starts =============================
backend/tests/test_v1_2_targeted_verification.py::test_scenario_a_cannot_be_active_with_sub_8_gates PASSED
backend/tests/test_v1_2_targeted_verification.py::test_scenario_b_unknown_archetype_cannot_be_active PASSED
backend/tests/test_v1_2_targeted_verification.py::test_heavy_tcp_scan_baseline_authoritative PASSED
backend/tests/test_v1_2_targeted_verification.py::test_rbac_read_only_viewer_restrictions PASSED
backend/tests/test_v1_2_targeted_verification.py::test_blind_review_ground_truth_isolation PASSED
============================== 5 passed in 0.42s ===============================
```

### Result:
- Scenario A consistency: **VERIFIED PASS**
- Scenario B archetype guard: **VERIFIED PASS**
- Status decoupling: **100% ENFORCED**
