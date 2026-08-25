"""Router: gia hạn gói cước (+30 / +365 ngày)."""
from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.admin import Admin
from app.services import subscription_service
from app.web.deps import get_current_admin

router = APIRouter(prefix="/users")


@router.post("/{user_id}/extend")
async def extend(
    user_id: int,
    days: int = Form(...),
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    if days in (30, 365):
        await subscription_service.extend_plan(session, user_id, days)
        await session.commit()
    return RedirectResponse(f"/users/{user_id}", status_code=303)
