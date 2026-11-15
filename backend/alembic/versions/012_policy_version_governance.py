"""012_policy_version_governance

Revision ID: 012_policy_version_governance
Revises: 011_prompt_inspector_hardening
Create Date: 2026-11-15 10:45:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = "012_policy_version_governance"
down_revision = "011_prompt_inspector_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "rule_prompts" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("rule_prompts")}
        if "ai_execution_suspended" not in existing_cols:
            op.add_column("rule_prompts", sa.Column("ai_execution_suspended", sa.Boolean(), nullable=False, server_default="0"))
        if "suspension_reason" not in existing_cols:
            op.add_column("rule_prompts", sa.Column("suspension_reason", sa.String(256), nullable=True))

    if "prompt_versions" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("prompt_versions")}
        if "revoked_by_user_id" not in existing_cols:
            op.add_column("prompt_versions", sa.Column("revoked_by_user_id", sa.String(36), nullable=True))
        if "revoked_at" not in existing_cols:
            op.add_column("prompt_versions", sa.Column("revoked_at", sa.DateTime(), nullable=True))
        if "revocation_reason" not in existing_cols:
            op.add_column("prompt_versions", sa.Column("revocation_reason", sa.Text(), nullable=True))
        if "previous_status" not in existing_cols:
            op.add_column("prompt_versions", sa.Column("previous_status", sa.String(32), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "prompt_versions" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("prompt_versions")}
        with op.batch_alter_table("prompt_versions") as batch_op:
            if "previous_status" in existing_cols:
                batch_op.drop_column("previous_status")
            if "revocation_reason" in existing_cols:
                batch_op.drop_column("revocation_reason")
            if "revoked_at" in existing_cols:
                batch_op.drop_column("revoked_at")
            if "revoked_by_user_id" in existing_cols:
                batch_op.drop_column("revoked_by_user_id")

    if "rule_prompts" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("rule_prompts")}
        with op.batch_alter_table("rule_prompts") as batch_op:
            if "suspension_reason" in existing_cols:
                batch_op.drop_column("suspension_reason")
            if "ai_execution_suspended" in existing_cols:
                batch_op.drop_column("ai_execution_suspended")
