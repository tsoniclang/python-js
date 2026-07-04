from tests.assertions import raises
from tsonic_python_js import (
    Float64Array,
    Int8Array,
    JsRangeError,
    Uint8Array,
    Uint8ClampedArray,
)


def test_set_bulk_copies_list_source_with_class_conversion() -> None:
    target = Uint8Array(5)
    target.set([1, 258, -1], 1)
    assert target.values() == [0, 1, 2, 255, 0]
    clamped = Uint8ClampedArray(3)
    clamped.set([-5, 2.6, 300])
    assert clamped.values() == [0, 3, 255]
    floats = Float64Array(2)
    floats.set([1.5], 1)
    assert floats.values() == [0.0, 1.5]


def test_set_bulk_accepts_typed_array_sources_including_overlap() -> None:
    target = Int8Array([1, 2, 3, 4])
    source = Uint8Array([255, 128])
    target.set(source, 2)
    assert target.values() == [1, 2, -1, -128]
    overlapping = Uint8Array([1, 2, 3, 4])
    overlapping.set(overlapping.subarray(0, 3), 1)
    assert overlapping.values() == [1, 1, 2, 3]


def test_set_bulk_raises_range_error_without_partial_writes() -> None:
    target = Uint8Array(3)
    with raises(JsRangeError):
        target.set([1, 2], 2)
    with raises(JsRangeError):
        target.set([1], -1)
    with raises(JsRangeError):
        target.set([1, 2, 3, 4])
    with raises(JsRangeError):
        target.set([1, "x"], 0)
    assert target.values() == [0, 0, 0]


def test_set_element_write_still_applies_conversion_and_bounds() -> None:
    target = Int8Array(2)
    target.set(1, 255)
    assert target.values() == [0, -1]
    with raises(JsRangeError):
        target.set(9, 1)
    with raises(JsRangeError):
        target.set(0.5, 1)
