# Phase 1 — Core Bot & Lịch Cá Nhân

> ⏱️ **Thời lượng:** Tuần 1–2
> 🎯 **Mục tiêu:** Bot nhận diện user, quản lý lịch cá nhân, báo lịch 7h sáng + nhắc trước giờ làm.
> 📦 **Deliverable:** Người dùng `/start` → được lưu DB; nhập lịch; nhận digest sáng + reminder tự động.
> 🔗 **Phụ thuộc:** Phase 0 hoàn thành.

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
- [ ] `/start` lưu user vào bảng `users` (verify bằng query DB).
- [ ] Thêm được lịch, `/today` và `/mylist` trả đúng dữ liệu.
- [ ] Job 7h sáng gửi digest (test bằng cách chỉnh giờ hoặc gọi task tay).
- [ ] Reminder gửi trước giờ đúng số phút cấu hình, không gửi lặp (nhờ `is_notified`).
- [ ] `docker compose up -d` → 5 service (postgres, redis, bot, worker, beat) chạy ổn.
- [ ] Không bị Telegram rate-limit khi gửi digest cho nhiều user (test với 5–10 user giả).
