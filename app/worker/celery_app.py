"""Khởi tạo Celery app + lịch Beat."""
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "botnews",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.worker.tasks.send_message",
        "app.worker.tasks.daily_digest",
        "app.worker.tasks.schedule_reminder",
    ],
)

celery_app.conf.update(
    timezone=settings.TIMEZONE,
    enable_utc=True,
    task_default_rate_limit="25/s",  # giữ dưới ngưỡng Telegram 30/s
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)

celery_app.conf.beat_schedule = {
    "daily-digest-7am": {
        "task": "app.worker.tasks.daily_digest.send_daily_digest",
        "schedule": crontab(hour=7, minute=0),
    },
    "schedule-reminder-every-minute": {
        "task": "app.worker.tasks.schedule_reminder.check_reminders",
        "schedule": crontab(minute="*"),
    },
}
