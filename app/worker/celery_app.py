import asyncio

from celery import Celery

from app.core.config import get_settings
from app.services.exchange import get_price


settings = get_settings()

celery_app = Celery("crypto_alerts", broker=settings.REDIS_URL)

celery_app.conf.beat_schedule = {
    "check-prices-every-minute": {
        "task": "app.worker.celery_app.check_prices",
        "schedule": 60.0,
    },
}


@celery_app.task
def check_prices():
    price = asyncio.run(get_price("BTCUSDT"))
    print(f"BTC price: {price}")