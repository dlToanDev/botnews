"""Entrypoint Telegram Bot (long polling)."""
from telegram import BotCommand, MenuButtonCommands, Update
from telegram.ext import (
    AIORateLimiter,
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from app.bot.handlers import ai, calendar_ui, features, menu, payment, schedule, start
from app.core.config import settings
from app.core.logging import get_logger, setup_logging

logger = get_logger(__name__)

_MENU_BUTTONS = r"^(🧭 Menu|📅 Lịch hôm nay|📋 Tất cả lịch|➕ Thêm lịch|ℹ️ Trợ giúp)$"

# Bí danh tiếng Việt (KHÔNG DẤU — Telegram không nhận dấu) cho từng lệnh tiếng Anh.
# Đây là NGUỒN DUY NHẤT: dùng cho cả handler lẫn nút Menu để không lệch nhau.
VI_ALIAS: dict[str, str] = {
    "start": "batdau",
    "help": "trogiup",
    "buy": "muagoi",
    "ai": "troly",
    "ainews": "aitin",
    "aigold": "aivang",
    "aicrypto": "aicoin",
    "today": "homnay",
    "mylist": "danhsach",
    "addschedule": "themlich",
    "calendar": "lich",
    "delete": "xoa",
    "gold": "vang",
    "crypto": "tiendientu",
    "setcrypto": "datcrypto",
    "football": "bongda",
    "live": "tructiep",
    "bxh": "bangxephang",
    "myteam": "doicuatoi",
    "setteam": "chondoi",
    "news": "tintuc",
    "setnews": "tukhoatin",
}

# Các lệnh hiển thị trong nút Menu (english_key, mô tả). Lệnh set* nâng cao không đưa vào menu.
_MENU_ITEMS: list[tuple[str, str]] = [
    ("start", "Khởi động & thông tin tài khoản"),
    ("buy", "🛒 Mua gói dịch vụ"),
    ("ai", "🤖 Hỏi trợ lý AI"),
    ("help", "Hướng dẫn sử dụng"),
    ("today", "Lịch hôm nay"),
    ("mylist", "Tất cả lịch của tôi"),
    ("calendar", "🗓️ Lịch tương tác"),
    ("addschedule", "Thêm lịch mới"),
    ("gold", "Giá vàng SJC/PNJ"),
    ("crypto", "Top vốn hóa & giá coin"),
    ("football", "Bóng đá / Live score"),
    ("live", "⚽ Trận đang diễn ra"),
    ("bxh", "🏆 Bảng xếp hạng"),
    ("myteam", "📅 Lịch đội theo dõi"),
    ("news", "Tin tức nóng"),
]

# Menu hiện CẢ 2 BỘ: tiếng Việt trước (🇻🇳), tiếng Anh sau (🇬🇧).
# Kèm lệnh tắt theo giải (1 bộ, không dấu): /epl, /bxhepl, ...
_LEAGUE_MENU = (
    [BotCommand(cmd, f"⚽ KQ {label}") for cmd, (_code, label) in features.LEAGUE_CMDS.items()]
    + [BotCommand(f"bxh{cmd}", f"🏆 BXH {label}") for cmd, (_code, label) in features.LEAGUE_CMDS.items()]
)
# Lệnh giá coin theo từng đồng (1 bộ, không dấu): /btc, /eth, ...
_COIN_MENU = [BotCommand(sym, f"💵 Giá {sym.upper()}") for sym in features.COIN_HANDLERS]
BOT_COMMANDS = (
    [BotCommand("menu", "🧭 Menu chính (mua gói & cài đặt)")]
    + [BotCommand(VI_ALIAS[en], f"🇻🇳 {desc}") for en, desc in _MENU_ITEMS]
    + [BotCommand(en, f"🇬🇧 {desc}") for en, desc in _MENU_ITEMS]
    + _COIN_MENU
    + _LEAGUE_MENU
)


def _cmd(english: str) -> list[str]:
    """Trả về [lệnh tiếng Anh, bí danh tiếng Việt] cho CommandHandler."""
    return [english, VI_ALIAS[english]]


async def _post_init(app: Application) -> None:
    """Đăng ký danh sách lệnh + bật nút Menu (chạy 1 lần khi bot khởi động)."""
    await app.bot.set_my_commands(BOT_COMMANDS)
    await app.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    logger.info("✅ Đã đăng ký %d lệnh (Anh+Việt) vào nút Menu Telegram", len(BOT_COMMANDS))


def build_application() -> Application:
    app = (
        Application.builder()
        .token(settings.BOT_TOKEN)
        .rate_limiter(AIORateLimiter())  # chống rate-limit Telegram
        .post_init(_post_init)  # đăng ký nút Menu khi khởi động
        .build()
    )

    # Mỗi handler nhận CẢ lệnh tiếng Anh lẫn bí danh tiếng Việt (_cmd()).
    # Core
    app.add_handler(CommandHandler(_cmd("start"), start.start))
    app.add_handler(CommandHandler(_cmd("help"), start.help_command))

    # Menu inline phân cấp (mua gói + tự cấu hình)
    app.add_handler(CommandHandler("menu", menu.menu_cmd))
    app.add_handler(CallbackQueryHandler(menu.menu_callback, pattern=r"^menu:"))

    # Mua gói dịch vụ (thanh toán SePay)
    app.add_handler(CommandHandler(_cmd("buy"), payment.buy_menu))
    app.add_handler(CallbackQueryHandler(payment.buy_callback, pattern=r"^buy:"))

    # Trợ lý AI (Gemini) — module trả phí
    app.add_handler(CommandHandler(_cmd("ai"), ai.ai_cmd))
    app.add_handler(CommandHandler(_cmd("ainews"), ai.ainews_cmd))
    app.add_handler(CommandHandler(_cmd("aigold"), ai.aigold_cmd))
    app.add_handler(CommandHandler(_cmd("aicrypto"), ai.aicrypto_cmd))

    # Lịch cá nhân
    app.add_handler(CommandHandler(_cmd("addschedule"), schedule.add_schedule))
    app.add_handler(CommandHandler(_cmd("today"), schedule.today))
    app.add_handler(CommandHandler(_cmd("mylist"), schedule.mylist))
    app.add_handler(CommandHandler(_cmd("calendar"), calendar_ui.cal_cmd))
    app.add_handler(CommandHandler(_cmd("delete"), schedule.delete))
    app.add_handler(CallbackQueryHandler(calendar_ui.cal_callback, pattern=r"^cal:"))

    # Module SaaS (gated bằng @require_module)
    app.add_handler(CommandHandler(_cmd("crypto"), features.crypto_cmd))
    app.add_handler(CommandHandler(_cmd("setcrypto"), features.setcrypto_cmd))
    app.add_handler(CommandHandler(_cmd("gold"), features.gold_cmd))
    app.add_handler(CommandHandler(_cmd("football"), features.football_cmd))
    app.add_handler(CommandHandler(_cmd("live"), features.live_cmd))
    app.add_handler(CommandHandler(_cmd("bxh"), features.standings_cmd))
    app.add_handler(CommandHandler(_cmd("myteam"), features.myteam_cmd))
    app.add_handler(CommandHandler(_cmd("setteam"), features.setteam_cmd))
    app.add_handler(CommandHandler(_cmd("news"), features.news_cmd))
    app.add_handler(CommandHandler(_cmd("setnews"), features.setnews_cmd))

    # Lệnh giá coin theo từng đồng (CoinGecko): /btc, /eth, /bnb, ...
    for sym, handler in features.COIN_HANDLERS.items():
        app.add_handler(CommandHandler(sym, handler))

    # Lệnh tắt theo giải (football-data.org): /epl (KQ vòng gần nhất) + /bxhepl (BXH), ...
    for cmd, handler in features.LEAGUE_RESULT_HANDLERS.items():
        app.add_handler(CommandHandler(cmd, handler))
    for cmd, handler in features.LEAGUE_STANDINGS_HANDLERS.items():
        app.add_handler(CommandHandler(f"bxh{cmd}", handler))

    # Nút menu (Reply Keyboard)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(_MENU_BUTTONS), schedule.menu_text)
    )
    # Nhận tiêu đề lịch khi đang thêm qua /lich (đăng ký SAU menu → nút menu ưu tiên trước).
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, calendar_ui.cal_title_text)
    )
    # Nhận đội yêu thích khi cấu hình bóng đá qua /menu (group=1 để không đụng handler text group 0).
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, menu.menu_text_input), group=1
    )

    return app


def main() -> None:
    setup_logging()
    app = build_application()
    logger.info("🤖 Bot đang chạy (long polling)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
