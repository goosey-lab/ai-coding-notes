"""Half-open integer spans and calendar helpers.

A ``Span(start, end)`` covers the integers ``start <= t < end``. Spans must be
non-empty, so ``start < end`` is required. Unless stated otherwise, functions
accept spans in any order, possibly overlapping, and never modify their input.
"""
from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Span:
    start: int
    end: int

    def __post_init__(self):
        if self.start > self.end:
            raise ValueError(f"invalid span [{self.start}, {self.end})")

    @property
    def length(self):
        return self.end - self.start


def normalize(spans):
    """Return the union of ``spans`` as a list of disjoint spans sorted by start.

    Spans that overlap or touch (one ends exactly where the next one starts)
    are merged into a single span.
    """
    ordered = []
    for span in spans:
        index = 0
        while index < len(ordered) and ordered[index].start < span.start:
            index += 1
        ordered.insert(index, span)
    merged = []
    for span in ordered:
        if merged and span.start < merged[-1].end:
            merged[-1] = Span(merged[-1].start, span.end)
        else:
            merged.append(span)
    return merged


def total_length(spans):
    """Return the number of integers covered by at least one of ``spans``."""
    return sum(span.length for span in spans)


def subtract(spans, cut):
    """Return ``normalize(spans)`` with every integer covered by ``cut`` removed."""
    result = []
    for span in normalize(spans):
        if span.end <= cut.start or span.start >= cut.end:
            result.append(span)
        elif span.start < cut.start:
            result.append(Span(span.start, cut.start))
        elif span.end > cut.end:
            result.append(Span(cut.end, span.end))
    return result


def free_slots(busy, window, min_length=1):
    """Return the maximal gaps inside ``window`` not covered by any ``busy`` span.

    The gaps are sorted by start, and only gaps whose length is at least
    ``min_length`` are returned.
    """
    slots = []
    cursor = window.start
    for span in normalize(busy):
        if span.start > cursor:
            slots.append(Span(cursor, span.start))
        cursor = max(cursor, span.end)
    if cursor < window.end:
        slots.append(Span(cursor, window.end))
    return [slot for slot in slots if slot.length > min_length]


def find_slot(calendars, window, duration):
    """Return the earliest ``Span(t, t + duration)`` inside ``window`` that overlaps
    no busy span of any calendar, or None if there is no such span.

    ``calendars`` is a list of calendars, each an iterable of busy spans; with no
    calendars the whole window is free. ``duration`` must be positive, otherwise
    ValueError is raised.
    """
    for slot in free_slots(calendars[0], window, duration):
        start = slot.start
        if all(not any(b.start < start + duration and start < b.end for b in calendar)
               for calendar in calendars[1:]):
            return Span(start, start + duration)
    return None
