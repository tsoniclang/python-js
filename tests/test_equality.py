import math

from tsonic_python_js import JsArray, object_is, same_value_zero, strict_equal, undefined


def test_strict_equal_primitives_and_nullish_values() -> None:
    assert strict_equal(undefined, undefined)
    assert not strict_equal(undefined, None)
    assert strict_equal(None, None)
    assert strict_equal(True, True)
    assert not strict_equal(True, 1)
    assert strict_equal("hello", "hello")
    assert not strict_equal("hello", "other")


def test_nan_and_signed_zero_semantics() -> None:
    nan = float("nan")
    assert not strict_equal(nan, nan)
    assert same_value_zero(nan, nan)
    assert object_is(nan, nan)
    assert strict_equal(0.0, -0.0)
    assert same_value_zero(0.0, -0.0)
    assert not object_is(0.0, -0.0)
    assert object_is(-0.0, -0.0)
    assert math.copysign(1.0, -0.0) < 0.0


def test_arrays_compare_by_identity_not_structure() -> None:
    left = JsArray([1, "a"])
    right = JsArray([1, "a"])
    alias = left
    assert not strict_equal(left, right)
    assert not same_value_zero(left, right)
    assert not object_is(left, right)
    assert strict_equal(left, alias)
    assert same_value_zero(left, alias)
    assert object_is(left, alias)
