"""Unit test football_service: lọc theo đội + format KQ (thuần)."""
from app.services.football_service import filter_by_teams, format_results_digest

_MATCHES = [
    {"home": "Arsenal", "away": "Chelsea", "home_goals": 2, "away_goals": 1, "matchday": 8},
    {"home": "Liverpool", "away": "Everton", "home_goals": 3, "away_goals": 0, "matchday": 8},
]


def test_filter_empty_teams_returns_all():
    assert filter_by_teams(_MATCHES, []) == _MATCHES


def test_filter_by_team_substring_case_insensitive():
    got = filter_by_teams(_MATCHES, ["arsenal"])
    assert len(got) == 1 and got[0]["home"] == "Arsenal"


def test_filter_matches_away_side_too():
    got = filter_by_teams(_MATCHES, ["everton"])
    assert len(got) == 1 and got[0]["away"] == "Everton"


def test_format_digest_has_league_round_scores():
    sections = [{"label": "Ngoại hạng Anh", "matchday": 8, "matches": _MATCHES}]
    text = format_results_digest(sections, "09:30 29/08")
    assert "Ngoại hạng Anh" in text
    assert "Vòng 8" in text
    assert "2-1" in text and "3-0" in text
    assert "Arsenal" in text and "Liverpool" in text
    assert "09:30 29/08" in text


def test_format_digest_skips_empty_sections():
    sections = [
        {"label": "La Liga", "matchday": None, "matches": []},
        {"label": "Ngoại hạng Anh", "matchday": 8, "matches": _MATCHES},
    ]
    text = format_results_digest(sections, "x")
    assert "La Liga" not in text
    assert "Ngoại hạng Anh" in text
