from tsonic_python_js import is_nullish, is_undefined, undefined


def test_undefined_singleton_is_not_none() -> None:
    assert undefined is undefined
    assert undefined is not None
    assert undefined != None  # noqa: E711
    assert str(undefined) == "undefined"
    assert repr(undefined) == "undefined"


def test_nullish_helpers_keep_none_and_undefined_distinct() -> None:
    assert is_undefined(undefined)
    assert not is_undefined(None)
    assert is_nullish(undefined)
    assert is_nullish(None)
    assert not is_nullish(0)
