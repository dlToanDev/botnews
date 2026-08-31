"""Adapter Bóng đá — API-Football (api-sports.io). Cần API_FOOTBALL_KEY.

Các endpoint hỗ trợ:
  • get_fixtures(date)        — lịch/kết quả theo ngày   (/fixtures?date=)
  • get_live_fixtures()       — trận đang đá real-time    (/fixtures?live=all)
  • get_standings(league)     — bảng xếp hạng             (/standings)
  • get_team_fixtures(id)     — lịch của 1 đội            (/fixtures?team=&next/last=)
  • search_team(query)        — tra cứu tên + id đội      (/teams?search=)
"""
from app.core.config import settings
from app.core.timeutils import now_local
from app.integrations.base import BaseAdapter, http_get_json

API_BASE = "https://v3.football.api-sports.io"

# League id thường dùng (tham khảo cho lệnh /bxh).
POPULAR_LEAGUES: dict[int, str] = {
    39: "Ngoại hạng Anh",
    140: "La Liga",
    135: "Serie A",
    78: "Bundesliga",
    61: "Ligue 1",
    2: "Champions League",
    3: "Europa League",
    340: "V.League 1 (VN)",
}


class FootballConfigError(RuntimeError):
    """Chưa cấu hình API_FOOTBALL_KEY."""


def _headers() -> dict:
    return {"x-apisports-key": settings.API_FOOTBALL_KEY}


def _require_key() -> None:
    if not settings.API_FOOTBALL_KEY:
        raise FootballConfigError()


def current_season() -> int:
    """Mùa giải hiện tại theo chuẩn API-Football (năm bắt đầu mùa châu Âu)."""
    now = now_local()
    return now.year if now.month >= 7 else now.year - 1


def _parse_fixture(f: dict) -> dict:
    teams = f.get("teams", {})
    goals = f.get("goals", {})
    fx = f.get("fixture", {})
    status = fx.get("status", {})
    return {
        "id": fx.get("id"),
        "home": teams.get("home", {}).get("name"),
        "away": teams.get("away", {}).get("name"),
        "home_id": teams.get("home", {}).get("id"),
        "away_id": teams.get("away", {}).get("id"),
        "home_goals": goals.get("home"),
        "away_goals": goals.get("away"),
        "status": status.get("short"),
        "elapsed": status.get("elapsed"),
        "timestamp": fx.get("timestamp"),
        "league": f.get("league", {}).get("name"),
    }


# ---------------- Fixtures theo ngày ----------------

class FixturesAdapter(BaseAdapter):
    """Lấy các trận theo ngày (YYYY-MM-DD)."""

    ttl = 120

    def __init__(self, date_str: str):
        self.date_str = date_str
        self.name = f"football:fixtures:{date_str}"

    async def fetch(self):
        _require_key()
        data = await http_get_json(
            f"{API_BASE}/fixtures",
            params={"date": self.date_str},
            headers=_headers(),
        )
        return [_parse_fixture(f) for f in data.get("response", [])]


# ---------------- Live score ----------------

class LiveFixturesAdapter(BaseAdapter):
    """Toàn bộ trận đang diễn ra (/fixtures?live=all)."""

    name = "football:live"
    ttl = 45  # live cần tươi

    async def fetch(self):
        _require_key()
        data = await http_get_json(
            f"{API_BASE}/fixtures",
            params={"live": "all"},
            headers=_headers(),
        )
        return [_parse_fixture(f) for f in data.get("response", [])]


# ---------------- Bảng xếp hạng ----------------

class StandingsAdapter(BaseAdapter):
    """BXH 1 giải theo mùa → {league, table[]}."""

    ttl = 900  # 15 phút

    def __init__(self, league: int, season: int):
        self.league = int(league)
        self.season = int(season)
        self.name = f"football:standings:{self.league}:{self.season}"

    async def fetch(self):
        _require_key()
        data = await http_get_json(
            f"{API_BASE}/standings",
            params={"league": self.league, "season": self.season},
            headers=_headers(),
        )
        resp = data.get("response", [])
        if not resp:
            return {"league": None, "table": []}
        lg = resp[0].get("league", {})
        groups = lg.get("standings", [])
        table = []
        for row in (groups[0] if groups else []):
            team = row.get("team", {})
            allst = row.get("all", {})
            table.append(
                {
                    "rank": row.get("rank"),
                    "team": team.get("name"),
                    "played": allst.get("played"),
                    "win": allst.get("win"),
                    "draw": allst.get("draw"),
                    "lose": allst.get("lose"),
                    "goals_diff": row.get("goalsDiff"),
                    "points": row.get("points"),
                }
            )
        return {"league": lg.get("name"), "table": table}


# ---------------- Lịch theo đội ----------------

class TeamFixturesAdapter(BaseAdapter):
    """`upcoming=True` → n trận sắp tới; False → n trận gần nhất."""

    ttl = 300  # 5 phút

    def __init__(self, team_id: int, upcoming: bool = True, count: int = 5):
        self.team_id = int(team_id)
        self.upcoming = upcoming
        self.count = count
        kind = "next" if upcoming else "last"
        self.name = f"football:team:{self.team_id}:{kind}:{count}"

    async def fetch(self):
        _require_key()
        param = "next" if self.upcoming else "last"
        data = await http_get_json(
            f"{API_BASE}/fixtures",
            params={"team": self.team_id, param: self.count},
            headers=_headers(),
        )
        return [_parse_fixture(f) for f in data.get("response", [])]


# ---------------- Tra cứu đội ----------------

class TeamSearchAdapter(BaseAdapter):
    """Tìm đội theo tên → list {id, name, country, logo}."""

    ttl = 86400  # 1 ngày (danh mục đội ít đổi)

    def __init__(self, query: str):
        self.query = query.strip()
        self.name = f"football:search:{self.query.lower()}"

    async def fetch(self):
        _require_key()
        data = await http_get_json(
            f"{API_BASE}/teams",
            params={"search": self.query},
            headers=_headers(),
        )
        out = []
        for it in data.get("response", []):
            team = it.get("team", {})
            out.append(
                {
                    "id": team.get("id"),
                    "name": team.get("name"),
                    "country": team.get("country"),
                    "logo": team.get("logo"),
                }
            )
        return out


# ---------------- Public API ----------------

async def get_fixtures(date_str: str) -> list[dict]:
    return await FixturesAdapter(date_str).get()


async def get_live_fixtures() -> list[dict]:
    return await LiveFixturesAdapter().get()


async def get_standings(league: int, season: int | None = None) -> dict:
    return await StandingsAdapter(league, season or current_season()).get()


async def get_team_fixtures(team_id: int, upcoming: bool = True, count: int = 5) -> list[dict]:
    return await TeamFixturesAdapter(team_id, upcoming, count).get()


async def search_team(query: str) -> list[dict]:
    return await TeamSearchAdapter(query).get()


def is_configured() -> bool:
    return bool(settings.API_FOOTBALL_KEY)
