"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-05 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(64), unique=True, index=True, nullable=False),
        sa.Column("email", sa.String(128), unique=True, index=True, nullable=False),
        sa.Column("hashed_password", sa.String(256), nullable=False),
        sa.Column("full_name", sa.String(128), default=""),
        sa.Column("role", sa.String(32), default="SOC Analyst", nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # Rules
    op.create_table(
        "rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("rule_id", sa.String(128), unique=True, index=True, nullable=False),
        sa.Column("name", sa.String(256), index=True, nullable=False),
        sa.Column("event_type", sa.String(128), index=True, nullable=False),
        sa.Column("description", sa.Text(), default=""),
        sa.Column("severity", sa.String(32), default="MEDIUM", index=True),
        sa.Column("status", sa.String(32), default="ACTIVE", index=True),
        sa.Column("data_source", sa.String(256), default=""),
        sa.Column("detection_tech", sa.String(128), default=""),
        sa.Column("evaluation_mode", sa.String(64), default=""),
        sa.Column("pattern_logic", sa.Text(), default=""),
        sa.Column("remediation", sa.Text(), default=""),
        sa.Column("raw_rule_text", sa.Text(), default=""),
        sa.Column("parsed_metadata", sa.JSON(), default=dict),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # Import Jobs
    op.create_table(
        "import_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("filename", sa.String(256), nullable=False),
        sa.Column("file_type", sa.String(32), default="JSON"),
        sa.Column("file_size", sa.Integer(), default=0),
        sa.Column("total_files", sa.Integer(), default=0),
        sa.Column("imported_count", sa.Integer(), default=0),
        sa.Column("duplicate_count", sa.Integer(), default=0),
        sa.Column("error_count", sa.Integer(), default=0),
        sa.Column("status", sa.String(32), default="PENDING", index=True),
        sa.Column("error_details", sa.JSON(), default=list),
        sa.Column("created_by", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )

    # Incidents
    op.create_table(
        "incidents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("incident_id", sa.String(64), unique=True, index=True, nullable=False),
        sa.Column("rule_id", sa.String(36), sa.ForeignKey("rules.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("import_job_id", sa.String(36), sa.ForeignKey("import_jobs.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("event_type", sa.String(128), index=True, nullable=False),
        sa.Column("title", sa.String(512), default="", index=True),
        sa.Column("description", sa.Text(), default=""),
        sa.Column("detail", sa.Text(), default=""),
        sa.Column("severity", sa.String(32), default="MEDIUM", index=True),
        sa.Column("event_severity", sa.String(32), default=""),
        sa.Column("status_code", sa.Integer(), default=1, index=True),
        sa.Column("status_name", sa.String(64), default="Open"),
        sa.Column("category", sa.String(128), default=""),
        sa.Column("subcategory", sa.String(128), default=""),
        sa.Column("source_ip", sa.String(64), default="", index=True),
        sa.Column("reporting_device", sa.String(128), default=""),
        sa.Column("reporting_ip", sa.String(64), default=""),
        sa.Column("customer", sa.String(128), default=""),
        sa.Column("ticket_id", sa.String(64), default=""),
        sa.Column("first_seen_epoch", sa.BigInteger(), nullable=True, index=True),
        sa.Column("last_seen_epoch", sa.BigInteger(), nullable=True),
        sa.Column("created_at_epoch", sa.BigInteger(), nullable=True, index=True),
        sa.Column("updated_at_epoch", sa.BigInteger(), nullable=True),
        sa.Column("raw_payload", sa.JSON(), default=dict),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # Incident Events
    op.create_table(
        "incident_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("incident_id", sa.String(36), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("event_id", sa.String(128), default="", index=True),
        sa.Column("event_receive_time", sa.BigInteger(), nullable=True),
        sa.Column("event_type", sa.String(128), default=""),
        sa.Column("raw_log", sa.Text(), default=""),
        sa.Column("attributes", sa.JSON(), default=dict),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # Historical Ground Truth (Separated Security Table)
    op.create_table(
        "historical_ground_truth",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("incident_id", sa.String(36), sa.ForeignKey("incidents.id", ondelete="CASCADE"), unique=True, nullable=False, index=True),
        sa.Column("resolution", sa.String(64), default="", index=True),
        sa.Column("cleared_reason", sa.Text(), default=""),
        sa.Column("comments", sa.Text(), default=""),
        sa.Column("cleared_user", sa.String(128), default=""),
        sa.Column("cleared_time_epoch", sa.BigInteger(), nullable=True),
        sa.Column("resolved_at_epoch", sa.BigInteger(), nullable=True),
        sa.Column("is_ml_generated", sa.Boolean(), default=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # Audit Logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=True, index=True),
        sa.Column("username", sa.String(64), nullable=True),
        sa.Column("action", sa.String(64), index=True, nullable=False),
        sa.Column("resource_type", sa.String(64), index=True, default=""),
        sa.Column("resource_id", sa.String(128), nullable=True),
        sa.Column("details", sa.JSON(), default=dict),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("historical_ground_truth")
    op.drop_table("incident_events")
    op.drop_table("incidents")
    op.drop_table("import_jobs")
    op.drop_table("rules")
    op.drop_table("users")

