"""Adapter Giá vàng — PNJ edge API (JSON, gồm cả SJC & nhẫn)."""
from app.integrations.base import BaseAdapter, http_get_json

PNJ_GOLD = "https://edge-api.pnj.io/ecom-frontend/v1/get-gold-price"


class GoldAdapter(BaseAdapter):
    """Trả list item: {code, name, buy, sell} (đơn vị VND)."""

    name = "gold:pnj"
    ttl = 300  # 5 phút

    @staticmethod
    def _to_vnd(val) -> int:
        try:
            return int(float(val) * 1000)  # API trả nghìn đồng → VND
        except (TypeError, ValueError):
            return 0

    async def fetch(self):
        raw = await http_get_json(PNJ_GOLD)
        items = []
        for it in raw.get("data", []):
            buy = self._to_vnd(it.get("giamua"))
            sell = self._to_vnd(it.get("giaban"))
            if sell <= 0:  # bỏ item không có giá bán
                continue
            items.append(
                {
                    "code": it.get("masp"),
                    "name": it.get("tensp"),
                    "buy": buy,
                    "sell": sell,
                }
            )
        return items


gold_adapter = GoldAdapter()


async def get_gold_prices() -> list[dict]:
    return await gold_adapter.get()


async def get_gold_by_code(code: str) -> dict | None:
    for it in await get_gold_prices():
        if it["code"] == code:
            return it
    return None
