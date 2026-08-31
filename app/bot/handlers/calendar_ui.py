"""Lịch tháng tương tác (/lich) — inline keyboard, sửa tin nhắn tại chỗ."""
import calendar as _cal
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.bot.decorators import require_active
from app.core.timeutils import LOCAL_TZ, now_local, to_local
from app.services import schedule_service
from app.services.user_service import get_or_create_user, is_active

_WEEKDAY_LABELS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]


# ---------------- Hàm thuần (test được) ----------------

def build_month_grid(
    year: int, month: int, event_days: set[int], today_day: int | None
) -> list[list[dict]]:
    """Lưới tháng: list tuần, mỗi tuần 7 ô {day, has_event, is_today}. day=0 = ô trống."""
    weeks = _cal.Calendar(firstweekday=0).monthdayscalendar(year, month)
    grid = []
    for wk in weeks:
        row = []
        for d in wk:
            row.append(
                {
                    "day": d,
                    "has_event": bool(d) and d in event_days,
                    "is_today": bool(d) and d == today_day,
                }
            )
        grid.append(row)
    return grid


# ---------------- Dựng bàn phím ----------------

def _month_text(year: int, month: int) -> str:
    return (
        f"📅 *Lịch tháng {month}/{year}*\n"
        "🔴 = có lịch · 🔘 = hôm nay\n"
        "_Bấm 1 ngày để xem / thêm lịch._"
    )


def _month_markup(year: int, month: int, event_days: set[int], today_day: int | None):
    grid = build_month_grid(year, month, event_days, today_day)
    rows = [[InlineKeyboardButton(w, callback_data="cal:nop") for w in _WEEKDAY_LABELS]]
    for week in grid:
        r = []
        for c in week:
            if not c["day"]:
                r.append(InlineKeyboardButton(" ", callback_data="cal:nop"))
                continue
            label = str(c["day"])
            if c["has_event"]:
                label += "🔴"
            elif c["is_today"]:
                label += "🔘"
            r.append(InlineKeyboardButton(label, callback_data=f"cal:day:{year}:{month}:{c['day']}"))
        rows.append(r)
    py, pm = (year - 1, 12) if month == 1 else (year, month - 1)
    ny, nm = (year + 1, 1) if month == 12 else (year, month + 1)
    rows.append(
        [
            InlineKeyboardButton("◀️", callback_data=f"cal:nav:{py}:{pm}"),
            InlineKeyboardButton(f"Tháng {month}/{year}", callback_data="cal:nop"),
            InlineKeyboardButton("▶️", callback_data=f"cal:nav:{ny}:{nm}"),
        ]
    )
    return InlineKeyboardMarkup(rows)


def _hours_view(year: int, month: int, day: int):
    text = f"🕐 Chọn *giờ* cho ngày {day:02d}/{month:02d}/{year}"
    rows = []
    for h0 in range(0, 24, 6):
        rows.append(
            [
                InlineKeyboardButton(f"{h:02d}h", callback_data=f"cal:hour:{year}:{month}:{day}:{h}")
                for h in range(h0, h0 + 6)
            ]
        )
    rows.append([InlineKeyboardButton("◀️ Lịch", callback_data=f"cal:back:{year}:{month}")])
    return text, InlineKeyboardMarkup(rows)


def _minutes_view(year: int, month: int, day: int, hour: int):
    text = f"🕐 {hour:02d}:__ — chọn *phút* ({day:02d}/{month:02d}/{year})"
    rows = [
        [
            InlineKeyboardButton(
                f"{hour:02d}:{mi:02d}", callback_data=f"cal:time:{year}:{month}:{day}:{hour}:{mi}"
            )
            for mi in (0, 15, 30, 45)
        ],
        [InlineKeyboardButton("◀️ Chọn giờ", callback_data=f"cal:add:{year}:{month}:{day}")],
    ]
    return text, InlineKeyboardMarkup(rows)


# ---------------- Render có DB ----------------

async def _month_view(tid: int, year: int, month: int):
    event_days = await schedule_service.month_event_days(tid, year, month)
    now = now_local()
    today_day = now.day if (now.year == year and now.month == month) else None
    return _month_text(year, month), _month_markup(year, month, event_days, today_day)


async def _day_view(tid: int, year: int, month: int, day: int):
    events = await schedule_service.day_events(tid, year, month, day)
    if not events:  # ngày trống → vào thẳng chọn giờ
        return _hours_view(year, month, day)
    text = f"📅 *{day:02d}/{month:02d}/{year}* — {len(events)} lịch\n_Bấm 1 việc để sửa / xóa._"
    rows = []
    for s in events:
        t = to_local(s.start_time).strftime("%H:%M")
        rows.append(
            [InlineKeyboardButton(
                f"🕘 {t} · {s.title[:30]}", callback_data=f"cal:ev:{s.id}:{year}:{month}:{day}"
            )]
        )
    rows.append(
        [
            InlineKeyboardButton("➕ Thêm", callback_data=f"cal:add:{year}:{month}:{day}"),
            InlineKeyboardButton("◀️ Lịch", callback_data=f"cal:back:{year}:{month}"),
        ]
    )
    return text, InlineKeyboardMarkup(rows)


def _event_menu(sch, year: int, month: int, day: int):
    """Menu hành động cho 1 việc: đổi giờ / đổi tiêu đề / xóa."""
    t = to_local(sch.start_time).strftime("%H:%M")
    text = f"📅 *{day:02d}/{month:02d}/{year}*\n🕘 *{t}* — {sch.title}\n\n_Chọn thao tác:_"
    rows = [
        [
            InlineKeyboardButton("✏️ Đổi giờ", callback_data=f"cal:eh:{sch.id}:{year}:{month}:{day}"),
            InlineKeyboardButton("✏️ Đổi tiêu đề", callback_data=f"cal:etitle:{sch.id}:{year}:{month}:{day}"),
        ],
        [
            InlineKeyboardButton("🗑️ Xóa", callback_data=f"cal:del:{sch.id}:{year}:{month}:{day}"),
            InlineKeyboardButton("◀️ Quay lại", callback_data=f"cal:day:{year}:{month}:{day}"),
        ],
    ]
    return text, InlineKeyboardMarkup(rows)


def _edit_hours_view(sid: int, year: int, month: int, day: int):
    text = f"✏️ Chọn *giờ mới* ({day:02d}/{month:02d}/{year})"
    rows = []
    for h0 in range(0, 24, 6):
        rows.append(
            [
                InlineKeyboardButton(f"{h:02d}h", callback_data=f"cal:emin:{sid}:{year}:{month}:{day}:{h}")
                for h in range(h0, h0 + 6)
            ]
        )
    rows.append([InlineKeyboardButton("◀️ Quay lại", callback_data=f"cal:ev:{sid}:{year}:{month}:{day}")])
    return text, InlineKeyboardMarkup(rows)


def _edit_minutes_view(sid: int, year: int, month: int, day: int, hour: int):
    text = f"✏️ {hour:02d}:__ — chọn *phút mới*"
    rows = [
        [
            InlineKeyboardButton(
                f"{hour:02d}:{mi:02d}",
                callback_data=f"cal:eset:{sid}:{year}:{month}:{day}:{hour}:{mi}",
            )
            for mi in (0, 15, 30, 45)
        ],
        [InlineKeyboardButton("◀️ Chọn giờ", callback_data=f"cal:eh:{sid}:{year}:{month}:{day}")],
    ]
    return text, InlineKeyboardMarkup(rows)


async def _event_menu_view(tid: int, sid: int, year: int, month: int, day: int):
    """Tìm việc trong ngày theo id rồi dựng menu. Không thấy → về chi tiết ngày."""
    for s in await schedule_service.day_events(tid, year, month, day):
        if s.id == sid:
            return _event_menu(s, year, month, day)
    return await _day_view(tid, year, month, day)


# ---------------- Handlers ----------------

@require_active
async def cal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tid = update.effective_user.id
    now = now_local()
    text, markup = await _month_view(tid, now.year, now.month)
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)


async def cal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    tg = update.effective_user
    user, _ = await get_or_create_user(tg.id, tg.username, tg.full_name)
    if user.status == "banned" or not is_active(user):
        await query.answer("⛔ Tài khoản không hợp lệ hoặc đã hết hạn.", show_alert=True)
        return
    await query.answer()

    parts = query.data.split(":")
    action = parts[1] if len(parts) > 1 else "nop"
    tid = tg.id
    try:
        if action == "nop":
            return
        if action in ("nav", "back"):
            y, m = int(parts[2]), int(parts[3])
            context.user_data.pop("cal_await", None)
            text, markup = await _month_view(tid, y, m)
        elif action == "day":
            y, m, d = int(parts[2]), int(parts[3]), int(parts[4])
            context.user_data.pop("cal_await", None)
            text, markup = await _day_view(tid, y, m, d)
        elif action == "add":
            y, m, d = int(parts[2]), int(parts[3]), int(parts[4])
            text, markup = _hours_view(y, m, d)
        elif action == "hour":
            y, m, d, h = (int(parts[i]) for i in range(2, 6))
            text, markup = _minutes_view(y, m, d, h)
        elif action == "time":
            y, m, d, h, mi = (int(parts[i]) for i in range(2, 7))
            dt = datetime(y, m, d, h, mi, tzinfo=LOCAL_TZ)
            context.user_data["cal_await"] = dt.isoformat()
            text = (
                f"✍️ Gõ *tiêu đề* cho lịch lúc {h:02d}:{mi:02d} ngày {d:02d}/{m:02d}/{y}\n"
                "_(gửi 1 tin nhắn)_"
            )
            markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton("◀️ Huỷ", callback_data=f"cal:back:{y}:{m}")]]
            )
        elif action == "del":
            sid = int(parts[2])
            y, m, d = int(parts[3]), int(parts[4]), int(parts[5])
            await schedule_service.delete_schedule(tid, sid)
            text, markup = await _day_view(tid, y, m, d)
        elif action == "ev":  # mở menu hành động của 1 việc
            sid = int(parts[2])
            y, m, d = int(parts[3]), int(parts[4]), int(parts[5])
            context.user_data.pop("cal_await", None)
            context.user_data.pop("cal_edit", None)
            text, markup = await _event_menu_view(tid, sid, y, m, d)
        elif action == "eh":  # đổi giờ → lưới giờ
            sid = int(parts[2])
            y, m, d = int(parts[3]), int(parts[4]), int(parts[5])
            text, markup = _edit_hours_view(sid, y, m, d)
        elif action == "emin":  # đổi giờ → lưới phút
            sid = int(parts[2])
            y, m, d, h = (int(parts[i]) for i in range(3, 7))
            text, markup = _edit_minutes_view(sid, y, m, d, h)
        elif action == "eset":  # lưu giờ mới
            sid = int(parts[2])
            y, m, d, h, mi = (int(parts[i]) for i in range(3, 8))
            await schedule_service.update_time(tid, sid, datetime(y, m, d, h, mi, tzinfo=LOCAL_TZ))
            text, markup = await _day_view(tid, y, m, d)
        elif action == "etitle":  # chờ tiêu đề mới
            sid = int(parts[2])
            y, m, d = int(parts[3]), int(parts[4]), int(parts[5])
            context.user_data["cal_edit"] = {"id": sid, "y": y, "m": m, "d": d}
            text = "✍️ Gõ *tiêu đề mới* (gửi 1 tin nhắn)"
            markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton("◀️ Huỷ", callback_data=f"cal:ev:{sid}:{y}:{m}:{d}")]]
            )
        else:
            return
    except (ValueError, IndexError):
        return
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)


async def cal_title_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Nhận tiêu đề qua /lich: tạo mới (cal_await) hoặc đổi tiêu đề (cal_edit). Không chờ → im lặng."""
    iso = context.user_data.get("cal_await")
    edit = context.user_data.get("cal_edit")
    if not iso and not edit:
        return
    title = (update.message.text or "").strip()
    if not title:
        await update.message.reply_text("✍️ Tiêu đề trống, gõ lại giúp mình.")
        return
    tid = update.effective_user.id

    if edit:  # đổi tiêu đề việc đã có
        context.user_data.pop("cal_edit", None)
        ok = await schedule_service.update_title(tid, edit["id"], title)
        await update.message.reply_text(
            "✅ Đã đổi tiêu đề.  Xem: /lich" if ok else "❌ Không sửa được (lịch không tồn tại?).",
        )
        return

    # tạo mới
    context.user_data.pop("cal_await", None)
    start_local = datetime.fromisoformat(iso)
    sch = await schedule_service.add_schedule(tid, title=title, start_local=start_local)
    await update.message.reply_text(
        f"✅ Đã thêm lịch:\n{schedule_service.format_schedule_line(sch)}\n"
        f"🔔 Nhắc trước {sch.reminder_minutes} phút.  Xem: /lich",
        parse_mode=ParseMode.MARKDOWN,
    )
