# Database Schema Changes and Alembic Migration (AIS 2.1)

## 1. Overview and Design Decisions

The database schema for AIS 2.1 was designed with the following architectural requirements:
1. **Full Traceability**: Every individual dry-run assessment, sufficiency check, and batch evaluation run must be persisted with immutable timestamps.
2. **SQLAlchemy 2.0 Strict Typing**: Models use `Mapped[T]` and `mapped_column()` declarative typing compliant with SQLAlchemy 2.0 standards.
3. **Database Engine Portability**: Compatible with both PostgreSQL (production target) and SQLite (local dev/test harnesses). JSON fields are stored as text/JSON with automatic serialization.
4. **Clean Migration Path**: Implemented under revision `006_verdict_intelligence_validation.py` branching off migration `005`.

---

## 2. Table Specifications

### 1. `verdict_trust_assessments`
Stores the output of single-incident or batch trust evaluations.
- `id` (String(36), PK): UUID.
- `rule_id` (String(255), Index): Target SIEM rule ID.
- `incident_id` (String(255), Index): Historical SIEM incident ID.
- `policy_version_id` (String(255), Nullable): Evaluated policy version.
- `raw_trust_score` (Float): Weighted raw score (0.0–100.0).
- `ordinal_trust_score` (Integer): Discrete trust scale (1–10).
- `is_calibrated` (Boolean): False if historical sample size $< 30$.
- `original_suggested_verdict` (String(50)): Raw LLM recommendation.
- `final_enforced_verdict` (String(50)): Verdict after guardrails G1–G7.
- `is_demoted` (Boolean): True if guardrail overridden.
- `demotion_reasons` (JSON/Text): List of triggered guardrails.
- `claim_support_score` (Float): Percentage of verified claims.
- `unsupported_claims_count` (Integer): Number of ungrounded entities.
- `contradictions_count` (Integer): Detected directional/data paradoxes.
- `created_at` (DateTime): Evaluation timestamp.

### 2. `evidence_sufficiency_audits`
Stores granular evidence contract compliance evaluations.
- `id` (String(36), PK): UUID.
- `incident_id` (String(255), Index): Incident reference.
- `rule_id` (String(255), Index): Associated rule.
- `is_sufficient` (Boolean): Infallible flag (False if any mandatory missing).
- `sufficiency_score` (Float): 4-tier weighted score (0.0–100.0).
- `missing_mandatory_fields` (JSON/Text): Missing essential fields.
- `coverage_score`, `integrity_score`, `consistency_score`, `freshness_score` (Float): Tier scores.
- `created_at` (DateTime): Timestamp.

### 3. `historical_ground_truth_records`
Stores adjudicated historical labels stripped of analyst leakage.
- `id` (String(36), PK): UUID.
- `incident_id` (String(255), Unique Index): Canonical incident ID.
- `rule_id` (String(255), Index): Rule identifier.
- `adjudicated_label` (String(50)): `TRUE_POSITIVE`, `FALSE_POSITIVE`, or `REQUIRES_ANALYST_ATTENTION`.
- `adjudication_confidence` (Float): Confidence in ground truth (0.0–1.0).
- `partition` (String(50)): `TRAIN`, `VALIDATION`, `BLIND_BENCHMARK`, `STRESS`.
- `sanitized_telemetry` (JSON/Text): Cleaned raw SIEM logs.
- `original_analyst_notes_hash` (String(64)): Audit hash of stripped notes.
- `created_at` (DateTime): Record creation time.

### 4. `historical_evaluation_runs`
Tracks batch historical simulation runs.
- `id` (String(36), PK): UUID.
- `policy_version_id` (String(255), Index): Tested policy version.
- `rule_id` (String(255), Index): Target rule.
- `status` (String(50)): `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`.
- `sample_size` (Integer): Number of evaluated incidents.
- `balanced_accuracy` (Float): Empirical balanced accuracy.
- `ece` (Float): Expected Calibration Error.
- `brier_score` (Float): Brier calibration score.
- `metrics_payload` (JSON/Text): Complete confusion matrix and Wilson CIs.
- `created_at` (DateTime): Run start timestamp.

### 5. `historical_evaluation_results`
Individual incident records within a batch evaluation run.
- `id` (String(36), PK): UUID.
- `run_id` (String(36), FK -> `historical_evaluation_runs.id`, Index): Parent run.
- `incident_id` (String(255), Index): Incident ID.
- `rule_id` (String(255)): Associated rule.
- `ground_truth_label` (String(50), Nullable): Target label.
- `suggested_verdict` (String(50)): Model proposed verdict.
- `enforced_verdict` (String(50)): Final guardrail verdict.
- `trust_score` (Integer): Ordinal score (1–10).
- `is_correct` (Boolean, Nullable): Alignment with ground truth.
- `created_at` (DateTime): Timestamp.

---

## 3. Migration Verification

The migration script `backend/alembic/versions/006_verdict_intelligence_validation.py` was executed and verified using Alembic:
```bash
python -m alembic upgrade head
```
Output confirmed:
```
INFO  [alembic.runtime.migration] Running upgrade 005_agent_intelligence_studio_2 -> 006_verdict_intelligence_validation
```
All tables, indexes, and foreign keys were created cleanly with zero constraint violations.
