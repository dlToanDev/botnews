# ☁️ Hướng dẫn Deploy BotNews lên VPS Google Cloud (Compute Engine)

Hướng dẫn **chi tiết từ số 0** để đưa toàn bộ dự án này lên một VM Google Cloud và chạy
production 24/7: bot Telegram (long polling), Celery worker + beat, Web Admin qua HTTPS,
Postgres + Redis, backup DB hằng ngày.

Kiến trúc chạy trên VM (7 service Docker):

```
Internet ──► nginx (80/443) ──► web:8000 (FastAPI Admin)
                                   │
        bot ── worker ── beat ─────┤ (chỉ trong docker network nội bộ)
                                   │
        postgres:5432 ── redis:6379  (KHÔNG lộ ra internet)
        certbot (auto-renew SSL)
```

> **Quy ước dùng trong tài liệu này** — thay bằng giá trị của bạn:
> - Project GCP: `botnews-prod`
> - Tên VM: `botnews-vm`
> - Zone: `asia-southeast1-b` (Singapore — gần VN nhất)
> - Domain admin: `admin.hvpgroup.vn`
> - Email cấp SSL: `admin@hvpgroup.vn`
> - Thư mục dự án trên VM: `/opt/botnews`

Bạn có thể làm theo **một trong hai đường**: [A) qua Console web](#phần-1a--tạo-vm-bằng-console-web-cách-dễ) (dễ, bấm chuột)
hoặc [B) qua `gcloud` CLI](#phần-1b--tạo-vm-bằng-gcloud-cli-cách-nhanh) (nhanh, copy-paste). Chọn 1 trong 2 rồi sang [Phần 2](#phần-2--cài-đặt-vm-lần-đầu).

---

## Phần 0 — Chuẩn bị (một lần)

- [ ] Có tài khoản Google Cloud + đã bật **Billing** (VM không thuộc free-tier vĩnh viễn; xem [chi phí](#phụ-lục--chi-phí-ước-tính)).
- [ ] Có **BOT_TOKEN** Telegram (từ [@BotFather](https://t.me/BotFather)).
- [ ] Có **domain** và quyền sửa DNS (Cloudflare, Google Domains, Mắt Bão, v.v.).
- [ ] (Máy của bạn) cài `gcloud` CLI nếu dùng đường B: <https://cloud.google.com/sdk/docs/install>.

```bash
# Đăng nhập & chọn project (chạy trên MÁY BẠN)
gcloud auth login
gcloud projects create botnews-prod            # hoặc dùng project sẵn có
gcloud config set project botnews-prod
# Bật API Compute Engine (bắt buộc trước khi tạo VM)
gcloud services enable compute.googleapis.com
```

---

## Phần 1A — Tạo VM bằng Console web (cách dễ)

1. Vào **Compute Engine → VM instances → Create instance**.
2. **Name:** `botnews-vm` · **Region:** `asia-southeast1 (Singapore)` · **Zone:** `asia-southeast1-b`.
3. **Machine type:** `e2-small` (2 vCPU / 2GB) là tối thiểu; khuyến nghị **`e2-medium` (2 vCPU / 4GB)** cho mượt.
4. **Boot disk:** Ubuntu **22.04 LTS**, dung lượng **30 GB** (SSD `pd-balanced`).
5. **Firewall:** tick **Allow HTTP traffic** và **Allow HTTPS traffic**.
6. Create. Ghi lại **External IP**.

Sau đó gán IP tĩnh (khỏi mất IP khi reboot): **VPC network → IP addresses → External IP addresses**
→ dòng của `botnews-vm` đổi **Type** từ *Ephemeral* → **Static**.

➡️ Xong, sang [Phần 2](#phần-2--cài-đặt-vm-lần-đầu).

---

## Phần 1B — Tạo VM bằng gcloud CLI (cách nhanh)

Chạy toàn bộ trên **MÁY BẠN**. Firewall GCP: mặc định VPC `default` đã cho SSH (22). Ta thêm rule cho 80/443.

```bash
# 1) Tạo VM Ubuntu 22.04, e2-medium, disk 30GB, gắn tag để áp firewall
gcloud compute instances create botnews-vm \
  --zone=asia-southeast1-b \
  --machine-type=e2-medium \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=30GB \
  --boot-disk-type=pd-balanced \
  --tags=http-server,https-server

# 2) Mở 80/443 cho VM (chỉ áp vào VM có tag http-server/https-server)
gcloud compute firewall-rules create allow-http \
  --allow=tcp:80 --target-tags=http-server --direction=INGRESS
gcloud compute firewall-rules create allow-https \
  --allow=tcp:443 --target-tags=https-server --direction=INGRESS

# 3) Đặt IP tĩnh cho VM (để DNS không hỏng khi reboot)
gcloud compute addresses create botnews-ip --region=asia-southeast1
STATIC_IP=$(gcloud compute addresses describe botnews-ip --region=asia-southeast1 --format='value(address)')
echo "IP tĩnh = $STATIC_IP"
# Gán IP tĩnh vào VM: gỡ access config cũ rồi thêm mới
gcloud compute instances delete-access-config botnews-vm --zone=asia-southeast1-b \
  --access-config-name="External NAT"
gcloud compute instances add-access-config botnews-vm --zone=asia-southeast1-b \
  --access-config-name="External NAT" --address="$STATIC_IP"
```

> **Quan trọng về firewall GCP:** cổng 5432 (Postgres) và 6379 (Redis) **không được mở** ở đây —
> compose production cũng không expose chúng ra host, nên DB/Redis không bao giờ chạm internet. Tốt.

---

## Phần 1.5 — Trỏ DNS

Tạo bản ghi **A** cho domain admin trỏ về **IP tĩnh** của VM:

| Type | Name    | Value        | TTL |
|------|---------|--------------|-----|
| A    | `admin` | `IP_TĨNH_VM` | Auto/300 |

Kiểm tra từ máy bạn (đợi vài phút cho DNS lan truyền):

```bash
dig +short admin.hvpgroup.vn      # phải in ra đúng IP tĩnh của VM
```

> Nếu dùng Cloudflare: để **DNS only** (mây xám) khi lần đầu xin SSL Let's Encrypt, tránh proxy chặn ACME challenge. Bật proxy (mây cam) sau khi có cert cũng được.

---

## Phần 2 — Cài đặt VM lần đầu

### 2.1. SSH vào VM

```bash
# gcloud tự tạo & quản lý SSH key cho bạn
gcloud compute ssh botnews-vm --zone=asia-southeast1-b
# (Hoặc bấm nút SSH trong Console web)
```

Từ đây trở đi, **các lệnh chạy TRÊN VM** (trừ khi ghi rõ "máy bạn").

### 2.2. Cài Docker + Compose plugin

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Đăng xuất rồi SSH lại để nhóm docker có hiệu lực (hoặc: newgrp docker)
exit
```

SSH lại rồi kiểm tra:

```bash
gcloud compute ssh botnews-vm --zone=asia-southeast1-b   # (máy bạn)
docker version && docker compose version                  # (trên VM) — không lỗi permission
```

### 2.3. Firewall trong VM (ufw) — lớp bảo vệ thứ 2

GCP firewall đã lọc ở tầng mạng; thêm `ufw` trên VM cho chắc.

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
sudo ufw status verbose
```

---

## Phần 3 — Đưa code lên VM

Có 2 cách. **Cách 1 (git clone)** khuyến nghị vì cập nhật code sau này chỉ cần `git pull`.

### Cách 1 — Git clone (khuyến nghị)

```bash
# (trên VM)
sudo mkdir -p /opt/botnews && sudo chown $USER: /opt/botnews
git clone <URL_REPO_CỦA_BẠN> /opt/botnews
cd /opt/botnews
```

> Repo private? Tạo **deploy key**: `ssh-keygen -t ed25519 -C botnews-vm` trên VM,
> copy `~/.ssh/id_ed25519.pub` vào GitHub repo → *Settings → Deploy keys*, rồi clone qua SSH URL.

### Cách 2 — Đẩy trực tiếp từ máy bạn (không cần git remote)

```bash
# (máy bạn) — nén & copy qua scp của gcloud, bỏ file rác
tar --exclude=.git --exclude=pgdata --exclude=redisdata --exclude='.env*' \
    -czf /tmp/botnews.tgz -C /home/toan/Dltoan/Code/botNews .
gcloud compute scp /tmp/botnews.tgz botnews-vm:~/ --zone=asia-southeast1-b
# (trên VM)
sudo mkdir -p /opt/botnews && sudo chown $USER: /opt/botnews
tar -xzf ~/botnews.tgz -C /opt/botnews && cd /opt/botnews
```

---

## Phần 4 — Cấu hình `.env` production

```bash
# (trên VM, tại /opt/botnews)
cp .env.prod.example .env
nano .env
```

Điền/đổi các giá trị sau (⚠️ **bắt buộc đổi mọi mật khẩu & secret**):

| Biến | Ghi chú |
|------|---------|
| `BOT_TOKEN` | Token thật từ BotFather |
| `POSTGRES_PASSWORD` | Sinh mạnh: `openssl rand -hex 32` |
| `DATABASE_URL` | Phải chứa **đúng** `POSTGRES_PASSWORD` ở trên (host giữ nguyên `postgres`) |
| `JWT_SECRET` | `openssl rand -hex 32` |
| `TIMEZONE` | `Asia/Ho_Chi_Minh` |
| `API_FOOTBALL_KEY`, `FOOTBALL_DATA_KEY`, `NEWSAPI_KEY` | Nếu dùng module tin tức/bóng đá |
| `GEMINI_API_KEY` | Nếu bật trợ lý AI (lấy ở [Google AI Studio](https://aistudio.google.com)) |
| `SEPAY_*` | Nếu bật bán gói trong bot (webhook trỏ `https://admin.hvpgroup.vn/api/sepay/webhook`) |

> Mẹo sinh nhanh 1 secret: `openssl rand -hex 32`. Nhớ để `POSTGRES_PASSWORD` và mật khẩu
> trong `DATABASE_URL` **giống hệt nhau**, nếu không container không kết nối được DB.

Đổi domain thật vào cấu hình Nginx:

```bash
sed -i 's/admin.yourdomain.com/admin.hvpgroup.vn/g' nginx/conf.d/admin.conf
```

---

## Phần 5 — Build, migration DB & tạo admin

```bash
C="docker compose -f docker-compose.prod.yml"

# 1) Build image từ Dockerfile
$C build

# 2) Bật DB + Redis trước, chờ 'healthy'
$C up -d postgres redis
$C ps           # đợi postgres/redis ở trạng thái healthy

# 3) Tạo bảng (chạy toàn bộ migration Alembic)
$C run --rm bot alembic upgrade head

# 4) Tạo tài khoản admin đăng nhập Web (sẽ hỏi mật khẩu)
$C run --rm bot python scripts/init_admin.py
# Không tương tác: $C run --rm -e ADMIN_PASSWORD='matkhaumanh' bot python scripts/init_admin.py
```

---

## Phần 6 — Cấp SSL Let's Encrypt (lần đầu)

Script tự xử lý bài toán con-gà-quả-trứng (cert giả → start nginx → xin cert thật → reload):

```bash
# Nên TEST bằng staging trước để tránh bị rate-limit của Let's Encrypt:
STAGING=1 DOMAIN=admin.hvpgroup.vn EMAIL=admin@hvpgroup.vn bash scripts/init_letsencrypt.sh

# Chạy thật (bỏ STAGING):
DOMAIN=admin.hvpgroup.vn EMAIL=admin@hvpgroup.vn bash scripts/init_letsencrypt.sh
```

> Nếu bước xin cert thất bại: kiểm tra `dig +short admin.hvpgroup.vn` đã ra đúng IP VM chưa,
> port 80 có mở chưa (`sudo ufw status`, firewall GCP `allow-http`), Cloudflare đang **DNS only**.

---

## Phần 7 — Khởi chạy toàn bộ & kiểm tra

```bash
C="docker compose -f docker-compose.prod.yml"
$C up -d               # bật hết 7 service
$C ps                  # tất cả phải 'healthy'
$C logs -f bot         # xem bot đã kết nối Telegram chưa (Ctrl+C để thoát)
```

Kiểm tra:

- Mở trình duyệt → `https://admin.hvpgroup.vn` → SSL hợp lệ (khóa xanh), đăng nhập bằng admin vừa tạo.
- Nhắn lệnh cho bot trên Telegram → bot phản hồi.
- `curl -I https://admin.hvpgroup.vn/healthz` → trả `{"status":"ok"}`.

> **Auto-renew SSL** đã tự động: service `certbot` chạy `certbot renew` mỗi 12h, `nginx` reload mỗi 6h. Không cần làm gì thêm.

---

## Phần 8 — Backup DB tự động

```bash
# Test backup thủ công
bash scripts/backup_db.sh
ls -lh backups/

# Đặt cron 2h sáng hằng ngày
crontab -e
# Thêm dòng:
0 2 * * * cd /opt/botnews && bash scripts/backup_db.sh >> /var/log/botnews-backup.log 2>&1
```

**Đẩy backup ra ngoài VM** (chống mất VM): set trong `.env` một trong hai —
`RCLONE_REMOTE=myremote:botnews-backups` (dùng rclone tới Google Drive/S3/GCS) hoặc
`SCP_TARGET=user@host:/path`. Script tự đẩy sau mỗi lần dump.

> Muốn dùng **GCS** làm nơi lưu offsite: `rclone config` chọn backend `google cloud storage`,
> tạo bucket `gsutil mb gs://botnews-backups`, rồi set `RCLONE_REMOTE=gcs:botnews-backups`.

---

## Phần 9 — Cập nhật code sau này (deploy phiên bản mới)

```bash
cd /opt/botnews
C="docker compose -f docker-compose.prod.yml"

git pull                       # kéo code mới (nếu deploy bằng git clone)
$C build                       # build lại image
$C run --rm bot alembic upgrade head   # chạy migration mới (nếu có)
$C up -d                       # áp dụng — chỉ service thay đổi được restart
$C ps
```

> Nếu deploy bằng Cách 2 (scp): lặp lại bước tar+scp+giải nén rồi chạy `$C build && $C up -d`.

---

## Phần 10 — Kiểm thử production (checklist bàn giao)

```bash
# Port DB/Redis KHÔNG lộ ra ngoài — chạy nmap từ MÁY KHÁC:
nmap -p 5432,6379 IP_TĨNH_VM        # phải 'closed/filtered'

# Reboot VM → mọi container tự lên lại nhờ restart: always
sudo reboot
# SSH lại rồi:  docker compose -f docker-compose.prod.yml ps

# Test restore từ backup
bash scripts/restore_db.sh backups/botnews_YYYYMMDD_HHMMSS.sql.gz
```

- [ ] `https://admin.hvpgroup.vn` login OK, cert hợp lệ, auto-renew bật.
- [ ] Bot phản hồi lệnh thật trên Telegram.
- [ ] `docker compose ps` → 7 service `healthy`, tự restart sau reboot.
- [ ] `nmap` xác nhận 5432/6379 đóng từ internet.
- [ ] `backup_db.sh` tạo dump hợp lệ; `restore_db.sh` restore thành công.
- [ ] `docker stats --no-stream` — RAM/CPU dưới ngưỡng sau vài ngày theo dõi.

---

## Lệnh vận hành thường dùng

```bash
C="docker compose -f docker-compose.prod.yml"
$C ps                     # trạng thái các service
$C logs -f bot            # theo dõi log 1 service (bot/worker/beat/web/nginx)
$C restart web            # restart 1 service
$C exec postgres psql -U botadmin botnews   # vào psql
docker stats --no-stream  # RAM/CPU hiện tại
$C down                   # dừng toàn bộ (GIỮ nguyên volume/dữ liệu)
```

---

## Phụ lục — Chi phí ước tính

| Hạng mục | Cấu hình | ~ USD/tháng |
|----------|----------|-------------|
| VM `e2-medium` (2vCPU/4GB) | 24/7, Singapore | ~24–28 |
| VM `e2-small` (2vCPU/2GB) | 24/7, tối thiểu | ~12–14 |
| Disk `pd-balanced` 30GB | | ~1.2 |
| IP tĩnh (khi VM đang chạy) | | miễn phí khi gắn VM |
| Egress (traffic ra) | bot dùng ít | vài USD |

> Con số tham khảo, thay đổi theo bảng giá GCP. Dùng [Pricing Calculator](https://cloud.google.com/products/calculator) để tính chính xác.
> Muốn tiết kiệm: cân nhắc **Committed use discount** (cam kết 1 năm) hoặc chọn `e2-small` nếu tải nhẹ.

---

## Xử lý sự cố nhanh

| Triệu chứng | Nguyên nhân & cách xử lý |
|-------------|--------------------------|
| `alembic upgrade` lỗi kết nối | Postgres chưa `healthy`. Chờ `$C ps` báo healthy rồi chạy lại. |
| Xin SSL thất bại | DNS chưa trỏ đúng IP / port 80 chưa mở / Cloudflare đang proxy. Sửa rồi chạy lại `init_letsencrypt.sh`. |
| Web 502 Bad Gateway | Service `web` chưa healthy: `$C logs web`. Thường do `.env` sai `DATABASE_URL`. |
| Bot không phản hồi | `$C logs bot` — kiểm tra `BOT_TOKEN`. Đảm bảo chỉ 1 instance bot chạy (long polling). |
| Container bị OOM/kill | RAM thấp: nâng VM lên `e2-medium`, hoặc giảm `--workers`/`--concurrency` trong compose. |
| `permission denied` khi gõ docker | Chưa đăng xuất/vào lại sau `usermod -aG docker`. Chạy `newgrp docker` hoặc SSH lại. |

---

**Tài liệu liên quan:** runbook VPS tổng quát tại [`docs/DEPLOYMENT.md`](DEPLOYMENT.md);
chi tiết Phase 4 tại [`docs/phases/phase-4-deployment.md`](phases/phase-4-deployment.md).
