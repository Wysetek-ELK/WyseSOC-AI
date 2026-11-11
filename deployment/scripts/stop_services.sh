#!/usr/bin/env bash
# ==============================================================================
# VERDICTUM AI — STOP SERVICES
# ==============================================================================

set -euo pipefail

echo "Stopping Verdictum AI Services..."
sudo systemctl stop ai-verdict-frontend
sudo systemctl stop ai-verdict-scheduler
sudo systemctl stop ai-verdict-worker
sudo systemctl stop ai-verdict-backend

echo "Verdictum AI services stopped successfully."

