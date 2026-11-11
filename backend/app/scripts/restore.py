"""
Production Restore & Disaster Recovery Tool (P4-REQ-09)
========================================================
Validates archive integrity and SHA-256 checksums before safely
restoring database and policy artifacts.
"""

import os
import sys
import shutil
import hashlib
import json
import argparse
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("restore")


def compute_sha256(filepath: str) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def restore_backup(
    backup_dir: str,
    target_db_path: str = "backend/ai_verdict.db",
    dry_run: bool = False,
) -> Dict[str, Any]:
    manifest_path = os.path.join(backup_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Manifest not found in backup directory: '{manifest_path}'")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    db_artifact = manifest.get("artifacts", {}).get("database", {})
    db_file = db_artifact.get("file")
    expected_hash = db_artifact.get("sha256")

    if not db_file or not expected_hash:
        raise ValueError("Invalid manifest: database artifact metadata missing.")

    backup_db_path = os.path.join(backup_dir, db_file)
    if not os.path.exists(backup_db_path):
        raise FileNotFoundError(f"Database archive missing from backup: '{backup_db_path}'")

    # Step 1: Pre-restore Checksum Verification
    actual_hash = compute_sha256(backup_db_path)
    if actual_hash != expected_hash:
        raise ValueError(
            f"Integrity check FAILED! SHA-256 mismatch for '{backup_db_path}'. "
            f"Expected {expected_hash}, got {actual_hash}. Aborting restore!"
        )

    logger.info(f"Integrity check PASSED. SHA-256 checksum verified: {actual_hash}")

    if dry_run:
        logger.info(f"DRY-RUN: Archive verified. Target '{target_db_path}' would be replaced with {backup_db_path}.")
        return {
            "status": "DRY_RUN_PASSED",
            "backup_id": manifest.get("backup_id"),
            "sha256_verified": True,
            "target": target_db_path,
        }

    # Step 2: Physical Restore
    os.makedirs(os.path.dirname(os.path.abspath(target_db_path)), exist_ok=True)
    if os.path.exists(target_db_path):
        # Create a rollback safety copy of the existing database
        rollback_copy = target_db_path + ".pre_restore_bak"
        logger.info(f"Preserving existing database to '{rollback_copy}' before overwrite.")
        shutil.copy2(target_db_path, rollback_copy)

    shutil.copy2(backup_db_path, target_db_path)
    logger.info(f"Database successfully restored to '{target_db_path}'.")

    return {
        "status": "RESTORE_SUCCESSFUL",
        "backup_id": manifest.get("backup_id"),
        "sha256_verified": True,
        "target": target_db_path,
    }


def main():
    parser = argparse.ArgumentParser(description="Verdictum AI Production Restore Tool")
    parser.add_argument("--backup-dir", required=True, help="Path to backup directory containing manifest.json")
    parser.add_argument("--target-db", default="backend/ai_verdict.db", help="Target path to restore database")
    parser.add_argument("--dry-run", action="store_true", help="Validate checksums without overwriting database")
    args = parser.parse_args()

    result = restore_backup(backup_dir=args.backup_dir, target_db_path=args.target_db, dry_run=args.dry_run)
    print(f"\nRestore operation finished: {result['status']}")


if __name__ == "__main__":
    main()

