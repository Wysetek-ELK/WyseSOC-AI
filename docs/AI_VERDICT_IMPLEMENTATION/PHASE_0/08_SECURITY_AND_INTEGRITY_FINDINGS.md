# 08. Security and Application Integrity Findings (Tasks H & I)

## 1. Executive Summary

This report documents the security posture, authentication architecture, role-based access control (RBAC), secrets management, and application integrity findings in AI Verdict. In strict accordance with the non-destructive audit mandate, all assessments were conducted via static code analysis, AST inspection, and read-only test verification.

---

## 2. Authentication & Identity Architecture

### 2.1 Cryptographic Implementations
- **Password Storage:** Hashed with `bcrypt` (12 rounds) via Passlib ([`backend/app/core/security.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/core/security.py#L18-L35)). Verified compliant with modern cryptographic standards.
- **Session Tokens:** JSON Web Tokens (JWT) signed with HMAC-SHA256 (`HS256`).
- **Session Delivery:** Primary authentication utilizes an `HttpOnly` cookie (`ai_verdict_session`) with `SameSite="lax"`, defending against cross-site script (XSS) token exfiltration. Programmatic clients may provide an `Authorization: Bearer <token>` header.

### 2.2 RBAC Role Hierarchy
User roles are mapped in [`backend/app/models/user.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/models/user.py#L10-L16):
- **`Administrator`:** Full system authority; exclusive access to policy approval, LLM configuration, FortiSIEM credential updates, and audit logs.
- **`SOC Analyst`:** Operational authority; incident triage, dry-run simulations, feedback submission.
- **`Read-Only Viewer`:** Read-only inspection of dashboards, incidents, and metrics.

All administrative endpoints are protected by `require_admin` or `require_role(["Administrator"])` dependencies in [`backend/app/core/deps.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/core/deps.py). Role enforcement was verified across all 17 routers.

---

## 3. Critical Security Vulnerabilities

### 3.1 Hardcoded Fallback Secret Key & Plaintext Credential Persistence (`AV-014`)
1. **Fallback Signing Key:**
   - **Location:** [`backend/app/config.py#L22`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/config.py#L22)
   - **Mechanism:** `SECRET_KEY = os.getenv("SECRET_KEY", "ai-verdict-super-secure-enterprise-secret-key-phase1-2026")`.
   - **Risk:** If `SECRET_KEY` is not explicitly declared on the host, any attacker with repository access can forge arbitrary administrative JWT tokens.
2. **Cleartext Persistence in `.env`:**
   - **Location:** [`backend/app/services/fortisiem_service.py#L1338-L1350`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/fortisiem_service.py#L1338-L1350)
   - **Mechanism:** Updating credentials in the UI writes `FORTISIEM_PASSWORD` directly into `.env` on disk.
   - **Risk:** Compromise of local filesystem permissions immediately leaks plain-text SIEM credentials.

### 3.2 Outbound Public IP Probing (`AV-011`)
- **Location:** [`backend/app/services/llm_config_service.py#L88-L105`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/llm_config_service.py#L88-L105)
- **Mechanism:** Calling `get_server1_outbound_ip()` initiates HTTP GET requests to `api.ipify.org`, `ifconfig.me/ip`, and `icanhazip.com`.
- **Risk:** Violates air-gap isolation in high-security SOCs and causes request hangs when egress traffic is firewalled.

### 3.3 Ground-Truth Leakage in Blind Review (`AV-006`)
- **Location:** [`backend/app/services/incident_service.py#L188-L201,L229`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/incident_service.py#L188-L201)
- **Mechanism:** While `gt_resp` is suppressed in blind mode, `raw_payload=inc.raw_payload` is returned unredacted.
- **Risk:** Analysts inspecting the Raw JSON tab see the historical `clearedReason`, `resolution`, and closing comments.

---

## 4. Application Integrity & Code Hygiene

### 4.1 Incomplete Alembic Migrations & Runtime Lifespan Raw DDL (`AV-012`)
- **Location:** [`backend/app/main.py#L40-L54`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/main.py#L40-L54)
- **Finding:** Startup lifespan executes raw SQL `ALTER TABLE` statements outside Alembic tracking.
- **Impact:** Automated CI/CD pipelines deploying schema via `alembic upgrade head` produce an incomplete schema missing 3 tables and 4 columns.

### 4.2 Route Contract Discrepancy (`AV-015`)
- **Finding:** Rule synchronization is implemented at `POST /api/fortisiem/sync-rules` ([`fortisiem.py#L261`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/api/fortisiem.py#L261)), whereas documentation references `POST /api/rules/sync/fortisiem`.

### 4.3 Development-Only Reset Routes in Production
- **Location:** [`backend/app/api/dev.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/api/dev.py)
- **Finding:** The backend mounts `/api/dev/reset` and `/api/dev/seed-fixtures`. While protected by `require_admin`, these destructive endpoints exist in the production route table.
- **Recommendation:** Guard the mounting of `dev.py` behind an environment check (`if settings.APP_ENV == "development":`).

