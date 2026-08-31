"""Router: cấu hình toàn hệ thống (hiện có: thông báo giá vàng)."""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    CRYPTO_SYMBOLS,
    FOOTBALL_LEAGUE_CODES,
    FOOTBALL_LEAGUES,
    NEWS_CATEGORIES,
    NEWS_CATEGORY_KEYS,
)
from app.core.database import get_session
from app.models.admin import Admin
from app.services import gold_service, system_settings_service
from app.web.deps import get_current_admin, templates

router = APIRouter(prefix="/settings")


@router.get("")
async def settings_page(
    request: Request,
    saved: int | None = None,
    err: int | None = None,
    tab: str | None = None,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    gold = await system_settings_service.get_gold_notify(session)
    crypto = await system_settings_service.get_crypto_notify(session)
    news = await system_settings_service.get_news_default(session)
    football = await system_settings_service.get_football_notify(session)
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "admin": admin,
            "gold_enabled": gold["enabled"],
            "gold_times": ", ".join(gold["times"]),
            "crypto_enabled": crypto["enabled"],
            "crypto_times": ", ".join(crypto["times"]),
            "crypto_all_coins": CRYPTO_SYMBOLS,
            "crypto_coins_selected": crypto["coins"],
            "news_cats_all": NEWS_CATEGORIES,
            "news_cats_selected": news["categories"],
            "football_enabled": football["enabled"],
            "football_times": ", ".join(football["times"]),
            "football_all_leagues": FOOTBALL_LEAGUES,
            "football_leagues_selected": football["leagues"],
            "saved": saved,
            "err": err,
            "tab": tab or "gold",
        },
    )


@router.post("/gold")
async def save_gold(
    enabled: str | None = Form(default=None),
    times: str = Form(default=""),
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    try:
        parsed = gold_service.parse_times(times)
    except ValueError:
        return RedirectResponse("/settings?err=1&tab=gold", status_code=303)
    await system_settings_service.set_gold_notify(session, enabled is not None, parsed)
    await session.commit()
    return RedirectResponse("/settings?saved=1&tab=gold", status_code=303)


@router.post("/crypto")
async def save_crypto(
    enabled: str | None = Form(default=None),
    times: str = Form(default=""),
    coins: list[str] = Form(default=[]),
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    try:
        parsed = gold_service.parse_times(times)
    except ValueError:
        return RedirectResponse("/settings?err=1&tab=crypto", status_code=303)
    valid_coins = [c for c in coins if c in CRYPTO_SYMBOLS]
    await system_settings_service.set_crypto_notify(session, enabled is not None, parsed, valid_coins)
    await session.commit()
    return RedirectResponse("/settings?saved=1&tab=crypto", status_code=303)


@router.post("/news")
async def save_news(
    categories: list[str] = Form(default=[]),
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    valid = [c for c in categories if c in NEWS_CATEGORY_KEYS]
    await system_settings_service.set_news_default(session, valid)
    await session.commit()
    return RedirectResponse("/settings?saved=1&tab=news", status_code=303)


@router.post("/football")
async def save_football(
    enabled: str | None = Form(default=None),
    times: str = Form(default=""),
    leagues: list[str] = Form(default=[]),
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    try:
        parsed = gold_service.parse_times(times)
    except ValueError:
        return RedirectResponse("/settings?err=1&tab=football", status_code=303)
    valid_leagues = [x for x in leagues if x in FOOTBALL_LEAGUE_CODES]
    await system_settings_service.set_football_notify(session, enabled is not None, parsed, valid_leagues)
    await session.commit()
    return RedirectResponse("/settings?saved=1&tab=football", status_code=303)
