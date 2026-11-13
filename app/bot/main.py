import asyncio

import httpx
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.alert import Direction
from app.repositories.alert import AlertRepository
from app.repositories.user import UserRepository
from app.services.alert_parser import parse_alert
from app.services.exchange import get_price

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


@dp.message(Command("alert"))
async def create_alert(message: Message, command: CommandObject):
    try:
        symbol, direction, target_price = parse_alert(command.args or "")
    except ValueError as error:
        await message.answer(str(error))
        return

    try:
        current_price = await get_price(symbol)
    except httpx.HTTPStatusError:
        await message.answer(f"Монета {symbol} не найдена на Binance.")
        return

    async with SessionLocal() as db:
        user = await UserRepository(db).get_by_telegram_id(message.from_user.id)
        if user is None:
            await message.answer("Сначала отправь /start")
            return
        await AlertRepository(db).create(
            user_id=user.id,
            symbol=symbol,
            direction=direction,
            target_price=target_price,
        )
        await db.commit()

    sign = ">" if direction == Direction.ABOVE else "<"
    await message.answer(
        f"Алерт создан: {symbol} {sign} {target_price}\n"
        f"Текущая цена: {current_price}"
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())