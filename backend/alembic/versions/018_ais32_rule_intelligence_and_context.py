"""018_ais32_rule_intelligence_and_context

Revision ID: 018_ais32_rule_intelligence_and_context
Revises: 017_ais31_holdout_benchmark
Create Date: 2026-11-28 18:30:00.000000

Additive, non-destructive schema extensions for AIS 3.2:
- `ais32_rule_contracts`: versioned, hash-verified dynamic rule contracts
- `ais32_organizational_contexts`: tenant-isolated, approval-governed org context records
- `ais32_execution_records`: Mode A/B benchmark & pilot provenance, token/evidence audits, validator diagnostics
"""

import sqlalchemy as sa
from alembic import op

revision = "018_ais32_rule_intelligence_and_context"
down_revision = "017_ais31_holdout_benchmark"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())
    true_default = sa.text("1" if conn.dialect.name == "sqlite" else "true")

    if "ais32_rule_contracts" not in existing_tables:
        op.create_table(
            "ais32_rule_contracts",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("contract_id", sa.String(128), nullable=False, index=True),
            sa.Column("contract_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
            sa.Column("rule_db_id", sa.String(36), sa.ForeignKey("rules.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("fortisiem_rule_id", sa.String(128), nullable=False, index=True),
            sa.Column("rule_name", sa.String(256), server_default="", nullable=False),
            sa.Column("rule_definition_hash", sa.String(64), server_default="", nullable=False),
            sa.Column("primary_archetype", sa.String(64), nullable=False, index=True),
            sa.Column("secondary_archetype", sa.String(64), nullable=True),
            sa.Column("mapping_rationale", sa.Text(), server_default="", nullable=False),
            sa.Column("approval_state", sa.String(32), server_default="PROVISIONAL", nullable=False, index=True),
            sa.Column("is_active", sa.Boolean(), server_default=true_default, nullable=False, index=True),
            sa.Column("contract_hash", sa.String(64), nullable=False, index=True),
            sa.Column("policy_provenance", sa.String(64), server_default="RULE_INTELLIGENCE_ENGINE_V3_2", nullable=False),
            sa.Column("contract_json", sa.JSON(), nullable=False),
            sa.Column("overrides_json", sa.JSON(), nullable=False),
            sa.Column("reviewer", sa.String(128), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("created_by", sa.String(128), server_default="system", nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("rule_db_id", "contract_version", name="uq_ais32_rule_contract_ver"),
        )

    if "ais32_organizational_contexts" not in existing_tables:
        op.create_table(
            "ais32_organizational_contexts",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("customer", sa.String(128), server_default="DEFAULT", nullable=False, index=True),
            sa.Column("context_type", sa.String(64), nullable=False, index=True),
            sa.Column("context_value", sa.String(512), nullable=False),
            sa.Column("match_pattern", sa.String(512), server_default="", nullable=False),
            sa.Column("dedup_hash", sa.String(64), nullable=False, index=True),
            sa.Column("description", sa.Text(), server_default="", nullable=False),
            sa.Column("source_system", sa.String(128), server_default="MANUAL_ADMIN", nullable=False),
            sa.Column("verification_status", sa.String(32), server_default="VERIFIED", nullable=False, index=True),
            sa.Column("approval_status", sa.String(32), server_default="PENDING", nullable=False, index=True),
            sa.Column("approved_by", sa.String(128), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("valid_from", sa.DateTime(), nullable=True),
            sa.Column("valid_until", sa.DateTime(), nullable=True, index=True),
            sa.Column("record_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
            sa.Column("metadata_json", sa.JSON(), nullable=False),
            sa.Column("created_by", sa.String(128), server_default="system", nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("customer", "context_type", "dedup_hash", name="uq_ais32_org_ctx_dedup"),
        )

    if "ais32_execution_records" not in existing_tables:
        op.create_table(
            "ais32_execution_records",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("run_id", sa.String(64), nullable=False, index=True),
            sa.Column("run_key", sa.String(128), nullable=False, index=True),
            sa.Column("cohort_key", sa.String(64), nullable=False, index=True),
            sa.Column("mode", sa.String(16), nullable=False, index=True),
            sa.Column("fortisiem_incident_id", sa.String(64), nullable=False, index=True),
            sa.Column("incident_db_id", sa.String(36), nullable=True, index=True),
            sa.Column("rule_id", sa.String(128), nullable=False, index=True),
            sa.Column("archetype", sa.String(64), nullable=False, index=True),
            sa.Column("contract_id", sa.String(128), nullable=True),
            sa.Column("contract_hash", sa.String(64), nullable=True),
            sa.Column("policy_hash", sa.String(64), server_default="", nullable=False),
            sa.Column("wire_prompt_sha256", sa.String(64), server_default="", nullable=False),
            sa.Column("model_identifier", sa.String(128), server_default="Qwen/Qwen3-14B-AWQ", nullable=False),
            sa.Column("actual_model_returned", sa.String(128), nullable=True),
            sa.Column("inference_request_id", sa.String(128), nullable=True),
            sa.Column("gpu_provenance", sa.String(64), server_default="LIVE_SERVER2_VLLM", nullable=False),
            sa.Column("execution_status", sa.String(32), server_default="COMPLETED", nullable=False, index=True),
            sa.Column("attempts", sa.Integer(), server_default=sa.text("1"), nullable=False),
            sa.Column("retry_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("latency_ms", sa.Float(), server_default=sa.text("0.0"), nullable=False),
            sa.Column("prompt_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("completion_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("finish_reason", sa.String(32), nullable=True),
            sa.Column("raw_llm_verdict", sa.String(32), nullable=True),
            sa.Column("validated_verdict", sa.String(32), server_default="REQUIRES_ATTENTION", nullable=False),
            sa.Column("effective_operational_verdict", sa.String(32), server_default="REQUIRES_ATTENTION", nullable=False),
            sa.Column("validator_status", sa.String(64), server_default="UNVERIFIED", nullable=False),
            sa.Column("validator_module", sa.String(64), server_default="", nullable=False),
            sa.Column("grounding_ratio", sa.Float(), server_default=sa.text("0.0"), nullable=False),
            sa.Column("trust_score", sa.Integer(), nullable=True),
            sa.Column("semantic_dimensions_json", sa.JSON(), nullable=False),
            sa.Column("token_audit_json", sa.JSON(), nullable=False),
            sa.Column("evidence_audit_json", sa.JSON(), nullable=False),
            sa.Column("org_context_json", sa.JSON(), nullable=False),
            sa.Column("validator_detail_json", sa.JSON(), nullable=False),
            sa.Column("parsed_output_json", sa.JSON(), nullable=False),
            sa.Column("wire_system_prompt", sa.Text(), server_default="", nullable=False),
            sa.Column("wire_user_content", sa.Text(), server_default="", nullable=False),
            sa.Column("raw_response_text", sa.Text(), server_default="", nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("run_id", "mode", "fortisiem_incident_id", name="uq_ais32_exec_run_mode_inc"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())
    for tbl in ("ais32_execution_records", "ais32_organizational_contexts", "ais32_rule_contracts"):
        if tbl in existing_tables:
            op.drop_table(tbl)
