import unittest

from durations import format_duration, parse_duration


class DurationExamples(unittest.TestCase):
    def test_parse_examples(self):
        self.assertEqual(parse_duration("1h30m"), 5400)
        self.assertEqual(parse_duration("90"), 90)

    def test_format_examples(self):
        self.assertEqual(format_duration(3690), "1h1m30s")
        self.assertEqual(format_duration(0), "0s")


if __name__ == "__main__":
    unittest.main()
