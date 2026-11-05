# AI Verdict — Database Schema Specification

## 1. Schema Entity Relationship Diagram

```mermaid
erDiagram
    users ||--o{ audit_logs : generates
    users ||--o{ import_jobs : creates
    import_jobs ||--o{ incidents : imports
    rules ||--o{ incidents : matches
    incidents ||--o{ incident_events : contains
    incidents ||--|| historical_ground_truth : isolates

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

    import_jobs {
        varchar(36) id PK
        varchar(256) filename
        varchar(32) file_type
        integer file_size
        integer total_files
        integer imported_count
        integer duplicate_count
        integer error_count
        varchar(32) status
        jsonb error_details
        varchar(64) created_by
        timestamp created_at
        timestamp completed_at
    }

    incidents {
        varchar(36) id PK
        varchar(64) incident_id UK
        varchar(36) rule_id FK
        varchar(36) import_job_id FK
        varchar(128) event_type
        varchar(512) title
        text description
        text detail
        varchar(32) severity
        varchar(32) event_severity
        integer status_code
        varchar(64) status_name
        varchar(128) category
        varchar(128) subcategory
        varchar(64) source_ip
        varchar(128) reporting_device
        varchar(64) reporting_ip
        varchar(128) customer
        varchar(64) ticket_id
        bigint first_seen_epoch
        bigint last_seen_epoch
        bigint created_at_epoch
        bigint updated_at_epoch
        jsonb raw_payload
        timestamp created_at
        timestamp updated_at
    }

    incident_events {
        varchar(36) id PK
        varchar(36) incident_id FK
        varchar(128) event_id
        bigint event_receive_time
        varchar(128) event_type
        text raw_log
        jsonb attributes
        timestamp created_at
    }

    historical_ground_truth {
        varchar(36) id PK
        varchar(36) incident_id FK UK
        varchar(64) resolution
        text cleared_reason
        text comments
        varchar(128) cleared_user
        bigint cleared_time_epoch
        bigint resolved_at_epoch
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

### `users`
Stores provisioned accounts and role assignments.
- `id`: UUID (Primary Key)
- `username`: Unique username (Indexed)
- `email`: Unique email (Indexed)
- `hashed_password`: Bcrypt / Argon2id salted hash
- `role`: Role (`Administrator`, `SOC Analyst`, `Read-Only Viewer`)
- `is_active`: Account active flag

### `rules`
Stores SIEM correlation rules parsed from vendor text or JSON definitions.
- `id`: UUID (Primary Key)
- `rule_id`: Unique Rule Identifier / Event Type (Indexed)
- `event_type`: Event type used for incident correlation (Indexed)
- `name`: Display name of detection rule
- `pattern_logic`: Detection conditions, regex filters, grouping expressions
- `remediation`: Triage and remediation instructions
- `raw_rule_text`: Unmodified rule definition text
- `parsed_metadata`: Vendor-specific triggered attributes and grouping tags (JSONB)

### `incidents`
Stores normalized searchable SIEM incident headers and unmodified raw payloads.
- `id`: UUID (Primary Key)
- `incident_id`: SIEM Incident ID (Unique, Indexed)
- `rule_id`: Foreign key to `rules.id` (Indexed)
- `import_job_id`: Foreign key to `import_jobs.id`
- `event_type`: Event type string (Indexed)
- `severity`: Standardized severity: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFORMATIONAL` (Indexed)
- `status_code`: Status integer (1 = Open, 2 = Closed)
- `source_ip`: Attacking or source host IP (Indexed)
- `first_seen_epoch`: Epoch millisecond timestamp
- `created_at_epoch`: Epoch millisecond timestamp (Indexed)
- `raw_payload`: Complete original incident JSON preserved unmodified (JSONB)

### `incident_events`
Stores individual security events contained within an incident's telemetry.
- `id`: UUID (Primary Key)
- `incident_id`: Foreign key to `incidents.id` (Indexed, CASCADE delete)
- `event_id`: SIEM Event ID
- `raw_log`: Raw text event log line
- `attributes`: Flexible dictionary of vendor-specific attributes (JSONB)

### `historical_ground_truth` (ISOLATED SECURITY TABLE)
Maintains historical verdict and closure-related data in a dedicated table, strictly isolated from incident investigation inputs.
- `id`: UUID (Primary Key)
- `incident_id`: Foreign key to `incidents.id` (Unique, Indexed, CASCADE delete)
- `resolution`: Historical verdict (e.g. `True Positive`, `False Positive`)
- `cleared_reason`: Closure reason provided by SIEM or analyst
- `comments`: Historical notes (e.g. `Resolution set by Machine Learning`)
- `cleared_user`: Analyst username who cleared the ticket
- `cleared_time_epoch`: Closure timestamp
- `is_ml_generated`: Flag indicating if resolution was set by an upstream ML model

### `audit_logs`
Immutable record of security and administrative actions.
- `id`: UUID (Primary Key)
- `username`: Operator username
- `action`: Action code (`LOGIN_SUCCESS`, `VIEW_INCIDENT`, `IMPORT_ZIP`, etc.)
- `resource_type`: Affected entity type (`INCIDENT`, `RULE`, `USER`, etc.)
- `details`: Structured action metadata (JSONB)
- `created_at`: Event timestamp (Indexed)

---

## 3. Future Extension Points (Phase 2 & Phase 3)

The schema includes explicit extension hooks for future phases without premature implementation:
- **Phase 2 Extensions**: `analyst_investigations`, `investigation_questions`, `rule_prompts`, `rule_prompt_versions`.
- **Phase 3 Extensions**: `evaluation_runs`, `model_predictions`, `rule_maturity_status`.
