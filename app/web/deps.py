"""Dependencies & tiện ích dùng chung cho Web Admin."""
from fastapi import Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import decode_session_token
from app.models.admin import Admin
from app.repositories import admin_repo

templates = Jinja2Templates(directory="app/web/templates")

from app.core.timeutils import fmt_local  # noqa: E402


def _localtime(dt, pattern: str = "%H:%M %d/%m/%Y") -> str:
    return fmt_local(dt, pattern) if dt else "—"


templates.env.filters["localtime"] = _localtime

COOKIE_NAME = "session"


class AuthRedirect(Exception):
    """Ném ra khi chưa đăng nhập → main.py redirect tới /login."""


async def get_current_admin(
    request: Request, session: AsyncSession = Depends(get_session)
) -> Admin:
    token = request.cookies.get(COOKIE_NAME)
    username = decode_session_token(token) if token else None
    if not username:
        raise AuthRedirect()
    admin = await admin_repo.get_by_username(session, username)
    if admin is None:
        raise AuthRedirect()
    return admin
