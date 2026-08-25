"""Model: Log (nhật ký hoạt động & audit)."""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Log(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    actor: Mapped[str] = mapped_column(String(20), default="system")  # user|admin|system
    action: Mapped[str] = mapped_column(String(100), index=True)
    level: Mapped[str] = mapped_column(String(10), default="info")  # info|warn|error
    detail: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
