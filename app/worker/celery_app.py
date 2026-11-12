import asyncio

from celery import Celery

from app.core.config import get_settings
from app.services.alert_checker import run_check
from app.services.exchange import get_price


settings = get_settings()

celery_app = Celery("crypto_alerts", broker=settings.REDIS_URL)

celery_app.conf.beat_schedule = {
    "check-alerts-every-minute": {
        "task": "app.worker.celery_app.check_alerts",
        "schedule": 60.0,
    },
}


@celery_app.task
def check_alerts():
    triggered = asyncio.run(run_check())
    for alert in triggered:
        print(f"{alert.symbol} {alert.direction.value} {alert.target_price}")
