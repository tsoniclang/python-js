"""SameValueZero keyed JS Map and Set carriers."""

from tsonic_python_js.equality import same_value_zero


class JsMap:
    __slots__ = ("_entries",)
    _entries: list[tuple[object, object]]

    def __init__(self, entries: list[tuple[object, object]] | None = None) -> None:
        self._entries = []
        if entries is not None:
            for key, value in entries:
                self.set(key, value)

    @property
    def size(self) -> int:
        return len(self._entries)

    def set(self, key: object, value: object) -> "JsMap":
        index = self._find_index(key)
        if index < 0:
            self._entries.append((key, value))
        else:
            self._entries[index] = (self._entries[index][0], value)
        return self

    def get(self, key: object) -> object:
        from tsonic_python_js.values import undefined

        index = self._find_index(key)
        return undefined if index < 0 else self._entries[index][1]

    def has(self, key: object) -> bool:
        return self._find_index(key) >= 0

    def delete(self, key: object) -> bool:
        index = self._find_index(key)
        if index < 0:
            return False
        del self._entries[index]
        return True

    def clear(self) -> None:
        self._entries.clear()

    def keys(self) -> list[object]:
        return [key for key, _ in self._entries]

    def values(self) -> list[object]:
        return [value for _, value in self._entries]

    def entries(self) -> list[tuple[object, object]]:
        return list(self._entries)

    def _find_index(self, key: object) -> int:
        for index, (existing, _) in enumerate(self._entries):
            if same_value_zero(existing, key):
                return index
        return -1


class JsSet:
    __slots__ = ("_values",)
    _values: list[object]

    def __init__(self, values: list[object] | None = None) -> None:
        self._values = []
        if values is not None:
            for value in values:
                self.add(value)

    @property
    def size(self) -> int:
        return len(self._values)

    def add(self, value: object) -> "JsSet":
        if not self.has(value):
            self._values.append(value)
        return self

    def has(self, value: object) -> bool:
        return any(same_value_zero(existing, value) for existing in self._values)

    def delete(self, value: object) -> bool:
        for index, existing in enumerate(self._values):
            if same_value_zero(existing, value):
                del self._values[index]
                return True
        return False

    def clear(self) -> None:
        self._values.clear()

    def values(self) -> list[object]:
        return list(self._values)

    def entries(self) -> list[tuple[object, object]]:
        return [(value, value) for value in self._values]
