#!/usr/bin/env bash
# ==============================================================================
# AI VERDICT — POSTGRESQL AUTOMATED BACKUP SCRIPT
# ==============================================================================

set -euo pipefail

BACKUP_DIR="/var/backups/ai-verdict"
DB_NAME="ai_verdict"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_backup_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

echo "Creating PostgreSQL backup for '$DB_NAME'..."
sudo -u postgres pg_dump "$DB_NAME" | gzip > "$BACKUP_FILE"

chmod 600 "$BACKUP_FILE"
echo "Backup created successfully at: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"

# Retention: Delete backups older than 14 days
echo "Purging backups older than 14 days..."
find "$BACKUP_DIR" -type f -name "${DB_NAME}_backup_*.sql.gz" -mtime +14 -delete

echo "Backup rotation complete."
