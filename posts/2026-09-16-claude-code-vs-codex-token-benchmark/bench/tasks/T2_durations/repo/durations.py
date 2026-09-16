"""Human-readable durations.

parse_duration(text) -> int (seconds)
  * The text is one or more components ``<non-negative integer><unit>``.
    Units: w (week, 604800 s), d (86400 s), h (3600 s), m (60 s), s (1 s).
  * Units are case-insensitive. Components may be separated by optional
    whitespace, and leading/trailing whitespace is ignored:
    "1h30m", "1h 30m" and " 2D " are all valid.
  * Each unit may appear at most once, and units must appear in descending
    order (w, d, h, m, s): "30m1h" and "1h1h" are invalid.
  * A bare integer with no unit means seconds: "90" -> 90.
  * Anything else raises ValueError, including empty or whitespace-only text,
    negative numbers, decimals and unknown units.

format_duration(seconds) -> str
  * The inverse of parse_duration: largest units first, no spaces, zero
    components omitted, e.g. 3690 -> "1h1m30s" and 86400 -> "1d".
  * 0 -> "0s".
  * Negative numbers and anything that is not an int raise ValueError
    (bool is not accepted as an int).
"""


def parse_duration(text):
    raise NotImplementedError


def format_duration(seconds):
    raise NotImplementedError
