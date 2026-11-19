# 01 — Existing UI & Backend Architecture Audit
**Verdictum AI — Agent Intelligence Studio 2.0 Redesign & Version Governance**
**Audit Date:** November 19, 2026
**Target Workspaces:** `frontend/src/app/agent-intelligence-studio/`, `backend/app/`

---

## 1. Executive Summary & Audit Objectives

The Agent Intelligence Studio (AIS) 2.0 represents Verdictum AI's operational workbench for detection rule modeling, AI investigation policy synthesis, quality gate evaluation, empirical local LLM inference validation, and analyst learning calibration.

This comprehensive audit examines the existing frontend implementation, backend API endpoints, service layer dependencies, database entities, and governance guardrails to prepare for:
1. **Redesigning the AIS interface into a simple, compact, attractive, 3-tab guided workspace** (Review Incidents, Test AI, Accuracy & Learning), with an un-intrusive **Advanced Settings** hub.
2. **Implementing Manage Version History**, enabling authorized SOC administrators to archive, restore, compare, and safely delete eligible obsolete policy versions without compromising immutable audit trails, execution provenance, or active policies.
3. **Preserving existing production policies**, specifically:
   - `Website access policy violation: Same Source and Destination` (UUID: `7bd13e89-0828-48e6-8cf5-f3cbf12d438c`, Active: v2 APPROVED, Candidate: v3 DRAFT).
   - `Heavy TCP Host Scan On Fixed Port` (UUID: `40498741-ee6b-4a71-9101-0d6d3f77154c`, Active: v7 APPROVED, Candidate: v8 DRAFT).

---

## 2. Frontend Architecture & Current UI Functionality Audit

### 2.1 File Structure and Components
The existing AIS frontend is structured around:
- Primary Route: `frontend/src/app/agent-intelligence-studio/page.tsx` (4,850 lines).
- Overview Component: `frontend/src/components/compact/AgentIntelligenceStudioOverview.tsx` (1,295 lines).
- Learning Dashboard: `frontend/src/components/learning/RuleLearningDashboard.tsx` (1,531 lines).
- Design System: `frontend/src/components/compact/CompactDesignSystem.tsx`.
- Modal Inspector: `frontend/src/components/prompt-inspector/ActualPromptInspectorModal.tsx`.
- Diagnostic Helpers: `frontend/src/lib/diagnostics.ts`.
- Quality Export Helpers: `frontend/src/lib/qualityExport.ts`.

### 2.2 Functional Capabilities Identified
1. **Rule Selection & Filtering**: Rule catalog table with search, severity filter, archetype filter, readiness filter, and sticky action column.
2. **Overview**: Decoupled lifecycle status strip (SIEM Rule Status, Policy Version, Readiness Score, Execution State), 6 Guided Checklist Stages, and Smart Next Action.
3. **Analyst Review & Learning**: Double-blind review interface with masked AI verdicts, submission of TP/FP/Insufficient Evidence, post-submission comparison reveal, and senior analyst adjudication.
4. **Policy Generation & Editing**: Intelligent draft synthesis using FortiSIEM rule XML semantics and evidence contracts; 9-part prompt component editor (common, rule-specific, conditions, evidence, TP/FP indicators, missing criteria, escalation, questions).
5. **Quality Gates G1–G8**: Automated evaluation against 8 mandatory gates:
   - G1: Schema & Output Format Structure
   - G2: Detection Anchor Integrity
   - G3: Grounding & Telemetry Consistency
   - G4: Abstention & Uncertainty Handling
   - G5: Benign Assumption & Noise Handling
   - G6: Determinism & Robustness
   - G7: Non-Fabrication of Unobserved Evidence
   - G8: Empirical Accuracy & Confidence Lower Bound
6. **AI Testing & Simulation**: Batch dry-run replay engine, local LLM evaluation against historical incident cases, and live inference verification.
7. **Prompt Inspection**: "View Actual LLM Prompt" dialog displaying the exact outbound payload, canonical JSON serialization, SHA-256 fingerprint, and token breakdown.
8. **Production Governance**: Lifecycle stage transitions (`LEARNING`, `VALIDATION`, `SUPERVISED_PILOT`, `CONTROLLED_PRODUCTION`), formal dual-key promotion requests, and emergency kill-switch.
9. **Version Management (Current State)**:
   - Basic version selector dropdown (`PromptVersionSelector`).
   - "Approve Version" button (guarded by 8 passed gates and 30 verified analyst reviews).
   - "Rollback Version" button.
   - "Revoke Version" modal (reason required).
   - **Gaps Identified**: No dedicated version history table; no archive/restore mechanism; no safe deletion impact preview; no bulk cleanup for obsolete drafts; archived versions not distinguished in the selector.

### 2.3 Identified UI Friction Points & Clutter
- **Navigation Fragmented**: Users currently switch between 3 large tabs (`overview`, `learning`, `advanced`) where each tab hosts multiple sub-panels, producing excessive vertical scrolling and visual overload.
- **Confusing Status Duplication**: Readiness scores, quality scores, and learning progress were duplicated across the Overview and Learning Dashboard with slight differences in gate calculations.
- **Readiness API Fail-Closed Inconsistency**: If `/api/prompts/rule/{rule_id}/readiness` fails or returns uncalibrated data, the Overview occasionally defaulted passed gates to `0/8`, contradicting the quality assessment preview.
- **Technical Setting Exposure**: Advanced technical configuration (prompt compiler templates, XML parsing, raw simulation results) was mixed into the analyst flow rather than sequestered into an Advanced Settings section.

---

## 3. Backend Architecture & Service Layer Audit

The FastAPI backend exposes modular services with strict separation of concerns:

| Service | File Path | Core Role | State & Invariants |
| :--- | :--- | :--- | :--- |
| **PolicyCompilerService** | `backend/app/services/policy_compiler_service.py` | Compiles 9 prompt components into executable LLM instructions. | Immutable compilation; enforces anti-prompt-injection delimiters and canonical EV-* tokens. |
| **EvidenceContractService** | `backend/app/services/evidence_contract_service.py` | Validates field availability and maps mandatory SIEM telemetry fields. | Enforces archetype requirements; detects missing or unmapped evidence. |
| **VerdictPipeline** | `backend/app/services/verdict_pipeline.py` | Orchestrates the end-to-end incident investigation flow. | Coordinates evidence ingestion, LLM invocation, validator check, and confidence normalization. |
| **IndependentVerdictValidator** | `backend/app/services/independent_verdict_validator.py` | Deterministic verification of LLM verdicts against cited evidence. | Checks grounding ratio ($\ge 0.80$), rejects ungrounded claims, validates abstention criteria. |
| **ReasoningIntegrityEngine** | `backend/app/services/reasoning_integrity_engine.py` | Validates logical coherence across verdict claims. | Checks cross-field contradictions, loopback claims, firewall actions, and directional consistency. |
| **ConfidenceNormalizer** | `backend/app/services/confidence_normalizer.py` | Mathematical calibration of ordinal trust scores (1–10). | Penalizes missing evidence and caps uncalibrated scores to $\le 6/10$. |
| **AnalystReviewService** | `backend/app/services/analyst_review_service.py` | Records double-blind human determinations. | Strictly isolates unrevealed AI verdicts until analyst submission; computes agreement outcomes. |
| **RuleLearningService** | `backend/app/services/rule_learning_service.py` | Maintains per-rule learning profiles, confusion matrices, and stage transitions. | Calculates Wilson score lower bounds; tracks TP recall and FP precision. |
| **ProductionReadinessService** | `backend/app/services/production_readiness_service.py` | Synthesizes readiness across 6 stages and generates Next Recommended Action. | Authoritative server-side evaluation. |

---

## 4. Protected Rules & Baseline State

The following rules and their policy versions must remain strictly protected:

1. **Website Access Policy Violation: Same Source and Destination**
   - Rule UUID: `7bd13e89-0828-48e6-8cf5-f3cbf12d438c`
   - Rule Identifier: `PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST`
   - Active Policy: **v2 APPROVED** (Status: `APPROVED`)
   - Candidate Draft: **v3 DRAFT** (Status: `DRAFT`)
   - Preservation Contract: Never automatically delete, archive, or replace v2 or v3.

2. **Heavy TCP Host Scan On Fixed Port**
   - Rule UUID: `40498741-ee6b-4a71-9101-0d6d3f77154c`
   - Rule Identifier: `PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`
   - Active Policy: **v7 APPROVED** (Status: `APPROVED`)
   - Candidate Draft: **v8 DRAFT** (Status: `DRAFT`)
   - Preservation Contract: Never automatically delete, archive, or replace v7 or v8.
