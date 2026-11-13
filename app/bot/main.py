import asyncio

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.core.config import get_settings

settings = get_settings()
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(f"Привет, {message.from_user.first_name}! Я пришлю уведомление, когда цена дойдёт до нужной.")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())