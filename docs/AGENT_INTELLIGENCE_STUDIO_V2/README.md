# AGENT INTELLIGENCE STUDIO 2.0 — DOCUMENTATION REPOSITORY

## Architecture Index & File Map

Agent Intelligence Studio 2.0 (AIS 2.0) transforms the AI Verdict platform from a generic rule-to-prompt generator into an enterprise-grade **Detection-Aware Policy Generation & Quality Validation System**. This directory contains the complete technical specification, architectural review, implementation details, validation reports, and operational guidelines for AIS 2.0.

### Directory Structure & Document Map

| Document | Title | Description |
| :--- | :--- | :--- |
| [README.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AGENT_INTELLIGENCE_STUDIO_V2/README.md) | **Directory Overview & Architecture Index** | Master index, system overview, and repository navigation. |
| [00_EXECUTIVE_SUMMARY.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AGENT_INTELLIGENCE_STUDIO_V2/00_EXECUTIVE_SUMMARY.md) | **Executive Summary** | High-level business, architectural, and operational summary of AIS 2.0. |
| [01_EXISTING_ARCHITECTURE_REVIEW.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AGENT_INTELLIGENCE_STUDIO_V2/01_EXISTING_ARCHITECTURE_REVIEW.md) | **Phase 0–4 Architecture Review** | Comprehensive audit of previous phases and drivers for intelligent policy generation. |
| [02_RULE_INTELLIGENCE_ANALYZER.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AGENT_INTELLIGENCE_STUDIO_V2/02_RULE_INTELLIGENCE_ANALYZER.md) | **Rule Intelligence Analyzer** | 7-tier input hierarchy, semantics extraction, and authoritative vs. observed value demarcation. |
| [03_DETECTION_ARCHETYPE_REGISTRY.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AGENT_INTELLIGENCE_STUDIO_V2/03_DETECTION_ARCHETYPE_REGISTRY.md) | **Detection Archetype Registry** | 12 behavioral archetypes, disambiguation heuristics, and contradiction rules. |
| [04_EVIDENCE_REQUIREMENT_MAPPING.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AGENT_INTELLIGENCE_STUDIO_V2/04_EVIDENCE_REQUIREMENT_MAPPING.md) | **Evidence Requirement Mapping** | Dynamic translation of detection semantics into Core, Conditional, and Optional contracts. |
| [05_INTELLIGENT_POLICY_GENERATION.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AGENT_INTELLIGENCE_STUDIO_V2/05_INTELLIGENT_POLICY_GENERATION.md) | **Intelligent Policy Generation** | 9-section tailored synthesis and Enterprise SOC Baseline v2.0.0. |
| [06_POLICY_QUALITY_VALIDATOR.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AGENT_INTELLIGENCE_STUDIO_V2/06_POLICY_QUALITY_VALIDATOR.md) | **Policy Quality Validator** | Specification of the 8 mandatory gates (G1–G8), blockers, and overrides. |
| [07_POLICY_QUALITY_SCORING.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AGENT_INTELLIGENCE_STUDIO_V2/07_POLICY_QUALITY_SCORING.md) | **Policy Quality Scoring Formula** | Mathematical formulation of the 0–100 inspection index and hard-gate override rule. |
| [08_SIMULATION_AND_REGRESSION_APPROVAL.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AGENT_INTELLIGENCE_STUDIO_V2/08_SIMULATION_AND_REGRESSION_APPROVAL.md) | **Simulation & Regression Approval** | Simulation Lab testing, drift prevention, and `INSUFFICIENT_DATA` handling. |
| [09_POLICY_LIFECYCLE_AND_GOVERNANCE.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AGENT_INTELLIGENCE_STUDIO_V2/09_POLICY_LIFECYCLE_AND_GOVERNANCE.md) | **Policy Lifecycle & Governance** | SOC Lead RBAC approval, version lineage, rollback, and contract synchronization. |
| [10_BULK_POLICY_QUALITY_AUDIT.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AGENT_INTELLIGENCE_STUDIO_V2/10_BULK_POLICY_QUALITY_AUDIT.md) | **Bulk Policy Quality Audit** | Enterprise-scale batch engine supporting 2,000+ rules in chunks of 100. |
| [11_CONTINUOUS_POLICY_MONITORING.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AGENT_INTELLIGENCE_STUDIO_V2/11_CONTINUOUS_POLICY_MONITORING.md) | **Continuous Policy Monitoring** | Rule drift, schema drift, and verified analyst feedback loops. |
| [12_FRONTEND_AND_API_INTEGRATION.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AGENT_INTELLIGENCE_STUDIO_V2/12_FRONTEND_AND_API_INTEGRATION.md) | **Frontend & API Integration** | Next.js 16 UI tabs, badges, modals, and FastAPI endpoint definitions. |
| [13_DATABASE_AND_MIGRATIONS.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AGENT_INTELLIGENCE_STUDIO_V2/13_DATABASE_AND_MIGRATIONS.md) | **Database & Migrations** | Alembic migration 005 schema additions and SQLAlchemy ORM models. |
| [14_SECURITY_AND_COMPATIBILITY.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AGENT_INTELLIGENCE_STUDIO_V2/14_SECURITY_AND_COMPATIBILITY.md) | **Security & Compatibility** | RepoDeploy Governor compliance, zero-push controls, tenant isolation, and prompt injection defense. |
| [15_TEST_RESULTS.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AGENT_INTELLIGENCE_STUDIO_V2/15_TEST_RESULTS.md) | **Test Execution & Verification** | Regression and new test suite execution reports (177 backend tests passed). |
| [16_LARGE_OUTBOUND_TRANSFER_CASE_STUDY.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AGENT_INTELLIGENCE_STUDIO_V2/16_LARGE_OUTBOUND_TRANSFER_CASE_STUDY.md) | **Reference Case Study: Large Outbound Transfer** | In-depth walkthrough of `PH_RULE_LARGE_OUTBOUND_XFER` lifecycle and resolution. |
| [17_BEFORE_AFTER_BEHAVIOR_MATRIX.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AGENT_INTELLIGENCE_STUDIO_V2/17_BEFORE_AFTER_BEHAVIOR_MATRIX.md) | **Before vs. After Behavior Matrix** | Comparative analysis of Studio 1.0 vs Studio 2.0 system behavior. |
| [18_DEPLOYMENT_AND_ROLLBACK_GUIDE.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AGENT_INTELLIGENCE_STUDIO_V2/18_DEPLOYMENT_AND_ROLLBACK_GUIDE.md) | **Deployment & Rollback Guide** | Standard operating procedures for safe rollout, migration, and zero-downtime rollback. |
| [19_REMAINING_LIMITATIONS.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AGENT_INTELLIGENCE_STUDIO_V2/19_REMAINING_LIMITATIONS.md) | **Remaining Limitations & Future Roadmap** | Explicit technical boundaries, edge cases, and future enhancements. |
| [20_IMPLEMENTATION_COMPLETION_CHECKLIST.md](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/AGENT_INTELLIGENCE_STUDIO_V2/20_IMPLEMENTATION_COMPLETION_CHECKLIST.md) | **Implementation Completion Checklist** | Work Package verification against all prompt requirements. |

---

### Key Architectural Tenets of AIS 2.0

1. **Authoritative vs. Observed Demarcation:** The system never mistakes observed incident telemetry (e.g., `sentBytes64: 2130499380`) for an authoritative SIEM rule threshold. Missing SIEM rule conditions yield an `INCOMPLETE` semantics status and block automatic approval via Gate G1.
2. **Behavioral Archetype Specialization:** 12 behavioral archetypes prevent category hallucination (e.g., network exfiltration policies no longer require process lineage or LOLBin hashes).
3. **8 Mandatory Policy Quality Gates:** G1 (Integrity & Completeness), G2 (Archetype Relevance), G3 (Evidence Contract Feasibility), G4 (True Positive Specificity), G5 (False Positive Validity), G6 (Abstention & Escalation Completeness), G7 (Internal Consistency), and G8 (Historical Simulation & Regression Check).
4. **Hard-Gate Override Rule:** A Quality Score (0–100) is strictly an inspection index. A failure on G1 or G2 immediately forces `approval_eligible = False` regardless of numerical score.
5. **No 100% Verdict Accuracy Claim:** The system enforces empirical evidence grounding and transparent uncertainty rather than claiming infallible verdict accuracy.
