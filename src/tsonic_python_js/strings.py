"""UTF-16 string helpers for JavaScript compatibility."""

import math


def utf16_code_units(value: str) -> tuple[int, ...]:
    """Return the JavaScript UTF-16 code-unit view of a Python string."""

    raw = value.encode("utf-16-le", "surrogatepass")
    return tuple(raw[index] | (raw[index + 1] << 8) for index in range(0, len(raw), 2))


def _from_code_units(units: tuple[int, ...]) -> str:
    raw = bytearray()
    for unit in units:
        raw.append(unit & 0xFF)
        raw.append((unit >> 8) & 0xFF)
    return bytes(raw).decode("utf-16-le", "surrogatepass")


def utf16_len(value: str) -> int:
    """Return JavaScript string length in UTF-16 code units."""

    return len(utf16_code_units(value))


def char_at(value: str, index: int) -> str:
    """Return the one-code-unit JS charAt result, or an empty string."""

    units = utf16_code_units(value)
    if index < 0 or index >= len(units):
        return ""
    return _from_code_units((units[index],))


def char_code_at(value: str, index: int) -> float:
    """Return JS charCodeAt, using NaN for out-of-range indexes."""

    units = utf16_code_units(value)
    if index < 0 or index >= len(units):
        return math.nan
    return float(units[index])


def js_slice_indices(length: int, start: int = 0, end: int | None = None) -> tuple[int, int]:
    """Normalize JavaScript Array/String slice indexes for a known length."""

    normalized_start = min(max(length + start if start < 0 else start, 0), length)
    raw_end = length if end is None else end
    normalized_end = min(max(length + raw_end if raw_end < 0 else raw_end, 0), length)
    return normalized_start, max(normalized_end, normalized_start)
