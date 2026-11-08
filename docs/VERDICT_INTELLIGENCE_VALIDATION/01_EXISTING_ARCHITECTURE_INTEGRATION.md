# Existing Architecture Integration (AIS 2.1)

## 1. Overview and Design Principles

The **Agent Intelligence Studio 2.1 — Dry-Run Intelligence Validation** layer is designed to extend, rather than duplicate or replace, the existing AIS 2.0 architecture. 

AIS 2.0 established:
- **Detection Archetype Registry**: 12 standardized behavioral archetypes (`backend/app/services/detection_archetype_registry.py`).
- **Evidence Requirement Mapper & Contracts**: Machine-verifiable data expectations per rule (`backend/app/services/evidence_requirement_mapper.py`).
- **Policy Quality Validator**: Structural and safety rules G1–G8 (`backend/app/services/policy_quality_validator.py`).
- **Policy Simulation Lab**: Historical simulation runs and policy diffing (`backend/app/services/policy_simulation_service.py`).
- **Local LLM Inference Framework**: Grounded verdict generation pipelines.

AIS 2.1 layers an **empirical intelligence validation engine** on top of these components. It treats detection policies not merely as generated text or static schemas, but as **testable hypotheses** whose real-world fidelity is empirically quantified against historical incident telemetry.

---

## 2. Component Integration Matrix

| AIS 2.0 Component | AIS 2.1 Extension Point | Integration Mechanism |
|---|---|---|
| `DetectionArchetypeRegistry` | Archetype-Aware Evidence Weights | `EvidenceSufficiencyEngine` queries `DetectionArchetypeRegistry.get_archetype_definition(archetype)` to dynamically resolve expected telemetry dimensions. |
| `EvidenceRequirementMapper` | Dynamic Evidence Contract Mapping | `EvidenceSufficiencyEngine` uses `RuleEvidenceContract` to enforce mandatory fields and detect missing evidence. |
| `PolicySimulationService` | Dry-Run Evaluation & Paired Regression | Extended with `run_dry_run_intelligence_evaluation` and `compare_runs`, enabling side-by-side regression testing without altering existing simulation code. |
| `HistoricalIncident` / DB Models | Empirical Validation Tables | `backend/app/models/verdict_intelligence.py` adds relational models for trust scores, sufficiency audits, ground truth records, and evaluation runs via foreign keys. |
| FastAPI Application (`main.py`) | Dual-Mounted REST API | Registered at both `settings.API_V1_STR` (`/api`) and `/api/v1` to ensure backward compatibility and frontend client alignment. |
| Next.js Frontend (`frontend/src/`) | Verdict Intelligence Dashboard | Extends API client (`frontend/src/lib/api.ts`) and adds dedicated route at `frontend/src/app/verdict-intelligence/page.tsx` with 5 integrated view modes (Dashboards A–E). |

---

## 3. End-to-End Data Pipeline Flow

```
                      +---------------------------------------+
                      |       Historical SIEM Telemetry       |
                      +---------------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |   HistoricalGroundTruthValidator     |
                      |   - Strips analyst notes/dispositions |
                      |   - Adjudicates ground truth labels   |
                      |   - Deterministic 4-way hash split    |
                      +---------------------------------------+
                                          |
                        +-----------------+-----------------+
                        |                                   |
                        v                                   v
        +-------------------------------+   +-------------------------------+
        |    Candidate Policy Prompt    |   |     Baseline Policy Prompt    |
        +-------------------------------+   +-------------------------------+
                        |                                   |
                        +-----------------+-----------------+
                                          |
                                          v
                      +---------------------------------------+
                      |          Local LLM Inference          |
                      |   (Suggested Verdict + Reasoning)     |
                      +---------------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |        EvidenceSufficiencyEngine      |
                      |   (Evaluates telemetry vs contract)   |
                      +---------------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |         VerdictClaimValidator         |
                      |   (Entity grounding, contradictions)  |
                      +---------------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |        VerdictGuardrailsEngine        |
                      |   (G1-G7 deterministic 3-way gate)    |
                      +---------------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |      VerdictTrustworthinessEngine     |
                      |   (1-10 Trust Score, calibration cap) |
                      +---------------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |   EmpiricalAccuracy & Calibration     |
                      |   (Wilson CIs, ECE, Risk-Coverage)    |
                      +---------------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |   Paired Regression Comparison        |
                      |   (VALIDATED / REGRESSION_DETECTED)   |
                      +---------------------------------------+
```

---

## 4. Separation of Concerns & Isolation Guarantee

To avoid degrading production stability:
1. **Zero Modifications to Existing G1–G8 Production Approval Gates**: AIS 2.0 production approval gates remain untouched. AIS 2.1 operates as an independent dry-run verification suite.
2. **No Automated Live SIEM Ticket Mutations**: The system operates exclusively on historical logs and shadow evaluations. It does not update tickets in FortiSIEM or trigger containment actions.
3. **Data Leakage Immunity**: The `HistoricalGroundTruthValidator.sanitize_incident_for_inference` function sanitizes payloads before passing them to the LLM, preventing the model from cheating on historical outcomes.
4. **Independent Database Isolation**: All new audit trails, metrics, and calibration points reside in dedicated tables (`verdict_trust_assessments`, `evidence_sufficiency_audits`, `historical_ground_truth_records`, `historical_evaluation_runs`, `historical_evaluation_results`) created cleanly under Alembic migration `006`.
