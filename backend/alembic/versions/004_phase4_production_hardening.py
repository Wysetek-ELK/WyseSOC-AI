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
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # 1. Add ai_verdict column to incidents if not present
    if "incidents" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("incidents")}
        if "ai_verdict" not in existing_cols:
            with op.batch_alter_table("incidents") as batch_op:
                batch_op.add_column(sa.Column("ai_verdict", sa.JSON(), nullable=True))

    # 2. Add bifurcated token analytics columns to dry_run_results
    if "dry_run_results" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("dry_run_results")}
        with op.batch_alter_table("dry_run_results") as batch_op:
            if "prompt_tokens" not in existing_cols:
                batch_op.add_column(sa.Column("prompt_tokens", sa.Integer(), server_default="0", nullable=False))
            if "completion_tokens" not in existing_cols:
                batch_op.add_column(sa.Column("completion_tokens", sa.Integer(), server_default="0", nullable=False))
            if "total_tokens" not in existing_cols:
                batch_op.add_column(sa.Column("total_tokens", sa.Integer(), server_default="0", nullable=False))

    # 3. Add cryptographic HMAC signature columns to audit_logs
    if "audit_logs" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("audit_logs")}
        with op.batch_alter_table("audit_logs") as batch_op:
            if "signature" not in existing_cols:
                batch_op.add_column(sa.Column("signature", sa.String(128), nullable=True))
            if "key_id" not in existing_cols:
                batch_op.add_column(sa.Column("key_id", sa.String(64), nullable=True))

    # 4. System Server Metric Samples (Server 1 & Server 2)
    if "system_server_samples" not in existing_tables:
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
    if "token_usage_records" not in existing_tables:
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
    if "telemetry_timeline_records" not in existing_tables:
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
    if "queued_tasks" not in existing_tables:
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
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "queued_tasks" in existing_tables:
        op.drop_table("queued_tasks")
    if "telemetry_timeline_records" in existing_tables:
        op.drop_table("telemetry_timeline_records")
    if "token_usage_records" in existing_tables:
        op.drop_table("token_usage_records")
    if "system_server_samples" in existing_tables:
        op.drop_table("system_server_samples")

    if "audit_logs" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("audit_logs")}
        with op.batch_alter_table("audit_logs") as batch_op:
            if "key_id" in existing_cols:
                batch_op.drop_column("key_id")
            if "signature" in existing_cols:
                batch_op.drop_column("signature")

    if "dry_run_results" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("dry_run_results")}
        with op.batch_alter_table("dry_run_results") as batch_op:
            if "total_tokens" in existing_cols:
                batch_op.drop_column("total_tokens")
            if "completion_tokens" in existing_cols:
                batch_op.drop_column("completion_tokens")
            if "prompt_tokens" in existing_cols:
                batch_op.drop_column("prompt_tokens")

    if "incidents" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("incidents")}
        if "ai_verdict" in existing_cols:
            with op.batch_alter_table("incidents") as batch_op:
                batch_op.drop_column("ai_verdict")
