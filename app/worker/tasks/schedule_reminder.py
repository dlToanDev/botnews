"""Task chạy mỗi phút: nhắc lịch trước giờ, đánh dấu is_notified để không lặp."""
import asyncio

from app.core.logging import get_logger
from app.core.timeutils import now_utc, to_local
from app.repositories import schedule_repo, user_repo
from app.services.schedule_service import collect_due_reminders
from app.worker.celery_app import celery_app
from app.worker.db import worker_session
from app.worker.tasks.send_message import send_message_task

logger = get_logger(__name__)


async def _run() -> int:
    now = now_utc()
    sent = 0
    async with worker_session() as session:
        # 1) Nhắc TRƯỚC giờ (còn ~N phút)
        due = await collect_due_reminders(session, now)
        for sch in due:
            user = await user_repo.get_by_id(session, sch.user_id)
            if user is None or user.status != "active":
                continue
            t = to_local(sch.start_time).strftime("%H:%M")
            loc = f"\n📍 {sch.location}" if sch.location else ""
            text = (
                f"⏰ *Nhắc lịch!*\n"
                f"🕘 *{t}* — {sch.title}{loc}\n"
                f"(còn ~{sch.reminder_minutes} phút nữa)"
            )
            send_message_task.delay(user.telegram_id, text)
            sch.is_notified = True
            sent += 1

        # 2) Báo ĐÚNG giờ (đến giờ rồi)
        due_now = await schedule_repo.list_due_started(session, now)
        for sch in due_now:
            user = await user_repo.get_by_id(session, sch.user_id)
            if user is None or user.status != "active":
                continue
            t = to_local(sch.start_time).strftime("%H:%M")
            loc = f"\n📍 {sch.location}" if sch.location else ""
            text = f"🔔 *Đến giờ rồi!*\n🕘 *{t}* — {sch.title}{loc}"
            send_message_task.delay(user.telegram_id, text)
            sch.started_notified = True
            sent += 1

        await session.commit()
    if sent:
        logger.info("Reminder: đã gửi %d thông báo lịch.", sent)
    return sent


@celery_app.task(name="app.worker.tasks.schedule_reminder.check_reminders")
def check_reminders() -> int:
    return asyncio.run(_run())
