# 09 — Dependency & Package Audit

## 1. Backend Python Dependencies (`backend/requirements.txt` — 22 Direct Packages)

| Declaration | Static Code Refs | Verification Status |
|---|---:|---|
| `fastapi>=0.110.0` | 36 | `Active` |
| `uvicorn[standard]>=0.28.0` | 8 | `Active` |
| `pydantic>=2.6.0` | 36 | `Active` |
| `email-validator>=2.0.0` | 0 | `Runtime plugin/driver dependency (Pydantic EmailStr / SQLAlchemy async / FastAPI UploadFile)` |
| `pydantic-settings>=2.2.0` | 1 | `Active` |
| `sqlalchemy>=2.0.28` | 368 | `Active` |
| `greenlet>=3.0.0` | 0 | `Runtime plugin/driver dependency (Pydantic EmailStr / SQLAlchemy async / FastAPI UploadFile)` |
| `alembic>=1.13.1` | 45 | `Active` |
| `aiosqlite>=0.20.0` | 33 | `Active` |
| `asyncpg>=0.29.0` | 8 | `Active` |
| `psycopg2-binary>=2.9.9` | 1 | `Active` |
| `bcrypt>=4.1.2` | 6 | `Active` |
| `pyjwt>=2.8.0` | 0 | `Imported as `import jwt` in `app/utils/security.py`` |
| `python-multipart>=0.0.9` | 0 | `Runtime plugin/driver dependency (Pydantic EmailStr / SQLAlchemy async / FastAPI UploadFile)` |
| `pytest>=8.0.0` | 545 | `Test & HTTP client dependency` |
| `pytest-asyncio>=0.23.5` | 32 | `Test & HTTP client dependency` |
| `httpx>=0.27.0` | 136 | `Test & HTTP client dependency` |
| `python-dateutil>=2.9.0` | 1 | `Active` |
| `psutil>=5.9.0` | 18 | `Active` |
| `celery>=5.3.0` | 1 | `Active` |
| `redis>=5.0.0` | 16 | `Active` |
| `tiktoken>=0.7.0` | 6 | `Active` |

*(Note: `pytest` and `pytest-asyncio` are declared in `requirements.txt` alongside production dependencies because there is no separate `requirements-dev.txt`. Moving test-only deps to `requirements-dev.txt` is an optional packaging improvement, not a removal.)*

## 2. Frontend Node Dependencies (`frontend/package.json` — 15 Direct Packages)

| Section | Package | Version | Static Refs | Verification Status |
|---|---|---|---:|---|
| `dependencies` | `clsx` | `^2.1.1` | 1 | Active |
| `dependencies` | `lucide-react` | `^1.69.0` | 47 | Active |
| `dependencies` | `next` | `16.4.5` | 127 | Active |
| `dependencies` | `react` | `19.3.0` | 107 | Active |
| `dependencies` | `react-dom` | `19.3.0` | 2 | Active |
| `dependencies` | `tailwind-merge` | `^3.7.0` | 1 | Active |
| `devDependencies` | `@tailwindcss/postcss` | `^4.3.3` | 2 | Active |
| `devDependencies` | `@tailwindcss/turbopack` | `^4` | 1 | POTENTIALLY UNUSED — `postcss.config.mjs` uses `@tailwindcss/postcss` only; verify with `next build` |
| `devDependencies` | `@types/node` | `^20` | 1 | Active |
| `devDependencies` | `@types/react` | `^19` | 2 | Active |
| `devDependencies` | `@types/react-dom` | `^19` | 1 | Active |
| `devDependencies` | `eslint` | `^9` | 10 | Active |
| `devDependencies` | `eslint-config-next` | `16.4.5` | 5 | Active |
| `devDependencies` | `tailwindcss` | `^4` | 5 | Active |
| `devDependencies` | `typescript` | `^5` | 3 | Active |
