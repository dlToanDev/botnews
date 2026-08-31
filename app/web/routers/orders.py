"""Router: admin xem đơn hàng (đối soát thanh toán)."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.admin import Admin
from app.repositories import order_repo
from app.web.deps import get_current_admin, templates

router = APIRouter(prefix="/orders")


@router.get("")
async def list_orders(
    request: Request,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    orders = await order_repo.list_recent(session, limit=200)
    return templates.TemplateResponse(
        "orders.html",
        {"request": request, "admin": admin, "orders": orders},
    )
