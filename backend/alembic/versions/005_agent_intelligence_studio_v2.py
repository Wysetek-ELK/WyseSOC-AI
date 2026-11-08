"""005_agent_intelligence_studio_v2

Revision ID: 005_agent_intelligence_studio_v2
Revises: 004_phase4_production_hardening
Create Date: 2026-11-08 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "005_agent_intelligence_studio_v2"
down_revision = "004_phase4_production_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # 1. Add quality columns to prompt_versions if present
    if "prompt_versions" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("prompt_versions")}
        with op.batch_alter_table("prompt_versions") as batch_op:
            if "quality_status" not in existing_cols:
                batch_op.add_column(sa.Column("quality_status", sa.String(32), server_default="GENERATED_DRAFT", nullable=False))
            if "quality_score" not in existing_cols:
                batch_op.add_column(sa.Column("quality_score", sa.Float(), nullable=True))
            if "quality_assessment_id" not in existing_cols:
                batch_op.add_column(sa.Column("quality_assessment_id", sa.String(64), nullable=True))

    # 2. Create rule_intelligence_snapshots table
    if "rule_intelligence_snapshots" not in existing_tables:
        op.create_table(
            "rule_intelligence_snapshots",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("rule_id", sa.String(36), sa.ForeignKey("rules.id", ondelete="CASCADE"), unique=True, index=True, nullable=False),
            sa.Column("rule_identifier", sa.String(128), index=True, nullable=False),
            sa.Column("primary_archetype", sa.String(64), index=True, default="UNKNOWN", nullable=False),
            sa.Column("secondary_archetype", sa.String(64), nullable=True),
            sa.Column("definition_status", sa.String(32), index=True, default="UNKNOWN", nullable=False),
            sa.Column("source_provenance", sa.String(64), default="HEURISTIC_PARSER", nullable=False),
            sa.Column("threshold", sa.Float(), nullable=True),
            sa.Column("threshold_unit", sa.String(32), nullable=True),
            sa.Column("aggregation_window", sa.String(64), nullable=True),
            sa.Column("review_required", sa.Boolean(), default=True, nullable=False),
            sa.Column("semantics_payload", sa.JSON(), nullable=False),
            sa.Column("rule_digest", sa.String(64), default="", nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )

    # 3. Create policy_quality_assessments table
    if "policy_quality_assessments" not in existing_tables:
        op.create_table(
            "policy_quality_assessments",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("rule_id", sa.String(36), sa.ForeignKey("rules.id", ondelete="CASCADE"), index=True, nullable=False),
            sa.Column("prompt_version_id", sa.String(36), sa.ForeignKey("prompt_versions.id", ondelete="SET NULL"), index=True, nullable=True),
            sa.Column("version_number", sa.Integer(), default=1, nullable=False),
            sa.Column("archetype", sa.String(64), default="UNKNOWN", nullable=False),
            sa.Column("quality_score", sa.Float(), default=0.0, nullable=False),
            sa.Column("approval_eligible", sa.Boolean(), default=False, index=True, nullable=False),
            sa.Column("simulation_status", sa.String(32), default="NOT_EVALUATED", nullable=False),
            sa.Column("score_breakdown", sa.JSON(), nullable=False),
            sa.Column("gate_results", sa.JSON(), nullable=False),
            sa.Column("blocking_issues", sa.JSON(), nullable=False),
            sa.Column("warnings", sa.JSON(), nullable=False),
            sa.Column("missing_evidence_mappings", sa.JSON(), nullable=False),
            sa.Column("recommendations", sa.JSON(), nullable=False),
            sa.Column("policy_digest", sa.String(64), default="", nullable=False),
            sa.Column("contract_digest", sa.String(64), default="", nullable=False),
            sa.Column("rule_digest", sa.String(64), default="", nullable=False),
            sa.Column("validator_version", sa.String(32), default="v2.0.0", nullable=False),
            sa.Column("evaluated_at", sa.DateTime(), nullable=False),
        )

    # 4. Create policy_drift_events table
    if "policy_drift_events" not in existing_tables:
        op.create_table(
            "policy_drift_events",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("rule_id", sa.String(36), sa.ForeignKey("rules.id", ondelete="CASCADE"), index=True, nullable=False),
            sa.Column("prompt_version_id", sa.String(36), sa.ForeignKey("prompt_versions.id", ondelete="SET NULL"), nullable=True),
            sa.Column("trigger_type", sa.String(64), index=True, nullable=False),
            sa.Column("summary", sa.String(512), default="", nullable=False),
            sa.Column("changed_fields", sa.JSON(), nullable=False),
            sa.Column("revalidation_required", sa.Boolean(), default=True, nullable=False),
            sa.Column("acknowledged", sa.Boolean(), default=False, nullable=False),
            sa.Column("acknowledged_by_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    # 5. Create bulk_quality_audit_jobs table
    if "bulk_quality_audit_jobs" not in existing_tables:
        op.create_table(
            "bulk_quality_audit_jobs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("status", sa.String(32), default="PENDING", index=True, nullable=False),
            sa.Column("total_rules", sa.Integer(), default=0, nullable=False),
            sa.Column("processed_rules", sa.Integer(), default=0, nullable=False),
            sa.Column("passed_count", sa.Integer(), default=0, nullable=False),
            sa.Column("review_required_count", sa.Integer(), default=0, nullable=False),
            sa.Column("critical_issues_count", sa.Integer(), default=0, nullable=False),
            sa.Column("incomplete_definitions_count", sa.Integer(), default=0, nullable=False),
            sa.Column("missing_evidence_count", sa.Integer(), default=0, nullable=False),
            sa.Column("average_quality_score", sa.Float(), default=0.0, nullable=False),
            sa.Column("summary_metrics", sa.JSON(), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "bulk_quality_audit_jobs" in existing_tables:
        op.drop_table("bulk_quality_audit_jobs")
    if "policy_drift_events" in existing_tables:
        op.drop_table("policy_drift_events")
    if "policy_quality_assessments" in existing_tables:
        op.drop_table("policy_quality_assessments")
    if "rule_intelligence_snapshots" in existing_tables:
        op.drop_table("rule_intelligence_snapshots")

    if "prompt_versions" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("prompt_versions")}
        with op.batch_alter_table("prompt_versions") as batch_op:
            if "quality_assessment_id" in existing_cols:
                batch_op.drop_column("quality_assessment_id")
            if "quality_score" in existing_cols:
                batch_op.drop_column("quality_score")
            if "quality_status" in existing_cols:
                batch_op.drop_column("quality_status")
