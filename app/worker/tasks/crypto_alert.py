"""Task poll giá Crypto (2') → cảnh báo biến động vượt ngưỡng watchlist."""
import asyncio

from app.core.dedup import should_alert
from app.core.logging import get_logger
from app.integrations.crypto import get_all_tickers
from app.repositories import module_repo
from app.worker.celery_app import celery_app
from app.worker.db import worker_session
from app.worker.tasks.send_message import send_message_task

logger = get_logger(__name__)
DEDUP_TTL = 1800  # 30' không lặp cùng 1 cảnh báo


async def _run() -> int:
    tickers = await get_all_tickers()
    sent = 0
    async with worker_session() as session:
        rows = await module_repo.eligible_users(session, "crypto")
        for user, st in rows:
            for w in (st.crypto_watchlist or []):
                sym = str(w.get("symbol", "")).upper()
                thr = float(w.get("threshold_pct", 0) or 0)
                t = tickers.get(sym)
                if not t or thr <= 0:
                    continue
                if abs(t["change_pct"]) < thr:
                    continue
                sign = "up" if t["change_pct"] >= 0 else "down"
                if not await should_alert(f"crypto:{user.id}:{sym}:{sign}", DEDUP_TTL):
                    continue
                arrow = "🟢▲" if sign == "up" else "🔴▼"
                text = (
                    f"🚨 *Cảnh báo Crypto*\n*{sym}* {arrow} `{t['change_pct']:+.2f}%`/24h\n"
                    f"💵 Giá: `{t['price']:,}`"
                )
                send_message_task.delay(user.telegram_id, text)
                sent += 1
    if sent:
        logger.info("Crypto alert: enqueue %d message.", sent)
    return sent


@celery_app.task(name="app.worker.tasks.crypto_alert.poll_and_alert")
def poll_and_alert() -> int:
    return asyncio.run(_run())
