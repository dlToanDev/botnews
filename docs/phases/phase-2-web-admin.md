# Phase 2 — Web Admin Dashboard & Phân Quyền SaaS

> ⏱️ **Thời lượng:** Tuần 3–4
> 🎯 **Mục tiêu:** Admin quản lý user, bật/tắt module theo user, gia hạn gói cước. Bot tôn trọng phân quyền.
> 📦 **Deliverable:** Web admin (HTTPS nội bộ) hoạt động; bot chặn user chưa mua/ hết hạn qua `@require_module`.
> 🔗 **Phụ thuộc:** Phase 1 hoàn thành.
> 🖥️ **Frontend:** Jinja2 + HTMX + Tailwind (đã chốt).

---

## ✅ TRẠNG THÁI: ĐÃ THỰC THI (2026-08-25)

Web Admin đã chạy thật và test end-to-end bằng `curl` (web **không cần** BOT_TOKEN).

**Đã kiểm chứng:**
- Migration thêm bảng `subscription_modules`, `admins` → tổng **7 bảng**.
- `init_admin.py` tạo admin OK.
- **Auth**: `/` chưa login → 303 về `/login`; sai mật khẩu → 401; đúng → 303 + set-cookie (JWT HttpOnly); trang trong bị chặn nếu chưa login.
- **Dashboard**: hiển thị tổng/active/expired/banned + thống kê module.
- **Quản lý User**: list + search; trang chi tiết.
- **Feature Toggle** (HTMX): bấm bật module `crypto` → partial trả "Đang bật"; DB `is_enabled=t`, có `enabled_at`.
- **Gia hạn**: `+30 ngày` → `expires_at` +30, status→active (verify DB).
- **Đổi status**: → `banned` (verify DB).
- **Logs**: hiện `module_toggle`, `plan_extend`, `status_change`.
- **Bot gating**: `has_module(crypto)=True / gold=False`; `@require_module` + 4 stub handlers (`/crypto /gold /football /news`).
- **Auto-expire**: task `expire_overdue` chuyển user quá hạn → `expired` (test OK). Beat lịch `expire-users-daily` (00:05).
- `pytest`: **8/8 pass** (parser + security).

**Truy cập web (local):** http://127.0.0.1:8000 — tài khoản admin đã tạo (mật khẩu bạn đặt qua `ADMIN_PASSWORD`).

**⚠️ Lưu ý:** Container `bot` vẫn cần `BOT_TOKEN` thật để chạy live (Web/Worker/Beat đã chạy đầy đủ).

---

## Task list (làm tuần tự)

### 2.1. Models & migration cho SaaS
- [ ] `app/models/subscription.py`: `SubscriptionModule` (mục 2.4).
- [ ] `app/models/admin.py`: `Admin` (mục 2.6).
- [ ] `alembic revision --autogenerate -m "add subscription_modules and admins"` → upgrade.
- [ ] Định nghĩa hằng số module keys: `schedule, gold, crypto, football, news`.

### 2.2. Auth Admin
- [ ] `app/core/security.py`: hash bcrypt, verify, tạo/verify JWT (hoặc session cookie).
- [ ] `scripts/init_admin.py`: tạo tài khoản admin đầu tiên (đọc user/pass từ prompt hoặc env).
- [ ] `app/web/routers/auth.py`: `/login` (form), `/logout`; set cookie/JWT.
- [ ] `app/web/deps.py`: `get_current_admin` — chặn mọi route nếu chưa đăng nhập.

### 2.3. Web app skeleton (FastAPI + Jinja2 + HTMX)
- [ ] `app/web/main.py` (mục 5.10) + mount static + templates.
- [ ] `templates/base.html` (layout + Tailwind CDN + HTMX script + sidebar).
- [ ] `templates/login.html`.
- [ ] Thêm service `web` vào `docker-compose.yml` (expose 8000 nội bộ).

### 2.4. Trang Dashboard (tổng quan)
- [ ] `app/web/routers/dashboard.py`: đếm tổng user, active/expired/banned, số user theo từng module.
- [ ] `templates/dashboard.html`: card thống kê.

### 2.5. Quản lý User
- [ ] `app/web/routers/users.py`: list (phân trang + search theo `telegram_id`/username), chi tiết user.
- [ ] Đổi `status`: active / expired / banned (HTMX inline).
- [ ] `templates/users.html`, `templates/user_detail.html`.

### 2.6. Feature Toggle (⭐ cốt lõi SaaS)
- [ ] `app/web/routers/modules.py`: bật/tắt từng `module_key` cho 1 user (upsert `subscription_modules`, HTMX checkbox).
- [ ] `app/services/subscription_service.py`: `set_module(user_id, key, enabled)`, `list_modules(user_id)`, `has_module(user_id, key)`.
- [ ] Hiển thị 5 checkbox module trong trang chi tiết user.

### 2.7. Gia hạn gói cước
- [ ] `app/web/routers/subscriptions.py`: nút `+30 ngày`, `+365 ngày` (mục 5.11).
- [ ] Logic cộng dồn từ `expires_at` hiện tại (nếu còn hạn) hoặc từ hôm nay.
- [ ] Tự set `status='active'` khi gia hạn; job/định kỳ set `expired` khi quá hạn.
- [ ] Ghi log `plan_extend` vào bảng `logs`.

### 2.8. Trang Logs
- [ ] `app/web/routers/logs.py`: list log, lọc theo `user_id` / `action` / `level`.
- [ ] `templates` bảng log có phân trang.

### 2.9. Kết nối phân quyền vào Bot
- [ ] `app/bot/decorators.py`: `@require_module(key)` + `@require_active` (mục 5.7).
- [ ] Áp decorator lên các handler tính năng (chuẩn bị cho Phase 3).
- [ ] Beat task định kỳ (mỗi ngày): quét user quá `expires_at` → set `status='expired'`.

## ✅ Definition of Done
- [x] Đăng nhập admin thành công; route bị chặn nếu chưa login (303→/login).
- [x] Dashboard hiển thị số liệu đúng.
- [x] Bật/tắt module cho 1 user → lưu DB, phản ánh ngay (HTMX partial).
- [x] Nhấn `+30`/`+365` → `expires_at` cập nhật đúng, log `plan_extend`.
- [x] Bot: `@require_module` chặn user không có module / hết hạn (logic verify OK; chạy live cần token).
- [x] Job `expire_overdue` chuyển user quá hạn sang `expired` + Beat lịch hằng ngày.
