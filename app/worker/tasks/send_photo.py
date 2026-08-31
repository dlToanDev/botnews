"""Task gửi 1 ảnh + caption Telegram; fallback về text nếu ảnh lỗi."""
import asyncio

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden, RetryAfter

from app.core.config import settings
from app.worker.celery_app import celery_app


@celery_app.task(bind=True, max_retries=5, rate_limit="25/s")
def send_photo_task(self, chat_id: int, photo_url: str, caption: str) -> str:
    async def _send() -> str:
        bot = Bot(token=settings.BOT_TOKEN)
        async with bot:
            try:
                await bot.send_photo(
                    chat_id=chat_id, photo=photo_url, caption=caption,
                    parse_mode=ParseMode.MARKDOWN,
                )
                return "sent"
            except RetryAfter as e:
                raise self.retry(countdown=int(e.retry_after) + 1) from e
            except Forbidden:
                return "forbidden"
            except BadRequest:
                # Ảnh hỏng/URL không tải được → vẫn gửi tin dạng text để không mất tin.
                await bot.send_message(
                    chat_id=chat_id, text=caption, parse_mode=ParseMode.MARKDOWN
                )
                return "sent_text"

    return asyncio.run(_send())
