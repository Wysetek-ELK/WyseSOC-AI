"""019_sentinel_chat_persistence

Revision ID: 019_sentinel_chat_persistence
Revises: 018_ais32_rule_intelligence_and_context
Create Date: 2026-11-28 19:40:00.000000

Additive, non-destructive schema extension for Verdictum Sentinel Chat persistence:
- `sentinel_conversations`: user-isolated conversation threads
- `sentinel_messages`: persisted messages with lifecycle status, token usage, finish_reason, and continuation lineage
"""

import sqlalchemy as sa
from alembic import op

revision = "019_sentinel_chat_persistence"
down_revision = "018_ais32_rule_intelligence_and_context"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())
    false_default = sa.text("0" if conn.dialect.name == "sqlite" else "false")

    if "sentinel_conversations" not in existing_tables:
        op.create_table(
            "sentinel_conversations",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("customer", sa.String(128), nullable=True, index=True),
            sa.Column("title", sa.String(256), server_default="Sentinel Investigation", nullable=False),
            sa.Column("attached_incident_id", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, index=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False, index=True),
        )

    if "sentinel_messages" not in existing_tables:
        op.create_table(
            "sentinel_messages",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("conversation_id", sa.String(36), sa.ForeignKey("sentinel_conversations.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("request_id", sa.String(64), nullable=True, index=True),
            sa.Column("role", sa.String(24), nullable=False),
            sa.Column("content", sa.Text(), server_default="", nullable=False),
            sa.Column("reasoning_content", sa.Text(), nullable=True),
            sa.Column("status", sa.String(32), server_default="COMPLETED", nullable=False, index=True),
            sa.Column("finish_reason", sa.String(64), nullable=True),
            sa.Column("stream_termination", sa.String(64), nullable=True),
            sa.Column("model_identifier", sa.String(128), nullable=True),
            sa.Column("prompt_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("completion_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("reasoning_tokens", sa.Integer(), nullable=True),
            sa.Column("total_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("requested_max_tokens", sa.Integer(), nullable=True),
            sa.Column("effective_context_window", sa.Integer(), nullable=True),
            sa.Column("latency_ms", sa.Float(), server_default=sa.text("0.0"), nullable=False),
            sa.Column("is_continuation", sa.Boolean(), server_default=false_default, nullable=False),
            sa.Column("parent_message_id", sa.String(36), nullable=True, index=True),
            sa.Column("continuation_index", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("attached_incident_id", sa.String(64), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, index=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("sentinel_messages")
    op.drop_table("sentinel_conversations")
