"""Session helper cho Celery worker.

Mỗi task chạy trong event loop riêng (asyncio.run). Để tránh lỗi tái sử dụng
connection pool giữa các loop, ta tạo engine mới (NullPool) cho mỗi lần dùng.
"""
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings


@asynccontextmanager
async def worker_session():
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()
