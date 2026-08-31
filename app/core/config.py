"""Cấu hình tập trung cho toàn hệ thống — đọc từ biến môi trường / file .env."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Telegram ---
    BOT_TOKEN: str

    # --- Database ---
    DATABASE_URL: str

    # --- Redis / Celery ---
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # --- Web Admin ---
    JWT_SECRET: str = "change-me"
    ADMIN_DEFAULT_USER: str = "admin"

    # --- Timezone ---
    TIMEZONE: str = "Asia/Ho_Chi_Minh"

    # --- External APIs (dùng ở Phase 3) ---
    API_FOOTBALL_KEY: str | None = None  # api-sports.io — dùng cho /live (real-time)
    FOOTBALL_DATA_KEY: str | None = None  # football-data.org — BXH & kết quả mùa hiện tại (free)
    NEWSAPI_KEY: str | None = None

    # --- Thanh toán SePay (bán gói trong bot) ---
    # Thiếu số tài khoản hoặc mã ngân hàng → tính năng /muagoi bị tắt.
    SEPAY_WEBHOOK_APIKEY: str | None = None
    SEPAY_ACCOUNT_NUMBER: str | None = None
    SEPAY_BANK_CODE: str | None = None  # mã ngân hàng SePay (vd: MBBank, Vietcombank, ACB)
    SEPAY_ACCOUNT_NAME: str | None = None

    @property
    def payment_enabled(self) -> bool:
        return bool(self.SEPAY_ACCOUNT_NUMBER and self.SEPAY_BANK_CODE)

    # --- Trợ lý AI (Google Gemini) ---
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.0-flash"

    @property
    def ai_enabled(self) -> bool:
        return bool(self.GEMINI_API_KEY)


settings = Settings()
