import unittest
from datetime import date
from decimal import Decimal

import ledger

P = ledger.parse_line


class HiddenLedger(unittest.TestCase):
    def test_parse_simple(self):
        self.assertEqual(P("2024-01-05,Coffee,-3.50"), (date(2024, 1, 5), "Coffee", Decimal("-3.50")))

    def test_parse_quoted_thousands(self):
        self.assertEqual(P('2024-01-05,Rent,"-1,200.50"'), (date(2024, 1, 5), "Rent", Decimal("-1200.50")))

    def test_parse_field_whitespace(self):
        self.assertEqual(P('  2024-02-29 , Salary , "2,000"  \n'), (date(2024, 2, 29), "Salary", Decimal("2000")))

    def test_balance_inclusive_both_ends(self):
        tx = [P("2024-03-01,A,10"), P("2024-03-10,B,5"), P("2024-03-31,C,1"),
              P("2024-04-01,D,100"), P("2024-02-29,E,1000")]
        self.assertEqual(ledger.balance_between(tx, date(2024, 3, 1), date(2024, 3, 31)), Decimal("16"))

    def test_balance_single_day(self):
        tx = [P("2024-03-10,B,5"), P("2024-03-11,C,7")]
        self.assertEqual(ledger.balance_between(tx, date(2024, 3, 10), date(2024, 3, 10)), Decimal("5"))

    def test_fee_threshold_is_free(self):
        self.assertEqual(ledger.monthly_fee(Decimal("5000.00")), Decimal("0.00"))

    def test_fee_just_below_threshold(self):
        self.assertEqual(ledger.monthly_fee(Decimal("4999.99")), Decimal("75.00"))

    def test_fee_rounds_half_up(self):
        self.assertEqual(ledger.monthly_fee(Decimal("1033.00")), Decimal("15.50"))

    def test_fee_negative_balance_uses_absolute_value(self):
        self.assertEqual(ledger.monthly_fee(Decimal("-200")), Decimal("3.00"))

    def test_fee_large_negative_balance_is_charged(self):
        self.assertEqual(ledger.monthly_fee(Decimal("-6000")), Decimal("90.00"))

    def test_fee_minimum_for_zero(self):
        self.assertEqual(ledger.monthly_fee(Decimal("0")), Decimal("1.00"))

    def test_fee_is_decimal_with_cents(self):
        fee = ledger.monthly_fee(Decimal("100"))
        self.assertIsInstance(fee, Decimal)
        self.assertEqual(str(fee), "1.50")
