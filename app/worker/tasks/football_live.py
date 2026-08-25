"""Task push live score bóng đá cho user theo dõi đội (mỗi 2')."""
import asyncio

from app.core.dedup import should_alert
from app.core.logging import get_logger
from app.core.timeutils import now_local
from app.integrations import football
from app.repositories import module_repo
from app.worker.celery_app import celery_app
from app.worker.db import worker_session
from app.worker.tasks.send_message import send_message_task

logger = get_logger(__name__)
LIVE_STATUSES = {"1H", "2H", "HT", "ET", "P", "LIVE"}
DEDUP_TTL = 600  # 10' cho cùng tỉ số


async def _run() -> int:
    if not football.is_configured():
        return 0
    date_str = now_local().strftime("%Y-%m-%d")
    fixtures = await football.get_fixtures(date_str)
    live = [f for f in fixtures if f.get("status") in LIVE_STATUSES]
    if not live:
        return 0

    sent = 0
    async with worker_session() as session:
        rows = await module_repo.eligible_users(session, "football")
        for user, st in rows:
            teams = [t.lower() for t in (st.favorite_teams or [])]
            if not teams:
                continue
            for f in live:
                names = f"{f['home']} {f['away']}".lower()
                if not any(t in names for t in teams):
                    continue
                key = f"football:{user.id}:{f['home']}:{f['away']}:{f['home_goals']}-{f['away_goals']}"
                if not await should_alert(key, DEDUP_TTL):
                    continue
                text = (
                    f"⚽ *LIVE* ({f['status']})\n"
                    f"{f['home']} `{f['home_goals']}-{f['away_goals']}` {f['away']}"
                )
                send_message_task.delay(user.telegram_id, text)
                sent += 1
    if sent:
        logger.info("Football live: enqueue %d message.", sent)
    return sent


@celery_app.task(name="app.worker.tasks.football_live.poll_and_alert")
def poll_and_alert() -> int:
    return asyncio.run(_run())
