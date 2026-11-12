from decimal import Decimal

from app.models.alert import Direction
from app.services.alert_checker import is_triggered
def test_above_when_price_higher():
    assert is_triggered(Direction.ABOVE, Decimal("105"), Decimal("100"))

def test_above_when_price_lower():
    assert is_triggered(Direction.ABOVE, Decimal("100"), Decimal("105")) is False

def test_above_when_price_equal():
    assert is_triggered(Direction.ABOVE, Decimal("100"), Decimal("100"))

def test_below_when_price_higher():
    assert is_triggered(Direction.BELOW, Decimal("105"), Decimal("100")) is False

def test_below_when_price_lower():
    assert is_triggered(Direction.BELOW, Decimal("100"), Decimal("105"))

def test_below_when_price_equal():
    assert is_triggered(Direction.BELOW, Decimal("100"), Decimal("100"))
