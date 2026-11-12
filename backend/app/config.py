import logging
import os
from typing import List, Optional, Set
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_FILE = os.path.join(BASE_DIR, "ai_verdict.db").replace("\\", "/")
ENV_FILE = os.path.join(BASE_DIR, ".env")

KNOWN_INSECURE_SECRETS: Set[str] = {
    "ai-verdict-super-secure-enterprise-secret-key-phase1-2026",
    "secret",
    "secretkey",
    "changeme",
    "password",
    "admin",
    "12345678",
    "default",
    "",
}

SUPPORTED_OPERATING_MODES: Set[str] = {
    "development",
    "integration",
    "shadow",
    "advisory",
    "autonomous",
}
PRODUCTION_SAFE_MODES: Set[str] = {"shadow", "advisory", "autonomous"}
VALIDATED_CONTEXT_BUDGET_TIERS: List[int] = [4096, 8192, 16384]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "Verdictum AI"
    PROJECT_NAME: str = "Verdictum AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    PLATFORM_OPERATING_MODE: str = os.getenv("PLATFORM_OPERATING_MODE", "")

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # Session / Cookie settings
    COOKIE_NAME: str = "ai_verdict_session"
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    COOKIE_SAMESITE: str = "lax"

    # Database URLs
    # Supports PostgreSQL in production and SQLite for local development/testing
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{DEFAULT_DB_FILE}"
    )
    SYNC_DATABASE_URL: str = os.getenv(
        "SYNC_DATABASE_URL",
        f"sqlite:///{DEFAULT_DB_FILE}"
    )

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # Ingestion & Upload Guards
    UPLOAD_MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50 MB
    ZIP_MAX_UNCOMPRESSED_SIZE: int = 250 * 1024 * 1024  # 250 MB
    ZIP_MAX_FILE_COUNT: int = 2000
    ZIP_MAX_RATIO: float = 50.0  # Max compression ratio to prevent zip bombs

    # FortiSIEM Integration Settings
    FORTISIEM_HOST: str = os.getenv("FORTISIEM_HOST", "")
    FORTISIEM_USERNAME: str = os.getenv("FORTISIEM_USERNAME", "")
    FORTISIEM_PASSWORD: str = os.getenv("FORTISIEM_PASSWORD", "")
    FORTISIEM_VERIFY_SSL: bool = os.getenv("FORTISIEM_VERIFY_SSL", "false").lower() == "true"
    FORTISIEM_TIMEOUT: float = float(os.getenv("FORTISIEM_TIMEOUT", "25.0"))
    FORTISIEM_MOCK_FALLBACK: bool = os.getenv("FORTISIEM_MOCK_FALLBACK", "false").lower() == "true"
    FORTISIEM_AUTO_POLL_ENABLED: bool = os.getenv("FORTISIEM_AUTO_POLL_ENABLED", "false").lower() == "true"
    FORTISIEM_POLL_INTERVAL_SECONDS: int = int(os.getenv("FORTISIEM_POLL_INTERVAL_SECONDS", "180"))
    FORTISIEM_AUTO_AI_VERDICT: bool = os.getenv("FORTISIEM_AUTO_AI_VERDICT", "true").lower() == "true"

    # Local LLM Server 2 Integration (vLLM / OpenAI-Compatible)
    LOCAL_LLM_BASE_URL: str = os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:8000/v1")
    LOCAL_LLM_MODEL_NAME: str = os.getenv("LOCAL_LLM_MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct-AWQ")
    LOCAL_LLM_API_KEY: str = os.getenv("LOCAL_LLM_API_KEY", "EMPTY")
    LOCAL_LLM_TIMEOUT: float = float(os.getenv("LOCAL_LLM_TIMEOUT", "60.0"))
    LOCAL_LLM_CONTEXT_BUDGET: int = int(os.getenv("LOCAL_LLM_CONTEXT_BUDGET", "16384"))
    LOCAL_LLM_MAX_TOKENS: int = int(os.getenv("LOCAL_LLM_MAX_TOKENS", "1024"))
    LOCAL_LLM_TARGET_INPUT_BUDGET: int = int(os.getenv("LOCAL_LLM_TARGET_INPUT_BUDGET", "8192"))
    LOCAL_LLM_VERIFIED_MAX_MODEL_LEN: Optional[int] = None
    LOCAL_LLM_ALLOW_MOCK_FALLBACK: bool = False
    LOCAL_LLM_PROVENANCE: str = os.getenv("LOCAL_LLM_PROVENANCE", "AUTO")
    TEST_ENVIRONMENT_ID: str = os.getenv("AI_VERDICT_TEST_ENV", "")

    # Server 1 Networking
    SERVER1_HOST: str = os.getenv("SERVER1_HOST", "")
    SERVER1_OUTBOUND_IP: str = os.getenv("SERVER1_OUTBOUND_IP", "")

    # Phase 4: Database Connection Pooling & Migration Hardening
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "20"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_TIMEOUT: float = float(os.getenv("DB_POOL_TIMEOUT", "30.0"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))
    AUTO_MIGRATE_ON_STARTUP: bool = os.getenv("AUTO_MIGRATE_ON_STARTUP", "false").lower() == "true"

    # Phase 4: Distributed Task Queue (Celery / Redis)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    USE_ASYNC_CELERY: bool = os.getenv("USE_ASYNC_CELERY", "false").lower() == "true"
    CELERY_TASK_TIMEOUT_SECONDS: int = int(os.getenv("CELERY_TASK_TIMEOUT_SECONDS", "300"))

    # Phase 4: Workload Scalability & GPU Management
    LLM_MAX_CONCURRENT_REQUESTS: int = int(os.getenv("LLM_MAX_CONCURRENT_REQUESTS", "4"))
    LLM_CIRCUIT_BREAKER_FAIL_THRESHOLD: int = int(os.getenv("LLM_CIRCUIT_BREAKER_FAIL_THRESHOLD", "5"))
    LLM_CIRCUIT_BREAKER_RECOVERY_TIME: float = float(os.getenv("LLM_CIRCUIT_BREAKER_RECOVERY_TIME", "30.0"))
    QUEUE_BACKPRESSURE_LIMIT: int = int(os.getenv("QUEUE_BACKPRESSURE_LIMIT", "1000"))

    # Phase 4: Cryptographic Audit Trail Signing
    AUDIT_SIGNING_KEY: str = os.getenv("AUDIT_SIGNING_KEY", "")

    @property
    def resolved_operating_mode(self) -> str:
        raw = (self.PLATFORM_OPERATING_MODE or "").strip().lower()
        if raw:
            return raw
        is_prod = self.APP_ENV.lower() in ("production", "prod")
        return "advisory" if is_prod else "development"

    def model_post_init(self, __context) -> None:
        is_prod = self.APP_ENV.lower() in ("production", "prod")
        if is_prod and (self.LOCAL_LLM_ALLOW_MOCK_FALLBACK or self.FORTISIEM_MOCK_FALLBACK):
            logging.getLogger("ai_verdict.config").critical(
                "SECURITY OVERRIDE (AIS-F12): Forcing LOCAL_LLM_ALLOW_MOCK_FALLBACK=False and FORTISIEM_MOCK_FALLBACK=False in production."
            )
            self.LOCAL_LLM_ALLOW_MOCK_FALLBACK = False
            self.FORTISIEM_MOCK_FALLBACK = False
        self.validate_security()

    def validate_security(self) -> None:
        """Validates production security, operating mode, and context budget configuration."""
        is_prod = self.APP_ENV.lower() in ("production", "prod")
        raw_mode = (self.PLATFORM_OPERATING_MODE or "").strip().lower()
        if raw_mode and raw_mode not in SUPPORTED_OPERATING_MODES:
            raise RuntimeError(
                f"Invalid PLATFORM_OPERATING_MODE '{raw_mode}'. "
                f"Expected one of: {sorted(SUPPORTED_OPERATING_MODES)}."
            )

        if is_prod:
            if not self.SECRET_KEY or self.SECRET_KEY in KNOWN_INSECURE_SECRETS:
                raise RuntimeError(
                    "Critical Security Blocker (AV-014): Insecure or missing SECRET_KEY in production. "
                    "Please set a cryptographically strong SECRET_KEY (minimum 32 characters) via environment variable."
                )
            if len(self.SECRET_KEY) < 32:
                raise RuntimeError(
                    "Critical Security Blocker (AV-014): SECRET_KEY is too short for production (minimum 32 characters required)."
                )
            if raw_mode == "development":
                raise RuntimeError(
                    "Critical Security Blocker (AIS-F12): PLATFORM_OPERATING_MODE='development' is forbidden when APP_ENV='production'."
                )
        else:
            # In development or testing, assign a safe dedicated development secret if unconfigured
            if not self.SECRET_KEY or self.SECRET_KEY in KNOWN_INSECURE_SECRETS:
                self.SECRET_KEY = "dev-insecure-test-key-32-chars-minimum-ok-for-local"

        if self.LOCAL_LLM_CONTEXT_BUDGET < 1024 or self.LOCAL_LLM_CONTEXT_BUDGET > 131072:
            raise RuntimeError(
                f"Invalid LOCAL_LLM_CONTEXT_BUDGET={self.LOCAL_LLM_CONTEXT_BUDGET}. Expected 1024..131072."
            )
        if self.LOCAL_LLM_MAX_TOKENS < 64 or self.LOCAL_LLM_MAX_TOKENS > 16384:
            raise RuntimeError(
                f"Invalid LOCAL_LLM_MAX_TOKENS={self.LOCAL_LLM_MAX_TOKENS}. Expected 64..16384."
            )
        if (self.LOCAL_LLM_CONTEXT_BUDGET - self.LOCAL_LLM_MAX_TOKENS) < 512:
            raise RuntimeError(
                "Invalid LLM token budget: (LOCAL_LLM_CONTEXT_BUDGET - LOCAL_LLM_MAX_TOKENS) must leave at least 512 prompt tokens."
            )


settings = Settings()
