# Mua gói trong Bot + QR + tự nâng cấp (SePay webhook)

Ngày: 2026-08-26 · Nhánh: `feat/web-admin-redesign` (nối tiếp)

## Mục tiêu
Người dùng mua dịch vụ ngay trong bot Telegram: chọn sản phẩm → bot gửi **QR VietQR**
→ user chuyển khoản → **SePay** phát hiện tiền về, bắn webhook → hệ thống **tự bật
module + gia hạn 30 ngày** và nhắn xác nhận cho user.

## Catalog (đã chốt) — hạn dùng 30 ngày/lần mua
| Sản phẩm | key | modules mở | Giá |
|---|---|---|---|
| 🥇 Giá vàng | `gold` | gold | 20.000 |
| ₿ Crypto | `crypto` | crypto | 20.000 |
| ⚽ Bóng đá | `football` | football | 20.000 |
| 📰 Tin tức | `news` | news | 20.000 |
| 💰 Combo Tài chính | `combo_finance` | gold, crypto | 40.000 |
| 🎬 Combo Giải trí | `combo_entertain` | football, news | 40.000 |
| 🎯 Full | `full` | gold, crypto, football, news | 70.000 |

📅 Lịch cá nhân: miễn phí, không bán (đã default-on cho mọi tài khoản).

## Mô hình hết hạn (v1)
**1 mốc chung** `user.expires_at`. Thanh toán thành công → bật các module của sản phẩm
+ đặt `status=active` + `expires_at = max(now, expires_at) + 30 ngày`. Xét quyền vẫn
qua `module_repo.eligible_users` (active + còn hạn + module bật).

## Thành phần

### 1. Model `Order` (bảng `orders`)
`id, user_id(FK), code(unique), item_key, item_label, modules(JSONB), amount(int),
status('pending'|'paid'|'expired'), created_at, paid_at, expires_at, raw(JSONB)`.
- `code` = `f"BOT{id}"` (nhét vào nội dung CK, dùng để khớp webhook).

### 2. Catalog config — `app/core/constants.py`
`SERVICE_PRICE/COMBO_PRICE/FULL_PRICE`, `SUBSCRIPTION_DAYS=30`, `PRODUCTS`, `PRODUCTS_BY_KEY`.

### 3. Repo `order_repo.py`
`create`, `get_by_id`, `get_by_code`, `mark_paid`, `list_recent` (cho admin).

### 4. Service `payment_service.py`
- `create_order(user_id, product_key) -> Order` (tạo + set code + amount + expires 15').
- `fulfill_order(order, raw) -> User` (idempotent): nếu đã paid → bỏ qua; else bật
  modules + gia hạn 30 ngày + mark paid + ghi log `order_paid`.
- `build_qr_url(order)`: ảnh QR SePay
  `https://qr.sepay.vn/img?acc=<acc>&bank=<bank>&amount=<amount>&des=<code>`.

### 5. Bot `handlers/payment.py`
- `/muagoi` (+ `/buy`, thêm vào Menu + VI_ALIAS): gửi inline keyboard nhóm Lẻ/Combo/Full.
- CallbackQuery `buy:<product_key>`: tạo đơn → gửi ảnh QR + số tiền + nội dung CK (mã đơn)
  + hướng dẫn "Bot sẽ tự nâng cấp sau khi nhận tiền (1-2 phút)".
- Đăng ký `CallbackQueryHandler` trong `bot/main.py`.

### 6. Webhook `web/routers/payment.py`
- `POST /api/sepay/webhook`, xác thực header `Authorization: Apikey <SEPAY_WEBHOOK_APIKEY>` → sai 401.
- Body SePay: `transferAmount`, `content`/`description`, `id` (mã GD)...
- Tìm `code` trong `content` (regex `BOT\d+`) → `order_repo.get_by_code`.
- Điều kiện mở: đơn tồn tại, chưa paid, `transferAmount >= order.amount`.
- Gọi `fulfill_order` → rồi `notify_user` (Telegram sendMessage qua BOT_TOKEN, httpx, best-effort).
- Luôn trả `{"success": true}` khi đã xử lý/không khớp (tránh SePay retry vô hạn); 401 chỉ khi sai key.
- **Tiền paid nhưng < giá / không khớp mã** → ghi log `order_unmatched`, không mở (admin xử lý tay).

### 7. Admin — trang "Đơn hàng"
`/orders`: bảng đơn gần đây (user, sản phẩm, số tiền, trạng thái, thời gian). Thêm mục nav.

### 8. Config `.env` (tính năng TẮT nếu thiếu)
`SEPAY_WEBHOOK_APIKEY, SEPAY_ACCOUNT_NUMBER, SEPAY_BANK_CODE, SEPAY_ACCOUNT_NAME`.
Nếu chưa cấu hình đủ → `/muagoi` báo "Tính năng thanh toán chưa được bật".

## Testing / verify
- Unit: `create_order` (code/amount đúng), `fulfill_order` idempotent (gọi 2 lần chỉ gia hạn 1 lần), catalog hợp lệ.
- Tích hợp: **giả lập** POST webhook (đúng/sai Apikey, đủ/thiếu tiền, gọi lại lần 2) → kiểm module bật + expires_at +30 ngày + đơn `paid`.
- QR URL đúng định dạng.
- Chạy được không cần SePay thật (dùng payload giả). Golive cần điền `.env` SePay + trỏ webhook về `https://<domain>/api/sepay/webhook`.

## Ngoài phạm vi (v1)
Hạn riêng từng module; hoàn tiền; nhiều ngân hàng; mã giảm giá.
