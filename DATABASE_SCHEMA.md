# AI Verdict — Database Schema Specification

## 1. Schema Entity Relationship Diagram

```mermaid
erDiagram
    users ||--o{ audit_logs : generates
    users ||--o{ import_jobs : creates
    users ||--o{ investigations : assigned_to
    import_jobs ||--o{ incidents : imports
    rules ||--o{ incidents : matches
    rules ||--o{ rule_prompts : configures
    rules ||--o{ learning_records : groups
    rule_prompts ||--o{ prompt_versions : versions
    incidents ||--o{ incident_events : contains
    incidents ||--|| historical_ground_truth : isolates
    incidents ||--o{ investigations : triaged_by
    incidents ||--o{ learning_records : verified_as
    investigations ||--o{ investigation_questions : records
    investigations ||--o{ investigation_evidence : attaches

    users {
        varchar(36) id PK
        varchar(64) username UK
        varchar(128) email UK
        varchar(256) hashed_password
        varchar(128) full_name
        varchar(32) role
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    rules {
        varchar(36) id PK
        varchar(128) rule_id UK
        varchar(256) name
        varchar(128) event_type UK
        text description
        varchar(32) severity
        varchar(32) status
        varchar(256) data_source
        varchar(128) detection_tech
        varchar(64) evaluation_mode
        text pattern_logic
        text remediation
        text raw_rule_text
        jsonb parsed_metadata
        timestamp created_at
        timestamp updated_at
    }

    rule_prompts {
        varchar(36) id PK
        varchar(36) rule_id FK
        varchar(256) title
        varchar(36) active_version_id
        timestamp created_at
        timestamp updated_at
    }

    prompt_versions {
        varchar(36) id PK
        varchar(36) prompt_id FK
        integer version_number
        varchar(32) status
        boolean is_template_draft
        text common_prompt
        text rule_specific_prompt
        text detection_conditions
        text required_evidence
        text tp_indicators
        text fp_indicators
        text missing_info_criteria
        text escalation_conditions
        jsonb analyst_questions
        varchar(512) change_summary
        varchar(36) created_by_user_id FK
        varchar(36) approved_by_user_id FK
        timestamp approved_at
        timestamp created_at
    }

    learning_records {
        varchar(36) id PK
        varchar(36) rule_id FK
        varchar(36) incident_id FK
        varchar(32) verified_verdict
        text analyst_explanation
        jsonb tp_indicators
        jsonb fp_indicators
        jsonb missing_evidence
        jsonb evidence_references
        jsonb answered_questions
        varchar(32) verification_status
        timestamp feedback_timestamp
        timestamp created_at
    }

    investigations {
        varchar(36) id PK
        varchar(36) incident_id FK
        varchar(36) assigned_to_user_id FK
        varchar(32) status
        varchar(32) analyst_verdict
        text verdict_reason
        text analyst_notes
        boolean is_disputed
        boolean is_independently_verified
        text insufficient_evidence_reason
        timestamp created_at
        timestamp updated_at
    }

    investigation_questions {
        varchar(36) id PK
        varchar(36) investigation_id FK
        text question
        text answer
        varchar(36) asked_by_user_id FK
        varchar(36) answered_by_user_id FK
        timestamp created_at
        timestamp answered_at
    }

    investigation_evidence {
        varchar(36) id PK
        varchar(36) investigation_id FK
        varchar(64) evidence_type
        varchar(256) reference_key
        text evidence_content
        text analyst_rationale
        timestamp created_at
    }

    incidents {
        varchar(36) id PK
        varchar(128) incident_id UK
        varchar(36) rule_id FK
        varchar(36) import_job_id FK
        varchar(128) event_type
        varchar(512) title
        text description
        text detail
        varchar(32) severity
        integer status_code
        varchar(64) category
        varchar(64) source_ip
        varchar(128) reporting_device
        bigint first_seen_epoch
        bigint last_seen_epoch
        bigint created_at_epoch
        jsonb raw_payload
        timestamp created_at
        timestamp updated_at
    }

    historical_ground_truth {
        varchar(36) id PK
        varchar(36) incident_id FK
        varchar(64) resolution
        text cleared_reason
        text comments
        varchar(128) cleared_user
        bigint cleared_time_epoch
        boolean is_ml_generated
        timestamp created_at
        timestamp updated_at
    }

    audit_logs {
        varchar(36) id PK
        varchar(64) user_id
        varchar(64) username
        varchar(64) action
        varchar(64) resource_type
        varchar(128) resource_id
        jsonb details
        varchar(64) ip_address
        timestamp created_at
    }
```

---

## 2. Table Specifications

### A. Phase 2 Tables

#### `investigations`
Manages the active SOC analyst triage workflow, question tracking, and verified verdicts.
- **`incident_id`**: Foreign key to `incidents.id` (`UNIQUE`, `ON DELETE CASCADE`).
- **`status`**: State machine (`PENDING_REVIEW`, `ASSIGNED`, `IN_PROGRESS`, `AWAITING_INFORMATION`, `REVIEWED`, `CLOSED_DRY_RUN`).
- **`analyst_verdict`**: Verified verdict (`TRUE_POSITIVE`, `FALSE_POSITIVE`, `REQUIRES_ATTENTION`).
- **`insufficient_evidence_reason`**: Mandatory reasoning when evidence is incomplete.
- **`is_disputed`**: Flag indicating conflict with historical ground truth.
- **`is_independently_verified`**: Quality flag enabling promotion to verified learning knowledge base.

#### `investigation_questions`
Threaded Q&A checklist items for hypothesis testing.
- **`investigation_id`**: Foreign key to `investigations.id`.
- **`question`**, **`answer`**, **`asked_by_user_id`**, **`answered_by_user_id`**.

#### `investigation_evidence`
Discrete technical artifacts attached to support the verdict.
- **`evidence_type`**: `TELEMETRY`, `LOG`, `PROCESS_TREE`, `FILE_HASH`, `NETWORK`, `REGISTRY`.
- **`reference_key`**: Specific artifact identifier (e.g., hash, IP, command).
- **`analyst_rationale`**: Technical justification.

#### `rule_prompts` & `prompt_versions`
Versioned prompt engineering store linking detection rules to structured LLM directives.
- **`is_template_draft`**: Boolean explicitly distinguishing template drafts synthesized from SIEM rules from AI outputs.
- **`status`**: `DRAFT`, `APPROVED`, `ARCHIVED`.
- **`active_version_id`**: Pointer to the approved production baseline prompt.

#### `learning_records`
Verified ground truth case repository used for future model evaluation and dry-run benchmarks.
- **`verified_verdict`**, **`analyst_explanation`**, **`tp_indicators`**, **`fp_indicators`**, **`missing_evidence`**, **`evidence_references`**.

---

### B. Phase 3 Tables (Dry-Run & Evaluation Framework)

#### `dry_run_configs`
Stores repeatable dry-run replay configurations linking SIEM rules, prompt versions, dataset partitions, and model providers.
- **`rule_id`**: Foreign key to `rules.id` (`NULL` evaluates across all ingested rules).
- **`prompt_version_id`**: Foreign key to `prompt_versions.id` (`NULL` defaults to active rule prompt).
- **`provider_type`**: `DISABLED`, `SIMULATED`, `OPENAI_COMPATIBLE`.
- **`split_strategy`**: `ALL`, `CHRONOLOGICAL_70_30`, `GROUP_AWARE_HOST`.
- **`dataset_filters`**: JSON filtering rules for custom subsets.

#### `dry_run_jobs`
Tracks batch replay execution tasks, item processing counters, and simulation flags.
- **`config_id`**: Foreign key to `dry_run_configs.id`.
- **`status`**: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`.
- **`total_items`**, **`processed_items`**, **`error_count`**.
- **`is_simulated`**: Boolean flag explicitly indicating simulated testing.
- **`started_at`**, **`completed_at`**.

#### `dry_run_results`
Stores fine-grained individual incident inference outputs and agreement metrics.
- **`job_id`**: Foreign key to `dry_run_jobs.id`.
- **`incident_id`**: Foreign key to `incidents.id`.
- **`predicted_verdict`**: `TRUE_POSITIVE`, `FALSE_POSITIVE`, `REQUIRES_ATTENTION`.
- **`confidence`**: 0.0 – 100.0.
- **`reasoning`**: Structured technical explanation.
- **`supporting_evidence`**, **`missing_evidence`**, **`analyst_questions`**.
- **`latency_ms`**: Measured execution latency.
- **`validation_status`**: `VALID`, `INVALID_SCHEMA`, `UNEXPECTED_VERDICT`.
- **`is_simulated`**: Boolean watermark tagging every simulated prediction.

#### `rule_maturity_evaluations`
Maintains the 5-tier conservative automation readiness lifecycle per SIEM rule.
- **`rule_id`**: Foreign key to `rules.id` (`UNIQUE`).
- **`maturity_status`**: `NOT_TESTED`, `LEARNING`, `UNDER_EVALUATION`, `CANDIDATE_FOR_AUTOMATION`, `APPROVED_FOR_AUTOMATION`.
- **`precision_score`**, **`recall_score`**, **`f1_score`**, **`coverage_score`**, **`sample_size`**.
- **`unresolved_evidence_gaps`**: Identified recurring telemetry deficiencies.
- **`is_admin_approved`**: Boolean human sign-off flag.
- **`approved_by_user_id`**, **`approved_at`**, **`approval_notes`**.

---

### C. Phase 1 Core Tables (Isolated Ground Truth Layer)

#### `historical_ground_truth`
**CRITICAL ISOLATION**: Stored in a completely dedicated table. Submitting an analyst verdict in `investigations` never updates or contaminates this table.
- **`resolution`**: Historical SIEM label ("True Positive", "False Positive").
- **`cleared_reason`**, **`comments`**, **`cleared_user`**, **`cleared_time_epoch`**, **`is_ml_generated`**.
