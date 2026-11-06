"""003_phase3_dryrun_and_evaluation

Revision ID: 003_phase3_dryrun_and_evaluation
Revises: 002_phase2_investigation_and_learning
Create Date: 2026-11-05 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "003_phase3_dryrun_and_evaluation"
down_revision = "002_phase2_investigation_and_learning"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Dry Run Configs
    op.create_table(
        "dry_run_configs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), default=""),
        sa.Column("rule_id", sa.String(36), sa.ForeignKey("rules.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("prompt_version_id", sa.String(36), sa.ForeignKey("prompt_versions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider_type", sa.String(32), default="SIMULATED", nullable=False),
        sa.Column("split_strategy", sa.String(32), default="ALL", nullable=False),
        sa.Column("dataset_filters", sa.JSON(), default=dict),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # Dry Run Jobs
    op.create_table(
        "dry_run_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("config_id", sa.String(36), sa.ForeignKey("dry_run_configs.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("status", sa.String(32), default="PENDING", index=True, nullable=False),
        sa.Column("total_items", sa.Integer(), default=0),
        sa.Column("processed_items", sa.Integer(), default=0),
        sa.Column("error_count", sa.Integer(), default=0),
        sa.Column("is_simulated", sa.Boolean(), default=True, index=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )

    # Dry Run Results
    op.create_table(
        "dry_run_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("dry_run_jobs.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("incident_id", sa.String(36), sa.ForeignKey("incidents.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("predicted_verdict", sa.String(32), index=True, nullable=False),
        sa.Column("confidence", sa.Integer(), default=100),
        sa.Column("reasoning", sa.Text(), default=""),
        sa.Column("supporting_evidence", sa.JSON(), default=list),
        sa.Column("missing_evidence", sa.JSON(), default=list),
        sa.Column("analyst_questions", sa.JSON(), default=list),
        sa.Column("latency_ms", sa.Integer(), default=0),
        sa.Column("model_identifier", sa.String(64), default="simulated-v1"),
        sa.Column("prompt_version_number", sa.Integer(), default=1),
        sa.Column("validation_status", sa.String(32), default="VALID", index=True),
        sa.Column("is_simulated", sa.Boolean(), default=True, index=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # Rule Maturity Evaluations
    op.create_table(
        "rule_maturity_evaluations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("rule_id", sa.String(36), sa.ForeignKey("rules.id", ondelete="CASCADE"), unique=True, index=True, nullable=False),
        sa.Column("maturity_status", sa.String(32), default="NOT_TESTED", index=True, nullable=False),
        sa.Column("precision_score", sa.Float(), default=0.0),
        sa.Column("recall_score", sa.Float(), default=0.0),
        sa.Column("f1_score", sa.Float(), default=0.0),
        sa.Column("coverage_score", sa.Float(), default=0.0),
        sa.Column("sample_size", sa.Integer(), default=0),
        sa.Column("unresolved_evidence_gaps", sa.JSON(), default=list),
        sa.Column("recommendation_explanation", sa.Text(), default=""),
        sa.Column("is_admin_approved", sa.Boolean(), default=False),
        sa.Column("approved_by_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("approval_notes", sa.Text(), default=""),
        sa.Column("latest_test_date", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("rule_maturity_evaluations")
    op.drop_table("dry_run_results")
    op.drop_table("dry_run_jobs")
    op.drop_table("dry_run_configs")
