#!/usr/bin/env bash
# ==============================================================================
# AI VERDICT — OLLAMA LOCAL LLM ALTERNATIVE INSTALLATION SCRIPT
# Architecture : Server 2 (Lightweight Alternative Engine)
# Target Cloud : AWS EC2 g4dn.2xlarge (NVIDIA T4 GPU) / Ubuntu
# ==============================================================================

set -euo pipefail

MODEL="${1:-qwen2.5:7b}"
SERVER_1_IP="${2:-}"

echo "===================================================================="
echo " Installing Ollama Server with Model: ${MODEL}"
echo "===================================================================="

if [ "$EUID" -ne 0 ]; then
  echo "[ERROR] Please run as root or with sudo."
  exit 1
fi

# 1. Install Ollama
echo "[1/4] Installing Ollama binary..."
curl -fsSL https://ollama.com/install.sh | sh

# 2. Configure systemd override to listen on 0.0.0.0
echo "[2/4] Configuring Ollama network binding..."
mkdir -p /etc/systemd/system/ollama.service.d/
cat <<EOF > /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_ORIGINS=*"
Environment="OLLAMA_NUM_PARALLEL=4"
EOF

systemctl daemon-reload
systemctl restart ollama
systemctl enable ollama

# 3. Pull Model
echo "[3/4] Pulling ${MODEL} model..."
ollama pull "$MODEL"

# 4. Firewall configuration
if [ -n "$SERVER_1_IP" ]; then
  echo "[4/4] Configuring UFW for Server 1 IP ($SERVER_1_IP)..."
  ufw allow 22/tcp || true
  ufw allow from "$SERVER_1_IP" to any port 11434 proto tcp comment "AI Verdict Server 1 API"
  echo "y" | ufw enable || true
fi

echo "===================================================================="
echo " Ollama Installation Complete!"
echo " OpenAI Compatible Endpoint: http://<SERVER_2_IP>:11434/v1"
echo " Test Command:"
echo "   curl http://127.0.0.1:11434/v1/models"
echo "===================================================================="

