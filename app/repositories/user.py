from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserORM


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_telegram_id(self, telegram_id: int) -> UserORM | None:
        return await self.db.scalar(select(UserORM).where(UserORM.telegram_id == telegram_id))

    async def create(self, telegram_id: int, username: str | None) -> UserORM:
        new_user = UserORM(telegram_id=telegram_id, username=username)
        self.db.add(new_user)
        return new_user
