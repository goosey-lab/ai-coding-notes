import unittest
from datetime import date
from decimal import Decimal

from ledger import balance_between, monthly_fee, parse_line


class LedgerTest(unittest.TestCase):
    def test_parse_simple(self):
        self.assertEqual(parse_line("2024-03-01,Book,-12.99"), (date(2024, 3, 1), "Book", Decimal("-12.99")))

    def test_parse_quoted_amount(self):
        self.assertEqual(parse_line('2024-03-02,Rent,"-1,200.00"'), (date(2024, 3, 2), "Rent", Decimal("-1200.00")))

    def test_balance_whole_month(self):
        txns = [parse_line("2024-03-01,A,10"), parse_line("2024-03-15,B,5"), parse_line("2024-03-31,C,1")]
        self.assertEqual(balance_between(txns, date(2024, 3, 1), date(2024, 3, 31)), Decimal("16"))

    def test_fee_minimum(self):
        self.assertEqual(monthly_fee(Decimal("20")), Decimal("1.00"))


if __name__ == "__main__":
    unittest.main()
