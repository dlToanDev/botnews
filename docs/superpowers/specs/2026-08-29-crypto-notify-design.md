# Thiết kế: Báo giá crypto tự động theo giờ (web config)

**Ngày:** 2026-08-29 · **Nhánh:** feat/web-admin-redesign

## Mục tiêu
Báo giá crypto (8 đồng BTC…TON) theo giờ cố định, cấu hình trên web:
cả hệ thống + per-account (per-account ghi đè). Mirror phần Giá vàng.

## Tái dùng
- `system_settings` (key `crypto_notify` = {enabled, times}).
- `gold_service.parse_times`, `gold_service.effective_times` (thuần, tổng quát).
- Pattern worker digest + trang /settings + card trang user.

## Mới / sửa
1. Model `UserSettings.crypto_times` (JSONB "HH:MM") + migration (add column).
2. `system_settings_service`: `get_crypto_notify` / `set_crypto_notify`.
3. `settings_service`: `get_crypto_times` / `set_crypto_times`.
4. `coingecko.get_tracked()` → 8 đồng chuẩn hoá đúng thứ tự COIN_IDS.
5. `app/services/crypto_service.py`: `format_price_digest(coins, when)` (thuần).
6. Worker `crypto_digest` (mỗi phút): module `crypto`; times = crypto_times user
   hoặc hệ thống; khớp HH:MM → gửi, dedup `cryptodigest:{uid}:{date}:{hhmm}`.
   Beat `crontab(minute="*")`. Giữ nguyên watchlist ngưỡng.
7. Web `/settings`: card Crypto (enabled + times) + POST `/settings/crypto`.
8. Trang user: card Crypto (giờ riêng) + POST `/users/{id}/crypto`.

## Kiểm thử
- Thuần: `format_price_digest`. Migration up/down. Smoke web + worker (không gửi).

## Ngoài phạm vi
- Đổi bộ 8 đồng qua web; đụng watchlist ngưỡng `/setcrypto`.
