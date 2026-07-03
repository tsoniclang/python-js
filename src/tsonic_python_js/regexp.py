"""RegExp hard-reject catalog."""

from tsonic_python_js.errors import JsUnsupportedError

REGEXP_STATUS = "hard-reject: no JS-compatible RegExp engine or proven subset is claimed"


def unsupported_regexp(*_args: object, **_kwargs: object) -> object:
    raise JsUnsupportedError(REGEXP_STATUS)
