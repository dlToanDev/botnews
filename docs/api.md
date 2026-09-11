# API surface — BotNews

Everything the system exposes or consumes. There is **no REST/JSON API for clients**:
the web tier serves HTML for a browser, plus one machine-to-machine webhook.

FastAPI's OpenAPI docs are **disabled on purpose** in `app/web/main.py`
(`docs_url=None, redoc_url=None, openapi_url=None`), so `/docs`, `/redoc` and
`/openapi.json` all return 404. This document is the replacement.

---

## 1. Web admin HTTP routes

Base: `https://<domain>/` behind nginx in production, `http://127.0.0.1:8000/` in dev.

Auth model: a `session` cookie holding an HS256 JWT (`sub` = admin username, 7-day TTL),
set at login with `httponly=True, samesite="lax"`. Every protected route depends on
`get_current_admin`; on failure it raises `AuthRedirect`, which the global exception
handler converts to `303 → /login`. **Unauthenticated requests get a redirect, not a 401.**

### Public

| Method | Path | Returns |
|---|---|---|
| `GET` | `/healthz` | `{"status": "ok"}` — no DB access, used by Docker/nginx health checks |
| `GET` | `/login` | login form |
| `POST` | `/login` | form `username`, `password`. Success → 303 `/` + `session` cookie. Failure → 401 + re-rendered form |
| `GET` | `/logout` | 303 `/login`, clears the cookie |

### Dashboard

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | KPIs (users by status/plan, enabled modules), 6-month growth series, users expiring within 7 days. Chart data is passed to Chart.js via `\|tojson` |

### Users

| Method | Path | Body / query | Effect |
|---|---|---|---|
| `GET` | `/users` | `?q=`, `?status=` | list. `q` matches username / full_name / telegram_id (ILIKE). ⚠️ `status` is filtered **in Python after** the SQL `LIMIT 100` |
| `GET` | `/users/{user_id}` | | detail: modules, plan, packages, per-module preferences |
| `POST` | `/users/{id}/status` | `status` | one of `active`/`expired`/`banned`; silently ignored otherwise |
| `POST` | `/users/{id}/plan` | `plan` | `free`/`vip` — label only, changes no access |
| `POST` | `/users/{id}/extend` | `days` | accepted range 1–3650; extends from current expiry if still valid, else from now; sets `active` |
| `POST` | `/users/{id}/cancel` | | expires now, status `expired`, disables **all** modules |
| `POST` | `/users/{id}/packages/{pkg}/apply` | | enables the bundle from `PACKAGES` (`full`, `finance`, `sport`, `info`); leaves other modules untouched |
| `POST` | `/users/{id}/modules/{key}/toggle` | | **HTMX** — returns the `_module_row.html` partial, not a redirect |
| `POST` | `/users/{id}/news` | `categories[]` | filtered against `NEWS_CATEGORY_KEYS` |
| `POST` | `/users/{id}/gold` | `gold_times` | comma/space separated `HH:MM`; parse error → `?gold_err=1` |
| `POST` | `/users/{id}/crypto` | `mode`, `crypto_times`, `coins[]` | ⚠️ parse error redirects with `?gold_err=1` (wrong flag) |
| `POST` | `/users/{id}/football` | `football_times`, `teams` | `teams` is a comma-separated string. ⚠️ same `?gold_err=1` bug |

All non-HTMX POSTs respond `303` back to `/users/{id}`.

### Orders

| Method | Path | Description |
|---|---|---|
| `GET` | `/orders` | 200 most recent orders, newest first — used for payment reconciliation |

### Logs

| Method | Path | Description |
|---|---|---|
| `GET` | `/logs` | `?action=` exact-match filter; 200 most recent, newest first |

### System settings

| Method | Path | Body |
|---|---|---|
| `GET` | `/settings` | `?tab=gold\|crypto\|news\|football`, `?saved=1`, `?err=1` |
| `POST` | `/settings/gold` | `enabled` (checkbox), `times` |
| `POST` | `/settings/crypto` | `enabled`, `times`, `coins[]` (validated against `CRYPTO_SYMBOLS`) |
| `POST` | `/settings/news` | `categories[]` (validated against `NEWS_CATEGORY_KEYS`) |
| `POST` | `/settings/football` | `enabled`, `times`, `leagues[]` (validated against `FOOTBALL_LEAGUE_CODES`) |

Times are parsed by `gold_service.parse_times()` — normalises, sorts, de-duplicates,
raises `ValueError` on anything that is not a valid `HH:MM`. Redirects to
`/settings?saved=1&tab=<tab>` or `?err=1&tab=<tab>`.

---

## 2. SePay payment webhook

The only machine-facing endpoint.

```
POST /api/sepay/webhook
Authorization: Apikey <SEPAY_WEBHOOK_APIKEY>
Content-Type: application/json
```

Request body (fields the handler reads):

| Field | Use |
|---|---|
| `transferType` | processed only when `"in"` or absent |
| `transferAmount` | integer VND; must be `>= order.amount` |
| `content` / `description` | scanned by regex `BOT[0-9A-F]{6}` for the order code |
| `code` | order code, if SePay supplies it directly (takes precedence) |

Responses:

| Status | When |
|---|---|
| `503 {"detail": "Payment not configured"}` | `SEPAY_WEBHOOK_APIKEY` unset — endpoint disabled |
| `401 {"detail": "Invalid apikey"}` | header mismatch (compared with `!=`, not constant-time) |
| `200 {"success": true}` | **every other case**, including no code found, unknown code, underpayment, already-paid retry, and successful fulfilment |

Returning 200 for unmatched payments is intentional — it stops SePay retrying — but it
means the caller cannot distinguish success from a silently dropped payment. Unmatched
cases are recorded in `logs` with `action="order_unmatched"` and
`detail.reason ∈ {no_code, code_not_found, underpaid}` for manual handling on `/orders`.

On success `payment_service.fulfill_order()` (idempotent — returns `False` if the order is
already `paid`) enables `order.modules`, extends `users.expires_at` by
`SUBSCRIPTION_DAYS = 30`, sets `status="active"`, marks the order paid, writes an
`order_paid` log, and best-effort sends a Telegram confirmation.

**Configure the webhook URL in the SePay dashboard as** `https://<domain>/api/sepay/webhook`.

---

## 3. Telegram bot commands

Every command has an unaccented Vietnamese alias; both are registered. `VI_ALIAS` in
`app/bot/main.py` is the single source of truth.

| English | Vietnamese | Gate | Description |
|---|---|---|---|
| `/start` | `/batdau` | `require_active` | register / account info |
| `/help` | `/trogiup` | `require_active` | usage help |
| `/menu` | — | `require_active` | hierarchical inline menu: buy + self-configure |
| `/buy` | `/muagoi` | **none** ⚠️ | product catalog → SePay QR |
| `/ai` | `/troly` | `require_module("ai")` | ask Gemini |
| `/ainews` | `/aitin` | `ai` | AI news summary |
| `/aigold` | `/aivang` | `ai` | AI gold analysis |
| `/aicrypto` | `/aicoin` | `ai` | AI crypto analysis |
| `/today` | `/homnay` | `require_active` | today's schedule |
| `/mylist` | `/danhsach` | `require_active` | all schedules |
| `/addschedule` | `/themlich` | `require_active` | e.g. `/themlich 08:00 Đi làm` |
| `/calendar` | `/lich` | `require_active` | inline month grid |
| `/delete` | `/xoa` | `require_active` | delete by id |
| `/gold` | `/vang` | `gold` | SJC/PNJ prices |
| `/crypto` | `/tiendientu` | `crypto` | top market cap / price |
| `/setcrypto` | `/datcrypto` | `crypto` | `/datcrypto BTC 5` → alert at ±5%/24h |
| `/football` | `/bongda` | `football` | fixtures / results |
| `/live` | `/tructiep` | `football` | live matches |
| `/bxh` | `/bangxephang` | `football` | standings |
| `/myteam` | `/doicuatoi` | `football` | followed teams' fixtures |
| `/setteam` | `/chondoi` | `football` | follow a team |
| `/news` | `/tintuc` | `news` | latest headlines |
| `/setnews` | `/tukhoatin` | `news` | keyword filter |

Generated shortcuts:
- **Per coin** from `COIN_IDS`: `/btc /eth /bnb /sol /xrp /doge /ada /ton`
- **Per league** from `features.LEAGUE_CMDS`: `/epl` … (latest results) and `/bxhepl` …
  (standings), for `PL, PD, SA, BL1, FL1, CL`

Callback query namespaces: `menu:*` (main menu), `buy:*` (product selection),
`cal:*` (calendar navigation/edit).

### Gating semantics

- `@require_active` — resolves or creates the user, rejects `banned` and expired accounts,
  stores `db_user_id` in `context.user_data`, writes a `command` audit log.
- `@require_module("key")` — all of the above, plus the module must be enabled in
  `subscription_modules`. Denied users get a "🔒 … chưa được kích hoạt" message.

---

## 4. Celery task API

Tasks are addressed by their explicit `name=`. Call them with
`<task>.delay(...)` / `.apply_async(...)`.

### Fan-out senders

| Task | Signature | Behaviour |
|---|---|---|
| `app.worker.tasks.send_message.send_message_task` | `(chat_id: int, text: str)` | Markdown parse mode, `rate_limit="25/s"`, `max_retries=5`. Retries on `RetryAfter` with the API-supplied countdown; returns `"forbidden"` if the user blocked the bot |
| `app.worker.tasks.send_photo.send_photo_task` | `(chat_id, photo_url, caption)` | same pattern |

### Periodic tasks

| Name | Beat cadence |
|---|---|
| `app.worker.tasks.daily_digest.send_daily_digest` | 07:00 daily |
| `app.worker.tasks.schedule_reminder.check_reminders` | every minute |
| `app.worker.tasks.expire_users.expire_overdue` | 00:05 daily |
| `app.worker.tasks.crypto_alert.poll_and_alert` | every 2 min |
| `app.worker.tasks.crypto_digest.poll_and_send` | every minute |
| `app.worker.tasks.gold_alert.poll_and_alert` | every 10 min |
| `app.worker.tasks.gold_digest.poll_and_send` | every minute |
| `app.worker.tasks.football_live.poll_and_alert` | every 2 min |
| `app.worker.tasks.football_digest.poll_and_send` | every minute |
| `app.worker.tasks.news_push.poll_and_alert` | every 2 min |

Each returns the number of messages enqueued. Adding a task requires touching **two**
places in `app/worker/celery_app.py`: `include=[...]` and, if periodic, `beat_schedule`.

Manual invocation:

```bash
.venv/bin/celery -A app.worker.celery_app call app.worker.tasks.gold_digest.poll_and_send
.venv/bin/celery -A app.worker.celery_app inspect registered
```

---

## 5. Outbound third-party APIs

All go through `app/integrations/`. `BaseAdapter` provides 3-attempt retry with backoff,
a Redis cache at `cache:<name>` (per-adapter TTL) and a stale copy at
`cache:<name>:stale` (20× TTL) served when the upstream fails.

| Service | Endpoint | Key | Adapter | TTL |
|---|---|---|---|---|
| PNJ gold | `edge-api.pnj.io/ecom-frontend/v1/get-gold-price` | none | `gold.GoldAdapter` | 300s |
| CoinGecko | markets API | none (free tier) | `coingecko.py` / `crypto.py` | see module |
| football-data.org | standings + results | `FOOTBALL_DATA_KEY` | `football_data.py` | see module |
| api-sports.io | live scores | `API_FOOTBALL_KEY` | `football.py` | see module |
| VNExpress RSS | 8 category feeds in `NEWS_CATEGORIES` | none | `news.py` (feedparser + BeautifulSoup) | see module |
| Google Gemini | `generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` | `GEMINI_API_KEY` | `gemini.py` | **no cache** |
| Telegram | `api.telegram.org/bot<token>/sendMessage` | `BOT_TOKEN` | `services/telegram_notify.py` (web tier), `python-telegram-bot` (bot/worker) | — |
| SePay VietQR | `qr.sepay.vn/img?acc=&bank=&amount=&des=` | — | `payment_service.build_qr_url` | — |

Gemini is called with `maxOutputTokens=800, temperature=0.7`, a 30s timeout, and the
system prompt folded into the user content. It raises `GeminiQuotaError` on HTTP 429 and
`GeminiError` otherwise. Usage is capped at `AI_DAILY_LIMIT = 30` requests/user/day via a
Redis counter (`ai:quota:<user_id>:<YYYYMMDD>`, 26h TTL) with a refund on failure.

---

## 6. Redis key map

| Pattern | Written by | TTL |
|---|---|---|
| `cache:<adapter>` | `BaseAdapter` | per adapter |
| `cache:<adapter>:stale` | `BaseAdapter` | 20× adapter TTL |
| `dedup:<key>` | `core/dedup.py::should_alert` | per call site |
| `dedup:crypto:<user>:<sym>:<up\|down>` | `crypto_alert` | 1800s |
| `dedup:golddigest:<user>:<YYYYMMDD>:<HH:MM>` | `gold_digest` | 7200s |
| `dedup:news:<user>:<link_hash>` | `news_push` | 86400s |
| `news:seen:<link_hash>` | `news_push` | 259200s |
| `news:seeded` | `news_push` | no expiry — first run seeds silently |
| `ai:quota:<user_id>:<YYYYMMDD>` | `ai_service` | 93600s |

⚠️ `<link_hash>` comes from Python's builtin `hash()`, which is salted per process, so news
dedup keys change on every worker restart.

Redis database allocation: `0` = app cache/dedup, `1` = Celery broker, `2` = Celery results.
