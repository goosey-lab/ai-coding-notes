from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    sku: str
    name: str
    unit_price_cents: int


@dataclass
class LineItem:
    item: Item
    quantity: int
