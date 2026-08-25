"""Decorators phân quyền cho handlers.

Phase 1: @require_active (nhận diện user + chặn banned/expired) và ghi log lệnh.
Phase 2 sẽ bổ sung @require_module(key) cho các tính năng SaaS.
"""
from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

from app.core.database import AsyncSessionLocal
from app.repositories import log_repo
from app.services.user_service import get_or_create_user, is_active


async def _log_command(user_id: int, command: str) -> None:
    async with AsyncSessionLocal() as session:
        await log_repo.write(
            session,
            action="command",
            user_id=user_id,
            actor="user",
            detail={"command": command},
        )
        await session.commit()


def require_active(handler):
    @wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        tg = update.effective_user
        message = update.effective_message
        user, _created = await get_or_create_user(tg.id, tg.username, tg.full_name)

        if user.status == "banned":
            await message.reply_text("⛔ Tài khoản của bạn đã bị khoá.")
            return
        if not is_active(user):
            await message.reply_text(
                "⌛ Tài khoản đã hết hạn. Vui lòng liên hệ Admin để gia hạn."
            )
            return

        context.user_data["db_user_id"] = user.id
        if message and message.text:
            await _log_command(user.id, message.text.split()[0])
        return await handler(update, context, *args, **kwargs)

    return wrapper
