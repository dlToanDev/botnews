"""Data access cho Admin."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin


async def get_by_username(session: AsyncSession, username: str) -> Admin | None:
    res = await session.execute(select(Admin).where(Admin.username == username))
    return res.scalar_one_or_none()


async def create(session: AsyncSession, username: str, password_hash: str) -> Admin:
    admin = Admin(username=username, password_hash=password_hash)
    session.add(admin)
    await session.flush()
    return admin
