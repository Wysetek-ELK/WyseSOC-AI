"""014_policy_version_history_management

Revision ID: 014_policy_version_history_management
Revises: 013_user_tenant_customer
Create Date: 2026-11-19 20:30:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = "014_policy_version_history_management"
down_revision = "013_user_tenant_customer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "prompt_versions" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("prompt_versions")}
        with op.batch_alter_table("prompt_versions") as batch_op:
            if "archived_at" not in existing_cols:
                batch_op.add_column(sa.Column("archived_at", sa.DateTime(), nullable=True))
            if "archived_by_user_id" not in existing_cols:
                batch_op.add_column(sa.Column("archived_by_user_id", sa.String(36), nullable=True))
            if "archival_reason" not in existing_cols:
                batch_op.add_column(sa.Column("archival_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "prompt_versions" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("prompt_versions")}
        with op.batch_alter_table("prompt_versions") as batch_op:
            if "archival_reason" in existing_cols:
                batch_op.drop_column("archival_reason")
            if "archived_by_user_id" in existing_cols:
                batch_op.drop_column("archived_by_user_id")
            if "archived_at" in existing_cols:
                batch_op.drop_column("archived_at")
