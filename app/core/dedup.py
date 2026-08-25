"""Chống spam cảnh báo trùng bằng Redis (SET NX EX)."""
from app.core.redis_client import redis_client


async def should_alert(key: str, ttl_seconds: int) -> bool:
    """Trả True nếu được phép gửi (chưa gửi gần đây); đồng thời đặt cờ TTL.

    Dùng SET key 1 NX EX ttl → thành công (True) nghĩa là key chưa tồn tại.
    """
    ok = await redis_client.set(f"dedup:{key}", "1", ex=ttl_seconds, nx=True)
    return bool(ok)
