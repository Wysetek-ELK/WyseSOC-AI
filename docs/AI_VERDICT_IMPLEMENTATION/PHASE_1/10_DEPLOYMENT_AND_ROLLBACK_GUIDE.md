# AI Verdict — Phase 1: Deployment & Rollback Guide

**Milestone:** Phase 1 (Critical Safety & Security Controls)  
**Applicability:** Production & Staging Deployments  

---

### 1. Environment Configuration Requirements

Before deploying Phase 1 to a production host, verify the environment variables configured in systemd or your container orchestration environment:

```bash
# 1. Environment Mode
APP_ENV=production

# 2. Secret Key (MANDATORY: Minimum 32 cryptographically random characters)
# Generate with: openssl rand -base64 32
SECRET_KEY="c2VjdXJlLWVudGVycHJpc2Utc29jLWFpLXZlcmRpY3QtMjAyNi1wcm9kdWN0aW9u"

# 3. Model Fallback Guard (Must remain false in production)
LOCAL_LLM_ALLOW_MOCK_FALLBACK=false

# 4. Outbound IP / Host Configuration (Optional override for zero-egress resolution)
SERVER1_OUTBOUND_IP=10.0.10.15
SERVER1_HOST=soc-server1.corp.internal

# 5. FortiSIEM Connection
FORTISIEM_HOST=https://fortisiem.corp.internal
FORTISIEM_USERNAME=svc_ai_verdict
FORTISIEM_PASSWORD=<secure_vault_password>
FORTISIEM_VERIFY_SSL=true
FORTISIEM_TIMEOUT=30.0
```

> [!CAUTION]
> If `APP_ENV=production` and `SECRET_KEY` is not set or uses the audit default, the application will refuse to start and will log `Critical Security Blocker`.

---

### 2. Deployment Procedure

#### Step 1: Code Checkout
```bash
git checkout feat/phase-1-safety-controls
```

#### Step 2: Backend Dependencies & Pre-Flight Checks
```bash
cd backend
python -m pytest tests -v
```
Ensure all 84 test cases pass before starting the service.

#### Step 3: Frontend Build
```bash
cd ../frontend
npm run build
```

#### Step 4: Restart Service
```bash
sudo systemctl restart ai-verdict-backend
sudo systemctl restart ai-verdict-frontend
```

#### Step 5: Post-Deployment Smoke Check
```bash
# 1. Check health
curl -s http://127.0.0.1:8000/health

# 2. Verify dev endpoints are disabled (expect 404)
curl -s -X POST http://127.0.0.1:8000/api/dev/reset-test-data

# 3. Verify FortiSIEM sync alias
curl -s -X POST http://127.0.0.1:8000/api/rules/sync/fortisiem -H "Authorization: Bearer <ADMIN_TOKEN>"
```

---

### 3. Safe Rollback Procedure

Because Phase 1 introduces zero breaking database schema changes and makes no backward-incompatible modifications to existing incident or rule tables, rolling back is clean and instantaneous:

#### Step 1: Revert Code to Pre-Phase 1 Commit
```bash
git checkout main
```

#### Step 2: Restart Services
```bash
sudo systemctl restart ai-verdict-backend
sudo systemctl restart ai-verdict-frontend
```

#### Step 3: Verify Pre-Rollback Status
All existing database records (incidents, rules, audit logs, and learning records) remain fully accessible and uncorrupted.

