#!/usr/bin/env bash
# Chạy toàn bộ stack ở foreground — giống `npm run dev`.
# Log của cả 4 tiến trình đổ chung ra terminal, có nhãn màu.
# Ctrl+C hoặc đóng terminal/VS Code => mọi thứ tự tắt.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT"

VENV="$ROOT/.venv"
[[ -x "$VENV/bin/python" ]] || { echo "❌ Chưa có venv (.venv)"; exit 1; }
[[ -f "$ROOT/.env" ]]       || { echo "❌ Thiếu file .env"; exit 1; }

PG_BIN="$HOME/.local/postgres/usr/lib/postgresql/16/bin"
REDIS_DIR="$HOME/.local/redis"

# --- Hạ tầng: bật nền, KHÔNG tắt khi thoát (postgres/redis chạy chung máy) ---
"$PG_BIN/pg_ctl" -D "$HOME/.local/postgres/data" status >/dev/null 2>&1 \
  || "$PG_BIN/pg_ctl" -D "$HOME/.local/postgres/data" -l "$HOME/.local/postgres/logfile" start >/dev/null
"$HOME/.local/bin/redis-cli" ping >/dev/null 2>&1 \
  || LD_LIBRARY_PATH="$REDIS_DIR/usr/lib/x86_64-linux-gnu" "$REDIS_DIR/usr/bin/redis-server" \
       --daemonize yes --port 6379 --dir "$REDIS_DIR/data" --logfile "$REDIS_DIR/redis.log"

PIDS=()

cleanup() {
  trap - INT TERM EXIT
  echo
  echo "⏹  Đang tắt..."
  for pid in "${PIDS[@]}"; do kill -TERM "$pid" 2>/dev/null; done
  for _ in $(seq 20); do
    local alive=0
    for pid in "${PIDS[@]}"; do kill -0 "$pid" 2>/dev/null && alive=1; done
    [[ $alive -eq 0 ]] && break
    sleep 0.5
  done
  for pid in "${PIDS[@]}"; do kill -KILL "$pid" 2>/dev/null; done
  # celery/uvicorn có thể để lại process con
  pkill -KILL -f "app[.]worker[.]celery_app" 2>/dev/null
  echo "✓ Đã tắt bot, web, worker, beat (postgres + redis vẫn chạy)"
  exit 0
}
trap cleanup INT TERM EXIT

# run <nhãn> <màu> <lệnh...> — gắn tiền tố vào từng dòng log
run() {
  local label="$1" color="$2"; shift 2
  "$@" > >(while IFS= read -r line; do printf "\033[%sm[%-6s]\033[0m %s\n" "$color" "$label" "$line"; done) 2>&1 &
  PIDS+=($!)
}

run bot    36 "$VENV/bin/python" -m app.bot.main
run web    32 "$VENV/bin/uvicorn" app.web.main:app --port 8000
run worker 33 "$VENV/bin/celery" -A app.worker.celery_app worker --loglevel=info --concurrency=2
run beat   35 "$VENV/bin/celery" -A app.worker.celery_app beat --loglevel=info

echo "▶  bot · web · worker · beat đang chạy — Ctrl+C để dừng"
echo "   Web admin: http://127.0.0.1:8000"
echo

wait -n          # tiến trình nào chết trước thì tắt hết phần còn lại
cleanup
