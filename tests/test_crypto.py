"""Unit test logic crypto (CoinGecko) + format hiển thị (thuần, không gọi mạng)."""
from app.bot.handlers import features
from app.integrations.coingecko import _normalize


# ---------------- Chuẩn hóa dữ liệu CoinGecko ----------------

_USD = {
    "id": "bitcoin",
    "symbol": "btc",
    "name": "Bitcoin",
    "current_price": 67234,
    "market_cap": 1_330_000_000_000,
    "market_cap_rank": 1,
    "high_24h": 68100,
    "low_24h": 65900,
    "total_volume": 28_500_000_000,
    "price_change_percentage_24h": 2.34,
}
_VND = {"id": "bitcoin", "current_price": 1_712_345_678}


def test_normalize_maps_fields_and_uppercases_symbol():
    d = _normalize(_USD, _VND)
    assert d["id"] == "bitcoin"
    assert d["symbol"] == "BTC"
    assert d["name"] == "Bitcoin"
    assert d["price_usd"] == 67234
    assert d["price_vnd"] == 1_712_345_678
    assert d["change_pct"] == 2.34
    assert d["high_usd"] == 68100
    assert d["low_usd"] == 65900
    assert d["market_cap"] == 1_330_000_000_000
    assert d["volume"] == 28_500_000_000
    assert d["rank"] == 1


def test_normalize_handles_missing_vnd():
    d = _normalize(_USD, None)
    assert d["price_vnd"] is None
    assert d["price_usd"] == 67234


# ---------------- Format số ----------------

def test_fmt_usd_large_no_decimals():
    assert features._fmt_usd(67234) == "$67,234"


def test_fmt_usd_mid_two_decimals():
    assert features._fmt_usd(164.2) == "$164.20"


def test_fmt_usd_small_four_decimals():
    assert features._fmt_usd(0.1523) == "$0.1523"


def test_fmt_usd_none():
    assert features._fmt_usd(None) == "N/A"


def test_fmt_compact_trillions():
    assert features._fmt_compact(1_330_000_000_000) == "$1.33T"


def test_fmt_compact_billions():
    assert features._fmt_compact(28_500_000_000) == "$28.50B"


def test_fmt_compact_millions():
    assert features._fmt_compact(5_200_000) == "$5.20M"


def test_fmt_compact_none():
    assert features._fmt_compact(None) == "N/A"


# ---------------- Format tin nhắn ----------------

def test_format_coin_contains_key_info():
    d = _normalize(_USD, _VND)
    text = features.format_coin(d)
    assert "Bitcoin" in text
    assert "BTC" in text
    assert "$67,234" in text
    assert "#1" in text
    assert "🟢" in text          # %24h dương → xanh
    assert "+2.34%" in text
    assert "$1.33T" in text       # vốn hóa
    assert "1.712.345.678" in text  # VND phân cách dấu chấm


def test_format_coin_red_arrow_on_negative():
    d = _normalize({**_USD, "price_change_percentage_24h": -1.2}, _VND)
    text = features.format_coin(d)
    assert "🔴" in text
    assert "-1.20%" in text


def test_format_top_lists_ranked_coins():
    coins = [
        _normalize(_USD, None),
        _normalize({**_USD, "id": "ethereum", "symbol": "eth", "name": "Ethereum",
                    "current_price": 3512, "market_cap_rank": 2,
                    "price_change_percentage_24h": -1.2}, None),
    ]
    text = features.format_top(coins)
    assert "TOP" in text
    assert "BTC" in text
    assert "ETH" in text
    assert "$67,234" in text
    assert "$3,512" in text
