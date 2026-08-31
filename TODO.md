# 📋 Việc cần làm tiếp — BotNews

_Cập nhật: 2026-08-26. Nhánh đang làm: `feat/web-admin-redesign` (chưa commit)._

Tất cả tính năng bên dưới **đã code + test xong**, chỉ còn **cấu hình để chạy thật** và vài tính năng backlog.

---

## 🔴 Ưu tiên 1 — Bật các tính năng đã làm (chỉ cần cấu hình)

### 1. Trợ lý AI (Gemini) — CHỈ còn thiếu API key
- [ ] Lấy key miễn phí: **Google AI Studio** (https://aistudio.google.com) → *Get API key*
- [ ] Điền vào `.env`:
  ```env
  GEMINI_API_KEY=<key_của_bạn>
  GEMINI_MODEL=gemini-2.0-flash
  ```
- [ ] `docker compose up -d --build bot`
- [ ] Gán module **AI** cho tài khoản mình (Web Admin `/users/<id>` hoặc mua qua `/muagoi`)
- [ ] Test: `/ai xin chào` · `/ainews` · `/aigold` · `/aicrypto BTCUSDT`
- Giới hạn: 30 câu/user/ngày; free Gemini 15 req/phút, 1.500 req/ngày.

### 2. Thanh toán SePay — còn thiếu WEBHOOK + DOMAIN
- [x] Đã điền `.env`: SEPAY_WEBHOOK_APIKEY / ACCOUNT_NUMBER / BANK_CODE / ACCOUNT_NAME
- [ ] **Quyết định cách lộ webhook ra internet** (đang vướng — xem mục dưới)
- [ ] Tạo **Webhook** trong dashboard SePay:
  - URL: `https://<domain>/api/sepay/webhook`
  - Sự kiện: **Money In**
  - Bảo mật: **API Key** = đúng `SEPAY_WEBHOOK_APIKEY`
- [ ] Bấm **Send Test** trên SePay → server phải trả `{"success": true}`
- [ ] Test tiền thật: `/muagoi` → mua 1 dịch vụ 20k → quét QR → chờ 1-2 phút bot tự nâng cấp
- [ ] Kiểm tra Web Admin `/orders` thấy đơn `paid`

### 3. Chốt DOMAIN / cách expose (đang bỏ ngỏ)
Chọn 1 trong 3 (đã bàn, chưa quyết):
- [ ] **Cloudflare Tunnel** — test ngay, không cần domain (URL tạm, đổi khi restart)
- [ ] **VPS có IP public + domain miễn phí** (DuckDNS) + HTTPS Let's Encrypt (repo có sẵn `scripts/init_letsencrypt.sh`)
- [ ] **Mua domain riêng** → trỏ DNS + cấu hình `nginx/` route `/api/sepay/webhook` về service `web`
> Ghi chú: cần nói cho Claude biết **máy chạy bot là máy cá nhân hay VPS**, và **mục đích test hay chạy thật** để chọn đúng.

---

## 🟡 Ưu tiên 2 — Tính năng backlog (đã bàn, chưa code)

### 4. Bóng đá theo giải + AI (cần API-Football key)
- [ ] Đăng ký key ở `dashboard.api-football.com` → điền `API_FOOTBALL_KEY` vào `.env`
- [ ] Lệnh theo giải: `/epl`, `/laliga`, `/seriea`, `/bundesliga`, `/ligue1`, `/vleague`
  - Menu con: **Lịch vòng này** / **Kết quả vòng này** (chưa đá → "chưa đá"; đã đá → tỉ số + cầu thủ ghi bàn) / **BXH**
- [ ] `/aibongda` — AI nhận định/tóm tắt vòng đấu (nối vào v2)
- League ID (API-Football): EPL 39, La Liga 140, Serie A 135, Bundesliga 78, Ligue 1 61, V.League 1 ~340 (xác nhận qua `/leagues?country=Vietnam`)
- ⚠️ Free chỉ 100 req/ngày → phải cache Redis.

### 5. AI v3 — Hiểu ngôn ngữ tự nhiên
- [ ] Người dùng gõ "giá vàng hôm nay" → AI tự hiểu & gọi đúng lệnh (không cần /gold)
- Phức tạp & dễ sai nhất; làm sau cùng.

### 6. Cải thiện nhỏ (tuỳ chọn)
- [ ] Beat task tự chuyển đơn `pending` quá hạn → `expired`
- [ ] Nút "Đã chuyển / Kiểm tra lại" trong bot sau khi hiện QR
- [ ] Thêm biểu đồ **doanh thu** vào Dashboard (từ bảng `orders`)
- [ ] Backfill module `schedule` cho user CŨ (hiện chỉ user mới tự có Lịch cá nhân)

---

## 🔧 Ghi nhớ vận hành
- Sửa code xong luôn phải rebuild: `docker compose up -d --build web bot`
- Chạy migration DB: `docker compose exec web alembic upgrade head`
- Xem log: `docker compose logs bot --tail 50` / `docker compose logs web --tail 50`
- Web Admin: http://localhost:8000 (sau này qua domain)

## 📦 Git — nhớ commit
Toàn bộ công việc đang ở nhánh `feat/web-admin-redesign` và **chưa commit**. Khi ưng, commit lại theo từng phần:
- Redesign Web Admin (dashboard/users/detail + gói dịch vụ)
- Lịch mặc định cho user mới + bỏ nút bật/tắt tất cả
- Menu lệnh Telegram (Anh + Việt)
- Thanh toán SePay (mua gói trong bot + webhook + trang /orders)
- Trợ lý AI Gemini v1 (chat) + v2 (tóm tắt/phân tích)

## 📄 Spec chi tiết (đã lưu)
- `docs/superpowers/specs/2026-08-26-web-admin-redesign-design.md`
- `docs/superpowers/specs/2026-08-26-in-bot-payment-sepay-design.md`
- `docs/superpowers/specs/2026-08-26-ai-assistant-gemini-design.md`
