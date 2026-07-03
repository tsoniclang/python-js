"""Number helpers needed by PJS-1 runtime semantics."""

import math

from tsonic_python_js.errors import JsTypeError
from tsonic_python_js.values import undefined


def _as_float(value: object) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    raise JsTypeError(f"expected a JS number-compatible value, got {type(value).__name__}")


def is_nan(value: object) -> bool:
    """Return true only for numeric NaN values."""

    return isinstance(value, float) and math.isnan(value)


def is_finite(value: object) -> bool:
    """Return true only for finite numeric values."""

    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


def is_integer(value: object) -> bool:
    if not is_finite(value):
        return False
    assert isinstance(value, int | float)
    return float(value).is_integer()


def is_safe_integer(value: object) -> bool:
    if not is_integer(value):
        return False
    assert isinstance(value, int | float)
    return abs(float(value)) <= 9_007_199_254_740_991


def is_negative_zero(value: object) -> bool:
    return isinstance(value, float) and value == 0.0 and math.copysign(1.0, value) < 0.0


def to_uint32(value: object) -> int:
    """Implement ECMAScript ToUint32 for supported numeric inputs."""

    number = _as_float(value)
    if not math.isfinite(number) or number == 0.0:
        return 0
    integer = math.copysign(math.floor(abs(number)), number)
    return int(integer) % 2**32


def to_int32(value: object) -> int:
    """Implement ECMAScript ToInt32 for supported numeric inputs."""

    uint32 = to_uint32(value)
    if uint32 >= 2**31:
        return uint32 - 2**32
    return uint32


def to_number(value: object) -> float:
    from tsonic_python_js.dynamic import JsValue

    if isinstance(value, JsValue):
        value = value.payload
    if value is undefined:
        return math.nan
    if value is None:
        return 0.0
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return 0.0
        if stripped in ("Infinity", "+Infinity"):
            return math.inf
        if stripped == "-Infinity":
            return -math.inf
        try:
            return float(stripped)
        except ValueError:
            return math.nan
    raise JsTypeError(f"cannot convert {type(value).__name__} to JS number")


def parse_int(value: object, radix: int | None = None) -> float:
    text = str(value).lstrip()
    sign = 1
    if text.startswith(("+", "-")):
        sign = -1 if text[0] == "-" else 1
        text = text[1:]
    actual_radix = 0 if radix is None else to_int32(radix)
    if actual_radix != 0 and (actual_radix < 2 or actual_radix > 36):
        return math.nan
    if actual_radix in (0, 16) and text[:2].lower() == "0x":
        actual_radix = 16
        text = text[2:]
    if actual_radix == 0:
        actual_radix = 10
    digits: list[str] = []
    for char in text:
        digit = _digit_value(char)
        if digit < 0 or digit >= actual_radix:
            break
        digits.append(char)
    if not digits:
        return math.nan
    return float(sign * int("".join(digits), actual_radix))


def parse_float(value: object) -> float:
    text = str(value).lstrip()
    for literal, result in (
        ("Infinity", math.inf),
        ("+Infinity", math.inf),
        ("-Infinity", -math.inf),
    ):
        if text.startswith(literal):
            return result
    best = ""
    for end in range(1, len(text) + 1):
        candidate = text[:end]
        try:
            float(candidate)
        except ValueError:
            continue
        best = candidate
    if best in ("+", "-") or best == "":
        return math.nan
    return float(best)


def math_abs(value: object) -> float:
    return abs(to_number(value))


def math_ceil(value: object) -> float:
    number = to_number(value)
    return number if not math.isfinite(number) or number == 0 else float(math.ceil(number))


def math_floor(value: object) -> float:
    number = to_number(value)
    return number if not math.isfinite(number) or number == 0 else float(math.floor(number))


def math_trunc(value: object) -> float:
    number = to_number(value)
    if not math.isfinite(number) or number == 0:
        return number
    return math.copysign(math.floor(abs(number)), number)


def math_round(value: object) -> float:
    number = to_number(value)
    if not math.isfinite(number) or number == 0:
        return number
    if -0.5 <= number < 0:
        return -0.0
    return float(math.floor(number + 0.5))


def math_max(*values: object) -> float:
    if not values:
        return -math.inf
    numbers = [to_number(value) for value in values]
    if any(math.isnan(number) for number in numbers):
        return math.nan
    result = numbers[0]
    for number in numbers[1:]:
        if number > result or (number == result == 0 and not is_negative_zero(number)):
            result = number
    return result


def math_min(*values: object) -> float:
    if not values:
        return math.inf
    numbers = [to_number(value) for value in values]
    if any(math.isnan(number) for number in numbers):
        return math.nan
    result = numbers[0]
    for number in numbers[1:]:
        if number < result or (number == result == 0 and is_negative_zero(number)):
            result = number
    return result


def math_sign(value: object) -> float:
    number = to_number(value)
    if math.isnan(number) or number == 0:
        return number
    return 1.0 if number > 0 else -1.0


def math_pow(base: object, exponent: object) -> float:
    try:
        return float(math.pow(to_number(base), to_number(exponent)))
    except ValueError:
        return math.nan


def math_sqrt(value: object) -> float:
    number = to_number(value)
    return math.nan if number < 0 else math.sqrt(number)


def math_imul(left: object, right: object) -> int:
    product = (to_uint32(left) * to_uint32(right)) & 0xFFFFFFFF
    return product - 0x100000000 if product & 0x80000000 else product


def math_clz32(value: object) -> int:
    uint32 = to_uint32(value)
    if uint32 == 0:
        return 32
    return 32 - uint32.bit_length()


def _digit_value(char: str) -> int:
    code = ord(char)
    if 48 <= code <= 57:
        return code - 48
    if 65 <= code <= 90:
        return code - 55
    if 97 <= code <= 122:
        return code - 87
    return -1
