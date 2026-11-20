"""015_immutable_approval_history_protection

Revision ID: 015_immutable_approval_history_protection
Revises: 014_policy_version_history_management
Create Date: 2026-11-20 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = "015_immutable_approval_history_protection"
down_revision = "014_policy_version_history_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "prompt_versions" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("prompt_versions")}
        with op.batch_alter_table("prompt_versions") as batch_op:
            if "was_ever_approved" not in existing_cols:
                batch_op.add_column(
                    sa.Column(
                        "was_ever_approved",
                        sa.Boolean(),
                        server_default=sa.text("0" if conn.dialect.name == "sqlite" else "false"),
                        nullable=False,
                    )
                )

        # Authoritatively backfill historical approval flag for all versions that were ever approved
        conn.execute(
            sa.text(
                """
                UPDATE prompt_versions
                SET was_ever_approved = """ + ("1" if conn.dialect.name == "sqlite" else "true") + """
                WHERE status = 'APPROVED'
                   OR previous_status = 'APPROVED'
                   OR approved_at IS NOT NULL
                   OR approved_by_user_id IS NOT NULL;
                """
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "prompt_versions" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("prompt_versions")}
        with op.batch_alter_table("prompt_versions") as batch_op:
            if "was_ever_approved" in existing_cols:
                batch_op.drop_column("was_ever_approved")
