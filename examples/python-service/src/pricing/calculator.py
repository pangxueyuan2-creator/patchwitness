from decimal import Decimal


def discounted_price(price: Decimal, discount_percent: int) -> Decimal:
    if price < 0:
        raise ValueError("price cannot be negative")
    if not 0 <= discount_percent <= 100:
        raise ValueError("discount percent must be between 0 and 100")
    multiplier = Decimal(100 - discount_percent) / Decimal(100)
    return (price * multiplier).quantize(Decimal("0.01"))

