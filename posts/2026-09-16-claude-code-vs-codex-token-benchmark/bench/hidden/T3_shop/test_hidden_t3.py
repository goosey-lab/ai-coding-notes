import dataclasses
import unittest

import shop
from shop import report
from shop.cart import Cart
from shop.models import Coupon, Item

PEN = Item("P1", "Pen", 150)
BOOK = Item("B1", "Book", 1999)


def cart_with(*lines):
    cart = Cart()
    for item, quantity in lines:
        cart.add(item, quantity)
    return cart


class HiddenCoupons(unittest.TestCase):
    def test_exported_from_package(self):
        self.assertIs(shop.Coupon, Coupon)

    def test_coupon_is_frozen_with_default_minimum(self):
        coupon = Coupon("SAVE10", 10)
        self.assertEqual(coupon.min_subtotal_cents, 0)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            coupon.percent_off = 20

    def test_percent_validation(self):
        for bad in [0, 101, -5]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    Coupon("X", bad)
        Coupon("ONE", 1)
        Coupon("ALL", 100)

    def test_no_coupon(self):
        cart = cart_with((PEN, 2))
        self.assertEqual(cart.discount_cents(), 0)
        self.assertEqual(cart.total_cents(), 300)

    def test_discount_after_bulk_rounded_down(self):
        cart = cart_with((PEN, 10), (BOOK, 1))
        cart.apply_coupon(Coupon("SAVE15", 15))
        self.assertEqual(cart.subtotal_cents(), 3424)
        self.assertEqual(cart.discount_cents(), 513)
        self.assertEqual(cart.total_cents(), 2911)

    def test_replace_and_remove(self):
        cart = cart_with((BOOK, 1))
        cart.apply_coupon(Coupon("A", 10))
        cart.apply_coupon(Coupon("B", 50))
        self.assertEqual(cart.discount_cents(), 999)
        cart.remove_coupon()
        self.assertEqual(cart.discount_cents(), 0)
        self.assertEqual(cart.total_cents(), 1999)

    def test_minimum_subtotal_boundary(self):
        cart = cart_with((PEN, 2))
        cart.apply_coupon(Coupon("BIG", 10, min_subtotal_cents=301))
        self.assertEqual(cart.discount_cents(), 0)
        cart.apply_coupon(Coupon("EQ", 10, min_subtotal_cents=300))
        self.assertEqual(cart.discount_cents(), 30)

    def test_full_discount(self):
        cart = cart_with((PEN, 1))
        cart.apply_coupon(Coupon("FREE", 100))
        self.assertEqual(cart.total_cents(), 0)

    def test_summary_with_coupon(self):
        cart = cart_with((PEN, 10), (BOOK, 1))
        cart.apply_coupon(Coupon("SAVE15", 15))
        self.assertEqual(report.summary(cart),
                         "10 x Pen: $14.25\n1 x Book: $19.99\nCoupon SAVE15: -$5.13\nTotal: $29.11")

    def test_summary_without_coupon_unchanged(self):
        cart = cart_with((PEN, 2))
        self.assertEqual(report.summary(cart), "2 x Pen: $3.00\nTotal: $3.00")

    def test_summary_zero_discount_has_no_coupon_line(self):
        cart = cart_with((PEN, 2))
        cart.apply_coupon(Coupon("BIG", 10, min_subtotal_cents=10000))
        self.assertEqual(report.summary(cart), "2 x Pen: $3.00\nTotal: $3.00")
