from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import Base
from app.deps import get_session
from app.initial_roles import role_seed_rows
from app.main import app
from app.models.role import Role
from app.services.users import ensure_admin_user


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    cur = dbapi_connection.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


@pytest.fixture
async def session_factory(tmp_path):
    db_url = f"sqlite+aiosqlite:///{tmp_path/'test.db'}"
    engine = create_async_engine(db_url)
    event.listen(engine.sync_engine, "connect", _enable_sqlite_foreign_keys)

    # SQLite can't render the pgvector Vector type; skip that one table in tests.
    # Phase 3+ tests that need vectors will run against a real Postgres.
    test_tables = [t for t in Base.metadata.tables.values() if t.name != "agent_memory_vectors"]

    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=test_tables))

    factory = async_sessionmaker(engine, expire_on_commit=False)

    # Seed default roles so subject creation can spawn a default team.
    now = datetime.now(timezone.utc)
    async with factory() as s:
        for row in role_seed_rows():
            s.add(Role(**row, created_at=now))
        await s.commit()

    yield factory
    await engine.dispose()


@pytest.fixture
async def client(session_factory):
    async def override_get_session():
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = override_get_session
    async with session_factory() as s:
        await ensure_admin_user(s, "admin@test.com", "pw")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
