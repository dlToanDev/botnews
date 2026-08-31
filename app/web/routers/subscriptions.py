"""Router: quản lý gói cước (gia hạn / hủy / đổi tên gói)."""
from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import PACKAGES_BY_KEY, PLANS
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
    # Chấp nhận số ngày tùy ý (1..3650) — nút nhanh +30/+365 hoặc ô nhập tay.
    if 1 <= days <= 3650:
        await subscription_service.extend_plan(session, user_id, days)
        await session.commit()
    return RedirectResponse(f"/users/{user_id}", status_code=303)


@router.post("/{user_id}/cancel")
async def cancel(
    user_id: int,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    await subscription_service.cancel_plan(session, user_id)
    await session.commit()
    return RedirectResponse(f"/users/{user_id}", status_code=303)


@router.post("/{user_id}/packages/{pkg}/apply")
async def apply_package(
    user_id: int,
    pkg: str,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    if pkg in PACKAGES_BY_KEY:
        await subscription_service.apply_package(session, user_id, pkg)
        await session.commit()
    return RedirectResponse(f"/users/{user_id}", status_code=303)


@router.post("/{user_id}/plan")
async def change_plan(
    user_id: int,
    plan: str = Form(...),
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    if plan in PLANS:
        await subscription_service.set_plan_name(session, user_id, plan)
        await session.commit()
    return RedirectResponse(f"/users/{user_id}", status_code=303)
