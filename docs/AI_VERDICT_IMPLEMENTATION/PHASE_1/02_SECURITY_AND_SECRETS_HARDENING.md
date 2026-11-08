# AI Verdict — Phase 1: Security and Secrets Hardening

**Requirement:** REQ-01  
**Audit Finding:** AV-014 (Insecure Default Secrets & Credential Writing to Disk)  
**Status:** **VERIFIED & IMPLEMENTED**  

---

### 1. Threat Model & Vulnerability Analysis

In the pre-Phase 1 audit baseline:
1. `backend/app/config.py` permitted running the application with a hardcoded default `SECRET_KEY` (`ai-verdict-super-secure-enterprise-secret-key-phase1-2026`). In production, this allows an attacker to forge JWT authentication tokens and impersonate administrators or analysts.
2. `FortiSIEMService.update_config()` received updated SIEM credentials and dynamically updated `.env` by rewriting the file on disk. In a containerized or shared server deployment:
   - Storing credentials in cleartext on disk violates SOC 2, ISO 27001, and NIST SP 800-53 controls.
   - Any local file inclusion (LFI) or read vulnerability on Server 1 could immediately expose the supervisory SIEM password.
   - Web application workers should never have write privileges to application source or configuration directories.

---

### 2. Architecture of Implemented Solution

```mermaid
flowchart TD
    Start[Application Boot: main.py] --> LoadSettings[Load Settings from Environment]
    LoadSettings --> CheckEnv{APP_ENV == 'production'?}
    CheckEnv -- No (dev/test) --> AllowStartup[Allow Startup with Notice]
    CheckEnv -- Yes (prod) --> ValidateSec[settings.validate_security()]
    ValidateSec --> CheckLen{len(SECRET_KEY) >= 32?}
    CheckLen -- No --> RaiseFatal[Raise RuntimeError: Abort Boot]
    CheckLen -- Yes --> CheckKnown{SECRET_KEY in KNOWN_INSECURE_SECRETS?}
    CheckKnown -- Yes --> RaiseFatal
    CheckKnown -- No --> BootSuccess[Application Startup Authorized]

    SIEMUpdate[PUT /api/siem/config] --> AuthCheck[Require Administrator Role]
    AuthCheck --> UpdateMemory[Update Settings in Active Process Memory]
    UpdateMemory --> LogNotice[Log REQ-01 Compliance Notice]
    LogNotice --> NoFileWrite[Zero Writes to .env on Disk]
```

---

### 3. Source Code Modifications

#### `backend/app/config.py`
```python
KNOWN_INSECURE_SECRETS: Set[str] = {
    "ai-verdict-super-secure-enterprise-secret-key-phase1-2026",
    "supersecret",
    "secret",
    "changeme",
    "password",
    "admin",
    "default",
}

class Settings(BaseSettings):
    APP_ENV: str = "development"
    SECRET_KEY: str = "ai-verdict-super-secure-enterprise-secret-key-phase1-2026"

    def validate_security(self) -> None:
        """Validates that production environments do not use weak or known secrets."""
        is_prod = self.APP_ENV.lower() in ("production", "prod")
        if is_prod:
            if not self.SECRET_KEY or len(self.SECRET_KEY.strip()) < 32:
                raise RuntimeError(
                    "Critical Security Blocker: In production mode (APP_ENV=production), "
                    "SECRET_KEY must be a cryptographically strong secret of at least 32 characters."
                )
            if self.SECRET_KEY.strip() in KNOWN_INSECURE_SECRETS:
                raise RuntimeError(
                    "Critical Security Blocker: In production mode (APP_ENV=production), "
                    "SECRET_KEY matches a known insecure default. A unique secret key is required."
                )
```

#### `backend/app/services/fortisiem_service.py`
In `FortiSIEMService.update_config()`:
```python
# 1. Update in-memory settings
settings.FORTISIEM_HOST = clean_host
settings.FORTISIEM_USERNAME = clean_user
if password is not None and password.strip():
    settings.FORTISIEM_PASSWORD = password.strip()
...
# REQ-01 / AV-014: Plaintext credential writes to .env on disk are strictly removed.
logger.info(
    "FortiSIEM configuration updated in-memory for the active session. "
    "Plaintext .env persistence is disabled to comply with REQ-01 / AV-014 security policies."
)
return cls.get_config()
```

---

### 4. Verification & Testing

Tests implemented in `backend/tests/test_phase1_security_controls.py`:
1. `test_req01_insecure_secret_key_rejection_in_prod`:
   - Confirms that setting `APP_ENV=production` with the default known key raises `RuntimeError("Critical Security Blocker")`.
   - Confirms that keys with length < 32 characters raise `RuntimeError`.
   - Confirms that empty keys raise `RuntimeError`.
   - Confirms that valid 32+ character keys pass validation cleanly.
2. `test_req01_fortisiem_password_never_persisted_to_env`:
   - Mocks a `.env` file on disk.
   - Invokes `FortiSIEMService.update_config()` with a sensitive password string.
   - Reads `.env` on disk and asserts that `FORTISIEM_PASSWORD` and the cleartext password string are never written to disk.

