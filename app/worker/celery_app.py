import asyncio

from celery import Celery

from app.core.config import get_settings
from app.services.alert_checker import run_check
from app.services.notifier import send_notifications


settings = get_settings()

celery_app = Celery("crypto_alerts", broker=settings.REDIS_URL)

celery_app.conf.beat_schedule = {
    "check-alerts-every-minute": {
        "task": "app.worker.celery_app.check_alerts",
        "schedule": 60.0,
    },
}


async def check_and_notify():
    triggered = await run_check()
    await send_notifications(triggered)


@celery_app.task
def check_alerts():
    asyncio.run(check_and_notify())
