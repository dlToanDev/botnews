"""Data access cho Log."""
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.log import Log


async def write(
    session: AsyncSession,
    *,
    action: str,
    user_id: int | None = None,
    actor: str = "system",
    level: str = "info",
    detail: dict | None = None,
) -> Log:
    log = Log(
        action=action,
        user_id=user_id,
        actor=actor,
        level=level,
        detail=detail or {},
    )
    session.add(log)
    await session.flush()
    return log


async def recent(session: AsyncSession, limit: int = 100) -> list[Log]:
    res = await session.execute(select(Log).order_by(desc(Log.created_at)).limit(limit))
    return list(res.scalars().all())
