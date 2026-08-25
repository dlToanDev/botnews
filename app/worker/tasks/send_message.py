"""Task gửi 1 message Telegram, rate-limited + tự retry khi bị giới hạn."""
import asyncio

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import Forbidden, RetryAfter

from app.core.config import settings
from app.worker.celery_app import celery_app


@celery_app.task(bind=True, max_retries=5, rate_limit="25/s")
def send_message_task(self, chat_id: int, text: str) -> str:
    async def _send() -> str:
        bot = Bot(token=settings.BOT_TOKEN)
        async with bot:
            try:
                await bot.send_message(
                    chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN
                )
                return "sent"
            except RetryAfter as e:
                raise self.retry(countdown=int(e.retry_after) + 1) from e
            except Forbidden:
                # User đã block bot → bỏ qua (Phase 2 có thể đánh dấu inactive)
                return "forbidden"

    return asyncio.run(_send())
