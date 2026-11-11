#!/usr/bin/env bash
# ==============================================================================
# AI VERDICT — LOCAL LLM SERVER 2 INSTALLATION & COMPATIBILITY SCRIPT
# Architecture : Server 2 (GPU Inference Node — Native Linux, No Docker)
# Serving Stack: vLLM OpenAI-Compatible Endpoint (/v1/chat/completions)
# ==============================================================================

set -euo pipefail

SERVER_DIR="${SERVER_DIR:-/opt/llm-server}"
SERVICE_USER="${SERVICE_USER:-llmuser}"
MODEL_NAME="${MODEL_NAME:-Qwen/Qwen2.5-7B-Instruct-AWQ}"
QUANTIZATION="${QUANTIZATION:-awq}"
DTYPE="${DTYPE:-float16}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-8}"
GPU_MEM_UTIL="${GPU_MEM_UTIL:-0.90}"
VLLM_API_KEY="${VLLM_API_KEY:-}"
SERVER_1_IP="${1:-${SERVER_1_IP:-}}"

echo "===================================================================="
echo " AI Verdict Server 2 (Local LLM) Native Setup"
echo " Model=$MODEL_NAME | Quantization=$QUANTIZATION | Dtype=$DTYPE"
echo " MaxModelLen=$MAX_MODEL_LEN | MaxNumSeqs=$MAX_NUM_SEQS | Port=$PORT"
echo "===================================================================="

if [ "$EUID" -ne 0 ]; then
  echo "[ERROR] Please run as root or with sudo: sudo bash install_llm_server.sh <SERVER_1_PRIVATE_IP>"
  exit 1
fi

echo "[1/8] Installing system prerequisites..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y build-essential curl wget git jq ufw logrotate python3 python3-pip python3-venv python3-dev

echo "[2/8] Checking NVIDIA GPU driver, VRAM, and compute capability..."
if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
  GPU_INFO="$(nvidia-smi --query-gpu=name,driver_version,memory.total,compute_cap --format=csv,noheader | head -n 1)"
  echo "[INFO] Detected GPU: $GPU_INFO"
  VRAM_MIB="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -n 1 | tr -d ' ')"
  if [ -n "$VRAM_MIB" ] && [ "$VRAM_MIB" -lt 14000 ]; then
    echo "[WARNING] Detected GPU VRAM=${VRAM_MIB} MiB (< 14000 MiB). Verify '${MODEL_NAME}' fits before starting."
  fi
else
  echo "[NOTICE] nvidia-smi not active; installing headless NVIDIA driver package..."
  apt-get install -y "linux-headers-$(uname -r)" || true
  apt-get install -y nvidia-driver-535-server nvidia-utils-535-server || \
    apt-get install -y nvidia-driver-535 nvidia-utils-535 || true
  echo "[WARNING] Reboot required before GPU inference can start if driver was just installed."
fi

echo "[3/8] Creating dedicated user and directories..."
if ! id "$SERVICE_USER" &>/dev/null; then
  useradd -r -s /bin/bash -d "$SERVER_DIR" "$SERVICE_USER"
fi
mkdir -p "$SERVER_DIR" "$SERVER_DIR/hf_cache" /var/log/llm-server
chown -R "$SERVICE_USER:$SERVICE_USER" "$SERVER_DIR" /var/log/llm-server

echo "[4/8] Creating/updating Python venv & installing vLLM..."
VENV_DIR="$SERVER_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
  chown -R "$SERVICE_USER:$SERVICE_USER" "$VENV_DIR"
fi
sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel
sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install "vllm>=0.6.0" "huggingface_hub[cli]" "torch"

echo "[5/8] Pre-caching model weights for '${MODEL_NAME}'..."
sudo -u "$SERVICE_USER" HF_HOME="$SERVER_DIR/hf_cache" "$VENV_DIR/bin/huggingface-cli" download \
  "$MODEL_NAME" --cache-dir "$SERVER_DIR/hf_cache" || {
    echo "[WARNING] Model pre-download skipped or failed; vLLM will download on first start."
}

echo "[6/8] Writing /etc/systemd/system/vllm-server.service..."
QUANT_ARG=""
if [ -n "$QUANTIZATION" ] && [ "$QUANTIZATION" != "none" ]; then
  QUANT_ARG="--quantization ${QUANTIZATION}"
fi
KEY_ARG=""
if [ -n "$VLLM_API_KEY" ]; then
  KEY_ARG="--api-key ${VLLM_API_KEY}"
fi

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
Environment="PYTHONUNBUFFERED=1"
ExecStart=${VENV_DIR}/bin/vllm serve ${MODEL_NAME} \\
    --host ${HOST} \\
    --port ${PORT} \\
    --max-model-len ${MAX_MODEL_LEN} \\
    --max-num-seqs ${MAX_NUM_SEQS} \\
    --gpu-memory-utilization ${GPU_MEM_UTIL} \\
    --dtype ${DTYPE} \\
    ${QUANT_ARG} \\
    ${KEY_ARG} \\
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

echo "[7/8] Configuring logrotate and firewall..."
cat <<EOF > /etc/logrotate.d/vllm-server
/var/log/llm-server/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
EOF

ufw allow 22/tcp comment "SSH Management" > /dev/null || true
if [ -n "$SERVER_1_IP" ]; then
  ufw allow from "$SERVER_1_IP" to any port "$PORT" proto tcp comment "AI Verdict Server 1 API"
fi
echo "y" | ufw enable > /dev/null 2>&1 || true

echo "[8/8] Enabling systemd service..."
systemctl daemon-reload
systemctl enable vllm-server.service
if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
  systemctl restart vllm-server.service
fi
echo "Server 2 setup complete. Validate with: python3 smoke_test_server2.py --base-url http://127.0.0.1:${PORT}/v1 --model ${MODEL_NAME}"
