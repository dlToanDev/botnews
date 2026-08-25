# Phase 3 — Real-time Integrations (4 Module Dữ liệu)

> ⏱️ **Thời lượng:** Tuần 5–7
> 🎯 **Mục tiêu:** Tích hợp Crypto, Vàng, Bóng đá, Tin tức qua Adapter + Celery; chỉ gửi cho user có module bật & còn hạn.
> 📦 **Deliverable:** Bot đầy đủ tính năng SaaS, cảnh báo real-time đúng phân quyền, không spam.
> 🔗 **Phụ thuộc:** Phase 2 hoàn thành (đã có `@require_module` + toggle).

---

## ✅ TRẠNG THÁI: ĐÃ THỰC THI (2026-08-25)

Đã tích hợp 4 module qua Adapter + Celery, test **với dữ liệu LIVE thật**.

**Nguồn dữ liệu chốt:**
| Module | Nguồn | Key? |
|---|---|---|
| ₿ Crypto | Binance REST `/ticker/24hr` | Không |
| 🥇 Vàng | PNJ edge API (gồm SJC + nhẫn) | Không |
| 📰 Tin tức | RSS (VnExpress + Tuổi Trẻ) qua feedparser | Không |
| ⚽ Bóng đá | API-Football | **Cần** `API_FOOTBALL_KEY` |

**Đã kiểm chứng (`scripts/smoke_phase3.py` — 9/9 OK, dữ liệu live):**
- Crypto live BTCUSDT (~$80.8k), Gold live 18 sản phẩm, News RSS 20 tin.
- Football báo đúng "chưa cấu hình key".
- `eligible_users(module)` lọc đúng (active + còn hạn + module bật).
- Crypto/Gold/News alert **gửi đúng** cho user đủ điều kiện; **dedup** chặn gửi lặp.
- Football `is_configured=False` → task no-op an toàn.
- `pytest`: **11/11** (parser + security + integrations).
- Pipeline **beat→worker chạy thật**: beat tự phát crypto (2') & news (15'); worker hit API live thành công.

**Nền tảng:** `integrations/base.py` (HTTP retry + cache Redis + **stale fallback** khi API lỗi), `core/dedup.py` (SET NX EX).

**Lệnh bot mới:** `/crypto /setcrypto /gold /football /setteam /news /setnews` (đều gated `@require_module`).

**Beat jobs:** crypto 2', gold 10', football-live 2', news 15' (+ digest 7h, reminder 1', expire 00:05).

**⚠️ VIỆC BẠN CẦN LÀM (tuỳ chọn):**
- Muốn dùng **Bóng đá**: đăng ký key tại api-sports.io, điền `API_FOOTBALL_KEY` vào `.env`, `docker compose up -d --build worker beat bot`.
- Chạy bot LIVE: điền `BOT_TOKEN` (như Phase 1).

---

## Task list (làm tuần tự)

### 3.1. Nền tảng Integration
- [ ] `app/integrations/base.py`: `BaseAdapter` với `async fetch()`, timeout, retry, cache Redis (TTL).
- [ ] Helper dedup alert: Redis key `alert:{user}:{topic}` TTL 15–30' (tránh spam cùng cảnh báo).
- [ ] Helper query "user đủ điều kiện nhận module X": join `users` + `subscription_modules` (enabled + active + còn hạn).

### 3.2. Module Crypto (₿)
- [ ] `app/integrations/crypto.py`: adapter Binance REST (giá) + option WebSocket; fallback CoinGecko (giá VND).
- [ ] Handler `/crypto` — xem giá hiện tại; `/setcrypto BTCUSDT 5` — thêm vào `crypto_watchlist` với ngưỡng %.
- [ ] `app/worker/tasks/crypto_alert.py` — poll mỗi 2': so % thay đổi vs ngưỡng → alert (dedup Redis).
- [ ] Áp `@require_module("crypto")`.

### 3.3. Module Giá vàng (🥇)
- [ ] `app/integrations/gold.py`: scrape SJC + PNJ (BeautifulSoup) hoặc API tổng hợp; cache Redis 5–10'.
- [ ] Xử lý lỗi khi web đổi cấu trúc (log + giữ giá cache cũ).
- [ ] Handler `/gold` — xem giá mua/bán SJC & PNJ.
- [ ] `app/worker/tasks/gold_alert.py` — poll mỗi 10': so ngưỡng `gold_alert_pct`.
- [ ] Áp `@require_module("gold")`.

### 3.4. Module Bóng đá (⚽)
- [ ] `app/integrations/football.py`: API-Football (lịch, live score, kết quả); cache lịch trong ngày.
- [ ] Handler `/football` — lịch hôm nay + kết quả; `/setteam Arsenal` — thêm `favorite_teams`.
- [ ] `app/worker/tasks/football_live.py` — trong khung giờ có trận: push live score/ bàn thắng cho user theo dõi.
- [ ] Chú ý quota API (free 100 req/ngày) → cache mạnh, chỉ poll khi có trận.
- [ ] Áp `@require_module("football")`.

### 3.5. Module Tin tức (📰)
- [ ] `app/integrations/news.py`: đọc RSS (VnExpress/Reuters/BBC) + option NewsAPI; dedup theo link.
- [ ] Handler `/news` — top tin nóng; `/setnews bitcoin,fed` — set `news_keywords`.
- [ ] `app/worker/tasks/news_push.py` — định kỳ: lọc theo keyword → push tin mới (dedup Redis theo URL).
- [ ] Áp `@require_module("news")`.

### 3.6. Tối ưu gửi hàng loạt
- [ ] Mọi task alert: query danh sách user đủ điều kiện → đẩy từng message qua `send_message_task` (rate-limited).
- [ ] Gộp batch, giữ tổng < 25 msg/s; log số message gửi mỗi lần.
- [ ] Thêm các task vào `beat_schedule` (mục 5.8).

## ✅ Definition of Done
- [x] `/crypto`, `/gold`, `/news` trả dữ liệu **live thật**; `/football` cần key (báo rõ khi thiếu).
- [x] Set watchlist/team/keyword lưu vào `user_settings` (`settings_service`).
- [x] Alert chỉ đến user có module bật + còn hạn (`eligible_users` verify).
- [x] Không nhận trùng cùng 1 cảnh báo trong TTL dedup (`core/dedup.py`).
- [x] Nguồn API lỗi → dùng cache cũ (stale fallback), có log, không crash.
- [x] Gửi qua Celery `send_message_task` (rate-limit 25/s) — dưới ngưỡng Telegram.
