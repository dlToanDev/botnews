"""Đọc/ghi cấu hình toàn hệ thống (bảng system_settings, key-value JSONB)."""
from app.models.system_setting import SystemSetting

GOLD_NOTIFY_KEY = "gold_notify"
CRYPTO_NOTIFY_KEY = "crypto_notify"
NEWS_DEFAULT_KEY = "news_default"
GOLD_NOTIFY_DEFAULT = {"enabled": False, "times": []}


async def get(session, key: str, default=None):
    row = await session.get(SystemSetting, key)
    return row.value if row is not None else default


async def set(session, key: str, value) -> None:
    row = await session.get(SystemSetting, key)
    if row is None:
        session.add(SystemSetting(key=key, value=value))
    else:
        row.value = value


async def get_gold_notify(session) -> dict:
    val = await get(session, GOLD_NOTIFY_KEY, None)
    if not isinstance(val, dict):
        return dict(GOLD_NOTIFY_DEFAULT)
    return {"enabled": bool(val.get("enabled")), "times": list(val.get("times") or [])}


async def set_gold_notify(session, enabled: bool, times: list[str]) -> None:
    await set(session, GOLD_NOTIFY_KEY, {"enabled": bool(enabled), "times": list(times)})


async def get_crypto_notify(session) -> dict:
    val = await get(session, CRYPTO_NOTIFY_KEY, None)
    if not isinstance(val, dict):
        return {"enabled": False, "times": [], "coins": []}
    return {
        "enabled": bool(val.get("enabled")),
        "times": list(val.get("times") or []),
        "coins": list(val.get("coins") or []),
    }


async def set_crypto_notify(session, enabled: bool, times: list[str], coins: list[str]) -> None:
    await set(
        session,
        CRYPTO_NOTIFY_KEY,
        {"enabled": bool(enabled), "times": list(times), "coins": list(coins)},
    )


FOOTBALL_NOTIFY_KEY = "football_notify"


async def get_football_notify(session) -> dict:
    val = await get(session, FOOTBALL_NOTIFY_KEY, None)
    if not isinstance(val, dict):
        return {"enabled": False, "times": [], "leagues": []}
    return {
        "enabled": bool(val.get("enabled")),
        "times": list(val.get("times") or []),
        "leagues": list(val.get("leagues") or []),
    }


async def set_football_notify(session, enabled: bool, times: list[str], leagues: list[str]) -> None:
    await set(
        session,
        FOOTBALL_NOTIFY_KEY,
        {"enabled": bool(enabled), "times": list(times), "leagues": list(leagues)},
    )


async def get_news_default(session) -> dict:
    val = await get(session, NEWS_DEFAULT_KEY, None)
    if not isinstance(val, dict):
        return {"categories": []}
    return {"categories": list(val.get("categories") or [])}


async def set_news_default(session, categories: list[str]) -> None:
    await set(session, NEWS_DEFAULT_KEY, {"categories": list(categories)})
