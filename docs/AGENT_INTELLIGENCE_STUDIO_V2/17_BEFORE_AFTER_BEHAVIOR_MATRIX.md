# 17. BEFORE VS. AFTER BEHAVIOR MATRIX

## Detailed Comparative Analysis

The table below contrasts system behavior, data integrity, and operational safety between **Agent Intelligence Studio 1.0** and **Agent Intelligence Studio 2.0**:

| System Dimension | Studio 1.0 (Legacy Baseline) | Studio 2.0 (AIS 2.0 Enhanced) |
| :--- | :--- | :--- |
| **SIEM Telemetry Ingestion** | Blindly ingested key-value pairs; mistook observed incident attributes (e.g. `sentBytes64: 2130499380`) for rule thresholds. | Implements a **7-tier input hierarchy**; strictly demarcates observed telemetry from authoritative SIEM rule definitions. |
| **Detection Semantics** | Relied on raw event types (e.g. "traffic", "process"). No concept of incomplete rule definitions. | Assigns explicit semantics statuses (`VERIFIED`, `INCOMPLETE`, `PROVISIONAL`); tracks provenance and monitored entity. |
| **Archetype Classification** | Coarse classification; contaminated prompts with instructions from unrelated domains. | **12 standardized behavioral archetypes** with deterministic disambiguation and explicit contradiction rules. |
| **Prompt Template Synthesis** | Monolithic, static markdown prompt template for all rules. | Tailored **9-section synthesis** dynamically generated from semantics, archetype, and supported evidence fields. |
| **Common SOC Baseline** | Contained unsafe rules: forced 85–95% confidence intervals; classified all RFC-1918 traffic as benign. | **Enterprise SOC Baseline v2**: removed artificial confidence ranges; eliminated dangerous RFC-1918 benign rules. |
| **Evidence Contract Alignment**| Evidence Contracts were independently generated or out of sync with prompt text. | **Evidence Requirement Mapper** generates aligned Core, Conditional, and Optional contracts; excludes unsupported fields. |
| **Quality Validation** | No automated pre-approval validation. Analysts had to manually read markdown text. | **8 Mandatory Quality Gates (G1–G8)** evaluated deterministically with hard-gate overrides and 0–100 inspection indexing. |
| **Hard-Gate Safety Override** | Not implemented. High scores or manual overrides could push broken prompts to production. | **Hard-Gate Override Rule**: G1 (incomplete definition) or G2 (archetype contradiction) failure immediately forces `approval_eligible = False`. |
| **Simulation Lab Role** | Standalone tool for manual dry-run replays; decoupled from prompt approval. | Integrated as **Gate G8**: candidate policies must pass historical regression testing before production approval. |
| **Cold-Start Handling** | N/A (Simulation was not an approval gate). | When historical samples $N < 5$, returns `INSUFFICIENT_DATA`; waives check with caution warning rather than blocking new rules. |
| **Approval Workflow** | Analysts could self-approve drafts; no pre-validation check; contract remained decoupled. | Strict **SOC Lead RBAC**; blocks unverified drafts; atomically synchronizes policy and Evidence Contract to `APPROVED`. |
| **Enterprise Scalability** | Single-rule editing UI only; unmanageable for 2,000+ rules. | **Bulk Quality Audit Service** audits libraries in bounded 100-rule chunks at ~120 rules/second with progress tracking. |
| **Drift Detection** | Static prompts; changes in SIEM rules went undetected. | **Policy Lifecycle Monitor** actively tracks SIEM hash modifications, schema drift, and verified analyst divergence. |
| **Rollback Safety** | Manual text copying; potential loss of historical audit trail. | **Non-destructive rollback**: creating a rollback version creates a new increment ($N+1$), preserving complete lineage. |
