# Phase 1 — Core Bot & Lịch Cá Nhân

> ⏱️ **Thời lượng:** Tuần 1–2
> 🎯 **Mục tiêu:** Bot nhận diện user, quản lý lịch cá nhân, báo lịch 7h sáng + nhắc trước giờ làm.
> 📦 **Deliverable:** Người dùng `/start` → được lưu DB; nhập lịch; nhận digest sáng + reminder tự động.
> 🔗 **Phụ thuộc:** Phase 0 hoàn thành.

---

## ✅ TRẠNG THÁI: ĐÃ THỰC THI (2026-08-25)

Toàn bộ code Phase 1 đã viết, migrate DB và nghiệm thu tự động.

**Đã kiểm chứng:**
- `alembic upgrade head` → tạo 4 bảng `users / user_settings / schedules / logs` (+ `alembic_version`).
- `scripts/smoke_phase1.py` — **11/11 OK**: tạo user (idempotent), parse input, thêm/liệt kê/xoá lịch, logic reminder (đúng lịch sắp tới, loại lịch xa), ghi log.
- `pytest tests/` — **5/5 pass** (parser).
- **Celery + Beat chạy thật**: Beat phát `check_reminders` mỗi phút → Worker nhận & chạy thành công. `send_daily_digest` lên lịch 7h sáng.
- Import sạch: `bot.main`, `worker.celery_app`, 3 task đăng ký đúng.

**Trạng thái container hiện tại:** `postgres`, `redis`, `worker`, `beat` đang chạy.

**⚠️ VIỆC BẠN CẦN LÀM để chạy bot LIVE (`/start`, `/today`...):**
1. Điền `BOT_TOKEN` thật vào `.env` (từ @BotFather).
2. Khởi động bot:
   ```bash
   docker compose up -d --build bot
   docker compose logs -f bot   # thấy "🤖 Bot đang chạy (long polling)..."
   ```
3. Nhắn `/start` cho bot → kiểm tra user được lưu:
   ```bash
   docker compose exec postgres psql -U botadmin -d botnews -c "SELECT telegram_id, full_name, status FROM users;"
   ```

> Lưu ý: khi tạo migration mới, chạy Alembic kèm quyền user để file không bị root sở hữu:
> `docker run --rm --network botnews_default --env-file .env -v "$PWD":/code --user $(id -u):$(id -g) botnews:dev alembic revision --autogenerate -m "..."`

---

## Task list (làm tuần tự)

### 1.1. Database models & migration
- [ ] Viết `app/models/base.py` (DeclarativeBase).
- [ ] Viết `app/models/user.py`: `User` + `UserSettings` (mục 2.1, 2.2, 5.5).
- [ ] Viết `app/models/schedule.py`: `Schedule` (mục 2.3).
- [ ] Viết `app/models/log.py`: `Log` (mục 2.5).
- [ ] Cấu hình **Alembic** (`alembic init`, sửa `env.py` trỏ `DATABASE_URL` + import models).
- [ ] `alembic revision --autogenerate -m "init core tables"` → `alembic upgrade head`.
- [ ] Kiểm tra bảng đã tạo trong DB.

### 1.2. Repository & Service layer
- [ ] `app/repositories/user_repo.py`: `get_by_telegram_id`, `create`, `update_status`.
- [ ] `app/repositories/schedule_repo.py`: `create`, `list_by_user`, `list_today`, `delete`, `list_upcoming(within_minutes)`.
- [ ] `app/repositories/log_repo.py`: `write(action, level, detail)`.
- [ ] `app/services/user_service.py`: `get_or_create_user`, `is_active`.
- [ ] `app/services/schedule_service.py`: CRUD lịch + parse input (title/time).

### 1.3. Bot core & nhận diện user
- [ ] `app/bot/main.py`: `build_application()` + `AIORateLimiter` + `run_polling` (mục 5.6).
- [ ] Handler `/start`, `/help`: gọi `get_or_create_user`, hiển thị `telegram_id` + gói cước.
- [ ] `app/bot/middlewares.py` hoặc `decorators.py`: `@require_active` kiểm tra `status`.
- [ ] Ghi mọi command vào bảng `logs`.

### 1.4. Module Lịch cá nhân
- [ ] `app/bot/handlers/schedule.py`:
  - [ ] `/addschedule` — hỗ trợ nhập nhanh (VD: `/addschedule 08:00 Đi làm`) + ConversationHandler cho nhập từng bước.
  - [ ] `/today` — liệt kê lịch hôm nay.
  - [ ] `/mylist` — liệt kê tất cả lịch active.
  - [ ] `/delete <id>` — xoá lịch.
- [ ] `app/bot/keyboards.py`: inline keyboard xác nhận/xoá.
- [ ] Xử lý timezone `Asia/Ho_Chi_Minh`.

### 1.5. Celery + Beat (thông báo tự động)
- [ ] `app/worker/celery_app.py` (mục 5.8) + `beat_schedule`.
- [ ] `app/worker/tasks/send_message.py` — gửi message rate-limited (mục 5.9).
- [ ] `app/worker/tasks/daily_digest.py` — **7h sáng**: query lịch hôm nay của từng user → gửi digest.
- [ ] `app/worker/tasks/schedule_reminder.py` — chạy mỗi phút: quét `list_upcoming`, gửi nhắc trước 15–30', đánh dấu `is_notified=TRUE`.
- [ ] Thêm service `bot`, `worker`, `beat` vào `docker-compose.yml`.

### 1.6. Kiểm thử tích hợp
- [ ] Test `/start` tạo user mới trong DB.
- [ ] Test thêm/xem/xoá lịch.
- [ ] Test thủ công trigger `daily_digest` (chạy task tay) → nhận message.
- [ ] Test reminder: tạo lịch cách 16 phút → nhận nhắc đúng giờ.

## ✅ Definition of Done
- [x] Logic `/start` lưu user (idempotent) — verify qua smoke test + query DB.
- [x] Thêm/liệt kê/xoá lịch (`add_schedule`/`list_today`/`list_all`/`delete`) đúng dữ liệu.
- [x] Job digest & reminder tồn tại + Beat phát định kỳ, Worker chạy thành công.
- [x] Reminder chọn đúng lịch trong cửa sổ nhắc, đánh dấu `is_notified` chống gửi lặp.
- [x] `docker compose up -d` → postgres/redis/worker/beat chạy ổn.
- [x] `AIORateLimiter` bật + gửi qua Celery `rate_limit=25/s` (dưới ngưỡng 30/s).
- [ ] Chạy bot LIVE và nhắn `/start` thật — **chờ bạn điền `BOT_TOKEN`** (xem mục "VIỆC BẠN CẦN LÀM").
