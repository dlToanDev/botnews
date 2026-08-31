"""Task đẩy tin mới theo loại cho user (mỗi 2'). Ai bật module news là nhận."""
import asyncio

from app.core.constants import NEWS_CATEGORY_LABELS
from app.core.dedup import should_alert
from app.core.logging import get_logger
from app.core.redis_client import redis_client
from app.integrations.news import get_news, match_keywords
from app.repositories import module_repo
from app.services import system_settings_service
from app.worker.celery_app import celery_app
from app.worker.db import worker_session
from app.worker.tasks.send_message import send_message_task
from app.worker.tasks.send_photo import send_photo_task

logger = get_logger(__name__)

DEDUP_TTL = 86400        # per-user: 1 ngày không gửi lại cùng 1 link
SEEN_TTL = 3 * 86400     # global: nhớ link đã thấy 3 ngày
MAX_PER_RUN = 10         # cap an toàn/user mỗi lần (phòng feed đổ dồn)
SEEDED_FLAG = "news:seeded"


def _link_hash(link: str) -> int:
    return abs(hash(link))


def effective_news_cats(user_cats: list[str], default_cats: list[str]) -> list[str]:
    """Danh mục hiệu lực: user nếu có; không thì mặc định hệ thống; cả hai trống → []."""
    if user_cats:
        return list(user_cats)
    return list(default_cats)


def _passes_filter(item: dict, cats: list[str], keywords: list[str]) -> bool:
    """User có nhận tin này không: cats rỗng = tất cả; có cats thì phải khớp; keyword lọc thêm."""
    if cats and item.get("category") not in cats:
        return False
    if keywords and not match_keywords(item.get("title", ""), keywords):
        return False
    return True


async def _new_items(items: list[dict]) -> list[dict]:
    """Chỉ trả tin có link lần đầu xuất hiện toàn cục. Lần chạy đầu: seed im lặng (không trả gì)."""
    seeded = await redis_client.get(SEEDED_FLAG)
    fresh = []
    for it in items:
        key = f"news:seen:{_link_hash(it['link'])}"
        is_new = await redis_client.set(key, "1", ex=SEEN_TTL, nx=True)
        if is_new and seeded:
            fresh.append(it)
    if not seeded:
        await redis_client.set(SEEDED_FLAG, "1")  # đánh dấu đã seed (không hết hạn)
        return []
    return fresh


async def _run() -> int:
    items = await get_news()
    if not items:
        return 0
    fresh = await _new_items(items)
    if not fresh:
        return 0

    sent = 0
    async with worker_session() as session:
        default_cats = (await system_settings_service.get_news_default(session)).get("categories", [])
        rows = await module_repo.eligible_users(session, "news")
        for user, st in rows:
            cats = effective_news_cats(list(st.news_categories or []), default_cats)
            keywords = list(st.news_keywords or [])
            pushed = 0
            for it in fresh:
                if pushed >= MAX_PER_RUN:
                    logger.warning("News push: user %s chạm cap %d tin/lần.", user.id, MAX_PER_RUN)
                    break
                if not _passes_filter(it, cats, keywords):
                    continue
                key = f"news:{user.id}:{_link_hash(it['link'])}"
                if not await should_alert(key, DEDUP_TTL):
                    continue
                label = NEWS_CATEGORY_LABELS.get(it.get("category"), "Tin tức")
                caption = f"📰 *Tin mới · {label}*\n[{it['title']}]({it['link']})"
                if it.get("image"):
                    send_photo_task.delay(user.telegram_id, it["image"], caption)
                else:
                    send_message_task.delay(user.telegram_id, caption)
                sent += 1
                pushed += 1
    if sent:
        logger.info("News push: enqueue %d message.", sent)
    return sent


@celery_app.task(name="app.worker.tasks.news_push.poll_and_alert")
def poll_and_alert() -> int:
    return asyncio.run(_run())
