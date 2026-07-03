"""Tagged dynamic value carrier for compat/unknown lanes."""

from dataclasses import dataclass
from typing import Literal

from tsonic_python_js.arrays import JsArray
from tsonic_python_js.equality import same_value_zero, strict_equal
from tsonic_python_js.errors import JsTypeError
from tsonic_python_js.objects import delete_property, get_property, set_property
from tsonic_python_js.values import undefined

JsValueKind = Literal["undefined", "null", "boolean", "number", "string", "array", "object"]


@dataclass(frozen=True, slots=True)
class JsValue:
    """Closed tagged carrier for dynamic JS compatibility lanes."""

    kind: JsValueKind
    payload: object

    @classmethod
    def from_python(cls, value: object) -> "JsValue":
        from tsonic_python_js.objects import JsObject

        if value is undefined:
            return cls("undefined", undefined)
        if value is None:
            return cls("null", None)
        if isinstance(value, bool):
            return cls("boolean", value)
        if isinstance(value, int | float) and not isinstance(value, bool):
            return cls("number", float(value))
        if isinstance(value, str):
            return cls("string", value)
        if isinstance(value, JsArray):
            return cls("array", value)
        if isinstance(value, JsObject):
            return cls("object", value)
        raise JsTypeError(f"unsupported dynamic JsValue payload: {type(value).__name__}")

    def get_property(self, key: object) -> object:
        return get_property(self.payload, key)

    def set_property(self, key: object, value: object) -> object:
        return set_property(self.payload, key, value)

    def delete_property(self, key: object) -> bool:
        return delete_property(self.payload, key)

    def strict_equal(self, other: object) -> bool:
        rhs = other.payload if isinstance(other, JsValue) else other
        return strict_equal(self.payload, rhs)

    def same_value_zero(self, other: object) -> bool:
        rhs = other.payload if isinstance(other, JsValue) else other
        return same_value_zero(self.payload, rhs)
