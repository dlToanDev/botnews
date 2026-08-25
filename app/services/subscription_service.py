"""Business logic cho phân quyền module & gói cước (SaaS core)."""
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import MODULE_KEYS
from app.core.database import AsyncSessionLocal
from app.core.timeutils import now_utc
from app.models.user import User
from app.repositories import log_repo, module_repo, user_repo


async def list_modules(session: AsyncSession, user_id: int) -> dict[str, bool]:
    """Trả về trạng thái bật/tắt của TẤT CẢ module (mặc định False nếu chưa có row)."""
    rows = await module_repo.list_for_user(session, user_id)
    existing = {r.module_key: r.is_enabled for r in rows}
    return {key: existing.get(key, False) for key in MODULE_KEYS}


async def set_module(session: AsyncSession, user_id: int, key: str, enabled: bool) -> None:
    if key not in MODULE_KEYS:
        raise ValueError(f"Module không hợp lệ: {key}")
    await module_repo.upsert(session, user_id, key, enabled)
    await log_repo.write(
        session,
        action="module_toggle",
        user_id=user_id,
        actor="admin",
        detail={"module": key, "enabled": enabled},
    )


async def set_status(session: AsyncSession, user_id: int, status: str) -> User | None:
    user = await user_repo.get_by_id(session, user_id)
    if user is None:
        return None
    user.status = status
    await log_repo.write(
        session, action="status_change", user_id=user_id, actor="admin",
        detail={"status": status},
    )
    return user


async def extend_plan(session: AsyncSession, user_id: int, days: int) -> User | None:
    """Cộng dồn từ hạn hiện tại (nếu còn) hoặc từ hôm nay; kích hoạt lại."""
    user = await user_repo.get_by_id(session, user_id)
    if user is None:
        return None
    now = now_utc()
    base = user.expires_at if (user.expires_at and user.expires_at > now) else now
    user.expires_at = base + timedelta(days=days)
    user.status = "active"
    await log_repo.write(
        session, action="plan_extend", user_id=user_id, actor="admin",
        detail={"days": days, "new_expiry": user.expires_at.isoformat()},
    )
    return user


# ---- Bot-facing (tự mở session) ----

async def has_module(user_id: int, key: str) -> bool:
    async with AsyncSessionLocal() as session:
        row = await module_repo.get(session, user_id, key)
        return bool(row and row.is_enabled)


async def expire_overdue_users() -> int:
    async with AsyncSessionLocal() as session:
        n = await user_repo.expire_overdue(session)
        if n:
            await log_repo.write(
                session, action="auto_expire", actor="system", detail={"count": n}
            )
        await session.commit()
        return n
