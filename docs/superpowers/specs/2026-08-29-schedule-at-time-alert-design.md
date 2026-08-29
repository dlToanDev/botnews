# Thiết kế: Báo đúng giờ cho lịch cá nhân (kèm giữ nhắc trước)

**Ngày:** 2026-08-29
**Nhánh:** feat/web-admin-redesign

## Mục tiêu
Khi tới đúng giờ đã ghi (vd 16:00) → bot gửi tin "🔔 Đến giờ rồi! …".
Vẫn giữ nhắc trước 30' như hiện tại ("còn ~30 phút nữa").

## Cơ chế
Hai loại thông báo độc lập, mỗi loại 1 cờ chống lặp:
- Nhắc trước: cờ sẵn có `is_notified` (giữ nguyên).
- Báo đúng giờ: cờ mới `started_notified`.

### Model + migration
`Schedule` thêm `started_notified: bool = False`. Migration thêm cột
`started_notified BOOLEAN NOT NULL DEFAULT false` (down: drop).

### Repo — `schedule_repo.py`
`list_due_started(session, now, grace_minutes=15)`: lịch active,
`started_notified=False`, `now - grace < start_time <= now`.
Cửa sổ 15': không bỏ sót khi worker trễ; không bắn dồn lịch quá khứ khi deploy.

### Worker — `schedule_reminder.py`
Sau vòng nhắc-trước, thêm vòng báo-đúng-giờ:
- lấy `list_due_started(now)`, lọc user active,
- gửi `🔔 *Đến giờ rồi!*\n🕘 *HH:MM* — <title>[📍 location]`,
- đặt `started_notified=True`. Chạy mỗi phút (đã có) → sai số ≤1'.

### Sửa giờ — `schedule_service.update_time`
Reset **cả** `is_notified=False` và `started_notified=False` để giờ mới nhắc lại
+ báo đúng giờ đúng lúc mới.

## Kiểm thử
- Live smoke KHÔNG gửi: tạo lịch tại now / now+1h / now-30' → `list_due_started`
  chỉ chọn lịch tại now; `update_time` reset cả 2 cờ; dọn dẹp.
- Migration up/down.

## Ngoài phạm vi (YAGNI)
- Lặp nhiều lần / snooze / âm báo riêng.
