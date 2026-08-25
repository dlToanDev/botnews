"""Unit test logic integrations (thuần, không gọi mạng)."""
from app.integrations.gold import GoldAdapter
from app.integrations.news import match_keywords


def test_gold_to_vnd_valid():
    assert GoldAdapter._to_vnd(15060) == 15_060_000


def test_gold_to_vnd_invalid():
    assert GoldAdapter._to_vnd("") == 0
    assert GoldAdapter._to_vnd(None) == 0


def test_match_keywords():
    assert match_keywords("Bitcoin tăng mạnh", ["bitcoin"]) is True
    assert match_keywords("Giá vàng hôm nay", ["fed", "vn-index"]) is False
    assert match_keywords("bất kỳ", []) is False
