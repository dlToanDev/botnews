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


async def set_news_keywords(telegram_id: int, keywords: list[str]) -> list:
    async with AsyncSessionLocal() as session:
        st = await _get_settings(session, telegram_id)
        if st is None:
            return []
        st.news_keywords = keywords
        flag_modified(st, "news_keywords")
        await session.commit()
        return keywords
