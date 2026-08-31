"""Task chạy mỗi phút: gửi bản tin giá crypto theo GIỜ CỐ ĐỊNH (per-user hoặc hệ thống)."""
import asyncio

from app.core.dedup import should_alert
from app.core.logging import get_logger
from app.core.timeutils import now_local
from app.integrations import coingecko
from app.repositories import module_repo
from app.services import system_settings_service
from app.services.crypto_service import format_price_digest, resolve_notify, select_coins
from app.worker.celery_app import celery_app
from app.worker.db import worker_session
from app.worker.tasks.send_message import send_message_task

logger = get_logger(__name__)
DEDUP_TTL = 7200


async def _run() -> int:
    now = now_local()
    hhmm = now.strftime("%H:%M")
    sent = 0
    async with worker_session() as session:
        sys_cfg = await system_settings_service.get_crypto_notify(session)
        rows = await module_repo.eligible_users(session, "crypto")
        if not rows:
            return 0

        all_coins = None
        for user, st in rows:
            times, coins = resolve_notify(
                st.crypto_notify_mode or "system",
                list(st.crypto_times or []),
                list(st.crypto_coins or []),
                sys_cfg["enabled"], sys_cfg["times"], sys_cfg["coins"],
            )
            if hhmm not in times:
                continue
            date = now.strftime("%Y%m%d")
            if not await should_alert(f"cryptodigest:{user.id}:{date}:{hhmm}", DEDUP_TTL):
                continue
            if all_coins is None:
                all_coins = await coingecko.get_tracked()
            picked = select_coins(all_coins, coins)
            if not picked:
                continue
            text = format_price_digest(picked, now.strftime("%H:%M %d/%m"))
            send_message_task.delay(user.telegram_id, text)
            sent += 1
    if sent:
        logger.info("Crypto digest: enqueue %d bản tin (%s).", sent, hhmm)
    return sent


@celery_app.task(name="app.worker.tasks.crypto_digest.poll_and_send")
def poll_and_send() -> int:
    return asyncio.run(_run())
