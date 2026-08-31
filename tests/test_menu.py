"""Unit test hàm thuần của menu bot (không cần Telegram runtime)."""
from app.bot.handlers.menu import (
    build_buy_root,
    build_main_menu,
    build_products_kb,
    format_owned,
    hhmm_to_display,
    toggle,
)


def _all_cb(markup):
    return [b.callback_data for row in markup.inline_keyboard for b in row]


def test_toggle_adds_and_removes():
    assert toggle(["a"], "b") == ["a", "b"]
    assert toggle(["a", "b"], "a") == ["b"]


def test_hhmm_to_display():
    assert hhmm_to_display("0900") == "09:00"
    assert hhmm_to_display("2230") == "22:30"


def test_main_menu_has_buy_and_mine():
    cbs = _all_cb(build_main_menu())
    assert "menu:buy" in cbs
    assert "menu:mine" in cbs


def test_buy_root_has_pkg_and_single():
    cbs = _all_cb(build_buy_root())
    assert "menu:buy:pkg" in cbs
    assert "menu:buy:single" in cbs


def test_products_kb_single_has_buy_gold():
    cbs = _all_cb(build_products_kb("single"))
    assert "buy:gold" in cbs and "buy:crypto" in cbs
    assert "buy:full" not in cbs  # full thuộc nhóm gói


def test_products_kb_pkg_has_full():
    cbs = _all_cb(build_products_kb("pkg"))
    assert "buy:full" in cbs
    assert "buy:gold" not in cbs


def test_format_owned_lists_enabled_only():
    text = format_owned({"gold": True, "crypto": False, "news": True})
    assert "vàng" in text.lower() or "Giá vàng" in text
    assert "Crypto" not in text  # crypto tắt → không hiện
