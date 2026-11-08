"""004_phase4_production_hardening

Revision ID: 004_phase4_production_hardening
Revises: 003_phase3_dryrun_and_evaluation
Create Date: 2026-11-08 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "004_phase4_production_hardening"
down_revision = "003_phase3_dryrun_and_evaluation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add ai_verdict column to incidents if not present
    with op.batch_alter_table("incidents") as batch_op:
        batch_op.add_column(sa.Column("ai_verdict", sa.JSON(), nullable=True))

    # 2. Add bifurcated token analytics columns to dry_run_results
    with op.batch_alter_table("dry_run_results") as batch_op:
        batch_op.add_column(sa.Column("prompt_tokens", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("completion_tokens", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("total_tokens", sa.Integer(), server_default="0", nullable=False))

    # 3. Add cryptographic HMAC signature columns to audit_logs
    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.add_column(sa.Column("signature", sa.String(128), nullable=True))
        batch_op.add_column(sa.Column("key_id", sa.String(64), nullable=True))

    # 4. System Server Metric Samples (Server 1 & Server 2)
    op.create_table(
        "system_server_samples",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("server_id", sa.String(32), index=True, nullable=False),
        sa.Column("server_name", sa.String(128), nullable=False),
        sa.Column("timestamp", sa.DateTime(), index=True, nullable=False),
        sa.Column("status", sa.String(32), default="ONLINE", nullable=False),
        sa.Column("cpu_percent", sa.Float(), default=0.0, nullable=False),
        sa.Column("memory_percent", sa.Float(), default=0.0, nullable=False),
        sa.Column("memory_used_gb", sa.Float(), default=0.0, nullable=False),
        sa.Column("memory_total_gb", sa.Float(), default=0.0, nullable=False),
        sa.Column("disk_percent", sa.Float(), nullable=True),
        sa.Column("disk_used_gb", sa.Float(), nullable=True),
        sa.Column("disk_total_gb", sa.Float(), nullable=True),
        sa.Column("gpu_percent", sa.Float(), nullable=True),
        sa.Column("gpu_memory_percent", sa.Float(), nullable=True),
        sa.Column("gpu_memory_used_gb", sa.Float(), nullable=True),
        sa.Column("gpu_memory_total_gb", sa.Float(), nullable=True),
        sa.Column("gpu_temp_c", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("active_requests", sa.Integer(), nullable=True),
        sa.Column("details", sa.JSON(), default=dict),
    )

    # 5. Token Usage Records Ledger
    op.create_table(
        "token_usage_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("process_type", sa.String(64), index=True, nullable=False),
        sa.Column("process_id", sa.String(64), index=True, nullable=True),
        sa.Column("incident_id", sa.String(64), index=True, nullable=True),
        sa.Column("rule_id", sa.String(64), index=True, nullable=True),
        sa.Column("model_identifier", sa.String(128), index=True, nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), default=0, nullable=False),
        sa.Column("completion_tokens", sa.Integer(), default=0, nullable=False),
        sa.Column("total_tokens", sa.Integer(), default=0, nullable=False),
        sa.Column("latency_ms", sa.Integer(), default=0, nullable=False),
        sa.Column("estimated_cost_usd", sa.Float(), default=0.0, nullable=False),
        sa.Column("is_simulated", sa.Boolean(), default=False, index=True, nullable=False),
        sa.Column("executed_by_user", sa.String(64), default="system", nullable=False),
        sa.Column("timestamp", sa.DateTime(), index=True, nullable=False),
        sa.Column("details", sa.JSON(), default=dict),
    )

    # 6. Telemetry Timeline Records Ledger
    op.create_table(
        "telemetry_timeline_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("incident_id", sa.String(64), index=True, nullable=True),
        sa.Column("event_type", sa.String(128), index=True, nullable=False),
        sa.Column("stage", sa.String(64), index=True, nullable=False),
        sa.Column("summary", sa.String(512), nullable=False),
        sa.Column("source", sa.String(128), default="Server 1 Database", nullable=False),
        sa.Column("severity", sa.String(32), default="INFO", nullable=False),
        sa.Column("source_ip", sa.String(64), nullable=True),
        sa.Column("reporting_device", sa.String(128), nullable=True),
        sa.Column("epoch_ms", sa.BigInteger(), index=True, nullable=True),
        sa.Column("token_count", sa.Integer(), default=0, nullable=False),
        sa.Column("timestamp", sa.DateTime(), index=True, nullable=False),
        sa.Column("details", sa.JSON(), default=dict),
    )

    # 7. Durable Task Queue Ledger
    op.create_table(
        "queued_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_name", sa.String(128), index=True, nullable=False),
        sa.Column("queue_name", sa.String(64), index=True, default="live_triage", nullable=False),
        sa.Column("entity_type", sa.String(64), index=True, default="INCIDENT", nullable=False),
        sa.Column("entity_id", sa.String(64), index=True, nullable=False),
        sa.Column("status", sa.String(32), default="QUEUED", index=True, nullable=False),
        sa.Column("retry_count", sa.Integer(), default=0, nullable=False),
        sa.Column("max_retries", sa.Integer(), default=3, nullable=False),
        sa.Column("payload", sa.JSON(), default=dict),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("queued_tasks")
    op.drop_table("telemetry_timeline_records")
    op.drop_table("token_usage_records")
    op.drop_table("system_server_samples")

    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.drop_column("key_id")
        batch_op.drop_column("signature")

    with op.batch_alter_table("dry_run_results") as batch_op:
        batch_op.drop_column("total_tokens")
        batch_op.drop_column("completion_tokens")
        batch_op.drop_column("prompt_tokens")

    with op.batch_alter_table("incidents") as batch_op:
        batch_op.drop_column("ai_verdict")

