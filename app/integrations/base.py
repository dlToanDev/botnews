"""Nền tảng cho Adapter gọi API ngoài: HTTP retry + cache Redis + stale fallback."""
import asyncio
import json
from typing import Any

import httpx

from app.core.logging import get_logger
from app.core.redis_client import redis_client

logger = get_logger(__name__)

DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 (BotNews/1.0)"}


async def http_get_json(url: str, *, params: dict | None = None,
                        headers: dict | None = None, timeout: float = 8.0,
                        attempts: int = 3) -> Any:
    """GET JSON với retry + backoff."""
    last_exc: Exception | None = None
    async with httpx.AsyncClient(timeout=timeout, headers={**DEFAULT_HEADERS, **(headers or {})}) as client:
        for i in range(attempts):
            try:
                r = await client.get(url, params=params)
                r.raise_for_status()
                return r.json()
            except Exception as e:  # noqa: BLE001
                last_exc = e
                await asyncio.sleep(0.4 * (i + 1))
    raise last_exc  # type: ignore[misc]


async def http_get_text(url: str, *, timeout: float = 8.0, attempts: int = 3) -> str:
    last_exc: Exception | None = None
    async with httpx.AsyncClient(timeout=timeout, headers=DEFAULT_HEADERS) as client:
        for i in range(attempts):
            try:
                r = await client.get(url)
                r.raise_for_status()
                return r.text
            except Exception as e:  # noqa: BLE001
                last_exc = e
                await asyncio.sleep(0.4 * (i + 1))
    raise last_exc  # type: ignore[misc]


class BaseAdapter:
    """Adapter có cache Redis. Subclass override `name`, `ttl`, `fetch()`."""

    name: str = "base"
    ttl: int = 60  # giây

    async def fetch(self) -> Any:
        """Lấy dữ liệu tươi (JSON-serializable). Subclass phải cài đặt."""
        raise NotImplementedError

    def _key(self) -> str:
        return f"cache:{self.name}"

    async def get(self, force: bool = False) -> Any:
        key = self._key()
        if not force:
            cached = await redis_client.get(key)
            if cached is not None:
                return json.loads(cached)
        try:
            data = await self.fetch()
        except Exception as e:  # noqa: BLE001
            stale = await redis_client.get(key + ":stale")
            if stale is not None:
                logger.warning("[%s] fetch lỗi (%s) → dùng cache cũ.", self.name, e)
                return json.loads(stale)
            logger.error("[%s] fetch lỗi và không có cache cũ: %s", self.name, e)
            raise
        payload = json.dumps(data, default=str)
        await redis_client.set(key, payload, ex=self.ttl)
        await redis_client.set(key + ":stale", payload, ex=self.ttl * 20)
        return data
