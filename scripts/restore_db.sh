#!/usr/bin/env bash
# ============================================================================
# restore_db.sh — Restore Postgres từ file backup (.sql.gz) — Phase 4 mục 4.6
# Dùng để KIỂM THỬ restore (bắt buộc test được thì backup mới có nghĩa).
#
# Cách dùng:  bash scripts/restore_db.sh backups/botnews_20260825_020000.sql.gz
# ⚠️ Sẽ GHI ĐÈ dữ liệu hiện tại (dump tạo với --clean --if-exists).
# ============================================================================
set -euo pipefail

DUMP="${1:-}"
if [ -z "$DUMP" ] || [ ! -f "$DUMP" ]; then
    echo "Cách dùng: bash scripts/restore_db.sh <file.sql.gz>" >&2
    exit 1
fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
set -a; source .env; set +a

COMPOSE="docker compose -f docker-compose.prod.yml"

echo "⚠️  Sắp GHI ĐÈ database '$POSTGRES_DB' bằng: $DUMP"
read -rp "Gõ 'yes' để tiếp tục: " ok
[ "$ok" = "yes" ] || { echo "Hủy."; exit 1; }

if ! gzip -t "$DUMP" 2>/dev/null; then
    echo "[LỖI] File gzip hỏng." >&2; exit 1
fi

echo "[..] Đang restore..."
gunzip -c "$DUMP" | $COMPOSE exec -T postgres \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1
echo "[OK] Restore hoàn tất."
