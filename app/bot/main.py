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

    await message.answer(
        f"Алерт создан: {symbol} {direction_sign(direction)} {target_price}\n"
        f"Текущая цена: {current_price}"
    )


@dp.message(Command("list"))
async def list_alerts(message: Message):
    async with SessionLocal() as db:
        user = await UserRepository(db).get_by_telegram_id(message.from_user.id)
        if user is None:
            await message.answer("Сначала отправь /start")
            return
        alerts = await AlertRepository(db).get_active_by_user(user.id)

    if not alerts:
        await message.answer("У тебя нет активных алертов. Создай: /alert BTC > 100000")
        return

    lines = ["Твои алерты:"]
    for number, alert in enumerate(alerts, start=1):
        lines.append(f"{number}. {alert.symbol} {direction_sign(alert.direction)} {alert.target_price}")
    lines.append("\nУдалить: /delete номер")
    await message.answer("\n".join(lines))


@dp.message(Command("delete"))
async def delete_alert(message: Message, command: CommandObject):
    if not command.args or not command.args.strip().isdecimal():
        await message.answer("Укажи номер алерта из /list. Например: /delete 1")
        return
    number = int(command.args.strip())

    async with SessionLocal() as db:
        user = await UserRepository(db).get_by_telegram_id(message.from_user.id)
        if user is None:
            await message.answer("Сначала отправь /start")
            return
        repo = AlertRepository(db)
        alerts = await repo.get_active_by_user(user.id)

        if not 1 <= number <= len(alerts):
            await message.answer(f"Нет алерта с номером {number}. Посмотри список: /list")
            return

        alert = alerts[number - 1]
        await repo.delete(alert)
        await db.commit()

    await message.answer(f"Удалён: {alert.symbol} {direction_sign(alert.direction)} {alert.target_price}")


def direction_sign(direction: Direction) -> str:
    return ">" if direction == Direction.ABOVE else "<"


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())