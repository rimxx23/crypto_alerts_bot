from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.alert import AlertORM, Direction


class AlertRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_active(self) -> list[AlertORM]:
        query = (
            select(AlertORM)
            .options(selectinload(AlertORM.user))
            .where(AlertORM.is_active.is_(True))
        )
        return (await self.db.scalars(query)).all()

    async def get_active_by_user(self, user_id: str) -> list[AlertORM]:
        query = (
            select(AlertORM)
            .where(AlertORM.user_id == user_id, AlertORM.is_active.is_(True))
            .order_by(AlertORM.created_at)
        )
        return (await self.db.scalars(query)).all()

    async def create(self, user_id: str, symbol: str, target_price: Decimal, direction: Direction) -> AlertORM:
        new_alert = AlertORM(user_id=user_id, symbol=symbol, target_price=target_price, direction=direction)
        self.db.add(new_alert)
        return new_alert

    async def delete(self, alert: AlertORM) -> None:
        await self.db.delete(alert)