import asyncio

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.repositories.user import UserRepository

settings = get_settings()
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):
    async with SessionLocal() as db:
        repo = UserRepository(db)
        user = await repo.get_by_telegram_id(message.from_user.id)
        if user is None:
            await repo.create(telegram_id=message.from_user.id, username=message.from_user.username)
            await db.commit()
            await message.answer(
                f"Привет, {message.from_user.first_name}! Ты зарегистрирован.\n"
                "Я пришлю уведомление, когда цена дойдёт до нужной."
            )
        else:
            await message.answer(f"С возвращением, {message.from_user.first_name}!")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())