"""Task hằng ngày: chuyển user quá hạn sang trạng thái 'expired'."""
import asyncio

from app.core.logging import get_logger
from app.services.subscription_service import expire_overdue_users
from app.worker.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.worker.tasks.expire_users.expire_overdue")
def expire_overdue() -> int:
    n = asyncio.run(expire_overdue_users())
    if n:
        logger.info("Auto-expire: %d user quá hạn.", n)
    return n
