# AI Verdict — Server 1 Native Deployment Guide

## 1. Operating System & Server Prerequisites

- **Target Operating System**: Ubuntu Server 22.04 / 24.04 LTS
- **Architecture**: Native bare-metal or cloud Linux instance (AWS EC2, etc.)
- **Memory**: Minimum 4 GB RAM (8 GB recommended for high ingestion volume)
- **Disk**: 50 GB+ SSD
- **Network**: Inbound ports 80 (HTTP) and 443 (HTTPS) open; Internal port 8000 (FastAPI) and 3000 (Next.js) bound to `127.0.0.1` only.

---

## 2. Automated Quick Installation

For a fully automated setup, execute the provided script on your Ubuntu server:
```bash
sudo bash deployment/scripts/install_ubuntu.sh
```

---

## 3. Manual Step-by-Step Installation

### Step 1: Install System Packages
```bash
sudo apt-get update -y
sudo apt-get install -y \
  build-essential curl wget git nginx \
  postgresql postgresql-contrib libpq-dev \
  python3 python3-pip python3-venv python3-dev ufw
```

### Step 2: Install Node.js 22 LTS
```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### Step 3: Configure PostgreSQL Database
```bash
sudo systemctl enable --now postgresql

# Create dedicated user and database
sudo -u postgres psql -c "CREATE USER aiverdict_user WITH ENCRYPTED PASSWORD 'YourSecureDbPassword';"
sudo -u postgres psql -c "CREATE DATABASE ai_verdict OWNER aiverdict_user;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ai_verdict TO aiverdict_user;"
```

### Step 4: Configure Application User & Repository
```bash
sudo useradd -r -s /bin/bash -d /opt/ai-verdict aiverdict
sudo mkdir -p /opt/ai-verdict /var/log/ai-verdict
sudo chown -R aiverdict:aiverdict /opt/ai-verdict /var/log/ai-verdict

# Clone or copy project files to /opt/ai-verdict
```

### Step 5: Backend Setup & Migrations
```bash
cd /opt/ai-verdict/backend
sudo -u aiverdict python3 -m venv venv
sudo -u aiverdict ./venv/bin/pip install --upgrade pip
sudo -u aiverdict ./venv/bin/pip install -r requirements.txt

# Configure backend environment variables
cat <<EOF | sudo -u aiverdict tee /opt/ai-verdict/backend/.env
PROJECT_NAME="AI Verdict"
VERSION="1.0.0"
SECRET_KEY="$(openssl rand -hex 32)"
DATABASE_URL="postgresql+asyncpg://aiverdict_user:YourSecureDbPassword@127.0.0.1:5432/ai_verdict"
SYNC_DATABASE_URL="postgresql+psycopg2://aiverdict_user:YourSecureDbPassword@127.0.0.1:5432/ai_verdict"
COOKIE_SECURE="true"
COOKIE_SAMESITE="lax"
EOF
chmod 600 /opt/ai-verdict/backend/.env

# Run database migrations
sudo -u aiverdict ./venv/bin/alembic upgrade head

# Seed initial Administrator account
sudo -u aiverdict ./venv/bin/python -m app.cli create-admin \
  --username "admin" \
  --email "admin@ai-verdict.internal" \
  --password "AdminPassword123!" \
  --full-name "Primary Administrator"
```

### Step 6: Frontend Build
```bash
cd /opt/ai-verdict/frontend
sudo -u aiverdict npm install
sudo -u aiverdict npm run build
```

### Step 7: Systemd Services
Copy the service units:
```bash
sudo cp /opt/ai-verdict/deployment/systemd/ai-verdict-backend.service /etc/systemd/system/
sudo cp /opt/ai-verdict/deployment/systemd/ai-verdict-frontend.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable --now ai-verdict-backend
sudo systemctl enable --now ai-verdict-frontend
```

### Step 8: Nginx Reverse Proxy & TLS Configuration
```bash
sudo cp /opt/ai-verdict/deployment/nginx/ai-verdict.conf /etc/nginx/sites-available/ai-verdict.conf
sudo ln -sf /etc/nginx/sites-available/ai-verdict.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx
```

---

## 4. Service Management & Operations

### Check Service Status
```bash
sudo systemctl status ai-verdict-backend
sudo systemctl status ai-verdict-frontend
sudo systemctl status nginx
```

### View Live Application Logs
```bash
# Backend logs
tail -f /var/log/ai-verdict/backend.log
tail -f /var/log/ai-verdict/backend-error.log

# Frontend logs
tail -f /var/log/ai-verdict/frontend.log

# Nginx access & error logs
tail -f /var/log/nginx/ai-verdict_access.log
tail -f /var/log/nginx/ai-verdict_error.log
```

### Restart Services
```bash
sudo systemctl restart ai-verdict-backend
sudo systemctl restart ai-verdict-frontend
```

---

## 5. Automated Database Backups & Recovery

### Scheduled Daily Backup (Cron)
Add to `/etc/cron.d/ai-verdict-backup`:
```cron
0 2 * * * root /bin/bash /opt/ai-verdict/deployment/scripts/backup_db.sh > /var/log/ai-verdict/backup.log 2>&1
```

### Manual Backup
```bash
sudo bash /opt/ai-verdict/deployment/scripts/backup_db.sh
```

### Database Restore Procedure
```bash
# Decompress and restore into PostgreSQL
gunzip -c /var/backups/ai-verdict/ai_verdict_backup_YYYYMMDD_HHMMSS.sql.gz | sudo -u postgres psql ai_verdict
```

