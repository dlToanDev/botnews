"""Entrypoint Web Admin Dashboard (FastAPI + Jinja2 + HTMX)."""
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.core.logging import setup_logging
from app.web.deps import AuthRedirect
from app.web.routers import auth, dashboard, logs, modules, subscriptions, users

setup_logging()

app = FastAPI(title="BotNews Admin", docs_url=None, redoc_url=None, openapi_url=None)

app.mount("/static", StaticFiles(directory="app/web/static"), name="static")


@app.exception_handler(AuthRedirect)
async def _auth_redirect(request: Request, exc: AuthRedirect) -> RedirectResponse:
    return RedirectResponse("/login", status_code=303)


app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(users.router)
app.include_router(modules.router)
app.include_router(subscriptions.router)
app.include_router(logs.router)
