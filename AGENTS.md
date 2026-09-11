# AGENTS.md

Repository instructions for AI coding agents (Codex, Cursor, Copilot, Claude Code, …).

This file is the tool-agnostic version of [`CLAUDE.md`](./CLAUDE.md). Where they overlap,
they are intentionally identical; `CLAUDE.md` carries the longer explanations.

## 1. What this project is

**BotNews** — a Vietnamese SaaS Telegram bot (personal calendar, gold prices, crypto,
football, news, Gemini AI assistant) with a FastAPI web admin dashboard, sold as monthly
per-module subscriptions paid by Vietnamese bank transfer via SePay.

## 2. Stack — read this first

**Python 3.12 only.** There is no Node.js, TypeScript, React, Next.js, NestJS, or Prisma
in this repository, and none should be added. If your task brief mentions those, it does
not match this codebase — ask before proceeding.

- Bot: `python-telegram-bot` 21.9, long polling
- Web: FastAPI + Jinja2 + HTMX + Tailwind CDN + Chart.js (server-rendered, no SPA)
- Jobs: Celery + Beat on Redis
- Data: PostgreSQL 16 via SQLAlchemy 2.0 async (`asyncpg`), migrations by Alembic
- Cache/dedup/quota: Redis 7

## 3. Commands

| Purpose | Command | Notes |
|---|---|---|
| Test | `.venv/bin/python -m pytest -q` | 76 tests, ~1.3s, all pure |
| Lint | `.venv/bin/ruff check .` | **ruff is not installed** — `uv pip install ruff` first |
| Format check | `.venv/bin/ruff format --check .` | same caveat |
| Typecheck | *(none exists)* | do not invent one |
| Build | *(none exists)* | plain Python |
| Migrate | `.venv/bin/alembic upgrade head` | |
| New migration | `.venv/bin/alembic revision --autogenerate -m "..."` | always review output |
| Dev up | `bash scripts/dev_start.sh` | non-Docker local stack |
| Dev down | `bash scripts/dev_stop.sh` | `--all` also stops pg/redis |
| Docker dev | `docker compose up -d` | |
| Docker prod | `docker compose -f docker-compose.prod.yml up -d` | nginx + certbot |
| Env self-check | `python scripts/check_setup.py` | config + redis + postgres |
| Create admin | `python scripts/init_admin.py` | reads `ADMIN_PASSWORD` env or prompts |

Before reporting work as done: run the tests, and run ruff if you installed it. Say
plainly which of the two you actually ran.

## 4. Layering

```
core → models → repositories → services → {bot, web, worker}
                                integrations ↗
```

- `repositories/` — ORM queries only. `flush()`, never `commit()`. No business rules.
- `services/` — business logic. Caller commits (except the few bot-facing helpers that
  open their own `AsyncSessionLocal` and commit — those are marked in the file).
- `integrations/` — outbound HTTP only, via `BaseAdapter` (retry + Redis cache + stale).
- Never import `bot`/`web`/`worker` from `core`, `models`, `repositories`, `services`.

## 5. Code style — match what exists

- Vietnamese docstrings/comments, English identifiers, Vietnamese user-facing text.
- 100-col lines, ruff `E,F,I,UP,B` (`B008` ignored), Python 3.12 syntax.
- `str | None` / `list[dict]`, never `Optional`/`List`.
- SQLAlchemy 2.0 `Mapped[...]` + `mapped_column(...)`; `DateTime(timezone=True)`;
  `JSONB` for flexible fields; `flag_modified()` after in-place JSONB mutation.
- Store UTC, render local. All conversions via `app/core/timeutils.py`.
- Celery: `def task()` wrapping `asyncio.run(_run())`, explicit `name=`, registered in
  `include=[...]` and (if periodic) `beat_schedule` in `app/worker/celery_app.py`.
- Outbound Telegram from workers only via `send_message_task.delay` / `send_photo_task.delay`.
- Gate bot features with `@require_active` / `@require_module("key")`.
- Guard repeated alerts with `should_alert(key, ttl)` from `app/core/dedup.py`.
- Constants (module keys, products, prices, coins, leagues, news categories) live in
  `app/core/constants.py` — one source of truth.
- Config only through `app/core/config.py::Settings`; add new keys to `.env.example` too.

## 6. Do not

- Do not modify `.env` (real secrets) or commit it.
- Do not `git add -A` — `celerybeat-schedule` is untracked and not gitignored.
- Do not delete `app/web/static/` (mounted at import; app won't start without it).
- Do not add npm/JS build tooling.
- Do not add DB or network calls to `tests/` — the suite is pure by design.
- Do not change a model without an Alembic migration; keep the revision chain linear
  (current head: `d6f8b0c2e4a7`).
- Do not read `os.environ` directly in app code.

## 7. Commit / PR

- Commit messages follow the existing log: `docs: ...`, `feat: ...`, short and Vietnamese
  or English, one logical change per commit.
- Branch off `main`; do not commit or push unless explicitly asked.

## 8. Further reading

- [`docs/architecture.md`](docs/architecture.md) — components, data flow, risks
- [`docs/database.md`](docs/database.md) — schema, indexes, migrations
- [`docs/api.md`](docs/api.md) — HTTP routes, webhook, bot commands, Celery tasks
- [`docs/development.md`](docs/development.md) — setup, workflows, troubleshooting
- [`docs/phases/`](docs/phases/) and [`IMPLEMENTATION_ROADMAP.md`](IMPLEMENTATION_ROADMAP.md)
  — historical plan; treat as intent, not as current truth
- [`docs/superpowers/specs/`](docs/superpowers/specs/) — per-feature design notes
