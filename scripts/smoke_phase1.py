"""Smoke test Phase 1 — kiểm thử services + logic reminder trực tiếp trên DB.

Chạy:
    docker run --rm --network botnews_default --env-file .env -v "$PWD":/code \
        botnews:dev python scripts/smoke_phase1.py
"""
import asyncio
from datetime import timedelta

TEST_TG_ID = 999_000_001


async def main() -> int:
    from sqlalchemy import delete as sa_delete
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.core.timeutils import now_local, now_utc
    from app.models.user import User
    from app.services import schedule_service, user_service

    failures: list[str] = []

    def check(name: str, cond: bool) -> None:
        print(f"[{'OK ' if cond else 'ERR'}] {name}")
        if not cond:
            failures.append(name)

    # --- dọn dữ liệu test cũ (nếu có) ---
    async with AsyncSessionLocal() as s:
        await s.execute(sa_delete(User).where(User.telegram_id == TEST_TG_ID))
        await s.commit()

    # 1) get_or_create_user
    user, created = await user_service.get_or_create_user(TEST_TG_ID, "tester", "Người Test")
    check("Tạo user mới", created and user.telegram_id == TEST_TG_ID)
    check("is_active mặc định = True", user_service.is_active(user))

    # gọi lại → không tạo trùng
    user2, created2 = await user_service.get_or_create_user(TEST_TG_ID)
    check("Gọi lại không tạo trùng (idempotent)", (not created2) and user2.id == user.id)

    # 2) parse input
    start_dt, title = schedule_service.parse_schedule_input("08:00 Đi làm")
    check("Parse 'HH:MM title'", title == "Đi làm" and start_dt.hour == 8)
    try:
        schedule_service.parse_schedule_input("linh tinh")
        check("Parse input sai phải raise", False)
    except schedule_service.ScheduleParseError:
        check("Parse input sai phải raise", True)

    # 3) thêm lịch: 1 lịch sắp tới (trong cửa sổ nhắc), 1 lịch xa
    soon_local = now_local() + timedelta(minutes=16)
    far_local = now_local() + timedelta(minutes=120)
    sch_soon = await schedule_service.add_schedule(TEST_TG_ID, "Lịch sắp tới", soon_local, reminder_minutes=30)
    sch_far = await schedule_service.add_schedule(TEST_TG_ID, "Lịch xa", far_local, reminder_minutes=30)
    check("Thêm được 2 lịch", bool(sch_soon.id) and bool(sch_far.id))

    # 4) list_all
    all_items = await schedule_service.list_all(TEST_TG_ID)
    check("list_all trả 2 lịch", len(all_items) == 2)

    # 5) collect_due_reminders: chỉ 'Lịch sắp tới' đến hạn nhắc
    async with AsyncSessionLocal() as s:
        due = await schedule_service.collect_due_reminders(s, now_utc())
    due_titles = {d.title for d in due if d.user_id == user.id}
    check("Reminder gồm 'Lịch sắp tới'", "Lịch sắp tới" in due_titles)
    check("Reminder KHÔNG gồm 'Lịch xa'", "Lịch xa" not in due_titles)

    # 6) delete
    ok = await schedule_service.delete_schedule(TEST_TG_ID, sch_far.id)
    remaining = await schedule_service.list_all(TEST_TG_ID)
    check("Xoá lịch OK", ok and len(remaining) == 1)

    # 7) log đã ghi (user_register + schedule_add ...)
    from app.models.log import Log
    async with AsyncSessionLocal() as s:
        logs = (await s.execute(select(Log).where(Log.user_id == user.id))).scalars().all()
    check("Có ghi log hoạt động", len(logs) >= 3)

    # --- dọn dữ liệu test ---
    async with AsyncSessionLocal() as s:
        await s.execute(sa_delete(User).where(User.telegram_id == TEST_TG_ID))
        await s.commit()
    print("[i] Đã dọn dữ liệu test.")

    print("\n=>", "TẤT CẢ OK ✅" if not failures else f"CÓ LỖI ❌ ({failures})")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
