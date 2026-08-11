from decimal import Decimal

from pricing import discounted_price


def test_discounted_price() -> None:
    assert discounted_price(Decimal("100.00"), 15) == Decimal("85.00")
