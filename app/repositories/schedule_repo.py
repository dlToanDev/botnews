"""Data access cho Schedule."""
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule import Schedule


async def create(session: AsyncSession, **fields) -> Schedule:
    sch = Schedule(**fields)
    session.add(sch)
    await session.flush()
    return sch


async def get(session: AsyncSession, schedule_id: int) -> Schedule | None:
    return await session.get(Schedule, schedule_id)


async def list_by_user(
    session: AsyncSession, user_id: int, only_active: bool = True
) -> list[Schedule]:
    stmt = select(Schedule).where(Schedule.user_id == user_id)
    if only_active:
        stmt = stmt.where(Schedule.is_active.is_(True))
    stmt = stmt.order_by(Schedule.start_time)
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def list_between(
    session: AsyncSession, user_id: int, start: datetime, end: datetime
) -> list[Schedule]:
    stmt = (
        select(Schedule)
        .where(
            Schedule.user_id == user_id,
            Schedule.is_active.is_(True),
            Schedule.start_time >= start,
            Schedule.start_time < end,
        )
        .order_by(Schedule.start_time)
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def delete(session: AsyncSession, schedule_id: int, user_id: int) -> bool:
    """Soft-independent delete: chỉ xoá nếu đúng chủ sở hữu."""
    sch = await session.get(Schedule, schedule_id)
    if sch is None or sch.user_id != user_id:
        return False
    await session.delete(sch)
    return True


async def list_due_reminders(
    session: AsyncSession, now: datetime, horizon_minutes: int = 60
) -> list[Schedule]:
    """Lịch active, chưa nhắc, bắt đầu trong khoảng (now, now + horizon].

    Việc lọc chính xác theo reminder_minutes của từng lịch thực hiện ở service.
    """
    upper = now + timedelta(minutes=horizon_minutes)
    stmt = select(Schedule).where(
        Schedule.is_active.is_(True),
        Schedule.is_notified.is_(False),
        Schedule.start_time > now,
        Schedule.start_time <= upper,
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())
