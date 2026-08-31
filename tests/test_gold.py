"""Unit test gold_service: parse giờ, giờ hiệu lực, format tin (thuần)."""
import pytest

from app.services.gold_service import effective_times, format_gold_prices, parse_times


# ---------------- parse_times ----------------

def test_parse_times_basic():
    assert parse_times("09:00, 16:00") == ["09:00", "16:00"]


def test_parse_times_normalizes_and_sorts_and_dedups():
    assert parse_times("16:00 9:00 09:00") == ["09:00", "16:00"]


def test_parse_times_empty():
    assert parse_times("") == []
    assert parse_times("   ") == []


def test_parse_times_invalid_raises():
    with pytest.raises(ValueError):
        parse_times("25:00")
    with pytest.raises(ValueError):
        parse_times("abc")
    with pytest.raises(ValueError):
        parse_times("09:70")


# ---------------- effective_times ----------------

def test_effective_prefers_user():
    assert effective_times(["07:30"], True, ["09:00"]) == ["07:30"]


def test_effective_falls_back_to_system_when_user_empty():
    assert effective_times([], True, ["09:00", "16:00"]) == ["09:00", "16:00"]


def test_effective_empty_when_system_disabled_and_no_user():
    assert effective_times([], False, ["09:00"]) == []


# ---------------- format_gold_prices ----------------

_ITEMS = [
    {"code": "SJC", "name": "Vàng miếng SJC 999.9", "buy": 14_570_000, "sell": 14_870_000},
    {"code": "N24K", "name": "Nhẫn Trơn PNJ 999.9", "buy": 14_570_000, "sell": 14_870_000},
    {"code": "24K", "name": "Vàng nữ trang 999.9", "buy": 14_300_000, "sell": 14_800_000},
    {"code": "33", "name": "Vàng 333 (8K)", "buy": 3_938_000, "sell": 4_928_000},
]


def test_format_gold_curated_and_unit():
    text = format_gold_prices(_ITEMS, "09:30 29/08")
    # 3 loại chính hiển thị (nhãn thân thiện)
    assert "Vàng miếng SJC" in text
    assert "Nhẫn trơn PNJ 999.9" in text
    assert "Vàng nữ trang 999.9" in text
    assert "14.570.000" in text and "14.800.000" in text
    assert "Mua" in text and "Bán" in text
    assert "09:30 29/08" in text
    assert "VND/chỉ" in text            # đơn vị đúng
    assert "Vàng 333" not in text       # loại phụ bị lọc


def test_format_gold_fallback_when_no_curated_codes():
    items = [{"code": "X1", "name": "Loại lạ A", "buy": 1_000_000, "sell": 1_100_000}]
    text = format_gold_prices(items, "09:30 29/08")
    assert "Loại lạ A" in text          # không có code chuẩn → vẫn hiện
