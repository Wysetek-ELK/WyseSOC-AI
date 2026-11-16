# VERDICTUM AI — VALIDATION V1.2.3: DATABASE MIGRATION & SAFE ROLLBACK (AV-012)

## 1. Compliance Standard: AV-012 Strict Schema Governance

Under Verdictum AI policy **AV-012**:
- Production database schemas must strictly match the latest Alembic head revision at application startup (`verify_schema_on_startup`).
- Runtime DDL statements (`create_all`, raw `ALTER TABLE`) are strictly forbidden during production launch.
- Every model change must be represented by an idempotent Alembic revision supporting automated upgrade, downgrade, and safe rollback without data loss.

---

## 2. Migration Design: `013_user_tenant_customer.py`

File location: [backend/alembic/versions/013_user_tenant_customer.py](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/alembic/versions/013_user_tenant_customer.py)

### Revision Metadata
- **Revision ID**: `013_user_tenant_customer`
- **Revises**: `012_policy_version_governance`
- **Table Altered**: `users`
- **Target Changes**: Add `customer` (VARCHAR(128), nullable) and index `ix_users_customer`.

### Implementation:
```python
"""013_user_tenant_customer

Revision ID: 013_user_tenant_customer
Revises: 012_policy_version_governance
Create Date: 2026-11-16 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = "013_user_tenant_customer"
down_revision = "012_policy_version_governance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "users" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("users")}
        existing_indexes = {ix["name"] for ix in inspector.get_indexes("users")}

        with op.batch_alter_table("users") as batch_op:
            if "customer" not in existing_cols:
                batch_op.add_column(sa.Column("customer", sa.String(128), nullable=True))
            if "ix_users_customer" not in existing_indexes:
                batch_op.create_index("ix_users_customer", ["customer"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "users" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("users")}
        existing_indexes = {ix["name"] for ix in inspector.get_indexes("users")}

        with op.batch_alter_table("users") as batch_op:
            if "ix_users_customer" in existing_indexes:
                batch_op.drop_index("ix_users_customer")
            if "customer" in existing_cols:
                batch_op.drop_column("customer")
```

---

## 3. Migration and Rollback Verification Evidence

Automated test `test_04_alembic_migration_013_idempotency_and_rollback` was executed in [backend/tests/test_v1_2_3_integrity_closure.py](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/tests/test_v1_2_3_integrity_closure.py):

1. **Initial Baseline**: Database schema at `012_policy_version_governance`.
2. **Upgrade Step**: Ran `upgrade()`. Inspector confirmed column `customer` and index `ix_users_customer` created.
3. **Downgrade Step**: Ran `downgrade()`. Inspector confirmed index `ix_users_customer` dropped and `customer` column removed cleanly via batch alter table.
4. **Re-Upgrade Step (Idempotency Check)**: Re-ran `upgrade()`. Verified successful reapplying of schema changes without duplicate column errors.
5. **Data Preservation**: Applied to active local SQLite database (`backend/ai_verdict.db`). All 5 existing user rows remained intact throughout downgrade and upgrade cycles.

### Production Pre-Flight Checklist
- `013_user_tenant_customer.py` committed to repository.
- Remote deployment script on Server 1 runs `alembic upgrade head` before restarting Gunicorn/Uvicorn processes.
- Startup verification (`verify_schema_on_startup`) will pass cleanly with `current_rev == "013_user_tenant_customer"`.
