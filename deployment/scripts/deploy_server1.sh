#!/usr/bin/env bash
# ==============================================================================
# AI VERDICT — SERVER 1 PRODUCTION DEPLOYMENT ENTRYPOINT (P4-REQ-08)
# Sets up FastAPI Backend, Celery Worker, PostgreSQL, Redis, and Next.js Frontend
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Starting Server 1 Native Ubuntu LTS Deployment..."
bash "$SCRIPT_DIR/install_ubuntu.sh"

echo "Verifying service health..."
systemctl status ai-verdict-backend --no-pager
systemctl status ai-verdict-worker --no-pager
systemctl status ai-verdict-scheduler --no-pager
systemctl status ai-verdict-frontend --no-pager
systemctl status nginx --no-pager

echo "Server 1 Deployment Verified Successfully."

