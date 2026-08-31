"""Format bản tin crypto digest (thuần). Dùng cho worker báo giá theo giờ."""

_ICON = {
    "BTC": "₿", "ETH": "Ξ", "BNB": "🔶", "SOL": "◎",
    "XRP": "✕", "DOGE": "Ð", "ADA": "₳", "TON": "💎",
}


def _fmt_usd(v) -> str:
    if v is None:
        return "N/A"
    if v >= 1000:
        return f"${v:,.0f}"
    if v >= 1:
        return f"${v:,.2f}"
    return f"${v:,.4f}"


def resolve_notify(
    mode: str,
    user_times: list[str],
    user_coins: list[str],
    sys_enabled: bool,
    sys_times: list[str],
    sys_coins: list[str],
) -> tuple[list[str], list[str]]:
    """(times, coins) hiệu lực cho 1 user theo chế độ.

    off → không nhận; custom → dùng của user; system → dùng của hệ thống (nếu bật).
    """
    if mode == "off":
        return [], []
    if mode == "custom":
        return list(user_times), list(user_coins)
    # system
    if not sys_enabled:
        return [], []
    return list(sys_times), list(sys_coins)


def select_coins(all_coins: list[dict], wanted: list[str]) -> list[dict]:
    """Lọc theo ký hiệu. wanted rỗng = giữ tất cả."""
    if not wanted:
        return list(all_coins)
    want = {w.upper() for w in wanted}
    return [c for c in all_coins if c.get("symbol") in want]


def format_price_digest(coins: list[dict], when_str: str) -> str:
    """Bản tin giá crypto — mỗi đồng 1 dòng: icon, symbol, giá, %24h."""
    lines = [f"📈 *GIÁ CRYPTO* · _{when_str}_", "━━━━━━━━━━━━━"]
    for c in coins:
        pct = c.get("change_pct") or 0
        arrow = "🟢" if pct >= 0 else "🔴"
        icon = _ICON.get(c.get("symbol"), "🪙")
        lines.append(f"{icon} *{c.get('symbol')}*  `{_fmt_usd(c.get('price_usd'))}`  {arrow} {pct:+.2f}%")
    return "\n".join(lines)
