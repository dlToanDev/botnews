"""Adapter Crypto — Binance REST (public, không cần key)."""
from app.integrations.base import BaseAdapter, http_get_json

BINANCE_24H = "https://api.binance.com/api/v3/ticker/24hr"
BINANCE_PRICE = "https://api.binance.com/api/v3/ticker/price"


class BinanceTickerAdapter(BaseAdapter):
    """Lấy toàn bộ 24h ticker 1 lần → dict symbol -> {price, change_pct}."""

    name = "crypto:binance:24h"
    ttl = 60

    async def fetch(self):
        data = await http_get_json(BINANCE_24H)
        out = {}
        for it in data:
            sym = it.get("symbol")
            if not sym:
                continue
            out[sym] = {
                "price": float(it["lastPrice"]),
                "change_pct": float(it["priceChangePercent"]),
            }
        return out


ticker_adapter = BinanceTickerAdapter()


async def get_all_tickers() -> dict[str, dict]:
    return await ticker_adapter.get()


async def get_price(symbol: str) -> dict | None:
    """Giá + %24h của 1 symbol (vd BTCUSDT). None nếu không có."""
    symbol = symbol.upper()
    tickers = await get_all_tickers()
    return tickers.get(symbol)
