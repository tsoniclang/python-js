"""Every committed Node oracle vector must match JsRegExp exactly."""

import json
from pathlib import Path

from tsonic_python_js import JsRegExp

_VECTORS_PATH = Path(__file__).resolve().parent / "oracle" / "regexp-vectors.json"


def _load_vectors() -> list[dict[str, object]]:
    with _VECTORS_PATH.open(encoding="utf-8") as handle:
        vectors: list[dict[str, object]] = json.load(handle)
    assert isinstance(vectors, list)
    assert vectors
    return vectors


def _run_vector(vector: dict[str, object]) -> tuple[object, object]:
    """Run one vector; returns (operation result, last_index state after)."""

    pattern = vector["pattern"]
    flags = vector["flags"]
    text = vector["input"]
    op = vector["op"]
    assert isinstance(pattern, str)
    assert isinstance(flags, str)
    assert isinstance(text, str)
    regexp = JsRegExp(pattern, flags)
    seed = vector.get("setLastIndex")
    if seed is not None:
        assert isinstance(seed, int)
        regexp.last_index = seed
    if op == "test":
        return regexp.test(text), regexp.last_index
    if op == "search":
        return regexp.search(text), regexp.last_index
    if op == "split":
        limit = vector.get("limit")
        assert limit is None or isinstance(limit, int)
        return regexp.split(text, limit), regexp.last_index
    if op == "replace":
        replacement = vector["replacement"]
        assert isinstance(replacement, str)
        return regexp.replace(text, replacement), regexp.last_index
    assert op == "testSequence"
    calls = vector["calls"]
    assert isinstance(calls, int)
    results: list[bool] = []
    states: list[int] = []
    for _ in range(calls):
        results.append(regexp.test(text))
        states.append(regexp.last_index)
    return results, states


def test_all_vectors_match_the_node_oracle() -> None:
    failures: list[str] = []
    for index, vector in enumerate(_load_vectors()):
        actual, state_after = _run_vector(vector)
        expected = vector["expected"]
        expected_state = vector["lastIndexAfter"]
        if actual != expected or type(actual) is not type(expected):
            failures.append(
                f"vector {index} {vector['op']} /{vector['pattern']}/{vector['flags']} "
                f"on {vector['input']!r}: expected {expected!r}, got {actual!r}"
            )
        if state_after != expected_state:
            failures.append(
                f"vector {index} {vector['op']} /{vector['pattern']}/{vector['flags']} "
                f"on {vector['input']!r}: expected last_index {expected_state!r}, "
                f"got {state_after!r}"
            )
    assert failures == []


def test_oracle_covers_every_operation_and_flag() -> None:
    vectors = _load_vectors()
    operations = {vector["op"] for vector in vectors}
    assert operations == {"test", "search", "split", "replace", "testSequence"}
    flags_seen = {
        flag for vector in vectors if isinstance(vector["flags"], str) for flag in vector["flags"]
    }
    assert flags_seen == {"i", "g", "m"}
    assert any("limit" in vector for vector in vectors)
    assert any("setLastIndex" in vector for vector in vectors)
    assert all("lastIndexAfter" in vector for vector in vectors)
