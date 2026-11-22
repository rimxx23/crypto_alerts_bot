import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.core.config import get_settings
from app.models.alert import AlertORM, Direction

settings = get_settings()
logger = logging.getLogger(__name__)


async def send_notifications(alerts: list[AlertORM]) -> None:
    async with Bot(token=settings.TELEGRAM_BOT_TOKEN) as bot:
        for alert in alerts:
            sign = ">" if alert.direction == Direction.ABOVE else "<"
            try:
                await bot.send_message(
                    chat_id=alert.user.telegram_id,
                    text=f"{alert.symbol} {sign} {alert.target_price} — price alert triggered!",
                )
            except TelegramAPIError as error:
                logger.warning("Could not send alert %s: %s", alert.id, error)
