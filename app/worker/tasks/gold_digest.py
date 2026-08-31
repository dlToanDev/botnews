"""Task chạy mỗi phút: gửi bản tin giá vàng theo GIỜ CỐ ĐỊNH (per-user hoặc hệ thống)."""
import asyncio

from app.core.dedup import should_alert
from app.core.logging import get_logger
from app.core.timeutils import now_local
from app.integrations.gold import get_gold_prices
from app.repositories import module_repo
from app.services import system_settings_service
from app.services.gold_service import effective_times, format_gold_prices
from app.worker.celery_app import celery_app
from app.worker.db import worker_session
from app.worker.tasks.send_message import send_message_task

logger = get_logger(__name__)
DEDUP_TTL = 7200  # 2 giờ: không gửi lặp cùng user+ngày+giờ


async def _run() -> int:
    now = now_local()
    hhmm = now.strftime("%H:%M")
    sent = 0
    async with worker_session() as session:
        sys_cfg = await system_settings_service.get_gold_notify(session)
        rows = await module_repo.eligible_users(session, "gold")
        # Bỏ qua sớm nếu không ai có thể nhận vào phút này (không user nào & hệ thống tắt)
        if not rows:
            return 0

        items = None
        for user, st in rows:
            times = effective_times(list(st.gold_times or []), sys_cfg["enabled"], sys_cfg["times"])
            if hhmm not in times:
                continue
            date = now.strftime("%Y%m%d")
            if not await should_alert(f"golddigest:{user.id}:{date}:{hhmm}", DEDUP_TTL):
                continue
            if items is None:  # chỉ gọi API khi thực sự cần
                items = await get_gold_prices()
            if not items:
                break
            text = format_gold_prices(items, now.strftime("%H:%M %d/%m"))
            send_message_task.delay(user.telegram_id, text)
            sent += 1
    if sent:
        logger.info("Gold digest: enqueue %d bản tin (%s).", sent, hhmm)
    return sent


@celery_app.task(name="app.worker.tasks.gold_digest.poll_and_send")
def poll_and_send() -> int:
    return asyncio.run(_run())
