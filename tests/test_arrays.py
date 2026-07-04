from tests.assertions import raises
from tsonic_python_js import JsArray, JsRangeError, undefined


def test_constructor_length_creates_holes() -> None:
    array = JsArray.with_length(3)
    assert array.length == 3
    assert not array.has_index(0)
    assert array.get(0) is undefined
    assert array.values_with_holes()[0] is not undefined
    numeric_length = JsArray.with_length(2.0)
    assert numeric_length.length == 2
    assert not numeric_length.has_index(0)


def test_index_write_extends_with_holes_and_preserves_present_undefined() -> None:
    array = JsArray()
    array.set(2, "c")
    array.set(1, undefined)
    assert array.length == 3
    assert not array.has_index(0)
    assert array.has_index(1)
    assert array.get(0) is undefined
    assert array.get(1) is undefined
    assert array.get(2) == "c"
    assert array.present_items() == ((1, undefined), (2, "c"))


def test_sparse_growth_and_negative_at_match_rust_js_array_expectations() -> None:
    values = JsArray([1.0, 2.0, 3.0])
    values.set_length(5)
    assert values.length == 5
    assert values.at(0) == 1.0
    assert values.at(-1) is undefined
    assert values.at(-5) == 1.0
    assert values.at(-3) == 3.0
    assert values.at(5) is undefined
    assert values.at(-6) is undefined
    values.set(4, 9.0)
    assert values.at(-1) == 9.0

    grown = JsArray([1, 2])
    assert grown.set(6, "x") == 7
    assert grown.length == 7
    assert not grown.has_index(3)
    assert grown.get(3) is undefined
    assert grown.delete(3)
    assert grown.length == 7
    with raises(JsRangeError):
        grown.set(-1, "y")


def test_delete_creates_hole_without_changing_length() -> None:
    array = JsArray([1, 0, 3])
    assert array.delete(1)
    assert array.length == 3
    assert not array.has_index(1)
    assert array.get(1) is undefined
    assert array.index_of(0) == -1
    array.set(1, 0)
    assert array.index_of(0) == 1


def test_length_write_truncates_or_extends_with_holes() -> None:
    array = JsArray([1, 2, 3])
    assert array.set_length(1) == 1
    assert array.length == 1
    assert array.get(1) is undefined
    assert array.set_length(4) == 4
    assert array.get(0) == 1
    assert not array.has_index(1)
    assert not array.has_index(3)


def test_push_and_pop_preserve_hole_semantics() -> None:
    array = JsArray.with_length(2)
    array.set(0, "a")
    assert array.push(undefined, "d") == 4
    assert array.has_index(2)
    assert array.pop() == "d"
    assert array.pop() is undefined
    assert array.pop() is undefined
    assert not array.has_index(1)
    assert array.pop() == "a"
    assert array.pop() is undefined


def test_at_supports_negative_indices_and_holes() -> None:
    array = JsArray([1.0, 2.0, 3.0])
    array.length = 5
    assert array.at(0) == 1.0
    assert array.at(-1) is undefined
    assert array.at(-5) == 1.0
    assert array.at(-3) == 3.0
    assert array.at(5) is undefined
    assert array.at(-6) is undefined
    array.set(4, 9.0)
    assert array.at(-1) == 9.0


def test_includes_uses_same_value_zero_and_treats_holes_as_undefined() -> None:
    array = JsArray.with_length(3)
    array.set(1, float("nan"))
    assert array.includes(float("nan"))
    assert array.includes(undefined)
    assert array.includes(float("nan"), -2)
    array.set(2, -0.0)
    assert array.includes(0.0)
    assert array.includes(-0.0)


def test_index_of_uses_strict_equality_and_skips_holes() -> None:
    array = JsArray.with_length(4)
    array.set(1, float("nan"))
    array.set(2, -0.0)
    array.set(3, undefined)
    assert array.index_of(float("nan")) == -1
    assert array.index_of(0.0) == 2
    assert array.index_of(-0.0) == 2
    assert array.index_of(undefined) == 3
    array.delete(3)
    assert array.index_of(undefined) == -1


def test_slice_normalizes_indices_and_preserves_holes() -> None:
    source = JsArray.with_length(5)
    source.set(1, "b")
    source.set(3, "d")
    sliced = source.slice(0, 4)
    assert sliced.length == 4
    assert not sliced.has_index(0)
    assert sliced.get(1) == "b"
    assert not sliced.has_index(2)
    assert sliced.get(3) == "d"
    negative = source.slice(-4, -1)
    assert negative.length == 3
    assert negative.get(0) == "b"
    assert not negative.has_index(1)
    assert negative.get(2) == "d"


def test_array_rejects_invalid_lengths_and_indices() -> None:
    with raises(JsRangeError):
        JsArray.with_length(-1)
    with raises(JsRangeError):
        JsArray.with_length(True)
    with raises(JsRangeError):
        JsArray.with_length(2.5)
    with raises(JsRangeError):
        JsArray().set(-1, "x")
    with raises(JsRangeError):
        JsArray().set(2**32 - 1, "x")
