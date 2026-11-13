"""009_rule_learning_and_governance

Revision ID: 009_rule_learning_and_governance
Revises: 008_soc_pilot
Create Date: 2026-11-13 20:50:00.000000

"""
import uuid
from datetime import datetime, timezone
from alembic import op
import sqlalchemy as sa

revision = "009_rule_learning_and_governance"
down_revision = "008_soc_pilot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # 1. rule_learning_profiles
    if "rule_learning_profiles" not in existing_tables:
        op.create_table(
            "rule_learning_profiles",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("rule_id", sa.String(36), sa.ForeignKey("rules.id", ondelete="CASCADE"), nullable=False),
            sa.Column("rule_identifier", sa.String(128), nullable=False),
            sa.Column("customer", sa.String(128), nullable=False, server_default="DEFAULT"),
            sa.Column("primary_archetype", sa.String(64), nullable=False, server_default="UNKNOWN"),
            sa.Column("lifecycle_stage", sa.String(32), nullable=False, server_default="LEARNING"),
            sa.Column("active_prompt_version_id", sa.String(36), nullable=True),
            sa.Column("active_model_identifier", sa.String(64), nullable=False, server_default="Qwen/Qwen2.5-7B-Instruct-AWQ"),
            sa.Column("total_incidents_processed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_analyst_reviews", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("verified_tp_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("verified_fp_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("ai_correct_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("ai_incorrect_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("abstention_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("validation_failure_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("empirical_accuracy", sa.Float(), nullable=True),
            sa.Column("fp_precision", sa.Float(), nullable=True),
            sa.Column("tp_recall", sa.Float(), nullable=True),
            sa.Column("wilson_lower_bound", sa.Float(), nullable=True),
            sa.Column("error_distribution", sa.JSON(), nullable=False),
            sa.Column("last_evaluated_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("rule_id", "customer", name="uq_rule_customer_learning"),
        )
        op.create_index("ix_rule_learning_profiles_rule_id", "rule_learning_profiles", ["rule_id"])
        op.create_index("ix_rule_learning_profiles_rule_identifier", "rule_learning_profiles", ["rule_identifier"])
        op.create_index("ix_rule_learning_profiles_customer", "rule_learning_profiles", ["customer"])
        op.create_index("ix_rule_learning_profiles_lifecycle_stage", "rule_learning_profiles", ["lifecycle_stage"])

    # 2. rule_learning_state_history
    if "rule_learning_state_history" not in existing_tables:
        op.create_table(
            "rule_learning_state_history",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("profile_id", sa.String(36), sa.ForeignKey("rule_learning_profiles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("previous_stage", sa.String(32), nullable=False),
            sa.Column("new_stage", sa.String(32), nullable=False),
            sa.Column("transition_reason", sa.Text(), nullable=False, server_default=""),
            sa.Column("triggered_by_user_id", sa.String(36), nullable=True),
            sa.Column("metrics_snapshot", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_rule_learning_state_history_profile_id", "rule_learning_state_history", ["profile_id"])

    # 3. analyst_verdict_reviews
    if "analyst_verdict_reviews" not in existing_tables:
        op.create_table(
            "analyst_verdict_reviews",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("incident_id", sa.String(36), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
            sa.Column("investigation_id", sa.String(36), sa.ForeignKey("investigations.id", ondelete="SET NULL"), nullable=True),
            sa.Column("rule_id", sa.String(128), nullable=False),
            sa.Column("customer", sa.String(128), nullable=False, server_default="DEFAULT"),
            sa.Column("reviewer_id", sa.String(128), nullable=False, server_default="analyst"),
            sa.Column("analyst_verdict", sa.String(32), nullable=False),
            sa.Column("analyst_notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("correction_reason", sa.String(64), nullable=True),
            sa.Column("evidence_references", sa.JSON(), nullable=False),
            sa.Column("blind_mode_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("revealed_ai_verdict", sa.String(32), nullable=True),
            sa.Column("comparison_outcome", sa.String(64), nullable=True),
            sa.Column("ground_truth_status", sa.String(32), nullable=False, server_default="VERIFIED"),
            sa.Column("review_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_analyst_verdict_reviews_incident_id", "analyst_verdict_reviews", ["incident_id"])
        op.create_index("ix_analyst_verdict_reviews_investigation_id", "analyst_verdict_reviews", ["investigation_id"])
        op.create_index("ix_analyst_verdict_reviews_rule_id", "analyst_verdict_reviews", ["rule_id"])
        op.create_index("ix_analyst_verdict_reviews_customer", "analyst_verdict_reviews", ["customer"])
        op.create_index("ix_analyst_verdict_reviews_reviewer_id", "analyst_verdict_reviews", ["reviewer_id"])
        op.create_index("ix_analyst_verdict_reviews_analyst_verdict", "analyst_verdict_reviews", ["analyst_verdict"])
        op.create_index("ix_analyst_verdict_reviews_ground_truth_status", "analyst_verdict_reviews", ["ground_truth_status"])

    # 4. analyst_review_adjudications
    if "analyst_review_adjudications" not in existing_tables:
        op.create_table(
            "analyst_review_adjudications",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("review_id", sa.String(36), sa.ForeignKey("analyst_verdict_reviews.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("incident_id", sa.String(64), nullable=False),
            sa.Column("adjudicator_user_id", sa.String(128), nullable=False),
            sa.Column("final_verdict", sa.String(32), nullable=False),
            sa.Column("adjudication_rationale", sa.Text(), nullable=False),
            sa.Column("original_dispute_reason", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_analyst_review_adjudications_review_id", "analyst_review_adjudications", ["review_id"])
        op.create_index("ix_analyst_review_adjudications_incident_id", "analyst_review_adjudications", ["incident_id"])

    # 5. rule_promotion_requests
    if "rule_promotion_requests" not in existing_tables:
        op.create_table(
            "rule_promotion_requests",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("profile_id", sa.String(36), sa.ForeignKey("rule_learning_profiles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("rule_id", sa.String(128), nullable=False),
            sa.Column("customer", sa.String(128), nullable=False, server_default="DEFAULT"),
            sa.Column("requested_stage", sa.String(32), nullable=False),
            sa.Column("current_stage", sa.String(32), nullable=False),
            sa.Column("requester_user_id", sa.String(128), nullable=False, server_default="system"),
            sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
            sa.Column("evaluation_run_id", sa.String(36), nullable=True),
            sa.Column("supporting_metrics", sa.JSON(), nullable=False),
            sa.Column("justification", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_rule_promotion_requests_profile_id", "rule_promotion_requests", ["profile_id"])
        op.create_index("ix_rule_promotion_requests_rule_id", "rule_promotion_requests", ["rule_id"])
        op.create_index("ix_rule_promotion_requests_customer", "rule_promotion_requests", ["customer"])
        op.create_index("ix_rule_promotion_requests_status", "rule_promotion_requests", ["status"])

    # 6. rule_promotion_approvals
    if "rule_promotion_approvals" not in existing_tables:
        op.create_table(
            "rule_promotion_approvals",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("request_id", sa.String(36), sa.ForeignKey("rule_promotion_requests.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("approver_user_id", sa.String(128), nullable=False),
            sa.Column("action", sa.String(32), nullable=False),
            sa.Column("decision_notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("approval_signature", sa.String(128), nullable=False, server_default=""),
            sa.Column("approved_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_rule_promotion_approvals_request_id", "rule_promotion_approvals", ["request_id"])

    # 7. production_automation_policies
    if "production_automation_policies" not in existing_tables:
        op.create_table(
            "production_automation_policies",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("profile_id", sa.String(36), sa.ForeignKey("rule_learning_profiles.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("rule_id", sa.String(128), nullable=False),
            sa.Column("customer", sa.String(128), nullable=False, server_default="DEFAULT"),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("allowed_verdicts", sa.JSON(), nullable=False),
            sa.Column("min_trust_score", sa.Integer(), nullable=False, server_default="8"),
            sa.Column("min_fp_precision", sa.Float(), nullable=False, server_default="0.98"),
            sa.Column("daily_closure_limit", sa.Integer(), nullable=False, server_default="50"),
            sa.Column("current_day_closure_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("emergency_disable", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_production_automation_policies_profile_id", "production_automation_policies", ["profile_id"])
        op.create_index("ix_production_automation_policies_rule_id", "production_automation_policies", ["rule_id"])
        op.create_index("ix_production_automation_policies_customer", "production_automation_policies", ["customer"])
        op.create_index("ix_production_automation_policies_is_enabled", "production_automation_policies", ["is_enabled"])
        op.create_index("ix_production_automation_policies_emergency_disable", "production_automation_policies", ["emergency_disable"])

    # 8. incident_automation_audits
    if "incident_automation_audits" not in existing_tables:
        op.create_table(
            "incident_automation_audits",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("incident_id", sa.String(64), nullable=False),
            sa.Column("rule_id", sa.String(128), nullable=False),
            sa.Column("customer", sa.String(128), nullable=False, server_default="DEFAULT"),
            sa.Column("action_type", sa.String(64), nullable=False),
            sa.Column("siem_target", sa.String(64), nullable=False, server_default="FortiSIEM"),
            sa.Column("siem_response_code", sa.Integer(), nullable=True),
            sa.Column("siem_transaction_id", sa.String(128), nullable=True),
            sa.Column("execution_status", sa.String(32), nullable=False, server_default="SUCCESS"),
            sa.Column("safety_checks_passed", sa.JSON(), nullable=False),
            sa.Column("closure_summary", sa.Text(), nullable=False, server_default=""),
            sa.Column("executed_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_incident_automation_audits_incident_id", "incident_automation_audits", ["incident_id"])
        op.create_index("ix_incident_automation_audits_rule_id", "incident_automation_audits", ["rule_id"])
        op.create_index("ix_incident_automation_audits_customer", "incident_automation_audits", ["customer"])
        op.create_index("ix_incident_automation_audits_action_type", "incident_automation_audits", ["action_type"])
        op.create_index("ix_incident_automation_audits_execution_status", "incident_automation_audits", ["execution_status"])

    # Idempotent dynamic seed: Provision learning profile and automation policy for each existing detection rule
    if "rules" in existing_tables:
        rules_table = sa.table(
            "rules",
            sa.column("id", sa.String),
            sa.column("rule_id", sa.String),
            sa.column("name", sa.String),
            sa.column("event_type", sa.String),
        )
        rlp_table = sa.table(
            "rule_learning_profiles",
            sa.column("id", sa.String),
            sa.column("rule_id", sa.String),
            sa.column("rule_identifier", sa.String),
            sa.column("customer", sa.String),
            sa.column("primary_archetype", sa.String),
            sa.column("lifecycle_stage", sa.String),
            sa.column("active_model_identifier", sa.String),
            sa.column("total_incidents_processed", sa.Integer),
            sa.column("total_analyst_reviews", sa.Integer),
            sa.column("verified_tp_count", sa.Integer),
            sa.column("verified_fp_count", sa.Integer),
            sa.column("ai_correct_count", sa.Integer),
            sa.column("ai_incorrect_count", sa.Integer),
            sa.column("abstention_count", sa.Integer),
            sa.column("validation_failure_count", sa.Integer),
            sa.column("error_distribution", sa.JSON),
            sa.column("created_at", sa.DateTime),
            sa.column("updated_at", sa.DateTime),
        )
        pap_table = sa.table(
            "production_automation_policies",
            sa.column("id", sa.String),
            sa.column("profile_id", sa.String),
            sa.column("rule_id", sa.String),
            sa.column("customer", sa.String),
            sa.column("is_enabled", sa.Boolean),
            sa.column("allowed_verdicts", sa.JSON),
            sa.column("min_trust_score", sa.Integer),
            sa.column("min_fp_precision", sa.Float),
            sa.column("daily_closure_limit", sa.Integer),
            sa.column("current_day_closure_count", sa.Integer),
            sa.column("emergency_disable", sa.Boolean),
            sa.column("created_at", sa.DateTime),
            sa.column("updated_at", sa.DateTime),
        )

        now = datetime.now(timezone.utc)
        rules_rows = conn.execute(sa.select(rules_table.c.id, rules_table.c.rule_id, rules_table.c.event_type)).fetchall()

        for r_row in rules_rows:
            r_id = str(r_row[0])
            r_ident = str(r_row[1] or r_row[2] or r_id)

            check = conn.execute(
                sa.select(rlp_table.c.id).where(
                    sa.and_(
                        rlp_table.c.rule_id == r_id,
                        rlp_table.c.customer == "DEFAULT"
                    )
                )
            ).fetchone()

            if not check:
                prof_id = str(uuid.uuid4())
                conn.execute(
                    rlp_table.insert().values(
                        id=prof_id,
                        rule_id=r_id,
                        rule_identifier=r_ident,
                        customer="DEFAULT",
                        primary_archetype="UNKNOWN",
                        lifecycle_stage="LEARNING",
                        active_model_identifier="Qwen/Qwen2.5-7B-Instruct-AWQ",
                        total_incidents_processed=0,
                        total_analyst_reviews=0,
                        verified_tp_count=0,
                        verified_fp_count=0,
                        ai_correct_count=0,
                        ai_incorrect_count=0,
                        abstention_count=0,
                        validation_failure_count=0,
                        error_distribution={},
                        created_at=now,
                        updated_at=now,
                    )
                )
                conn.execute(
                    pap_table.insert().values(
                        id=str(uuid.uuid4()),
                        profile_id=prof_id,
                        rule_id=r_ident,
                        customer="DEFAULT",
                        is_enabled=False,
                        allowed_verdicts=["FALSE_POSITIVE"],
                        min_trust_score=8,
                        min_fp_precision=0.98,
                        daily_closure_limit=50,
                        current_day_closure_count=0,
                        emergency_disable=False,
                        created_at=now,
                        updated_at=now,
                    )
                )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    for tbl in [
        "incident_automation_audits",
        "production_automation_policies",
        "rule_promotion_approvals",
        "rule_promotion_requests",
        "analyst_review_adjudications",
        "analyst_verdict_reviews",
        "rule_learning_state_history",
        "rule_learning_profiles",
    ]:
        if tbl in existing_tables:
            op.drop_table(tbl)
