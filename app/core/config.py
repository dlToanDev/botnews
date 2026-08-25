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
    API_FOOTBALL_KEY: str | None = None
    NEWSAPI_KEY: str | None = None


settings = Settings()
