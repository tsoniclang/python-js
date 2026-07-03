"""Core JavaScript value sentinels."""

from typing import Final


class _JsUndefined:
    __slots__ = ()

    def __repr__(self) -> str:
        return "undefined"

    def __str__(self) -> str:
        return "undefined"

    def __bool__(self) -> bool:
        return False


undefined: Final = _JsUndefined()


def is_undefined(value: object) -> bool:
    """Return true only for the JavaScript undefined singleton."""

    return value is undefined


def is_nullish(value: object) -> bool:
    """Return true for JavaScript null or undefined."""

    return value is None or value is undefined
