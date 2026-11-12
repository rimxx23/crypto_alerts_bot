from datetime import datetime, timezone
from decimal import Decimal

from app.db.session import SessionLocal
from app.models.alert import AlertORM, Direction
from app.repositories.alert import AlertRepository
from app.services.exchange import get_price


def is_triggered(direction: Direction, price: Decimal, target_price: Decimal) -> bool:
    if direction == Direction.ABOVE:
        return price >= target_price
    else:
        return price <= target_price

async def run_check() -> list[AlertORM]:
    async with SessionLocal() as db:
        alerts = await AlertRepository(db).get_active()
        symbols = {alert.symbol for alert in alerts}
        prices = {symbol: await get_price(symbol) for symbol in symbols}
        triggered = []
        for alert in alerts:
            price = prices[alert.symbol]
            if is_triggered(alert.direction, price, alert.target_price):
                alert.is_active = False
                alert.triggered_at = datetime.now(timezone.utc)
                triggered.append(alert)
        await db.commit()
        return triggered