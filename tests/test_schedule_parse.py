"""Unit test cho parser lịch (thuần logic, không cần DB)."""
from datetime import timedelta

import pytest

from app.core.timeutils import now_local
from app.services.schedule_service import ScheduleParseError, parse_schedule_input


def test_time_only():
    start, title = parse_schedule_input("08:00 Đi làm")
    assert title == "Đi làm"
    assert start.hour == 8 and start.minute == 0


def test_time_only_past_rolls_to_tomorrow():
    past = (now_local() - timedelta(hours=2)).strftime("%H:%M")
    start, _ = parse_schedule_input(f"{past} Việc")
    assert start > now_local()


def test_date_dm():
    start, title = parse_schedule_input("26/12 14:30 Họp team")
    assert (start.month, start.day, start.hour, start.minute) == (12, 26, 14, 30)
    assert title == "Họp team"


def test_date_iso():
    start, title = parse_schedule_input("2030-01-15 09:00 Khám sức khỏe")
    assert (start.year, start.month, start.day) == (2030, 1, 15)
    assert title == "Khám sức khỏe"


def test_invalid_raises():
    with pytest.raises(ScheduleParseError):
        parse_schedule_input("blah blah")
