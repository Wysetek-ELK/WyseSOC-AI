#!/usr/bin/env bash
# ==============================================================================
# AI VERDICT — STOP SERVICES
# ==============================================================================

set -euo pipefail

echo "Stopping AI Verdict Services..."
sudo systemctl stop ai-verdict-frontend
sudo systemctl stop ai-verdict-backend

echo "AI Verdict services stopped successfully."
