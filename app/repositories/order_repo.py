"""Data access cho Order (đơn mua gói)."""
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order


async def create(session: AsyncSession, order: Order) -> Order:
    session.add(order)
    await session.flush()
    return order


async def get_by_id(session: AsyncSession, order_id: int) -> Order | None:
    return await session.get(Order, order_id)


async def get_by_code(session: AsyncSession, code: str) -> Order | None:
    res = await session.execute(select(Order).where(Order.code == code))
    return res.scalar_one_or_none()


async def list_recent(session: AsyncSession, limit: int = 100) -> list[Order]:
    res = await session.execute(
        select(Order).order_by(desc(Order.created_at)).limit(limit)
    )
    return list(res.scalars().all())
