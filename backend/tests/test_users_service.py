import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.users import ensure_admin_user


@pytest.fixture
async def session(tmp_path):
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
    assert a.password_hash == b.password_hash
