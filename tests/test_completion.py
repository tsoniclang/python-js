import math

from tests.assertions import raises
from tsonic_python_js import (
    REGEXP_STATUS,
    ArrayBuffer,
    DataView,
    Float32Array,
    Float64Array,
    Int8Array,
    Int16Array,
    Int32Array,
    JsDate,
    JsError,
    JsMap,
    JsObject,
    JsRangeError,
    JsReferenceError,
    JsSet,
    JsSyntaxError,
    JsTypeError,
    JsUnsupportedError,
    JsURIError,
    JsValue,
    TypedArray,
    Uint8Array,
    Uint8ClampedArray,
    Uint16Array,
    Uint32Array,
    delete_property,
    ends_with,
    from_char_code,
    from_code_point,
    get_property,
    includes,
    index_of,
    is_integer,
    is_safe_integer,
    json_parse,
    json_stringify,
    last_index_of,
    math_abs,
    math_ceil,
    math_clz32,
    math_floor,
    math_imul,
    math_max,
    math_min,
    math_pow,
    math_round,
    math_sign,
    math_sqrt,
    math_trunc,
    object_is,
    pad_end,
    pad_start,
    parse_float,
    parse_int,
    property_key,
    repeat,
    same_value_zero,
    set_property,
    split,
    starts_with,
    strict_equal,
    string_slice,
    substr,
    substring,
    to_number,
    trim,
    trim_end,
    trim_start,
    undefined,
    unsupported_regexp,
)


def test_object_and_dynamic_value_operations_are_closed() -> None:
    obj = JsObject([(1, "one"), ("x", 2)])
    assert obj.keys() == ["1", "x"]
    assert obj.values() == ["one", 2]
    assert obj.entries() == [("1", "one"), ("x", 2)]
    assert obj.has_own(1)
    assert get_property(obj, "x") == 2
    assert set_property(obj, "y", 3) == 3
    assert delete_property(obj, "x")
    assert get_property(obj, "x") is undefined
    assert property_key(True) == "true"
    wrapped = JsValue.from_python(obj)
    assert wrapped.kind == "object"
    assert wrapped.get_property("y") == 3
    assert wrapped.strict_equal(obj)
    assert wrapped.same_value_zero(obj)
    with raises(JsTypeError):
        JsValue.from_python(object())


def test_completed_array_methods_preserve_holes() -> None:
    from tsonic_python_js import JsArray

    source = JsArray.with_length(4)
    source.set(1, 2)
    source.set(3, 4)
    assert source.shift() is undefined
    assert source.unshift(0) == 4
    assert source.keys() == [0, 1, 2, 3]
    assert source.values() == [0, 2, undefined, 4]
    assert source.entries()[2] == (2, undefined)
    assert source.slice().concat(JsArray(["x"])).get(4) == "x"
    source.fill(9, 1, 3)
    assert source.values() == [0, 9, 9, 4]
    source.delete(1)
    source.copy_within(2, 0, 2)
    assert source.values() == [0, undefined, 0, undefined]
    source.reverse()
    assert source.values() == [undefined, 0, undefined, 0]
    removed = source.splice(1, 2, "a", "b")
    assert removed.values() == [0, undefined]
    assert source.values() == [undefined, "a", "b", 0]
    assert source.join("|") == "|a|b|0"
    assert source.to_string() == ",a,b,0"
    assert source.map(lambda value, _index, _array: f"{value}!").values() == [
        undefined,
        "a!",
        "b!",
        "0!",
    ]
    assert source.filter(lambda value, _index, _array: value != "b").values() == ["a", 0]
    assert source.reduce(lambda acc, value, _index, _array: f"{acc}{value}", "") == "ab0"
    assert source.some(lambda value, _index, _array: value == "a")
    assert source.every(lambda value, _index, _array: value is not undefined)
    assert source.find(lambda value, _index, _array: value == "b") == "b"
    assert source.find_index(lambda value, _index, _array: value == "b") == 2
    visited: list[int] = []
    source.for_each(lambda _value, index, _array: visited.append(index))
    assert visited == [1, 2, 3]
    with raises(JsRangeError):
        JsArray().reduce(lambda acc, value, _index, _array: acc)


def test_array_keys_yield_all_indexes_including_holes() -> None:
    from tsonic_python_js import JsArray

    assert JsArray.with_length(2).keys() == [0, 1]
    sparse = JsArray.with_length(3)
    sparse.set(1, "present")
    assert sparse.keys() == [0, 1, 2]


def test_string_completion_helpers() -> None:
    assert string_slice("javascript", -3) == "ipt"
    assert substring("abc", 2, 0) == "ab"
    assert substr("javascript", -6, 3) == "scr"
    assert index_of("hello", "l") == 2
    assert last_index_of("banana", "ana") == 3
    assert last_index_of("abc", "c", 2) == 2
    assert includes("hello", "ell")
    assert starts_with("hello", "he")
    assert ends_with("hello", "lo")
    assert trim("\ufeff hi \n") == "hi"
    assert trim_start("  hi  ") == "hi  "
    assert trim_end("  hi  ") == "  hi"
    assert repeat("x", 3) == "xxx"
    assert pad_start("5", 3, "0") == "005"
    assert pad_end("5", 3, "0") == "500"
    assert split("a,b,c", ",", 2) == ["a", "b"]
    assert split("abc", "", 2) == ["a", "b"]
    assert from_char_code(0x41, 0x110000, -1) == "A\u0000\uffff"
    assert from_code_point(0x1F600) == "😀"
    with raises(JsRangeError):
        repeat("x", -1)
    with raises(JsRangeError):
        from_code_point(0x110000)


def test_number_and_math_completion_helpers() -> None:
    assert parse_int("ff", 16) == 255.0
    assert parse_int("xyz") != parse_int("xyz")
    assert parse_float("  -1.5e+2x") == -150.0
    assert parse_float("1e+") == 1.0
    assert to_number(None) == 0.0
    assert math.isnan(to_number(undefined))
    assert is_integer(42.0)
    assert is_safe_integer(9_007_199_254_740_991)
    assert not is_safe_integer(9_007_199_254_740_992)
    assert math_abs(-3) == 3
    assert math_ceil(1.2) == 2
    assert math_floor(1.8) == 1
    assert math_trunc(-1.8) == -1
    assert object_is(math_round(-0.2), -0.0)
    assert math_max(-0.0, 0.0) == 0.0
    assert object_is(math_min(-0.0, 0.0), -0.0)
    assert math_sign(-3) == -1
    assert math_pow(2, 3) == 8
    assert math_sqrt(9) == 3
    assert math_imul(0xFFFFFFFF, 5) == -5
    assert math_clz32(1) == 31


def test_json_collections_date_and_regexp_completion() -> None:
    parsed = json_parse('{"x":[1,null,true],"skip":null}')
    assert isinstance(parsed, JsObject)
    array = get_property(parsed, "x")
    assert json_stringify(parsed) == '{"x":[1,null,true],"skip":null}'
    assert json_stringify(undefined) is None
    assert json_stringify(array) == "[1,null,true]"
    obj = JsObject([("a", undefined), ("b", float("nan")), ("c", "ok")])
    assert json_stringify(obj) == '{"b":null,"c":"ok"}'
    with raises(JsSyntaxError):
        json_parse("{")

    key_a = JsObject()
    key_b = JsObject()
    map_value = JsMap([(float("nan"), "nan"), (key_a, 1)])
    map_value.set(key_b, 2)
    assert map_value.size == 3
    assert map_value.get(float("nan")) == "nan"
    assert map_value.has(key_a)
    assert map_value.delete(key_a)
    assert map_value.keys()[0] != map_value.keys()[1]
    set_value = JsSet([float("nan"), float("nan"), key_b])
    assert set_value.size == 2
    assert set_value.has(float("nan"))
    assert set_value.entries()[0][0] is set_value.entries()[0][1]

    date = JsDate(0)
    assert date.get_time() == 0
    assert date.to_iso_string() == "1970-01-01T00:00:00.000Z"
    assert JsDate.parse("1970-01-01T00:00:00.000Z").get_utc_full_year() == 1970
    assert date.get_utc_month() == 0
    assert date.get_utc_date() == 1
    assert isinstance(JsDate.now(), JsDate)
    assert REGEXP_STATUS.startswith("hard-reject")
    with raises(JsUnsupportedError):
        unsupported_regexp("x")


def test_typed_arrays_views_copies_bounds_and_errors() -> None:
    assert issubclass(Int8Array, TypedArray)
    buffer = ArrayBuffer(8)
    view = DataView(buffer)
    view.set_uint16(0, 0x1234)
    assert view.get_uint16(0) == 0x1234
    view.set_uint16(2, 0x1234, little_endian=True)
    assert view.get_uint16(2, little_endian=True) == 0x1234
    view.set_int8(4, -1)
    assert view.get_int8(4) == -1
    view.set_uint8(5, 255)
    assert view.get_uint8(5) == 255
    view.set_float32(0, 1.5, little_endian=True)
    assert math.isclose(view.get_float32(0, little_endian=True), 1.5)
    f64 = Float64Array([1.25])
    assert f64.values() == [1.25]
    u8 = Uint8Array([1, 2, 3, 4])
    sub = u8.subarray(1, 3)
    copied = u8.slice(1, 3)
    sub.set(0, 9)
    assert u8.values() == [1, 9, 3, 4]
    copied.set(0, 7)
    assert u8.values() == [1, 9, 3, 4]
    assert Uint8ClampedArray([-1, 2.6, 300, float("nan")]).values() == [0, 3, 255, 0]
    assert Uint8Array([-1, 256]).values() == [255, 0]
    assert Int8Array([255, 128]).values() == [-1, -128]
    assert Uint16Array([-1, 65536]).values() == [65535, 0]
    assert Int16Array([65535, 32768]).values() == [-1, -32768]
    assert Uint32Array([-1, 4294967296]).values() == [4294967295, 0]
    assert Int32Array([4294967295, 2147483648]).values() == [-1, -2147483648]
    view.set_uint8(0, -1)
    assert view.get_uint8(0) == 255
    view.set_int8(1, 255)
    assert view.get_int8(1) == -1
    view.set_uint16(2, -1)
    assert view.get_uint16(2) == 65535
    view.set_int16(2, 65535)
    assert view.get_int16(2) == -1
    view.set_uint32(0, -1)
    assert view.get_uint32(0) == 4294967295
    view.set_int32(0, 4294967295)
    assert view.get_int32(0) == -1
    assert Int16Array([1]).values() == [1]
    assert Uint16Array([1]).values() == [1]
    assert Int32Array([1]).values() == [1]
    assert Uint32Array([1]).values() == [1]
    assert Float32Array([1.5]).values()[0] > 1
    with raises(JsRangeError):
        DataView(buffer, 9)
    with raises(JsRangeError):
        u8.get(99)


def test_error_names_and_global_equality_symbols_remain_available() -> None:
    for error_type in (
        JsError,
        JsTypeError,
        JsRangeError,
        JsSyntaxError,
        JsReferenceError,
        JsURIError,
    ):
        assert error_type("x").message == "x"
        assert error_type("x").name
    assert strict_equal(1, 1)
    assert same_value_zero(float("nan"), float("nan"))
