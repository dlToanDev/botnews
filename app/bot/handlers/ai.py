"""Handler: trợ lý AI (Gemini) — module trả phí `ai`.

v1: chat hỏi–đáp (/ai). v2: phân tích theo dịch vụ (/ainews, /aigold, /aicrypto).
"""
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from app.bot.decorators import require_module
from app.core.config import settings
from app.core.constants import AI_DAILY_LIMIT
from app.integrations.gemini import GeminiQuotaError
from app.services import ai_service


async def _run(update: Update, context: ContextTypes.DEFAULT_TYPE, producer) -> None:
    """Khung chung: kiểm cấu hình + quota + gọi AI + trả lời. `producer(user_id)->str`."""
    if not settings.ai_enabled:
        await update.message.reply_text("⚠️ Trợ lý AI chưa được cấu hình. Liên hệ admin.")
        return

    user_id = context.user_data.get("db_user_id")
    allowed, used = await ai_service.check_and_incr(user_id)
    if not allowed:
        await update.message.reply_text(
            f"🚫 Bạn đã dùng hết *{AI_DAILY_LIMIT} lượt AI* hôm nay. Mai thử lại nhé!",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    try:
        text = await producer(user_id)
    except ai_service.NoDataError as e:
        await ai_service.refund(user_id)  # không tính lượt khi thiếu dữ liệu nguồn
        await update.message.reply_text(f"⚠️ {e}")
        return
    except GeminiQuotaError:
        await update.message.reply_text("⏳ AI đang quá tải, vui lòng thử lại sau ít phút.")
        return
    except Exception:
        await update.message.reply_text("❌ Xin lỗi, AI gặp sự cố. Vui lòng thử lại.")
        return

    remaining = max(0, AI_DAILY_LIMIT - used)
    # Plain text: nội dung AI không kiểm soát được, dễ vỡ Markdown parser.
    await update.message.reply_text(f"{text}\n\n— Còn {remaining}/{AI_DAILY_LIMIT} lượt hôm nay.")


@require_module("ai")
async def ai_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ai <câu hỏi> — chat hỏi–đáp tự do."""
    question = " ".join(context.args).strip() if context.args else ""
    if not question:
        await update.message.reply_text(
            "🤖 *Trợ lý AI* — các lệnh:\n"
            "• `/ai <câu hỏi>` — hỏi bất cứ điều gì\n"
            "• `/ainews` — tóm tắt tin nóng hôm nay\n"
            "• `/aigold` — nhận định giá vàng\n"
            "• `/aicrypto BTCUSDT` — phân tích 1 coin\n\n"
            "Ví dụ: `/ai giải thích blockchain trong 3 câu`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    await _run(update, context, lambda uid: ai_service.answer(uid, question))


@require_module("ai")
async def ainews_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ainews — AI tóm tắt tin nóng."""
    await _run(update, context, ai_service.summarize_news)


@require_module("ai")
async def aigold_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/aigold — AI nhận định giá vàng."""
    await _run(update, context, ai_service.analyze_gold)


@require_module("ai")
async def aicrypto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/aicrypto <symbol> — AI phân tích 1 coin."""
    symbol = (context.args[0].upper() if context.args else "BTCUSDT")
    await _run(update, context, lambda uid: ai_service.analyze_crypto(uid, symbol))
