from decimal import Decimal

from app.models.alert import Direction


def is_triggered(direction: Direction, price: Decimal, target_price: Decimal) -> bool:
    if direction == Direction.ABOVE:
        return price >= target_price
    else:
        return price <= target_price
    