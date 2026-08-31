"""Handlers: mua gói dịch vụ trong bot (QR SePay)."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.core.config import settings
from app.core.constants import PRODUCTS
from app.core.database import AsyncSessionLocal
from app.services import payment_service
from app.services.user_service import get_or_create_user


def _vnd(amount: int) -> str:
    return f"{amount:,}".replace(",", ".") + "đ"


def _buy_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard: dịch vụ lẻ (2 cột) → combo → full."""
    singles = [p for p in PRODUCTS if p["type"] == "single"]
    rows: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(singles), 2):
        rows.append(
            [
                InlineKeyboardButton(
                    f"{p['label']} — {_vnd(p['price'])}", callback_data=f"buy:{p['key']}"
                )
                for p in singles[i : i + 2]
            ]
        )
    for p in PRODUCTS:
        if p["type"] in ("combo", "full"):
            rows.append(
                [
                    InlineKeyboardButton(
                        f"{p['label']} — {_vnd(p['price'])}", callback_data=f"buy:{p['key']}"
                    )
                ]
            )
    return InlineKeyboardMarkup(rows)


async def buy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/muagoi — hiện danh mục để chọn mua."""
    if not settings.payment_enabled:
        await update.message.reply_text(
            "⚠️ Tính năng thanh toán chưa được bật. Vui lòng liên hệ admin."
        )
        return
    await update.message.reply_text(
        "*🛒 Chọn gói dịch vụ muốn mua* (hạn dùng 30 ngày):\n\n"
        "• Lẻ mỗi dịch vụ: 20.000đ\n"
        "• Combo (2 dịch vụ): 40.000đ\n"
        "• Full 4 dịch vụ: 70.000đ",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_buy_keyboard(),
    )


async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý bấm nút mua → tạo đơn + gửi QR."""
    query = update.callback_query
    await query.answer()

    if not settings.payment_enabled:
        await query.message.reply_text("⚠️ Tính năng thanh toán chưa được bật.")
        return

    product_key = query.data.split(":", 1)[1]
    if payment_service.get_product(product_key) is None:
        await query.message.reply_text("❌ Sản phẩm không hợp lệ.")
        return

    tg = update.effective_user
    user, _ = await get_or_create_user(tg.id, tg.username, tg.full_name)

    async with AsyncSessionLocal() as session:
        order = await payment_service.create_order(session, user.id, product_key)
        await session.commit()
        qr_url = payment_service.build_qr_url(order)
        caption = (
            f"🧾 *Đơn:* {order.item_label}\n"
            f"💵 *Số tiền:* {_vnd(order.amount)}\n"
            f"📝 *Nội dung CK:* `{order.code}`\n\n"
            "📲 Quét QR bằng app ngân hàng — số tiền & nội dung đã điền sẵn, "
            "*giữ nguyên nội dung* để hệ thống khớp đơn.\n"
            "⏳ Đơn có hạn 15 phút.\n"
            "✅ Bot sẽ *tự nâng cấp* sau khi nhận tiền (thường 1-2 phút), không cần thao tác thêm."
        )

    await query.message.reply_photo(photo=qr_url, caption=caption, parse_mode=ParseMode.MARKDOWN)
