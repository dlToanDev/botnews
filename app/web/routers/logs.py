"""Router: xem Logs hoạt động."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.admin import Admin
from app.models.log import Log
from app.web.deps import get_current_admin, templates

router = APIRouter(prefix="/logs")


@router.get("")
async def list_logs(
    request: Request,
    action: str | None = None,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Log).order_by(desc(Log.created_at)).limit(200)
    if action:
        stmt = stmt.where(Log.action == action)
    rows = (await session.execute(stmt)).scalars().all()
    return templates.TemplateResponse(
        "logs.html",
        {"request": request, "admin": admin, "logs": rows, "action": action or ""},
    )
