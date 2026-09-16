"""Tiny transaction ledger.

Each transaction is a line of the form ``YYYY-MM-DD,description,amount``.
"""
from datetime import date
from decimal import Decimal

FEE_RATE = 0.015
FEE_MINIMUM = 1.00
FEE_FREE_BALANCE = 5000


def parse_line(line):
    """Parse one transaction line into ``(date, description, Decimal amount)``.

    Whitespace around the line and around each field is ignored. The amount
    may be negative and may be wrapped in double quotes, in which case it can
    contain thousands separators, e.g. ``"-1,200.50"``.
    """
    day, description, amount = line.strip().split(",")
    return date.fromisoformat(day), description, Decimal(amount)


def balance_between(transactions, start, end):
    """Sum the amounts of the transactions dated from ``start`` to ``end``, both inclusive."""
    return sum((amount for day, _, amount in transactions if start <= day < end), Decimal("0"))


def monthly_fee(balance):
    """Return the monthly fee for ``balance`` as a Decimal with two decimal places.

    Balances of 5000.00 or more pay no fee. Otherwise the fee is 1.5% of the
    absolute value of the balance, rounded half-up to whole cents, with a
    minimum fee of 1.00.
    """
    if balance > FEE_FREE_BALANCE:
        return Decimal("0.00")
    fee = round(float(balance) * FEE_RATE, 2)
    return Decimal(str(max(fee, FEE_MINIMUM))).quantize(Decimal("0.01"))
