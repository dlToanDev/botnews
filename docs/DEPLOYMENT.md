# 🚀 Runbook Triển khai Production (Phase 4)

Hướng dẫn deploy BotNews lên VPS Linux (2vCPU/4GB), chạy 24/7, HTTPS cho admin,
tự phục hồi sau reboot, backup DB hằng ngày. **Bot mode: Long Polling** (không cần webhook).

Kiến trúc: `nginx (80/443) → web:8000`; các service khác (postgres, redis, bot,
worker, beat, certbot) chỉ chạy trong docker network nội bộ, **không lộ ra internet**.

Giả định thư mục dự án trên VPS: `/opt/botnews`. Domain ví dụ: `admin.hvpgroup.vn`.

---

## 4.1. Chuẩn bị VPS

```bash
# --- Cài Docker + Compose plugin (Ubuntu/Debian) ---
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # đăng xuất/vào lại để có hiệu lực

# --- Tạo user non-root (nếu đang là root) ---
adduser deploy && usermod -aG sudo,docker deploy

# --- SSH key + tắt password login ---
# Trên MÁY BẠN:  ssh-copy-id deploy@VPS_IP
# Trên VPS, sửa /etc/ssh/sshd_config:
#   PasswordAuthentication no
#   PermitRootLogin no
sudo systemctl restart ssh

# --- Firewall: mở 22/80/443, đóng phần còn lại ---
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

> Port **5432/6379 không cần mở** — compose production không expose chúng ra host.

**DNS:** Tạo bản ghi **A** `admin.hvpgroup.vn → IP_VPS`. Kiểm tra: `dig +short admin.hvpgroup.vn`.

---

## 4.2 – 4.4. Đưa code lên & khởi chạy

```bash
# Clone code
sudo mkdir -p /opt/botnews && sudo chown $USER: /opt/botnews
git clone <repo-url> /opt/botnews
cd /opt/botnews

# .env production (KHÔNG commit)
cp .env.prod.example .env
nano .env            # điền BOT_TOKEN, đổi mọi PASSWORD/SECRET (openssl rand -hex 32)

# Đổi domain trong Nginx site config
sed -i 's/admin.yourdomain.com/admin.hvpgroup.vn/g' nginx/conf.d/admin.conf

# Build + bật DB trước, chạy migration + tạo admin
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d postgres redis
docker compose -f docker-compose.prod.yml run --rm bot alembic upgrade head
docker compose -f docker-compose.prod.yml run --rm bot python scripts/init_admin.py
```

---

## 4.3. SSL Let's Encrypt (lần đầu)

```bash
# Bootstrap cert (tạo cert giả → start nginx → xin cert thật → reload)
DOMAIN=admin.hvpgroup.vn EMAIL=admin@hvpgroup.vn bash scripts/init_letsencrypt.sh
# Test trước bằng staging để tránh rate-limit:  STAGING=1 DOMAIN=... EMAIL=... bash scripts/init_letsencrypt.sh
```

Sau đó bật **toàn bộ** stack:

```bash
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps      # tất cả phải 'healthy'
```

> Auto-renew: service `certbot` tự chạy `certbot renew` mỗi 12h; `nginx` tự reload mỗi 6h.

**IP allowlist (tùy chọn):** mở `nginx/conf.d/admin.conf`, bỏ comment `allow <IP>; deny all;`
trong block 443, rồi `docker compose -f docker-compose.prod.yml exec nginx nginx -s reload`.

---

## 4.5. Backup & vận hành

```bash
# Test backup thủ công
bash scripts/backup_db.sh
ls -lh backups/

# Cron 2h sáng hằng ngày
crontab -e
# Thêm dòng:
0 2 * * * cd /opt/botnews && bash scripts/backup_db.sh >> /var/log/botnews-backup.log 2>&1
```

Đẩy backup ra ngoài VPS (chống mất VPS): set `RCLONE_REMOTE` hoặc `SCP_TARGET` trong `.env`.
Log rotation container đã cấu hình sẵn (`json-file`, max 10m × 3 file) trong compose.

**Giám sát (tùy chọn):** endpoint `GET /healthz` trả `{"status":"ok"}` — trỏ Uptime Kuma vào
`https://admin.hvpgroup.vn/healthz`.

---

## 4.6. Kiểm thử production (checklist)

```bash
# SSL hợp lệ + login
curl -I https://admin.hvpgroup.vn            # 200/301, cert hợp lệ

# Port DB/Redis KHÔNG lộ ra ngoài (chạy từ máy khác):
nmap -p 5432,6379 IP_VPS                     # phải 'closed/filtered'

# Reboot → mọi container tự lên lại
sudo reboot
# đăng nhập lại:  docker compose -f docker-compose.prod.yml ps

# Test restore từ backup
bash scripts/restore_db.sh backups/botnews_YYYYMMDD_HHMMSS.sql.gz
```

- [ ] `https://admin.hvpgroup.vn` login OK, cert hợp lệ.
- [ ] Bot phản hồi lệnh thật trên Telegram.
- [ ] `docker compose ps` → 7 service `healthy`, tự restart sau reboot.
- [ ] `nmap` xác nhận 5432/6379 đóng từ ngoài.
- [ ] `backup_db.sh` tạo dump hợp lệ; `restore_db.sh` restore thành công.
- [ ] `docker stats` — RAM/CPU dưới ngưỡng sau vài ngày.

---

## Lệnh vận hành thường dùng

```bash
C="docker compose -f docker-compose.prod.yml"
$C ps                     # trạng thái
$C logs -f bot            # xem log 1 service
$C restart web            # restart 1 service
$C pull && $C up -d       # cập nhật image
git pull && $C up -d --build   # deploy code mới
$C down                   # dừng (giữ volume/dữ liệu)
docker stats --no-stream  # RAM/CPU
```
