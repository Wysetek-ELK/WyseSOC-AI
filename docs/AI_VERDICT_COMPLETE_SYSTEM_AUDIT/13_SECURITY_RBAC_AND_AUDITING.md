# 13. Security, RBAC, and Auditing Audit

## 1. Executive Summary

This report delivers a rigorous security assessment of the AI Verdict platform. It evaluates identity and access management (IAM), role-based access control (RBAC), security audit logging, cryptographic implementations, and credential protection mechanisms across backend and frontend layers.

Several critical security vulnerabilities were discovered during code inspection, including hardcoded cryptographic secrets, cleartext credential persistence, and unauthorized external network egress.

---

## 2. Authentication and Session Management

### 2.1 Cryptographic Primitives
- **Password Hashing:** Passlib with `bcrypt` (12 rounds) in [`backend/app/core/security.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/core/security.py#L18-L35).
- **Token Format:** JSON Web Tokens (JWT) signed using HMAC-SHA256 (`HS256`).
- **Token Expiration:** Configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` (defaults to 480 minutes / 8 hours).

### 2.2 Dual-Channel Token Delivery
The authentication endpoint `POST /api/auth/login` supports both browser and programmatic API clients:
1. **HttpOnly Cookie:** Sets `access_token` cookie with `HttpOnly=True`, `SameSite="lax"`, and `Secure` (in production). Defends against Cross-Site Scripting (XSS) token theft.
2. **Bearer Token Response:** Returns `{ "access_token": "...", "token_type": "bearer" }` in the response body for programmatic API access.

---

## 3. Role-Based Access Control (RBAC) Architecture

User roles are defined in [`backend/app/models/user.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/models/user.py#L10-L16):

| Role Name | Authority Scope | Typical Personas |
| :--- | :--- | :--- |
| **`ADMINISTRATOR`** | Full System Authority | SOC Manager, Lead Engineer, System Architect |
| **`SOC_ANALYST`** | Operational Triage & Testing | Tier 1/2/3 SOC Analysts, Threat Hunters |
| **`READ_ONLY_VIEWER`** | Read-Only Inspection | Security Auditors, Executive Management, Compliance Officers |

### 3.1 Endpoint Role Enforcement (`deps.py`)
Role enforcement is handled in [`backend/app/core/deps.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/core/deps.py#L65-L105) via FastAPI dependency injection:
- `get_current_user`: Validates JWT signature and loads user from database.
- `require_role(allowed_roles: List[str])`: Verifies that `current_user.role` matches the required privilege level; raises `HTTPException(403, "Insufficient permissions")` if violated.
- `require_admin`: Convenience dependency requiring `Role.ADMINISTRATOR`.

### 3.2 RBAC Enforcement Verification Table

| Protected Resource / Action | Required Role | Enforcement Location | Verified Status |
| :--- | :--- | :--- | :--- |
| **Approve Policy Prompt** | `ADMINISTRATOR` | [`prompts.py#L95`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/api/prompts.py#L95) | **Enforced** |
| **Archive / Rollback Policy** | `ADMINISTRATOR` | [`prompts.py#L140`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/api/prompts.py#L140) | **Enforced** |
| **Configure LLM Endpoint** | `ADMINISTRATOR` | [`llm_config.py#L45`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/api/llm_config.py#L45) | **Enforced** |
| **Configure FortiSIEM Auth** | `ADMINISTRATOR` | [`fortisiem.py#L50`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/api/fortisiem.py#L50) | **Enforced** |
| **View Audit Logs** | `ADMINISTRATOR` | [`audit.py#L25`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/api/audit.py#L25) | **Enforced** |
| **Execute Dry-Run Simulation** | `ADMINISTRATOR` / `SOC_ANALYST` | [`dry_run.py#L40`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/api/dry_run.py#L40) | **Enforced** |
| **Submit Feedback Override** | `ADMINISTRATOR` / `SOC_ANALYST` | [`incidents.py#L130`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/api/incidents.py#L130) | **Enforced** |
| **View Incidents / Metrics** | All Roles | [`incidents.py#L30`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/api/incidents.py#L30) | **Enforced** |

---

## 4. Audit Logging Engine

Security and administrative events are written to the `audit_logs` table via `AuditService` in [`backend/app/services/audit_service.py`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/audit_service.py#L20-L65):
- **Logged Events:** User login, user logout, policy approval, policy rollback, LLM configuration change, FortiSIEM credential update, manual incident re-triage.
- **Captured Attributes:** `timestamp`, `user_id`, `username`, `action`, `resource_type`, `resource_id`, `details` JSON, `client_ip`.
- **Immutability:** The audit log table lacks update and delete API endpoints; it is strictly append-only.

---

## 5. Critical Security Vulnerabilities

### 5.1 Hardcoded Fallback Secret Key & Plaintext Credential Persistence (`AV-014`)
1. **Hardcoded Fallback Secret Key:**
   - **Location:** [`backend/app/config.py#L22`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/config.py#L22)
   - **Code:**
     ```python
     SECRET_KEY: str = "ai-verdict-super-secure-enterprise-secret-key-phase1-2026"
     ```
   - **Finding:** If `SECRET_KEY` is not explicitly declared in the host environment, the application falls back to this hardcoded, publicly visible string. Anyone with repository access can forge administrative JWT tokens and seize full control of the platform.
2. **Cleartext Persistence in `.env`:**
   - **Location:** [`backend/app/services/fortisiem_service.py#L1338-L1350`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/fortisiem_service.py#L1338-L1350)
   - **Finding:** When an administrator updates FortiSIEM credentials via the UI, the service writes the username, cleartext password, and server IP directly into the `.env` file on disk:
     ```python
     # fortisiem_service.py lines 1342-1346
     f.write(f"FORTISIEM_PASSWORD={password}\n")
     ```

### 5.2 Outbound Public IP Probing (`AV-011`)
- **Location:** [`backend/app/services/llm_config_service.py#L89-L92`](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/backend/app/services/llm_config_service.py#L89-L92)
- **Code:**
  ```python
  urls = [
      "https://api.ipify.org",
      "https://ifconfig.me/ip",
      "https://icanhazip.com"
  ]
  ```
- **Finding:** When an administrator visits the LLM Diagnostic page, the server initiates outbound HTTP requests to three commercial public IP discovery services. This violates air-gap policies, leaks internal deployment timing, and causes requests to hang in environments blocking egress traffic.

---

## 6. Input Sanitization & Attack Resistance

| Attack Vector | Defense Mechanism | Assessment |
| :--- | :--- | :--- |
| **SQL Injection** | SQLAlchemy ORM parameterized queries used across all standard routers. | **Protected**: No raw string concatenation in user query parameters. |
| **Zip Bomb / Path Traversal** | `ZipGuard` sandbox validates compression ratio (50:1), total files (2,000), uncompressed size (250MB), and strips relative path traversals (`..`). | **Protected** |
| **Prompt Injection** | Model payload allowlist strips HTML/script tags and forces inputs into typed JSON schema. | **Partially Protected**: Direct attacker control over incident telemetry fields (e.g. `cmdline`) could theoretically manipulate reasoning, but output is schema-constrained. |
| **Cross-Site Scripting (XSS)** | Next.js automatic React DOM escaping; authentication tokens held in HttpOnly cookies. | **Protected** |

