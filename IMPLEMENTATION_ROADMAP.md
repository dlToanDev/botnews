# 🤖 SaaS Telegram Bot Multi-User + Web Admin Dashboard
## Kế hoạch Phát triển Chi tiết (Implementation Roadmap)

> **Mô hình:** SaaS bán tính năng theo gói cước. Admin (1 người) quản lý user qua Web Dashboard nội bộ, bật/tắt module cho từng khách hàng, quản lý hạn gói cước. Bot phục vụ đa người dùng qua Telegram.
> **Hạ tầng:** 1 VPS Linux (2 vCPU / 4GB RAM), Docker + Docker Compose.

---

## 1. KIẾN TRÚC KỸ THUẬT (TECH STACK)

### 1.1. Lựa chọn & Lý do

| Thành phần | Công nghệ đề xuất | Lý do |
|---|---|---|
| **Ngôn ngữ Backend** | **Python 3.12** | Hệ sinh thái mạnh cho bot, data, async. Dễ maintain một mình. |
| **Bot Framework** | **python-telegram-bot v21+** (async) | API ổn định nhất, hỗ trợ `JobQueue`, conversation handler, rate-limit built-in (`AIORateLimiter`). |
| **Web API / Admin Backend** | **FastAPI** | Async, tự sinh docs (`/docs`), Pydantic validation, chung ngôn ngữ với bot → tái sử dụng models/DB. |
| **Web Admin Frontend** | **Jinja2 + HTMX + Tailwind CSS** (khuyến nghị) *hoặc* React SPA | Chỉ 1 admin → không cần SPA nặng. HTMX cho tốc độ dev nhanh, ít JS, nhẹ VPS. Nếu muốn UI phong phú → React. |
| **Database** | **PostgreSQL 16** | Multi-user, quan hệ phức tạp (gói cước, module, log), transaction an toàn. **Không dùng SQLite** cho production đa người dùng ghi đồng thời. |
| **ORM** | **SQLAlchemy 2.0 (async)** + **Alembic** (migration) | Chuẩn công nghiệp, quản lý schema theo version. |
| **Cache + Message Broker** | **Redis 7** | Cache giá real-time (crypto/vàng), lưu state, làm broker cho Celery, dedup alert. |
| **Task Queue (async jobs)** | **Celery** (worker + **Celery Beat**) | Gửi thông báo hàng loạt tránh block bot; retry tự động; **quản lý rate-limit Telegram**. |
| **Scheduler** | **Celery Beat** (cron trong DB qua `django-celery-beat`-like hoặc `celery beat` config) | Job 7h sáng báo lịch; poll giá theo chu kỳ. |
| **Reverse Proxy / SSL** | **Nginx + Certbot (Let's Encrypt)** | HTTPS cho Web Admin, che bot webhook (nếu dùng webhook). |
| **Auth Admin** | **JWT / Session Cookie + bcrypt** | 1 tài khoản admin, thêm 2FA (TOTP) nếu cần. |

> **Kiến trúc chạy Bot:** Với VPS riêng, dùng **Long Polling** cho đơn giản (không cần mở port/SSL cho bot). Khi scale lớn → chuyển **Webhook** qua Nginx.

### 1.2. ⚠️ Chống Rate-Limit Telegram (RẤT QUAN TRỌNG)

Telegram giới hạn: **~30 messages/giây toàn bot**, **1 msg/giây cho mỗi chat**, **~20 msg/phút cho cùng 1 group**.

**Giải pháp:**
1. **Không gửi trực tiếp trong loop.** Mọi thông báo hàng loạt → đẩy vào **Celery queue**.
2. Bật `AIORateLimiter` của python-telegram-bot (tự động throttle + retry khi gặp `RetryAfter`).
3. Celery worker gửi theo batch, `rate_limit` task (vd `29/s`), có `sleep` giữa các nhóm.
4. **Dedup alert bằng Redis** (key có TTL) để không spam cùng 1 cảnh báo giá.

### 1.3. Nguồn API dữ liệu

| Module | Nguồn khuyến nghị | Ghi chú |
|---|---|---|
| **⚽ Bóng đá (Live score)** | **API-Football** (api-sports.io) | Free 100 req/ngày; live score, lịch, kết quả. Alt: `football-data.org` (free tier). |
| **₿ Crypto / Bitcoin** | **Binance API** (REST + **WebSocket**) | Free, real-time, không cần key cho public data. WebSocket `!ticker@arr` cho biến động giá. Alt: **CoinGecko** (REST, có giá VND). |
| **🥇 Giá vàng (SJC/PNJ)** | **SJC không có API chính thức** → scrape trang SJC/PNJ hoặc dùng API bên thứ 3 | Nguồn thực tế: `sjc.com.vn` (form POST), `giavang.pnj.com.vn`, hoặc API tổng hợp `webgia.com` / `giavang.org`. Cần cache Redis 5–10 phút, xử lý lỗi khi web đổi cấu trúc. |
| **📰 Tin tức nóng** | **RSS feeds** (miễn phí, ổn định) + **NewsAPI.org** / **GNews** | RSS VnExpress/Tuoitre/Reuters/BBC. NewsAPI cho tìm kiếm quốc tế (free 100 req/ngày). |

> **Nguyên tắc:** Bọc mỗi nguồn trong 1 **Adapter class** (interface chung `fetch()`), để dễ thay nguồn khi API chết/đổi giá mà không sửa business logic.

---

## 2. THIẾT KẾ CƠ SỞ DỮ LIỆU (DATABASE SCHEMA)

```
┌──────────────┐      ┌────────────────────┐
│    users     │─1──N─│  subscription_     │
│              │      │  modules           │
└──────┬───────┘      └────────────────────┘
       │1
       ├──N──► user_settings (1-1 thực tế)
       ├──N──► schedules
       └──N──► logs
```

### 2.1. Bảng `users` — Danh sách khách hàng Telegram

```sql
CREATE TABLE users (
    id              BIGSERIAL PRIMARY KEY,
    telegram_id     BIGINT UNIQUE NOT NULL,        -- user_id từ Telegram
    username        VARCHAR(64),                    -- @username (có thể null)
    full_name       VARCHAR(255),
    phone           VARCHAR(20),
    status          VARCHAR(20) NOT NULL DEFAULT 'active',  -- active | expired | banned
    plan            VARCHAR(50) DEFAULT 'free',     -- free | basic | pro | vip
    expires_at      TIMESTAMPTZ,                    -- hạn gói cước (NULL = vô hạn)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_expires_at ON users(expires_at);
```

### 2.2. Bảng `user_settings` — Cấu hình cá nhân từng user

```sql
CREATE TABLE user_settings (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    timezone            VARCHAR(50) DEFAULT 'Asia/Ho_Chi_Minh',
    daily_digest_time   TIME DEFAULT '07:00',       -- giờ báo lịch tổng hợp
    reminder_minutes    INT DEFAULT 30,             -- nhắc trước giờ làm (15-30 phút)
    -- Ngưỡng cảnh báo crypto (JSONB linh hoạt)
    crypto_watchlist    JSONB DEFAULT '[]',         -- [{"symbol":"BTCUSDT","threshold_pct":5}]
    gold_alert_pct      NUMERIC(5,2),               -- % biến động vàng để cảnh báo
    news_keywords       JSONB DEFAULT '[]',         -- ["bitcoin","fed"]
    favorite_teams      JSONB DEFAULT '[]',         -- ["Arsenal","Man City"]
    language            VARCHAR(10) DEFAULT 'vi',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 2.3. Bảng `schedules` — Lịch cá nhân người dùng

```sql
CREATE TABLE schedules (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title           VARCHAR(255) NOT NULL,          -- "Đi làm", "Họp team"
    description     TEXT,
    start_time      TIMESTAMPTZ NOT NULL,           -- thời điểm bắt đầu
    end_time        TIMESTAMPTZ,
    location        VARCHAR(255),
    -- Lịch lặp lại (RRULE-like)
    recurrence      VARCHAR(20) DEFAULT 'none',     -- none | daily | weekly | monthly
    recur_days      JSONB DEFAULT '[]',             -- [1,2,3,4,5] (thứ trong tuần)
    reminder_minutes INT DEFAULT 30,                -- ghi đè setting nếu cần
    is_notified     BOOLEAN DEFAULT FALSE,          -- đã gửi nhắc lịch chưa (job đánh dấu)
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_schedules_user ON schedules(user_id);
CREATE INDEX idx_schedules_start ON schedules(start_time) WHERE is_active = TRUE;
```

### 2.4. Bảng `subscription_modules` — Phân quyền tính năng (Feature Toggle)

> Đây là **trái tim của mô hình SaaS**: bật/tắt từng module cho từng user.

```sql
CREATE TABLE subscription_modules (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    module_key      VARCHAR(50) NOT NULL,           -- 'schedule' | 'gold' | 'crypto' | 'football' | 'news'
    is_enabled      BOOLEAN NOT NULL DEFAULT FALSE, -- Admin tích chọn bật/tắt
    config          JSONB DEFAULT '{}',             -- cấu hình riêng module nếu cần
    enabled_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, module_key)
);
CREATE INDEX idx_modules_user ON subscription_modules(user_id);
CREATE INDEX idx_modules_lookup ON subscription_modules(user_id, module_key, is_enabled);
```

**Các module_key chuẩn hoá:**
| module_key | Tên hiển thị |
|---|---|
| `schedule` | Lịch cá nhân |
| `gold` | Giá vàng SJC/PNJ |
| `crypto` | Cảnh báo giá Crypto |
| `football` | Bóng đá / Live score |
| `news` | Tin tức nóng |

### 2.5. Bảng `logs` — Nhật ký hoạt động & audit

```sql
CREATE TABLE logs (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT REFERENCES users(id) ON DELETE SET NULL,  -- NULL = system/admin
    actor           VARCHAR(20) DEFAULT 'system',   -- user | admin | system
    action          VARCHAR(100) NOT NULL,          -- 'command', 'notify_sent', 'module_toggle', 'plan_extend'
    level           VARCHAR(10) DEFAULT 'info',     -- info | warn | error
    detail          JSONB DEFAULT '{}',             -- payload chi tiết
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_logs_user ON logs(user_id);
CREATE INDEX idx_logs_action ON logs(action);
CREATE INDEX idx_logs_created ON logs(created_at DESC);
```

### 2.6. Bảng `admins` — Tài khoản quản trị (bổ sung)

```sql
CREATE TABLE admins (
    id              BIGSERIAL PRIMARY KEY,
    username        VARCHAR(64) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,          -- bcrypt
    totp_secret     VARCHAR(64),                    -- 2FA (tùy chọn)
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## 3. CẤU TRÚC MÃ NGUỒN DỰ ÁN (PROJECT STRUCTURE)

Kiến trúc **monorepo** — Bot & Web Admin & Worker dùng chung `core` (models, DB, config) nhưng chạy container riêng.

```
botNews/
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env                          # Biến môi trường (KHÔNG commit)
├── .env.example
├── .gitignore
├── README.md
├── IMPLEMENTATION_ROADMAP.md
│
├── alembic/                      # Database migrations
│   ├── versions/
│   └── env.py
├── alembic.ini
│
├── nginx/
│   ├── nginx.conf
│   └── certbot/                  # SSL certs
│
├── app/                          # ⭐ Toàn bộ source Python (1 image dùng chung)
│   ├── __init__.py
│   │
│   ├── core/                     # 🔧 Shared core (dùng bởi bot + web + worker)
│   │   ├── __init__.py
│   │   ├── config.py             # Pydantic Settings đọc từ .env
│   │   ├── database.py           # Async engine + session factory
│   │   ├── redis_client.py       # Redis connection pool
│   │   ├── logging.py            # Structured logging
│   │   └── security.py           # bcrypt, JWT helpers
│   │
│   ├── models/                   # 🗄️ SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── user.py               # User, UserSettings
│   │   ├── schedule.py
│   │   ├── subscription.py       # SubscriptionModule
│   │   ├── log.py
│   │   └── admin.py
│   │
│   ├── repositories/             # 📦 Data access layer (CRUD)
│   │   ├── user_repo.py
│   │   ├── schedule_repo.py
│   │   ├── module_repo.py
│   │   └── log_repo.py
│   │
│   ├── services/                 # 🧠 Business logic (tái dùng bot & web)
│   │   ├── __init__.py
│   │   ├── user_service.py       # Đăng ký, kiểm tra hạn, ban
│   │   ├── schedule_service.py   # CRUD lịch, tính reminder
│   │   ├── subscription_service.py  # Check module bật/tắt, gia hạn gói
│   │   └── notification_service.py  # Đẩy message vào Celery queue
│   │
│   ├── integrations/             # 🌐 Adapters gọi API bên ngoài
│   │   ├── __init__.py
│   │   ├── base.py               # BaseAdapter (interface fetch())
│   │   ├── crypto.py             # Binance / CoinGecko
│   │   ├── gold.py               # SJC / PNJ scraper
│   │   ├── football.py           # API-Football
│   │   └── news.py               # RSS / NewsAPI
│   │
│   ├── bot/                      # 🤖 Telegram Bot service
│   │   ├── __init__.py
│   │   ├── main.py               # Entry: khởi tạo Application, polling
│   │   ├── middlewares.py        # Auth: nhận diện user_id, check status/module
│   │   ├── keyboards.py          # Inline / Reply keyboards
│   │   ├── handlers/
│   │   │   ├── __init__.py
│   │   │   ├── start.py          # /start, /help, đăng ký
│   │   │   ├── schedule.py       # /addschedule, /mylist, /today
│   │   │   ├── crypto.py         # /crypto, set watchlist
│   │   │   ├── gold.py           # /gold
│   │   │   ├── football.py       # /football
│   │   │   ├── news.py           # /news
│   │   │   └── settings.py       # /settings (timezone, reminder)
│   │   └── decorators.py         # @require_module('crypto'), @require_active
│   │
│   ├── worker/                   # ⚙️ Celery tasks + Beat schedule
│   │   ├── __init__.py
│   │   ├── celery_app.py         # Khởi tạo Celery + broker Redis
│   │   ├── beat_schedule.py      # Định nghĩa cron jobs
│   │   └── tasks/
│   │       ├── __init__.py
│   │       ├── daily_digest.py   # 7h sáng: gửi lịch tổng hợp
│   │       ├── schedule_reminder.py  # Quét lịch sắp tới, nhắc trước 15-30'
│   │       ├── crypto_alert.py   # Poll giá, so ngưỡng, gửi alert
│   │       ├── gold_alert.py
│   │       ├── football_live.py
│   │       ├── news_push.py
│   │       └── send_message.py   # Task gửi 1 message (rate-limited)
│   │
│   └── web/                      # 🖥️ Web Admin Dashboard (FastAPI)
│       ├── __init__.py
│       ├── main.py               # FastAPI app, mount routers
│       ├── deps.py               # Dependency: get_current_admin
│       ├── routers/
│       │   ├── auth.py           # Login/logout admin
│       │   ├── dashboard.py      # Trang tổng quan (thống kê)
│       │   ├── users.py          # CRUD user, đổi status
│       │   ├── modules.py        # Toggle module theo user
│       │   ├── subscriptions.py  # Gia hạn +30/+365 ngày
│       │   └── logs.py           # Xem log
│       ├── schemas/              # Pydantic request/response
│       │   ├── user.py
│       │   └── module.py
│       ├── templates/            # Jinja2 (nếu dùng HTMX)
│       │   ├── base.html
│       │   ├── login.html
│       │   ├── dashboard.html
│       │   ├── users.html
│       │   └── user_detail.html
│       └── static/
│           ├── css/
│           └── js/
│
├── scripts/
│   ├── init_admin.py             # Tạo tài khoản admin đầu tiên
│   ├── seed.py                   # Seed dữ liệu test
│   └── backup_db.sh              # Cron backup PostgreSQL
│
├── tests/
│   ├── test_services/
│   ├── test_integrations/
│   └── test_bot/
│
├── requirements.txt
├── Dockerfile                    # 1 image chung cho bot/web/worker
└── pyproject.toml
```

> **Nguyên tắc kiến trúc:** `handlers` & `routers` **KHÔNG** chứa business logic → chỉ gọi `services`. `services` gọi `repositories`. Real-time notification luôn qua `notification_service` → Celery. Điều này giúp cùng 1 logic (vd "gia hạn gói") dùng được cho cả Web Admin lẫn command bot.

---

## 4. LỘ TRÌNH TRIỂN KHAI THEO GIAI ĐOẠN (ROADMAP)

### 🟢 PHASE 1 — Core Bot & Nền tảng (Tuần 1–2)
**Mục tiêu:** Bot chạy được, nhận diện user, quản lý lịch cá nhân + báo lịch 7h sáng.

- [ ] Setup repo, `docker-compose` (postgres + redis + bot), `.env`, config.
- [ ] Thiết kế models + Alembic migration (bảng `users`, `user_settings`, `schedules`, `logs`).
- [ ] Bot `/start`: tự động **upsert user** theo `telegram_id` vào DB.
- [ ] Middleware nhận diện + kiểm tra `status` (active/expired/banned).
- [ ] Module Lịch cá nhân: `/addschedule`, `/today`, `/mylist`, `/delete`.
- [ ] Celery + Beat: job **7h sáng** gửi digest lịch trong ngày.
- [ ] Job **reminder** quét lịch mỗi phút, nhắc trước 15–30'.
- [ ] Bật `AIORateLimiter`, log mọi lệnh vào `logs`.

**Kết quả:** Người dùng nhập lịch, nhận báo lịch sáng + nhắc trước giờ.

### 🟡 PHASE 2 — Web Admin Dashboard (Tuần 3–4)
**Mục tiêu:** Admin quản lý user, phân quyền module, gia hạn gói.

- [ ] FastAPI app + auth admin (login JWT/session + bcrypt, `init_admin.py`).
- [ ] Bảng `subscription_modules`, `admins` + migration.
- [ ] Trang **Dashboard**: tổng user, active/expired, thống kê module.
- [ ] Trang **Quản lý User**: list, search, đổi status (active/expired/banned).
- [ ] **Feature Toggle**: checkbox bật/tắt từng module cho từng user (`schedule/gold/crypto/football/news`).
- [ ] **Gia hạn gói**: nút `+30 ngày`, `+365 ngày` → cập nhật `expires_at`.
- [ ] Trang **Logs**: xem hoạt động, lọc theo user/action.
- [ ] Decorator bot `@require_module()` + `@require_active` đọc từ DB → chặn user chưa mua/ hết hạn.

**Kết quả:** Bạn hoàn toàn kiểm soát ai dùng gì, đến khi nào.

### 🟠 PHASE 3 — Real-time Integrations (Tuần 5–7)
**Mục tiêu:** Tích hợp 4 module dữ liệu real-time qua Adapter + Celery.

- [ ] `integrations/base.py` + adapter cho từng nguồn (cache Redis + xử lý lỗi/retry).
- [ ] **Crypto:** poll Binance/CoinGecko, so `crypto_watchlist`, dedup Redis, gửi alert biến động %.
- [ ] **Gold:** scrape SJC/PNJ mỗi 5–10', so ngưỡng `gold_alert_pct`.
- [ ] **Football:** API-Football, `/football` + push live score cho `favorite_teams`.
- [ ] **News:** RSS/NewsAPI, lọc `news_keywords`, push tin nóng.
- [ ] Mỗi task **chỉ gửi cho user có module `is_enabled=TRUE` và còn hạn** (query filter).
- [ ] Tối ưu batch gửi + rate-limit qua Celery.

**Kết quả:** Bot đầy đủ tính năng SaaS, đúng phân quyền.

### 🔴 PHASE 4 — Deployment VPS (Tuần 8)
**Mục tiêu:** Production ổn định, bảo mật, tự backup.

- [ ] `docker-compose.prod.yml`: postgres, redis, bot, worker, beat, web, nginx.
- [ ] **Nginx** reverse proxy cho Web Admin + **Certbot SSL** (HTTPS).
- [ ] Giới hạn truy cập Admin: HTTPS + (tùy chọn) IP allowlist / Basic Auth lớp ngoài.
- [ ] Healthcheck container + `restart: always`.
- [ ] Cron **backup PostgreSQL** hàng ngày (`scripts/backup_db.sh` → lưu ngoài/S3).
- [ ] Log rotation, giám sát tài nguyên (2vCPU/4GB → giới hạn worker concurrency = 2–4).
- [ ] Chuyển bot sang **Webhook** (nếu cần) qua Nginx.

**Kết quả:** Hệ thống chạy 24/7, an toàn, tự phục hồi.

---

## 5. KHUNG CODE MẪU (BOILERPLATE)

### 5.1. `docker-compose.yml`

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    # KHÔNG expose port ra ngoài trên prod; chỉ nội bộ network
    ports:
      - "127.0.0.1:5432:5432"

  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  bot:
    build: .
    restart: always
    command: python -m app.bot.main
    env_file: .env
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }

  worker:
    build: .
    restart: always
    # concurrency thấp vì VPS 2 vCPU
    command: celery -A app.worker.celery_app worker --loglevel=info --concurrency=2
    env_file: .env
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }

  beat:
    build: .
    restart: always
    command: celery -A app.worker.celery_app beat --loglevel=info
    env_file: .env
    depends_on:
      redis: { condition: service_healthy }

  web:
    build: .
    restart: always
    command: uvicorn app.web.main:app --host 0.0.0.0 --port 8000 --workers 2
    env_file: .env
    expose:
      - "8000"
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/certbot:/etc/letsencrypt:ro
    depends_on:
      - web

volumes:
  pgdata:
  redisdata:
```

### 5.2. `.env.example`

```dotenv
# Telegram
BOT_TOKEN=123456:ABC-YourTelegramBotToken

# Database
POSTGRES_USER=botadmin
POSTGRES_PASSWORD=changeme_strong
POSTGRES_DB=botnews
DATABASE_URL=postgresql+asyncpg://botadmin:changeme_strong@postgres:5432/botnews

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# Web Admin
JWT_SECRET=super_secret_random_string
ADMIN_DEFAULT_USER=admin

# External APIs
API_FOOTBALL_KEY=your_key
NEWSAPI_KEY=your_key
```

### 5.3. `app/core/config.py` — Cấu hình tập trung

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    BOT_TOKEN: str
    DATABASE_URL: str
    REDIS_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    JWT_SECRET: str = "change-me"

    # External
    API_FOOTBALL_KEY: str | None = None
    NEWSAPI_KEY: str | None = None


settings = Settings()
```

### 5.4. `app/core/database.py` — Async DB session

```python
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, pool_size=10, max_overflow=20)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

### 5.5. `app/models/user.py` — Model User

```python
from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    full_name: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|expired|banned
    plan: Mapped[str] = mapped_column(String(50), default="free")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

### 5.6. ⭐ `app/bot/main.py` — Khởi tạo Bot + kết nối DB, nhận diện `user_id`

```python
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes, AIORateLimiter,
)
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.user import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_or_create_user(update: Update) -> User:
    """Nhận diện user_id từ Telegram → upsert vào DB."""
    tg = update.effective_user
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == tg.id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                telegram_id=tg.id,
                username=tg.username,
                full_name=tg.full_name,
                status="active",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info("New user registered: %s (%s)", tg.id, tg.username)
        return user


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await get_or_create_user(update)

    if user.status == "banned":
        await update.message.reply_text("⛔ Tài khoản của bạn đã bị khoá.")
        return

    await update.message.reply_text(
        f"👋 Chào {user.full_name}!\n"
        f"🆔 User ID của bạn: `{user.telegram_id}`\n"
        f"📦 Gói cước: {user.plan}\n\n"
        "Gõ /help để xem hướng dẫn.",
        parse_mode="Markdown",
    )


def build_application() -> Application:
    app = (
        Application.builder()
        .token(settings.BOT_TOKEN)
        .rate_limiter(AIORateLimiter())  # ✅ chống rate-limit tự động
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    # TODO: thêm handlers schedule/crypto/gold/football/news...
    return app


def main() -> None:
    app = build_application()
    logger.info("🤖 Bot started (long polling)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
```

### 5.7. `app/bot/decorators.py` — Phân quyền module (kết nối SaaS logic)

```python
from functools import wraps
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.subscription import SubscriptionModule


def require_module(module_key: str):
    """Chỉ cho phép nếu Admin đã bật module này cho user & user còn hạn."""
    def decorator(handler):
        @wraps(handler)
        async def wrapper(update, context, *args, **kwargs):
            tg_id = update.effective_user.id
            async with AsyncSessionLocal() as session:
                user = (await session.execute(
                    select(User).where(User.telegram_id == tg_id)
                )).scalar_one_or_none()

                if not user or user.status != "active":
                    await update.message.reply_text("⛔ Tài khoản chưa kích hoạt hoặc đã hết hạn.")
                    return

                mod = (await session.execute(
                    select(SubscriptionModule).where(
                        SubscriptionModule.user_id == user.id,
                        SubscriptionModule.module_key == module_key,
                        SubscriptionModule.is_enabled.is_(True),
                    )
                )).scalar_one_or_none()

                if not mod:
                    await update.message.reply_text(
                        f"🔒 Tính năng '{module_key}' chưa được kích hoạt cho gói của bạn.\n"
                        "Liên hệ Admin để nâng cấp."
                    )
                    return
            return await handler(update, context, *args, **kwargs)
        return wrapper
    return decorator

# Sử dụng:
# @require_module("crypto")
# async def crypto_handler(update, context): ...
```

### 5.8. `app/worker/celery_app.py` + Beat schedule

```python
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "botnews",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.worker.tasks.daily_digest",
        "app.worker.tasks.schedule_reminder",
        "app.worker.tasks.crypto_alert",
        "app.worker.tasks.gold_alert",
        "app.worker.tasks.send_message",
    ],
)

celery_app.conf.update(
    timezone="Asia/Ho_Chi_Minh",
    task_default_rate_limit="25/s",   # ✅ giữ dưới ngưỡng Telegram 30/s
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    "daily-digest-7am": {
        "task": "app.worker.tasks.daily_digest.send_daily_digest",
        "schedule": crontab(hour=7, minute=0),
    },
    "schedule-reminder-every-minute": {
        "task": "app.worker.tasks.schedule_reminder.check_reminders",
        "schedule": crontab(minute="*"),
    },
    "crypto-poll-every-2min": {
        "task": "app.worker.tasks.crypto_alert.poll_and_alert",
        "schedule": crontab(minute="*/2"),
    },
    "gold-poll-every-10min": {
        "task": "app.worker.tasks.gold_alert.poll_and_alert",
        "schedule": crontab(minute="*/10"),
    },
}
```

### 5.9. `app/worker/tasks/send_message.py` — Gửi message an toàn (rate-limited)

```python
import asyncio
from telegram import Bot
from telegram.error import RetryAfter, Forbidden
from app.core.config import settings
from app.worker.celery_app import celery_app

_bot = Bot(token=settings.BOT_TOKEN)


@celery_app.task(bind=True, max_retries=5, rate_limit="25/s")
def send_message_task(self, chat_id: int, text: str):
    """Task gửi 1 message, tự retry khi bị Telegram giới hạn."""
    async def _send():
        try:
            await _bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
        except RetryAfter as e:
            raise self.retry(countdown=int(e.retry_after) + 1)
        except Forbidden:
            # User đã block bot → có thể đánh dấu inactive
            pass

    asyncio.run(_send())
```

### 5.10. `app/web/main.py` — Khung Web Admin (FastAPI)

```python
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from app.web.routers import auth, dashboard, users, modules, subscriptions, logs
from app.web.deps import get_current_admin

app = FastAPI(title="BotNews Admin", docs_url=None)  # tắt docs công khai

app.mount("/static", StaticFiles(directory="app/web/static"), name="static")

app.include_router(auth.router, tags=["auth"])
app.include_router(dashboard.router, dependencies=[Depends(get_current_admin)])
app.include_router(users.router, prefix="/users", dependencies=[Depends(get_current_admin)])
app.include_router(modules.router, prefix="/modules", dependencies=[Depends(get_current_admin)])
app.include_router(subscriptions.router, prefix="/subscriptions", dependencies=[Depends(get_current_admin)])
app.include_router(logs.router, prefix="/logs", dependencies=[Depends(get_current_admin)])
```

### 5.11. `app/web/routers/subscriptions.py` — Gia hạn gói (+30/+365)

```python
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select
from app.core.database import get_session
from app.models.user import User

router = APIRouter()


@router.post("/extend/{user_id}")
async def extend_plan(user_id: int, days: int, session=Depends(get_session)):
    """days = 30 hoặc 365. Cộng dồn từ hạn hiện tại (nếu còn) hoặc từ hôm nay."""
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one()
    now = datetime.now(timezone.utc)
    base = user.expires_at if (user.expires_at and user.expires_at > now) else now
    user.expires_at = base + timedelta(days=days)
    user.status = "active"
    await session.commit()
    return {"user_id": user_id, "new_expiry": user.expires_at.isoformat()}
```

### 5.12. `Dockerfile`

```dockerfile
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "app.bot.main"]
```

### 5.13. `nginx/nginx.conf` (rút gọn — Web Admin qua HTTPS)

```nginx
events {}
http {
    server {
        listen 80;
        server_name admin.yourdomain.com;
        location /.well-known/acme-challenge/ { root /var/www/certbot; }
        location / { return 301 https://$host$request_uri; }
    }
    server {
        listen 443 ssl;
        server_name admin.yourdomain.com;
        ssl_certificate     /etc/letsencrypt/live/admin.yourdomain.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/admin.yourdomain.com/privkey.pem;

        # (tùy chọn) chỉ cho IP của bạn truy cập
        # allow 1.2.3.4; deny all;

        location / {
            proxy_pass http://web:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

---

## 6. GHI CHÚ VẬN HÀNH & TỐI ƯU CHO VPS 2vCPU/4GB

| Hạng mục | Khuyến nghị |
|---|---|
| **Celery concurrency** | `--concurrency=2` (khớp 2 vCPU), tránh OOM. |
| **PostgreSQL** | `shared_buffers=512MB`, `max_connections=50`. |
| **Redis** | `maxmemory 512mb`, policy `allkeys-lru`. |
| **Uvicorn (web)** | `--workers 2`. |
| **Poll giá** | Crypto 2', Vàng 10', tránh gọi API quá dày (rate-limit nguồn). |
| **Dedup alert** | Redis key `alert:{user}:{symbol}` TTL 15–30' → không spam. |
| **Backup** | `pg_dump` cron hằng ngày, giữ 7 bản, đẩy ra ngoài VPS. |
| **Bảo mật Admin** | HTTPS + IP allowlist + mật khẩu mạnh + 2FA. Không expose port DB/Redis. |
| **Monitoring** | `docker stats`, log rotation, cân nhắc Uptime Kuma (nhẹ). |

---

## 7. THỨ TỰ KHỞI ĐỘNG NHANH (Quick Start)

```bash
# 1. Chuẩn bị
cp .env.example .env         # điền BOT_TOKEN, mật khẩu DB...

# 2. Khởi động hạ tầng
docker compose up -d postgres redis

# 3. Migration DB
docker compose run --rm bot alembic upgrade head

# 4. Tạo admin đầu tiên
docker compose run --rm bot python scripts/init_admin.py

# 5. Chạy toàn bộ
docker compose up -d

# 6. Kiểm tra
docker compose logs -f bot
```

---

**Tổng kết:** Kiến trúc tách 4 tiến trình (bot / worker / beat / web) chung 1 codebase — dễ maintain một mình, mở rộng được, và điểm mấu chốt SaaS nằm ở bảng `subscription_modules` + decorator `@require_module` giúp bạn bán từng tính năng linh hoạt qua Web Admin.
