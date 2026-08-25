"""Task push tin nóng theo từ khoá user (mỗi 15')."""
import asyncio

from app.core.dedup import should_alert
from app.core.logging import get_logger
from app.integrations.news import get_news, match_keywords
from app.repositories import module_repo
from app.worker.celery_app import celery_app
from app.worker.db import worker_session
from app.worker.tasks.send_message import send_message_task

logger = get_logger(__name__)
DEDUP_TTL = 86400  # 1 ngày không gửi lại cùng 1 link
MAX_PER_RUN = 3    # tối đa 3 tin/user mỗi lần chạy


async def _run() -> int:
    items = await get_news()
    if not items:
        return 0

    sent = 0
    async with worker_session() as session:
        rows = await module_repo.eligible_users(session, "news")
        for user, st in rows:
            keywords = list(st.news_keywords or [])
            if not keywords:
                continue
            pushed = 0
            for it in items:
                if pushed >= MAX_PER_RUN:
                    break
                if not match_keywords(it["title"], keywords):
                    continue
                link = it["link"]
                key = f"news:{user.id}:{abs(hash(link))}"
                if not await should_alert(key, DEDUP_TTL):
                    continue
                text = f"📰 *Tin nóng*\n[{it['title']}]({link})"
                send_message_task.delay(user.telegram_id, text)
                sent += 1
                pushed += 1
    if sent:
        logger.info("News push: enqueue %d message.", sent)
    return sent


@celery_app.task(name="app.worker.tasks.news_push.poll_and_alert")
def poll_and_alert() -> int:
    return asyncio.run(_run())
