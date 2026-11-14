"""010_actual_llm_prompt_inspector

Revision ID: 010_actual_llm_prompt_inspector
Revises: 009_rule_learning_and_governance
Create Date: 2026-11-14 19:40:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = "010_actual_llm_prompt_inspector"
down_revision = "009_rule_learning_and_governance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "actual_llm_prompt_captures" not in existing_tables:
        op.create_table(
            "actual_llm_prompt_captures",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("execution_id", sa.String(36), nullable=False, index=True),
            sa.Column("incident_id", sa.String(64), nullable=False, index=True),
            sa.Column("rule_id", sa.String(128), nullable=False, index=True),
            sa.Column("rule_name", sa.String(256), nullable=False, server_default=""),
            sa.Column("policy_version_id", sa.String(64), nullable=True),
            sa.Column("policy_version_number", sa.Integer(), nullable=True),
            sa.Column("policy_status", sa.String(32), nullable=False, server_default="UNCONFIGURED"),
            sa.Column("policy_source", sa.String(32), nullable=False, server_default="DATABASE"),
            sa.Column("dispatch_status", sa.String(32), nullable=False, server_default="DISPATCHED"),
            sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("model_name", sa.String(64), nullable=False, server_default=""),
            sa.Column("provider_type", sa.String(64), nullable=False, server_default="OPENAI_COMPATIBLE"),
            sa.Column("generation_settings", sa.JSON(), nullable=False),
            sa.Column("compiled_system_prompt", sa.Text(), nullable=False),
            sa.Column("user_message", sa.Text(), nullable=False),
            sa.Column("rag_precedents", sa.JSON(), nullable=False),
            sa.Column("has_rag_precedents", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("evidence_requirements", sa.JSON(), nullable=False),
            sa.Column("verdict_schema", sa.JSON(), nullable=False),
            sa.Column("raw_request_payload", sa.JSON(), nullable=False),
            sa.Column("request_sha256", sa.String(64), nullable=False, index=True),
            sa.Column("response_raw", sa.Text(), nullable=True),
            sa.Column("response_verdict", sa.String(32), nullable=True),
            sa.Column("response_confidence", sa.Float(), nullable=True),
            sa.Column("prompt_tokens", sa.Integer(), nullable=True),
            sa.Column("completion_tokens", sa.Integer(), nullable=True),
            sa.Column("total_tokens", sa.Integer(), nullable=True),
            sa.Column("latency_ms", sa.Integer(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("prompt_integrity_status", sa.String(32), nullable=False, server_default="VERIFIED"),
            sa.Column("integrity_details", sa.JSON(), nullable=False),
            sa.Column("l1_explanation", sa.JSON(), nullable=False),
            sa.Column("is_redacted", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("captured_at", sa.DateTime(), nullable=False, server_default=sa.func.now(), index=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "actual_llm_prompt_captures" in existing_tables:
        op.drop_table("actual_llm_prompt_captures")
