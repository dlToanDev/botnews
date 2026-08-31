"""Gửi tin nhắn Telegram từ tiến trình web (webhook) — dùng BOT_TOKEN, best-effort."""
import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def send_message(chat_id: int, text: str) -> None:
    """Gửi message; nuốt lỗi (không để webhook fail chỉ vì gửi tin lỗi)."""
    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                url,
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            )
            if resp.status_code != 200:
                logger.warning("Gửi Telegram thất bại: %s %s", resp.status_code, resp.text[:200])
    except Exception as e:  # noqa: BLE001
        logger.warning("Lỗi gửi Telegram: %s", e)
