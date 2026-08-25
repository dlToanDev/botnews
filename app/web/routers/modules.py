"""Router: bật/tắt module (Feature Toggle) — trả partial cho HTMX."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import MODULE_LABELS
from app.core.database import get_session
from app.models.admin import Admin
from app.repositories import module_repo
from app.services import subscription_service
from app.web.deps import get_current_admin, templates

router = APIRouter(prefix="/users")


@router.post("/{user_id}/modules/{key}/toggle")
async def toggle_module(
    request: Request,
    user_id: int,
    key: str,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    current = await module_repo.get(session, user_id, key)
    new_state = not (current.is_enabled if current else False)
    await subscription_service.set_module(session, user_id, key, new_state)
    await session.commit()
    return templates.TemplateResponse(
        "_module_row.html",
        {
            "request": request,
            "user_id": user_id,
            "mod": {"key": key, "label": MODULE_LABELS.get(key, key), "enabled": new_state},
        },
    )
