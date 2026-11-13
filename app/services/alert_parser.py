from decimal import Decimal, InvalidOperation

from app.models.alert import Direction

DIRECTIONS = {
    ">": Direction.ABOVE,
    "<": Direction.BELOW,
}

USAGE = "Формат: /alert BTC > 100000"


def parse_alert(text: str) -> tuple[str, Direction, Decimal]:
    parts = text.split()
    if len(parts) != 3:
        raise ValueError(f"Нужно три части: монета, знак и цена. {USAGE}")

    coin, sign, price_text = parts

    if sign not in DIRECTIONS:
        raise ValueError(f"Знак должен быть > или <. {USAGE}")

    try:
        price = Decimal(price_text)
    except InvalidOperation:
        raise ValueError(f"Цена должна быть числом. {USAGE}")

    if not price.is_finite():
        raise ValueError(f"Цена должна быть числом. {USAGE}")

    if price <= 0:
        raise ValueError("Цена должна быть больше нуля.")

    symbol = coin.upper() + "USDT"
    return symbol, DIRECTIONS[sign], price
