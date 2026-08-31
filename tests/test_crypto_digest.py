"""Unit test format bản tin crypto digest (thuần)."""
from app.services.crypto_service import format_price_digest

_COINS = [
    {"symbol": "BTC", "price_usd": 67234, "change_pct": 2.34},
    {"symbol": "ETH", "price_usd": 3512, "change_pct": -1.2},
]


def test_digest_has_header_symbols_prices_arrows():
    text = format_price_digest(_COINS, "09:30 29/08")
    assert "09:30 29/08" in text
    assert "BTC" in text and "ETH" in text
    assert "$67,234" in text and "$3,512" in text
    assert "+2.34%" in text and "-1.20%" in text
    assert "🟢" in text and "🔴" in text


def test_digest_handles_missing_change():
    text = format_price_digest([{"symbol": "TON", "price_usd": 5.1, "change_pct": None}], "x")
    assert "TON" in text


# ---------------- resolve_notify + select_coins ----------------
from app.services.crypto_service import resolve_notify, select_coins  # noqa: E402


def test_resolve_off():
    assert resolve_notify("off", ["09:00"], ["BTC"], True, ["10:00"], ["ETH"]) == ([], [])


def test_resolve_custom_uses_user():
    assert resolve_notify("custom", ["09:00"], ["BTC"], True, ["10:00"], ["ETH"]) == (["09:00"], ["BTC"])


def test_resolve_system_enabled_uses_system():
    assert resolve_notify("system", ["09:00"], ["BTC"], True, ["10:00"], ["ETH"]) == (["10:00"], ["ETH"])


def test_resolve_system_disabled_empty():
    assert resolve_notify("system", [], [], False, ["10:00"], ["ETH"]) == ([], [])


def test_select_coins_empty_means_all():
    allc = [{"symbol": "BTC"}, {"symbol": "ETH"}]
    assert select_coins(allc, []) == allc


def test_select_coins_filters_by_symbol():
    allc = [{"symbol": "BTC"}, {"symbol": "ETH"}, {"symbol": "SOL"}]
    got = [c["symbol"] for c in select_coins(allc, ["ETH", "SOL"])]
    assert got == ["ETH", "SOL"]
