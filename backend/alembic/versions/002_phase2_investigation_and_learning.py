"""002_phase2_investigation_and_learning

Revision ID: 002_phase2_investigation_and_learning
Revises: 001_initial_schema
Create Date: 2026-11-05 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "002_phase2_investigation_and_learning"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Investigations
    op.create_table(
        "investigations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("incident_id", sa.String(36), sa.ForeignKey("incidents.id", ondelete="CASCADE"), unique=True, index=True, nullable=False),
        sa.Column("assigned_to_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("status", sa.String(32), default="PENDING_REVIEW", index=True, nullable=False),
        sa.Column("analyst_verdict", sa.String(32), nullable=True, index=True),
        sa.Column("verdict_reason", sa.Text(), default=""),
        sa.Column("analyst_notes", sa.Text(), default=""),
        sa.Column("is_disputed", sa.Boolean(), default=False, index=True),
        sa.Column("is_independently_verified", sa.Boolean(), default=False, index=True),
        sa.Column("insufficient_evidence_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # Investigation Questions
    op.create_table(
        "investigation_questions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("investigation_id", sa.String(36), sa.ForeignKey("investigations.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), default=""),
        sa.Column("asked_by_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("answered_by_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("answered_at", sa.DateTime(), nullable=True),
    )

    # Investigation Evidence
    op.create_table(
        "investigation_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("investigation_id", sa.String(36), sa.ForeignKey("investigations.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("evidence_type", sa.String(64), default="TELEMETRY"),
        sa.Column("reference_key", sa.String(256), default=""),
        sa.Column("evidence_content", sa.Text(), default=""),
        sa.Column("analyst_rationale", sa.Text(), default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # Rule Prompts
    op.create_table(
        "rule_prompts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("rule_id", sa.String(36), sa.ForeignKey("rules.id", ondelete="CASCADE"), unique=True, index=True, nullable=False),
        sa.Column("title", sa.String(256), default=""),
        sa.Column("active_version_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # Prompt Versions
    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("prompt_id", sa.String(36), sa.ForeignKey("rule_prompts.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), default="DRAFT", index=True, nullable=False),
        sa.Column("is_template_draft", sa.Boolean(), default=True),
        sa.Column("common_prompt", sa.Text(), default=""),
        sa.Column("rule_specific_prompt", sa.Text(), default=""),
        sa.Column("detection_conditions", sa.Text(), default=""),
        sa.Column("required_evidence", sa.Text(), default=""),
        sa.Column("tp_indicators", sa.Text(), default=""),
        sa.Column("fp_indicators", sa.Text(), default=""),
        sa.Column("missing_info_criteria", sa.Text(), default=""),
        sa.Column("escalation_conditions", sa.Text(), default=""),
        sa.Column("analyst_questions", sa.JSON(), default=list),
        sa.Column("change_summary", sa.String(512), default="Initial draft"),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_by_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # Learning Records
    op.create_table(
        "learning_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("rule_id", sa.String(36), sa.ForeignKey("rules.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("incident_id", sa.String(36), sa.ForeignKey("incidents.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("verified_verdict", sa.String(32), nullable=False, index=True),
        sa.Column("analyst_explanation", sa.Text(), default=""),
        sa.Column("tp_indicators", sa.JSON(), default=list),
        sa.Column("fp_indicators", sa.JSON(), default=list),
        sa.Column("missing_evidence", sa.JSON(), default=list),
        sa.Column("evidence_references", sa.JSON(), default=list),
        sa.Column("answered_questions", sa.JSON(), default=list),
        sa.Column("verification_status", sa.String(32), default="VERIFIED", index=True),
        sa.Column("feedback_timestamp", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("learning_records")
    op.drop_table("prompt_versions")
    op.drop_table("rule_prompts")
    op.drop_table("investigation_evidence")
    op.drop_table("investigation_questions")
    op.drop_table("investigations")
