import math
import unittest

import calc
from calc import errors

VALUES = {
    "existing_precedence": ("1 + 2 * 3", None, 7),
    "existing_parentheses": ("(1 + 2) * 3", None, 9),
    "existing_division": ("7 / 2", None, 3.5),
    "decimal": ("3.25 * 2", None, 6.5),
    "leading_and_trailing_dot": (".5 + 2.", None, 2.5),
    "scientific": ("1e3 + 2.5E-2", None, 1e3 + 2.5e-2),
    "unary_minus": ("-3 + 5", None, 2),
    "repeated_unary": ("--3 * +-+2", None, -6),
    "unary_after_operator": ("2 * -3", None, -6),
    "power_right_associative": ("2^3^2", None, 512),
    "power_binds_tighter_than_unary": ("-2^2", None, -4),
    "negative_exponent": ("2^-1", None, 0.5),
    "parenthesized_negative_base": ("(-2)^2", None, 4),
    "variables": ("x * y + 1", {"x": 2, "y": 3.5}, 8.0),
    "underscore_names": ("_a1 + 1", {"_a1": 1}, 2),
    "min_max_varargs": ("max(1, 5, 3) - min(4)", None, 1),
    "abs": ("abs(-2.5)", None, 2.5),
    "nested_calls": ("max(abs(-7), min(2, x))", {"x": 10}, 7),
    "whitespace_everywhere": ("  max ( 1 , 2 )  ^ 2 ", None, 4),
}

ERRORS = {
    "incomplete": ("1 +", None, "ParseError", 3),
    "missing_paren": ("(1+2", None, "ParseError", 4),
    "unexpected_operator": ("1 + * 2", None, "ParseError", 4),
    "bad_character": ("2 $ 3", None, "ParseError", 2),
    "leftover_token": ("2x", None, "ParseError", 1),
    "trailing_comma": ("min(1,)", None, "ParseError", 6),
    "empty": ("", None, "ParseError", 0),
    "blank": ("   ", None, "ParseError", 3),
    "unknown_variable": ("y + 1", None, "UnknownNameError", 0),
    "unknown_variable_with_env": ("x + z", {"x": 1}, "UnknownNameError", 4),
    "unknown_function": ("1 + foo(2)", None, "UnknownNameError", 4),
    "abs_arity": ("abs(1, 2)", None, "ArgumentError", 0),
    "min_needs_argument": ("2 * min()", None, "ArgumentError", 4),
    "division_by_zero": ("1 / (2 - 2)", None, "DivisionByZeroError", 2),
    "zero_to_negative_power": ("0 ^ -1", None, "DivisionByZeroError", 2),
    "nested_division_position": ("max(1, 2/0)", None, "DivisionByZeroError", 8),
}


def run(expr, env):
    return calc.evaluate(expr) if env is None else calc.evaluate(expr, env)


def value_test(expr, env, expected):
    def test(self):
        result = run(expr, env)
        if isinstance(expected, float):
            self.assertIsInstance(result, float)
            self.assertTrue(math.isclose(result, expected, rel_tol=1e-12), f"{expr!r} gave {result!r}")
        else:
            self.assertEqual(result, expected)
    return test


def error_test(expr, env, name, position):
    def test(self):
        error_class = getattr(errors, name)
        with self.assertRaises(error_class) as caught:
            run(expr, env)
        self.assertEqual(caught.exception.position, position)
    return test


class HiddenCalc(unittest.TestCase):
    def test_literal_types(self):
        self.assertIs(type(calc.evaluate("3")), int)
        self.assertIs(type(calc.evaluate("3.0")), float)
        self.assertIs(type(calc.evaluate("1e3")), float)

    def test_errors_exported(self):
        for name in ("ParseError", "UnknownNameError", "ArgumentError", "DivisionByZeroError"):
            self.assertTrue(issubclass(getattr(errors, name), errors.CalcError))
            self.assertIs(getattr(calc, name), getattr(errors, name))


for key, case in VALUES.items():
    setattr(HiddenCalc, f"test_value_{key}", value_test(*case))
for key, case in ERRORS.items():
    setattr(HiddenCalc, f"test_error_{key}", error_test(*case))
