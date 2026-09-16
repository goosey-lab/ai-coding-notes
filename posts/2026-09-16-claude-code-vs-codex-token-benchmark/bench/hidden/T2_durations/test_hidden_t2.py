import unittest

from durations import format_duration as fmt
from durations import parse_duration as parse


class HiddenDurations(unittest.TestCase):
    def test_single_units(self):
        self.assertEqual([parse("1w"), parse("2d"), parse("3h"), parse("4m"), parse("5s")],
                         [604800, 172800, 10800, 240, 5])

    def test_all_units_combined(self):
        self.assertEqual(parse("1w2d3h4m5s"), 604800 + 172800 + 10800 + 240 + 5)

    def test_whitespace_and_case(self):
        self.assertEqual(parse(" 1H 30M "), 5400)
        self.assertEqual(parse(" 2D "), 172800)

    def test_bare_integer_is_seconds(self):
        self.assertEqual(parse("90"), 90)
        self.assertEqual(parse("0"), 0)

    def test_zero_components_and_large_numbers(self):
        self.assertEqual(parse("0s"), 0)
        self.assertEqual(parse("1h0m"), 3600)
        self.assertEqual(parse("100m"), 6000)

    def test_invalid_text(self):
        for bad in ["", "   ", "30m1h", "1h1h", "1.5h", "-5s", "5x", "h", "abc", "1h-30m"]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    parse(bad)

    def test_format(self):
        self.assertEqual(fmt(3690), "1h1m30s")
        self.assertEqual(fmt(0), "0s")
        self.assertEqual(fmt(604805), "1w5s")
        self.assertEqual(fmt(59), "59s")
        self.assertEqual(fmt(86400), "1d")

    def test_format_invalid(self):
        for bad in [-1, 1.5, True, "10"]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    fmt(bad)

    def test_round_trip(self):
        for n in [0, 1, 59, 60, 61, 3599, 3600, 86399, 90061, 1213261]:
            with self.subTest(n=n):
                self.assertEqual(parse(fmt(n)), n)
