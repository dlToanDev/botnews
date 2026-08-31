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
        "app.worker.tasks.send_photo",
        "app.worker.tasks.daily_digest",
        "app.worker.tasks.schedule_reminder",
        "app.worker.tasks.expire_users",
        "app.worker.tasks.crypto_alert",
        "app.worker.tasks.crypto_digest",
        "app.worker.tasks.gold_alert",
        "app.worker.tasks.gold_digest",
        "app.worker.tasks.football_live",
        "app.worker.tasks.football_digest",
        "app.worker.tasks.news_push",
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
    "expire-users-daily": {
        "task": "app.worker.tasks.expire_users.expire_overdue",
        "schedule": crontab(hour=0, minute=5),
    },
    "crypto-poll-2min": {
        "task": "app.worker.tasks.crypto_alert.poll_and_alert",
        "schedule": crontab(minute="*/2"),
    },
    "gold-poll-10min": {
        "task": "app.worker.tasks.gold_alert.poll_and_alert",
        "schedule": crontab(minute="*/10"),
    },
    "gold-digest-every-minute": {
        "task": "app.worker.tasks.gold_digest.poll_and_send",
        "schedule": crontab(minute="*"),
    },
    "crypto-digest-every-minute": {
        "task": "app.worker.tasks.crypto_digest.poll_and_send",
        "schedule": crontab(minute="*"),
    },
    "football-digest-every-minute": {
        "task": "app.worker.tasks.football_digest.poll_and_send",
        "schedule": crontab(minute="*"),
    },
    "football-live-2min": {
        "task": "app.worker.tasks.football_live.poll_and_alert",
        "schedule": crontab(minute="*/2"),
    },
    "news-push-2min": {
        "task": "app.worker.tasks.news_push.poll_and_alert",
        "schedule": crontab(minute="*/2"),
    },
}
