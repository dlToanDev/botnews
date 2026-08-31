"""Logic báo kết quả bóng đá: lọc theo đội + format tin (thuần)."""


def filter_by_teams(matches: list[dict], teams: list[str]) -> list[dict]:
    """teams rỗng → tất cả; có → giữ trận có home/away chứa tên đội (không phân biệt hoa/thường)."""
    if not teams:
        return list(matches)
    wants = [t.lower() for t in teams if t.strip()]
    out = []
    for m in matches:
        hay = f"{m.get('home') or ''} {m.get('away') or ''}".lower()
        if any(w in hay for w in wants):
            out.append(m)
    return out


def _score(m: dict) -> str:
    if m.get("home_goals") is None:
        return "vs"
    return f"{m['home_goals']}-{m['away_goals']}"


def _results_block(matches: list[dict]) -> str:
    rows = []
    for m in matches:
        home = (m.get("home") or "")[:14]
        away = (m.get("away") or "")[:14]
        rows.append(f"{home:>14} {_score(m):^5} {away}")
    return "```\n" + "\n".join(rows) + "\n```"


def format_results_digest(sections: list[dict], when_str: str) -> str:
    """sections = [{label, matchday, matches}]. Bỏ giải không có trận."""
    lines = [f"⚽ *KẾT QUẢ BÓNG ĐÁ* · _{when_str}_"]
    for sec in sections:
        matches = sec.get("matches") or []
        if not matches:
            continue
        md = sec.get("matchday")
        title = f"🏆 *{sec.get('label')}*"
        if md:
            title += f" — _Vòng {md}_"
        lines.append(title)
        lines.append(_results_block(matches))
    return "\n".join(lines)
