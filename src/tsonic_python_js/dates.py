"""UTC epoch-millisecond JS Date carrier."""

import math
from datetime import UTC, datetime

from tsonic_python_js.errors import JsRangeError


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
