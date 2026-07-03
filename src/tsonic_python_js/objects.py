"""Closed JavaScript object carrier and property operations."""

from collections import OrderedDict
from collections.abc import Iterable

from tsonic_python_js.values import undefined


def property_key(key: object) -> str:
    if key is None:
        return "null"
    if key is undefined:
        return "undefined"
    if isinstance(key, bool):
        return "true" if key else "false"
    if isinstance(key, int):
        return str(key)
    if isinstance(key, float):
        if key.is_integer():
            return str(int(key))
        return str(key)
    return str(key)


class JsObject:
    """Own-property JS object carrier with insertion-ordered enumerable keys."""

    __slots__ = ("_properties",)
    _properties: OrderedDict[str, object]

    def __init__(self, entries: Iterable[tuple[object, object]] | None = None) -> None:
        self._properties = OrderedDict()
        if entries is not None:
            for key, value in entries:
                self.set(key, value)

    def get(self, key: object) -> object:
        return self._properties.get(property_key(key), undefined)

    def set(self, key: object, value: object) -> object:
        self._properties[property_key(key)] = value
        return value

    def delete(self, key: object) -> bool:
        self._properties.pop(property_key(key), None)
        return True

    def has_own(self, key: object) -> bool:
        return property_key(key) in self._properties

    def keys(self) -> list[str]:
        return list(self._properties.keys())

    def values(self) -> list[object]:
        return list(self._properties.values())

    def entries(self) -> list[tuple[str, object]]:
        return list(self._properties.items())


def get_property(value: object, key: object) -> object:
    from tsonic_python_js.arrays import JsArray
    from tsonic_python_js.strings import char_at, utf16_len

    if isinstance(value, JsObject):
        return value.get(key)
    if isinstance(value, JsArray):
        if property_key(key) == "length":
            return value.length
        index = _array_index_key(key)
        if index is None:
            return undefined
        return value.get(index)
    if isinstance(value, str):
        if property_key(key) == "length":
            return utf16_len(value)
        index = _array_index_key(key)
        if index is None:
            return undefined
        char = char_at(value, index)
        return undefined if char == "" else char
    return undefined


def set_property(value: object, key: object, new_value: object) -> object:
    from tsonic_python_js.arrays import JsArray

    if isinstance(value, JsObject):
        return value.set(key, new_value)
    if isinstance(value, JsArray):
        if property_key(key) == "length":
            value.set_length(new_value)
            return new_value
        index = _array_index_key(key)
        if index is not None:
            value.set(index, new_value)
            return new_value
    return undefined


def delete_property(value: object, key: object) -> bool:
    from tsonic_python_js.arrays import JsArray

    if isinstance(value, JsObject):
        return value.delete(key)
    if isinstance(value, JsArray):
        index = _array_index_key(key)
        if index is not None:
            return value.delete(index)
    return True


def _array_index_key(key: object) -> int | None:
    text = property_key(key)
    if not text.isdecimal():
        return None
    index = int(text)
    if index > 2**32 - 2:
        return None
    return index
