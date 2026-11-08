# Report 12: Security Hardening, Network Boundaries & Secrets Compliance

## 1. Compliance Architecture & Attack Surface Minimization

Production readiness requires eliminating common attack vectors, credential exposures, and unauthenticated network paths:
1. **Zero Secret Exposure in Repositories:** All API keys, database credentials, and cryptographic salts are injected strictly via Linux environment variables or `/opt/ai-verdict/backend/.env` with `0600` permissions.
2. **Strict Secrets Validation (AV-014):** In production mode (`APP_ENV=production`), `Settings.validate_security()` enforces minimum 32-character high-entropy values for `SECRET_KEY` and `AUDIT_SIGNING_KEY`.
3. **No External Public-IP Leakage:** Disables all calls to public STUN or external IP discovery endpoints (`api.ipify.org`, etc.). All IP references are strictly local or internal enterprise subnets.
4. **Development Route Exclusion (REQ-08):** In production mode, development routes (`app/api/dev.py`) are strictly unmounted and inaccessible.

---

## 2. Network Segmentation & Firewall Isolation

```
                                  INTERNET / INGRESS
                                          |
                              (Port 443 HTTPS / TLS 1.3)
                                          v
+---------------------------------------------------------------------------------------------------+
|                     SERVER 1: PUBLIC / INGRESS ZONE (Nginx Ingress)                               |
|   UFW Policy:                                                                                     |
|   - Allow 22/tcp (SSH from Jumpbox / Bastion)                                                     |
|   - Allow 80/tcp (HTTP -> Redirects 301 to 443)                                                   |
|   - Allow 443/tcp (HTTPS TLS 1.3)                                                                 |
|   - DENY ALL other inbound ports                                                                  |
|                                                                                                   |
|   Internal Bindings:                                                                              |
|   - FastAPI Uvicorn : 127.0.0.1:8000 (Loopback only)                                              |
|   - PostgreSQL      : 127.0.0.1:5432 (Loopback only)                                              |
|   - Redis Broker    : 127.0.0.1:6379 (Loopback only)                                              |
|   - Next.js UI      : 127.0.0.1:3000 (Loopback only)                                              |
+---------------------------------------------------------------------------------------------------+
                                          |
                                          | Internal Private Network Only (e.g. 10.10.20.0/24)
                                          v
+---------------------------------------------------------------------------------------------------+
|                     SERVER 2: ISOLATED GPU ZONE (vLLM Inference)                                  |
|   UFW Policy:                                                                                     |
|   - Allow 22/tcp (SSH from Bastion)                                                               |
|   - Allow from 10.10.20.4 to any port 8000 proto tcp (Server 1 API traffic ONLY)                   |
|   - DENY ALL other inbound traffic                                                                |
+---------------------------------------------------------------------------------------------------+
```

---

## 3. Reverse Proxy & HTTP Security Headers

In `deployment/nginx/ai-verdict.conf`, modern security headers are enforced globally:

```nginx
# Security Headers
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self';" always;
```

---

## 4. RepoDeploy Governor Compliance Checklist

AI Verdict strictly adheres to the RepoDeploy Governor deployment rules:
- [x] Zero direct unverified `git push` commands.
- [x] Zero destructive Git operations (force-push, branch deletion blocked).
- [x] Mandatory two-stage release gate (GitHub update approval + remote deployment approval).
- [x] Real public/private IP masking in committed documentation.
- [x] Server deployment configs maintained strictly outside the repository in protected paths.
- [x] Native systemd Linux deployment (no Docker required).
- [x] Automated post-deployment health check with immediate rollback capability.

