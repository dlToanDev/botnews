"""Business logic bán gói dịch vụ qua SePay (tạo đơn, QR, ghi nhận thanh toán)."""
import re
import secrets
from datetime import timedelta
from urllib.parse import quote

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import (
    ORDER_TTL_MINUTES,
    PRODUCTS_BY_KEY,
    SUBSCRIPTION_DAYS,
)
from app.core.timeutils import now_utc
from app.models.order import Order
from app.repositories import log_repo, module_repo, order_repo, user_repo

# Mã đơn dạng BOT + 6 hex hoa (vd BOT9F3A2C). Dùng để khớp nội dung chuyển khoản.
_CODE_RE = re.compile(r"BOT[0-9A-F]{6}", re.IGNORECASE)


def get_product(product_key: str) -> dict | None:
    return PRODUCTS_BY_KEY.get(product_key)


def _new_code() -> str:
    return "BOT" + secrets.token_hex(3).upper()


def parse_order_code(content: str | None) -> str | None:
    """Rút mã đơn (BOTxxxxxx) từ nội dung chuyển khoản webhook."""
    if not content:
        return None
    m = _CODE_RE.search(content)
    return m.group(0).upper() if m else None


def build_qr_url(order: Order) -> str:
    """URL ảnh QR VietQR của SePay — quét là tự điền số tiền + nội dung (mã đơn)."""
    return (
        "https://qr.sepay.vn/img"
        f"?acc={quote(settings.SEPAY_ACCOUNT_NUMBER or '')}"
        f"&bank={quote(settings.SEPAY_BANK_CODE or '')}"
        f"&amount={order.amount}"
        f"&des={quote(order.code)}"
    )


async def create_order(session: AsyncSession, user_id: int, product_key: str) -> Order:
    """Tạo đơn PENDING cho một sản phẩm trong catalog."""
    product = PRODUCTS_BY_KEY.get(product_key)
    if product is None:
        raise ValueError(f"Sản phẩm không hợp lệ: {product_key}")
    order = Order(
        user_id=user_id,
        code=_new_code(),
        item_key=product["key"],
        item_label=product["label"],
        modules=list(product["modules"]),
        amount=product["price"],
        status="pending",
        expires_at=now_utc() + timedelta(minutes=ORDER_TTL_MINUTES),
    )
    await order_repo.create(session, order)
    await log_repo.write(
        session,
        action="order_create",
        user_id=user_id,
        actor="user",
        detail={"code": order.code, "item": product_key, "amount": order.amount},
    )
    return order


async def fulfill_order(session: AsyncSession, order: Order, raw: dict) -> bool:
    """Ghi nhận thanh toán: bật module + gia hạn 30 ngày. IDEMPOTENT.

    Trả True nếu vừa mở (lần đầu), False nếu đơn đã paid trước đó (bỏ qua).
    """
    if order.status == "paid":
        return False

    now = now_utc()
    user = await user_repo.get_by_id(session, order.user_id)
    if user is None:
        return False

    for key in order.modules:
        await module_repo.upsert(session, order.user_id, key, True)

    base = user.expires_at if (user.expires_at and user.expires_at > now) else now
    user.expires_at = base + timedelta(days=SUBSCRIPTION_DAYS)
    user.status = "active"

    order.status = "paid"
    order.paid_at = now
    order.raw = raw

    await log_repo.write(
        session,
        action="order_paid",
        user_id=order.user_id,
        actor="system",
        detail={
            "code": order.code,
            "item": order.item_key,
            "amount": order.amount,
            "modules": order.modules,
            "new_expiry": user.expires_at.isoformat(),
        },
    )
    return True
