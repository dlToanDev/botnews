#!/usr/bin/env bash
# Khởi động toàn bộ stack dev trên máy local (không dùng Docker).
# Gồm: postgres, redis, bot, web, celery worker, celery beat.
# Log ghi vào logs/, PID ghi vào logs/pids/. Dừng bằng scripts/dev_stop.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LOG_DIR="$ROOT/logs"
PID_DIR="$LOG_DIR/pids"
mkdir -p "$PID_DIR"

PG_DATA="$HOME/.local/postgres/data"
PG_BIN="$HOME/.local/postgres/usr/lib/postgresql/16/bin"
REDIS_DIR="$HOME/.local/redis"

export PYTHONPATH="$ROOT"
PY="$ROOT/.venv/bin/python"
[[ -x "$PY" ]] || { echo "❌ Chưa có venv. Chạy: uv venv .venv && uv pip install -r requirements.txt"; exit 1; }
[[ -f "$ROOT/.env" ]] || { echo "❌ Thiếu file .env (xem .env.example)"; exit 1; }

# --- Hạ tầng: postgres + redis ---------------------------------------------
if "$PG_BIN/pg_ctl" -D "$PG_DATA" status >/dev/null 2>&1; then
  echo "✓ postgres đã chạy"
else
  "$PG_BIN/pg_ctl" -D "$PG_DATA" -l "$HOME/.local/postgres/logfile" start >/dev/null
  echo "✓ postgres started"
fi

if "$REDIS_DIR/../bin/redis-cli" ping >/dev/null 2>&1; then
  echo "✓ redis đã chạy"
else
  LD_LIBRARY_PATH="$REDIS_DIR/usr/lib/x86_64-linux-gnu" \
    "$REDIS_DIR/usr/bin/redis-server" --daemonize yes --port 6379 \
    --dir "$REDIS_DIR/data" --logfile "$REDIS_DIR/redis.log"
  echo "✓ redis started"
fi

# --- Tiến trình ứng dụng ----------------------------------------------------
# start <tên> <lệnh...>  — bỏ qua nếu đã chạy, ghi log + pid
start() {
  local name="$1"; shift
  local pidfile="$PID_DIR/$name.pid"
  if [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    echo "✓ $name đã chạy (pid $(cat "$pidfile"))"
    return
  fi
  # setsid: mỗi tiến trình một process group riêng, để dev_stop.sh kill
  # cả cây con (uvicorn/celery sinh nhiều process) mà không đụng shell gọi nó.
  setsid "$@" >>"$LOG_DIR/$name.log" 2>&1 &
  echo $! >"$pidfile"
  echo "✓ $name started (pid $!) → logs/$name.log"
}

start bot    "$PY" -m app.bot.main
start web    "$ROOT/.venv/bin/uvicorn" app.web.main:app --port 8000
start worker "$ROOT/.venv/bin/celery" -A app.worker.celery_app worker --loglevel=info --concurrency=2
start beat   "$ROOT/.venv/bin/celery" -A app.worker.celery_app beat --loglevel=info

sleep 3
echo
echo "Web admin: http://127.0.0.1:8000"
echo "Xem log:   tail -f logs/{bot,web,worker,beat}.log"
echo "Dừng:      scripts/dev_stop.sh"

# Cảnh báo sớm nếu tiến trình nào chết ngay sau khi khởi động
for name in bot web worker beat; do
  pid="$(cat "$PID_DIR/$name.pid")"
  kill -0 "$pid" 2>/dev/null || echo "⚠️  $name đã thoát — xem logs/$name.log"
done
