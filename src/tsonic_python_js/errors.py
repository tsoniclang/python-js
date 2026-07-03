"""Closed exception types for JS runtime semantic failures."""


class JsError(Exception):
    """Base class for JavaScript compatibility runtime errors."""

    name = "Error"

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        if self.message:
            return f"{self.name}: {self.message}"
        return self.name


class JsTypeError(JsError):
    """JavaScript TypeError equivalent."""

    name = "TypeError"


class JsRangeError(JsError):
    """JavaScript RangeError equivalent."""

    name = "RangeError"


class JsSyntaxError(JsError):
    """JavaScript SyntaxError equivalent."""

    name = "SyntaxError"


class JsReferenceError(JsError):
    """JavaScript ReferenceError equivalent."""

    name = "ReferenceError"


class JsURIError(JsError):
    """JavaScript URIError equivalent."""

    name = "URIError"


class JsUnsupportedError(JsError):
    """Closed hard-reject for unsupported JS compatibility lanes."""

    name = "UnsupportedError"
