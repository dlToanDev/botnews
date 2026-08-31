"""Data access cho User + UserSettings."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_MODULES
from app.core.timeutils import now_utc
from app.models.subscription import SubscriptionModule
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
    # Bật sẵn các module nền cho tài khoản mới (vd: lịch cá nhân ai cũng có).
    now = now_utc()
    for key in DEFAULT_MODULES:
        session.add(
            SubscriptionModule(
                user_id=user.id, module_key=key, is_enabled=True, enabled_at=now
            )
        )
    await session.flush()
    return user


async def list_active(session: AsyncSession) -> list[User]:
    res = await session.execute(select(User).where(User.status == "active"))
    return list(res.scalars().all())


async def search(
    session: AsyncSession, q: str | None = None, limit: int = 100, offset: int = 0
) -> list[User]:
    from sqlalchemy import cast, or_
    from sqlalchemy import String as SAString

    stmt = select(User)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                User.username.ilike(like),
                User.full_name.ilike(like),
                cast(User.telegram_id, SAString).ilike(like),
            )
        )
    stmt = stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def count_by_status(session: AsyncSession) -> dict[str, int]:
    from sqlalchemy import func

    res = await session.execute(select(User.status, func.count()).group_by(User.status))
    return {status: cnt for status, cnt in res.all()}


async def count_by_plan(session: AsyncSession) -> dict[str, int]:
    from sqlalchemy import func

    res = await session.execute(select(User.plan, func.count()).group_by(User.plan))
    return {plan: cnt for plan, cnt in res.all()}


async def count_new_by_month(session: AsyncSession, months: int = 6) -> dict[str, int]:
    """Số user mới theo tháng (YYYY-MM), phủ đủ `months` tháng gần nhất (gồm cả 0)."""
    from datetime import timedelta

    from sqlalchemy import func

    since = now_utc() - timedelta(days=31 * months)
    bucket = func.to_char(User.created_at, "YYYY-MM")
    res = await session.execute(
        select(bucket, func.count())
        .where(User.created_at >= since)
        .group_by(bucket)
    )
    counts = {label: cnt for label, cnt in res.all()}

    # Dựng chuỗi tháng liên tục để biểu đồ không bị hụt cột.
    now = now_utc()
    y, m = now.year, now.month
    labels: list[str] = []
    for _ in range(months):
        labels.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    labels.reverse()
    return {label: counts.get(label, 0) for label in labels}


async def expiring_soon(session: AsyncSession, days: int = 7) -> list[User]:
    """User đang active sắp hết hạn trong `days` ngày tới (sớm nhất lên đầu)."""
    from datetime import timedelta

    now = now_utc()
    until = now + timedelta(days=days)
    stmt = (
        select(User)
        .where(
            User.status == "active",
            User.expires_at.is_not(None),
            User.expires_at > now,
            User.expires_at <= until,
        )
        .order_by(User.expires_at.asc())
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def expire_overdue(session: AsyncSession) -> int:
    """Chuyển user active đã quá hạn → expired. Trả về số user bị đổi."""
    from sqlalchemy import update

    res = await session.execute(
        update(User)
        .where(User.status == "active", User.expires_at.is_not(None), User.expires_at <= now_utc())
        .values(status="expired")
    )
    return res.rowcount or 0
