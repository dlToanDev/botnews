# Thiết kế: Giá vàng — thông báo theo giờ (per-account + hệ thống) + /vang đẹp

**Ngày:** 2026-08-29 · **Nhánh:** feat/web-admin-redesign

## Mục tiêu
- Thông báo giá vàng tự động theo **giờ cố định** hằng ngày.
- Cấu hình trên web: **per-account** và **cả hệ thống** (per-account ghi đè).
- `/vang` hiện Mua & Bán, trình bày đẹp hơn.

## Kiến trúc
### 1. Hạ tầng cấu hình hệ thống (mới)
Bảng key-value `system_settings(key PK, value JSONB, updated_at)` + model +
migration. Service `system_settings_service.get(session,key,default)` /
`set(session,key,value)`. Gold dưới key `gold_notify = {"enabled":bool,"times":[...]}`.

### 2. Per-account
`UserSettings.gold_times` (JSONB list "HH:MM") + migration.
Quy tắc: user có times → dùng; trống → theo hệ thống (nếu enabled).

### 3. gold_service.py (thuần, test được)
- `parse_times(raw) -> list[str]`: tách theo dấu phẩy/space, chuẩn hoá "HH:MM",
  validate 00–23:00–59, dedup+sort; sai → ValueError; rỗng → [].
- `effective_times(user_times, sys_enabled, sys_times) -> list[str]`.
- `format_gold_prices(items, when_str) -> str`: card Markdown, mỗi loại Mua & Bán.

### 4. Web
- users.py: POST `/users/{id}/gold` (Form `gold_times` chuỗi) → parse → lưu.
  user_detail.html: card "🥇 Cài đặt Giá vàng" (ô nhập giờ, trống=theo hệ thống).
- Router mới `settings.py`: GET `/settings` + POST `/settings/gold`
  (enabled + times). Template `settings.html`. Đăng ký ở web/main.py + link menu (base.html). Chỉ admin.

### 5. Worker `gold_digest` (mỗi phút)
now HH:MM (giờ VN). Lấy `get_gold_prices()` 1 lần. Với mỗi user module gold:
times = effective_times(user.gold_times, sys.enabled, sys.times); nếu HH:MM ∈ times
→ gửi format_gold_prices, dedup `golddigest:{uid}:{date}:{hhmm}` (TTL ~2h).
Beat `crontab(minute="*")`. Giữ nguyên gold_alert (ngưỡng).

### 6. /vang
gold_cmd dùng `format_gold_prices(items, now)`.

## Kiểm thử
- Thuần: parse_times (hợp lệ/sai/rỗng), effective_times (3 nhánh), format_gold_prices.
- Migration up/down; live smoke chọn user theo giờ (không gửi).

## Ngoài phạm vi
- Đổi nguồn giá; per-item threshold; opt-out riêng khi hệ thống bật.
