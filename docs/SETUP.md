# 🛠️ Hướng dẫn Setup & Tạo Bot Telegram

Hướng dẫn từ đầu đến khi bot chạy được (dev/local). Deploy production xem riêng ở
[`docs/DEPLOYMENT.md`](./DEPLOYMENT.md).

Kiến trúc: 1 codebase chạy 5 tiến trình — `bot` (long polling), `worker` + `beat`
(Celery), `web` (FastAPI admin), cùng `postgres` + `redis`.

---

## 1. Yêu cầu

- **Docker** + **Docker Compose plugin** (`docker compose version`).
- Một tài khoản **Telegram** (để chat với @BotFather).
- (Tùy chọn) Python 3.12 nếu muốn chạy ngoài Docker.

> Không cần cài Python/Postgres/Redis lên máy — mọi thứ chạy trong Docker.

---

## 2. Tạo Bot trên Telegram (@BotFather)

1. Mở Telegram, tìm **@BotFather** (có tick xanh) → bấm **Start**.
2. Gõ `/newbot`.
3. Nhập **tên hiển thị** của bot (VD: `HVP News Bot`).
4. Nhập **username** — phải kết thúc bằng `bot` (VD: `hvp_news_bot`).
5. BotFather trả về **token** dạng:

   ```
   7123456789:AAH-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

   → **Copy token này**, sẽ dán vào `.env` ở bước 4.

> ⚠️ Token là mật khẩu của bot — không commit, không chia sẻ. Lỡ lộ thì gõ
> `/revoke` trong BotFather để cấp token mới.

### Thiết lập thêm (khuyến nghị, trong BotFather)

- `/setdescription` — mô tả bot.
- `/setuserpic` — ảnh đại diện.
- `/setcommands` — menu gợi ý lệnh. Chọn bot rồi **dán nguyên khối** dưới đây:

  ```
  start - Khởi động / đăng ký
  help - Xem hướng dẫn
  today - Lịch hôm nay
  mylist - Tất cả lịch
  addschedule - Thêm lịch: /addschedule 08:00 Đi làm
  delete - Xoá lịch theo id
  crypto - Giá coin: /crypto BTCUSDT
  setcrypto - Cảnh báo coin: /setcrypto BTCUSDT 5
  gold - Giá vàng SJC/PNJ
  football - Lịch/kết quả bóng đá
  setteam - Theo dõi đội: /setteam Arsenal
  news - Tin nóng
  setnews - Lọc tin: /setnews bitcoin,fed
  ```

> **Privacy mode:** mặc định bot chỉ nhận lệnh gửi trực tiếp. Giữ nguyên là được.
> Chỉ khi muốn bot đọc mọi tin trong group mới cần `/setprivacy` → Disable.

---

## 3. Lấy code

```bash
git clone <repo-url> botNews
cd botNews
```

---

## 4. Cấu hình `.env`

```bash
cp .env.example .env
```

Mở `.env` và sửa tối thiểu:

| Biến | Ý nghĩa | Bắt buộc |
|------|---------|----------|
| `BOT_TOKEN` | Token từ @BotFather (bước 2) | ✅ |
| `POSTGRES_PASSWORD` | Mật khẩu DB (đổi khác mặc định) | ✅ |
| `DATABASE_URL` | Đổi password cho khớp `POSTGRES_PASSWORD` | ✅ |
| `JWT_SECRET` | Chuỗi ngẫu nhiên cho web admin (`openssl rand -hex 32`) | ✅ |
| `API_FOOTBALL_KEY`, `NEWSAPI_KEY` | Chỉ cần nếu dùng module bóng đá/tin tức | ⬜ |

> Ba biến `POSTGRES_PASSWORD` và phần password trong `DATABASE_URL` phải **giống nhau**.

---

## 5. Khởi chạy bằng Docker

```bash
# 1) Bật DB + Redis trước
docker compose up -d postgres redis

# 2) Tạo bảng (migration)
docker compose run --rm bot alembic upgrade head

# 3) Tạo tài khoản admin cho web (sẽ hỏi mật khẩu)
docker compose run --rm web python scripts/init_admin.py

# 4) Bật toàn bộ (bot + worker + beat + web)
docker compose up -d

# 5) Xem trạng thái + log
docker compose ps
docker compose logs -f bot
```

Log `bot` xuất hiện `🤖 Bot đang chạy (long polling)...` là OK.

---

## 6. Kiểm tra kết nối & token

```bash
docker compose run --rm bot python scripts/check_setup.py
```

Kết quả mong đợi:

```
[OK ] Config load. BOT_TOKEN prefix = 7123...
[OK ] Redis PING thành công.
[OK ] PostgreSQL SELECT 1 thành công.
[OK ] Bot token hợp lệ: @hvp_news_bot (id=...)
=> KẾT QUẢ: TẤT CẢ OK ✅
```

---

## 7. Dùng thử

- **Trên Telegram:** mở bot của bạn → bấm **Start** (hoặc gõ `/start`) → gõ `/help`.
  - Thử: `/addschedule 08:00 Đi làm`, rồi `/today`.
- **Web Admin:** mở <


> → đăng nhập bằng `ADMIN_DEFAULT_USER`
  (mặc định `admin`) và mật khẩu vừa tạo ở bước 5.3.

> Module `crypto/gold/football/news` bị khoá theo gói — Admin bật cho user trong
> web admin (mục Subscriptions/Modules).

---

## 8. Lệnh vận hành thường dùng

```bash
docker compose ps                 # trạng thái service
docker compose logs -f worker     # xem log 1 service
docker compose restart bot        # restart bot sau khi đổi .env
docker compose down               # dừng (giữ dữ liệu trong volume)
docker compose up -d --build      # build lại sau khi sửa code
```

---

## 9. Xử lý sự cố

| Triệu chứng | Nguyên nhân / cách xử lý |
|-------------|--------------------------|
| `check_setup` báo **Bot token không hợp lệ** | Token dán sai/thừa khoảng trắng. Copy lại từ BotFather, `docker compose restart bot`. |
| Bot **không phản hồi** `/start` | Chưa `docker compose up -d` service `bot`; hoặc chạy 2 tiến trình cùng token (Telegram chỉ cho 1 long-polling). Kiểm tra `docker compose logs bot`. |
| Cổng **5432/6379 bị chiếm** trên máy | Bản dev map ra host `127.0.0.1:15432` (Postgres) và `16380` (Redis) để tránh đụng — nội bộ Docker vẫn 5432/6379, không cần đổi gì. |
| `alembic upgrade` lỗi kết nối | Postgres chưa `healthy`. Chờ `docker compose ps` báo healthy rồi chạy lại. |
| Đăng nhập web sai | Chạy lại `docker compose run --rm web python scripts/init_admin.py` để đặt lại mật khẩu. |

---

## Bước tiếp theo

Đưa hệ thống lên VPS chạy 24/7 + HTTPS + backup: xem [`docs/DEPLOYMENT.md`](./DEPLOYMENT.md).
