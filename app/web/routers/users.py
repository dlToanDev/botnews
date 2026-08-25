"""Router: quản lý User."""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import MODULE_KEYS, MODULE_LABELS, USER_STATUSES
from app.core.database import get_session
from app.models.admin import Admin
from app.repositories import user_repo
from app.services import subscription_service
from app.web.deps import get_current_admin, templates

router = APIRouter(prefix="/users")


@router.get("")
async def list_users(
    request: Request,
    q: str | None = None,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    users = await user_repo.search(session, q=q)
    return templates.TemplateResponse(
        "users.html",
        {"request": request, "admin": admin, "users": users, "q": q or ""},
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
    return templates.TemplateResponse(
        "user_detail.html",
        {
            "request": request,
            "admin": admin,
            "user": user,
            "modules": module_list,
            "statuses": USER_STATUSES,
        },
    )


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
