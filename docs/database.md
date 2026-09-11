# Database — BotNews

PostgreSQL 16, accessed with **SQLAlchemy 2.0 async ORM** over `asyncpg`, migrated with
**Alembic**. There is no Prisma in this project and no `schema.prisma` file.

Models live in `app/models/` and are the source of truth for the schema.
`app/models/__init__.py` imports all of them so `Base.metadata` is complete for
Alembic autogenerate — **a new model must be added there or it will be silently ignored**.

---

## 1. Conventions

- All timestamps are `TIMESTAMPTZ` (`DateTime(timezone=True)`) and stored in **UTC**.
  Conversion to `Asia/Ho_Chi_Minh` happens at the presentation edge via
  `app/core/timeutils.py`.
- `created_at` / `updated_at` use `server_default=func.now()` and `onupdate=func.now()`.
- Flexible / list-shaped fields are `JSONB` with a Python-side `default=list` or
  `default=dict`. Because these defaults are Python-side, **in-place mutation requires
  `flag_modified(obj, "column")`** (see `app/services/settings_service.py`).
- Enum-like columns are plain `String` with the allowed values documented in comments and
  validated in `app/core/constants.py` — there are no Postgres `ENUM` types.
- `id` is `BigInteger` on most tables; `schedules.id` and `subscription_modules.id` are
  plain `Integer`.

## 2. Tables

### `users`
The bot's account record, keyed to Telegram.

| Column | Type | Notes |
|---|---|---|
| `id` | BIGINT PK | internal id — used everywhere except the Telegram edge |
| `telegram_id` | BIGINT | **UNIQUE, indexed** — the Telegram chat/user id |
| `username` | VARCHAR(64) NULL | Telegram @handle |
| `full_name` | VARCHAR(255) NULL | |
| `phone` | VARCHAR(20) NULL | never populated by any current code path |
| `status` | VARCHAR(20), indexed | `active` \| `expired` \| `banned` |
| `plan` | VARCHAR(50) | `free` \| `vip` — **a label only, grants nothing** |
| `expires_at` | TIMESTAMPTZ NULL, indexed | NULL = no expiry |
| `created_at`, `updated_at` | TIMESTAMPTZ | |

Relationship: `settings` → one `user_settings` row, `cascade="all, delete-orphan"`.

### `user_settings`
Per-user notification preferences. One row per user (`user_id` UNIQUE, `ON DELETE CASCADE`).
Created automatically in `user_repo.create()`.

| Column | Type | Purpose |
|---|---|---|
| `timezone` | VARCHAR(50) = `Asia/Ho_Chi_Minh` | stored but not yet used per-user |
| `daily_digest_time` | TIME = 07:00 | stored; the 07:00 digest is currently global |
| `reminder_minutes` | INT = 30 | default lead time for calendar reminders |
| `crypto_watchlist` | JSONB | `[{"symbol": "BTC", "threshold_pct": 5}]` — threshold alerts |
| `crypto_times` | JSONB | `["09:00", "16:00"]` — digest delivery times |
| `crypto_notify_mode` | VARCHAR(10) | `system` \| `custom` \| `off` |
| `crypto_coins` | JSONB | symbols to include; empty = all |
| `gold_alert_pct` | NUMERIC(5,2) NULL | gold move threshold |
| `gold_times` | JSONB | gold digest times |
| `news_keywords` | JSONB | extra title filter |
| `news_categories` | JSONB | keys from `NEWS_CATEGORIES`; empty = fall back to system default |
| `favorite_teams` | JSONB | substring-matched team names |
| `football_times` | JSONB | football results digest times |
| `language` | VARCHAR(10) = `vi` | stored, not used |

### `subscription_modules`
**This table, not `users.plan`, is what gates features.**

| Column | Type | Notes |
|---|---|---|
| `user_id` | BIGINT FK → users, CASCADE, indexed | |
| `module_key` | VARCHAR(50) | one of `MODULE_KEYS`: `schedule, gold, crypto, football, news, ai` |
| `is_enabled` | BOOL | |
| `config` | JSONB | reserved; not read anywhere today |
| `enabled_at` | TIMESTAMPTZ NULL | set on enable, cleared on disable |

`UNIQUE (user_id, module_key)` — constraint name `uq_user_module`.
New users get `DEFAULT_MODULES = ["schedule"]` enabled at creation.

### `schedules`
Personal calendar entries.

| Column | Type | Notes |
|---|---|---|
| `user_id` | FK → users, CASCADE, indexed | |
| `title` | VARCHAR(255) | |
| `description` | TEXT NULL | |
| `start_time` | TIMESTAMPTZ, indexed | UTC |
| `end_time` | TIMESTAMPTZ NULL | |
| `location` | VARCHAR(255) NULL | |
| `recurrence` | VARCHAR(20) | `none` \| `daily` \| `weekly` \| `monthly` — **stored but recurrence is not expanded by any task** |
| `recur_days` | JSONB | likewise unused |
| `reminder_minutes` | INT = 30 | |
| `is_notified` | BOOL | already reminded *before* start |
| `started_notified` | BOOL | already announced *at* start |
| `is_active` | BOOL | |

Reminder queries: `list_due_reminders` (start in `(now, now+60min]`, `is_notified=false`)
and `list_due_started` (start in `(now-15min, now]`, `started_notified=false` — the grace
window prevents both missed reminders after worker lag and a burst after a deploy).

### `orders`
SePay purchases.

| Column | Type | Notes |
|---|---|---|
| `user_id` | BIGINT FK → users, CASCADE, indexed | |
| `code` | VARCHAR(32) **UNIQUE, indexed** | `BOT` + 6 uppercase hex; goes in the transfer memo |
| `item_key`, `item_label` | VARCHAR | snapshot from `PRODUCTS` |
| `modules` | JSONB | module keys to enable on payment |
| `amount` | INT | VND |
| `status` | VARCHAR(20), indexed | `pending` \| `paid` \| `expired` — **nothing ever sets `expired`** |
| `raw` | JSONB | the matched webhook payload (contains bank transaction data) |
| `created_at` (indexed), `paid_at`, `expires_at` | TIMESTAMPTZ | `expires_at` = created + 15 min |

### `admins`
Web dashboard accounts. Created by `scripts/init_admin.py`.

| Column | Type | Notes |
|---|---|---|
| `username` | VARCHAR(64) UNIQUE, indexed | |
| `password_hash` | VARCHAR(255) | bcrypt |
| `totp_secret` | VARCHAR(64) NULL | **column exists, 2FA is not implemented** |
| `last_login_at` | TIMESTAMPTZ NULL | |

No role column — every admin has full access.

### `logs`
Audit + activity trail.

| Column | Type | Notes |
|---|---|---|
| `user_id` | BIGINT FK → users, **SET NULL**, indexed | |
| `actor` | VARCHAR(20) | `user` \| `admin` \| `system` |
| `action` | VARCHAR(100), indexed | see below |
| `level` | VARCHAR(10) | `info` \| `warn` \| `error` |
| `detail` | JSONB | free-form payload |
| `created_at` | TIMESTAMPTZ, indexed | |

Action values in use: `command`, `user_register`, `module_toggle`, `package_apply`,
`plan_change`, `plan_cancel`, `plan_extend`, `status_change`, `auto_expire`,
`order_create`, `order_paid`, `order_unmatched`.

> A row is written for **every bot command**. This table is the fastest-growing one and
> has no retention policy. `/logs` filters on `action` and orders by `created_at DESC`,
> but there is no composite index for that pair.

### `system_settings`
Global key/value config, edited from `/settings`.

| Column | Type |
|---|---|
| `key` | VARCHAR(64) PK |
| `value` | JSONB |
| `updated_at` | TIMESTAMPTZ |

Known keys (`app/services/system_settings_service.py`):

| Key | Shape |
|---|---|
| `gold_notify` | `{"enabled": bool, "times": ["HH:MM"]}` |
| `crypto_notify` | `{"enabled": bool, "times": [...], "coins": ["BTC", …]}` |
| `football_notify` | `{"enabled": bool, "times": [...], "leagues": ["PL", …]}` |
| `news_default` | `{"categories": ["thoisu", …]}` |

## 3. Relationships

```
users 1──1 user_settings          (CASCADE)
users 1──* subscription_modules   (CASCADE, unique per module_key)
users 1──* schedules              (CASCADE)
users 1──* orders                 (CASCADE)
users 1──* logs                   (SET NULL — logs survive user deletion)

admins            standalone
system_settings   standalone
```

## 4. Migrations

Alembic is configured for async in `alembic/env.py`: it imports `app.models`, takes
`target_metadata = Base.metadata`, reads the URL from `app.core.config.settings`
(the `sqlalchemy.url` in `alembic.ini` is a placeholder) and runs with `compare_type=True`.

Current chain — **linear, single head**:

```
458a856d62d9  init core tables                users, user_settings, schedules, logs
4d8f8a24c3da  add subscription modules + admins
c3f9a1b2d4e6  add orders
e7a2c4f8b1d3  add news categories
f1b3d5a7c9e2  add started_notified
a9c1e3f5b7d0  gold notify                     gold_times + system_settings
b4d6f8a0c2e5  add crypto times
c5e7a9b1d3f6  crypto notify granular          crypto_notify_mode, crypto_coins
d6f8b0c2e4a7  add football times              ← HEAD
```

### Working with migrations

```bash
.venv/bin/alembic current                                  # where am I
.venv/bin/alembic upgrade head                             # apply
.venv/bin/alembic revision --autogenerate -m "short msg"   # generate
.venv/bin/alembic downgrade -1                             # roll back one
.venv/bin/alembic history --verbose
```

**Always read the autogenerated file before applying it.** In this repo the established
pattern for adding a NOT NULL JSONB column to an existing table is:

```python
op.add_column("user_settings",
    sa.Column("crypto_times", postgresql.JSONB(), nullable=False, server_default="[]"))
op.alter_column("user_settings", "crypto_times", server_default=None)
```

i.e. backfill with a `server_default`, then drop the default so the Python-side default
takes over. Autogenerate does not do this for you. Keep the chain linear — do not create
branches.

## 5. Indexes present

`users`: `telegram_id` (unique), `status`, `expires_at`
`schedules`: `user_id`, `start_time`
`subscription_modules`: `user_id`, unique `(user_id, module_key)`
`orders`: `user_id`, `code` (unique), `status`, `created_at`
`logs`: `user_id`, `action`, `created_at`
`admins`: `username` (unique)

### Missing / worth adding

- `logs (action, created_at DESC)` — the exact `/logs` query shape.
- `subscription_modules (module_key, is_enabled)` — `eligible_users` filters on both, then
  joins `users` and `user_settings`; this join runs once per minute per digest task.
- `orders (status, created_at)` if the orders view ever gets a status filter.

## 6. Connection pooling

| Process | Engine |
|---|---|
| web, bot | `app/core/database.py` — `pool_size=10, max_overflow=20, pool_pre_ping=True` |
| Celery task | `app/worker/db.py` — a **new** engine with `NullPool` per task, disposed on exit |

The worker cannot reuse the shared pool because each task runs `asyncio.run()`, creating a
fresh event loop; pooled asyncpg connections are bound to the loop that created them.

Production Postgres is tuned in `docker-compose.prod.yml`:
`shared_buffers=512MB`, `max_connections=50`, `effective_cache_size=1536MB`.
With 2 uvicorn workers × 30 potential connections plus bot and workers, `max_connections=50`
is a realistic ceiling to watch.

## 7. Backup & restore

```bash
bash scripts/backup_db.sh                         # pg_dump | gzip → backups/, keeps 7
bash scripts/restore_db.sh backups/<file>.sql.gz  # ⚠️ overwrites; prompts for "yes"
```

`backup_db.sh` runs `pg_dump --clean --if-exists` through the prod compose container and
verifies the gzip before keeping the file. Suggested cron: `0 2 * * *`.
Restore has never been exercised in this repo — test it before you rely on it.
