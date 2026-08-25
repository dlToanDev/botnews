"""Task poll giá vàng (10') → cảnh báo khi SJC biến động vượt ngưỡng user."""
import asyncio

from app.core.dedup import should_alert
from app.core.logging import get_logger
from app.core.redis_client import redis_client
from app.integrations.gold import get_gold_by_code
from app.repositories import module_repo
from app.worker.celery_app import celery_app
from app.worker.db import worker_session
from app.worker.tasks.send_message import send_message_task

logger = get_logger(__name__)
BASELINE_KEY = "gold:baseline:SJC"
DEDUP_TTL = 1800


async def _run() -> int:
    sjc = await get_gold_by_code("SJC")
    if not sjc or not sjc.get("sell"):
        return 0
    current = float(sjc["sell"])

    baseline_raw = await redis_client.get(BASELINE_KEY)
    if baseline_raw is None:
        await redis_client.set(BASELINE_KEY, current)
        return 0
    baseline = float(baseline_raw)
    if baseline <= 0:
        await redis_client.set(BASELINE_KEY, current)
        return 0

    pct = (current - baseline) / baseline * 100.0
    sent = 0
    async with worker_session() as session:
        rows = await module_repo.eligible_users(session, "gold")
        for user, st in rows:
            thr = float(st.gold_alert_pct or 0)
            if thr <= 0 or abs(pct) < thr:
                continue
            if not await should_alert(f"gold:{user.id}", DEDUP_TTL):
                continue
            arrow = "🟢▲" if pct >= 0 else "🔴▼"
            text = (
                f"🚨 *Cảnh báo Giá vàng SJC*\n{arrow} `{pct:+.2f}%`\n"
                f"💰 Giá bán hiện tại: `{current:,.0f}` VND"
            )
            send_message_task.delay(user.telegram_id, text)
            sent += 1

    if sent:  # reset mốc để đo biến động tiếp theo từ đây
        await redis_client.set(BASELINE_KEY, current)
        logger.info("Gold alert: enqueue %d message (pct=%.2f).", sent, pct)
    return sent


@celery_app.task(name="app.worker.tasks.gold_alert.poll_and_alert")
def poll_and_alert() -> int:
    return asyncio.run(_run())
