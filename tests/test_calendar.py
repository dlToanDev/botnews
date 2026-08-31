"""Unit test lịch tương tác: month bounds + dựng lưới tháng (thuần, không cần DB/Telegram)."""
from app.bot.handlers.calendar_ui import build_month_grid
from app.core.timeutils import local_month_bounds_utc


# ---------------- local_month_bounds_utc (VN = UTC+7) ----------------

def test_month_bounds_august():
    start, end = local_month_bounds_utc(2026, 8)
    # 2026-08-01 00:00 +07 == 2026-07-31 17:00 UTC
    assert (start.year, start.month, start.day, start.hour) == (2026, 7, 31, 17)
    # 2026-09-01 00:00 +07 == 2026-08-31 17:00 UTC
    assert (end.year, end.month, end.day, end.hour) == (2026, 8, 31, 17)
    assert (end - start).days == 31


def test_month_bounds_december_rolls_year():
    start, end = local_month_bounds_utc(2026, 12)
    assert (start.year, start.month, start.day, start.hour) == (2026, 11, 30, 17)
    # đầu tháng 1/2027 (+07) == 2026-12-31 17:00 UTC
    assert (end.year, end.month, end.day, end.hour) == (2026, 12, 31, 17)


# ---------------- build_month_grid ----------------

def _cell(grid, day):
    for week in grid:
        for c in week:
            if c["day"] == day:
                return c
    raise AssertionError(f"không thấy ngày {day}")


def test_grid_covers_all_days_of_august_2026():
    grid = build_month_grid(2026, 8, set(), None)
    days = sorted(c["day"] for week in grid for c in week if c["day"])
    assert days == list(range(1, 32))          # đủ 1..31
    assert all(len(week) == 7 for week in grid)  # mỗi tuần 7 ô


def test_grid_marks_event_days_and_today():
    grid = build_month_grid(2026, 8, {8, 28}, 27)
    assert _cell(grid, 8)["has_event"] is True
    assert _cell(grid, 28)["has_event"] is True
    assert _cell(grid, 9)["has_event"] is False
    assert _cell(grid, 27)["is_today"] is True
    assert _cell(grid, 8)["is_today"] is False


def test_grid_padding_cells_are_zero():
    grid = build_month_grid(2026, 8, set(), None)
    # ô đệm (không thuộc tháng) có day == 0
    assert any(c["day"] == 0 for week in grid for c in week)
