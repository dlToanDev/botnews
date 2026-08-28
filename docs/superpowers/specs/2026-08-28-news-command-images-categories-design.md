# Thiết kế: Nâng cấp lệnh /news — ảnh (album) + lọc theo loại

**Ngày:** 2026-08-28
**Nhánh:** feat/web-admin-redesign

## Mục tiêu

Lệnh `/news` (xem thủ công) hiện chỉ trả danh sách link. Nâng cấp:
- `/news` → 3 tin mới nhất (mọi loại), dạng **album ảnh**.
- `/news <loại>` → 3 tin mới nhất theo loại (vd `/news thethao`).
- `/news <loại sai>` → hướng dẫn + liệt kê 8 loại hợp lệ.

## Phạm vi

Chỉ sửa `news_cmd` trong `app/bot/handlers/features.py`. Không đụng worker đẩy
tự động, DB, hay adapter (đã có `category` + `image`).

## Kiến trúc

### Hàm thuần (test được)
- `_pick_news(items, category, limit) -> list` — lọc theo `category` (None = tất cả),
  trả tối đa `limit` tin **có ảnh** (`image` khác None), giữ thứ tự nguồn.
- `_news_caption(item) -> str` — caption Markdown 1 tin:
  ```
  📰 *Tiêu đề*
  [Đọc bài »](link)
  ```

### Handler `news_cmd` (viết lại)
1. `@require_module("news")` giữ nguyên.
2. Nếu có `context.args[0]`:
   - Chuẩn hóa lower; nếu **không** thuộc `NEWS_CATEGORY_KEYS` → trả tin nhắn
     hướng dẫn liệt kê 8 loại (label + key), dừng.
   - Ngược lại `category = key`.
   Không có arg → `category = None`.
3. `items = await get_news()`; `picked = _pick_news(items, category, 3)`.
4. `picked` rỗng vì không có ảnh → fallback: gửi **danh sách chữ** (5 tin đầu khớp
   loại) như hành vi cũ. `items` rỗng hẳn → "⚠️ Chưa lấy được tin, thử lại sau."
5. Có ảnh → dựng `list[InputMediaPhoto(media=image, caption=_news_caption(it),
   parse_mode=MARKDOWN)]` và `update.message.reply_media_group(media=...)`.
   (Gửi trực tiếp từ tiến trình bot, không qua Celery.)

## Xử lý lỗi
- Album lỗi (ảnh hỏng) → bắt exception, fallback gửi danh sách chữ để không mất tin.
- Loại sai → hướng dẫn, không coi là lỗi.

## Kiểm thử
- `_pick_news`: category None = tất cả; lọc đúng loại; bỏ tin không ảnh; tôn trọng `limit`.
- `_news_caption`: chứa tiêu đề + link, đúng định dạng.
- (Album gửi thật kiểm chứng thủ công trên Telegram — không unit test được PTB network.)

## Ngoài phạm vi (YAGNI)
- Không phân trang, không nút inline, không đổi tin đẩy tự động.
