"""011_prompt_inspector_hardening

Revision ID: 011_prompt_inspector_hardening
Revises: 010_actual_llm_prompt_inspector
Create Date: 2026-11-14 21:50:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = "011_prompt_inspector_hardening"
down_revision = "010_actual_llm_prompt_inspector"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "actual_llm_prompt_captures" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("actual_llm_prompt_captures")}

        if "canonical_serialized_payload" not in existing_cols:
            op.add_column("actual_llm_prompt_captures", sa.Column("canonical_serialized_payload", sa.Text(), nullable=True))
        if "payload_format" not in existing_cols:
            op.add_column("actual_llm_prompt_captures", sa.Column("payload_format", sa.String(32), nullable=False, server_default="CANONICAL_JSON"))
        if "policy_snapshot_hash" not in existing_cols:
            op.add_column("actual_llm_prompt_captures", sa.Column("policy_snapshot_hash", sa.String(64), nullable=True))
        if "retry_count" not in existing_cols:
            op.add_column("actual_llm_prompt_captures", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
        if "is_active_verdict_capture" not in existing_cols:
            op.add_column("actual_llm_prompt_captures", sa.Column("is_active_verdict_capture", sa.Boolean(), nullable=False, server_default="1"))
        if "is_simulated" not in existing_cols:
            op.add_column("actual_llm_prompt_captures", sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default="0"))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "actual_llm_prompt_captures" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("actual_llm_prompt_captures")}
        with op.batch_alter_table("actual_llm_prompt_captures") as batch_op:
            if "is_simulated" in existing_cols:
                batch_op.drop_column("is_simulated")
            if "is_active_verdict_capture" in existing_cols:
                batch_op.drop_column("is_active_verdict_capture")
            if "retry_count" in existing_cols:
                batch_op.drop_column("retry_count")
            if "policy_snapshot_hash" in existing_cols:
                batch_op.drop_column("policy_snapshot_hash")
            if "payload_format" in existing_cols:
                batch_op.drop_column("payload_format")
            if "canonical_serialized_payload" in existing_cols:
                batch_op.drop_column("canonical_serialized_payload")
