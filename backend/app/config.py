import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_FILE = os.path.join(BASE_DIR, "ai_verdict.db").replace("\\", "/")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
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


settings = Settings()
