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
