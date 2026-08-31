"""Models: User + UserSettings."""
from datetime import datetime, time

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Time,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    full_name: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)  # active|expired|banned
    plan: Mapped[str] = mapped_column(String(50), default="free")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    settings: Mapped["UserSettings"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Ho_Chi_Minh")
    daily_digest_time: Mapped[time] = mapped_column(Time, default=time(7, 0))
    reminder_minutes: Mapped[int] = mapped_column(default=30)
    crypto_watchlist: Mapped[list] = mapped_column(JSONB, default=list)
    crypto_times: Mapped[list] = mapped_column(JSONB, default=list)  # giờ nhận báo giá crypto "HH:MM"
    crypto_notify_mode: Mapped[str] = mapped_column(String(10), default="system")  # system|custom|off
    crypto_coins: Mapped[list] = mapped_column(JSONB, default=list)  # đồng muốn nhận (rỗng=tất cả)
    gold_alert_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))
    gold_times: Mapped[list] = mapped_column(JSONB, default=list)  # giờ nhận báo giá vàng "HH:MM"
    news_keywords: Mapped[list] = mapped_column(JSONB, default=list)
    news_categories: Mapped[list] = mapped_column(JSONB, default=list)
    favorite_teams: Mapped[list] = mapped_column(JSONB, default=list)
    football_times: Mapped[list] = mapped_column(JSONB, default=list)  # giờ nhận KQ bóng đá "HH:MM"
    language: Mapped[str] = mapped_column(String(10), default="vi")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="settings")
