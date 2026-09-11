# Development guide — BotNews

How to set up, run, test and change this repository. Python 3.12 only — there is no
Node.js toolchain here.

Related: [`docs/SETUP.md`](SETUP.md) (creating the Telegram bot with @BotFather),
[`docs/DEPLOYMENT.md`](DEPLOYMENT.md), [`docs/DEPLOY_SAME_VPS.md`](DEPLOY_SAME_VPS.md),
[`docs/DEPLOYMENT_GCLOUD.md`](DEPLOYMENT_GCLOUD.md).

---

## 1. Prerequisites

- Python 3.12
- PostgreSQL 16 and Redis 7 — either via Docker, or installed locally
- A Telegram bot token from @BotFather (see `docs/SETUP.md`)
- Optional: `API_FOOTBALL_KEY`, `FOOTBALL_DATA_KEY`, `NEWSAPI_KEY`, `GEMINI_API_KEY`,
  SePay credentials. Missing keys disable the corresponding feature rather than crashing —
  only `BOT_TOKEN` and `DATABASE_URL` are mandatory.

## 2. Setup

### Option A — Docker (simplest)

```bash
cp .env.example .env
$EDITOR .env                       # at minimum: BOT_TOKEN, POSTGRES_PASSWORD, JWT_SECRET
docker compose up -d --build
docker compose run --rm web alembic upgrade head
docker compose run --rm -e ADMIN_PASSWORD='a-strong-password' web python scripts/init_admin.py
docker compose run --rm bot python scripts/check_setup.py    # verifies config + redis + pg
```

Admin console → http://127.0.0.1:8000 (dev compose binds to localhost only).
Postgres is on host port `15432`, Redis on `16380`, to avoid clashing with local installs.
Inside the Docker network they remain `5432` / `6379`, which is what `.env` must use.

### Option B — local venv (what `scripts/dev_start.sh` expects)

```bash
uv venv .venv                          # or: python3.12 -m venv .venv
uv pip install -r requirements.txt     # or: .venv/bin/pip install -r requirements.txt
uv pip install ruff                    # NOT in requirements.txt — see §4

cp .env.example .env
# point DATABASE_URL/REDIS_URL at localhost, e.g.
#   DATABASE_URL=postgresql+asyncpg://botadmin:pass@localhost:5432/botnews
#   REDIS_URL=redis://localhost:6379/0
#   CELERY_BROKER_URL=redis://localhost:6379/1
#   CELERY_RESULT_BACKEND=redis://localhost:6379/2

export PYTHONPATH=$PWD
.venv/bin/alembic upgrade head
ADMIN_PASSWORD='a-strong-password' .venv/bin/python scripts/init_admin.py
```

> `scripts/dev_start.sh` assumes Postgres at `~/.local/postgres` and Redis at
> `~/.local/redis` (a user-local, non-Docker install). If yours live elsewhere, start them
> yourself and launch the four app processes manually (§3).

## 3. Running

### Via the dev script

```bash
bash scripts/dev_start.sh        # postgres, redis, bot, web, worker, beat
tail -f logs/web.log logs/bot.log logs/worker.log logs/beat.log
bash scripts/dev_stop.sh         # stops app processes, keeps infra
bash scripts/dev_stop.sh --all   # also stops postgres + redis
```

Logs go to `logs/*.log`, PIDs to `logs/pids/`. Both are gitignored.

### Manually (four terminals)

```bash
export PYTHONPATH=$PWD

.venv/bin/python -m app.bot.main
.venv/bin/uvicorn app.web.main:app --reload --host 127.0.0.1 --port 8000
.venv/bin/celery -A app.worker.celery_app worker --loglevel=info --concurrency=2
.venv/bin/celery -A app.worker.celery_app beat  --loglevel=info
```

Only one `bot` process may run at a time — Telegram long polling rejects a second
`getUpdates` consumer with a 409 conflict.

### Docker

```bash
docker compose up -d                                # dev
docker compose logs -f web worker
docker compose -f docker-compose.prod.yml up -d     # prod: + nginx + certbot, no host ports
docker compose -f docker-compose.coexist.yml up -d  # when sharing a VPS with other stacks
```

## 4. Quality commands

| What | Command | Status |
|---|---|---|
| Tests | `.venv/bin/python -m pytest -q` | ✅ 76 pass in ~1.3s |
| Lint | `.venv/bin/ruff check .` | ⚠️ ruff is configured in `pyproject.toml` but **not installed** and **not in `requirements.txt`** — install it first |
| Format | `.venv/bin/ruff format .` | same caveat |
| Typecheck | — | **none exists**; no mypy/pyright config. Don't claim one ran |
| Build | — | **none**; Python runs from source |
| CI | — | **none**; there is no `.github/` directory |

Ruff config (`pyproject.toml`): line length 100, target `py312`, rules `E, F, I, UP, B`,
`B008` ignored (FastAPI `Depends()` in argument defaults is idiomatic).

Pytest config: `asyncio_mode = "auto"`, `testpaths = ["tests"]`.

## 5. Testing

### What exists

76 tests in `tests/`, all **pure**: no database, no network, no Telegram runtime, no
`conftest.py`, no fixtures. They import functions directly and assert on return values.

| File | Covers |
|---|---|
| `test_calendar.py` | `local_month_bounds_utc`, `build_month_grid` |
| `test_crypto.py` | CoinGecko `_normalize`, display formatting |
| `test_crypto_digest.py` | `format_price_digest`, `resolve_notify`, `select_coins` |
| `test_football.py` | `filter_by_teams`, `format_results_digest` |
| `test_gold.py` | `parse_times`, `effective_times`, `format_gold_prices` |
| `test_integrations.py` | `GoldAdapter._to_vnd`, `match_keywords` |
| `test_menu.py` | inline-menu builders, `toggle`, `hhmm_to_display` |
| `test_news.py` | `_extract_image`, `_parse_feed`, `_passes_filter`, `_news_caption` |
| `test_schedule_parse.py` | natural-language schedule parsing |
| `test_security.py` | bcrypt round-trip, JWT encode/decode |

Keep new tests in this style. If you need DB or HTTP coverage, add it deliberately with a
fixture layer — don't sneak network calls into the existing suite.

### What is missing

No test touches any of these, in rough priority order:

1. **`payment_service.fulfill_order` idempotency** — the money path. Pure enough to test
   with a fake session or an in-memory SQLite/pg session.
2. **`payment_service.parse_order_code`** — a regex; trivially testable, currently untested.
3. **The SePay webhook handler** — auth rejection, `transferType` filtering, underpayment,
   duplicate delivery, unknown code. Testable with FastAPI `TestClient`.
4. **Auth** — `get_current_admin` redirect behaviour, expired/forged token handling.
5. **Every repository function** — no DB-backed tests exist at all.
6. **Every Celery task** — `_run()` bodies are async and mockable but untested.
7. **`subscription_service`** — `extend_plan` / `cancel_plan` / `apply_package` semantics.
8. **`schedule_repo.list_due_reminders` / `list_due_started`** window logic, including the
   15-minute grace window.
9. **Timezone edge cases** beyond the month-bounds tests (DST is not a concern for
   `Asia/Ho_Chi_Minh`, but UTC-boundary digests are).

## 6. Common workflows

### Add a bot command

1. Add the English key → unaccented Vietnamese alias in `VI_ALIAS` (`app/bot/main.py`).
2. Add it to `_MENU_ITEMS` if it should appear in the Telegram menu button.
3. Write the handler in `app/bot/handlers/`, decorated with `@require_active` or
   `@require_module("key")`.
4. Register it: `app.add_handler(CommandHandler(_cmd("english"), module.handler))`.
5. Add a pure unit test for any formatting/parsing helper you introduced.

### Add a scheduled job

1. Create `app/worker/tasks/<name>.py` with an `async def _run()` and a sync
   `@celery_app.task(name="app.worker.tasks.<name>.<fn>")` wrapper calling `asyncio.run(_run())`.
2. Use `async with worker_session() as session:` for DB access.
3. Resolve recipients with `module_repo.eligible_users(session, "<module>")`.
4. Guard sends with `should_alert(key, ttl)`.
5. Enqueue with `send_message_task.delay(...)` — never send inline.
6. Add the module to `include=[...]` **and** an entry in `beat_schedule` in
   `app/worker/celery_app.py`. Restart both worker and beat.

### Add an admin page

1. New router in `app/web/routers/<name>.py` with `Depends(get_current_admin)` and
   `Depends(get_session)`.
2. Template in `app/web/templates/<name>.html` extending `base.html`.
3. `app.include_router(...)` in `app/web/main.py`.
4. Add a nav entry to the `nav` list at the top of `templates/base.html`.
5. POST handlers: mutate via a service, `await session.commit()`, return
   `RedirectResponse(..., status_code=303)`.

### Change the schema

```bash
$EDITOR app/models/<model>.py
# if it is a NEW model, also add it to app/models/__init__.py
.venv/bin/alembic revision --autogenerate -m "short message"
$EDITOR alembic/versions/<new>.py      # ALWAYS review
.venv/bin/alembic upgrade head
```

For a NOT NULL column on an existing table, follow the repo's pattern: add with
`server_default`, then `alter_column(..., server_default=None)`. Keep the revision chain
linear (head: `d6f8b0c2e4a7`). See [`docs/database.md`](database.md) § Migrations.

### Add an external data source

Subclass `BaseAdapter` in `app/integrations/<name>.py` with a `name`, a `ttl`, and an
`async def fetch()`. You get retry, Redis caching and stale fallback for free. Add any new
API key to `Settings` in `app/core/config.py` **and** to `.env.example`.

## 7. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `RuntimeError: Directory 'app/web/static' does not exist` | `app/web/main.py` mounts it at import. Recreate it: `mkdir -p app/web/static && touch app/web/static/.gitkeep` |
| Bot exits with a 409 conflict | Two `bot` processes polling. `bash scripts/dev_stop.sh`, or stop the Docker `bot` service |
| Task raises "attached to a different loop" | You used `AsyncSessionLocal` inside a Celery task. Use `worker_session()` from `app/worker/db.py` |
| JSONB edit doesn't persist | Mutated the list/dict in place without `flag_modified(obj, "column")` |
| Beat fires nothing | Task module missing from `include=[...]`, or beat not restarted after editing `beat_schedule` |
| Stale `celerybeat-schedule` | Beat's local shelf file at the repo root. Safe to delete while beat is stopped. It is **untracked and not gitignored** — never `git add -A` |
| Digests arrive at the wrong minute | Times are compared against `now_local()` in `Asia/Ho_Chi_Minh`; the DB stores UTC. Check `TIMEZONE` in `.env` |
| News re-pushes old articles after a restart | Known bug: `_link_hash` uses salted builtin `hash()` — see `docs/architecture.md` § Problems |
| `alembic upgrade` can't connect | `alembic.ini`'s `sqlalchemy.url` is a placeholder; the real URL comes from `.env` via `app.core.config`. Check `DATABASE_URL` and that `PYTHONPATH` includes the repo root |
| `ruff: command not found` | It is configured but not installed: `uv pip install ruff` |
| Admin login always bounces to `/login` | No admin row (`scripts/init_admin.py`), or `JWT_SECRET` changed since the cookie was issued |
| Payments never activate | Webhook not reachable, wrong `Authorization: Apikey`, or the user edited the transfer memo. Check `/orders` and `/logs?action=order_unmatched` |

## 8. Secrets and files never to commit

`.env` (real bot token, DB password, API keys), `logs/`, `celerybeat-schedule`,
`__pycache__/`, `.venv/`, `backups/`, `pgdata/`, `redisdata/`.

`.gitignore` covers most of these; **`celerybeat-schedule` is not covered** — stage files
explicitly rather than using `git add -A`.

## 9. Deployment pointers

- `docker-compose.prod.yml` — 7 services, resource limits, log rotation, no host ports for
  postgres/redis/web; nginx is the only ingress.
- `nginx/conf.d/admin.conf` — replace every `admin.yourdomain.com` before deploying; a
  `default_server` block returns 444 for unknown Host headers; an optional IP allowlist is
  commented out near the bottom.
- `scripts/init_letsencrypt.sh` — bootstraps TLS (self-signed → nginx up → real cert).
- `scripts/backup_db.sh` / `scripts/restore_db.sh` — nightly dump (keeps 7) and restore.
  Restore has not been exercised here; test it before relying on it.
