"""008_soc_pilot

Revision ID: 008_soc_pilot
Revises: 007_distributed_locks
Create Date: 2026-11-11 11:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "008_soc_pilot"
down_revision = "007_distributed_locks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "pilot_configurations" not in existing_tables:
        op.create_table(
            "pilot_configurations",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("pilot_name", sa.String(128), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("is_active_config", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("mode", sa.String(32), nullable=False, server_default="DISABLED"),
            sa.Column("is_paused", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("selected_rule_ids", sa.JSON(), nullable=False),
            sa.Column("selected_archetypes", sa.JSON(), nullable=False),
            sa.Column("included_severities", sa.JSON(), nullable=False),
            sa.Column("ingestion_source", sa.String(32), nullable=False, server_default="ALL"),
            sa.Column("daily_evaluation_budget", sa.Integer(), nullable=False, server_default="500"),
            sa.Column("hourly_evaluation_budget", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("max_concurrent_inference", sa.Integer(), nullable=False, server_default="2"),
            sa.Column("request_timeout_seconds", sa.Float(), nullable=False, server_default="60.0"),
            sa.Column("require_analyst_review", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("require_approved_policy", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("allow_external_writeback", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("allow_auto_incident_closure", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("error_handling_policy", sa.String(64), nullable=False, server_default="ABSTAIN_AND_LOG"),
            sa.Column("consecutive_error_pause_threshold", sa.Integer(), nullable=False, server_default="5"),
            sa.Column("reporting_schedule", sa.String(32), nullable=False, server_default="HOURLY"),
            sa.Column("created_by", sa.String(128), nullable=False),
            sa.Column("updated_by", sa.String(128), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_pilot_configurations_mode", "pilot_configurations", ["mode"])
        op.create_index("ix_pilot_configurations_is_active_config", "pilot_configurations", ["is_active_config"])

    if "pilot_config_history" not in existing_tables:
        op.create_table(
            "pilot_config_history",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("pilot_id", sa.String(36), sa.ForeignKey("pilot_configurations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(64), nullable=False),
            sa.Column("mode", sa.String(32), nullable=False),
            sa.Column("is_paused", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("config_snapshot", sa.JSON(), nullable=False),
            sa.Column("change_reason", sa.Text(), nullable=False),
            sa.Column("changed_by", sa.String(128), nullable=False),
            sa.Column("changed_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_pilot_config_history_pilot_id", "pilot_config_history", ["pilot_id"])

    if "pilot_evaluations" not in existing_tables:
        op.create_table(
            "pilot_evaluations",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("idempotency_key", sa.String(192), nullable=False),
            sa.Column("pilot_id", sa.String(36), sa.ForeignKey("pilot_configurations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("pilot_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("incident_id", sa.String(64), nullable=False),
            sa.Column("incident_db_id", sa.String(36), nullable=True),
            sa.Column("rule_id", sa.String(128), nullable=False),
            sa.Column("archetype", sa.String(64), nullable=False, server_default="UNKNOWN"),
            sa.Column("severity", sa.String(32), nullable=False, server_default="MEDIUM"),
            sa.Column("execution_mode", sa.String(32), nullable=False),
            sa.Column("source_type", sa.String(32), nullable=False, server_default="LIVE"),
            sa.Column("eligibility_status", sa.String(32), nullable=False, server_default="EVALUATED"),
            sa.Column("proposed_verdict", sa.String(32), nullable=True),
            sa.Column("validated_verdict", sa.String(32), nullable=True),
            sa.Column("validation_status", sa.String(64), nullable=True),
            sa.Column("abstention_reason", sa.Text(), nullable=True),
            sa.Column("trust_score", sa.Integer(), nullable=True),
            sa.Column("raw_trust_score", sa.Float(), nullable=True),
            sa.Column("is_calibrated", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("evidence_completeness", sa.Float(), nullable=True),
            sa.Column("grounding_ratio", sa.Float(), nullable=True),
            sa.Column("supporting_evidence", sa.JSON(), nullable=False),
            sa.Column("contradictory_evidence", sa.JSON(), nullable=False),
            sa.Column("missing_evidence", sa.JSON(), nullable=False),
            sa.Column("policy_version_id", sa.String(64), nullable=True),
            sa.Column("policy_version_number", sa.Integer(), nullable=True),
            sa.Column("policy_digest", sa.String(128), nullable=True),
            sa.Column("model_identifier", sa.String(128), nullable=False, server_default=""),
            sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("evidence_snapshot_hash", sa.String(64), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("analyst_feedback_action", sa.String(32), nullable=True),
            sa.Column("analyst_decision", sa.String(32), nullable=True),
            sa.Column("analyst_override_reason", sa.Text(), nullable=True),
            sa.Column("analyst_user", sa.String(128), nullable=True),
            sa.Column("analyst_decided_at", sa.DateTime(), nullable=True),
            sa.Column("supervisor_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("supervisor_user", sa.String(128), nullable=True),
            sa.Column("supervisor_verified_at", sa.DateTime(), nullable=True),
            sa.Column("supervisor_notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_pilot_eval_idempotency", "pilot_evaluations", ["idempotency_key"], unique=True)
        op.create_index("ix_pilot_eval_pilot_created", "pilot_evaluations", ["pilot_id", "created_at"])
        op.create_index("ix_pilot_evaluations_incident_id", "pilot_evaluations", ["incident_id"])
        op.create_index("ix_pilot_evaluations_rule_id", "pilot_evaluations", ["rule_id"])
        op.create_index("ix_pilot_evaluations_execution_mode", "pilot_evaluations", ["execution_mode"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "pilot_evaluations" in existing_tables:
        op.drop_table("pilot_evaluations")
    if "pilot_config_history" in existing_tables:
        op.drop_table("pilot_config_history")
    if "pilot_configurations" in existing_tables:
        op.drop_table("pilot_configurations")

