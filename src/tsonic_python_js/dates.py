"""UTC epoch-millisecond JS Date carrier and Date static helpers.

``date_parse`` accepts the same closed UTC ISO-8601 subset as the Rust
runtime's ``date::JsDate::parse``: ``YYYY-MM-DDTHH:MM:SS[.fff]Z`` with
digit-only fields, month 1-12, day 1-31, hour 0-23, minute/second 0-59, and
at most the first three fraction digits significant. Failure is signalled
with NaN (the runtime's Python-native NaN convention from numbers.py), where
the Rust twin raises its RangeError; Rust's extra raw-numeric-string
acceptance is not part of this closed subset.
"""

import math
import time
from datetime import UTC, datetime

from tsonic_python_js.errors import JsRangeError

_MS_PER_DAY = 86_400_000


class JsDate:
    __slots__ = ("_epoch_ms",)
    _epoch_ms: float

    def __init__(self, epoch_ms: int | float) -> None:
        self._epoch_ms = float(epoch_ms)

    @classmethod
    def now(cls) -> "JsDate":
        return cls(datetime.now(UTC).timestamp() * 1000.0)

    @classmethod
    def parse(cls, value: str) -> "JsDate":
        text = value
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as error:
            raise JsRangeError("invalid date") from error
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return cls(parsed.timestamp() * 1000.0)

    def get_time(self) -> float:
        return self._epoch_ms

    def to_iso_string(self) -> str:
        if not math.isfinite(self._epoch_ms):
            raise JsRangeError("invalid time value")
        dt = datetime.fromtimestamp(self._epoch_ms / 1000.0, UTC)
        millis = int(dt.microsecond / 1000)
        return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{millis:03d}Z"

    def get_utc_full_year(self) -> int:
        return datetime.fromtimestamp(self._epoch_ms / 1000.0, UTC).year

    def get_utc_month(self) -> int:
        return datetime.fromtimestamp(self._epoch_ms / 1000.0, UTC).month - 1

    def get_utc_date(self) -> int:
        return datetime.fromtimestamp(self._epoch_ms / 1000.0, UTC).day


def date_now() -> float:
    """Return JS Date.now(): whole milliseconds since the Unix epoch."""

    return float(time.time_ns() // 1_000_000)


def date_parse(value: str) -> float:
    """Parse the closed UTC ISO-8601 subset to epoch milliseconds, NaN otherwise."""

    text = value.strip()
    if not text.endswith("Z"):
        return math.nan
    date_text, separator, time_text = text[:-1].partition("T")
    if not separator:
        return math.nan
    date_fields = date_text.split("-")
    time_fields = time_text.split(":")
    if len(date_fields) != 3 or len(time_fields) != 3:
        return math.nan
    second_text, _, fraction = time_fields[2].partition(".")
    fields = [*date_fields[:3], time_fields[0], time_fields[1], second_text]
    millis_text = fraction[:3].ljust(3, "0")
    if not all(_is_ascii_digits(field) for field in [*fields, millis_text]):
        return math.nan
    year, month, day, hour, minute, second = (int(field) for field in fields)
    valid = 1 <= month <= 12 and 1 <= day <= 31 and hour <= 23 and minute <= 59 and second <= 59
    if not valid:
        return math.nan
    total_millis = (
        _days_from_civil(year, month, day) * _MS_PER_DAY
        + hour * 3_600_000
        + minute * 60_000
        + second * 1_000
        + int(millis_text)
    )
    return float(total_millis)


def _is_ascii_digits(text: str) -> bool:
    return text != "" and all("0" <= char <= "9" for char in text)


def _days_from_civil(year: int, month: int, day: int) -> int:
    """Days since 1970-01-01 in the proleptic Gregorian calendar."""

    shifted_year = year - (1 if month <= 2 else 0)
    era = (shifted_year if shifted_year >= 0 else shifted_year - 399) // 400
    year_of_era = shifted_year - era * 400
    day_of_year = (153 * (month + (-3 if month > 2 else 9)) + 2) // 5 + day - 1
    day_of_era = year_of_era * 365 + year_of_era // 4 - year_of_era // 100 + day_of_year
    return era * 146_097 + day_of_era - 719_468
