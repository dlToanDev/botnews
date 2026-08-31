"""Task mỗi phút: báo KẾT QUẢ bóng đá vòng gần nhất theo GIỜ CỐ ĐỊNH (giải/hệ thống + đội per-user)."""
import asyncio

from app.core.constants import FOOTBALL_LEAGUE_CODES, FOOTBALL_LEAGUE_LABELS
from app.core.dedup import should_alert
from app.core.logging import get_logger
from app.core.timeutils import now_local
from app.integrations import football_data
from app.repositories import module_repo
from app.services import system_settings_service
from app.services.football_service import filter_by_teams, format_results_digest
from app.services.gold_service import effective_times
from app.worker.celery_app import celery_app
from app.worker.db import worker_session
from app.worker.tasks.send_message import send_message_task

logger = get_logger(__name__)
DEDUP_TTL = 7200


async def _run() -> int:
    if not football_data.is_configured():
        return 0
    now = now_local()
    hhmm = now.strftime("%H:%M")
    sent = 0
    async with worker_session() as session:
        sys_cfg = await system_settings_service.get_football_notify(session)
        rows = await module_repo.eligible_users(session, "football")
        if not rows:
            return 0

        leagues = sys_cfg["leagues"] or FOOTBALL_LEAGUE_CODES
        cache: dict[str, dict] = {}  # code -> {matchday, matches}

        for user, st in rows:
            times = effective_times(list(st.football_times or []), sys_cfg["enabled"], sys_cfg["times"])
            if hhmm not in times:
                continue
            date = now.strftime("%Y%m%d")
            if not await should_alert(f"footballdigest:{user.id}:{date}:{hhmm}", DEDUP_TTL):
                continue

            teams = list(st.favorite_teams or [])
            sections = []
            for code in leagues:
                if code not in cache:
                    cache[code] = await football_data.get_recent_results(code)
                data = cache[code]
                matches = filter_by_teams(data.get("matches") or [], teams)
                if matches:
                    sections.append(
                        {"label": FOOTBALL_LEAGUE_LABELS.get(code, code),
                         "matchday": data.get("matchday"), "matches": matches}
                    )
            if not sections:
                continue
            text = format_results_digest(sections, now.strftime("%H:%M %d/%m"))
            send_message_task.delay(user.telegram_id, text)
            sent += 1
    if sent:
        logger.info("Football digest: enqueue %d bản tin (%s).", sent, hhmm)
    return sent


@celery_app.task(name="app.worker.tasks.football_digest.poll_and_send")
def poll_and_send() -> int:
    return asyncio.run(_run())
