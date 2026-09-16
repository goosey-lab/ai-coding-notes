import random
import signal
import unittest

from spans import Span, find_slot, free_slots, normalize, subtract, total_length

LIMIT_SECONDS = 15


class TimeLimit:
    def __enter__(self):
        def expire(signum, frame):
            raise TimeoutError(f"took longer than {LIMIT_SECONDS} s")
        self.previous = signal.signal(signal.SIGALRM, expire)
        signal.setitimer(signal.ITIMER_REAL, LIMIT_SECONDS)

    def __exit__(self, *exc):
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, self.previous)
        return False


def oracle_union(spans):
    merged = []
    for start, end in sorted((s.start, s.end) for s in spans):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [Span(s, e) for s, e in merged]


def oracle_gaps(busy, window):
    gaps, cursor = [], window.start
    for span in oracle_union(busy):
        if span.end <= cursor:
            continue
        if span.start >= window.end:
            break
        if span.start > cursor:
            gaps.append(Span(cursor, span.start))
        cursor = max(cursor, span.end)
    if cursor < window.end:
        gaps.append(Span(cursor, window.end))
    return gaps


RNG = random.Random(20260916)
BIG = [Span(s, s + RNG.randint(1, 100)) for s in (RNG.randrange(0, 10_000_000) for _ in range(100_000))]
BIG_WINDOW = Span(0, 10_000_000)


class HiddenSpans(unittest.TestCase):
    def test_span_rejects_empty(self):
        with self.assertRaises(ValueError):
            Span(3, 3)

    def test_span_rejects_reversed(self):
        with self.assertRaises(ValueError):
            Span(4, 3)

    def test_normalize_touching(self):
        self.assertEqual(normalize([Span(3, 5), Span(1, 3)]), [Span(1, 5)])

    def test_normalize_contained(self):
        self.assertEqual(normalize([Span(0, 10), Span(2, 3)]), [Span(0, 10)])

    def test_normalize_unsorted_chain(self):
        data = [Span(8, 9), Span(0, 2), Span(1, 5), Span(5, 6), Span(10, 12)]
        self.assertEqual(normalize(data), [Span(0, 6), Span(8, 9), Span(10, 12)])

    def test_normalize_keeps_input(self):
        data = [Span(4, 6), Span(0, 5)]
        normalize(data)
        self.assertEqual(data, [Span(4, 6), Span(0, 5)])

    def test_normalize_empty(self):
        self.assertEqual(normalize([]), [])

    def test_total_length_counts_overlap_once(self):
        self.assertEqual(total_length([Span(0, 10), Span(5, 15), Span(20, 21)]), 16)

    def test_total_length_duplicates(self):
        self.assertEqual(total_length([Span(1, 4), Span(1, 4), Span(1, 4)]), 3)

    def test_subtract_splits_inside(self):
        self.assertEqual(subtract([Span(0, 10)], Span(3, 5)), [Span(0, 3), Span(5, 10)])

    def test_subtract_across_spans(self):
        self.assertEqual(subtract([Span(0, 5), Span(7, 12), Span(15, 20)], Span(3, 17)),
                         [Span(0, 3), Span(17, 20)])

    def test_subtract_normalizes_untouched_spans(self):
        self.assertEqual(subtract([Span(4, 6), Span(0, 2), Span(2, 3)], Span(10, 11)), [Span(0, 3), Span(4, 6)])

    def test_subtract_everything(self):
        self.assertEqual(subtract([Span(2, 4), Span(5, 6)], Span(0, 10)), [])

    def test_free_slots_basic(self):
        self.assertEqual(free_slots([Span(3, 5)], Span(0, 10)), [Span(0, 3), Span(5, 10)])

    def test_free_slots_min_length_is_inclusive(self):
        self.assertEqual(free_slots([Span(3, 5)], Span(0, 10), 3), [Span(0, 3), Span(5, 10)])
        self.assertEqual(free_slots([Span(3, 5)], Span(0, 10), 4), [Span(5, 10)])

    def test_free_slots_clipped_to_window(self):
        self.assertEqual(free_slots([Span(-5, 2), Span(8, 30)], Span(0, 10)), [Span(2, 8)])

    def test_free_slots_busy_after_window(self):
        self.assertEqual(free_slots([Span(20, 30)], Span(0, 10)), [Span(0, 10)])

    def test_free_slots_length_one_gap(self):
        self.assertEqual(free_slots([Span(0, 4), Span(5, 10)], Span(0, 10)), [Span(4, 5)])

    def test_find_slot_starts_inside_gap(self):
        self.assertEqual(find_slot([[Span(0, 2)], [Span(3, 4)]], Span(0, 10), 2), Span(4, 6))

    def test_find_slot_exact_fit(self):
        self.assertEqual(find_slot([[Span(0, 4)], [Span(6, 10)]], Span(0, 10), 2), Span(4, 6))

    def test_find_slot_none(self):
        self.assertIsNone(find_slot([[Span(0, 5)], [Span(5, 10)]], Span(0, 10), 1))

    def test_find_slot_no_calendars(self):
        self.assertEqual(find_slot([], Span(5, 20), 3), Span(5, 8))

    def test_find_slot_longer_than_window(self):
        self.assertIsNone(find_slot([], Span(0, 5), 6))

    def test_find_slot_rejects_non_positive_duration(self):
        for duration in (0, -1):
            with self.subTest(duration=duration):
                with self.assertRaises(ValueError):
                    find_slot([[Span(0, 1)]], Span(0, 10), duration)

    def test_perf_normalize(self):
        expected = oracle_union(BIG)
        with TimeLimit():
            result = normalize(BIG)
        self.assertEqual(result, expected)

    def test_perf_total_length(self):
        expected = sum(s.length for s in oracle_union(BIG))
        with TimeLimit():
            result = total_length(BIG)
        self.assertEqual(result, expected)

    def test_perf_subtract(self):
        cut = Span(2_500_000, 7_500_000)
        expected = [s for s in oracle_union(BIG) if s.end <= cut.start or s.start >= cut.end]
        for s in oracle_union(BIG):
            if s.start < cut.start < s.end:
                expected.append(Span(s.start, cut.start))
            if s.start < cut.end < s.end:
                expected.append(Span(cut.end, s.end))
        expected.sort()
        with TimeLimit():
            result = subtract(BIG, cut)
        self.assertEqual(result, expected)

    def test_perf_free_slots(self):
        expected = [g for g in oracle_gaps(BIG, BIG_WINDOW) if g.length >= 50]
        with TimeLimit():
            result = free_slots(BIG, BIG_WINDOW, 50)
        self.assertEqual(result, expected)

    def test_perf_find_slot(self):
        calendars = [BIG[i::50] for i in range(50)]
        gap = next((g for g in oracle_gaps(BIG, BIG_WINDOW) if g.length >= 300), None)
        expected = Span(gap.start, gap.start + 300) if gap else None
        with TimeLimit():
            result = find_slot(calendars, BIG_WINDOW, 300)
        self.assertEqual(result, expected)
