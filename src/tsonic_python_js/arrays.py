"""Sparse JavaScript array carrier."""

import math
from collections.abc import Callable, Iterable
from typing import Final

from tsonic_python_js.equality import same_value_zero, strict_equal
from tsonic_python_js.errors import JsRangeError
from tsonic_python_js.strings import js_slice_indices
from tsonic_python_js.values import undefined


class _Hole:
    __slots__ = ()

    def __repr__(self) -> str:
        return "<hole>"


_HOLE: Final = _Hole()


class JsArray:
    """Sparse JS array carrier that preserves holes separately from undefined."""

    __slots__ = ("_slots",)
    _slots: list[object]

    def __init__(
        self, values: Iterable[object] | None = None, *, length: object | None = None
    ) -> None:
        if values is not None and length is not None:
            raise JsRangeError("JsArray accepts either values or length, not both")
        if values is not None:
            self._slots = list(values)
            return
        if length is None:
            self._slots = []
            return
        self._slots = [_HOLE] * self._validate_length(length)

    @classmethod
    def with_length(cls, length: object) -> "JsArray":
        return cls(length=length)

    @classmethod
    def from_sparse(cls, length: object, entries: Iterable[tuple[int, object]]) -> "JsArray":
        array = cls.with_length(length)
        for index, value in entries:
            array.set(index, value)
        return array

    @staticmethod
    def _validate_length(length: object) -> int:
        if isinstance(length, bool) or not isinstance(length, int | float):
            raise JsRangeError("invalid JS array length")
        if not math.isfinite(length) or length < 0 or length > 2**32 - 1:
            raise JsRangeError("invalid JS array length")
        integer_length = int(length)
        if integer_length != length:
            raise JsRangeError("invalid JS array length")
        return integer_length

    @staticmethod
    def _validate_index(index: object) -> int:
        if isinstance(index, bool) or not isinstance(index, int) or index < 0 or index > 2**32 - 2:
            raise JsRangeError("invalid JS array index")
        return index

    @property
    def length(self) -> int:
        return len(self._slots)

    @length.setter
    def length(self, new_length: int) -> None:
        self.set_length(new_length)

    def set_length(self, new_length: object) -> int:
        valid_length = self._validate_length(new_length)
        if valid_length < len(self._slots):
            del self._slots[valid_length:]
        else:
            self._slots.extend([_HOLE] * (valid_length - len(self._slots)))
        return valid_length

    def has_index(self, index: int) -> bool:
        return 0 <= index < self.length and self._slots[index] is not _HOLE

    def get(self, index: int) -> object:
        if index < 0 or index >= self.length or self._slots[index] is _HOLE:
            return undefined
        return self._slots[index]

    def set(self, index: object, value: object) -> int:
        valid_index = self._validate_index(index)
        if valid_index >= self.length:
            self._slots.extend([_HOLE] * (valid_index + 1 - self.length))
        self._slots[valid_index] = value
        return self.length

    def delete(self, index: int) -> bool:
        if 0 <= index < self.length:
            self._slots[index] = _HOLE
        return True

    def push(self, *values: object) -> int:
        self._slots.extend(values)
        return self.length

    def pop(self) -> object:
        if not self._slots:
            return undefined
        value = self._slots.pop()
        return undefined if value is _HOLE else value

    def shift(self) -> object:
        if not self._slots:
            return undefined
        value = self._slots.pop(0)
        return undefined if value is _HOLE else value

    def unshift(self, *values: object) -> int:
        self._slots[0:0] = list(values)
        return self.length

    def at(self, index: int) -> object:
        normalized = self.length + index if index < 0 else index
        return self.get(normalized)

    def includes(self, search_element: object, from_index: int = 0) -> bool:
        start = self._search_start(from_index)
        for index in range(start, self.length):
            value = undefined if self._slots[index] is _HOLE else self._slots[index]
            if same_value_zero(value, search_element):
                return True
        return False

    def index_of(self, search_element: object, from_index: int = 0) -> int:
        start = self._search_start(from_index)
        for index in range(start, self.length):
            if self._slots[index] is not _HOLE and strict_equal(self._slots[index], search_element):
                return index
        return -1

    def slice(self, start: int = 0, end: int | None = None) -> "JsArray":
        from_index, to_index = js_slice_indices(self.length, start, end)
        result = JsArray.with_length(to_index - from_index)
        for source_index in range(from_index, to_index):
            if self.has_index(source_index):
                result.set(source_index - from_index, self._slots[source_index])
        return result

    def concat(self, *items: object) -> "JsArray":
        result = self.slice()
        for item in items:
            if isinstance(item, JsArray):
                offset = result.length
                result.set_length(offset + item.length)
                for index, value in item.present_items():
                    result.set(offset + index, value)
            else:
                result.push(item)
        return result

    def fill(self, value: object, start: int = 0, end: int | None = None) -> "JsArray":
        from_index, to_index = js_slice_indices(self.length, start, end)
        for index in range(from_index, to_index):
            self._slots[index] = value
        return self

    def copy_within(self, target: int, start: int = 0, end: int | None = None) -> "JsArray":
        to_index = _relative_index(target, self.length)
        from_index, final_index = js_slice_indices(self.length, start, end)
        count = min(final_index - from_index, self.length - to_index)
        copied = self._slots[from_index : from_index + count]
        for offset, value in enumerate(copied):
            self._slots[to_index + offset] = value
        return self

    def reverse(self) -> "JsArray":
        self._slots.reverse()
        return self

    def splice(self, start: int, delete_count: int | None = None, *items: object) -> "JsArray":
        actual_start = _relative_index(start, self.length)
        actual_delete_count = (
            self.length - actual_start
            if delete_count is None
            else min(max(delete_count, 0), self.length - actual_start)
        )
        removed_slots = self._slots[actual_start : actual_start + actual_delete_count]
        removed = JsArray.with_length(len(removed_slots))
        for index, value in enumerate(removed_slots):
            if value is not _HOLE:
                removed.set(index, value)
        self._slots[actual_start : actual_start + actual_delete_count] = list(items)
        return removed

    def join(self, separator: str = ",") -> str:
        parts: list[str] = []
        for slot in self._slots:
            if slot is _HOLE or slot is undefined or slot is None:
                parts.append("")
            elif isinstance(slot, bool):
                parts.append("true" if slot else "false")
            else:
                parts.append(str(slot))
        return separator.join(parts)

    def to_string(self) -> str:
        return self.join(",")

    def keys(self) -> list[int]:
        return [index for index, value in enumerate(self._slots) if value is not _HOLE]

    def values(self) -> list[object]:
        return [undefined if value is _HOLE else value for value in self._slots]

    def entries(self) -> list[tuple[int, object]]:
        return [
            (index, undefined if value is _HOLE else value)
            for index, value in enumerate(self._slots)
        ]

    def map(self, callback: Callable[[object, int, "JsArray"], object]) -> "JsArray":
        result = JsArray.with_length(self.length)
        for index, value in self.present_items():
            result.set(index, callback(value, index, self))
        return result

    def filter(self, callback: Callable[[object, int, "JsArray"], bool]) -> "JsArray":
        result = JsArray()
        for index, value in self.present_items():
            if callback(value, index, self):
                result.push(value)
        return result

    def reduce(
        self,
        callback: Callable[[object, object, int, "JsArray"], object],
        initial_value: object = undefined,
    ) -> object:
        items = list(self.present_items())
        if initial_value is undefined:
            if not items:
                raise JsRangeError("reduce of empty array with no initial value")
            _, accumulator = items.pop(0)
        else:
            accumulator = initial_value
        for index, value in items:
            accumulator = callback(accumulator, value, index, self)
        return accumulator

    def some(self, callback: Callable[[object, int, "JsArray"], bool]) -> bool:
        return any(callback(value, index, self) for index, value in self.present_items())

    def every(self, callback: Callable[[object, int, "JsArray"], bool]) -> bool:
        return all(callback(value, index, self) for index, value in self.present_items())

    def find(self, callback: Callable[[object, int, "JsArray"], bool]) -> object:
        for index, value in self.present_items():
            if callback(value, index, self):
                return value
        return undefined

    def find_index(self, callback: Callable[[object, int, "JsArray"], bool]) -> int:
        for index, value in self.present_items():
            if callback(value, index, self):
                return index
        return -1

    def for_each(self, callback: Callable[[object, int, "JsArray"], object]) -> None:
        for index, value in self.present_items():
            callback(value, index, self)

    def present_items(self) -> tuple[tuple[int, object], ...]:
        return tuple(
            (index, value) for index, value in enumerate(self._slots) if value is not _HOLE
        )

    def values_with_holes(self) -> tuple[object, ...]:
        return tuple(self._slots)

    def _search_start(self, from_index: int) -> int:
        if from_index >= self.length:
            return self.length
        if from_index >= 0:
            return from_index
        return max(self.length + from_index, 0)


def _relative_index(index: int, length: int) -> int:
    if index < 0:
        return max(length + index, 0)
    return min(index, length)
