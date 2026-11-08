"""006_verdict_intelligence_validation

Revision ID: 006_verdict_intelligence_validation
Revises: 005_agent_intelligence_studio_v2
Create Date: 2026-11-08 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "006_verdict_intelligence_validation"
down_revision = "005_agent_intelligence_studio_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # 1. verdict_trust_assessments
    if "verdict_trust_assessments" not in existing_tables:
        op.create_table(
            "verdict_trust_assessments",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("incident_id", sa.String(64), index=True, nullable=False),
            sa.Column("rule_id", sa.String(128), index=True, nullable=False),
            sa.Column("archetype", sa.String(64), default="UNKNOWN"),
            sa.Column("suggested_verdict", sa.String(32), nullable=False),
            sa.Column("effective_verdict", sa.String(32), index=True, nullable=False),
            sa.Column("trust_score", sa.Integer(), nullable=True),
            sa.Column("raw_trust_score", sa.Float(), default=0.0),
            sa.Column("evidence_sufficiency_score", sa.Float(), default=0.0),
            sa.Column("evidence_status", sa.String(32), default="INSUFFICIENT", index=True),
            sa.Column("score_dimensions", sa.JSON(), nullable=True),
            sa.Column("supporting_evidence", sa.JSON(), nullable=True),
            sa.Column("contradictory_evidence", sa.JSON(), nullable=True),
            sa.Column("missing_evidence", sa.JSON(), nullable=True),
            sa.Column("confidence_limitations", sa.JSON(), nullable=True),
            sa.Column("historical_validation_status", sa.String(32), default="UNCALIBRATED"),
            sa.Column("is_calibrated", sa.Boolean(), default=False),
            sa.Column("calibrated_probability", sa.Float(), nullable=True),
            sa.Column("applicable_policy_version", sa.Integer(), nullable=True),
            sa.Column("applicable_contract_version", sa.String(64), nullable=True),
            sa.Column("escalation_reason", sa.String(256), nullable=True),
            sa.Column("human_readable_explanation", sa.Text(), default=""),
            sa.Column("model_identifier", sa.String(64), default="default-model"),
            sa.Column("is_simulated", sa.Boolean(), default=False, index=True),
            sa.Column("evaluated_at", sa.DateTime(), nullable=False),
        )

    # 2. evidence_sufficiency_assessments
    if "evidence_sufficiency_assessments" not in existing_tables:
        op.create_table(
            "evidence_sufficiency_assessments",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("incident_id", sa.String(64), index=True, nullable=False),
            sa.Column("rule_id", sa.String(128), index=True, nullable=False),
            sa.Column("archetype", sa.String(64), default="UNKNOWN"),
            sa.Column("overall_sufficiency_score", sa.Float(), default=0.0),
            sa.Column("required_coverage_score", sa.Float(), default=0.0),
            sa.Column("integrity_provenance_score", sa.Float(), default=0.0),
            sa.Column("consistency_corroboration_score", sa.Float(), default=0.0),
            sa.Column("freshness_relevance_score", sa.Float(), default=0.0),
            sa.Column("evidence_status", sa.String(32), default="INSUFFICIENT", index=True),
            sa.Column("mandatory_fields_present", sa.JSON(), nullable=True),
            sa.Column("mandatory_fields_missing", sa.JSON(), nullable=True),
            sa.Column("conditional_fields_evaluated", sa.JSON(), nullable=True),
            sa.Column("optional_enrichment_present", sa.JSON(), nullable=True),
            sa.Column("unsupported_fields_requested", sa.JSON(), nullable=True),
            sa.Column("contradictions_detected", sa.JSON(), nullable=True),
            sa.Column("evaluated_at", sa.DateTime(), nullable=False),
        )

    # 3. ground_truth_validations
    if "ground_truth_validations" not in existing_tables:
        op.create_table(
            "ground_truth_validations",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("incident_id", sa.String(64), unique=True, index=True, nullable=False),
            sa.Column("rule_id", sa.String(128), index=True, nullable=False),
            sa.Column("original_analyst_verdict", sa.String(64), default=""),
            sa.Column("adjudicated_label", sa.String(32), index=True, nullable=False),
            sa.Column("provenance", sa.String(64), default="HISTORICAL_IMPORT"),
            sa.Column("analyst_rationale", sa.Text(), nullable=True),
            sa.Column("label_reliability", sa.Float(), default=1.0),
            sa.Column("dataset_partition", sa.String(32), default="LOCKED_TEST", index=True),
            sa.Column("is_eligible_for_evaluation", sa.Boolean(), default=True, index=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    # 4. historical_evaluation_runs
    if "historical_evaluation_runs" not in existing_tables:
        op.create_table(
            "historical_evaluation_runs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("run_name", sa.String(128), nullable=False),
            sa.Column("rule_id", sa.String(128), index=True, nullable=True),
            sa.Column("archetype", sa.String(64), index=True, nullable=True),
            sa.Column("dataset_id", sa.String(64), default="default-dataset"),
            sa.Column("dataset_hash", sa.String(64), default=""),
            sa.Column("policy_version_id", sa.String(64), nullable=True),
            sa.Column("baseline_run_id", sa.String(36), nullable=True),
            sa.Column("status", sa.String(32), default="PENDING", index=True),
            sa.Column("validation_state", sa.String(32), default="INCONCLUSIVE", index=True),
            sa.Column("total_cases", sa.Integer(), default=0),
            sa.Column("evaluated_cases", sa.Integer(), default=0),
            sa.Column("verified_ground_truth_cases", sa.Integer(), default=0),
            sa.Column("metrics", sa.JSON(), nullable=True),
            sa.Column("selective_metrics", sa.JSON(), nullable=True),
            sa.Column("calibration_metrics", sa.JSON(), nullable=True),
            sa.Column("regression_summary", sa.JSON(), nullable=True),
            sa.Column("config_snapshot", sa.JSON(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
        )

    # 5. historical_evaluation_results
    if "historical_evaluation_results" not in existing_tables:
        op.create_table(
            "historical_evaluation_results",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("run_id", sa.String(36), sa.ForeignKey("historical_evaluation_runs.id", ondelete="CASCADE"), index=True, nullable=False),
            sa.Column("incident_id", sa.String(64), index=True, nullable=False),
            sa.Column("rule_id", sa.String(128), index=True, nullable=False),
            sa.Column("suggested_verdict", sa.String(32), nullable=False),
            sa.Column("effective_verdict", sa.String(32), index=True, nullable=False),
            sa.Column("ground_truth_label", sa.String(32), nullable=True),
            sa.Column("trust_score", sa.Integer(), nullable=True),
            sa.Column("raw_trust_score", sa.Float(), default=0.0),
            sa.Column("evidence_sufficiency_score", sa.Float(), default=0.0),
            sa.Column("evidence_status", sa.String(32), default="INSUFFICIENT"),
            sa.Column("is_correct", sa.Boolean(), nullable=True),
            sa.Column("is_abstained", sa.Boolean(), default=False),
            sa.Column("is_critical_error", sa.Boolean(), default=False),
            sa.Column("claims_summary", sa.JSON(), nullable=True),
            sa.Column("escalation_reason", sa.String(256), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("historical_evaluation_results")
    op.drop_table("historical_evaluation_runs")
    op.drop_table("ground_truth_validations")
    op.drop_table("evidence_sufficiency_assessments")
    op.drop_table("verdict_trust_assessments")

