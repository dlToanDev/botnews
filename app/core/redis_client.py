"""Redis connection pool dùng chung (cache giá real-time, dedup alert, state)."""
import redis.asyncio as aioredis

from app.core.config import settings

redis_client: aioredis.Redis = aioredis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
)


async def ping() -> bool:
    """Kiểm tra kết nối Redis."""
    return await redis_client.ping()
