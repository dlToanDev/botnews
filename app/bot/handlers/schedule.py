"""Handlers: quản lý lịch cá nhân."""
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.bot.decorators import require_active
from app.services import schedule_service
from app.services.schedule_service import ScheduleParseError, format_schedule_line


@require_active
async def add_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    raw = update.message.text.partition(" ")[2].strip()  # bỏ phần "/addschedule"
    if not raw:
        await update.message.reply_text(
            "✍️ Cú pháp:\n"
            "`/addschedule 08:00 Đi làm`\n"
            "`/addschedule 26/08 14:30 Họp team`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    try:
        start_local, title = schedule_service.parse_schedule_input(raw)
    except ScheduleParseError as e:
        await update.message.reply_text(f"⚠️ {e}", parse_mode=ParseMode.MARKDOWN)
        return

    sch = await schedule_service.add_schedule(
        update.effective_user.id, title=title, start_local=start_local
    )
    await update.message.reply_text(
        f"✅ Đã thêm lịch:\n{format_schedule_line(sch)}\n"
        f"🔔 Nhắc trước {sch.reminder_minutes} phút.",
        parse_mode=ParseMode.MARKDOWN,
    )


@require_active
async def today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    items = await schedule_service.list_today(update.effective_user.id)
    if not items:
        await update.message.reply_text("📭 Hôm nay bạn chưa có lịch nào.")
        return
    body = "\n".join(format_schedule_line(s) for s in items)
    await update.message.reply_text(
        f"*📅 Lịch hôm nay ({len(items)}):*\n{body}", parse_mode=ParseMode.MARKDOWN
    )


@require_active
async def mylist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    items = await schedule_service.list_all(update.effective_user.id)
    if not items:
        await update.message.reply_text("📭 Bạn chưa có lịch nào.")
        return
    body = "\n".join(format_schedule_line(s) for s in items)
    await update.message.reply_text(
        f"*📋 Tất cả lịch ({len(items)}):*\n{body}\n\n_Xoá bằng_ `/delete <id>`",
        parse_mode=ParseMode.MARKDOWN,
    )


@require_active
async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("✍️ Cú pháp: `/delete <id>`", parse_mode=ParseMode.MARKDOWN)
        return
    ok = await schedule_service.delete_schedule(update.effective_user.id, int(args[0]))
    await update.message.reply_text("🗑️ Đã xoá lịch." if ok else "❌ Không tìm thấy lịch của bạn.")


@require_active
async def menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý nút bấm trên Reply Keyboard."""
    text = update.message.text
    if text == "📅 Lịch hôm nay":
        await today(update, context)
    elif text == "📋 Tất cả lịch":
        await mylist(update, context)
    elif text == "➕ Thêm lịch":
        await update.message.reply_text(
            "✍️ Gửi: `/addschedule 08:00 Việc cần làm`", parse_mode=ParseMode.MARKDOWN
        )
    elif text == "ℹ️ Trợ giúp":
        from app.bot.handlers.start import help_command

        await help_command(update, context)
