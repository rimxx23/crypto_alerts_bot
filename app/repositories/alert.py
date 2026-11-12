from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import AlertORM


class AlertRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_active(self) -> list[AlertORM]:
        return (await self.db.scalars(select(AlertORM).where(AlertORM.is_active == True))).all()