"""Kiểm tra nhanh môi trường Phase 0.

Cách dùng (local, cần postgres/redis đã 'up' và map ra 127.0.0.1):
    DATABASE_URL=postgresql+asyncpg://botadmin:<pass>@localhost:5432/botnews \
    REDIS_URL=redis://localhost:6379/0 \
    python scripts/check_setup.py

Trong Docker:
    docker compose run --rm bot python scripts/check_setup.py
"""
import asyncio
import sys


async def main() -> int:
    ok = True

    # 1) Config
    try:
        from app.core.config import settings
        token = settings.BOT_TOKEN
        print(f"[OK ] Config load. BOT_TOKEN prefix = {token[:5]}...")
    except Exception as e:  # noqa: BLE001
        print(f"[ERR] Không load được config: {e}")
        return 1

    # 2) Redis
    try:
        from app.core.redis_client import ping
        await ping()
        print("[OK ] Redis PING thành công.")
    except Exception as e:  # noqa: BLE001
        print(f"[ERR] Redis lỗi: {e}")
        ok = False

    # 3) PostgreSQL
    try:
        from sqlalchemy import text
        from app.core.database import engine
        async with engine.connect() as conn:
            (val,) = (await conn.execute(text("SELECT 1"))).one()
            assert val == 1
        print("[OK ] PostgreSQL SELECT 1 thành công.")
    except Exception as e:  # noqa: BLE001
        print(f"[ERR] PostgreSQL lỗi: {e}")
        ok = False

    # 4) Bot token (tùy chọn — chỉ chạy nếu token đã điền)
    if token and not token.startswith("PUT_YOUR"):
        try:
            from telegram import Bot
            me = await Bot(token=token).get_me()
            print(f"[OK ] Bot token hợp lệ: @{me.username} (id={me.id})")
        except Exception as e:  # noqa: BLE001
            print(f"[ERR] Bot token không hợp lệ: {e}")
            ok = False
    else:
        print("[SKIP] BOT_TOKEN chưa điền — bỏ qua kiểm tra Telegram.")

    print("\n=> KẾT QUẢ:", "TẤT CẢ OK ✅" if ok else "CÓ LỖI ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
