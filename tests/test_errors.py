from tests.assertions import raises
from tsonic_python_js import JsError, JsRangeError, JsReferenceError, JsSyntaxError, JsTypeError


def test_error_hierarchy_is_closed_under_js_error() -> None:
    for error_type in (JsTypeError, JsRangeError, JsSyntaxError, JsReferenceError):
        assert issubclass(error_type, JsError)


def test_errors_raise_as_python_exceptions() -> None:
    with raises(JsRangeError):
        raise JsRangeError("bad range")
