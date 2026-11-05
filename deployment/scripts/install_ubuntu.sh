#!/usr/bin/env bash
# ==============================================================================
# AI VERDICT — UBUNTU SERVER LTS AUTOMATED INSTALLATION SCRIPT
# Architecture: Server 1 (Application Server)
# Target OS: Ubuntu 22.04 / 24.04 LTS
# ==============================================================================

set -euo pipefail

echo "=========================================================="
echo " Starting AI Verdict Server 1 Native Installation"
echo "=========================================================="

# Check root privileges
if [ "$EUID" -ne 0 ]; then
  echo "Error: Please run as root or with sudo"
  exit 1
fi

APP_DIR="/opt/ai-verdict"
APP_USER="aiverdict"
DB_NAME="ai_verdict"
DB_USER="aiverdict_user"
DB_PASS=$(openssl rand -hex 16)
SECRET_KEY=$(openssl rand -hex 32)

echo "[1/8] Updating apt packages and installing system tools..."
apt-get update -y
apt-get install -y \
  build-essential \
  curl \
  wget \
  git \
  nginx \
  postgresql \
  postgresql-contrib \
  libpq-dev \
  python3 \
  python3-pip \
  python3-venv \
  python3-dev \
  ufw

echo "[2/8] Installing Node.js 22 LTS..."
if ! command -v node &> /dev/null; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
fi
echo "Node version: $(node --version)"
echo "NPM version: $(npm --version)"

echo "[3/8] Creating service user '$APP_USER'..."
if ! id "$APP_USER" &>/dev/null; then
  useradd -r -s /bin/bash -d "$APP_DIR" "$APP_USER"
fi

mkdir -p "$APP_DIR"
mkdir -p /var/log/ai-verdict
chown -R "$APP_USER:$APP_USER" /var/log/ai-verdict

echo "[4/8] Configuring PostgreSQL Database '$DB_NAME'..."
systemctl start postgresql
systemctl enable postgresql

sudo -u postgres psql -c "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER';" | grep -q 1 || \
sudo -u postgres psql -c "CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASS';"

sudo -u postgres psql -c "SELECT 1 FROM pg_database WHERE datname='$DB_NAME';" | grep -q 1 || \
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

echo "[5/8] Setting up Backend Python Virtual Environment..."
cd "$APP_DIR/backend"
sudo -u "$APP_USER" python3 -m venv venv
sudo -u "$APP_USER" ./venv/bin/pip install --upgrade pip setuptools wheel
sudo -u "$APP_USER" ./venv/bin/pip install -r requirements.txt

# Create .env for backend
cat <<EOF > "$APP_DIR/backend/.env"
PROJECT_NAME="AI Verdict"
VERSION="1.0.0"
SECRET_KEY="$SECRET_KEY"
DATABASE_URL="postgresql+asyncpg://$DB_USER:$DB_PASS@127.0.0.1:5432/$DB_NAME"
SYNC_DATABASE_URL="postgresql+psycopg2://$DB_USER:$DB_PASS@127.0.0.1:5432/$DB_NAME"
COOKIE_SECURE="true"
COOKIE_SAMESITE="lax"
EOF
chown "$APP_USER:$APP_USER" "$APP_DIR/backend/.env"
chmod 600 "$APP_DIR/backend/.env"

echo "[6/8] Running Database Migrations & Initial Setup..."
sudo -u "$APP_USER" ./venv/bin/alembic upgrade head
sudo -u "$APP_USER" ./venv/bin/python -m app.cli create-admin \
  --username "admin" \
  --email "admin@ai-verdict.internal" \
  --password "AdminPassword123!" \
  --full-name "System Administrator"

echo "[7/8] Building Frontend Next.js Application..."
cd "$APP_DIR/frontend"
cat <<EOF > "$APP_DIR/frontend/.env.production"
NEXT_PUBLIC_APP_NAME="AI Verdict"
EOF
sudo -u "$APP_USER" npm install
sudo -u "$APP_USER" npm run build

echo "[8/8] Installing systemd services and Nginx configuration..."
cp "$APP_DIR/deployment/systemd/ai-verdict-backend.service" /etc/systemd/system/
cp "$APP_DIR/deployment/systemd/ai-verdict-frontend.service" /etc/systemd/system/

systemctl daemon-reload
systemctl enable ai-verdict-backend
systemctl enable ai-verdict-frontend
systemctl restart ai-verdict-backend
systemctl restart ai-verdict-frontend

# Nginx config
cp "$APP_DIR/deployment/nginx/ai-verdict.conf" /etc/nginx/sites-available/ai-verdict.conf
ln -sf /etc/nginx/sites-available/ai-verdict.conf /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

echo "=========================================================="
echo " AI Verdict Installation Complete!"
echo " Backend Status: $(systemctl is-active ai-verdict-backend)"
echo " Frontend Status: $(systemctl is-active ai-verdict-frontend)"
echo " Database User: $DB_USER"
echo " Initial Admin: admin / AdminPassword123!"
echo "=========================================================="
