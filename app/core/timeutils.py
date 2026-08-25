"""Tiện ích thời gian — lưu UTC trong DB, hiển thị theo giờ địa phương (VN)."""
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.config import settings

LOCAL_TZ = ZoneInfo(settings.TIMEZONE)
UTC = timezone.utc


def now_utc() -> datetime:
    return datetime.now(UTC)


def now_local() -> datetime:
    return datetime.now(LOCAL_TZ)


def to_local(dt: datetime) -> datetime:
    """Chuyển datetime (aware) sang giờ địa phương."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(LOCAL_TZ)


def to_utc(dt: datetime) -> datetime:
    """Chuyển datetime (aware) sang UTC. Nếu naive → coi là giờ địa phương."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=LOCAL_TZ)
    return dt.astimezone(UTC)


def local_day_bounds_utc(ref: datetime | None = None) -> tuple[datetime, datetime]:
    """Trả về (đầu ngày, cuối ngày) theo giờ VN của ngày `ref`, quy đổi sang UTC."""
    local = to_local(ref) if ref else now_local()
    start_local = datetime.combine(local.date(), time.min, tzinfo=LOCAL_TZ)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


def fmt_local(dt: datetime, pattern: str = "%H:%M %d/%m/%Y") -> str:
    return to_local(dt).strftime(pattern)
