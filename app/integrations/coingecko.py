"""Adapter CoinGecko — giá coin đầy đủ (USD+VND, vốn hóa, đỉnh/đáy). Public, không cần key."""
import asyncio

from app.core.constants import COIN_IDS
from app.integrations.base import BaseAdapter, http_get_json

COINGECKO_MARKETS = "https://api.coingecko.com/api/v3/coins/markets"


class CoinMarketsAdapter(BaseAdapter):
    """Gọi /coins/markets với bộ params cho trước; mỗi biến thể có cache riêng."""

    ttl = 60

    def __init__(self, cache_key: str, params: dict):
        self.name = f"crypto:coingecko:{cache_key}"
        self.params = params

    async def fetch(self):
        return await http_get_json(COINGECKO_MARKETS, params=self.params)


def _normalize(usd: dict, vnd: dict | None) -> dict:
    """Chuẩn hóa 1 item CoinGecko (bản USD + bản VND) → dict thống nhất."""
    return {
        "id": usd.get("id"),
        "symbol": (usd.get("symbol") or "").upper(),
        "name": usd.get("name"),
        "price_usd": usd.get("current_price"),
        "price_vnd": (vnd or {}).get("current_price"),
        "change_pct": usd.get("price_change_percentage_24h"),
        "high_usd": usd.get("high_24h"),
        "low_usd": usd.get("low_24h"),
        "market_cap": usd.get("market_cap"),
        "volume": usd.get("total_volume"),
        "rank": usd.get("market_cap_rank"),
    }


# Adapter cho nhóm đồng ta theo dõi (lấy 1 lần cho cả nhóm, cache lại).
_IDS = ",".join(COIN_IDS.values())
_usd_adapter = CoinMarketsAdapter(
    "tracked:usd",
    {"vs_currency": "usd", "ids": _IDS, "price_change_percentage": "24h"},
)
_vnd_adapter = CoinMarketsAdapter("tracked:vnd", {"vs_currency": "vnd", "ids": _IDS})


async def get_coin(coin_id: str) -> dict | None:
    """Dữ liệu đầy đủ 1 đồng theo CoinGecko id. None nếu không có."""
    usd_list, vnd_list = await asyncio.gather(_usd_adapter.get(), _vnd_adapter.get())
    usd_by = {it["id"]: it for it in usd_list}
    vnd_by = {it["id"]: it for it in vnd_list}
    raw = usd_by.get(coin_id)
    if not raw:
        return None
    return _normalize(raw, vnd_by.get(coin_id))


async def get_tracked() -> list[dict]:
    """8 đồng theo dõi (COIN_IDS), chuẩn hoá, đúng thứ tự khai báo."""
    usd_list, vnd_list = await asyncio.gather(_usd_adapter.get(), _vnd_adapter.get())
    usd_by = {it["id"]: it for it in usd_list}
    vnd_by = {it["id"]: it for it in vnd_list}
    out = []
    for sym, coin_id in COIN_IDS.items():
        raw = usd_by.get(coin_id)
        if raw:
            d = _normalize(raw, vnd_by.get(coin_id))
            d["symbol"] = sym.upper()  # dùng ký hiệu ta khai báo (tránh symbol lạ từ API, vd TON)
            out.append(d)
    return out


async def get_top(limit: int = 10) -> list[dict]:
    """Top N đồng theo vốn hóa (giảm dần)."""
    adapter = CoinMarketsAdapter(
        f"top:{limit}",
        {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": limit,
            "page": 1,
            "price_change_percentage": "24h",
        },
    )
    return [_normalize(it, None) for it in await adapter.get()]
