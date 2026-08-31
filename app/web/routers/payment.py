"""Router: webhook SePay — nhận biến động số dư, tự nâng cấp gói."""
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.logging import get_logger
from app.repositories import log_repo, order_repo, user_repo
from app.services import payment_service, telegram_notify

logger = get_logger(__name__)
router = APIRouter(prefix="/api/sepay")


def _vnd(amount: int) -> str:
    return f"{amount:,}".replace(",", ".") + "đ"


@router.post("/webhook")
async def sepay_webhook(
    request: Request,
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    # Chưa cấu hình apikey → endpoint coi như chưa bật (tránh để hở).
    if not settings.SEPAY_WEBHOOK_APIKEY:
        raise HTTPException(status_code=503, detail="Payment not configured")
    if authorization != f"Apikey {settings.SEPAY_WEBHOOK_APIKEY}":
        raise HTTPException(status_code=401, detail="Invalid apikey")

    payload = await request.json()

    # Chỉ xử lý tiền CHUYỂN VÀO.
    if payload.get("transferType") not in (None, "in"):
        return {"success": True}

    amount = int(payload.get("transferAmount") or 0)
    content = payload.get("content") or payload.get("description") or ""
    code = payload.get("code") or payment_service.parse_order_code(content)

    if not code:
        await _log_unmatched(session, "no_code", payload)
        return {"success": True}

    order = await order_repo.get_by_code(session, str(code).upper())
    if order is None:
        await _log_unmatched(session, "code_not_found", payload)
        return {"success": True}

    if order.status == "paid":  # SePay retry / trùng → bỏ qua
        return {"success": True}

    if amount < order.amount:  # trả thiếu → không mở, để admin xử lý tay
        await _log_unmatched(session, "underpaid", payload)
        return {"success": True}

    opened = await payment_service.fulfill_order(session, order, raw=payload)
    await session.commit()

    if opened:
        user = await user_repo.get_by_id(session, order.user_id)
        if user is not None:
            await telegram_notify.send_message(
                user.telegram_id,
                f"✅ *Thanh toán thành công!*\n"
                f"🧾 {order.item_label} ({_vnd(order.amount)})\n"
                f"🎉 Đã kích hoạt dịch vụ, hạn dùng đến "
                f"*{user.expires_at:%H:%M %d/%m/%Y}*.\nCảm ơn bạn!",
            )
        logger.info("Đơn %s đã thanh toán & nâng cấp user %s", order.code, order.user_id)

    return {"success": True}


async def _log_unmatched(session: AsyncSession, reason: str, payload: dict) -> None:
    await log_repo.write(
        session,
        action="order_unmatched",
        actor="system",
        level="warn",
        detail={"reason": reason, "payload": payload},
    )
    await session.commit()
