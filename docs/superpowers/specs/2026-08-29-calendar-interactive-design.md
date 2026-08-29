# Thiết kế: Lịch cá nhân — parser DD/MM/YYYY + lệnh /lich (calendar tương tác)

**Ngày:** 2026-08-29
**Nhánh:** feat/web-admin-redesign

## Mục tiêu

1. `/themlich` (add): không ghi ngày → mặc định **hôm nay** (đã có sẵn). Bổ sung
   định dạng **DD/MM/YYYY**: `/themlich 30/08/2026 08:00 thức dậy`.
2. Lệnh mới **`/lich`**: hiện lịch tháng tương tác (inline keyboard).
   - Ngày có lịch tô khác (🔴), hôm nay 🔘.
   - Bấm ngày **có lịch** → sửa tin nhắn tại chỗ, hiện chi tiết ngày (giờ + việc, nút xoá).
   - Bấm ngày **chưa có lịch** → chọn **giờ** (nút) → **phút** (00/15/30/45) → gõ tiêu đề → tạo.
   - ◀️ ▶️ đổi tháng.

## Kiến trúc

### 1. Parser — `app/services/schedule_service.py`
Thêm regex `_DATE_DMY = ^(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2})\s+(.+)$`,
kiểm tra **trước** `_DATE_DM`. Năm lấy tường minh (không rollover). Cập nhật text
hướng dẫn `/themlich` (thêm ví dụ DD/MM/YYYY).

### 2. Timeutils — `app/core/timeutils.py`
Thêm `local_month_bounds_utc(year, month) -> (utc_start, utc_end)`: đầu tháng →
đầu tháng sau (giờ VN) quy đổi UTC. Dùng để query cả tháng.

### 3. Service — thêm hàm (mở session riêng, theo telegram_id)
- `month_event_days(telegram_id, year, month) -> set[int]` — ngày (local) có lịch.
- `day_events(telegram_id, year, month, day) -> list[Schedule]`.
- Tái dùng `add_schedule`, `delete_schedule` sẵn có.

### 4. Hàm thuần dựng lưới — `app/bot/handlers/calendar_ui.py`
`build_month_grid(year, month, event_days: set[int], today_day: int | None) -> list[list[dict]]`
dùng `calendar.Calendar(firstweekday=0).monthdayscalendar`. Mỗi ô:
`{"day": int, "has_event": bool, "is_today": bool}` (day=0 = ô trống). Test được.

### 5. Handler tương tác — `app/bot/handlers/calendar_ui.py`
- `cal_cmd` (`@require_active`): dựng view tháng hiện tại, `reply_text(reply_markup=...)`.
- `cal_callback` (`CallbackQueryHandler pattern="^cal:"`): guard active thủ công
  (`get_or_create_user` + `is_active`; chặn thì `query.answer(alert)`), rồi phân nhánh:
  - `cal:nop` → answer, bỏ qua (ô trống / nhãn).
  - `cal:nav:Y:M` → edit sang view tháng (kèm chặn lùi quá khứ xa: cho tự do, YAGNI).
  - `cal:day:Y:M:D` → edit sang chi tiết ngày. Ngày trống → vào thẳng lưới giờ.
  - `cal:add:Y:M:D` → lưới giờ (0–23).
  - `cal:hour:Y:M:D:HH` → lưới phút (00/15/30/45).
  - `cal:time:Y:M:D:HH:MM` → `context.user_data["cal_await"] = "<iso_local>"`,
    edit "✍️ Gõ tiêu đề cho lịch HH:MM DD/MM/YYYY".
  - `cal:del:ID:Y:M:D` → `delete_schedule`, re-render chi tiết ngày.
  - `cal:back:Y:M` → view tháng.
- `cal_title_text` (MessageHandler text, không lệnh): nếu có `cal_await` → tạo lịch
  với datetime đã lưu + text làm title, xoá cờ, gửi xác nhận + gợi ý `/lich`. Không
  có cờ → im lặng (return).

**Nhãn nút ngày:** `str(day)` + hậu tố `🔴` nếu có lịch, `🔘` nếu hôm nay (ưu tiên 🔴).
Ô trống → `" "` callback `cal:nop`.

### 6. Đăng ký — `app/bot/main.py`
- `VI_ALIAS["calendar"] = "lich"`; menu item `("calendar", "🗓️ Lịch (calendar)")`.
- `CommandHandler(_cmd("calendar"), calendar_ui.cal_cmd)`.
- `CallbackQueryHandler(calendar_ui.cal_callback, pattern=r"^cal:")`.
- `MessageHandler(filters.TEXT & ~filters.COMMAND, calendar_ui.cal_title_text)` đăng ký
  **sau** menu_text (cùng group 0 → menu button vào menu_text trước, text tự do rơi
  xuống cal_title_text). Nút Reply "➕ Thêm lịch" trỏ hướng dẫn sang `/lich`.

## Trạng thái
Không dùng ConversationHandler. State bước "gõ tiêu đề" lưu ở `context.user_data["cal_await"]`
(chuỗi ISO local). Điều hướng tháng/ngày xoá `cal_await` để tránh dùng nhầm giờ cũ.

## Xử lý lỗi
- Callback data hỏng → `query.answer()` + bỏ qua.
- Title rỗng/space → nhắc gõ lại, giữ `cal_await`.
- Xoá không đúng chủ → thông báo, re-render.

## Kiểm thử
- Parser DD/MM/YYYY (+ giờ/phút biên) — thêm vào `test_schedule_parse.py`.
- `local_month_bounds_utc` (đầu/cuối tháng, cả tháng 12).
- `build_month_grid`: số tuần/ô đúng, đánh dấu has_event & is_today đúng, ô trống=0.
- Parse callback data `cal:*` đúng thành phần.

## Ngoài phạm vi (YAGNI)
- Lịch lặp (recurrence), sửa (edit) lịch — chỉ thêm/xoá.
- Chọn phút tự do ngoài 00/15/30/45.
- Đổi reminder_minutes qua UI (giữ mặc định 30).
