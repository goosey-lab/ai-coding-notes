import unittest

from spans import Span, find_slot, normalize, subtract, total_length


class SpanExamples(unittest.TestCase):
    def test_normalize_overlapping(self):
        self.assertEqual(normalize([Span(5, 7), Span(1, 3), Span(2, 4)]), [Span(1, 4), Span(5, 7)])

    def test_normalize_touching(self):
        self.assertEqual(normalize([Span(1, 3), Span(3, 5)]), [Span(1, 5)])

    def test_total_length(self):
        self.assertEqual(total_length([Span(0, 10), Span(5, 15)]), 15)

    def test_subtract(self):
        self.assertEqual(subtract([Span(0, 10)], Span(3, 5)), [Span(0, 3), Span(5, 10)])

    def test_find_slot(self):
        self.assertEqual(find_slot([[Span(0, 2)], [Span(3, 4)]], Span(0, 10), 2), Span(4, 6))


if __name__ == "__main__":
    unittest.main()
