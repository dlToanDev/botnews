# Architecture — BotNews

Describes the system **as it exists today** in this repository.

> **Stack note.** This is a Python 3.12 monorepo. There is no Next.js, React, TypeScript,
> NestJS or Prisma anywhere in the tree, and no `package.json`. The web admin is
> server-rendered Jinja2 + HTMX with Tailwind and Chart.js loaded from CDNs.

---

## 1. Overview

BotNews is a Vietnamese SaaS Telegram bot with a web admin console. Users subscribe to
individual feature modules (gold prices, crypto, football, news, AI assistant) for 30 days
at a time, paying by bank transfer through SePay. A personal calendar module is free for
everyone. Admins manage users, modules, packages and system-wide notification settings
through the dashboard.

## 2. Processes

One codebase (`app/`), five long-running processes, all built from the same `Dockerfile`:

| Process | Command | Responsibility |
|---|---|---|
| `bot` | `python -m app.bot.main` | Telegram long polling, all user interaction |
| `web` | `uvicorn app.web.main:app --workers 2` | Admin dashboard + SePay webhook |
| `worker` | `celery -A app.worker.celery_app worker --concurrency=2` | Executes tasks |
| `beat` | `celery -A app.worker.celery_app beat` | Periodic schedule trigger |
| infra | `postgres:16-alpine`, `redis:7-alpine` | State and broker/cache |

Production (`docker-compose.prod.yml`) adds `nginx` (TLS termination, reverse proxy to
`web:8000`) and `certbot` (Let's Encrypt renewal). In prod, Postgres/Redis/web expose no
host ports; nginx is the only ingress.

```
                    Telegram API
                         │  long polling
                    ┌────▼─────┐
    Admin ──HTTPS──►│  nginx   │──►│ web (FastAPI) │
                    └──────────┘   └───┬───────────┘
    SePay ──webhook────────────────────┘   │
                                            │
        ┌───────────────────┬───────────────┼──────────────┐
        │                   │               │              │
   ┌────▼────┐        ┌─────▼─────┐   ┌─────▼─────┐  ┌─────▼─────┐
   │   bot   │        │  worker   │   │   beat    │  │ postgres  │
   └────┬────┘        └─────┬─────┘   └─────┬─────┘  └───────────┘
        │                   │               │
        └───────────────────┴───────────────┴──────► redis
                                     (broker, cache, dedup, AI quota)
```

## 3. Layering

```
app/core/          config · database · redis_client · security · timeutils
                   constants · dedup · logging
app/models/        SQLAlchemy declarative models (source of truth for the schema)
app/repositories/  data access; flush() only, never commit()
app/services/      business logic; caller commits
app/integrations/  outbound HTTP adapters
app/bot/           Telegram handlers, keyboards, permission decorators
app/web/           FastAPI routers, Jinja templates, auth dependency
app/worker/        Celery app, per-task async session helper, task modules
```

Dependency direction is strictly downward. `repositories` and `services` never import
from `bot`, `web`, or `worker`.

### Session strategy (three different ones, deliberately)

| Caller | Helper | Why |
|---|---|---|
| web | `Depends(get_session)` → `AsyncSessionLocal` | pooled engine, `pool_size=10, max_overflow=20, pool_pre_ping` |
| bot | `async with AsyncSessionLocal()` | same pooled engine, single event loop |
| Celery task | `async with worker_session()` (`app/worker/db.py`) | each task calls `asyncio.run()`, so a fresh **NullPool** engine is created and disposed per task — a pooled engine cannot be shared across event loops |

## 4. Bot architecture (`app/bot/`)

- `main.py` builds the `Application` with `AIORateLimiter`, registers every handler, and
  in `post_init` publishes the command list + menu button to Telegram.
- **Bilingual commands.** `VI_ALIAS` maps each English command to an unaccented Vietnamese
  alias (`buy`→`muagoi`, `gold`→`vang`, …). It is the single source of truth for both
  `CommandHandler` registration (`_cmd()`) and the Telegram menu, so the two cannot drift.
  Per-coin (`/btc`, `/eth`, …) and per-league (`/epl`, `/bxhepl`, …) shortcuts are
  generated from `COIN_IDS` and `features.LEAGUE_CMDS`.
- **Handlers**: `start`, `menu` (hierarchical inline menu for buying + self-configuration),
  `payment` (SePay QR), `ai` (Gemini), `schedule` + `calendar_ui` (calendar, inline month
  grid), `features` (gold / crypto / football / news commands).
- **Authorization decorators** (`decorators.py`):
  - `@require_active` — resolves/creates the user, rejects `banned` and expired, stores
    `db_user_id` in `context.user_data`, writes a `command` audit log.
  - `@require_module("key")` — the same, plus requires the module enabled for that user.
- **Message handler ordering matters.** Reply-keyboard buttons are matched first (group 0
  regex), then calendar title capture (group 0), then football-team text input (group 1).
  Adding a broad `filters.TEXT` handler will break the menu.

## 5. Web admin (`app/web/`)

- FastAPI with OpenAPI/docs **disabled** (`docs_url=None, redoc_url=None, openapi_url=None`).
- Jinja2 templates in `app/web/templates/`, a custom `localtime` filter registered in
  `deps.py`. Static files mounted from `app/web/static/` (mount happens at import, so the
  directory must exist).
- HTMX is used for exactly one partial: the per-user module toggle
  (`POST /users/{id}/modules/{key}/toggle` → `_module_row.html`). Everything else is a
  classic form POST + 303 redirect.
- Auth: a `session` cookie holding an HS256 JWT (`sub` = admin username, 7-day expiry).
  `get_current_admin` decodes it and reloads the `Admin` row; failure raises `AuthRedirect`,
  which a global exception handler turns into a 303 to `/login`.
- `GET /healthz` is deliberately DB-free, for Docker/nginx health checks.

## 6. Background jobs (`app/worker/`)

Every task is a synchronous Celery function wrapping `asyncio.run(_run())`, with an
explicit task `name=`. Modules must be listed in `include=[...]` in `celery_app.py`.

Celery config: `timezone=Asia/Ho_Chi_Minh`, `enable_utc=True`,
`task_default_rate_limit="25/s"` (under Telegram's 30/s), `task_acks_late=True`,
`worker_prefetch_multiplier=1`.

Beat schedule:

| Job | Cadence | Task |
|---|---|---|
| Daily calendar digest | 07:00 | `daily_digest.send_daily_digest` |
| Schedule reminders | every minute | `schedule_reminder.check_reminders` |
| Expire overdue users | 00:05 | `expire_users.expire_overdue` |
| Crypto threshold alerts | every 2 min | `crypto_alert.poll_and_alert` |
| Gold threshold alerts | every 10 min | `gold_alert.poll_and_alert` |
| Gold digest | every minute | `gold_digest.poll_and_send` |
| Crypto digest | every minute | `crypto_digest.poll_and_send` |
| Football digest | every minute | `football_digest.poll_and_send` |
| Football live | every 2 min | `football_live.poll_and_alert` |
| News push | every 2 min | `news_push.poll_and_alert` |

The "every minute" digest tasks exist because users pick arbitrary `HH:MM` delivery times;
each run compares `now_local().strftime("%H:%M")` against each user's configured times.

**Fan-out pattern.** A polling task never sends directly. It resolves eligible users
(`module_repo.eligible_users(session, module_key)` — active, unexpired, module enabled),
checks Redis dedup, then enqueues `send_message_task.delay(...)` /
`send_photo_task.delay(...)`. `send_message_task` handles `RetryAfter` (retry with
`countdown`) and `Forbidden` (user blocked the bot → swallowed).

## 7. External integrations (`app/integrations/`)

All adapters extend `BaseAdapter`, which gives retry with backoff (3 attempts), a Redis
cache key `cache:<name>` with per-adapter TTL, and a `cache:<name>:stale` copy at 20× TTL
used as a fallback when the upstream fetch fails.

| Adapter | Source | Notes |
|---|---|---|
| `gold.py` | PNJ edge API | JSON; values in thousands VND, TTL 300s |
| `coingecko.py` / `crypto.py` | CoinGecko | prices in USD + VND, per-coin commands |
| `football_data.py` | football-data.org | standings + results, needs `FOOTBALL_DATA_KEY` |
| `football.py` | api-sports.io | live scores, needs `API_FOOTBALL_KEY` |
| `news.py` | VNExpress RSS (feedparser + BeautifulSoup) | 8 categories in `NEWS_CATEGORIES` |
| `gemini.py` | Google Gemini `generateContent` | not a `BaseAdapter` (no caching); raises `GeminiError` / `GeminiQuotaError` |

## 8. Subscription & payment flow

```
/muagoi → PRODUCTS catalog (single 20k / combo 40k / full 80k)
        → payment_service.create_order()   Order(status=pending, code="BOT" + 6 hex, TTL 15 min)
        → SePay VietQR image URL (amount + code pre-filled)
User transfers → SePay POST /api/sepay/webhook  (Authorization: Apikey <SEPAY_WEBHOOK_APIKEY>)
        → match order by code (payload field or regex over transfer content)
        → guards: transferType == "in", not already paid, amount >= order.amount
        → payment_service.fulfill_order(): enable order.modules, extend expires_at +30d,
          status=active, order.status=paid, audit log — idempotent
        → telegram_notify.send_message() confirmation (best-effort, errors swallowed)
```

Unmatched webhooks (`no_code`, `code_not_found`, `underpaid`) are written to `logs` with
`action="order_unmatched"` for manual reconciliation on `/orders`.

Two orthogonal concepts, easy to confuse:
- **`User.plan`** (`free` / `vip`) is a *label only*. It grants nothing.
- **`subscription_modules`** rows are what actually gate features.
- **`User.expires_at`** is the global validity window; `PACKAGES` (admin-side bundles) and
  `PRODUCTS` (bot-side purchasables) are two separate catalogs in `constants.py`.

## 9. Configuration

`app/core/config.py` (pydantic-settings, reads `.env`, `extra="ignore"`). Feature flags are
derived properties: `settings.payment_enabled` (needs account number + bank code),
`settings.ai_enabled` (needs Gemini key). Missing keys degrade features gracefully rather
than crashing — except `BOT_TOKEN` and `DATABASE_URL`, which are required.

---

## 10. Problems

### Architectural

1. **No API layer / no schemas.** `app/web/schemas/` exists but is empty. Routers talk to
   repositories and services directly and return HTML. Adding a mobile client or any
   external consumer means building an API tier from scratch.
2. **Three parallel notification-config systems.** Per-user `UserSettings` columns
   (`gold_times`, `crypto_times`, `crypto_notify_mode`, `crypto_coins`, `football_times`,
   `news_categories`), system-wide `system_settings` JSONB rows, and admin-side per-user
   overrides. Resolution logic (`effective_times`, `resolve_notify`, `effective_news_cats`)
   is spread across three services. This is the most likely source of future bugs.
3. **Four "every minute" beat jobs** each do a full eligible-user scan. Fine at current
   scale, linear in user count, and the cost is paid 1,440×/day per job whether or not
   anyone is scheduled for that minute. Gold digest short-circuits the API call; the others
   are less careful.
4. **`PACKAGES` vs `PRODUCTS` duplication.** Two overlapping bundle catalogs with different
   keys for the same modules.
5. **No transaction boundary discipline in the webhook.** `fulfill_order` mutates modules,
   user expiry and order status, then the router commits — correct today, but there is no
   explicit `begin()` block, and `_log_unmatched` commits separately.
6. **Bot writes settings through `telegram_id`, admin through `user_id`.**
   `settings_service` has both shapes (`add_crypto_watch(telegram_id, …)` vs
   `set_crypto_prefs(session, user_id, …)`), which is confusing and duplicated.

### Security

| Issue | Where | Severity |
|---|---|---|
| `JWT_SECRET` defaults to `"change-me"`; a deploy that forgets to set it accepts forged admin sessions | `app/core/config.py` | **High** |
| No rate limiting or lockout on `POST /login` — unlimited bcrypt-guessing | `app/web/routers/auth.py` | **High** |
| JWT session tokens cannot be revoked; logout only clears the cookie, the token stays valid for 7 days | `app/core/security.py` | Medium |
| Webhook API key compared with `!=` (not constant-time) | `app/web/routers/payment.py` | Medium |
| No CSRF tokens on admin forms; `SameSite=Lax` on the session cookie is the only defence | `app/web/` | Medium |
| Session cookie is not `secure=True`, so it can be sent over plain HTTP | `app/web/routers/auth.py` | Medium |
| `admins.totp_secret` column exists but 2FA is not implemented | `app/models/admin.py` | Medium |
| `buy_menu` / `buy_callback` lack `@require_active` — banned/expired users can create orders | `app/bot/handlers/payment.py` | Low |
| Full webhook payloads (including bank transaction details) are stored in `orders.raw` and in `logs.detail` with no redaction or retention policy | `payment.py` | Low |
| Third-party JS loaded from CDNs with no SRI hashes | `app/web/templates/base.html` | Low |
| Only one admin role — every admin can do everything | schema-wide | Low |
| `logs` table grows unbounded (a row per bot command); no retention job | `app/models/log.py` | Low |

### Performance

| Issue | Where |
|---|---|
| `_link_hash` uses builtin `hash()`, salted per process — news dedup keys change on every worker restart, causing re-pushes | `app/worker/tasks/news_push.py` |
| Digest tasks iterate all eligible users in Python and issue a Redis round-trip per user per minute | `gold_digest.py`, `crypto_digest.py`, `football_digest.py` |
| `news_push` does a Redis `SET NX` per (user × fresh item) — quadratic-ish as users grow | `news_push.py` |
| `user_repo.search()` limits to 100 in SQL, then `users.py` filters by status in Python → filtered views under-report | `app/web/routers/users.py` |
| No pagination anywhere: `/users` capped at 100, `/logs` at 200, `/orders` at 200 | web routers |
| `logs` has no composite index for the `(action, created_at)` filter used by `/logs` | `app/models/log.py` |
| Celery worker `concurrency=2` with `rate_limit=25/s` per task — the send path is the throughput ceiling | `celery_app.py` |
| A new `create_async_engine` per Celery task (connect + TLS handshake per task) | `app/worker/db.py` — deliberate, but costly at 1,440 runs/day × 4 jobs |
| `AI_DAILY_LIMIT` is enforced in Redis only; a Redis flush resets everyone's quota | `app/services/ai_service.py` |

### Correctness bugs found while reading

- `buy_menu` displays "Full 4 dịch vụ: 70.000đ"; `constants.py` says `FULL_PRICE = 80_000`
  covering 5 modules. The QR charges 80k. **The user-facing price is wrong.**
- `users.py` `save_crypto_prefs` and `save_football_prefs` both redirect with `?gold_err=1`
  on a parse error — copy-paste leftover, wrong error shown.
- `system_settings_service.set` shadows the builtin `set`.

---

## 11. Recommended improvements

Ordered by value / effort. None of these have been applied.

**Do first (security, low effort)**
1. Make `JWT_SECRET` required with no default; fail startup if unset in production.
2. Rate-limit `POST /login` (Redis counter keyed on IP + username) and add a lockout.
3. Use `hmac.compare_digest` for the SePay API key check.
4. Set `secure=True` on the session cookie when serving over HTTPS.
5. Add `@require_active` to the two payment handlers.
6. Fix the `/muagoi` price text, or better, generate it from `PRODUCTS`.

**Do next (correctness)**
7. Replace `hash()` with `hashlib.sha1(link.encode()).hexdigest()[:16]` in `news_push`.
8. Move the status filter in `/users` into the SQL query and add real pagination.
9. Fix the `?gold_err=1` redirects in the crypto/football handlers.

**Then (structure)**
10. Consolidate notification-preference resolution into one service with a single
    `resolve_delivery(user, module) -> times` entry point and unit tests.
11. Merge `PACKAGES` and `PRODUCTS` into one catalog.
12. Normalise `settings_service` on `user_id`; resolve `telegram_id` at the handler edge.
13. Add a composite index `(action, created_at DESC)` on `logs` and a retention task.

**Testing gaps** (see `docs/development.md` § Testing)
14. No test touches the web layer, the repositories, the Celery tasks, or the payment flow.
    `payment_service.fulfill_order` idempotency and `parse_order_code` are the highest-value
    untested logic in the codebase and are both pure enough to test today.

**Operational**
15. Add `ruff` to `requirements.txt` — it is configured but not installed, so lint has
    never actually run in this environment.
16. Add `celerybeat-schedule` and `app/web/static/` handling to `.gitignore` / tracking.
17. There is no CI configuration of any kind (`.github/` does not exist).
