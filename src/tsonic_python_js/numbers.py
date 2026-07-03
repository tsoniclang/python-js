"""Number helpers needed by PJS-1 runtime semantics."""

import math

from tsonic_python_js.errors import JsTypeError


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
