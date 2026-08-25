"""Tạo (hoặc cập nhật mật khẩu) tài khoản admin đầu tiên.

Cách dùng:
    # Không tương tác (CI/script): đặt sẵn mật khẩu qua env
    docker compose run --rm -e ADMIN_PASSWORD='matkhaumanh' web python scripts/init_admin.py

    # Tương tác: sẽ hỏi mật khẩu
    docker compose run --rm web python scripts/init_admin.py
"""
import asyncio
import getpass
import os

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.repositories import admin_repo


async def main() -> int:
    username = os.getenv("ADMIN_USER", settings.ADMIN_DEFAULT_USER)
    password = os.getenv("ADMIN_PASSWORD")
    if not password:
        password = getpass.getpass(f"Mật khẩu cho admin '{username}': ")
    if len(password) < 6:
        print("❌ Mật khẩu phải >= 6 ký tự.")
        return 1

    async with AsyncSessionLocal() as session:
        admin = await admin_repo.get_by_username(session, username)
        if admin is None:
            admin = await admin_repo.create(session, username, hash_password(password))
            print(f"✅ Đã tạo admin '{username}'.")
        else:
            admin.password_hash = hash_password(password)
            print(f"♻️  Đã cập nhật mật khẩu cho admin '{username}'.")
        await session.commit()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
