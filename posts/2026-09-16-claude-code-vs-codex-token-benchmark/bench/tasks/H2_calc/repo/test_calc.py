import unittest

from calc import CalcError, evaluate


class CalcTest(unittest.TestCase):
    def test_precedence(self):
        self.assertEqual(evaluate("1 + 2 * 3"), 7)

    def test_parentheses(self):
        self.assertEqual(evaluate("(1 + 2) * 3"), 9)

    def test_division(self):
        self.assertEqual(evaluate("7 / 2"), 3.5)

    def test_incomplete_expression(self):
        with self.assertRaises(CalcError):
            evaluate("1 +")


if __name__ == "__main__":
    unittest.main()
