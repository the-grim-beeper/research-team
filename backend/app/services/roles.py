from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Role


async def list_roles(session: AsyncSession) -> list[Role]:
    rows = await session.scalars(select(Role).order_by(Role.category, Role.display_name))
    return list(rows.all())


async def get_role_by_slug(session: AsyncSession, slug: str) -> Role | None:
    return await session.scalar(select(Role).where(Role.slug == slug))
