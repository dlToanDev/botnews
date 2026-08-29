# Thiết kế: Cấu hình crypto chi tiết — theo đồng + 3 chế độ/tài khoản

**Ngày:** 2026-08-29 · **Nhánh:** feat/web-admin-redesign

## Mục tiêu
Cấu hình báo giá crypto cụ thể hơn: chọn TỪNG đồng (hệ thống + per-account),
và mỗi tài khoản có 3 chế độ: Theo hệ thống / Tùy chỉnh riêng / Tắt.

## Model (migration)
UserSettings thêm:
- `crypto_notify_mode` String default "system" ("system"|"custom"|"off")
- `crypto_coins` JSONB list ký hiệu (vd ["BTC","ETH"]); rỗng = tất cả
- (`crypto_times` đã có)
System `crypto_notify` thêm `coins` → {enabled, times, coins}.

## Logic (crypto_service, thuần)
- `resolve_notify(mode, user_times, user_coins, sys_enabled, sys_times, sys_coins) -> (times, coins)`
  - off → ([], [])
  - custom → (user_times, user_coins)
  - system → (sys_times, sys_coins) nếu sys_enabled, ngược lại ([], [])
- `select_coins(all_coins, wanted) -> list`: lọc theo symbol; wanted rỗng = tất cả.

## Worker crypto_digest
Mỗi user: (times, coins) = resolve_notify(...); nếu HH:MM ∈ times → gửi
format_price_digest(select_coins(get_tracked(), coins)). Dedup như cũ.

## Web
- /settings card Crypto: enabled + times + 8 ô tick đồng. POST /settings/crypto (coins).
- Trang user card Crypto: radio mode + times + 8 ô tick đồng. POST /users/{id}/crypto.

## Constants
`CRYPTO_SYMBOLS = [k.upper() for k in COIN_IDS]` (BTC…TON) cho checkbox.

## Kiểm thử
- Thuần: resolve_notify (3 chế độ + sys tắt), select_coins (rỗng=tất cả, lọc).
- Migration up/down; smoke web + worker.

## Giữ nguyên
Phần Vàng (chỉ giờ); watchlist ngưỡng /setcrypto.
