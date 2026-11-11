#!/usr/bin/env bash
# ==============================================================================
# AI VERDICT — UBUNTU SERVER LTS IDEMPOTENT NATIVE INSTALLATION SCRIPT
# Architecture: Server 1 (Application Server — Native Linux, No Docker)
# Target OS: Ubuntu 22.04 / 24.04 LTS
# ==============================================================================

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/ai-verdict}"
APP_USER="${APP_USER:-aiverdict}"
DB_NAME="${DB_NAME:-ai_verdict}"
DB_USER="${DB_USER:-aiverdict_user}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
LOCAL_LLM_BASE_URL="${LOCAL_LLM_BASE_URL:-http://REPLACE_WITH_SERVER2_PRIVATE_HOST:8000/v1}"
LOCAL_LLM_MODEL_NAME="${LOCAL_LLM_MODEL_NAME:-Qwen/Qwen2.5-7B-Instruct-AWQ}"
INITIAL_ADMIN_USER="${INITIAL_ADMIN_USER:-admin}"
INITIAL_ADMIN_EMAIL="${INITIAL_ADMIN_EMAIL:-admin@example.com}"
INITIAL_ADMIN_PASSWORD="${INITIAL_ADMIN_PASSWORD:-}"

echo "=========================================================="
echo " Verdictum AI Server 1 Native Installation (Idempotent)"
echo " APP_DIR=$APP_DIR | APP_USER=$APP_USER"
echo "=========================================================="

if [ "$EUID" -ne 0 ]; then
  echo "Error: Please run as root or with sudo"
  exit 1
fi

echo "[1/9] Installing system dependencies (PostgreSQL, Redis, Nginx, Python, Build Tools)..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y \
  build-essential \
  curl \
  wget \
  git \
  nginx \
  postgresql \
  postgresql-contrib \
  redis-server \
  libpq-dev \
  python3 \
  python3-pip \
  python3-venv \
  python3-dev \
  logrotate \
  ufw

echo "[2/9] Checking Node.js 22 LTS..."
if ! command -v node &> /dev/null; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
fi
echo "Node version: $(node --version) | NPM version: $(npm --version)"

echo "[3/9] Ensuring service user '$APP_USER' and log directories..."
if ! id "$APP_USER" &>/dev/null; then
  useradd -r -s /bin/bash -d "$APP_DIR" "$APP_USER"
fi
mkdir -p "$APP_DIR" /var/log/ai-verdict
chown -R "$APP_USER:$APP_USER" /var/log/ai-verdict

echo "[4/9] Ensuring PostgreSQL & Redis services are running..."
systemctl enable --now postgresql
systemctl enable --now redis-server

ENV_FILE="$APP_DIR/backend/.env"
if [ -f "$ENV_FILE" ]; then
  echo "[INFO] Existing $ENV_FILE found — preserving secrets and credentials (idempotent mode)."
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
else
  gen_db_pass="${DB_PASS:-$(openssl rand -hex 16)}"
  gen_jwt_tok="${APP_JWT_SIGNER:-$(openssl rand -hex 32)}"
  gen_audit_hmac="${AUDIT_SIGNING_KEY:-$(openssl rand -hex 32)}"

  sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER';" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$gen_db_pass';"
  sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME';" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
  sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

  cp "$APP_DIR/deployment/env.production.example" "$ENV_FILE"
  sed -i \
    -e "s|REPLACE_WITH_OPENSSL_RAND_HEX_32_MINIMUM_32_CHARACTERS|${gen_jwt_tok}|g" \
    -e "s|REPLACE_WITH_OPENSSL_RAND_HEX_32_FOR_HMAC_AUDIT_SIGNATURES|${gen_audit_hmac}|g" \
    -e "s|aiverdict_user:REPLACE_WITH_DB_PASSWORD@127.0.0.1:5432/ai_verdict|${DB_USER}:${gen_db_pass}@127.0.0.1:5432/${DB_NAME}|g" \
    -e "s|http://REPLACE_WITH_SERVER2_PRIVATE_HOST:8000/v1|${LOCAL_LLM_BASE_URL}|g" \
    -e "s|Qwen/Qwen2.5-7B-Instruct-AWQ|${LOCAL_LLM_MODEL_NAME}|g" \
    "$ENV_FILE"
  chown "$APP_USER:$APP_USER" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
fi

echo "[5/9] Installing Backend Python Virtual Environment..."
cd "$APP_DIR/backend"
if [ ! -d "$APP_DIR/backend/venv" ]; then
  sudo -u "$APP_USER" python3 -m venv venv
fi
sudo -u "$APP_USER" ./venv/bin/pip install --upgrade pip setuptools wheel
sudo -u "$APP_USER" ./venv/bin/pip install -r requirements.txt

echo "[6/9] Running Alembic Migrations..."
sudo -u "$APP_USER" ./venv/bin/alembic upgrade head
if [ -n "$INITIAL_ADMIN_PASSWORD" ]; then
  sudo -u "$APP_USER" ./venv/bin/python -m app.cli create-admin \
    --username "$INITIAL_ADMIN_USER" \
    --email "$INITIAL_ADMIN_EMAIL" \
    --password "$INITIAL_ADMIN_PASSWORD" \
    --full-name "System Administrator" || true
else
  echo "[NOTICE] INITIAL_ADMIN_PASSWORD not supplied; skipping create-admin (run app.cli create-admin manually)."
fi

echo "[7/9] Building Frontend Next.js Application..."
cd "$APP_DIR/frontend"
if [ ! -f "$APP_DIR/frontend/.env.production" ]; then
  cat <<EOF > "$APP_DIR/frontend/.env.production"
NEXT_PUBLIC_APP_NAME="Verdictum AI"
EOF
  chown "$APP_USER:$APP_USER" "$APP_DIR/frontend/.env.production"
fi
sudo -u "$APP_USER" npm ci --no-audit --no-fund || sudo -u "$APP_USER" npm install
sudo -u "$APP_USER" npm run build

echo "[8/9] Installing systemd units, logrotate, and Nginx..."
cp "$APP_DIR/deployment/systemd/ai-verdict-backend.service" /etc/systemd/system/
cp "$APP_DIR/deployment/systemd/ai-verdict-worker.service" /etc/systemd/system/
cp "$APP_DIR/deployment/systemd/ai-verdict-frontend.service" /etc/systemd/system/
if [ -f "$APP_DIR/deployment/systemd/ai-verdict-scheduler.service" ]; then
  cp "$APP_DIR/deployment/systemd/ai-verdict-scheduler.service" /etc/systemd/system/
fi
if [ -f "$APP_DIR/deployment/logrotate/ai-verdict" ]; then
  cp "$APP_DIR/deployment/logrotate/ai-verdict" /etc/logrotate.d/ai-verdict
fi

systemctl daemon-reload
systemctl enable ai-verdict-backend ai-verdict-worker ai-verdict-scheduler ai-verdict-frontend
systemctl restart ai-verdict-backend
systemctl restart ai-verdict-worker
systemctl restart ai-verdict-scheduler
systemctl restart ai-verdict-frontend

cp "$APP_DIR/deployment/nginx/ai-verdict.conf" /etc/nginx/sites-available/ai-verdict.conf
ln -sf /etc/nginx/sites-available/ai-verdict.conf /etc/nginx/sites-enabled/ai-verdict.conf
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

echo "[9/9] Configuring conservative firewall (SSH + HTTP/HTTPS only)..."
ufw allow 22/tcp comment "SSH" > /dev/null || true
ufw allow 80/tcp comment "HTTP Redirect" > /dev/null || true
ufw allow 443/tcp comment "HTTPS Reverse Proxy" > /dev/null || true
echo "y" | ufw enable > /dev/null 2>&1 || true

echo "=========================================================="
echo " Verdictum AI Server 1 Native Setup Complete"
echo " Run: bash $APP_DIR/deployment/scripts/verify_server1.sh"
echo "=========================================================="
