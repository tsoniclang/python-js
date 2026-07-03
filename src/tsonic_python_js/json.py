"""JSON helpers over closed JS carriers."""

import json
import math
from typing import Any, cast

from tsonic_python_js.arrays import JsArray
from tsonic_python_js.errors import JsSyntaxError, JsTypeError
from tsonic_python_js.objects import JsObject
from tsonic_python_js.values import undefined


def json_parse(text: str) -> object:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as error:
        raise JsSyntaxError(error.msg) from error
    return _from_json_value(parsed)


def json_stringify(value: object) -> str | None:
    converted = _to_json_value(value, in_array=False)
    if converted is undefined:
        return None
    return json.dumps(converted, separators=(",", ":"), ensure_ascii=False)


def _from_json_value(value: object) -> object:
    if isinstance(value, list):
        return JsArray(_from_json_value(item) for item in cast(list[Any], value))
    if isinstance(value, dict):
        return JsObject(
            (key, _from_json_value(item)) for key, item in cast(dict[str, Any], value).items()
        )
    return value


def _to_json_value(value: object, *, in_array: bool) -> object:
    if value is undefined:
        return None if in_array else undefined
    if isinstance(value, str | bool) or value is None:
        return value
    if isinstance(value, int | float) and not isinstance(value, bool):
        if not math.isfinite(value):
            return None
        return value
    if isinstance(value, JsArray):
        return [_to_json_value(item, in_array=True) for item in value.values()]
    if isinstance(value, JsObject):
        result: dict[str, object] = {}
        for key, item in value.entries():
            converted = _to_json_value(item, in_array=False)
            if converted is not undefined:
                result[key] = converted
        return result
    raise JsTypeError(f"unsupported JSON value: {type(value).__name__}")
