# Phase 0 — Chuẩn bị Môi trường & Khung Dự án

> ⏱️ **Thời lượng:** 1–2 ngày
> 🎯 **Mục tiêu:** Có bộ khung repo chạy được (postgres + redis lên container), sẵn sàng để code Phase 1.
> 📦 **Deliverable:** `docker compose up -d postgres redis` chạy OK; project import được `app.core.config`.
> 🔗 **Phụ thuộc:** Không.

## Task list (làm tuần tự)

### 0.1. Khởi tạo repo & cấu trúc thư mục
- [ ] `git init`, tạo `.gitignore` (bỏ `.env`, `__pycache__`, `*.pyc`, `pgdata/`).
- [ ] Tạo cây thư mục `app/` theo mục 3 của roadmap (`core`, `models`, `repositories`, `services`, `integrations`, `bot`, `worker`, `web`).
- [ ] Thêm `__init__.py` vào mọi package.

### 0.2. Dependencies & môi trường Python
- [ ] Tạo `requirements.txt`: `python-telegram-bot[rate-limiter]`, `fastapi`, `uvicorn`, `sqlalchemy`, `asyncpg`, `alembic`, `celery`, `redis`, `pydantic-settings`, `bcrypt`, `httpx`, `beautifulsoup4`, `feedparser`, `jinja2`, `python-multipart`, `pyjwt`.
- [ ] Tạo `pyproject.toml` (metadata + config ruff/black nếu dùng).
- [ ] Tạo virtualenv local để dev/test nhanh (không bắt buộc dùng Docker khi code).

### 0.3. Config tập trung
- [ ] Viết `app/core/config.py` (Pydantic `Settings`, đọc `.env`) — theo mục 5.3.
- [ ] Tạo `.env.example` (mục 5.2) và `.env` thật (điền `BOT_TOKEN` từ @BotFather).
- [ ] Viết `app/core/database.py` (async engine + session) — mục 5.4.
- [ ] Viết `app/core/redis_client.py` (connection pool Redis).
- [ ] Viết `app/core/logging.py` (structured logging cơ bản).

### 0.4. Docker nền tảng
- [ ] Viết `Dockerfile` (mục 5.12).
- [ ] Viết `docker-compose.yml` với **postgres + redis** trước (mục 5.1, chưa cần bot/web).
- [ ] `docker compose up -d postgres redis` → kiểm tra `docker compose ps` healthy.

### 0.5. Bot token & kiểm tra kết nối
- [ ] Tạo bot qua **@BotFather**, lấy token, điền vào `.env`.
- [ ] Viết script test nhỏ gửi 1 message tới chính mình để xác nhận token OK.

## ✅ Definition of Done
- [ ] `docker compose ps` → postgres & redis đều `healthy`.
- [ ] `python -c "from app.core.config import settings; print(settings.BOT_TOKEN[:5])"` chạy không lỗi.
- [ ] Kết nối được PostgreSQL bằng `psql` hoặc DBeaver.
- [ ] Bot token xác nhận hợp lệ (gửi thử 1 message thành công).
- [ ] Cấu trúc thư mục khớp mục 3 roadmap.
