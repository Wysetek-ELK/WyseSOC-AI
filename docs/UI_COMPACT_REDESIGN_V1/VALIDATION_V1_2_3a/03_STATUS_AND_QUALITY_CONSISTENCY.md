# Verdictum AI — Validation V1.2.3a
## Report 03: Status Decoupling Matrix & Quality Score Mathematical Parity

**Auditor / Engineer:** Senior Full-Stack Architect, SOC AI Governance Engineer  
**Scope:** Decoupled 4-domain lifecycle status matrix, formula verification, and quality gate breakdown  
**Date:** November 17, 2026  
**Status:** 100% MATHEMATICAL PARITY VERIFIED  

---

### 1. Four-Domain Decoupled Lifecycle Matrix

Verdictum AI strictly enforces that four independent lifecycle states are never conflated:

$$\text{SIEM Deployment Status} \neq \text{AI Policy Approval Status} \neq \text{Production Readiness Status} \neq \text{AI Execution Status}$$

| Lifecycle Domain | Authoritative Source | Valid Values | Heavy TCP Fixed Port (Candidate v3) | Heavy TCP Fixed Port (Baseline v1) |
|---|---|---|---|---|
| **1. SIEM Rule Deployment** | `rules.status` (from FortiSIEM registry) | `ACTIVE`, `INACTIVE`, `UNKNOWN` | **ACTIVE** (`SIEM Rule Active`) | **ACTIVE** (`SIEM Rule Active`) |
| **2. Policy Version & Status** | `prompt_versions.status` | `DRAFT`, `VALIDATED`, `APPROVED`, `REVOKED` | **DRAFT** (`Policy v3: DRAFT`) | **APPROVED** (`Active Policy v1`) |
| **3. Production Readiness** | `ProductionReadinessService.evaluate_readiness` | `READY`, `BLOCKED`, `NOT_EVALUATED` | **BLOCKED** (`6 / 8 Gates Passed`) | **BLOCKED** (`2 / 8 Gates Passed`) |
| **4. AI Execution Runtime** | Runtime configuration & circuit breaker | `Enabled`, `Disabled`, `Suspended`, `Offline` | **Disabled** (Policy not approved) | **Offline** (Server 2 offline) |

---

### 2. Quality Score Mathematical Parity Proof

#### Theoretical Formula
In `PolicyQualityValidator` (`backend/app/services/policy_quality_validator.py`):
$$\text{Quality Score} = \sum_{i=1}^{8} \text{Score}(G_i)$$

Where gate score weights are partitioned as follows:
- $G_1$ (Rule Integrity & Provenance): Max 10.0 pts
- $G_2$ (Detection Condition Specificity): Max 10.0 pts
- $G_3$ (Evidence Contract Feasibility): Max 20.0 pts
- $G_4$ (True Positive Criteria Validity): Max 10.0 pts
- $G_5$ (False Positive & Benign Assumptions): Max 10.0 pts
- $G_6$ (Abstention & Escalation Safety): Max 15.0 pts
- $G_7$ (Policy Consistency & Semantics): Max 10.0 pts
- $G_8$ (Historical Simulation & Regression): Max 15.0 pts
- **Total Maximum Score:** 100.0 pts

#### Exact Mathematical Breakdown: Heavy TCP Host Scan Candidate v3

| Gate ID | Gate Name | Max Score | Server 1 Score (PostgreSQL) | Local Test Score (SQLite) | Status | Assessment Findings |
|---|---|---|---|---|---|---|
| **G1** | Rule Integrity & Provenance | 10.0 | **3.0** | **2.0** | **FAILED** (Blocker) | Incomplete SIEM XML definition (`RULE_DEFINITION_INCOMPLETE`). Deduction: -5.0. Provenance: Server 1 `AUTO_SYNCED_FROM_INCIDENT` (-2.0) = **3.0**; Local test `HEURISTIC_PARSER` (-3.0) = **2.0**. |
| **G2** | Detection Condition Specificity | 10.0 | **10.0** | **10.0** | **PASSED** | Explicit network scan port and event conditions verified. |
| **G3** | Evidence Contract Feasibility | 20.0 | **20.0** | **20.0** | **PASSED** | Full evidence mapping to FortiSIEM normalized schema fields. |
| **G4** | TP Criteria Validity | 10.0 | **10.0** | **10.0** | **PASSED** | Valid indicators for external scan, unauthorized reconnaissance. |
| **G5** | FP Criteria & Benign Assumptions | 10.0 | **10.0** | **10.0** | **PASSED** | Valid indicators for authorized vulnerability scanners, internal monitoring. |
| **G6** | Abstention & Escalation Safety | 15.0 | **15.0** | **15.0** | **PASSED** | Explicit missing-info and supervisor escalation rules present. |
| **G7** | Internal Policy Consistency | 10.0 | **10.0** | **10.0** | **PASSED** | Consistent across detection conditions, TP, and FP definitions. |
| **G8** | Simulation & Regression | 15.0 | **0.0** | **0.0** | **WARNING** | Simulation replay unperformed / Server 2 offline. Non-blocking warning. |
| **SUM** | **Total Gate Score Sum** | **100.0** | **78.0** | **77.0** | **BLOCKED** | $\sum_{i=1}^8 \text{Score}(G_i) \equiv \text{Quality Score}$ |

#### Verification Verdict
- **Server 1 PostgreSQL:** `quality_score = 78.0`, `readiness_score = 78.0`, `sum(gates) = 78.0`. **Exact 100% parity.**
- **Local Test SQLite:** `quality_score = 77.0`, `readiness_score = 77.0`, `sum(gates) = 77.0`. **Exact 100% parity.**
- **Sub-8 Quality Gate Lockout:** Both environments pass 6/8 gates, fail G1 with a hard blocking issue, and enforce `approval_eligible = false`. The "Approve" button is locked.
