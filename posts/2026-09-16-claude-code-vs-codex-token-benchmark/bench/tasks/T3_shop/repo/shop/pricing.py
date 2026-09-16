"""Per-line pricing rules."""

BULK_THRESHOLD = 10
BULK_DISCOUNT_PERCENT = 5


def line_total_cents(line):
    """Price of a line item in cents, with the bulk discount (rounded down) applied."""
    total = line.item.unit_price_cents * line.quantity
    if line.quantity >= BULK_THRESHOLD:
        total -= total * BULK_DISCOUNT_PERCENT // 100
    return total
