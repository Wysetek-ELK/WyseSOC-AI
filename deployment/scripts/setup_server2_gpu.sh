#!/usr/bin/env bash
# ==============================================================================
# AI VERDICT — SERVER 2 GPU PROVISIONING WRAPPER (P4-REQ-08)
# Restricts Server 2 GPU inference access strictly to Server 1 IP
# ==============================================================================
set -euo pipefail

SERVER_1_IP="${1:-}"

if [ -z "$SERVER_1_IP" ]; then
    echo "Usage: sudo bash setup_server2_gpu.sh <SERVER_1_PRIVATE_IP>"
    echo "Example: sudo bash setup_server2_gpu.sh <SERVER_1_PRIVATE_IP>"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Executing Server 2 vLLM installation restricted to Server 1 IP: $SERVER_1_IP..."
bash "$SCRIPT_DIR/install_llm_server.sh" "$SERVER_1_IP"

