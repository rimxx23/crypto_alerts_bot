from decimal import Decimal, InvalidOperation

from app.models.alert import Direction

DIRECTIONS = {
    ">": Direction.ABOVE,
    "<": Direction.BELOW,
}

USAGE = "Usage: /alert BTC > 100000"


def parse_alert(text: str) -> tuple[str, Direction, Decimal]:
    parts = text.split()
    if len(parts) != 3:
        raise ValueError(f"Enter a coin, a comparison sign, and a price. {USAGE}")

    coin, sign, price_text = parts

    if sign not in DIRECTIONS:
        raise ValueError(f"The comparison sign must be > or <. {USAGE}")

    try:
        price = Decimal(price_text)
    except InvalidOperation:
        raise ValueError(f"The price must be a finite number. {USAGE}")

    if not price.is_finite():
        raise ValueError(f"The price must be a finite number. {USAGE}")

    if price <= 0:
        raise ValueError("The price must be greater than zero.")

    symbol = coin.upper() + "USDT"
    return symbol, DIRECTIONS[sign], price
