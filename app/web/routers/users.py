"""Router: quản lý User."""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    CRYPTO_SYMBOLS,
    MODULE_KEYS,
    MODULE_LABELS,
    NEWS_CATEGORIES,
    NEWS_CATEGORY_KEYS,
    PACKAGES,
    PLANS,
    USER_STATUSES,
)
from app.core.database import get_session
from app.models.admin import Admin
from app.repositories import module_repo, user_repo
from app.services import gold_service, settings_service, subscription_service
from app.web.deps import get_current_admin, templates

router = APIRouter(prefix="/users")


@router.get("")
async def list_users(
    request: Request,
    q: str | None = None,
    status: str | None = None,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    users = await user_repo.search(session, q=q)
    if status in USER_STATUSES:
        users = [u for u in users if u.status == status]
    mod_map = await module_repo.enabled_map_for_users(session, [u.id for u in users])
    modules_meta = [
        {"key": k, "label": MODULE_LABELS[k], "emoji": MODULE_LABELS[k].split(" ")[0]}
        for k in MODULE_KEYS
    ]
    return templates.TemplateResponse(
        "users.html",
        {
            "request": request,
            "admin": admin,
            "users": users,
            "q": q or "",
            "status": status or "",
            "statuses": USER_STATUSES,
            "mod_map": mod_map,
            "modules_meta": modules_meta,
        },
    )


@router.get("/{user_id}")
async def user_detail(
    request: Request,
    user_id: int,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    user = await user_repo.get_by_id(session, user_id)
    if user is None:
        return RedirectResponse("/users", status_code=303)
    modules = await subscription_service.list_modules(session, user_id)
    module_list = [
        {"key": k, "label": MODULE_LABELS[k], "enabled": modules[k]} for k in MODULE_KEYS
    ]
    enabled_count = sum(1 for k in MODULE_KEYS if modules[k])
    news_categories = await settings_service.get_news_categories(session, user_id)
    gold_times = await settings_service.get_gold_times(session, user_id)
    crypto_prefs = await settings_service.get_crypto_prefs(session, user_id)
    football_prefs = await settings_service.get_football_prefs(session, user_id)
    return templates.TemplateResponse(
        "user_detail.html",
        {
            "request": request,
            "admin": admin,
            "user": user,
            "user_id": user.id,  # _module_row.html include cần user_id cho hx-post
            "modules": module_list,
            "enabled_count": enabled_count,
            "total_modules": len(MODULE_KEYS),
            "statuses": USER_STATUSES,
            "plans": PLANS,
            "packages": PACKAGES,
            "module_labels": MODULE_LABELS,
            "news_cats_all": NEWS_CATEGORIES,
            "news_cats_selected": news_categories,
            "gold_times": ", ".join(gold_times),
            "crypto_mode": crypto_prefs["mode"],
            "crypto_times": ", ".join(crypto_prefs["times"]),
            "crypto_coins_selected": crypto_prefs["coins"],
            "crypto_all_coins": CRYPTO_SYMBOLS,
            "football_times": ", ".join(football_prefs["times"]),
            "football_teams": ", ".join(football_prefs["teams"]),
        },
    )


@router.post("/{user_id}/news")
async def save_news_categories(
    user_id: int,
    categories: list[str] = Form(default=[]),
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    valid = [c for c in categories if c in NEWS_CATEGORY_KEYS]
    await settings_service.set_news_categories(session, user_id, valid)
    await session.commit()
    return RedirectResponse(f"/users/{user_id}", status_code=303)


@router.post("/{user_id}/gold")
async def save_gold_times(
    user_id: int,
    gold_times: str = Form(default=""),
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    try:
        times = gold_service.parse_times(gold_times)
    except ValueError:
        return RedirectResponse(f"/users/{user_id}?gold_err=1", status_code=303)
    await settings_service.set_gold_times(session, user_id, times)
    await session.commit()
    return RedirectResponse(f"/users/{user_id}", status_code=303)


@router.post("/{user_id}/crypto")
async def save_crypto_prefs(
    user_id: int,
    mode: str = Form(default="system"),
    crypto_times: str = Form(default=""),
    coins: list[str] = Form(default=[]),
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    try:
        times = gold_service.parse_times(crypto_times)
    except ValueError:
        return RedirectResponse(f"/users/{user_id}?gold_err=1", status_code=303)
    valid_coins = [c for c in coins if c in CRYPTO_SYMBOLS]
    await settings_service.set_crypto_prefs(session, user_id, mode, times, valid_coins)
    await session.commit()
    return RedirectResponse(f"/users/{user_id}", status_code=303)


@router.post("/{user_id}/football")
async def save_football_prefs(
    user_id: int,
    football_times: str = Form(default=""),
    teams: str = Form(default=""),
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    try:
        times = gold_service.parse_times(football_times)
    except ValueError:
        return RedirectResponse(f"/users/{user_id}?gold_err=1", status_code=303)
    team_list = [t.strip() for t in teams.split(",") if t.strip()]
    await settings_service.set_football_prefs(session, user_id, times, team_list)
    await session.commit()
    return RedirectResponse(f"/users/{user_id}", status_code=303)


@router.post("/{user_id}/status")
async def change_status(
    user_id: int,
    status: str = Form(...),
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    if status in USER_STATUSES:
        await subscription_service.set_status(session, user_id, status)
        await session.commit()
    return RedirectResponse(f"/users/{user_id}", status_code=303)
