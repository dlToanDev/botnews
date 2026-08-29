# Thiết kế: Sửa lịch trong /lich (đổi giờ + tiêu đề)

**Ngày:** 2026-08-29
**Nhánh:** feat/web-admin-redesign

## Mục tiêu
Trong lịch tương tác `/lich`, cho phép **sửa** một lịch: đổi **giờ** và/hoặc
**tiêu đề**. (Xóa đã có sẵn.)

## UX
Chi tiết ngày: mỗi việc hiện là nút xóa-ngay → đổi thành nút mở **menu hành động**:
- ✏️ Đổi giờ → lưới giờ (0–23) → phút (00/15/30/45) → lưu, về chi tiết ngày.
- ✏️ Đổi tiêu đề → bot hỏi, user gõ tiêu đề mới → lưu.
- 🗑️ Xóa (như cũ).
- ◀️ Quay lại chi tiết ngày.

## Kỹ thuật
### Repo — `schedule_repo.py`
`update(session, schedule_id, user_id, **fields) -> bool`: lấy theo id, chỉ sửa nếu
đúng chủ; gán fields; trả True/False.

### Service — `schedule_service.py`
- `update_time(telegram_id, schedule_id, new_start_local) -> bool` — lưu `start_time`
  (UTC) + đặt `is_notified=False` (để nhắc lại đúng giờ mới); ghi log.
- `update_title(telegram_id, schedule_id, title) -> bool` — lưu `title`; ghi log.

### Handlers — `calendar_ui.py`
- `_day_view`: nút mỗi việc đổi callback → `cal:ev:ID:Y:M:D`.
- `_event_menu(sch, y, m, d)` (view mới): text tóm tắt việc + 4 nút.
- Nhánh callback mới:
  - `cal:ev:ID:Y:M:D` → menu hành động.
  - `cal:eh:ID:Y:M:D` → lưới giờ (sửa).
  - `cal:emin:ID:Y:M:D:HH` → lưới phút (sửa).
  - `cal:eset:ID:Y:M:D:HH:MM` → `update_time`, về chi tiết ngày.
  - `cal:etitle:ID:Y:M:D` → set `context.user_data["cal_edit"]={"id":ID}`, hỏi tiêu đề mới.
- `cal_title_text`: xử lý cả `cal_await` (tạo mới) lẫn `cal_edit` (đổi tiêu đề).

## Xử lý lỗi
- Sửa không đúng chủ / không tồn tại → thông báo nhẹ, về chi tiết ngày.
- Callback hỏng → bỏ qua (như hiện tại).

## Kiểm thử
- Live smoke: thêm → đổi giờ → đổi tiêu đề → kiểm DB → xóa.
- Không có hạ tầng unit-test DB (nhất quán cách đã verify các phần DB trước).

## Ngoài phạm vi (YAGNI)
- Đổi ngày (chỉ giờ + tiêu đề); đổi số phút nhắc; sửa qua lệnh text.
