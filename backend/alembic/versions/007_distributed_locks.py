"""007_distributed_locks

Revision ID: 007_distributed_locks
Revises: 006_verdict_intelligence_validation
Create Date: 2026-11-10 21:05:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "007_distributed_locks"
down_revision = "006_verdict_intelligence_validation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "distributed_locks" not in existing_tables:
        op.create_table(
            "distributed_locks",
            sa.Column("lock_key", sa.String(128), primary_key=True),
            sa.Column("owner_id", sa.String(128), nullable=False),
            sa.Column("acquired_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_distributed_locks_expires_at", "distributed_locks", ["expires_at"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "distributed_locks" in set(inspector.get_table_names()):
        op.drop_index("ix_distributed_locks_expires_at", table_name="distributed_locks")
        op.drop_table("distributed_locks")

