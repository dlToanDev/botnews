# 🤖 BotNews

**Bot Telegram SaaS đa người dùng + Web Admin Dashboard.**

Người dùng mua từng **module dịch vụ** theo tháng (giá vàng, crypto, bóng đá, tin tức,
trợ lý AI) ngay trong bot — quét QR chuyển khoản qua **SePay**, hệ thống tự kích hoạt sau
1–2 phút. Module **Lịch cá nhân** miễn phí cho mọi tài khoản. Admin quản lý người dùng,
gói cước, bật/tắt module và cấu hình thông báo qua giao diện web.

Toàn bộ giao diện tiếng Việt. Mỗi lệnh có bí danh tiếng Việt không dấu
(`/muagoi`, `/vang`, `/tiendientu`, `/bongda`, `/tintuc`…).

| Module | Nội dung |
|---|---|
| 📅 Lịch cá nhân | Thêm lịch tự nhiên (`08:00 Đi làm`), lưới tháng tương tác, nhắc trước giờ + báo đúng giờ, tổng hợp 7h sáng |
| 🥇 Giá vàng | SJC/PNJ, bản tin theo giờ tự chọn, cảnh báo vượt ngưỡng |
| ₿ Crypto | Giá & vốn hóa (CoinGecko), lệnh riêng từng đồng (`/btc`, `/eth`…), cảnh báo ±%/24h |
| ⚽ Bóng đá | Kết quả, BXH, trận trực tiếp, đội yêu thích; 6 giải lớn (`/epl`, `/bxhepl`…) |
| 📰 Tin tức | 8 chuyên mục RSS VNExpress, tự đẩy tin mới kèm ảnh, lọc từ khóa |
| 🤖 Trợ lý AI | Hỏi đáp + phân tích vàng/crypto/tin bằng Google Gemini (30 lượt/ngày) |
| 🛒 Bán gói trong bot | Lẻ 20.000đ · Combo 40.000đ · Full 80.000đ / 30 ngày, QR SePay tự khớp đơn |
| 📊 Web Admin | Dashboard thống kê, quản lý user & module, đơn hàng, nhật ký, cấu hình hệ thống |

---

## 🧱 Công nghệ

> ⚠️ Dự án **Python thuần**. Không có Next.js / React / TypeScript / NestJS / Prisma,
> không có `package.json`.

Python 3.12 · `python-telegram-bot` 21.9 · FastAPI + Jinja2 + HTMX + Tailwind (CDN) ·
Celery 5.4 + Beat · PostgreSQL 16 (SQLAlchemy 2.0 async / `asyncpg`) · Alembic · Redis 7 ·
Docker Compose + Nginx + Let's Encrypt.

Một codebase, **5 tiến trình**: `bot` · `web` · `worker` · `beat` + `postgres` · `redis`.

---

## 🚀 Setup

Chọn **một** trong hai cách.

### Cách A — Docker (nhanh nhất, không cần cài Python/Postgres/Redis)

```bash
# 1. Cấu hình
cp .env.example .env
$EDITOR .env          # bắt buộc: BOT_TOKEN · POSTGRES_PASSWORD · JWT_SECRET

# 2. Build & khởi động
docker compose up -d --build

# 3. Tạo bảng trong DB
docker compose run --rm web alembic upgrade head

# 4. Tạo tài khoản admin đầu tiên
docker compose run --rm -e ADMIN_PASSWORD='mat-khau-manh' web python scripts/init_admin.py

# 5. Kiểm tra môi trường (config + Redis + Postgres)
docker compose run --rm bot python scripts/check_setup.py
```

Xong → mở **http://127.0.0.1:8000**

> Trong `.env`, host của DB/Redis phải là tên service Docker: `postgres` và `redis`
> (không phải `localhost`). Ra ngoài host, Postgres map cổng `15432`, Redis `16380`
> để tránh đụng service sẵn có trên máy.

### Cách B — Chạy local bằng venv

```bash
# 1. Môi trường Python (cần sẵn PostgreSQL 16 + Redis 7 trên máy)
uv venv .venv                          # hoặc: python3.12 -m venv .venv
uv pip install -r requirements.txt
uv pip install ruff                    # tùy chọn — ruff chưa có trong requirements.txt

# 2. Cấu hình — trỏ DB/Redis về localhost
cp .env.example .env
$EDITOR .env
```

```ini
BOT_TOKEN=<token từ @BotFather>
DATABASE_URL=postgresql+asyncpg://botadmin:matkhau@localhost:5432/botnews
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
JWT_SECRET=<chuỗi ngẫu nhiên dài>
```

```bash
# 3. Tạo bảng + tài khoản admin
export PYTHONPATH=$PWD
.venv/bin/alembic upgrade head
ADMIN_PASSWORD='mat-khau-manh' .venv/bin/python scripts/init_admin.py

# 4. Kiểm tra môi trường
.venv/bin/python scripts/check_setup.py
```

> Chưa có `BOT_TOKEN`? Xem cách tạo bot với @BotFather: [`docs/SETUP.md`](docs/SETUP.md).

---

## ▶️ Chạy app

### Local — `./dev.sh` (khuyến nghị khi dev)

Chạy cả 4 tiến trình ở **foreground**, log gộp chung ra terminal có nhãn màu.
Ctrl+C hoặc đóng terminal là mọi thứ tự tắt — giống `npm run dev`.

```bash
./dev.sh
```

```
▶  bot · web · worker · beat đang chạy — Ctrl+C để dừng
   Web admin: http://127.0.0.1:8000
```

Script tự bật Postgres + Redis nếu chưa chạy, và **giữ nguyên** hai service này khi thoát.

### Local — chạy nền bằng `scripts/dev_start.sh`

Dùng khi muốn app chạy nền, log ghi ra file.

```bash
bash scripts/dev_start.sh            # bật postgres, redis, bot, web, worker, beat
tail -f logs/{bot,web,worker,beat}.log

bash scripts/dev_stop.sh             # dừng app, giữ postgres + redis
bash scripts/dev_stop.sh --all       # dừng luôn hạ tầng
```

Log ở `logs/*.log`, PID ở `logs/pids/`.

> `dev.sh` và `dev_start.sh` đều giả định Postgres ở `~/.local/postgres` và Redis ở
> `~/.local/redis`. Nếu bạn cài chỗ khác, tự khởi động hạ tầng rồi chạy thủ công (dưới).

### Local — chạy thủ công (4 terminal)

```bash
export PYTHONPATH=$PWD

.venv/bin/python -m app.bot.main                                          # bot
.venv/bin/uvicorn app.web.main:app --reload --port 8000                   # web (có hot-reload)
.venv/bin/celery -A app.worker.celery_app worker --loglevel=info -c 2     # worker
.venv/bin/celery -A app.worker.celery_app beat  --loglevel=info           # beat
```

> ⚠️ Chỉ được chạy **một** tiến trình `bot` tại một thời điểm — Telegram long polling
> từ chối consumer thứ hai với lỗi 409.

### Docker

```bash
docker compose up -d                      # chạy nền
docker compose logs -f web worker bot     # xem log
docker compose restart worker beat        # restart sau khi sửa task Celery
docker compose down                       # dừng
```

### Production

```bash
docker compose -f docker-compose.prod.yml up -d      # + nginx + certbot, không lộ port ra ngoài

DOMAIN=admin.example.com EMAIL=you@example.com \
  bash scripts/init_letsencrypt.sh                   # cấp SSL lần đầu
```

Chi tiết: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) ·
[`docs/DEPLOY_SAME_VPS.md`](docs/DEPLOY_SAME_VPS.md) ·
[`docs/DEPLOYMENT_GCLOUD.md`](docs/DEPLOYMENT_GCLOUD.md)

---

## 🧪 Test & lint

```bash
.venv/bin/python -m pytest -q      # 76 test thuần, ~1.3s (không cần DB/mạng)
.venv/bin/ruff check .             # lint — cài trước: uv pip install ruff
.venv/bin/ruff format .            # format
```

Chưa có typecheck, chưa có bước build, chưa có CI.

## 🗄️ Migration

```bash
.venv/bin/alembic current                                  # đang ở revision nào
.venv/bin/alembic upgrade head                             # áp dụng
.venv/bin/alembic revision --autogenerate -m "mô tả ngắn"  # tạo mới — LUÔN đọc lại file sinh ra
.venv/bin/alembic downgrade -1                             # lùi 1 bước
```

## 🔐 Biến môi trường

Đầy đủ trong [`.env.example`](.env.example).

| Nhóm | Biến | Ghi chú |
|---|---|---|
| Bắt buộc | `BOT_TOKEN`, `DATABASE_URL` | thiếu là không khởi động được |
| Nên đổi | `JWT_SECRET`, `POSTGRES_PASSWORD` | mặc định `JWT_SECRET` là `change-me` — **phải đổi trước khi deploy** |
| Tùy chọn | `SEPAY_*` | thiếu → tắt `/muagoi` |
| Tùy chọn | `GEMINI_API_KEY` | thiếu → tắt module AI |
| Tùy chọn | `FOOTBALL_DATA_KEY`, `API_FOOTBALL_KEY` | thiếu → hạn chế module bóng đá |

⚠️ Không commit `.env`, `logs/`, `celerybeat-schedule`.

## 🧯 Lỗi thường gặp

| Triệu chứng | Cách xử lý |
|---|---|
| Bot thoát với lỗi 409 | Đang chạy 2 tiến trình bot. `bash scripts/dev_stop.sh` hoặc tắt service `bot` trong Docker |
| `Directory 'app/web/static' does not exist` | `mkdir -p app/web/static && touch app/web/static/.gitkeep` |
| Đăng nhập admin cứ quay lại `/login` | Chưa tạo admin (`scripts/init_admin.py`), hoặc `JWT_SECRET` đã đổi sau khi cookie được cấp |
| `alembic` không kết nối được | URL thật lấy từ `.env` qua `app.core.config` (`alembic.ini` chỉ là placeholder). Kiểm tra `DATABASE_URL` và `PYTHONPATH` |
| `ruff: command not found` | `uv pip install ruff` |
| Thanh toán không tự kích hoạt | Kiểm tra `/orders` và `/logs?action=order_unmatched` |

Thêm: [`docs/development.md`](docs/development.md) § Troubleshooting.

## 📚 Tài liệu

| File | Nội dung |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Kiến trúc, luồng dữ liệu, rủi ro & đề xuất cải tiến |
| [`docs/database.md`](docs/database.md) | Schema, index, migration |
| [`docs/api.md`](docs/api.md) | Route web, webhook SePay, lệnh bot, Celery task, key Redis |
| [`docs/development.md`](docs/development.md) | Quy trình phát triển & xử lý sự cố |
| [`docs/SETUP.md`](docs/SETUP.md) | Tạo bot Telegram với @BotFather |
| [`CLAUDE.md`](CLAUDE.md) · [`AGENTS.md`](AGENTS.md) | Hướng dẫn cho AI agent làm việc trên repo |
