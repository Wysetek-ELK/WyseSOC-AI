"""016_ground_truth_certification_and_cohort_isolation

Revision ID: 016_ground_truth_certification_and_cohort_isolation
Revises: 015_immutable_approval_history_protection
Create Date: 2026-11-25 07:40:00.000000

Additive, non-destructive schema extensions for AIS 2.6f:
- Extends analyst_verdict_reviews with certification, lock, snapshot hash, and learning-isolation columns.
- Creates benchmark_cohorts, benchmark_cohort_items, and benchmark_review_revisions tables.
"""
import sqlalchemy as sa
from alembic import op

revision = "016_ground_truth_certification_and_cohort_isolation"
down_revision = "015_immutable_approval_history_protection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())
    false_default = sa.text("0" if conn.dialect.name == "sqlite" else "false")
    true_default = sa.text("1" if conn.dialect.name == "sqlite" else "true")

    if "analyst_verdict_reviews" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("analyst_verdict_reviews")}
        with op.batch_alter_table("analyst_verdict_reviews") as batch_op:
            if "benchmark_cohort_id" not in existing_cols:
                batch_op.add_column(sa.Column("benchmark_cohort_id", sa.String(64), nullable=True))
                batch_op.create_index("ix_avr_benchmark_cohort_id", ["benchmark_cohort_id"])
            if "certification_round" not in existing_cols:
                batch_op.add_column(sa.Column("certification_round", sa.Integer(), server_default=sa.text("1"), nullable=False))
            if "review_mode" not in existing_cols:
                batch_op.add_column(sa.Column("review_mode", sa.String(32), server_default=sa.text("'OPERATIONAL'"), nullable=False))
                batch_op.create_index("ix_avr_review_mode", ["review_mode"])
            if "detection_correctness" not in existing_cols:
                batch_op.add_column(sa.Column("detection_correctness", sa.String(32), nullable=True))
            if "authorization_context" not in existing_cols:
                batch_op.add_column(sa.Column("authorization_context", sa.String(32), nullable=True))
            if "confidence_level" not in existing_cols:
                batch_op.add_column(sa.Column("confidence_level", sa.String(16), nullable=True))
            if "evidence_sufficiency_status" not in existing_cols:
                batch_op.add_column(sa.Column("evidence_sufficiency_status", sa.String(32), nullable=True))
            if "evidence_snapshot_hash" not in existing_cols:
                batch_op.add_column(sa.Column("evidence_snapshot_hash", sa.String(64), nullable=True))
            if "rule_snapshot_hash" not in existing_cols:
                batch_op.add_column(sa.Column("rule_snapshot_hash", sa.String(64), nullable=True))
            if "additional_evidence_json" not in existing_cols:
                batch_op.add_column(sa.Column("additional_evidence_json", sa.JSON(), nullable=True))
            if "attestation_flags" not in existing_cols:
                batch_op.add_column(sa.Column("attestation_flags", sa.JSON(), nullable=True))
            if "is_locked" not in existing_cols:
                batch_op.add_column(sa.Column("is_locked", sa.Boolean(), server_default=false_default, nullable=False))
            if "is_draft" not in existing_cols:
                batch_op.add_column(sa.Column("is_draft", sa.Boolean(), server_default=false_default, nullable=False))
            if "exposure_risk_flag" not in existing_cols:
                batch_op.add_column(sa.Column("exposure_risk_flag", sa.Boolean(), server_default=false_default, nullable=False))
            if "excluded_from_learning" not in existing_cols:
                batch_op.add_column(sa.Column("excluded_from_learning", sa.Boolean(), server_default=false_default, nullable=False))

    if "benchmark_cohorts" not in existing_tables:
        op.create_table(
            "benchmark_cohorts",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("cohort_key", sa.String(64), nullable=False, unique=True, index=True),
            sa.Column("name", sa.String(256), nullable=False),
            sa.Column("description", sa.Text(), server_default=""),
            sa.Column("version", sa.String(32), server_default="2.6e", nullable=False),
            sa.Column("is_frozen", sa.Boolean(), server_default=true_default, nullable=False),
            sa.Column("required_reviewers", sa.Integer(), server_default=sa.text("2"), nullable=False),
            sa.Column("excluded_from_learning", sa.Boolean(), server_default=true_default, nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    if "benchmark_cohort_items" not in existing_tables:
        op.create_table(
            "benchmark_cohort_items",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("cohort_id", sa.String(36), sa.ForeignKey("benchmark_cohorts.id", ondelete="CASCADE"), index=True, nullable=False),
            sa.Column("incident_db_id", sa.String(36), sa.ForeignKey("incidents.id", ondelete="SET NULL"), index=True, nullable=True),
            sa.Column("fortisiem_incident_id", sa.String(64), index=True, nullable=False),
            sa.Column("rule_id", sa.String(128), nullable=False),
            sa.Column("rule_name", sa.String(256), server_default=""),
            sa.Column("expected_policy_version_id", sa.String(64), nullable=True),
            sa.Column("expected_policy_prompt_id", sa.String(64), nullable=True),
            sa.Column("customer", sa.String(128), server_default="DEFAULT"),
            sa.Column("is_priority", sa.Boolean(), server_default=false_default, index=True, nullable=False),
            sa.Column("priority_rank", sa.Integer(), nullable=True),
            sa.Column("raw_evidence_sha256", sa.String(64), server_default=""),
            sa.Column("rule_definition_sha256", sa.String(64), server_default=""),
            sa.Column("canonical_evidence_sha256", sa.String(64), server_default=""),
            sa.Column("eligibility_status", sa.String(32), server_default="ELIGIBLE", nullable=False),
            sa.Column("certification_status", sa.String(32), server_default="GT0_UNREVIEWED", index=True, nullable=False),
            sa.Column("certified_verdict", sa.String(32), nullable=True),
            sa.Column("assigned_reviewer_1", sa.String(128), nullable=True),
            sa.Column("assigned_reviewer_2", sa.String(128), nullable=True),
            sa.Column("exposure_risk_flag", sa.Boolean(), server_default=false_default, nullable=False),
            sa.Column("exposure_risk_reason", sa.Text(), server_default=""),
            sa.Column("certification_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("cohort_id", "fortisiem_incident_id", name="uq_cohort_fortisiem_incident"),
        )

    if "benchmark_review_revisions" not in existing_tables:
        op.create_table(
            "benchmark_review_revisions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("review_id", sa.String(36), sa.ForeignKey("analyst_verdict_reviews.id", ondelete="CASCADE"), index=True, nullable=False),
            sa.Column("incident_id", sa.String(64), index=True, nullable=False),
            sa.Column("previous_verdict", sa.String(32), nullable=False),
            sa.Column("new_verdict", sa.String(32), nullable=False),
            sa.Column("previous_rationale", sa.Text(), server_default=""),
            sa.Column("new_rationale", sa.Text(), server_default=""),
            sa.Column("revised_by_user_id", sa.String(128), nullable=False),
            sa.Column("revision_reason", sa.Text(), server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "benchmark_review_revisions" in existing_tables:
        op.drop_table("benchmark_review_revisions")
    if "benchmark_cohort_items" in existing_tables:
        op.drop_table("benchmark_cohort_items")
    if "benchmark_cohorts" in existing_tables:
        op.drop_table("benchmark_cohorts")

    if "analyst_verdict_reviews" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("analyst_verdict_reviews")}
        drop_cols = [
            "benchmark_cohort_id", "certification_round", "review_mode",
            "detection_correctness", "authorization_context", "confidence_level",
            "evidence_sufficiency_status", "evidence_snapshot_hash", "rule_snapshot_hash",
            "additional_evidence_json", "attestation_flags", "is_locked", "is_draft",
            "exposure_risk_flag", "excluded_from_learning",
        ]
        with op.batch_alter_table("analyst_verdict_reviews") as batch_op:
            for col in drop_cols:
                if col in existing_cols:
                    batch_op.drop_column(col)
