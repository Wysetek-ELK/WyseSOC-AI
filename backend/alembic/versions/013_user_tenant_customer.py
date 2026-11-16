"""013_user_tenant_customer

Revision ID: 013_user_tenant_customer
Revises: 012_policy_version_governance
Create Date: 2026-11-16 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = "013_user_tenant_customer"
down_revision = "012_policy_version_governance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "users" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("users")}
        existing_indexes = {ix["name"] for ix in inspector.get_indexes("users")}

        with op.batch_alter_table("users") as batch_op:
            if "customer" not in existing_cols:
                batch_op.add_column(sa.Column("customer", sa.String(128), nullable=True))
            if "ix_users_customer" not in existing_indexes:
                batch_op.create_index("ix_users_customer", ["customer"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "users" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("users")}
        existing_indexes = {ix["name"] for ix in inspector.get_indexes("users")}

        with op.batch_alter_table("users") as batch_op:
            if "ix_users_customer" in existing_indexes:
                batch_op.drop_index("ix_users_customer")
            if "customer" in existing_cols:
                batch_op.drop_column("customer")
