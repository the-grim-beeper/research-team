# Research Team — Phase 1 (Foundations) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a deployable skeleton — FastAPI + Postgres (with pgvector) + Alembic + JWT auth backend; Next.js (App Router, static export) frontend; single Docker container; Railway-deployable. End state: a logged-in user can create up to three active research subjects, archive them, and see them listed. No agents, no ingestion, no cycles yet — just the cabinet the rest of the system slots into.

**Architecture:** Single-container deployment (FYSA pattern). FastAPI serves the API under `/api/v1/*` and the statically-exported Next.js frontend from `/`. SQLAlchemy 2.x async sessions, Alembic migrations, pgvector extension installed up-front (used in later phases). JWT auth with bcrypt-hashed password. Domain logic in `services/`; routes are thin adapters over services. All request/response bodies are typed Pydantic models.

**Tech Stack:**
- Backend: Python 3.11, FastAPI, SQLAlchemy 2.x (async), asyncpg, Alembic, pgvector, Pydantic v2, pydantic-settings, python-jose (JWT), passlib[bcrypt], pytest, pytest-asyncio, httpx
- Frontend: Next.js 14 (App Router, static export), Tailwind CSS, shadcn/ui, TypeScript
- Infra: Docker (multi-stage), docker-compose for local dev, Railway for prod, Postgres 16

**Roadmap (subsequent phases — written as separate plans after this one ships):**
- **Phase 2 — Domain core:** Roles, Agents, Memory schema; agent CRUD; per-agent settings panel UI
- **Phase 3 — OpenRouter execution:** On-demand single-agent runs, system-prompt + memory wiring, artifacts table, budget tracking
- **Phase 4 — Librarian ingestion:** Source registration; RSS, upload, paste, Tavily web search, arXiv, YouTube captions; corpus + bibliography
- **Phase 5 — Cycle engine:** APScheduler, overnight cron path, cycle settings actually drive runs
- **Phase 6 — Standup UI:** Briefing + agent cards + roundtable + library tab; Editor/Critic/Contrarian/Question-Generator producing artifacts

---

## File Structure (Phase 1)

```
research-team/
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 0001_initial.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app, route registration, static-frontend mount
│   │   ├── config.py                # Settings via pydantic-settings
│   │   ├── db.py                    # Async engine, session factory, Base
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   └── subject.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   └── subject.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py              # password hash, JWT issue/verify
│   │   │   ├── users.py             # bootstrap admin
│   │   │   └── subjects.py          # subject CRUD + 3-active constraint
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   └── subjects.py
│   │   └── deps.py                  # FastAPI dependencies (DB session, current_user)
│   └── tests/
│       ├── conftest.py
│       ├── test_auth.py
│       └── test_subjects.py
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.mjs              # static export
│   ├── tailwind.config.ts
│   ├── postcss.config.mjs
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                 # Subject list (auth-gated)
│   │   ├── login/page.tsx
│   │   └── globals.css
│   ├── components/
│   │   ├── auth-provider.tsx        # client-side JWT context
│   │   ├── subject-list.tsx
│   │   └── ui/                      # shadcn components added on demand
│   └── lib/
│       ├── api.ts                   # fetch wrapper with JWT
│       └── types.ts                 # mirrors backend Pydantic models
├── Dockerfile                       # multi-stage: build frontend → build backend → final
├── docker-compose.yml               # local dev: web + db
├── railway.json
├── .env.example
├── .gitignore
└── README.md
```

---

## Task 1: Repo scaffolding and `.gitignore`

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `README.md`

- [ ] **Step 1.1: Write `.gitignore`**

```
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
.pytest_cache/
.coverage
htmlcov/

# Node / Next.js
node_modules/
.next/
out/
.turbo/
*.tsbuildinfo

# Env
.env
.env.local
.env.*.local

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
*.swp
```

- [ ] **Step 1.2: Write `.env.example`**

```
# Backend
DATABASE_URL=postgresql+asyncpg://research:research@localhost:5432/research
JWT_SECRET=change-me-in-prod
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=43200
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-me

# Frontend (build-time)
NEXT_PUBLIC_API_BASE=/api/v1
```

- [ ] **Step 1.3: Write minimal `README.md`**

```markdown
# Research Team

Personal multi-agent research environment. See `docs/superpowers/specs/2026-05-10-research-team-design.md` for the full design.

## Local development

```bash
cp .env.example .env
docker-compose up --build
```

Backend: http://localhost:8000
Frontend (dev): http://localhost:3000
Frontend (prod build, served by backend): http://localhost:8000

## Phase status

- **Phase 1 (current):** Foundations — auth, subjects CRUD, deployable skeleton.
- **Phase 2+:** see `docs/superpowers/plans/`.
```

- [ ] **Step 1.4: Commit**

```bash
git add .gitignore .env.example README.md
git commit -m "chore: add gitignore, env template, readme"
```

---

## Task 2: Backend project skeleton

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 2.1: Write `backend/pyproject.toml`**

```toml
[project]
name = "research-team-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi==0.115.0",
  "uvicorn[standard]==0.30.6",
  "sqlalchemy[asyncio]==2.0.35",
  "asyncpg==0.29.0",
  "alembic==1.13.3",
  "pgvector==0.3.5",
  "pydantic==2.9.2",
  "pydantic-settings==2.5.2",
  "python-jose[cryptography]==3.3.0",
  "passlib[bcrypt]==1.7.4",
  "python-multipart==0.0.12",
]

[project.optional-dependencies]
dev = [
  "pytest==8.3.3",
  "pytest-asyncio==0.24.0",
  "httpx==0.27.2",
  "aiosqlite==0.20.0",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["app*"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 2.2: Write `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://research:research@localhost:5432/research"
    jwt_secret: str = "change-me-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 43200  # 30 days
    admin_email: str = "admin@example.com"
    admin_password: str = "change-me"


settings = Settings()
```

- [ ] **Step 2.3: Write `backend/app/__init__.py` (empty)**

```python
```

- [ ] **Step 2.4: Write `backend/app/main.py` with health route**

```python
from fastapi import FastAPI

app = FastAPI(title="Research Team", version="0.1.0")


@app.get("/api/v1/health")
async def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 2.5: Write `backend/tests/__init__.py` (empty)**

```python
```

- [ ] **Step 2.6: Write `backend/tests/conftest.py`**

```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
```

- [ ] **Step 2.7: Write the failing test `backend/tests/test_health.py`**

```python
async def test_health_returns_ok(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2.8: Install deps and run the test**

Run:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/test_health.py -v
```
Expected: `test_health_returns_ok PASSED`.

- [ ] **Step 2.9: Commit**

```bash
git add backend/
git commit -m "feat(backend): scaffold FastAPI app with health route and pytest setup"
```

---

## Task 3: Database engine, session factory, and Alembic

**Files:**
- Create: `backend/app/db.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`

- [ ] **Step 3.1: Write `backend/app/db.py`**

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.database_url, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
```

- [ ] **Step 3.2: Initialize Alembic config**

Run:
```bash
cd backend
alembic init alembic
```
This creates `alembic/` and `alembic.ini`. Verify both exist.

- [ ] **Step 3.3: Replace `backend/alembic.ini` `sqlalchemy.url` line**

Find the `sqlalchemy.url = ...` line and change it to:
```
sqlalchemy.url =
```
(intentionally blank — `env.py` will load it from settings).

- [ ] **Step 3.4: Replace `backend/alembic/env.py`**

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import settings
from app.db import Base
from app import models  # noqa: F401  registers all models

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 3.5: Create `backend/app/models/__init__.py` (empty for now)**

```python
```

- [ ] **Step 3.6: Commit**

```bash
git add backend/app/db.py backend/alembic.ini backend/alembic/ backend/app/models/__init__.py
git commit -m "feat(backend): add async SQLAlchemy engine and Alembic setup"
```

---

## Task 4: User and Subject models + initial migration

**Files:**
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/subject.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/0001_initial.py`

- [ ] **Step 4.1: Write `backend/app/models/user.py`**

```python
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

- [ ] **Step 4.2: Write `backend/app/models/subject.py`**

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    brief: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")  # 'active' | 'archived'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

- [ ] **Step 4.3: Update `backend/app/models/__init__.py` to register both**

```python
from app.models.subject import Subject  # noqa: F401
from app.models.user import User  # noqa: F401
```

- [ ] **Step 4.4: Write `backend/alembic/versions/0001_initial.py`**

```python
"""initial: users, subjects, pgvector extension

Revision ID: 0001
Revises:
Create Date: 2026-05-10
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("brief", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_subjects_user_id", "subjects", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_subjects_user_id", table_name="subjects")
    op.drop_table("subjects")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")
```

- [ ] **Step 4.5: Start Postgres locally and run migration**

Run:
```bash
docker run --rm -d --name research-pg \
  -e POSTGRES_USER=research -e POSTGRES_PASSWORD=research -e POSTGRES_DB=research \
  -p 5432:5432 pgvector/pgvector:pg16
sleep 3
cd backend
alembic upgrade head
```
Expected: `Running upgrade  -> 0001, initial: users, subjects, pgvector extension`.

- [ ] **Step 4.6: Verify schema**

Run:
```bash
docker exec research-pg psql -U research -d research -c "\dt"
docker exec research-pg psql -U research -d research -c "\dx vector"
```
Expected: tables `users` and `subjects` listed; `vector` extension installed.

- [ ] **Step 4.7: Commit**

```bash
git add backend/app/models/ backend/alembic/versions/
git commit -m "feat(backend): add User and Subject models with initial migration and pgvector"
```

---

## Task 5: Auth service — password hashing and JWT

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/auth.py`
- Create: `backend/tests/test_auth_service.py`

- [ ] **Step 5.1: Write `backend/app/services/__init__.py` (empty)**

```python
```

- [ ] **Step 5.2: Write the failing test `backend/tests/test_auth_service.py`**

```python
from datetime import timedelta

import pytest

from app.services.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password_roundtrip():
    h = hash_password("hunter2")
    assert h != "hunter2"
    assert verify_password("hunter2", h) is True
    assert verify_password("wrong", h) is False


def test_create_and_decode_jwt_roundtrip():
    token = create_access_token(subject="42", expires_delta=timedelta(minutes=5))
    payload = decode_access_token(token)
    assert payload["sub"] == "42"


def test_decode_rejects_tampered_token():
    token = create_access_token(subject="42", expires_delta=timedelta(minutes=5))
    tampered = token[:-2] + ("aa" if token[-2:] != "aa" else "bb")
    with pytest.raises(ValueError):
        decode_access_token(tampered)
```

- [ ] **Step 5.3: Run the test to confirm it fails**

Run: `cd backend && pytest tests/test_auth_service.py -v`
Expected: ImportError / module not found for `app.services.auth`.

- [ ] **Step 5.4: Write `backend/app/services/auth.py`**

```python
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e
```

- [ ] **Step 5.5: Run the tests**

Run: `cd backend && pytest tests/test_auth_service.py -v`
Expected: all three tests pass.

- [ ] **Step 5.6: Commit**

```bash
git add backend/app/services/__init__.py backend/app/services/auth.py backend/tests/test_auth_service.py
git commit -m "feat(backend): add password hashing and JWT service with tests"
```

---

## Task 6: User bootstrap service and FastAPI startup hook

**Files:**
- Create: `backend/app/services/users.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_users_service.py`

- [ ] **Step 6.1: Write the failing test `backend/tests/test_users_service.py`**

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.users import ensure_admin_user


@pytest.fixture
async def session(monkeypatch, tmp_path):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.db import Base

    db_url = f"sqlite+aiosqlite:///{tmp_path/'test.db'}"
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        yield s
    await engine.dispose()


async def test_ensure_admin_user_creates_when_missing(session: AsyncSession):
    user = await ensure_admin_user(session, email="admin@x", password="pw")
    assert user.id is not None
    assert user.email == "admin@x"
    assert user.password_hash != "pw"


async def test_ensure_admin_user_idempotent(session: AsyncSession):
    a = await ensure_admin_user(session, email="admin@x", password="pw")
    b = await ensure_admin_user(session, email="admin@x", password="pw2")
    assert a.id == b.id
    # Password is NOT updated on subsequent calls; it stays the original hash.
    assert a.password_hash == b.password_hash
```

- [ ] **Step 6.2: Run the test to confirm it fails**

Run: `cd backend && pytest tests/test_users_service.py -v`
Expected: ImportError for `app.services.users`.

- [ ] **Step 6.3: Write `backend/app/services/users.py`**

```python
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.auth import hash_password


async def ensure_admin_user(session: AsyncSession, email: str, password: str) -> User:
    """Create the admin user if not present. Idempotent — does not update password."""
    existing = await session.scalar(select(User).where(User.email == email))
    if existing is not None:
        return existing
    user = User(
        email=email,
        password_hash=hash_password(password),
        created_at=datetime.now(timezone.utc),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
```

- [ ] **Step 6.4: Run the test**

Run: `cd backend && pytest tests/test_users_service.py -v`
Expected: both tests pass.

- [ ] **Step 6.5: Modify `backend/app/main.py` to bootstrap admin on startup**

Replace the file with:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.db import SessionLocal
from app.services.users import ensure_admin_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with SessionLocal() as session:
        await ensure_admin_user(session, settings.admin_email, settings.admin_password)
    yield


app = FastAPI(title="Research Team", version="0.1.0", lifespan=lifespan)


@app.get("/api/v1/health")
async def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 6.6: Verify the existing health test still passes**

Run: `cd backend && pytest tests/test_health.py -v`
Expected: pass. (Lifespan runs against the real configured DB; if your DB isn't running, the test client won't trigger lifespan — verify with manual run below.)

- [ ] **Step 6.7: Manually verify admin bootstrap**

Run:
```bash
cd backend
ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD=changeme uvicorn app.main:app --port 8000 &
sleep 2
docker exec research-pg psql -U research -d research -c "SELECT id, email FROM users;"
kill %1
```
Expected: one row with `email = admin@example.com`.

- [ ] **Step 6.8: Commit**

```bash
git add backend/app/services/users.py backend/app/main.py backend/tests/test_users_service.py
git commit -m "feat(backend): bootstrap admin user on startup"
```

---

## Task 7: Auth schemas, login route, current-user dependency

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/deps.py`
- Create: `backend/app/routes/__init__.py`
- Create: `backend/app/routes/auth.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_auth_routes.py`

- [ ] **Step 7.1: Write `backend/app/schemas/__init__.py` (empty)**

```python
```

- [ ] **Step 7.2: Write `backend/app/schemas/auth.py`**

```python
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: int
    email: EmailStr
```

- [ ] **Step 7.3: Write `backend/app/deps.py`**

```python
from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models.user import User
from app.services.auth import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    try:
        payload = decode_access_token(token)
    except ValueError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e)) from e
    user_id_raw = payload.get("sub")
    if user_id_raw is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing subject")
    user = await session.get(User, int(user_id_raw))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user
```

- [ ] **Step 7.4: Write `backend/app/routes/__init__.py` (empty)**

```python
```

- [ ] **Step 7.5: Write `backend/app/routes/auth.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.auth import LoginRequest, MeResponse, TokenResponse
from app.services.auth import create_access_token, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    user = await session.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return TokenResponse(access_token=create_access_token(subject=str(user.id)))


@router.get("/me", response_model=MeResponse)
async def me(current: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(id=current.id, email=current.email)
```

- [ ] **Step 7.6: Modify `backend/app/main.py` to register the auth router**

Replace the file with:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.db import SessionLocal
from app.routes import auth as auth_routes
from app.services.users import ensure_admin_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with SessionLocal() as session:
        await ensure_admin_user(session, settings.admin_email, settings.admin_password)
    yield


app = FastAPI(title="Research Team", version="0.1.0", lifespan=lifespan)
app.include_router(auth_routes.router)


@app.get("/api/v1/health")
async def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 7.7: Update `backend/tests/conftest.py` to use a per-test SQLite DB and a clean app**

Replace `backend/tests/conftest.py` with:

```python
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import Base
from app.deps import get_session
from app.main import app
from app.services.users import ensure_admin_user


@pytest.fixture
async def session_factory(tmp_path):
    db_url = f"sqlite+aiosqlite:///{tmp_path/'test.db'}"
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.fixture
async def client(session_factory):
    async def override_get_session():
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = override_get_session
    # Bootstrap admin in the test DB.
    async with session_factory() as s:
        await ensure_admin_user(s, "admin@test", "pw")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
```

- [ ] **Step 7.8: Write the failing test `backend/tests/test_auth_routes.py`**

```python
async def test_login_succeeds_with_correct_credentials(client):
    r = await client.post("/api/v1/auth/login", json={"email": "admin@test", "password": "pw"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and len(body["access_token"]) > 20


async def test_login_rejects_wrong_password(client):
    r = await client.post("/api/v1/auth/login", json={"email": "admin@test", "password": "nope"})
    assert r.status_code == 401


async def test_me_returns_user_when_authenticated(client):
    login = await client.post("/api/v1/auth/login", json={"email": "admin@test", "password": "pw"})
    token = login.json()["access_token"]
    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "admin@test"


async def test_me_rejects_missing_token(client):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401
```

- [ ] **Step 7.9: Run all backend tests**

Run: `cd backend && pytest -v`
Expected: all tests pass (health, auth_service, users_service, auth_routes).

- [ ] **Step 7.10: Commit**

```bash
git add backend/app/schemas/ backend/app/deps.py backend/app/routes/ backend/app/main.py backend/tests/conftest.py backend/tests/test_auth_routes.py
git commit -m "feat(backend): add login route, /me, and JWT-based current-user dependency"
```

---

## Task 8: Subject schemas and service (with 3-active constraint)

**Files:**
- Create: `backend/app/schemas/subject.py`
- Create: `backend/app/services/subjects.py`
- Create: `backend/tests/test_subjects_service.py`

- [ ] **Step 8.1: Write `backend/app/schemas/subject.py`**

```python
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SubjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    brief: str = Field(default="", max_length=10_000)


class SubjectRead(BaseModel):
    id: int
    title: str
    brief: str
    status: Literal["active", "archived"]
    created_at: datetime
```

- [ ] **Step 8.2: Write the failing test `backend/tests/test_subjects_service.py`**

```python
import pytest

from app.services.subjects import (
    ActiveSubjectLimit,
    archive_subject,
    create_subject,
    list_subjects,
)


async def test_create_and_list_subject(session_factory):
    async with session_factory() as s:
        sub = await create_subject(s, user_id=1, title="AI governance", brief="Trends.")
        assert sub.id is not None
        assert sub.status == "active"
        rows = await list_subjects(s, user_id=1)
    assert [r.title for r in rows] == ["AI governance"]


async def test_three_active_limit(session_factory):
    async with session_factory() as s:
        for i in range(3):
            await create_subject(s, user_id=1, title=f"S{i}", brief="")
        with pytest.raises(ActiveSubjectLimit):
            await create_subject(s, user_id=1, title="S4", brief="")


async def test_archiving_frees_a_slot(session_factory):
    async with session_factory() as s:
        first = await create_subject(s, user_id=1, title="S0", brief="")
        for i in range(1, 3):
            await create_subject(s, user_id=1, title=f"S{i}", brief="")
        await archive_subject(s, user_id=1, subject_id=first.id)
        # Should now be allowed again.
        await create_subject(s, user_id=1, title="S3", brief="")
        rows = await list_subjects(s, user_id=1, status="active")
    titles = sorted(r.title for r in rows)
    assert titles == ["S1", "S2", "S3"]


async def test_archive_unknown_raises(session_factory):
    async with session_factory() as s:
        with pytest.raises(LookupError):
            await archive_subject(s, user_id=1, subject_id=999)
```

- [ ] **Step 8.3: Run the test to confirm it fails**

Run: `cd backend && pytest tests/test_subjects_service.py -v`
Expected: ImportError for `app.services.subjects`.

- [ ] **Step 8.4: Write `backend/app/services/subjects.py`**

```python
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subject import Subject

ACTIVE_LIMIT = 3


class ActiveSubjectLimit(Exception):
    """Raised when creating a new active subject would exceed the per-user cap."""


async def _count_active(session: AsyncSession, user_id: int) -> int:
    rows = await session.scalars(
        select(Subject).where(Subject.user_id == user_id, Subject.status == "active")
    )
    return len(rows.all())


async def create_subject(session: AsyncSession, user_id: int, title: str, brief: str) -> Subject:
    if await _count_active(session, user_id) >= ACTIVE_LIMIT:
        raise ActiveSubjectLimit(f"At most {ACTIVE_LIMIT} active subjects allowed")
    subject = Subject(
        user_id=user_id,
        title=title,
        brief=brief,
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    session.add(subject)
    await session.commit()
    await session.refresh(subject)
    return subject


async def list_subjects(
    session: AsyncSession, user_id: int, status: str | None = None
) -> list[Subject]:
    stmt = select(Subject).where(Subject.user_id == user_id).order_by(Subject.created_at.desc())
    if status is not None:
        stmt = stmt.where(Subject.status == status)
    rows = await session.scalars(stmt)
    return list(rows.all())


async def archive_subject(session: AsyncSession, user_id: int, subject_id: int) -> Subject:
    subject = await session.get(Subject, subject_id)
    if subject is None or subject.user_id != user_id:
        raise LookupError(f"Subject {subject_id} not found")
    subject.status = "archived"
    await session.commit()
    await session.refresh(subject)
    return subject
```

- [ ] **Step 8.5: Run the tests**

Run: `cd backend && pytest tests/test_subjects_service.py -v`
Expected: all four tests pass.

- [ ] **Step 8.6: Commit**

```bash
git add backend/app/schemas/subject.py backend/app/services/subjects.py backend/tests/test_subjects_service.py
git commit -m "feat(backend): add subject service with 3-active-per-user constraint"
```

---

## Task 9: Subject routes

**Files:**
- Create: `backend/app/routes/subjects.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_subject_routes.py`

- [ ] **Step 9.1: Write `backend/app/routes/subjects.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.subject import SubjectCreate, SubjectRead
from app.services.subjects import (
    ActiveSubjectLimit,
    archive_subject,
    create_subject,
    list_subjects,
)

router = APIRouter(prefix="/api/v1/subjects", tags=["subjects"])


def _to_read(s) -> SubjectRead:
    return SubjectRead(
        id=s.id, title=s.title, brief=s.brief, status=s.status, created_at=s.created_at
    )


@router.get("", response_model=list[SubjectRead])
async def list_endpoint(
    status_filter: str | None = None,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SubjectRead]:
    rows = await list_subjects(session, user_id=current.id, status=status_filter)
    return [_to_read(s) for s in rows]


@router.post("", response_model=SubjectRead, status_code=201)
async def create_endpoint(
    payload: SubjectCreate,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SubjectRead:
    try:
        s = await create_subject(session, user_id=current.id, title=payload.title, brief=payload.brief)
    except ActiveSubjectLimit as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e
    return _to_read(s)


@router.post("/{subject_id}/archive", response_model=SubjectRead)
async def archive_endpoint(
    subject_id: int,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SubjectRead:
    try:
        s = await archive_subject(session, user_id=current.id, subject_id=subject_id)
    except LookupError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    return _to_read(s)
```

- [ ] **Step 9.2: Modify `backend/app/main.py` to register the subjects router**

Find the line:
```python
app.include_router(auth_routes.router)
```
Add immediately after:
```python
from app.routes import subjects as subject_routes  # noqa: E402
app.include_router(subject_routes.router)
```

- [ ] **Step 9.3: Write the failing test `backend/tests/test_subject_routes.py`**

```python
async def _login(client) -> str:
    r = await client.post("/api/v1/auth/login", json={"email": "admin@test", "password": "pw"})
    return r.json()["access_token"]


async def test_create_list_archive_flow(client):
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    # initially empty
    r = await client.get("/api/v1/subjects", headers=headers)
    assert r.status_code == 200
    assert r.json() == []

    # create one
    r = await client.post(
        "/api/v1/subjects", headers=headers, json={"title": "AI governance", "brief": ""}
    )
    assert r.status_code == 201
    sid = r.json()["id"]

    # list shows it
    r = await client.get("/api/v1/subjects", headers=headers)
    assert [s["id"] for s in r.json()] == [sid]

    # archive it
    r = await client.post(f"/api/v1/subjects/{sid}/archive", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "archived"

    # filter active = empty
    r = await client.get("/api/v1/subjects?status_filter=active", headers=headers)
    assert r.json() == []


async def test_three_active_limit_returns_409(client):
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    for i in range(3):
        r = await client.post(
            "/api/v1/subjects", headers=headers, json={"title": f"S{i}", "brief": ""}
        )
        assert r.status_code == 201
    r = await client.post(
        "/api/v1/subjects", headers=headers, json={"title": "S4", "brief": ""}
    )
    assert r.status_code == 409


async def test_subjects_require_auth(client):
    r = await client.get("/api/v1/subjects")
    assert r.status_code == 401
```

- [ ] **Step 9.4: Run all backend tests**

Run: `cd backend && pytest -v`
Expected: all tests pass.

- [ ] **Step 9.5: Commit**

```bash
git add backend/app/routes/subjects.py backend/app/main.py backend/tests/test_subject_routes.py
git commit -m "feat(backend): add subjects routes (list, create, archive) with auth"
```

---

## Task 10: Frontend project skeleton (Next.js + Tailwind)

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.mjs`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.mjs`
- Create: `frontend/app/layout.tsx`
- Create: `frontend/app/globals.css`
- Create: `frontend/app/page.tsx`

- [ ] **Step 10.1: Write `frontend/package.json`**

```json
{
  "name": "research-team-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "14.2.13",
    "react": "18.3.1",
    "react-dom": "18.3.1"
  },
  "devDependencies": {
    "@types/node": "20.16.5",
    "@types/react": "18.3.7",
    "@types/react-dom": "18.3.0",
    "autoprefixer": "10.4.20",
    "eslint": "8.57.1",
    "eslint-config-next": "14.2.13",
    "postcss": "8.4.47",
    "tailwindcss": "3.4.12",
    "typescript": "5.6.2"
  }
}
```

- [ ] **Step 10.2: Write `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "baseUrl": ".",
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 10.3: Write `frontend/next.config.mjs` (static export)**

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
};
export default nextConfig;
```

- [ ] **Step 10.4: Write `frontend/tailwind.config.ts`**

```typescript
import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: { extend: {} },
  plugins: [],
} satisfies Config;
```

- [ ] **Step 10.5: Write `frontend/postcss.config.mjs`**

```javascript
export default {
  plugins: { tailwindcss: {}, autoprefixer: {} },
};
```

- [ ] **Step 10.6: Write `frontend/app/globals.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root { color-scheme: light dark; }

body {
  @apply bg-neutral-50 text-neutral-900 antialiased;
}
```

- [ ] **Step 10.7: Write `frontend/app/layout.tsx`**

```tsx
import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Research Team",
  description: "Personal multi-agent research environment",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

- [ ] **Step 10.8: Write a minimal placeholder `frontend/app/page.tsx`**

```tsx
export default function Home() {
  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-2xl font-semibold">Research Team</h1>
      <p className="mt-2 text-neutral-600">Phase 1 — foundations placeholder.</p>
    </main>
  );
}
```

- [ ] **Step 10.9: Install and build**

Run:
```bash
cd frontend
npm install
npm run build
```
Expected: `out/` directory is created with static HTML (look for `out/index.html`).

- [ ] **Step 10.10: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): scaffold Next.js with Tailwind and static export"
```

---

## Task 11: Frontend API client and auth context

**Files:**
- Create: `frontend/lib/api.ts`
- Create: `frontend/lib/types.ts`
- Create: `frontend/components/auth-provider.tsx`

- [ ] **Step 11.1: Write `frontend/lib/types.ts`**

```typescript
export type SubjectStatus = "active" | "archived";

export interface Subject {
  id: number;
  title: string;
  brief: string;
  status: SubjectStatus;
  created_at: string;
}

export interface Me {
  id: number;
  email: string;
}
```

- [ ] **Step 11.2: Write `frontend/lib/api.ts`**

```typescript
const TOKEN_KEY = "rt.token";

const API_BASE =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_BASE) || "/api/v1";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token === null) window.localStorage.removeItem(TOKEN_KEY);
  else window.localStorage.setItem(TOKEN_KEY, token);
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function api<T>(
  path: string,
  init: RequestInit & { auth?: boolean } = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (init.auth !== false) {
    const tok = getToken();
    if (tok) headers.set("Authorization", `Bearer ${tok}`);
  }
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new ApiError(res.status, text || res.statusText);
  }
  if (res.status === 204) return undefined as unknown as T;
  return (await res.json()) as T;
}
```

- [ ] **Step 11.3: Write `frontend/components/auth-provider.tsx`**

```tsx
"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, getToken, setToken, ApiError } from "@/lib/api";
import type { Me } from "@/lib/types";

interface AuthState {
  me: Me | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setMe(null);
      setLoading(false);
      return;
    }
    try {
      const m = await api<Me>("/auth/me");
      setMe(m);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setToken(null);
        setMe(null);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(
    async (email: string, password: string) => {
      const r = await api<{ access_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
        auth: false,
      });
      setToken(r.access_token);
      await refresh();
    },
    [refresh],
  );

  const logout = useCallback(() => {
    setToken(null);
    setMe(null);
  }, []);

  return <Ctx.Provider value={{ me, loading, login, logout }}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth must be used within AuthProvider");
  return v;
}
```

- [ ] **Step 11.4: Build to confirm no TS errors**

Run:
```bash
cd frontend
npm run build
```
Expected: build succeeds.

- [ ] **Step 11.5: Commit**

```bash
git add frontend/lib/ frontend/components/auth-provider.tsx
git commit -m "feat(frontend): add API client and auth context"
```

---

## Task 12: Login page and subjects list page

**Files:**
- Modify: `frontend/app/layout.tsx`
- Create: `frontend/app/login/page.tsx`
- Create: `frontend/components/subject-list.tsx`
- Modify: `frontend/app/page.tsx`

- [ ] **Step 12.1: Modify `frontend/app/layout.tsx` to wrap with AuthProvider**

Replace the file with:

```tsx
import "./globals.css";
import type { Metadata } from "next";
import { AuthProvider } from "@/components/auth-provider";

export const metadata: Metadata = {
  title: "Research Team",
  description: "Personal multi-agent research environment",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
```

- [ ] **Step 12.2: Write `frontend/app/login/page.tsx`**

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-sm p-8">
      <h1 className="text-2xl font-semibold mb-6">Sign in</h1>
      <form onSubmit={onSubmit} className="space-y-4">
        <label className="block">
          <span className="text-sm">Email</span>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded border border-neutral-300 px-3 py-2"
          />
        </label>
        <label className="block">
          <span className="text-sm">Password</span>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded border border-neutral-300 px-3 py-2"
          />
        </label>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded bg-neutral-900 py-2 text-white disabled:opacity-50"
        >
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </main>
  );
}
```

- [ ] **Step 12.3: Write `frontend/components/subject-list.tsx`**

```tsx
"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Subject } from "@/lib/types";

export function SubjectList() {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState("");
  const [brief, setBrief] = useState("");
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const rows = await api<Subject[]>("/subjects");
      setSubjects(rows);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api<Subject>("/subjects", {
        method: "POST",
        body: JSON.stringify({ title, brief }),
      });
      setTitle("");
      setBrief("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    }
  }

  async function onArchive(id: number) {
    await api<Subject>(`/subjects/${id}/archive`, { method: "POST" });
    await refresh();
  }

  const active = subjects.filter((s) => s.status === "active");
  const archived = subjects.filter((s) => s.status === "archived");

  return (
    <div className="space-y-8">
      <section>
        <h2 className="text-lg font-medium mb-2">Active subjects ({active.length}/3)</h2>
        {loading ? (
          <p className="text-sm text-neutral-500">Loading…</p>
        ) : active.length === 0 ? (
          <p className="text-sm text-neutral-500">No active subjects yet.</p>
        ) : (
          <ul className="divide-y divide-neutral-200 rounded border border-neutral-200">
            {active.map((s) => (
              <li key={s.id} className="flex items-center justify-between p-3">
                <div>
                  <div className="font-medium">{s.title}</div>
                  {s.brief && <div className="text-sm text-neutral-600">{s.brief}</div>}
                </div>
                <button
                  onClick={() => onArchive(s.id)}
                  className="text-sm text-neutral-600 hover:text-neutral-900"
                >
                  Archive
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2 className="text-lg font-medium mb-2">New subject</h2>
        <form onSubmit={onCreate} className="space-y-3">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Title"
            required
            className="w-full rounded border border-neutral-300 px-3 py-2"
          />
          <textarea
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            placeholder="Brief (your framing of the project)"
            className="w-full rounded border border-neutral-300 px-3 py-2"
            rows={3}
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={active.length >= 3 || !title.trim()}
            className="rounded bg-neutral-900 px-4 py-2 text-white disabled:opacity-50"
          >
            Create
          </button>
        </form>
      </section>

      {archived.length > 0 && (
        <section>
          <h2 className="text-lg font-medium mb-2">Archived</h2>
          <ul className="divide-y divide-neutral-200 rounded border border-neutral-200 opacity-70">
            {archived.map((s) => (
              <li key={s.id} className="p-3">
                <div className="font-medium">{s.title}</div>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
```

- [ ] **Step 12.4: Replace `frontend/app/page.tsx` with auth-gated subjects view**

```tsx
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import { SubjectList } from "@/components/subject-list";

export default function Home() {
  const { me, loading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !me) router.replace("/login");
  }, [loading, me, router]);

  if (loading || !me) return null;

  return (
    <main className="mx-auto max-w-3xl p-8">
      <header className="mb-8 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Research Team</h1>
        <div className="flex items-center gap-4 text-sm text-neutral-600">
          <span>{me.email}</span>
          <button onClick={logout} className="hover:text-neutral-900">
            Sign out
          </button>
        </div>
      </header>
      <SubjectList />
    </main>
  );
}
```

- [ ] **Step 12.5: Build to confirm no TS errors**

Run:
```bash
cd frontend
npm run build
```
Expected: build succeeds; `out/index.html` and `out/login/index.html` exist.

- [ ] **Step 12.6: Commit**

```bash
git add frontend/app/ frontend/components/subject-list.tsx
git commit -m "feat(frontend): login page and subject list (create/archive)"
```

---

## Task 13: FastAPI serves the static frontend

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 13.1: Modify `backend/app/main.py` to mount static frontend at `/`**

Replace the file with:

```python
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import SessionLocal
from app.routes import auth as auth_routes
from app.routes import subjects as subject_routes
from app.services.users import ensure_admin_user

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "out"


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with SessionLocal() as session:
        await ensure_admin_user(session, settings.admin_email, settings.admin_password)
    yield


app = FastAPI(title="Research Team", version="0.1.0", lifespan=lifespan)
app.include_router(auth_routes.router)
app.include_router(subject_routes.router)


@app.get("/api/v1/health")
async def health() -> dict:
    return {"status": "ok"}


# Serve the statically-exported frontend if present (production).
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
```

- [ ] **Step 13.2: Run all backend tests**

Run: `cd backend && pytest -v`
Expected: all tests pass (the static mount is conditional on dir existing, so tests are unaffected).

- [ ] **Step 13.3: Manually verify combined serving**

Run:
```bash
cd frontend && npm run build && cd ..
cd backend && uvicorn app.main:app --port 8000 &
sleep 2
curl -s http://localhost:8000/api/v1/health
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/
kill %1
```
Expected: `{"status":"ok"}` for the API, `200` for `/`.

- [ ] **Step 13.4: Commit**

```bash
git add backend/app/main.py
git commit -m "feat(backend): serve static frontend from /"
```

---

## Task 14: Dockerfile (multi-stage) and docker-compose

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`

- [ ] **Step 14.1: Write `Dockerfile`**

```dockerfile
# ---------- frontend builder ----------
FROM node:20-alpine AS frontend
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------- backend ----------
FROM python:3.11-slim AS runtime
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml ./backend/
RUN pip install --no-cache-dir -e ./backend

COPY backend/ ./backend/
COPY --from=frontend /app/out ./frontend/out

WORKDIR /app/backend
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

- [ ] **Step 14.2: Write `docker-compose.yml`**

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: research
      POSTGRES_PASSWORD: research
      POSTGRES_DB: research
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U research"]
      interval: 5s
      timeout: 5s
      retries: 10

  web:
    build: .
    environment:
      DATABASE_URL: postgresql+asyncpg://research:research@db:5432/research
      JWT_SECRET: ${JWT_SECRET:-dev-secret}
      ADMIN_EMAIL: ${ADMIN_EMAIL:-admin@example.com}
      ADMIN_PASSWORD: ${ADMIN_PASSWORD:-changeme}
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy

volumes:
  pgdata:
```

- [ ] **Step 14.3: Build and run**

Run:
```bash
docker-compose up --build -d
sleep 10
curl -s http://localhost:8000/api/v1/health
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"changeme"}'
docker-compose down
```
Expected: health returns `{"status":"ok"}`; login returns a JSON object containing `access_token`.

- [ ] **Step 14.4: Commit**

```bash
git add Dockerfile docker-compose.yml
git commit -m "chore: add multi-stage Dockerfile and docker-compose for local dev"
```

---

## Task 15: Railway deployment config and final E2E smoke test

**Files:**
- Create: `railway.json`
- Modify: `README.md`

- [ ] **Step 15.1: Write `railway.json`**

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": { "builder": "DOCKERFILE", "dockerfilePath": "Dockerfile" },
  "deploy": {
    "startCommand": "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/api/v1/health",
    "healthcheckTimeout": 30,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 5
  }
}
```

Note: the `startCommand` runs from the image's `WORKDIR` (`/app/backend`), so `alembic` and `app.main:app` resolve correctly.

- [ ] **Step 15.2: Append a deployment section to `README.md`**

Add at the end of `README.md`:

```markdown

## Deploying to Railway

1. Create a new Railway project from this repo.
2. Add the **Postgres** plugin. Railway will provision `DATABASE_URL` for you.
3. **Important:** the Railway-provided `DATABASE_URL` uses the `postgres://` scheme.
   Override it for the web service to start with `postgresql+asyncpg://` so SQLAlchemy uses the async driver. Example:
   ```
   DATABASE_URL=postgresql+asyncpg://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.PGHOST}}:${{Postgres.PGPORT}}/${{Postgres.PGDATABASE}}
   ```
4. Set the remaining env vars: `JWT_SECRET`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`.
5. Deploy. Migrations run on container start; admin user is created on first boot.
```

- [ ] **Step 15.3: Run the full local E2E flow end-to-end**

Run:
```bash
docker-compose up --build -d
sleep 12

# 1. Health
curl -s http://localhost:8000/api/v1/health

# 2. Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"changeme"}' | python -c "import json,sys;print(json.load(sys.stdin)['access_token'])")
echo "Token: ${TOKEN:0:20}…"

# 3. /me
curl -s http://localhost:8000/api/v1/auth/me -H "Authorization: Bearer $TOKEN"

# 4. Create three subjects
for i in 1 2 3; do
  curl -s -X POST http://localhost:8000/api/v1/subjects \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d "{\"title\":\"Subject $i\",\"brief\":\"\"}"
  echo
done

# 5. Fourth should fail with 409
curl -s -o /dev/null -w "Fourth create: %{http_code}\n" -X POST http://localhost:8000/api/v1/subjects \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"title":"Subject 4","brief":""}'

# 6. List
curl -s http://localhost:8000/api/v1/subjects -H "Authorization: Bearer $TOKEN" | python -m json.tool

# 7. Frontend serves
curl -s -o /dev/null -w "Frontend root: %{http_code}\n" http://localhost:8000/
curl -s -o /dev/null -w "Login page: %{http_code}\n" http://localhost:8000/login/

docker-compose down
```
Expected:
- Health returns `{"status":"ok"}`
- Token is a non-empty string
- `/me` returns admin email
- Three creates succeed; fourth returns `Fourth create: 409`
- List shows three subjects
- Frontend root and `/login/` both return `200`

- [ ] **Step 15.4: Commit**

```bash
git add railway.json README.md
git commit -m "chore: add railway deploy config and document deployment"
```

---

## Phase 1 Done

At this point:
- A user can sign in, create up to 3 active subjects, archive them, see them listed.
- Backend is fully tested (auth, subjects, services, routes).
- Frontend is statically built and served by the backend container.
- Postgres has `pgvector` ready for Phase 2 memory tables.
- Deployable to Railway with a single push.

The next plan (`docs/superpowers/plans/2026-MM-DD-phase-2-domain-core.md`) introduces the role catalog, agent instances, and per-agent settings UI — laying the groundwork for the cognitive-friction engine.
