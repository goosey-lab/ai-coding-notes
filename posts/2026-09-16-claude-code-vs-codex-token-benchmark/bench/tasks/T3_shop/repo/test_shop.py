import unittest

from shop import Cart, Item
from shop.report import summary

PEN = Item("P1", "Pen", 150)


class ShopTest(unittest.TestCase):
    def test_bulk_discount(self):
        cart = Cart()
        cart.add(PEN, 10)
        self.assertEqual(cart.total_cents(), 1425)

    def test_add_merges_same_sku(self):
        cart = Cart()
        cart.add(PEN)
        cart.add(PEN, 2)
        self.assertEqual(len(cart.lines), 1)
        self.assertEqual(cart.lines[0].quantity, 3)

    def test_summary(self):
        cart = Cart()
        cart.add(PEN, 2)
        self.assertEqual(summary(cart), "2 x Pen: $3.00\nTotal: $3.00")


if __name__ == "__main__":
    unittest.main()
