#!/usr/bin/env bash
# ==============================================================================
# AI VERDICT — LOCAL LLM SERVER AUTOMATED INSTALLATION & CONFIGURATION SCRIPT
# Architecture : Server 2 (GPU Inference Node)
# Target Cloud : AWS EC2 g4dn.2xlarge (1x NVIDIA T4 GPU, 16GB VRAM, 8 vCPUs, 32GB RAM)
# Target OS    : Ubuntu 22.04 LTS / Ubuntu 24.04 LTS
# Serving Stack: vLLM (OpenAI-Compatible Engine) + Qwen2.5-7B-Instruct-AWQ
# ==============================================================================

set -euo pipefail

# --- Configuration Defaults ---
SERVER_DIR="/opt/llm-server"
SERVICE_USER="llmuser"
DEFAULT_MODEL="Qwen/Qwen2.5-7B-Instruct-AWQ"
MODEL_NAME="${MODEL_NAME:-$DEFAULT_MODEL}"
PORT="8000"
MAX_MODEL_LEN="4096"
GPU_MEM_UTIL="0.90"
SERVER_1_IP="${1:-}"  # Optional: Pass Server 1 private IP as first argument for UFW

echo "===================================================================="
echo " Starting AI Verdict Local LLM Server Setup (AWS g4dn.2xlarge / T4)"
echo " Model: ${MODEL_NAME}"
echo " Port : ${PORT}"
echo "===================================================================="

# Check root privileges
if [ "$EUID" -ne 0 ]; then
  echo "[ERROR] Please run this script as root or with sudo:"
  echo "  sudo bash install_llm_server.sh [SERVER_1_PRIVATE_IP]"
  exit 1
fi

# Detect OS
if [ -f /etc/os-release ]; then
  . /etc/os-release
  echo "[INFO] Detected OS: $NAME $VERSION_ID"
  if [[ "$ID" != "ubuntu" && "$ID_LIKE" != *"ubuntu"* && "$ID_LIKE" != *"debian"* ]]; then
    echo "[WARNING] This script is optimized for Ubuntu LTS. Proceeding anyway..."
  fi
fi

# ------------------------------------------------------------------------------
# 1. System Package Updates & Prereqs
# ------------------------------------------------------------------------------
echo ""
echo "[1/7] Updating system packages and installing prerequisites..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y \
  build-essential \
  curl \
  wget \
  git \
  jq \
  ufw \
  python3 \
  python3-pip \
  python3-venv \
  python3-dev

# ------------------------------------------------------------------------------
# 2. NVIDIA Driver & CUDA Setup
# ------------------------------------------------------------------------------
echo ""
echo "[2/7] Checking NVIDIA GPU drivers and CUDA support..."
if ! command -v nvidia-smi &> /dev/null; then
  echo "[INFO] nvidia-smi not detected. Installing recommended headless NVIDIA drivers..."
  apt-get install -y linux-headers-$(uname -r)
  
  # Install standard datacenter/server driver for AWS G4dn (Turing T4)
  apt-get install -y nvidia-driver-535-server nvidia-utils-535-server || \
  apt-get install -y nvidia-driver-535 nvidia-utils-535

  echo "[NOTICE] NVIDIA drivers installed. Note that if this is a fresh instance,"
  echo "         a system reboot may be required before the driver activates."
else
  echo "[INFO] NVIDIA driver already active:"
  nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader || true
fi

# ------------------------------------------------------------------------------
# 3. Create Dedicated Service User & Directories
# ------------------------------------------------------------------------------
echo ""
echo "[3/7] Setting up dedicated service user and directories..."
if ! id "$SERVICE_USER" &>/dev/null; then
  useradd -r -s /bin/bash -d "$SERVER_DIR" "$SERVICE_USER"
  echo "[INFO] Created system user '$SERVICE_USER'"
fi

mkdir -p "$SERVER_DIR"
mkdir -p "$SERVER_DIR/hf_cache"
mkdir -p /var/log/llm-server

chown -R "$SERVICE_USER:$SERVICE_USER" "$SERVER_DIR"
chown -R "$SERVICE_USER:$SERVICE_USER" /var/log/llm-server

# ------------------------------------------------------------------------------
# 4. Python Virtual Environment & vLLM Installation
# ------------------------------------------------------------------------------
echo ""
echo "[4/7] Installing vLLM inference engine in virtual environment..."
VENV_DIR="$SERVER_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

# Upgrade pip and install vLLM
sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel
sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install \
  "vllm>=0.6.0" \
  "huggingface_hub[cli]" \
  "torch"

echo "[INFO] vLLM installation complete:"
sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" show vllm | grep -E "Name|Version" || true

# ------------------------------------------------------------------------------
# 5. Pre-Cache / Download Model Weights
# ------------------------------------------------------------------------------
echo ""
echo "[5/7] Pre-caching model weights for '${MODEL_NAME}'..."
echo "      (AWQ 4-bit weights are ~5.5GB; downloads directly to cache)..."

sudo -u "$SERVICE_USER" HF_HOME="$SERVER_DIR/hf_cache" "$VENV_DIR/bin/huggingface-cli" download \
  "$MODEL_NAME" \
  --cache-dir "$SERVER_DIR/hf_cache" || {
    echo "[WARNING] Could not pre-download model with huggingface-cli. vLLM will download at startup."
}

# ------------------------------------------------------------------------------
# 6. Create & Enable Systemd Service
# ------------------------------------------------------------------------------
echo ""
echo "[6/7] Creating systemd service unit '/etc/systemd/system/vllm-server.service'..."

cat <<EOF > /etc/systemd/system/vllm-server.service
[Unit]
Description=vLLM OpenAI-Compatible Inference Server (AI Verdict Server 2)
After=network.target nvidia-persistenced.service
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${SERVER_DIR}
Environment="HF_HOME=${SERVER_DIR}/hf_cache"
Environment="CUDA_VISIBLE_DEVICES=0"
Environment="NCCL_DEBUG=INFO"
Environment="PYTHONUNBUFFERED=1"
ExecStart=${VENV_DIR}/bin/vllm serve ${MODEL_NAME} \\
    --host 0.0.0.0 \\
    --port ${PORT} \\
    --max-model-len ${MAX_MODEL_LEN} \\
    --gpu-memory-utilization ${GPU_MEM_UTIL} \\
    --dtype float16 \\
    --trust-remote-code \\
    --disable-log-requests

Restart=always
RestartSec=10
LimitNOFILE=65535
TimeoutStartSec=600

StandardOutput=append:/var/log/llm-server/vllm.log
StandardError=append:/var/log/llm-server/vllm_error.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable vllm-server.service

if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
  echo "[INFO] Starting vllm-server.service..."
  systemctl restart vllm-server.service
else
  echo "[WARNING] GPU driver not active yet. Please reboot the server: 'sudo reboot'"
  echo "          vLLM will start automatically on boot once the driver is initialized."
fi

# ------------------------------------------------------------------------------
# 7. Network Firewall (UFW) Hardening
# ------------------------------------------------------------------------------
echo ""
echo "[7/7] Configuring network firewall rules..."
# Allow SSH
ufw allow 22/tcp comment "SSH Management" > /dev/null || true

if [ -n "$SERVER_1_IP" ]; then
  echo "[INFO] Whitelisting Server 1 IP ($SERVER_1_IP) for Port ${PORT}..."
  ufw allow from "$SERVER_1_IP" to any port "$PORT" proto tcp comment "AI Verdict Server 1 API"
  echo "[INFO] Firewall rule added: Only $SERVER_1_IP can connect to port $PORT."
else
  echo "[NOTICE] No Server 1 IP passed as argument."
  echo "         Remember to restrict Port ${PORT} in your AWS Security Group to Server 1's Private IP!"
fi

# Enable UFW if not already active
echo "y" | ufw enable > /dev/null 2>&1 || true

# ------------------------------------------------------------------------------
# Verification & Summary
# ------------------------------------------------------------------------------
echo ""
echo "===================================================================="
echo " Installation Complete!"
echo "===================================================================="
echo " Service Name   : vllm-server.service"
echo " Model          : ${MODEL_NAME}"
echo " Port           : ${PORT} (OpenAI Compatible: /v1/chat/completions)"
echo " Log Files      : /var/log/llm-server/vllm.log"
echo ""
echo " Management Commands:"
echo "   sudo systemctl status vllm-server"
echo "   sudo journalctl -u vllm-server -f"
echo "   tail -f /var/log/llm-server/vllm.log"
echo ""
echo " Verification Test (Run once service is active):"
echo "   curl http://127.0.0.1:${PORT}/v1/models"
echo ""
echo " Sample Inference Test:"
echo "   curl -X POST http://127.0.0.1:${PORT}/v1/chat/completions \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"model\": \"${MODEL_NAME}\", \"messages\": [{\"role\": \"user\", \"content\": \"Ping. Respond with Pong.\"}]}'"
echo "===================================================================="

