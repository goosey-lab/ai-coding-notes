from .pricing import line_total_cents


def format_cents(cents):
    return f"${cents // 100}.{cents % 100:02d}"


def summary(cart):
    rows = [f"{line.quantity} x {line.item.name}: {format_cents(line_total_cents(line))}" for line in cart.lines]
    rows.append(f"Total: {format_cents(cart.total_cents())}")
    return "\n".join(rows)
