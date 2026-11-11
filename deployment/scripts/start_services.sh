#!/usr/bin/env bash
# ==============================================================================
# AI VERDICT — START SERVICES (SYSTEMD & NGINX)
# ==============================================================================

set -euo pipefail

echo "Starting AI Verdict Services..."
sudo systemctl start postgresql
sudo systemctl start redis-server
sudo systemctl start ai-verdict-backend
sudo systemctl start ai-verdict-worker
sudo systemctl start ai-verdict-scheduler
sudo systemctl start ai-verdict-frontend
sudo systemctl restart nginx

echo "Services status:"
sudo systemctl status ai-verdict-backend --no-pager -n 3
sudo systemctl status ai-verdict-worker --no-pager -n 3
sudo systemctl status ai-verdict-scheduler --no-pager -n 3
sudo systemctl status ai-verdict-frontend --no-pager -n 3

