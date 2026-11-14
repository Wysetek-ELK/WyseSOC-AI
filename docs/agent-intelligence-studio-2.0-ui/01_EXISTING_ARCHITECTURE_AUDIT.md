# 01 - Existing Architecture Audit

## 1. Executive Summary

This document presents a comprehensive audit of Verdictum AI's pre-existing Agent Intelligence Studio (AIS), detection rule catalog, policy quality evaluation engine, analyst review workflows, simulation infrastructure, and governance promotion processes prior to the AIS 2.0 UX Simplification and Evidence-Based Production Readiness implementation.

The pre-existing platform possessed sophisticated algorithmic capabilities—including deterministic rule parsing, 12 detection archetypes, 8 policy quality gates (G1–G8), statistical Wilson score lower bounds, double-blind review queues, and regression simulation replay. However, the user experience exposed deep technical complexity, raw mathematical formulas, and disjointed interfaces that overwhelmed Level 1 (L1) SOC analysts and confused production deployment state with policy readiness state.

---

## 2. Pre-Existing Component Architecture

### 2.1 Frontend Architecture

| Component / File | Primary Purpose | Architectural Deficiencies Prior to AIS 2.0 |
|---|---|---|
| `frontend/src/app/agent-intelligence-studio/page.tsx` | Main studio page (3,800+ lines) | Overwhelming 7-tab interface (`editor`, `intelligence`, `contract`, `quality`, `simulation`, `drift`, `learning`) with dense JSON viewers, exposed statistical formulas, and no clear guided progression for L1 analysts. |
| `frontend/src/app/detection-intelligence/page.tsx` & `/rules` | Detection rules directory table | Lacked production readiness columns; conflated baseline SIEM deployment status (`ACTIVE`) with AI policy readiness; lacked readiness filtering. |
| `frontend/src/components/compact/AgentIntelligenceStudioOverview.tsx` | Initial compact overview prototype | Used client-side heuristics instead of single authoritative backend readiness service; lacked explicit 6 guided checklist stages and simple L1 explanations. |
| `frontend/src/components/learning/RuleLearningDashboard.tsx` | Analyst review & learning interface | Powerful double-blind and adjudication tools, but lacked plain-English distinction between reviews collected, ground truth, statistical evidence, and production eligibility. |
| `frontend/src/components/compact/CompactDesignSystem.tsx` | Reusable compact UI controls | `EvidenceCompletenessIndicator` evaluated raw field counts (`available / required`) rather than validating semantic completeness, leading to false 100% displays on unverified rules. |

### 2.2 Backend Services & Engines

```
+----------------------------------------------------------------------------------------------------+
|                                    VERDICTUM AI BACKEND ENGINE                                     |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  +-------------------------+     +-------------------------------+     +------------------------+  |
|  | Ingestion & Resolution  | --> | Semantics & Contract Resolver | --> | Detection Archetypes   |  |
|  | Rule & Incident Models  |     | get_rule_semantics_and_...    |     | 12 Registered Classes  |  |
|  +-------------------------+     +-------------------------------+     +------------------------+  |
|                                                  |                                                 |
|                                                  v                                                 |
|  +-------------------------+     +-------------------------------+     +------------------------+  |
|  | Quality Gates (G1-G8)   | <-- | Policy Quality Validator      | <-- | Machine Contract       |  |
|  | PolicyQualityValidator  |     | G1: Def  G2: Raw  G3: Feas... |     | Core / Relevant Fields |  |
|  +-------------------------+     +-------------------------------+     +------------------------+  |
|              |                                   |                                                 |
|              v                                   v                                                 |
|  +-------------------------+     +-------------------------------+     +------------------------+  |
|  | Rule Learning Service   |     | Historical Evaluation Replay  |     | Governance Approval    |  |
|  | Double-Blind Queue      |     | G8 Non-Simulated Verification |     | Cryptographic Digests  |  |
|  | Wilson Score Bound      |     | HistoricalEvaluationRecord    |     | PromptStudioService    |  |
|  +-------------------------+     +-------------------------------+     +------------------------+  |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

1. **Rule Parsing & Resolution (`RuleService`, `RuleIntelligenceAnalyzer`):**
   - Parses FortiSIEM XML/JSON detection rule definitions into `Rule` models.
   - Extracts event types, severity, pattern logic, and parsed metadata.

2. **Detection Archetype Classification (`DetectionArchetypeRegistry`):**
   - Implements 12 distinct archetypes: `NETWORK_SCAN`, `BRUTE_FORCE`, `BEACONING`, `DATA_EXFILTRATION`, `CREDENTIAL_ACCESS`, `PRIVILEGE_ESCALATION`, `PERSISTENCE`, `DEFENSE_EVASION`, `LATERAL_MOVEMENT`, `DISCOVERY`, `COMMAND_AND_CONTROL`, and `SUSPICIOUS_EXECUTION`.
   - Each archetype specifies mandatory core fields, semantic conditions, and threshold requirements.

3. **Policy Quality Engine (`PolicyQualityValidator`):**
   - Evaluates 8 deterministic gates:
     - **G1: Rule Definition Completeness** (authoritative correlation logic & thresholds).
     - **G2: Raw Telemetry Compatibility** (valid event types).
     - **G3: Evidence Feasibility & Mapping** (required contract fields present).
     - **G4: Policy Contract Compilation** (syntactic validity of 9 policy sections).
     - **G5: Indicator Explicit Definitions** (clear TP/FP distinction).
     - **G6: Abstention & Uncertainty Handling** (safe escalation on missing data).
     - **G7: Policy Consistency & Conflict** (no contradictory directives).
     - **G8: Simulation Regression Blocker** (empirical accuracy benchmarks, zero critical false negatives).

4. **Analyst Review & Learning Service (`RuleLearningService`):**
   - Collects double-blind human determinations (`TRUE_POSITIVE`, `FALSE_POSITIVE`, `INSUFFICIENT_EVIDENCE`).
   - Computes FP precision, TP recall, and 95% Wilson confidence lower bounds.
   - Requires ≥30 verified samples for Supervised Pilot, ≥100 verified samples for Controlled Production.

5. **Production Promotion & Safety (`PromptStudioService.approve_version`):**
   - Server-side gate re-evaluation requiring RBAC `Administrator` role.
   - Cryptographically binds `policy_digest`, `contract_digest`, and `rule_digest`.
   - Prevents approval when any quality gate or definition requirement fails.

---

## 3. Discovered Architectural Gaps & Problem Statements

### Gap 1: UI Cognitive Overload & Absence of L1-Friendly Hierarchy
- The existing studio presented an engineer or analyst with dozens of competing configuration knobs, raw YAML contracts, and complex statistical metrics across 7 tabs.
- L1 analysts could not answer the fundamental operational questions:
  1. *What does this detection rule do?*
  2. *How complete is its AI intelligence?*
  3. *What is missing?*
  4. *What should I do next?*
  5. *Is this rule eligible for production approval?*

### Gap 2: Inconsistent Readiness Source of Truth
- Readiness state was fragmented: `/prompts/summary` computed one representation, `CompactDesignSystem` computed another on the client, and `RuleLearningService` maintained a separate profile state.
- There was no unified, authoritative endpoint delivering a structured readiness evaluation with human-readable stages and prioritized smart next actions.

### Gap 3: Conflation of Readiness with Deployment Status
- In the rule directory (`/detection-intelligence`), rules imported from FortiSIEM had `status = "ACTIVE"`.
- However, their AI triage policies were in early draft stages or incomplete.
- The UI conflated "SIEM alert ingestion is active" with "AI automated triage is production-ready", causing severe operator confusion.

### Gap 4: False 100% Evidence Completeness
- `EvidenceCompletenessIndicator` previously calculated `(availableCount / requiredCount) * 100`.
- If an incident payload happened to contain 5 raw telemetry fields, the indicator reported 100% complete, even if the underlying rule lacked semantic correlation thresholds and Gate 3 failed.

### Gap 5: Inconsistent Archetype Resolution for Unpersisted Rules
- In `/api/prompts/summary`, detection archetypes were looked up solely via `rule_intelligence_snapshots`.
- If a rule lacked a pre-computed snapshot in the database, the summary defaulted to `"UNKNOWN"`, whereas viewing the rule dynamically in the Studio evaluated it as `"NETWORK_SCAN"`.

---

## 4. Architectural Target State

The architecture was redesigned into a **3-Tier Guided Workflow**:
1. **Tier 1 (Default L1 Interface):** 3-Tab Architecture (`Overview`, `Analyst Review & Learning`, `Advanced Configuration`).
2. **Tier 2 (Authoritative Backend Engine):** `ProductionReadinessService` evaluating 6 human-readable stages and cascading smart next action.
3. **Tier 3 (Separation of Concerns):** Clear architectural boundary between SIEM Deployment Status (`ACTIVE`, `INACTIVE`) and AI Production Readiness (`BLOCKED`, `INCOMPLETE`, `LEARNING`, `VALIDATING`, `READY_FOR_APPROVAL`, `APPROVED`, `ACTIVE`).
