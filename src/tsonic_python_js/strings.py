"""UTF-16 string helpers for JavaScript compatibility.

Case conversion notes: ``to_upper_case``/``to_lower_case`` use Python's
``str.upper()``/``str.lower()`` — the Unicode default full case mappings,
including the conditional Final_Sigma rule — mirroring the Rust runtime's use
of its standard-library default mappings. No locale-sensitive variants are
offered. Divergence from a JS engine is limited to Unicode-version skew
between CPython's bundled tables and the engine's; unpaired surrogate code
units have no case mapping and pass through unchanged in both.
"""

import math

from tsonic_python_js.errors import JsRangeError
from tsonic_python_js.values import undefined


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


def at(value: str, index: int) -> object:
    """Return JS String.prototype.at: one code unit, negative from the end.

    Returns the undefined sentinel when the normalized index is out of range.
    """

    units = utf16_code_units(value)
    normalized = len(units) + index if index < 0 else index
    if normalized < 0 or normalized >= len(units):
        return undefined
    return _from_code_units((units[normalized],))


def char_code_at(value: str, index: int) -> float:
    """Return JS charCodeAt, using NaN for out-of-range indexes."""

    units = utf16_code_units(value)
    if index < 0 or index >= len(units):
        return math.nan
    return float(units[index])


def code_point_at(value: str, index: int) -> object:
    """Return JS codePointAt: combines surrogate pairs, undefined out of range."""

    units = utf16_code_units(value)
    if index < 0 or index >= len(units):
        return undefined
    first = units[index]
    if 0xD800 <= first <= 0xDBFF and index + 1 < len(units):
        second = units[index + 1]
        if 0xDC00 <= second <= 0xDFFF:
            return float(((first - 0xD800) << 10) + (second - 0xDC00) + 0x10000)
    return float(first)


def js_slice_indices(length: int, start: int = 0, end: int | None = None) -> tuple[int, int]:
    """Normalize JavaScript Array/String slice indexes for a known length."""

    normalized_start = min(max(length + start if start < 0 else start, 0), length)
    raw_end = length if end is None else end
    normalized_end = min(max(length + raw_end if raw_end < 0 else raw_end, 0), length)
    return normalized_start, max(normalized_end, normalized_start)


def string_slice(value: str, start: int = 0, end: int | None = None) -> str:
    units = utf16_code_units(value)
    from_index, to_index = js_slice_indices(len(units), start, end)
    return _from_code_units(units[from_index:to_index])


def substring(value: str, start: int = 0, end: int | None = None) -> str:
    length = utf16_len(value)
    start_index = min(max(start, 0), length)
    end_index = length if end is None else min(max(end, 0), length)
    if start_index > end_index:
        start_index, end_index = end_index, start_index
    return string_slice(value, start_index, end_index)


def substr(value: str, start: int = 0, length: int | None = None) -> str:
    size = utf16_len(value)
    from_index = max(size + start, 0) if start < 0 else min(start, size)
    count = size - from_index if length is None else max(length, 0)
    return string_slice(value, from_index, from_index + count)


def index_of(value: str, search: str, position: int = 0) -> int:
    units = utf16_code_units(value)
    needle = utf16_code_units(search)
    start = min(max(position, 0), len(units))
    if not needle:
        return start
    for index in range(start, len(units) - len(needle) + 1):
        if units[index : index + len(needle)] == needle:
            return index
    return -1


def last_index_of(value: str, search: str, position: int | None = None) -> int:
    units = utf16_code_units(value)
    needle = utf16_code_units(search)
    start = len(units) if position is None else min(max(position, 0), len(units))
    if not needle:
        return start
    for index in range(min(start, len(units) - len(needle)), -1, -1):
        if units[index : index + len(needle)] == needle:
            return index
    return -1


def includes(value: str, search: str, position: int = 0) -> bool:
    return index_of(value, search, position) != -1


def starts_with(value: str, search: str, position: int = 0) -> bool:
    start = min(max(position, 0), utf16_len(value))
    return index_of(value, search, start) == start


def ends_with(value: str, search: str, end_position: int | None = None) -> bool:
    end = utf16_len(value) if end_position is None else min(max(end_position, 0), utf16_len(value))
    needle_len = utf16_len(search)
    start = end - needle_len
    return start >= 0 and string_slice(value, start, end) == search


def concat(value: str, *parts: str) -> str:
    """Return JS String.prototype.concat over already-string arguments."""

    return "".join((value, *parts))


def replace(value: str, search: str, replacement: str) -> str:
    """Replace the first occurrence of a literal search string, JS-style.

    No pattern semantics. The replacement honors the JS GetSubstitution
    tokens defined for a string search with no capture groups: ``$$``
    (literal ``$``), ``$&`` (the matched text), dollar-backtick (text before
    the match), and ``$'`` (text after the match). Any other ``$`` sequence
    stays literal, exactly as in JS string replace.
    """

    units = utf16_code_units(value)
    needle = utf16_code_units(search)
    index = index_of(value, search)
    if index == -1:
        return value
    before = _from_code_units(units[:index])
    after = _from_code_units(units[index + len(needle) :])
    return before + _expand_replacement(replacement, search, before, after) + after


def _expand_replacement(replacement: str, matched: str, before: str, after: str) -> str:
    parts: list[str] = []
    position = 0
    while position < len(replacement):
        char = replacement[position]
        if char == "$" and position + 1 < len(replacement):
            token = replacement[position + 1]
            if token == "$":
                parts.append("$")
                position += 2
                continue
            if token == "&":
                parts.append(matched)
                position += 2
                continue
            if token == "`":
                parts.append(before)
                position += 2
                continue
            if token == "'":
                parts.append(after)
                position += 2
                continue
        parts.append(char)
        position += 1
    return "".join(parts)


def to_upper_case(value: str) -> str:
    """Return the Unicode default (non-locale) full uppercase mapping."""

    return value.upper()


def to_lower_case(value: str) -> str:
    """Return the Unicode default (non-locale) full lowercase mapping."""

    return value.lower()


_JS_TRIM_CHARS = "".join(
    chr(code)
    for code in (
        0x0009,
        0x000A,
        0x000B,
        0x000C,
        0x000D,
        0x0020,
        0x00A0,
        0x1680,
        0x2000,
        0x2001,
        0x2002,
        0x2003,
        0x2004,
        0x2005,
        0x2006,
        0x2007,
        0x2008,
        0x2009,
        0x200A,
        0x2028,
        0x2029,
        0x202F,
        0x205F,
        0x3000,
        0xFEFF,
    )
)


def trim(value: str) -> str:
    return value.strip(_JS_TRIM_CHARS)


def trim_start(value: str) -> str:
    return value.lstrip(_JS_TRIM_CHARS)


def trim_end(value: str) -> str:
    return value.rstrip(_JS_TRIM_CHARS)


def repeat(value: str, count: int) -> str:
    if count < 0:
        raise JsRangeError("repeat count must be non-negative")
    return value * count


def pad_start(value: str, target_length: int, pad_string: str = " ") -> str:
    return _pad(value, target_length, pad_string, at_start=True)


def pad_end(value: str, target_length: int, pad_string: str = " ") -> str:
    return _pad(value, target_length, pad_string, at_start=False)


def split(value: str, separator: str, limit: int | None = None) -> list[str]:
    if limit == 0:
        return []
    max_items = 2**32 - 1 if limit is None or limit < 0 else limit
    if separator == "":
        return [char_at(value, index) for index in range(min(utf16_len(value), max_items))]
    parts = value.split(separator)
    return parts[:max_items]


def from_char_code(*codes: int) -> str:
    return _from_code_units(tuple(code & 0xFFFF for code in codes))


def from_code_point(*code_points: int) -> str:
    chars: list[str] = []
    for code_point in code_points:
        if code_point < 0 or code_point > 0x10FFFF:
            raise JsRangeError("invalid code point")
        chars.append(chr(code_point))
    return "".join(chars)


def _pad(value: str, target_length: int, pad_string: str, *, at_start: bool) -> str:
    current_length = utf16_len(value)
    if target_length <= current_length or pad_string == "":
        return value
    needed = target_length - current_length
    repeated = (pad_string * ((needed // max(utf16_len(pad_string), 1)) + 1))[:needed]
    return repeated + value if at_start else value + repeated
