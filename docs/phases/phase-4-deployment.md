# Phase 4 — Deployment VPS, Bảo mật & Backup

> ⏱️ **Thời lượng:** Tuần 8
> 🎯 **Mục tiêu:** Chạy production 24/7 ổn định, HTTPS cho admin, tự phục hồi, tự backup.
> 📦 **Deliverable:** Hệ thống live trên VPS; admin truy cập qua HTTPS; backup DB hằng ngày.
> 🔗 **Phụ thuộc:** Phase 1–3 hoàn thành.
> 🤖 **Bot mode:** Long Polling (đã chốt) — không cần route webhook, đơn giản hơn.

> ✅ **Trạng thái:** Toàn bộ **artifact deploy đã có sẵn trong repo** — chỉ còn thao tác
> chạy trên VPS thật. Xem runbook chi tiết: [`docs/DEPLOYMENT.md`](../DEPLOYMENT.md).
>
> | Artifact | File |
> |---|---|
> | Compose production (7 service + certbot) | `docker-compose.prod.yml` |
> | Nginx reverse proxy + SSL + redirect + allowlist | `nginx/nginx.conf`, `nginx/conf.d/admin.conf` |
> | Bootstrap SSL Let's Encrypt | `scripts/init_letsencrypt.sh` |
> | Backup DB (giữ 7 bản, offsite tùy chọn) | `scripts/backup_db.sh` |
> | Restore DB (test restore) | `scripts/restore_db.sh` |
> | Healthcheck endpoint | `GET /healthz` (app/web/main.py) |
> | Mẫu env production | `.env.prod.example` |
>
> Các ô `[ ]` bên dưới là **thao tác vận hành trên VPS** (cài Docker, DNS, ufw, chạy compose…)
> — thực hiện theo `docs/DEPLOYMENT.md`.

## Task list (làm tuần tự)

### 4.1. Chuẩn bị VPS
- [ ] Cài Docker + Docker Compose plugin trên VPS Linux (2vCPU/4GB).
- [ ] Tạo user non-root, cấu hình SSH key, tắt password login.
- [ ] Cấu hình firewall (`ufw`): mở 22, 80, 443; **đóng 5432/6379** ra ngoài.
- [ ] Trỏ domain `admin.yourdomain.com` về IP VPS (A record).

### 4.2. Compose production
- [ ] `docker-compose.prod.yml`: postgres, redis, bot, worker, beat, web, nginx.
- [ ] `restart: always` + `healthcheck` cho mọi service.
- [ ] Giới hạn tài nguyên: worker `--concurrency=2`, uvicorn `--workers 2`.
- [ ] Postgres tuning: `shared_buffers=512MB`, `max_connections=50`.
- [ ] Redis: `maxmemory 512mb --maxmemory-policy allkeys-lru`.
- [ ] **Không** expose port DB/Redis ra ngoài (chỉ trong docker network).

### 4.3. Nginx + SSL
- [ ] `nginx/nginx.conf` reverse proxy `web:8000` (mục 5.13).
- [ ] Chạy **Certbot** lấy SSL Let's Encrypt cho `admin.yourdomain.com`.
- [ ] Redirect 80 → 443; auto-renew cert (cron certbot renew).
- [ ] (Tùy chọn) IP allowlist trong Nginx: chỉ IP của bạn truy cập admin.

### 4.4. Khởi chạy & migration
- [ ] Copy `.env` production lên VPS (không commit).
- [ ] `docker compose -f docker-compose.prod.yml up -d postgres redis`.
- [ ] `docker compose run --rm bot alembic upgrade head`.
- [ ] `docker compose run --rm bot python scripts/init_admin.py`.
- [ ] `docker compose -f docker-compose.prod.yml up -d` (toàn bộ).

### 4.5. Backup & vận hành
- [ ] `scripts/backup_db.sh`: `pg_dump` hằng ngày, giữ 7 bản, đẩy ra ngoài VPS (S3/rclone/scp).
- [ ] Thêm vào crontab VPS (VD 2h sáng).
- [ ] Log rotation cho container (`json-file` max-size/max-file trong compose).
- [ ] (Tùy chọn) Uptime Kuma hoặc healthcheck endpoint để giám sát.

### 4.6. Kiểm thử production
- [ ] Truy cập `https://admin.yourdomain.com` → SSL hợp lệ, login OK.
- [ ] Bot phản hồi lệnh thật.
- [ ] Reboot VPS → mọi container tự khởi động lại (`restart: always`).
- [ ] Chạy thử `backup_db.sh` → có file dump hợp lệ, restore thử được.

## ✅ Definition of Done
- [ ] Toàn bộ 7 service chạy `healthy` trên VPS, tự restart sau reboot.
- [ ] Web Admin truy cập qua **HTTPS**, cert auto-renew.
- [ ] Port DB/Redis **không** lộ ra internet (kiểm tra bằng `nmap` từ ngoài).
- [ ] Bot hoạt động đầy đủ 4 module + lịch cá nhân trên production.
- [ ] Backup DB tự động chạy hằng ngày, đã test restore thành công.
- [ ] RAM/CPU ổn định dưới ngưỡng (theo dõi `docker stats` vài ngày).

---

## 🎉 Sau Phase 4
Hệ thống SaaS đã live. Các bước mở rộng tương lai (optional):
- Thanh toán tự động (VNPay/Momo) + tự kích hoạt gói.
- Webhook mode nếu user tăng mạnh.
- Dashboard biểu đồ doanh thu, retention.
- Multi-admin / phân quyền admin.
