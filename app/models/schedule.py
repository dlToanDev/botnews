"""Model: Schedule (lịch cá nhân)."""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    location: Mapped[str | None] = mapped_column(String(255))
    recurrence: Mapped[str] = mapped_column(String(20), default="none")  # none|daily|weekly|monthly
    recur_days: Mapped[list] = mapped_column(JSONB, default=list)
    reminder_minutes: Mapped[int] = mapped_column(default=30)
    is_notified: Mapped[bool] = mapped_column(Boolean, default=False)  # đã nhắc TRƯỚC giờ
    started_notified: Mapped[bool] = mapped_column(Boolean, default=False)  # đã báo ĐÚNG giờ
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
