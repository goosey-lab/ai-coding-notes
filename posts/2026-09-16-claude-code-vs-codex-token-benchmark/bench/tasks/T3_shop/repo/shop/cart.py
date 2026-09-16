from .models import LineItem
from .pricing import line_total_cents


class Cart:
    def __init__(self):
        self.lines = []

    def add(self, item, quantity=1):
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        for line in self.lines:
            if line.item.sku == item.sku:
                line.quantity += quantity
                return
        self.lines.append(LineItem(item, quantity))

    def subtotal_cents(self):
        return sum(line_total_cents(line) for line in self.lines)

    def total_cents(self):
        return self.subtotal_cents()
