"""Cập nhật cấu hình cá nhân (watchlist crypto, teams, news keywords, ngưỡng vàng)."""
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.core.database import AsyncSessionLocal
from app.models.user import User, UserSettings


async def _get_settings(session, telegram_id: int) -> UserSettings | None:
    res = await session.execute(
        select(UserSettings).join(User, User.id == UserSettings.user_id).where(
            User.telegram_id == telegram_id
        )
    )
    return res.scalar_one_or_none()


async def add_crypto_watch(telegram_id: int, symbol: str, threshold_pct: float) -> list:
    symbol = symbol.upper()
    async with AsyncSessionLocal() as session:
        st = await _get_settings(session, telegram_id)
        if st is None:
            return []
        wl = [w for w in (st.crypto_watchlist or []) if w.get("symbol") != symbol]
        wl.append({"symbol": symbol, "threshold_pct": threshold_pct})
        st.crypto_watchlist = wl
        flag_modified(st, "crypto_watchlist")
        await session.commit()
        return wl


async def add_favorite_team(telegram_id: int, team: str) -> list:
    async with AsyncSessionLocal() as session:
        st = await _get_settings(session, telegram_id)
        if st is None:
            return []
        teams = list(st.favorite_teams or [])
        if team not in teams:
            teams.append(team)
        st.favorite_teams = teams
        flag_modified(st, "favorite_teams")
        await session.commit()
        return teams


async def get_favorite_teams(telegram_id: int) -> list:
    async with AsyncSessionLocal() as session:
        st = await _get_settings(session, telegram_id)
        return list(st.favorite_teams or []) if st else []


async def set_news_keywords(telegram_id: int, keywords: list[str]) -> list:
    async with AsyncSessionLocal() as session:
        st = await _get_settings(session, telegram_id)
        if st is None:
            return []
        st.news_keywords = keywords
        flag_modified(st, "news_keywords")
        await session.commit()
        return keywords


async def _get_settings_by_user_id(session, user_id: int) -> UserSettings | None:
    res = await session.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    return res.scalar_one_or_none()


async def get_news_categories(session, user_id: int) -> list:
    """Danh mục tin user đang chọn (rỗng = tất cả). Dùng cho web dashboard."""
    st = await _get_settings_by_user_id(session, user_id)
    return list(st.news_categories or []) if st else []


async def set_news_categories(session, user_id: int, categories: list[str]) -> list:
    """Lưu danh mục tin (session do caller commit). Dùng cho web dashboard."""
    st = await _get_settings_by_user_id(session, user_id)
    if st is None:
        return []
    st.news_categories = categories
    flag_modified(st, "news_categories")
    return categories


async def get_gold_times(session, user_id: int) -> list:
    """Giờ nhận báo giá vàng của user (rỗng = theo hệ thống). Dùng cho web."""
    st = await _get_settings_by_user_id(session, user_id)
    return list(st.gold_times or []) if st else []


async def set_gold_times(session, user_id: int, times: list[str]) -> list:
    """Lưu giờ báo giá vàng per-user (session do caller commit)."""
    st = await _get_settings_by_user_id(session, user_id)
    if st is None:
        return []
    st.gold_times = times
    flag_modified(st, "gold_times")
    return times


async def get_crypto_prefs(session, user_id: int) -> dict:
    """Cấu hình crypto per-user: {mode, times, coins}."""
    st = await _get_settings_by_user_id(session, user_id)
    if st is None:
        return {"mode": "system", "times": [], "coins": []}
    return {
        "mode": st.crypto_notify_mode or "system",
        "times": list(st.crypto_times or []),
        "coins": list(st.crypto_coins or []),
    }


async def get_football_prefs(session, user_id: int) -> dict:
    """Cấu hình bóng đá per-user: {times, teams}."""
    st = await _get_settings_by_user_id(session, user_id)
    if st is None:
        return {"times": [], "teams": []}
    return {"times": list(st.football_times or []), "teams": list(st.favorite_teams or [])}


async def set_football_prefs(session, user_id: int, times: list[str], teams: list[str]) -> None:
    st = await _get_settings_by_user_id(session, user_id)
    if st is None:
        return
    st.football_times = times
    st.favorite_teams = teams
    flag_modified(st, "football_times")
    flag_modified(st, "favorite_teams")


async def set_crypto_prefs(session, user_id: int, mode: str, times: list[str], coins: list[str]) -> None:
    st = await _get_settings_by_user_id(session, user_id)
    if st is None:
        return
    st.crypto_notify_mode = mode if mode in ("system", "custom", "off") else "system"
    st.crypto_times = times
    st.crypto_coins = coins
    flag_modified(st, "crypto_times")
    flag_modified(st, "crypto_coins")
