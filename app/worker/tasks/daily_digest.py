"""Task 7h sáng: gửi tổng hợp lịch trong ngày cho từng user active."""
import asyncio

from app.core.logging import get_logger
from app.core.timeutils import local_day_bounds_utc
from app.repositories import schedule_repo, user_repo
from app.services.schedule_service import format_schedule_line
from app.services.user_service import is_active
from app.worker.celery_app import celery_app
from app.worker.db import worker_session
from app.worker.tasks.send_message import send_message_task

logger = get_logger(__name__)


async def _run() -> int:
    start, end = local_day_bounds_utc()
    sent = 0
    async with worker_session() as session:
        users = await user_repo.list_active(session)
        for user in users:
            if not is_active(user):
                continue
            items = await schedule_repo.list_between(session, user.id, start, end)
            if not items:
                continue
            body = "\n".join(format_schedule_line(s) for s in items)
            text = f"*☀️ Chào buổi sáng!*\n*Lịch hôm nay ({len(items)}):*\n{body}"
            send_message_task.delay(user.telegram_id, text)
            sent += 1
    logger.info("Daily digest: đã enqueue %d user.", sent)
    return sent


@celery_app.task(name="app.worker.tasks.daily_digest.send_daily_digest")
def send_daily_digest() -> int:
    return asyncio.run(_run())
