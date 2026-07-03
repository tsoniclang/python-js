"""JavaScript equality algorithms claimed by PJS-1."""

from tsonic_python_js.numbers import is_nan, is_negative_zero
from tsonic_python_js.values import undefined


def _same_numeric_value(left: object, right: object) -> bool:
    if is_nan(left) or is_nan(right):
        return False
    return left == right


def strict_equal(left: object, right: object) -> bool:
    """Implement JavaScript strict equality for PJS-1 supported values."""

    from tsonic_python_js.dynamic import JsValue

    if isinstance(left, JsValue):
        left = left.payload
    if isinstance(right, JsValue):
        right = right.payload
    if left is undefined or right is undefined:
        return left is undefined and right is undefined
    if left is None or right is None:
        return left is None and right is None
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left is right
    if isinstance(left, int | float) and isinstance(right, int | float):
        return _same_numeric_value(left, right)
    if isinstance(left, str) or isinstance(right, str):
        return isinstance(left, str) and isinstance(right, str) and left == right
    return left is right


def same_value_zero(left: object, right: object) -> bool:
    """Implement SameValueZero for PJS-1 supported values."""

    if is_nan(left) and is_nan(right):
        return True
    return strict_equal(left, right)


def object_is(left: object, right: object) -> bool:
    """Implement Object.is for PJS-1 supported values."""

    if is_nan(left) and is_nan(right):
        return True
    if isinstance(left, int | float) and isinstance(right, int | float):
        if left == 0 and right == 0:
            return is_negative_zero(left) == is_negative_zero(right)
        return left == right
    return strict_equal(left, right)
