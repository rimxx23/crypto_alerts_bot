from decimal import Decimal

import pytest

from app.models.alert import Direction
from app.services.alert_parser import parse_alert


def test_parse_above():
    assert parse_alert("BTC > 100000") == ("BTCUSDT", Direction.ABOVE, Decimal("100000"))


def test_parse_below_lowercase_and_fraction():
    assert parse_alert("eth < 2500.5") == ("ETHUSDT", Direction.BELOW, Decimal("2500.5"))


def test_parse_not_enough_parts():
    with pytest.raises(ValueError):
        parse_alert("BTC")


def test_parse_price_not_a_number():
    with pytest.raises(ValueError):
        parse_alert("BTC > abc")


@pytest.mark.parametrize("price", ["nan", "inf", "-inf"])
def test_parse_special_decimal_values(price):
    with pytest.raises(ValueError):
        parse_alert(f"BTC > {price}")


def test_parse_unknown_sign():
    with pytest.raises(ValueError):
        parse_alert("BTC = 100")


def test_parse_negative_price():
    with pytest.raises(ValueError):
        parse_alert("BTC > -5")
