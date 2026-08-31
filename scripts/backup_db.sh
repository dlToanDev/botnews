#!/usr/bin/env bash
# ============================================================================
# backup_db.sh — Backup Postgres hằng ngày (Phase 4 mục 4.5)
# - pg_dump qua container postgres (không cần expose port).
# - Giữ 7 bản gần nhất, tự xóa bản cũ.
# - (Tùy chọn) đẩy ra ngoài VPS qua rclone hoặc scp.
#
# Cách dùng:  bash scripts/backup_db.sh
# Crontab (2h sáng):
#   0 2 * * * cd /opt/botnews && bash scripts/backup_db.sh >> /var/log/botnews-backup.log 2>&1
# ============================================================================
set -euo pipefail

# Chạy tại thư mục dự án (nơi có docker-compose.prod.yml + .env).
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Nạp biến DB từ .env.
set -a; source .env; set +a

COMPOSE="docker compose -f docker-compose.prod.yml"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
KEEP="${BACKUP_KEEP:-7}"
STAMP="$(date +%Y%m%d_%H%M%S)"
FILE="$BACKUP_DIR/botnews_${STAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "[$(date '+%F %T')] Bắt đầu backup -> $FILE"
$COMPOSE exec -T postgres \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists \
    | gzip > "$FILE"

# Kiểm tra file không rỗng và gzip hợp lệ.
if ! gzip -t "$FILE" 2>/dev/null || [ ! -s "$FILE" ]; then
    echo "[LỖI] Dump không hợp lệ, xóa $FILE" >&2
    rm -f "$FILE"
    exit 1
fi
echo "[OK] Dump hợp lệ: $(du -h "$FILE" | cut -f1)"

# Xóa bản cũ, chỉ giữ $KEEP bản mới nhất.
ls -1t "$BACKUP_DIR"/botnews_*.sql.gz 2>/dev/null | tail -n +"$((KEEP + 1))" | xargs -r rm -f
echo "[OK] Giữ tối đa $KEEP bản backup."

# --- Đẩy ra ngoài VPS (tùy chọn) — bật bằng biến môi trường ---
# rclone: cấu hình remote trước (rclone config), rồi set RCLONE_REMOTE.
if [ -n "${RCLONE_REMOTE:-}" ]; then
    echo "[..] Đẩy lên rclone remote: $RCLONE_REMOTE"
    rclone copy "$FILE" "$RCLONE_REMOTE" && echo "[OK] rclone xong."
fi
# scp: set SCP_TARGET="user@host:/path".
if [ -n "${SCP_TARGET:-}" ]; then
    echo "[..] scp -> $SCP_TARGET"
    scp "$FILE" "$SCP_TARGET" && echo "[OK] scp xong."
fi

echo "[$(date '+%F %T')] Backup hoàn tất."
