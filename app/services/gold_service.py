"""Logic giá vàng: parse giờ thông báo, giờ hiệu lực, format tin nhắn (thuần)."""
import re

_HHMM = re.compile(r"^(\d{1,2}):(\d{2})$")


def _fmt_vnd(n) -> str:
    try:
        return f"{float(n):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "—"


def parse_times(raw: str) -> list[str]:
    """Chuỗi giờ ('09:00, 16:00' / '9:00 16:00') → list 'HH:MM' chuẩn hoá, dedup, sort.

    Rỗng → []. Sai định dạng hoặc giờ/phút ngoài phạm vi → ValueError.
    """
    if not raw or not raw.strip():
        return []
    tokens = [t for t in re.split(r"[,\s]+", raw.strip()) if t]
    out = set()
    for tok in tokens:
        m = _HHMM.match(tok)
        if not m:
            raise ValueError(f"Giờ không hợp lệ: {tok} (dùng dạng HH:MM)")
        hh, mm = int(m.group(1)), int(m.group(2))
        if hh > 23 or mm > 59:
            raise ValueError(f"Giờ không hợp lệ: {tok}")
        out.add(f"{hh:02d}:{mm:02d}")
    return sorted(out)


def effective_times(user_times: list[str], sys_enabled: bool, sys_times: list[str]) -> list[str]:
    """Giờ thông báo hiệu lực: ưu tiên của user; trống thì theo hệ thống (nếu bật)."""
    if user_times:
        return list(user_times)
    return list(sys_times) if sys_enabled else []


# 3 loại vàng người dùng quan tâm nhất: (code, icon, nhãn thân thiện).
GOLD_DISPLAY: list[tuple[str, str, str]] = [
    ("SJC", "🟡", "Vàng miếng SJC"),
    ("N24K", "💍", "Nhẫn trơn PNJ 999.9"),
    ("24K", "📿", "Vàng nữ trang 999.9"),
]


def _card(icon: str, label: str, it: dict) -> list[str]:
    return [
        f"{icon} *{label}*",
        f"   Mua  `{_fmt_vnd(it.get('buy'))}`",
        f"   Bán  `{_fmt_vnd(it.get('sell'))}`",
    ]


def format_gold_prices(items: list[dict], when_str: str) -> str:
    """Bản tin giá vàng — thẻ theo loại (lọc 3 loại chính), đơn vị VND/chỉ.

    Nếu không tìm thấy code chuẩn nào → fallback hiện tối đa 3 loại đầu (dùng tên gốc).
    """
    by_code = {it.get("code"): it for it in items}
    blocks: list[list[str]] = []
    for code, icon, label in GOLD_DISPLAY:
        it = by_code.get(code)
        if it:
            blocks.append(_card(icon, label, it))
    if not blocks:  # nguồn đổi code → vẫn hiện được vài loại đầu
        for it in items[:3]:
            blocks.append(_card("🔸", it.get("name", "—"), it))

    lines = [f"🥇 *GIÁ VÀNG* · _{when_str}_", "━━━━━━━━━━━━━━━━━"]
    lines.append("\n\n".join("\n".join(b) for b in blocks))
    lines.append("━━━━━━━━━━━━━━━━━")
    lines.append("💡 _Đơn vị: VND/chỉ (1 lượng = 10 chỉ)_")
    return "\n".join(lines)
