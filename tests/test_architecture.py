import ast
import inspect
from pathlib import Path

import tsonic_python_js

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "tsonic_python_js"
TESTS = ROOT / "tests"

FORBIDDEN_IMPORT_PREFIXES = (
    "tsts",
    "tsonic",
    "target_api",
    "quickjs",
    "js2py",
    "py_mini_racer",
    "v8",
    "node",
    "npm",
)
FORBIDDEN_SOURCE_MARKERS = (
    ".analysis",
    "eval(",
    "exec(",
    "getattr(",
    "setattr(",
    "__dict__",
    "subprocess.run(['node'",
    'subprocess.run(["node"',
    "subprocess.Popen(['node'",
    'subprocess.Popen(["node"',
)


def _python_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def test_product_sources_do_not_import_forbidden_runtime_layers() -> None:
    violations: list[str] = []
    for path in _python_files(SRC):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                names = [node.module]
            else:
                continue
            for name in names:
                if name == "tsonic_python_js":
                    continue
                if name.startswith("tsonic_python_js."):
                    continue
                if any(
                    name == prefix or name.startswith(f"{prefix}.")
                    for prefix in FORBIDDEN_IMPORT_PREFIXES
                ):
                    violations.append(f"{path}: forbidden import {name}")
    assert violations == []


def test_product_sources_do_not_contain_forbidden_shortcuts() -> None:
    violations: list[str] = []
    for path in _python_files(SRC):
        source = path.read_text(encoding="utf-8")
        for marker in FORBIDDEN_SOURCE_MARKERS:
            if marker in source:
                violations.append(f"{path}: contains {marker}")
    assert violations == []


def test_every_exported_public_api_has_direct_test_reference() -> None:
    test_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in _python_files(TESTS)
        if path.name != "test_architecture.py"
    )
    missing: list[str] = []
    for name in tsonic_python_js.__all__:
        value = getattr(tsonic_python_js, name)
        assert value is not None
        if not _contains_word(test_text, name):
            missing.append(name)
        if inspect.isfunction(value) or inspect.isclass(value):
            assert value.__module__.startswith("tsonic_python_js")
    assert missing == []


def _contains_word(text: str, needle: str) -> bool:
    for index in _find_all(text, needle):
        before = text[index - 1] if index > 0 else ""
        after_index = index + len(needle)
        after = text[after_index] if after_index < len(text) else ""
        if not _is_identifier_char(before) and not _is_identifier_char(after):
            return True
    return False


def _find_all(text: str, needle: str) -> list[int]:
    indexes: list[int] = []
    start = 0
    while True:
        index = text.find(needle, start)
        if index < 0:
            return indexes
        indexes.append(index)
        start = index + len(needle)


def _is_identifier_char(char: str) -> bool:
    return char == "_" or char.isalnum()
