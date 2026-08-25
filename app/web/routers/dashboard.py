"""Router: Dashboard tổng quan."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import MODULE_KEYS, MODULE_LABELS
from app.core.database import get_session
from app.models.admin import Admin
from app.repositories import module_repo, user_repo
from app.web.deps import get_current_admin, templates

router = APIRouter()


@router.get("/")
async def dashboard(
    request: Request,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    by_status = await user_repo.count_by_status(session)
    by_module = await module_repo.count_enabled_by_module(session)
    total = sum(by_status.values())
    module_stats = [
        {"key": k, "label": MODULE_LABELS[k], "count": by_module.get(k, 0)}
        for k in MODULE_KEYS
    ]
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "admin": admin,
            "total": total,
            "active": by_status.get("active", 0),
            "expired": by_status.get("expired", 0),
            "banned": by_status.get("banned", 0),
            "module_stats": module_stats,
        },
    )
