"""Handlers: /start, /help."""
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.bot.keyboards import MAIN_MENU
from app.services.user_service import get_or_create_user

HELP_TEXT = (
    "*🤖 Hướng dẫn sử dụng*\n\n"
    "*Lịch cá nhân:*\n"
    "• `/addschedule 08:00 Đi làm` — thêm lịch\n"
    "• `/addschedule 26/08 14:30 Họp` — thêm theo ngày\n"
    "• `/today` — lịch hôm nay\n"
    "• `/mylist` — tất cả lịch\n"
    "• `/delete <id>` — xoá lịch\n\n"
    "⏰ Bot tự gửi *tổng hợp lịch lúc 7h sáng* và *nhắc trước giờ*.\n\n"
    "*Module nâng cấp* (Admin kích hoạt theo gói):\n"
    "• `/crypto BTCUSDT` — giá + %24h · `/setcrypto BTCUSDT 5` — cảnh báo ≥5%\n"
    "• `/gold` — giá vàng SJC/PNJ\n"
    "• `/football` — lịch/kết quả · `/setteam Arsenal` — theo dõi đội\n"
    "• `/news` — tin nóng · `/setnews bitcoin,fed` — lọc theo từ khoá"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg = update.effective_user
    user, created = await get_or_create_user(tg.id, tg.username, tg.full_name)

    if user.status == "banned":
        await update.message.reply_text("⛔ Tài khoản của bạn đã bị khoá.")
        return

    greet = "🎉 Chào mừng bạn lần đầu đến với Bot!" if created else f"👋 Chào {user.full_name}!"
    await update.message.reply_text(
        f"{greet}\n"
        f"🆔 User ID: `{user.telegram_id}`\n"
        f"📦 Gói cước: *{user.plan}*\n\n"
        "Gõ /help để xem hướng dẫn.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=MAIN_MENU,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.MARKDOWN)
