import asyncio
from collections.abc import Awaitable, Callable
from decimal import Decimal
from uuid import uuid4

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.alert import Direction
from app.repositories.alert import AlertRepository
from app.repositories.user import UserRepository
from app.services.ai_alert import AlertDraft, extract_alert, normalize_price
from app.services.alert_parser import parse_alert
from app.services.exchange import get_price

settings = get_settings()
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher(events_isolation=SimpleEventIsolation())


class AIAlert(StatesGroup):
    collecting = State()
    confirming = State()


@dp.message(CommandStart())
async def start(message: Message):
    async with SessionLocal() as db:
        repo = UserRepository(db)
        user = await repo.get_by_telegram_id(message.from_user.id)
        if user is None:
            await repo.create(telegram_id=message.from_user.id, username=message.from_user.username)
            await db.commit()
            await message.answer(
                f"Hi, {message.from_user.first_name}! You are registered.\n"
                "I will notify you when the price reaches your target."
            )
        else:
            await message.answer(f"Welcome back, {message.from_user.first_name}!")


@dp.message(Command("alert"))
async def create_alert(message: Message, command: CommandObject):
    try:
        symbol, direction, target_price = parse_alert(command.args or "")
    except ValueError as error:
        await message.answer(str(error))
        return

    await save_alert(message, message.from_user.id, symbol, direction, target_price)


async def save_alert(
    message: Message,
    telegram_id: int,
    symbol: str,
    direction: Direction,
    target_price: Decimal,
    on_saved: Callable[[], Awaitable[None]] | None = None,
) -> None:
    try:
        current_price = await get_price(symbol)
    except httpx.HTTPStatusError:
        await message.answer(f"Could not get the price of {symbol} from Binance. Check the symbol or try again later.")
        return
    except httpx.RequestError:
        await message.answer("Binance is unavailable. Try again later.")
        return

    async with SessionLocal() as db:
        user = await UserRepository(db).get_by_telegram_id(telegram_id)
        if user is None:
            await message.answer("Send /start first.")
            return
        await AlertRepository(db).create(
            user_id=user.id,
            symbol=symbol,
            direction=direction,
            target_price=target_price,
        )
        await db.commit()

    if on_saved is not None:
        await on_saved()

    await message.answer(
        f"Alert created: {symbol} {direction_sign(direction)} {target_price}\n"
        f"Current price: {current_price}"
    )


@dp.message(Command("list"))
async def list_alerts(message: Message):
    async with SessionLocal() as db:
        user = await UserRepository(db).get_by_telegram_id(message.from_user.id)
        if user is None:
            await message.answer("Send /start first.")
            return
        alerts = await AlertRepository(db).get_active_by_user(user.id)

    if not alerts:
        await message.answer("You have no active alerts. Create one with /alert BTC > 100000.")
        return

    lines = ["Your alerts:"]
    for number, alert in enumerate(alerts, start=1):
        lines.append(f"{number}. {alert.symbol} {direction_sign(alert.direction)} {alert.target_price}")
    lines.append("\nTo delete an alert, use /delete followed by its number.")
    await message.answer("\n".join(lines))


@dp.message(Command("delete"))
async def delete_alert(message: Message, command: CommandObject):
    if not command.args or not command.args.strip().isdecimal():
        await message.answer("Enter an alert number from /list. For example, /delete 1.")
        return
    number = int(command.args.strip())

    async with SessionLocal() as db:
        user = await UserRepository(db).get_by_telegram_id(message.from_user.id)
        if user is None:
            await message.answer("Send /start first.")
            return
        repo = AlertRepository(db)
        alerts = await repo.get_active_by_user(user.id)

        if not 1 <= number <= len(alerts):
            await message.answer(f"Alert {number} was not found. Use /list to see your alerts.")
            return

        alert = alerts[number - 1]
        await repo.delete(alert)
        await db.commit()

    await message.answer(f"Deleted: {alert.symbol} {direction_sign(alert.direction)} {alert.target_price}")


def direction_sign(direction: Direction) -> str:
    return ">" if direction == Direction.ABOVE else "<"


@dp.message(Command("cancel"), F.chat.type == "private")
async def cancel_ai_alert(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Alert draft cleared.")


@dp.message(F.chat.type == "private", F.text, ~F.text.startswith("/"))
async def build_ai_alert(message: Message, state: FSMContext):
    if not settings.OLLAMA_MODEL:
        return
    if await state.get_state() == AIAlert.confirming.state:
        await message.answer("Confirm the alert using the button or send /cancel.")
        return

    text = message.text.strip()
    if not text or len(text) > 500:
        await message.answer("Describe your alert in one message of up to 500 characters.")
        return

    data = await state.get_data()
    draft = AlertDraft.model_validate(data.get("draft", dict.fromkeys(AlertDraft.model_fields)))
    price = normalize_price(text) if draft.symbol and draft.direction else None
    if price is not None:
        draft = draft.model_copy(update={"target_price": price})
    else:
        try:
            result = await extract_alert(text, draft, settings.OLLAMA_BASE_URL, settings.OLLAMA_MODEL)
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            await message.answer("Could not parse your message. Try again or use /alert.")
            return
        if not result.supported:
            await message.answer("I can create price alerts. Try: Notify me if BTC falls below 80000.")
            return
        fields = result.draft.model_dump()
        fields.update(draft.model_dump(exclude_none=True))
        draft = AlertDraft.model_validate(fields)

    if draft.symbol is None:
        question = "Which coin should I track?"
    elif draft.direction is None:
        question = f"Should I notify you above or below the target price for {draft.symbol}?"
    elif draft.target_price is None:
        question = f"What is the target price for {draft.symbol}?"
    else:
        await preview_ai_alert(message, state, draft)
        return

    await state.set_data({"draft": draft.model_dump(mode="json")})
    await state.set_state(AIAlert.collecting)
    await message.answer(question)


async def preview_ai_alert(message: Message, state: FSMContext, draft: AlertDraft):
    key = uuid4().hex
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Create", callback_data=f"ai-alert:yes:{key}"),
        InlineKeyboardButton(text="Cancel", callback_data=f"ai-alert:no:{key}"),
    ]])
    await state.set_data({"draft": draft.model_dump(mode="json"), "key": key})
    await state.set_state(AIAlert.confirming)
    await message.answer(
        f"Create alert: {draft.symbol} {direction_sign(draft.direction)} {draft.target_price}?",
        reply_markup=keyboard,
    )


@dp.callback_query(F.data.startswith("ai-alert:"))
async def confirm_ai_alert(callback: CallbackQuery, state: FSMContext):
    _, decision, key = callback.data.split(":", 2)
    data = await state.get_data()
    if not isinstance(callback.message, Message) or key != data.get("key"):
        await callback.answer("This draft is already closed.")
        return

    await callback.answer()
    if decision == "no":
        await state.clear()
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("Alert canceled.")
        return

    draft = AlertDraft.model_validate(data["draft"])
    await save_alert(
        callback.message,
        callback.from_user.id,
        draft.symbol,
        draft.direction,
        Decimal(draft.target_price),
        on_saved=state.clear,
    )
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())