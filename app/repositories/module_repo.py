"""Data access cho SubscriptionModule."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timeutils import now_utc
from app.models.subscription import SubscriptionModule


async def list_for_user(session: AsyncSession, user_id: int) -> list[SubscriptionModule]:
    res = await session.execute(
        select(SubscriptionModule).where(SubscriptionModule.user_id == user_id)
    )
    return list(res.scalars().all())


async def get(session: AsyncSession, user_id: int, module_key: str) -> SubscriptionModule | None:
    res = await session.execute(
        select(SubscriptionModule).where(
            SubscriptionModule.user_id == user_id,
            SubscriptionModule.module_key == module_key,
        )
    )
    return res.scalar_one_or_none()


async def upsert(
    session: AsyncSession, user_id: int, module_key: str, is_enabled: bool
) -> SubscriptionModule:
    row = await get(session, user_id, module_key)
    if row is None:
        row = SubscriptionModule(user_id=user_id, module_key=module_key)
        session.add(row)
    row.is_enabled = is_enabled
    row.enabled_at = now_utc() if is_enabled else None
    await session.flush()
    return row


async def eligible_users(session: AsyncSession, module_key: str):
    """User active + còn hạn + đã bật module → trả list (User, UserSettings)."""
    from app.core.timeutils import now_utc
    from app.models.user import User, UserSettings

    now = now_utc()
    stmt = (
        select(User, UserSettings)
        .join(SubscriptionModule, SubscriptionModule.user_id == User.id)
        .join(UserSettings, UserSettings.user_id == User.id)
        .where(
            SubscriptionModule.module_key == module_key,
            SubscriptionModule.is_enabled.is_(True),
            User.status == "active",
            (User.expires_at.is_(None)) | (User.expires_at > now),
        )
    )
    res = await session.execute(stmt)
    return list(res.all())


async def enabled_map_for_users(
    session: AsyncSession, user_ids: list[int]
) -> dict[int, set[str]]:
    """Trả {user_id: {module_key đang bật}} cho nhiều user trong 1 query (tránh N+1)."""
    if not user_ids:
        return {}
    res = await session.execute(
        select(SubscriptionModule.user_id, SubscriptionModule.module_key).where(
            SubscriptionModule.user_id.in_(user_ids),
            SubscriptionModule.is_enabled.is_(True),
        )
    )
    out: dict[int, set[str]] = {uid: set() for uid in user_ids}
    for uid, key in res.all():
        out.setdefault(uid, set()).add(key)
    return out


async def count_enabled_by_module(session: AsyncSession) -> dict[str, int]:
    from sqlalchemy import func

    res = await session.execute(
        select(SubscriptionModule.module_key, func.count())
        .where(SubscriptionModule.is_enabled.is_(True))
        .group_by(SubscriptionModule.module_key)
    )
    return {key: cnt for key, cnt in res.all()}
