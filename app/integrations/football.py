"""Adapter Bóng đá — API-Football (api-sports.io). Cần API_FOOTBALL_KEY."""
from app.core.config import settings
from app.integrations.base import BaseAdapter, http_get_json

API_BASE = "https://v3.football.api-sports.io"


class FootballConfigError(RuntimeError):
    """Chưa cấu hình API_FOOTBALL_KEY."""


class FixturesAdapter(BaseAdapter):
    """Lấy các trận theo ngày (YYYY-MM-DD)."""

    ttl = 120

    def __init__(self, date_str: str):
        self.date_str = date_str
        self.name = f"football:fixtures:{date_str}"

    async def fetch(self):
        if not settings.API_FOOTBALL_KEY:
            raise FootballConfigError()
        data = await http_get_json(
            f"{API_BASE}/fixtures",
            params={"date": self.date_str},
            headers={"x-apisports-key": settings.API_FOOTBALL_KEY},
        )
        out = []
        for f in data.get("response", []):
            teams = f.get("teams", {})
            goals = f.get("goals", {})
            out.append(
                {
                    "home": teams.get("home", {}).get("name"),
                    "away": teams.get("away", {}).get("name"),
                    "home_goals": goals.get("home"),
                    "away_goals": goals.get("away"),
                    "status": f.get("fixture", {}).get("status", {}).get("short"),
                    "league": f.get("league", {}).get("name"),
                }
            )
        return out


async def get_fixtures(date_str: str) -> list[dict]:
    return await FixturesAdapter(date_str).get()


def is_configured() -> bool:
    return bool(settings.API_FOOTBALL_KEY)
