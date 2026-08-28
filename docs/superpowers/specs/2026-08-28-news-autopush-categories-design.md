# Thiết kế: Đẩy tin tự động theo loại + cấu hình trên web + ảnh banner

**Ngày:** 2026-08-28
**Nhánh:** feat/web-admin-redesign

## Mục tiêu

Bật module `news` cho một tài khoản → tài khoản đó **tự động nhận tin mới** qua
Telegram (không cần gõ lệnh). Admin cấu hình **loại tin** cho từng tài khoản trên
dashboard web. Mỗi tin gửi kèm **ảnh banner** của bài báo.

## Bối cảnh & vấn đề hiện tại

- Worker `app/worker/tasks/news_push.py` đã tồn tại nhưng có dòng
  `if not keywords: continue` → user chưa đặt `/setnews` thì **không nhận tin nào**.
  Đây là lý do tính năng "chưa ổn".
- Lịch chạy 15 phút/lần (chậm). Cache tin 600s (poll nhanh cũng thấy tin cũ).
- Chưa có lọc theo loại, chưa cấu hình được trên web, tin chỉ có text.

## Quyết định thiết kế (đã chốt với người dùng)

- Lọc theo **loại tin** (category). User chọn loại nào → chỉ nhận loại đó;
  **không chọn loại nào → nhận tất cả** tin mới. Từ khoá `/setnews` (nếu có) lọc thêm.
- Cấu hình trên **dashboard web, admin chỉnh cho từng tk** (web hiện chỉ có auth admin,
  không làm self-service cho end-user).
- Đẩy **2 phút/lần**, **mỗi tin 1 tin nhắn**, **kèm ảnh banner**.
- Chống spam tin cũ bằng **tập link đã thấy toàn cục + seed im lặng lần đầu**.
- Bật module `news` = có đẩy (không thêm cờ bật/tắt riêng — YAGNI).

## Danh mục tin

8 loại (RSS chuyên mục VNExpress), khai báo trong `app/core/constants.py`:

```python
NEWS_CATEGORIES = [
    {"key": "thoisu",    "label": "Thời sự",   "rss": "https://vnexpress.net/rss/thoi-su.rss"},
    {"key": "thegioi",   "label": "Thế giới",  "rss": "https://vnexpress.net/rss/the-gioi.rss"},
    {"key": "kinhdoanh", "label": "Kinh doanh","rss": "https://vnexpress.net/rss/kinh-doanh.rss"},
    {"key": "thethao",   "label": "Thể thao",  "rss": "https://vnexpress.net/rss/the-thao.rss"},
    {"key": "congnghe",  "label": "Công nghệ", "rss": "https://vnexpress.net/rss/so-hoa.rss"},
    {"key": "giaitri",   "label": "Giải trí",  "rss": "https://vnexpress.net/rss/giai-tri.rss"},
    {"key": "phapluat",  "label": "Pháp luật", "rss": "https://vnexpress.net/rss/phap-luat.rss"},
    {"key": "suckhoe",   "label": "Sức khỏe",  "rss": "https://vnexpress.net/rss/suc-khoe.rss"},
]
```

## Kiến trúc

### 1. `app/integrations/news.py` (viết lại)

- Fetch **từng feed theo loại**; mỗi item gắn thêm `category` (key) + `image`.
- Hạ **TTL 600s → 120s** để poll 2 phút thấy tin mới.
- `_extract_image(entry)` — thử lần lượt: `media_thumbnail[0].url` →
  `media_content[0].url` → `enclosures` (type ảnh) → regex `<img src>` trong
  `summary/description`; không có → `None`.
- Item: `{title, link, published, source, category, image}`.
- Giữ `match_keywords(title, keywords)`.
- `get_news()` trả list tổng hợp (lệnh `/news` vẫn xem mới nhất chung).

### 2. Model + migration

`UserSettings` (app/models/user.py) thêm:
```python
news_categories: Mapped[list] = mapped_column(JSONB, default=list)
```
Alembic migration thêm cột `news_categories JSONB NOT NULL DEFAULT '[]'`
(downgrade: drop cột).

### 3. `app/services/settings_service.py`

Thêm hàm theo **pattern web** (session + user_id, như `subscription_service.set_module`):
```python
async def set_news_categories(session, user_id: int, categories: list[str]) -> list:
    st = await _get_settings_by_user_id(session, user_id)   # helper mới theo user_id
    if st is None:
        return []
    st.news_categories = categories
    flag_modified(st, "news_categories")
    return categories   # web route commit sau
```
(commit do route web quản lý, giống `toggle_module`.)

### 4. Web dashboard — trang chi tiết user

- Route GET `user_detail` (routers/users.py): nạp thêm `UserSettings`, truyền
  `news_categories` hiện tại + `NEWS_CATEGORIES` vào template.
- `user_detail.html`: thêm card **"📰 Cài đặt Tin tức"** — 8 checkbox danh mục
  (tích sẵn theo lựa chọn hiện tại) + nút **Lưu**. Form `method=post`
  `action="/users/{id}/news"` (POST → redirect về trang, giống form status).
  Ghi chú UI: "Không chọn loại nào = nhận tất cả tin".
- Route mới `POST /users/{user_id}/news` (routers/users.py hoặc modules.py):
  nhận `categories: list[str] = Form([])`, lọc theo key hợp lệ, gọi service, commit,
  redirect 303 về `/users/{user_id}`.

### 5. Task gửi ảnh — `app/worker/tasks/send_photo.py` (mới)

```python
@celery_app.task(bind=True, max_retries=5, rate_limit="25/s")
def send_photo_task(self, chat_id, photo_url, caption) -> str:
    # bot.send_photo(chat_id, photo=photo_url, caption=caption, parse_mode=MARKDOWN)
    # RetryAfter → retry; Forbidden → "forbidden";
    # BadRequest (ảnh lỗi) → fallback bot.send_message(caption) để vẫn nhận tin
```

### 6. Worker đẩy tin — `app/worker/tasks/news_push.py` (viết lại)

- Lấy `get_news()`.
- **Lọc tin mới toàn cục (chống spam):**
  - `key = f"news:seen:{_link_hash(link)}"`, `redis.set(key,"1",nx=True,ex=SEEN_TTL~3 ngày)`
    → `True` nếu lần đầu thấy.
  - Cờ `news:seeded`: nếu **chưa** seed → đánh dấu hết tin hiện có là đã thấy,
    **không gửi**, rồi bật cờ. Nếu **đã** seed → các link lần đầu thấy = tin mới.
- Với mỗi tin mới, duyệt `module_repo.eligible_users(session, "news")`:
  - `cats = st.news_categories or []`; bỏ qua nếu `cats` không rỗng và
    `item.category not in cats`.
  - `kw = st.news_keywords or []`; nếu có kw và `not match_keywords(title, kw)` → bỏ.
  - Per-user dedup `news:{user.id}:{hash}` (TTL 1 ngày) — an toàn thêm.
  - Cap an toàn **10 tin/user/lần** (log nếu vượt).
  - `caption = f"📰 *Tin mới · {label}*\n[{title}]({link})"`.
  - Có `image` → `send_photo_task.delay(...)`; không → `send_message_task.delay(...)`.

### 7. Lịch chạy — `app/worker/celery_app.py`

Đổi entry `news-push` từ `crontab(minute="*/15")` → `crontab(minute="*/2")`.
Thêm `app.worker.tasks.send_photo` vào `include`.

## Xử lý lỗi

- Feed 1 loại lỗi → bỏ loại đó, các loại khác vẫn chạy (try/except per feed như hiện tại).
- Ảnh lỗi khi gửi → fallback text (mục 5).
- Redis lỗi khi seed → tin nhắn không bị gửi trùng nhờ per-user dedup; nếu cả hai lỗi,
  cùng lắm gửi lặp 1 lần (chấp nhận được).

## Kiểm thử

- `_extract_image`: enclosure ảnh / `<img>` trong description / không có ảnh → None.
- `news.py`: item gắn đúng `category`.
- Logic lọc user: cats rỗng = nhận tất cả; cats có = chỉ khớp; keyword lọc thêm.
- Logic "tin mới": seed lần đầu không trả tin; lần sau chỉ trả link mới.
- Migration up/down chạy được.

## Ngoài phạm vi (YAGNI)

- Không login self-service cho end-user.
- Không thêm nguồn ngoài VNExpress.
- Không tóm tắt AI/không nhiều ảnh; chỉ 1 ảnh banner + caption.
- Lệnh `/news` giữ nguyên (xem tổng hợp mới nhất).
