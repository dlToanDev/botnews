"""Data access cho User + UserSettings."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserSettings


async def get_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    res = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return res.scalar_one_or_none()


async def get_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def create(
    session: AsyncSession,
    *,
    telegram_id: int,
    username: str | None = None,
    full_name: str | None = None,
) -> User:
    user = User(
        telegram_id=telegram_id,
        username=username,
        full_name=full_name,
        status="active",
    )
    user.settings = UserSettings()  # tạo settings mặc định kèm theo
    session.add(user)
    await session.flush()
    return user


async def list_active(session: AsyncSession) -> list[User]:
    res = await session.execute(select(User).where(User.status == "active"))
    return list(res.scalars().all())
