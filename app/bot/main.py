"""Entrypoint Telegram Bot (long polling)."""
from telegram import Update
from telegram.ext import (
    AIORateLimiter,
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from app.bot.handlers import features, schedule, start
from app.core.config import settings
from app.core.logging import get_logger, setup_logging

logger = get_logger(__name__)

_MENU_BUTTONS = r"^(📅 Lịch hôm nay|📋 Tất cả lịch|➕ Thêm lịch|ℹ️ Trợ giúp)$"


def build_application() -> Application:
    app = (
        Application.builder()
        .token(settings.BOT_TOKEN)
        .rate_limiter(AIORateLimiter())  # chống rate-limit Telegram
        .build()
    )

    # Core
    app.add_handler(CommandHandler("start", start.start))
    app.add_handler(CommandHandler("help", start.help_command))

    # Lịch cá nhân
    app.add_handler(CommandHandler("addschedule", schedule.add_schedule))
    app.add_handler(CommandHandler("today", schedule.today))
    app.add_handler(CommandHandler("mylist", schedule.mylist))
    app.add_handler(CommandHandler("delete", schedule.delete))

    # Module SaaS (gated bằng @require_module)
    app.add_handler(CommandHandler("crypto", features.crypto))
    app.add_handler(CommandHandler("gold", features.gold))
    app.add_handler(CommandHandler("football", features.football))
    app.add_handler(CommandHandler("news", features.news))

    # Nút menu (Reply Keyboard)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(_MENU_BUTTONS), schedule.menu_text)
    )

    return app


def main() -> None:
    setup_logging()
    app = build_application()
    logger.info("🤖 Bot đang chạy (long polling)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
