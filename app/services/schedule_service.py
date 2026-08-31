"""Business logic cho Lịch cá nhân."""
import re
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.timeutils import (
    LOCAL_TZ,
    local_day_bounds_utc,
    local_month_bounds_utc,
    now_local,
    to_local,
    to_utc,
)
from app.models.schedule import Schedule
from app.repositories import log_repo, schedule_repo, user_repo


class ScheduleParseError(ValueError):
    """Không parse được input lịch."""


_TIME_ONLY = re.compile(r"^(\d{1,2}):(\d{2})\s+(.+)$", re.DOTALL)
_DATE_DMY = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2})\s+(.+)$", re.DOTALL)
_DATE_DM = re.compile(r"^(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})\s+(.+)$", re.DOTALL)
_DATE_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})\s+(\d{1,2}):(\d{2})\s+(.+)$", re.DOTALL)


def parse_schedule_input(text: str) -> tuple[datetime, str]:
    """Parse input thành (start_local_aware, title).

    Hỗ trợ:
      - "08:00 Đi làm"                → hôm nay (hoặc mai nếu đã qua giờ)
      - "26/08 08:00 Họp team"        → ngày/tháng năm hiện tại
      - "30/08/2026 08:00 Thức dậy"   → ngày/tháng/năm đầy đủ
      - "2026-08-26 08:00 Họp team"   → ngày đầy đủ (ISO)
    """
    text = text.strip()
    now = now_local()

    if m := _DATE_ISO.match(text):
        y, mo, d, hh, mm, title = m.groups()
        start = datetime(int(y), int(mo), int(d), int(hh), int(mm), tzinfo=LOCAL_TZ)
    elif m := _DATE_DMY.match(text):
        d, mo, y, hh, mm, title = m.groups()
        start = datetime(int(y), int(mo), int(d), int(hh), int(mm), tzinfo=LOCAL_TZ)
    elif m := _DATE_DM.match(text):
        d, mo, hh, mm, title = m.groups()
        start = datetime(now.year, int(mo), int(d), int(hh), int(mm), tzinfo=LOCAL_TZ)
        if start < now:  # nếu ngày/tháng đã qua trong năm nay → sang năm sau
            start = start.replace(year=now.year + 1)
    elif m := _TIME_ONLY.match(text):
        hh, mm, title = m.groups()
        start = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
        if start <= now:  # đã qua giờ hôm nay → đặt cho ngày mai
            start += timedelta(days=1)
    else:
        raise ScheduleParseError(
            "Sai định dạng. Ví dụ:\n"
            "• `08:00 Đi làm`\n"
            "• `26/08 14:30 Họp team`\n"
            "• `2026-08-26 09:00 Khám sức khỏe`"
        )

    hh_i, mm_i = start.hour, start.minute
    if hh_i > 23 or mm_i > 59:
        raise ScheduleParseError("Giờ/phút không hợp lệ.")
    return start, title.strip()


async def add_schedule(
    telegram_id: int,
    title: str,
    start_local: datetime,
    reminder_minutes: int = 30,
    description: str | None = None,
    location: str | None = None,
) -> Schedule:
    async with AsyncSessionLocal() as session:
        user = await user_repo.get_by_telegram_id(session, telegram_id)
        if user is None:
            raise ValueError("User chưa tồn tại")
        sch = await schedule_repo.create(
            session,
            user_id=user.id,
            title=title,
            start_time=to_utc(start_local),
            reminder_minutes=reminder_minutes,
            description=description,
            location=location,
        )
        await log_repo.write(
            session,
            action="schedule_add",
            user_id=user.id,
            actor="user",
            detail={"schedule_id": sch.id, "title": title},
        )
        await session.commit()
        await session.refresh(sch)
        return sch


async def list_today(telegram_id: int) -> list[Schedule]:
    async with AsyncSessionLocal() as session:
        user = await user_repo.get_by_telegram_id(session, telegram_id)
        if user is None:
            return []
        start, end = local_day_bounds_utc()
        return await schedule_repo.list_between(session, user.id, start, end)


async def list_all(telegram_id: int) -> list[Schedule]:
    async with AsyncSessionLocal() as session:
        user = await user_repo.get_by_telegram_id(session, telegram_id)
        if user is None:
            return []
        return await schedule_repo.list_by_user(session, user.id, only_active=True)


async def day_events(telegram_id: int, year: int, month: int, day: int) -> list[Schedule]:
    """Lịch của 1 ngày (giờ VN)."""
    ref = datetime(year, month, day, 12, 0, tzinfo=LOCAL_TZ)
    async with AsyncSessionLocal() as session:
        user = await user_repo.get_by_telegram_id(session, telegram_id)
        if user is None:
            return []
        start, end = local_day_bounds_utc(ref)
        return await schedule_repo.list_between(session, user.id, start, end)


async def month_event_days(telegram_id: int, year: int, month: int) -> set[int]:
    """Tập ngày (theo giờ VN) trong tháng có ít nhất 1 lịch."""
    async with AsyncSessionLocal() as session:
        user = await user_repo.get_by_telegram_id(session, telegram_id)
        if user is None:
            return set()
        start, end = local_month_bounds_utc(year, month)
        rows = await schedule_repo.list_between(session, user.id, start, end)
        return {to_local(s.start_time).day for s in rows}


async def update_time(telegram_id: int, schedule_id: int, new_start_local: datetime) -> bool:
    """Đổi giờ 1 lịch. Đặt lại is_notified=False để nhắc đúng giờ mới."""
    async with AsyncSessionLocal() as session:
        user = await user_repo.get_by_telegram_id(session, telegram_id)
        if user is None:
            return False
        ok = await schedule_repo.update(
            session, schedule_id, user.id,
            start_time=to_utc(new_start_local), is_notified=False, started_notified=False,
        )
        if ok:
            await log_repo.write(
                session, action="schedule_edit_time", user_id=user.id, actor="user",
                detail={"schedule_id": schedule_id},
            )
        await session.commit()
        return ok


async def update_title(telegram_id: int, schedule_id: int, title: str) -> bool:
    """Đổi tiêu đề 1 lịch."""
    async with AsyncSessionLocal() as session:
        user = await user_repo.get_by_telegram_id(session, telegram_id)
        if user is None:
            return False
        ok = await schedule_repo.update(session, schedule_id, user.id, title=title)
        if ok:
            await log_repo.write(
                session, action="schedule_edit_title", user_id=user.id, actor="user",
                detail={"schedule_id": schedule_id, "title": title},
            )
        await session.commit()
        return ok


async def delete_schedule(telegram_id: int, schedule_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        user = await user_repo.get_by_telegram_id(session, telegram_id)
        if user is None:
            return False
        ok = await schedule_repo.delete(session, schedule_id, user.id)
        if ok:
            await log_repo.write(
                session,
                action="schedule_delete",
                user_id=user.id,
                actor="user",
                detail={"schedule_id": schedule_id},
            )
        await session.commit()
        return ok


async def collect_due_reminders(session: AsyncSession, now_utc_dt: datetime) -> list[Schedule]:
    """Lấy các lịch đang trong cửa sổ nhắc (now >= start - reminder_minutes)."""
    candidates = await schedule_repo.list_due_reminders(session, now_utc_dt, horizon_minutes=60)
    due = []
    for sch in candidates:
        remind_at = sch.start_time - timedelta(minutes=sch.reminder_minutes)
        if now_utc_dt >= remind_at:
            due.append(sch)
    return due


def format_schedule_line(sch: Schedule) -> str:
    t = to_local(sch.start_time).strftime("%H:%M")
    loc = f" @ {sch.location}" if sch.location else ""
    return f"🕘 *{t}* — {sch.title}{loc}  (#{sch.id})"
