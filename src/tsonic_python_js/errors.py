"""Closed exception types for JS runtime semantic failures."""


class JsError(Exception):
    """Base class for JavaScript compatibility runtime errors."""


class JsTypeError(JsError):
    """JavaScript TypeError equivalent."""


class JsRangeError(JsError):
    """JavaScript RangeError equivalent."""


class JsSyntaxError(JsError):
    """JavaScript SyntaxError equivalent."""


class JsReferenceError(JsError):
    """JavaScript ReferenceError equivalent."""
