#!/usr/bin/env bash
# Dừng các tiến trình ứng dụng do dev_start.sh khởi động.
# Mặc định GIỮ postgres + redis chạy; thêm --all để tắt luôn hạ tầng.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$ROOT/logs/pids"
STOP_INFRA=0
[[ "${1:-}" == "--all" ]] && STOP_INFRA=1

for name in bot web worker beat; do
  pidfile="$PID_DIR/$name.pid"
  if [[ ! -f "$pidfile" ]]; then
    echo "· $name không chạy"
    continue
  fi
  pid="$(cat "$pidfile")"
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "· $name đã tắt sẵn"
    rm -f "$pidfile"
    continue
  fi
  # Kill cả nhóm tiến trình: uvicorn/celery sinh process con
  pgid="$(ps -o pgid= -p "$pid" | tr -d ' ')"
  kill -TERM -"$pgid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null
  for _ in $(seq 20); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.5
  done
  if kill -0 "$pid" 2>/dev/null; then
    kill -KILL -"$pgid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null
    echo "✓ $name stopped (buộc dừng)"
  else
    echo "✓ $name stopped"
  fi
  rm -f "$pidfile"
done

if [[ $STOP_INFRA -eq 1 ]]; then
  "$HOME/.local/postgres/usr/lib/postgresql/16/bin/pg_ctl" -D "$HOME/.local/postgres/data" stop -m fast >/dev/null 2>&1 \
    && echo "✓ postgres stopped" || echo "· postgres không chạy"
  "$HOME/.local/bin/redis-cli" shutdown nosave >/dev/null 2>&1 \
    && echo "✓ redis stopped" || echo "· redis không chạy"
else
  echo
  echo "(postgres + redis vẫn chạy — dùng --all để tắt luôn)"
fi
