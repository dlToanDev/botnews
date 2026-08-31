# 🔗 Deploy BotNews lên VPS ĐANG CHẠY web khác (dùng chung máy)

Dành cho trường hợp: bạn đã có 1 VPS Google Cloud (`daylatoan-server`) và **đang chạy sẵn 1 web**
ở đó. Ta cài thêm dự án này lên **cùng máy**, không đụng tới web cũ.

Nguyên tắc: web cũ đang giữ cổng **80/443** → BotNews **không chạy nginx/certbot riêng**.
Thay vào đó dùng file [`docker-compose.coexist.yml`](../docker-compose.coexist.yml) — chỉ mở
Web Admin ở `127.0.0.1:8010` (localhost VPS), rồi cho reverse-proxy sẵn có trỏ 1 subdomain sang.
DB/Redis vẫn không lộ ra internet.

> Quy ước: SSH vào bằng `gcloud compute ssh daylatoan-server --zone=asia-southeast1-c --project=toan-506508`.
> Thư mục dự án: `/opt/botnews`. Subdomain ví dụ: `admin.tenmien.com`.

---

## Bước 0 — Kiểm tra môi trường (chạy 1 lần)

SSH vào VPS rồi chạy để biết web cũ chạy kiểu gì, ai giữ 80/443, còn bao nhiêu RAM:

```bash
. /etc/os-release; echo "$PRETTY_NAME"
free -h | head -2                       # RAM còn trống (cần thêm ~2GB cho BotNews)
df -h / | tail -1                       # dung lượng đĩa
docker --version 2>/dev/null || echo "chưa có docker"
docker ps --format '{{.Names}} | {{.Image}} | {{.Ports}}'   # web cũ có trong docker?
sudo ss -ltnp | grep -E ':80 |:443 '    # ai đang giữ 80/443
which nginx && nginx -v 2>&1            # có nginx cài trên host không?
ls /etc/nginx/sites-enabled/ /etc/nginx/conf.d/ 2>/dev/null
```

Nhìn output, xác định bạn thuộc **Case A** hay **Case B** để làm [Bước 5](#bước-5--cho-web-cũ-proxy-sang-2-case):

- **Case A — có `nginx` cài trên host** (dòng `which nginx` ra đường dẫn, `ss` thấy `nginx` giữ 80/443).
- **Case B — 80/443 do container Docker giữ** (nginx/traefik/caddy trong `docker ps`).

Nếu **chưa có Docker**, cài trước:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
exit    # đăng xuất rồi SSH lại để nhóm docker có hiệu lực
```

---

## Bước 1 — Đưa code lên VPS

**Cách 1 — git clone (khuyến nghị, sau này `git pull` để update):**

```bash
sudo mkdir -p /opt/botnews && sudo chown $USER: /opt/botnews
git clone <URL_REPO> /opt/botnews
cd /opt/botnews
```

**Cách 2 — copy thẳng từ máy bạn (không cần git remote):**

```bash
# (MÁY BẠN) nén bỏ file rác rồi scp qua gcloud
tar --exclude=.git --exclude=pgdata --exclude=redisdata --exclude='.env*' \
    -czf /tmp/botnews.tgz -C /home/toan/Dltoan/Code/botNews .
gcloud compute scp /tmp/botnews.tgz daylatoan-server:~/ \
    --zone=asia-southeast1-c --project=toan-506508
# (TRÊN VPS)
sudo mkdir -p /opt/botnews && sudo chown $USER: /opt/botnews
tar -xzf ~/botnews.tgz -C /opt/botnews && cd /opt/botnews
```

---

## Bước 2 — Cấu hình `.env`

```bash
cd /opt/botnews
cp .env.prod.example .env
nano .env
```

Bắt buộc điền/đổi: `BOT_TOKEN`, `POSTGRES_PASSWORD` (`openssl rand -hex 32`), `JWT_SECRET`
(`openssl rand -hex 32`), và **`DATABASE_URL` phải chứa đúng `POSTGRES_PASSWORD`** vừa đặt.
Điền thêm `GEMINI_API_KEY`, `API_FOOTBALL_KEY`, `NEWSAPI_KEY`, `SEPAY_*` nếu dùng.

> ⚠️ Vì DB của BotNews chạy trong container riêng (volume `pgdata` riêng), nó **không**
> đụng gì tới database của web cũ.

---

## Bước 3 — Build, tạo bảng, tạo admin

```bash
cd /opt/botnews
C="docker compose -f docker-compose.coexist.yml"

$C build
$C up -d postgres redis
$C ps                                   # chờ postgres/redis 'healthy'
$C run --rm bot alembic upgrade head    # tạo bảng
$C run --rm bot python scripts/init_admin.py   # tạo tài khoản admin (hỏi mật khẩu)
```

---

## Bước 4 — Bật toàn bộ stack

```bash
$C up -d
$C ps                                   # 6 service: postgres redis bot worker beat web
curl -s http://127.0.0.1:8010/healthz   # trả {"status":"ok"} → web đã sống
```

Lúc này **bot Telegram đã chạy** (thử nhắn lệnh). Web Admin đã sống ở `127.0.0.1:8010`
nhưng chưa ra internet — làm tiếp Bước 5 để truy cập qua domain.

> Muốn xem tạm không cần domain: từ máy bạn tạo SSH tunnel rồi mở `http://localhost:8010`:
> `gcloud compute ssh daylatoan-server --zone=asia-southeast1-c --project=toan-506508 -- -L 8010:127.0.0.1:8010`

---

## Bước 5 — Cho web cũ proxy sang (2 Case)

Trỏ DNS trước: tạo bản ghi **A** `admin.tenmien.com → IP VPS` (`dig +short admin.tenmien.com` phải ra đúng IP).

### Case A — Host có nginx cài sẵn

Tạo vhost mới cho subdomain (không sửa file của web cũ):

```bash
sudo tee /etc/nginx/conf.d/botnews-admin.conf >/dev/null <<'EOF'
server {
    listen 80;
    server_name admin.tenmien.com;
    location / {
        proxy_pass http://127.0.0.1:8010;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }
}
EOF
sudo nginx -t && sudo systemctl reload nginx
```

Cấp SSL bằng certbot của host (nếu chưa có: `sudo apt install -y certbot python3-certbot-nginx`):

```bash
sudo certbot --nginx -d admin.tenmien.com --agree-tos -m admin@tenmien.com --redirect
# certbot tự sửa vhost sang 443 + auto-renew qua systemd timer
```

Xong → `https://admin.tenmien.com`.

### Case B — 80/443 do container Docker giữ (nginx/traefik/caddy)

Web container proxy tới `127.0.0.1:8010` của host. Cách nối tùy tool:

- **Nginx trong Docker:** thêm 1 server block giống Case A nhưng `proxy_pass http://host.docker.internal:8010;`
  (thêm `extra_hosts: ["host.docker.internal:host-gateway"]` vào service nginx đó), rồi reload. SSL vẫn dùng certbot của stack cũ.
- **Traefik:** thêm labels router cho host `admin.tenmien.com` trỏ tới service ngoài (dùng `traefik.http.services...loadbalancer.server.url=http://host.docker.internal:8010`).
- **Caddy:** thêm vào `Caddyfile`:
  ```
  admin.tenmien.com {
      reverse_proxy host.docker.internal:8010
  }
  ```
  Caddy tự lo SSL. Reload container caddy.

> Không chắc web cũ dùng gì ở Case B? Dán cho tôi output `docker ps` + file cấu hình của nó, tôi viết đúng đoạn cần thêm.

---

## Bước 6 — Backup & kiểm thử

```bash
cd /opt/botnews
bash scripts/backup_db.sh && ls -lh backups/     # test backup
crontab -e
# thêm: 0 2 * * * cd /opt/botnews && bash scripts/backup_db.sh >> /var/log/botnews-backup.log 2>&1
```

Checklist:
- [ ] `https://admin.tenmien.com` login được, cert hợp lệ.
- [ ] Bot phản hồi lệnh Telegram thật.
- [ ] `docker compose -f docker-compose.coexist.yml ps` → 6 service `healthy`.
- [ ] Web cũ **vẫn chạy bình thường** (không bị ảnh hưởng).
- [ ] `sudo reboot` → cả web cũ lẫn BotNews tự lên lại.

---

## Cập nhật code sau này

```bash
cd /opt/botnews && C="docker compose -f docker-compose.coexist.yml"
git pull                     # (hoặc scp lại nếu dùng Cách 2)
$C build
$C run --rm bot alembic upgrade head
$C up -d && $C ps
```

## Lệnh vận hành

```bash
C="docker compose -f docker-compose.coexist.yml"
$C ps                 # trạng thái
$C logs -f bot        # log bot/worker/beat/web
$C restart web
$C down               # dừng BotNews (không đụng web cũ, giữ dữ liệu)
docker stats --no-stream
```

---

## ⚠️ Lưu ý quan trọng

- **Chỉ 1 bản bot chạy 1 lúc.** Nếu bot đang chạy ở máy khác/local với cùng `BOT_TOKEN`, tắt nó
  trước — 2 bản long-polling sẽ xung đột.
- **Đừng mở cổng 8010 ra ngoài.** File compose đã bind `127.0.0.1` (chỉ localhost VPS). Không đổi
  thành `0.0.0.0` trừ khi bạn hiểu rủi ro.
- **Firewall GCP:** không cần mở thêm cổng nào (dùng lại 80/443 của web cũ). DB/Redis không lộ ra ngoài.
- **RAM:** stack thêm ~1.5–2GB. Nếu VPS chật, cân nhắc nâng RAM hoặc giảm `--workers/--concurrency`.
