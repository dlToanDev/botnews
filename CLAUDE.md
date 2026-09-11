# CLAUDE.md — BotNews

Instructions for AI agents working in this repository. Read this before touching code.

## ⚠️ Stack reality check

This project is **Python**, not TypeScript. There is **no Next.js, no React, no NestJS,
no Prisma, no `package.json`, no `node_modules`** anywhere in the tree. If a task
description assumes that stack, stop and confirm with the user before writing code.

Actual stack:

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Telegram bot | `python-telegram-bot` 21.9 (long polling) |
| Web admin | FastAPI 0.115 + Jinja2 templates + HTMX + Tailwind (CDN) + Chart.js |
| Background jobs | Celery 5.4 + Celery Beat, Redis broker |
| ORM | SQLAlchemy 2.0 async (`asyncpg`) — **not Prisma** |
| Migrations | Alembic 1.14 |
| Database | PostgreSQL 16 |
| Cache / dedup / quota | Redis 7 |
| Packaging | `requirements.txt` + `pyproject.toml` (ruff + pytest config only) |

## Project shape

One codebase, five runtime processes sharing `app/`:

```
app/bot/      Telegram long-polling process  → python -m app.bot.main
app/web/      FastAPI admin dashboard        → uvicorn app.web.main:app
app/worker/   Celery worker                  → celery -A app.worker.celery_app worker
app/worker/   Celery beat (same module)      → celery -A app.worker.celery_app beat
```

Shared layers, in dependency order (never invert these):

```
app/core/          config, database engine, redis, security, timeutils, constants, dedup
app/models/        SQLAlchemy declarative models
app/repositories/  data access — pure SQL/ORM, no business rules, NEVER commits
app/services/      business logic; the caller usually commits
app/integrations/  outbound HTTP adapters (CoinGecko, PNJ gold, football, RSS, Gemini)
app/bot/ app/web/ app/worker/   entrypoints + presentation
```

**Rule: `repositories` and `services` must not import from `bot`, `web`, or `worker`.**

## Commands

```bash
# Tests (76 tests, all pure — no DB, no network, no Telegram)
.venv/bin/python -m pytest -q

# Lint — ruff is CONFIGURED in pyproject.toml but NOT INSTALLED.
# Install it before claiming a lint pass:  uv pip install ruff  (or pip install ruff)
.venv/bin/ruff check .
.venv/bin/ruff format --check .

# There is NO typecheck command and no mypy config. Do not invent one.
# There is NO build step — Python source runs directly.

# Migrations
.venv/bin/alembic upgrade head
.venv/bin/alembic revision --autogenerate -m "short message"
.venv/bin/alembic current

# Local dev stack (no Docker; expects ~/.local/postgres and ~/.local/redis)
bash scripts/dev_start.sh          # starts postgres, redis, bot, web, worker, beat
bash scripts/dev_stop.sh           # stops app processes; --all also stops infra
tail -f logs/{bot,web,worker,beat}.log

# Docker
docker compose up -d                                   # dev
docker compose -f docker-compose.prod.yml up -d        # prod (nginx + certbot)
docker compose run --rm -e ADMIN_PASSWORD='...' web python scripts/init_admin.py
docker compose run --rm bot python scripts/check_setup.py
```

## Conventions actually used in this codebase

Follow these; they are consistent across every file.

- **Docstrings and comments are in Vietnamese.** Code identifiers are English.
  Keep writing them in Vietnamese — do not switch the codebase to English.
- **User-facing strings are Vietnamese**, formatted for Telegram Markdown
  (`parse_mode="Markdown"`) or Jinja templates.
- Line length **100** (`[tool.ruff] line-length = 100`), target `py312`.
- Ruff rules enabled: `E, F, I, UP, B`; `B008` ignored (FastAPI `Depends()` in defaults).
- **Modern typing**: `str | None`, `list[dict]`, `dict[str, int]`. No `Optional`, no `List`.
- **Models**: SQLAlchemy 2.0 `Mapped[...]` / `mapped_column(...)` style only.
  Timestamps are `DateTime(timezone=True)` with `server_default=func.now()`.
  Flexible fields use `JSONB`.
- **Time**: everything in the DB is UTC. Convert at the edges with `app/core/timeutils.py`
  (`now_utc`, `now_local`, `to_local`, `local_day_bounds_utc`, `fmt_local`).
  `settings.TIMEZONE` is `Asia/Ho_Chi_Minh`.
  When mutating a `JSONB` column in place, call `flag_modified(obj, "field")` —
  see `app/services/settings_service.py`.
- **Repositories** end with `await session.flush()`, never `commit()`.
  The router / service / task that owns the request commits.
- **Sessions**:
  - web → `Depends(get_session)` from `app.core.database`
  - bot → `async with AsyncSessionLocal() as session:`
  - Celery task → `async with worker_session() as session:` from `app.worker.db`
    (a fresh `NullPool` engine per task, because each task runs its own `asyncio.run`).
- **Celery tasks** are sync wrappers around an `async def _run()` via `asyncio.run(_run())`,
  and they are always registered with an explicit
  `@celery_app.task(name="app.worker.tasks.<mod>.<fn>")`. Add new task modules to the
  `include=[...]` list in `app/worker/celery_app.py` or they will never be discovered.
- **Sending Telegram messages from a task** goes through `send_message_task.delay(...)` /
  `send_photo_task.delay(...)` — never call the Bot API inline in a polling task.
- **Feature gating**: bot handlers use `@require_active` or `@require_module("<key>")`
  from `app/bot/decorators.py`. Module keys live in `MODULE_KEYS` in `app/core/constants.py`.
- **Alert de-duplication** goes through `app/core/dedup.py::should_alert(key, ttl)`
  (Redis `SET NX EX`). Always use it in a polling task that sends messages.
- **External API calls** subclass `BaseAdapter` in `app/integrations/base.py` to get
  retry + Redis cache + stale fallback. Do not call `httpx` directly from a service.
- **Bot commands are bilingual**: every command has an unaccented Vietnamese alias
  declared in `VI_ALIAS` in `app/bot/main.py`, registered via `_cmd("english")`.
  `VI_ALIAS` is the single source of truth for both handlers and the Telegram menu.
- **Audit logging**: state changes write a row via `log_repo.write(...)` with a stable
  `action` string (`order_paid`, `module_toggle`, `plan_extend`, …).

## Hard rules

1. **Never edit `.env`.** It contains live secrets (bot token, DB password, API keys).
2. **Never commit** `.env`, `celerybeat-schedule`, `logs/`, or `__pycache__/`.
   `celerybeat-schedule` is currently untracked but *not* in `.gitignore` — do not `git add -A`.
3. `app/web/static/` must exist — `app/web/main.py` mounts it at import time and the app
   will not start without it. It holds only `.gitkeep`.
4. **Every model change needs an Alembic migration.** Autogenerate, then read the
   generated file — it frequently misses server defaults and JSONB defaults, and the
   existing migrations in `alembic/versions/` backfill with explicit
   `server_default` + a later `alter_column` to drop it. Follow that pattern.
   The chain is linear with a single head (`d6f8b0c2e4a7`); keep it linear.
5. **Tests must stay pure.** `tests/` has no conftest, no fixtures, no DB, no network.
   New tests should test formatting/parsing/pure helpers the same way. If you need
   integration coverage, say so rather than adding network calls to the suite.
6. Do not add a JS build step, bundler, or npm dependency. The admin UI is deliberately
   server-rendered Jinja + HTMX with CDN Tailwind.
7. Config values go in `app/core/config.py` (`Settings`, pydantic-settings) and
   `.env.example` — never read `os.environ` directly in app code.
8. Shared constants (module keys, packages, prices, coin ids, league codes, news
   categories) belong in `app/core/constants.py`. Do not duplicate them in handlers.

## Known landmines

Read `docs/architecture.md` § "Problems" for the full list. The ones most likely to
bite you while editing:

- `app/worker/tasks/news_push.py::_link_hash` uses Python's builtin `hash()`, which is
  salted per process (`PYTHONHASHSEED`). Dedup keys therefore change on every worker
  restart. Do not copy this pattern; use `hashlib` if you touch it.
- `app/bot/handlers/payment.py::buy_menu` advertises "Full 4 dịch vụ: 70.000đ" while
  `app/core/constants.py` defines `FULL_PRICE = 80_000` for 5 services. The QR amount
  comes from constants, so the displayed text is wrong.
- `buy_menu` / `buy_callback` are **not** decorated with `@require_active`, so a banned
  or expired user can still create orders.
- `user_repo.search()` applies `limit=100` in SQL, and `users.py` filters by status
  *afterwards in Python* — a status filter can silently return fewer rows than exist.
- There is no rate limiting on `POST /login` and no CSRF token on admin forms
  (the session cookie is `SameSite=Lax`, which is the only mitigation).
- `admins.totp_secret` exists in the schema but 2FA is not implemented anywhere.

## Where things live

| Task | File |
|---|---|
| Add a bot command | `app/bot/main.py` (`VI_ALIAS`, `_MENU_ITEMS`, handler registration) + `app/bot/handlers/` |
| Add a scheduled job | `app/worker/tasks/<name>.py` + `include` + `beat_schedule` in `app/worker/celery_app.py` |
| Add an admin page | `app/web/routers/<name>.py` + `app/web/templates/<name>.html` + `include_router` in `app/web/main.py` + nav in `templates/base.html` |
| Add a feature module | `MODULE_KEYS`/`MODULE_LABELS`/`PRODUCTS` in `app/core/constants.py`, then `@require_module` |
| Add an external data source | `app/integrations/<name>.py` subclassing `BaseAdapter` |
| Change a DB table | `app/models/*.py` + `alembic revision --autogenerate` |

See also: `docs/architecture.md`, `docs/database.md`, `docs/api.md`, `docs/development.md`.
