#!/usr/bin/env bash
# ==============================================================================
# AI VERDICT — SERVER 1 SAFE ROLLBACK SCRIPT
# Restores approved git SHA, preserves database/audit records, rebuilds, restarts.
# ==============================================================================
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/ai-verdict}"
TARGET_SHA="${1:-}"
APP_USER="${APP_USER:-aiverdict}"

if [ -z "$TARGET_SHA" ]; then
  echo "Usage: sudo bash rollback_server1.sh <APPROVED_COMMIT_SHA>"
  exit 1
fi

if [ "$EUID" -ne 0 ]; then
  echo "Error: Run as root or with sudo"
  exit 1
fi

echo "Rolling back $APP_DIR to approved commit SHA: $TARGET_SHA ..."
cd "$APP_DIR"
git fetch --all --tags
git checkout --force "$TARGET_SHA"

echo "Refreshing backend dependencies and checking Alembic head..."
cd "$APP_DIR/backend"
sudo -u "$APP_USER" ./venv/bin/pip install -r requirements.txt
sudo -u "$APP_USER" ./venv/bin/alembic upgrade head

echo "Rebuilding frontend..."
cd "$APP_DIR/frontend"
sudo -u "$APP_USER" npm run build

echo "Restarting services in safe order (backend -> worker -> scheduler -> frontend -> nginx)..."
systemctl restart ai-verdict-backend
systemctl restart ai-verdict-worker
systemctl restart ai-verdict-scheduler
systemctl restart ai-verdict-frontend
systemctl reload nginx

bash "$APP_DIR/deployment/scripts/verify_server1.sh"
echo "Rollback to $TARGET_SHA complete and verified."

