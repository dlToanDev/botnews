#!/usr/bin/env bash
# ============================================================================
# init_letsencrypt.sh — Bootstrap SSL Let's Encrypt lần đầu (Phase 4 mục 4.3)
# Giải bài toán con-gà-quả-trứng: Nginx cần cert để start, nhưng certbot cần
# Nginx chạy để xác thực. Cách làm:
#   1) Tạo cert giả (self-signed) để Nginx start được.
#   2) Start Nginx.
#   3) Xóa cert giả, xin cert thật qua webroot ACME challenge.
#   4) Reload Nginx.
#
# Cách dùng:  DOMAIN=admin.hvpgroup.vn EMAIL=admin@hvpgroup.vn bash scripts/init_letsencrypt.sh
# ============================================================================
set -euo pipefail

DOMAIN="${DOMAIN:?Cần set DOMAIN, vd: DOMAIN=admin.hvpgroup.vn}"
EMAIL="${EMAIL:?Cần set EMAIL, vd: EMAIL=admin@hvpgroup.vn}"
STAGING="${STAGING:-0}"   # =1 để test bằng Let's Encrypt staging (tránh rate limit)

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
COMPOSE="docker compose -f docker-compose.prod.yml"

CERT_PATH="/etc/letsencrypt/live/$DOMAIN"

echo "### 1. Tạo cert giả cho $DOMAIN để Nginx start được..."
$COMPOSE run --rm --entrypoint "\
  sh -c 'mkdir -p $CERT_PATH && \
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout $CERT_PATH/privkey.pem \
    -out $CERT_PATH/fullchain.pem \
    -subj /CN=localhost'" certbot

echo "### 2. Start Nginx..."
$COMPOSE up -d nginx

echo "### 3. Xóa cert giả..."
$COMPOSE run --rm --entrypoint "\
  rm -rf /etc/letsencrypt/live/$DOMAIN \
         /etc/letsencrypt/archive/$DOMAIN \
         /etc/letsencrypt/renewal/$DOMAIN.conf" certbot

echo "### 4. Xin cert thật từ Let's Encrypt..."
STAGING_ARG=""
[ "$STAGING" != "0" ] && STAGING_ARG="--staging"
$COMPOSE run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
    $STAGING_ARG \
    --email $EMAIL --agree-tos --no-eff-email \
    -d $DOMAIN --non-interactive" certbot

echo "### 5. Reload Nginx với cert thật..."
$COMPOSE exec nginx nginx -s reload

echo "✅ Xong. Kiểm tra: https://$DOMAIN"
