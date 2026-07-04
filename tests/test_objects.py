from tsonic_python_js import (
    JsArray,
    JsObject,
    JsValue,
    delete_property,
    get_property,
    set_property,
    undefined,
)


def test_property_write_and_delete_round_trip_on_object_carrier() -> None:
    obj = JsObject()
    assert set_property(obj, "a", 1) == 1
    assert set_property(obj, 2, "two") == "two"
    assert get_property(obj, "a") == 1
    assert get_property(obj, "2") == "two"
    assert delete_property(obj, 2)
    assert get_property(obj, "2") is undefined
    assert delete_property(obj, "missing")


def test_property_write_and_delete_round_trip_on_array_carrier() -> None:
    array = JsArray()
    assert set_property(array, 2, "c") == "c"
    assert get_property(array, "length") == 3
    assert get_property(array, 2) == "c"
    assert set_property(array, "length", 1) == 1
    assert get_property(array, 2) is undefined
    assert set_property(array, "name", "x") is undefined
    assert get_property(array, "name") is undefined
    assert delete_property(array, 0)
    assert get_property(array, 0) is undefined


def test_property_writes_flow_through_js_value_wrappers() -> None:
    wrapped_object = JsValue.from_python(JsObject([("k", "v")]))
    assert wrapped_object.set_property("k", "w") == "w"
    assert wrapped_object.get_property("k") == "w"
    assert wrapped_object.delete_property("k")
    assert wrapped_object.get_property("k") is undefined

    wrapped_array = JsValue.from_python(JsArray(["a"]))
    assert wrapped_array.set_property(1, "b") == "b"
    assert wrapped_array.get_property("length") == 2
    assert wrapped_array.delete_property(0)
    assert wrapped_array.get_property(0) is undefined

    primitive = JsValue.from_python("hi")
    assert primitive.get_property(0) == "h"
    assert primitive.get_property("length") == 2
    assert primitive.set_property(0, "x") is undefined
    assert primitive.get_property(0) == "h"
    assert primitive.delete_property(0)
