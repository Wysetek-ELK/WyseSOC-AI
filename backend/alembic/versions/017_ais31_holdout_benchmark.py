"""017_ais31_holdout_benchmark

Revision ID: 017_ais31_holdout_benchmark
Revises: 016_ground_truth_certification_and_cohort_isolation
Create Date: 2026-11-28 09:30:00.000000

Additive, non-destructive schema extensions for AIS 3.1:
- Creates `ais31_benchmark_runs` and `ais31_benchmark_results` tables for idempotent,
  checkpointed live GPU holdout evaluation with strict ground-truth isolation.
"""
import sqlalchemy as sa
from alembic import op

revision = "017_ais31_holdout_benchmark"
down_revision = "016_ground_truth_certification_and_cohort_isolation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())
    false_default = sa.text("0" if conn.dialect.name == "sqlite" else "false")
    true_default = sa.text("1" if conn.dialect.name == "sqlite" else "true")

    if "ais31_benchmark_runs" not in existing_tables:
        op.create_table(
            "ais31_benchmark_runs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("run_key", sa.String(96), nullable=False, unique=True, index=True),
            sa.Column("cohort_key", sa.String(64), nullable=False, index=True),
            sa.Column("run_type", sa.String(32), server_default="FULL_HOLDOUT_100", nullable=False),
            sa.Column("benchmark_grade", sa.String(64), server_default="PROVISIONAL_SINGLE_REVIEW_BENCHMARK", nullable=False),
            sa.Column("status", sa.String(32), server_default="CREATED", index=True, nullable=False),
            sa.Column("expected_model", sa.String(128), server_default="Qwen/Qwen3-14B-AWQ", nullable=False),
            sa.Column("actual_model_returned", sa.String(128), nullable=True),
            sa.Column("vllm_version", sa.String(64), nullable=True),
            sa.Column("context_limit", sa.Integer(), server_default=sa.text("8192"), nullable=False),
            sa.Column("max_completion_tokens", sa.Integer(), server_default=sa.text("768"), nullable=False),
            sa.Column("target_input_budget", sa.Integer(), server_default=sa.text("7424"), nullable=False),
            sa.Column("neutral_prompt_version", sa.String(64), server_default="NEUTRAL_SOC_BASELINE_V2", nullable=False),
            sa.Column("neutral_prompt_sha256", sa.String(64), server_default="", nullable=False),
            sa.Column("policy_freeze_sha256", sa.String(64), server_default="", nullable=False),
            sa.Column("manifest_sha256", sa.String(64), server_default="", nullable=False),
            sa.Column("rag_excluded", sa.Boolean(), server_default=true_default, nullable=False),
            sa.Column("memory_excluded", sa.Boolean(), server_default=true_default, nullable=False),
            sa.Column("temperature", sa.Float(), server_default=sa.text("0.0"), nullable=False),
            sa.Column("enable_thinking", sa.Boolean(), server_default=false_default, nullable=False),
            sa.Column("total_target_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("completed_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("failed_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("created_by_user", sa.String(128), server_default="system", nullable=False),
            sa.Column("config_json", sa.JSON(), nullable=True),
            sa.Column("runtime_manifest_json", sa.JSON(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )

    if "ais31_benchmark_results" not in existing_tables:
        op.create_table(
            "ais31_benchmark_results",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("run_id", sa.String(36), sa.ForeignKey("ais31_benchmark_runs.id", ondelete="CASCADE"), index=True, nullable=False),
            sa.Column("cohort_item_id", sa.String(36), nullable=True),
            sa.Column("incident_db_id", sa.String(36), index=True, nullable=True),
            sa.Column("fortisiem_incident_id", sa.String(64), index=True, nullable=False),
            sa.Column("rule_id", sa.String(128), nullable=False),
            sa.Column("rule_name", sa.String(256), server_default=""),
            sa.Column("sequence_rank", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("execution_status", sa.String(32), server_default="COMPLETED", index=True, nullable=False),
            sa.Column("eligibility_state", sa.String(32), server_default="ELIGIBLE", nullable=False),
            sa.Column("exclusion_reason", sa.Text(), nullable=True),
            sa.Column("evidence_sha256", sa.String(64), server_default=""),
            sa.Column("canonical_evidence_sha256", sa.String(64), server_default=""),
            sa.Column("rule_definition_sha256", sa.String(64), server_default=""),
            sa.Column("policy_sha256", sa.String(64), server_default=""),
            sa.Column("wire_prompt_sha256", sa.String(64), server_default=""),
            sa.Column("result_integrity_sha256", sa.String(64), server_default=""),
            sa.Column("model_identifier", sa.String(128), server_default="Qwen/Qwen3-14B-AWQ"),
            sa.Column("actual_model_returned", sa.String(128), nullable=True),
            sa.Column("inference_request_id", sa.String(128), nullable=True),
            sa.Column("request_timestamp_utc", sa.String(64), nullable=True),
            sa.Column("response_timestamp_utc", sa.String(64), nullable=True),
            sa.Column("prompt_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("completion_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("total_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("finish_reason", sa.String(32), nullable=True),
            sa.Column("latency_ms", sa.Float(), server_default=sa.text("0.0"), nullable=False),
            sa.Column("attempts", sa.Integer(), server_default=sa.text("1"), nullable=False),
            sa.Column("gpu_provenance", sa.String(64), server_default="LIVE_SERVER2_VLLM", nullable=False),
            sa.Column("error_classification", sa.String(64), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("wire_system_prompt", sa.Text(), server_default=""),
            sa.Column("wire_user_content", sa.Text(), server_default=""),
            sa.Column("wire_token_audit_json", sa.JSON(), nullable=True),
            sa.Column("raw_response_text", sa.Text(), server_default=""),
            sa.Column("raw_vllm_envelope_json", sa.JSON(), nullable=True),
            sa.Column("parsed_output_json", sa.JSON(), nullable=True),
            sa.Column("raw_llm_verdict", sa.String(32), nullable=True),
            sa.Column("raw_llm_confidence", sa.Float(), nullable=True),
            sa.Column("parsed_verdict", sa.String(32), nullable=True),
            sa.Column("validated_application_verdict", sa.String(32), server_default="REQUIRES_ATTENTION"),
            sa.Column("validator_status", sa.String(64), server_default="UNVERIFIED"),
            sa.Column("validator_action", sa.String(64), server_default="ABSTENTION_PRESERVED"),
            sa.Column("validator_rejection_reason", sa.Text(), nullable=True),
            sa.Column("validator_reason_codes_json", sa.JSON(), nullable=True),
            sa.Column("deterministic_override", sa.Boolean(), server_default=false_default, nullable=False),
            sa.Column("evidence_grounding_status", sa.String(32), server_default="UNVERIFIED"),
            sa.Column("grounding_ratio", sa.Float(), server_default=sa.text("0.0"), nullable=False),
            sa.Column("inconclusive_reason", sa.Text(), nullable=True),
            sa.Column("mode_b_policy_eligibility", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("run_id", "fortisiem_incident_id", name="uq_ais31_run_incident"),
        )


def downgrade() -> None:
    op.drop_table("ais31_benchmark_results")
    op.drop_table("ais31_benchmark_runs")
