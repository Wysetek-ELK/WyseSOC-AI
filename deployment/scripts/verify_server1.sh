#!/usr/bin/env bash
# ==============================================================================
# AI VERDICT — SERVER 1 POST-INSTALL & READINESS VERIFICATION SCRIPT
# ==============================================================================
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/ai-verdict}"
BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:3000}"

echo "Verifying Server 1 AI Verdict stack..."

echo "[1/6] Checking systemd units..."
for svc in postgresql redis-server ai-verdict-backend ai-verdict-worker ai-verdict-frontend nginx; do
  if systemctl is-active --quiet "$svc"; then
    echo "  OK: $svc active"
  else
    echo "  FAIL: $svc not active"
    exit 1
  fi
done

echo "[2/6] Checking Alembic schema head..."
cd "$APP_DIR/backend"
./venv/bin/alembic current

echo "[3/6] Checking Redis ping..."
redis-cli ping

echo "[4/6] Checking Nginx configuration..."
nginx -t

echo "[5/6] Checking Backend /api/health..."
curl -fsS "${BACKEND_URL}/api/health" | python3 -m json.tool

echo "[6/6] Checking Frontend reachability..."
curl -fsSI "${FRONTEND_URL}/login" | head -n 5

echo "Server 1 verification passed."

