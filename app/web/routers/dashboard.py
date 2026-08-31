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
    by_plan = await user_repo.count_by_plan(session)
    growth = await user_repo.count_new_by_month(session, months=6)
    expiring = await user_repo.expiring_soon(session, days=7)

    total = sum(by_status.values())
    module_stats = [
        {"key": k, "label": MODULE_LABELS[k], "count": by_module.get(k, 0)}
        for k in MODULE_KEYS
    ]

    # Dữ liệu gọn cho Chart.js (đổ thẳng vào |tojson ở template).
    charts = {
        "status": {
            "labels": ["Active", "Expired", "Banned"],
            "data": [
                by_status.get("active", 0),
                by_status.get("expired", 0),
                by_status.get("banned", 0),
            ],
        },
        "modules": {
            "labels": [m["label"] for m in module_stats],
            "data": [m["count"] for m in module_stats],
        },
        "plans": {
            "labels": list(by_plan.keys()) or ["free"],
            "data": list(by_plan.values()) or [0],
        },
        "growth": {
            "labels": list(growth.keys()),
            "data": list(growth.values()),
        },
    }

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
            "charts": charts,
            "expiring": expiring,
        },
    )
