import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_FILE = os.path.join(BASE_DIR, "ai_verdict.db").replace("\\", "/")
ENV_FILE = os.path.join(BASE_DIR, ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "AI Verdict"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "ai-verdict-super-secure-enterprise-secret-key-phase1-2026")
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
    FORTISIEM_MOCK_FALLBACK: bool = os.getenv("FORTISIEM_MOCK_FALLBACK", "true").lower() == "true"
    FORTISIEM_AUTO_POLL_ENABLED: bool = os.getenv("FORTISIEM_AUTO_POLL_ENABLED", "true").lower() == "true"
    FORTISIEM_POLL_INTERVAL_SECONDS: int = int(os.getenv("FORTISIEM_POLL_INTERVAL_SECONDS", "180"))
    FORTISIEM_AUTO_AI_VERDICT: bool = os.getenv("FORTISIEM_AUTO_AI_VERDICT", "true").lower() == "true"

    # Local LLM Server 2 Integration (vLLM / OpenAI-Compatible)
    LOCAL_LLM_BASE_URL: str = os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:8000/v1")
    LOCAL_LLM_MODEL_NAME: str = os.getenv("LOCAL_LLM_MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct-AWQ")
    LOCAL_LLM_API_KEY: str = os.getenv("LOCAL_LLM_API_KEY", "EMPTY")
    LOCAL_LLM_TIMEOUT: float = float(os.getenv("LOCAL_LLM_TIMEOUT", "30.0"))
    LOCAL_LLM_ALLOW_MOCK_FALLBACK: bool = os.getenv("LOCAL_LLM_ALLOW_MOCK_FALLBACK", "false").lower() == "true"


settings = Settings()
