"""Adapter football-data.org — BXH & kết quả MÙA HIỆN TẠI (gói Free).

Bổ khuyết cho api-sports (gói Free của api-sports không cho truy cập mùa hiện
tại). Dùng cho các lệnh tắt theo giải: /epl, /bxhepl, /laliga, ...

  • get_standings(code)  — bảng xếp hạng      (/competitions/{code}/standings)
  • get_recent_results(code) — kết quả vòng gần nhất (/competitions/{code}/matches?status=FINISHED)

Cần FOOTBALL_DATA_KEY (đăng ký free tại football-data.org). Gửi qua header
X-Auth-Token. Free: 10 request/phút, 12 giải top.
"""
from app.core.config import settings
from app.integrations.base import BaseAdapter, http_get_json

API_BASE = "https://api.football-data.org/v4"

# Mã giải football-data.org ↔ tên tiếng Việt (chỉ các giải mở trên gói Free).
COMPETITIONS: dict[str, str] = {
    "PL": "Ngoại hạng Anh",
    "PD": "La Liga",
    "SA": "Serie A",
    "BL1": "Bundesliga",
    "FL1": "Ligue 1",
    "CL": "Champions League",
}


class FootballDataConfigError(RuntimeError):
    """Chưa cấu hình FOOTBALL_DATA_KEY."""


def _headers() -> dict:
    return {"X-Auth-Token": settings.FOOTBALL_DATA_KEY or ""}


def _require_key() -> None:
    if not settings.FOOTBALL_DATA_KEY:
        raise FootballDataConfigError()


def is_configured() -> bool:
    return bool(settings.FOOTBALL_DATA_KEY)


def _team_name(t: dict) -> str | None:
    return t.get("shortName") or t.get("name") or t.get("tla")


def _parse_match(m: dict) -> dict:
    ft = m.get("score", {}).get("fullTime", {})
    return {
        "home": _team_name(m.get("homeTeam", {})),
        "away": _team_name(m.get("awayTeam", {})),
        "home_goals": ft.get("home"),
        "away_goals": ft.get("away"),
        "status": m.get("status"),
        "matchday": m.get("matchday"),
        "utc": m.get("utcDate"),
    }


# ---------------- Bảng xếp hạng ----------------

class StandingsAdapter(BaseAdapter):
    """BXH 1 giải mùa hiện tại → {league, table[]}."""

    ttl = 900  # 15 phút

    def __init__(self, code: str):
        self.code = code.upper()
        self.name = f"footballdata:standings:{self.code}"

    async def fetch(self):
        _require_key()
        data = await http_get_json(
            f"{API_BASE}/competitions/{self.code}/standings",
            headers=_headers(),
            timeout=12.0,
        )
        league = data.get("competition", {}).get("name")
        # Lấy bảng TOTAL (không phải sân nhà/khách) của giai đoạn vòng tròn.
        table_rows: list[dict] = []
        for grp in data.get("standings", []):
            if grp.get("type") == "TOTAL":
                table_rows = grp.get("table", [])
                break
        table = [
            {
                "rank": r.get("position"),
                "team": _team_name(r.get("team", {})),
                "played": r.get("playedGames"),
                "win": r.get("won"),
                "draw": r.get("draw"),
                "lose": r.get("lost"),
                "goals_diff": r.get("goalDifference"),
                "points": r.get("points"),
            }
            for r in table_rows
        ]
        return {"league": league, "table": table}


# ---------------- Kết quả vòng gần nhất ----------------

class RecentResultsAdapter(BaseAdapter):
    """Các trận đã đá; handler tự lọc ra vòng (matchday) mới nhất."""

    ttl = 300  # 5 phút

    def __init__(self, code: str):
        self.code = code.upper()
        self.name = f"footballdata:results:{self.code}"

    async def fetch(self):
        _require_key()
        data = await http_get_json(
            f"{API_BASE}/competitions/{self.code}/matches",
            params={"status": "FINISHED"},
            headers=_headers(),
            timeout=12.0,
        )
        return [_parse_match(m) for m in data.get("matches", [])]


# ---------------- Public API ----------------

async def get_standings(code: str) -> dict:
    return await StandingsAdapter(code).get()


async def get_recent_results(code: str) -> dict:
    """Trả {matchday, matches[]} của vòng đã đá gần nhất; matches rỗng nếu chưa có."""
    matches = await RecentResultsAdapter(code).get()
    if not matches:
        return {"matchday": None, "matches": []}
    latest = max(m["matchday"] for m in matches if m.get("matchday") is not None)
    rows = [m for m in matches if m.get("matchday") == latest]
    rows.sort(key=lambda m: m.get("utc") or "")
    return {"matchday": latest, "matches": rows}
