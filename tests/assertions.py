from collections.abc import Generator
from contextlib import contextmanager


@contextmanager
def raises[E: BaseException](expected: type[E]) -> Generator[None]:
    try:
        yield
    except expected:
        return
    except Exception:
        raise
    raise AssertionError(f"expected {expected.__name__}")
