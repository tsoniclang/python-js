import math

from tests.assertions import raises
from tsonic_python_js import JsTypeError, is_finite, is_nan, to_int32, to_uint32


def test_number_predicates_are_numeric_only() -> None:
    assert is_nan(float("nan"))
    assert not is_nan(1.0)
    assert not is_nan("NaN")
    assert is_finite(0)
    assert is_finite(1.5)
    assert not is_finite(float("inf"))
    assert not is_finite(True)


def test_to_uint32_matches_js_wraparound_edges() -> None:
    assert to_uint32(0) == 0
    assert to_uint32(-1) == 4_294_967_295
    assert to_uint32(4_294_967_297) == 1
    assert to_uint32(3.9) == 3
    assert to_uint32(-3.9) == 4_294_967_293
    assert to_uint32(float("inf")) == 0
    assert to_uint32(math.nan) == 0


def test_to_int32_matches_js_signed_wraparound_edges() -> None:
    assert to_int32(0) == 0
    assert to_int32(2_147_483_647) == 2_147_483_647
    assert to_int32(2_147_483_648) == -2_147_483_648
    assert to_int32(4_294_967_295) == -1
    assert to_int32(-1) == -1


def test_to_int32_and_to_uint32_reject_unsupported_values() -> None:
    with raises(JsTypeError):
        to_int32("1")
    with raises(JsTypeError):
        to_uint32(None)
