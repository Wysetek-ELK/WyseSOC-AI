import os
import shutil
import pytest
from app.scripts.backup import create_backup
from app.scripts.restore import restore_backup
from app.services.audit_service import AuditService, compute_audit_signature
from datetime import datetime


@pytest.mark.asyncio
async def test_backup_and_restore_workflow(tmp_path):
    """
    P4-REQ-09: Tests full physical backup snapshot creation, SHA-256 checksum
    manifest generation, and dry-run restore validation.
    """
    # Create a dummy sqlite db
    db_file = str(tmp_path / "test_backup.db")
    import sqlite3
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE test_table (id INT PRIMARY KEY, name TEXT);")
    conn.execute("INSERT INTO test_table VALUES (1, 'security_event_1');")
    conn.commit()
    conn.close()

    backup_dir = str(tmp_path / "backups")

    # 1. Create backup
    manifest = create_backup(db_path=db_file, output_dir=backup_dir)
    assert manifest["status"] == "COMPLETED"
    assert "database" in manifest["artifacts"]
    assert manifest["artifacts"]["database"]["sha256"] is not None

    # 2. Dry-run restore
    backup_instance_dir = os.path.join(backup_dir, manifest["backup_id"])
    restore_result = restore_backup(
        backup_dir=backup_instance_dir,
        target_db_path=str(tmp_path / "restored.db"),
        dry_run=True,
    )
    assert restore_result["status"] == "DRY_RUN_PASSED"
    assert restore_result["sha256_verified"] is True


@pytest.mark.asyncio
async def test_audit_hmac_signature_and_tamper_detection(db_session):
    """
    P4-REQ-09: Tests cryptographic HMAC-SHA256 signature generation and tamper detection.
    """
    audit = AuditService(db_session)

    # 1. Log an authenticated action with HMAC signature
    entry = await audit.log(
        action="USER_LOGIN",
        user_id="user-123",
        username="analyst_alice",
        entity_type="SYSTEM",
        details={"ip": "10.0.0.1"},
    )
    assert entry.signature is not None
    assert entry.key_id == "hmac-sha256-v1"

    # 2. Verify single record validity
    is_valid = AuditService.verify_record(entry)
    assert is_valid is True

    # 3. Verify entire audit trail integrity
    audit_report = await audit.verify_audit_integrity(limit=10)
    assert audit_report["integrity_status"] == "VALID"
    assert audit_report["tampered_count"] == 0

    # 4. Tamper with entry and verify detection
    entry.action = "UNAUTHORIZED_ADMIN_GRANT"
    is_tampered_valid = AuditService.verify_record(entry)
    assert is_tampered_valid is False

