"""Model: Order (đơn mua gói dịch vụ, thanh toán qua SePay)."""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Mã nhét vào nội dung chuyển khoản, dùng để khớp webhook (vd "BOT9F3A2C").
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    item_key: Mapped[str] = mapped_column(String(50))
    item_label: Mapped[str] = mapped_column(String(100))
    modules: Mapped[list] = mapped_column(JSONB, default=list)  # module_key sẽ mở
    amount: Mapped[int] = mapped_column(Integer)  # VND
    status: Mapped[str] = mapped_column(
        String(20), default="pending", index=True
    )  # pending|paid|expired
    raw: Mapped[dict] = mapped_column(JSONB, default=dict)  # payload webhook đã khớp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
