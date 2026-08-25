"""Business logic cho User."""
from app.core.database import AsyncSessionLocal
from app.core.timeutils import now_utc
from app.models.user import User
from app.repositories import log_repo, user_repo


async def get_or_create_user(
    telegram_id: int,
    username: str | None = None,
    full_name: str | None = None,
) -> tuple[User, bool]:
    """Trả về (user, created). Tạo mới + settings mặc định nếu chưa có."""
    async with AsyncSessionLocal() as session:
        user = await user_repo.get_by_telegram_id(session, telegram_id)
        created = False
        if user is None:
            user = await user_repo.create(
                session,
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
            )
            created = True
            await log_repo.write(
                session,
                action="user_register",
                user_id=user.id,
                actor="user",
                detail={"telegram_id": telegram_id, "username": username},
            )
        await session.commit()
        return user, created


def is_active(user: User) -> bool:
    if user.status != "active":
        return False
    if user.expires_at is not None and user.expires_at <= now_utc():
        return False
    return True
