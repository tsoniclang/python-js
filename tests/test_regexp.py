"""Construction-rejection surface and direct parser/vm edge tests for JsRegExp."""

from tests.assertions import raises
from tsonic_python_js import (
    REGEXP_STATUS,
    JsRegExp,
    JsSyntaxError,
    JsUnsupportedError,
    unsupported_regexp,
)

_UNSUPPORTED_PATTERNS = [
    # lazy quantifiers
    "a*?",
    "a+?",
    "a??",
    "a{1,2}?",
    "a{2}?",
    # backreferences
    "(a)\\1",
    "\\5",
    "\\k<name>",
    # lookaround
    "(?=a)",
    "(?!a)",
    "(?<=a)",
    "(?<!a)",
    # named groups
    "(?<name>a)",
    # word-boundary assertions
    "\\bword",
    "no\\B",
    # property escapes
    "\\p{L}",
    "\\P{L}",
    "[\\p{L}]",
    # control escapes and unrecognized escapes
    "\\cA",
    "[\\cA]",
    "\\q",
    "[\\q]",
    # legacy octal escapes
    "\\01",
    "[\\1]",
    # \u{...} needs the u flag; malformed hex stays out of the subset
    "\\u{41}",
    "\\xZZ",
    "\\u12",
    # bare braces and unbounded quantifier operands
    "{",
    "}",
    "a{",
    "a{,2}",
    "a{1001}",
    # class ranges bounded by a class escape
    "[\\d-z]",
    "[a-\\d]",
]

_SYNTAX_ERROR_PATTERNS = [
    "(",
    "(a",
    ")",
    "a)",
    "(?)",
    "[",
    "[a",
    "[a-",
    "a\\",
    "[z-a]",
    "a{2,1}",
    "*",
    "+",
    "?",
    "^*",
    "$+",
]

_UNSUPPORTED_FLAGS = ["u", "y", "s", "d", "v", "x", "gu"]


def test_out_of_subset_constructs_are_rejected_at_construction() -> None:
    for pattern in _UNSUPPORTED_PATTERNS:
        with raises(JsUnsupportedError):
            JsRegExp(pattern)


def test_malformed_patterns_raise_syntax_errors() -> None:
    for pattern in _SYNTAX_ERROR_PATTERNS:
        with raises(JsSyntaxError):
            JsRegExp(pattern)


def test_flags_outside_igm_and_duplicates_are_rejected() -> None:
    for flags in _UNSUPPORTED_FLAGS:
        with raises(JsUnsupportedError):
            JsRegExp("a", flags)
    for flags in ("ii", "gg", "mm", "gig"):
        with raises(JsSyntaxError):
            JsRegExp("a", flags)


def test_split_rejects_capturing_groups() -> None:
    with raises(JsUnsupportedError):
        JsRegExp("(,)").split("a,b")
    assert JsRegExp("(?:,)").split("a,b") == ["a", "b"]


def test_rejection_status_and_helper_stay_available() -> None:
    assert REGEXP_STATUS.startswith("hard-reject")
    with raises(JsUnsupportedError):
        unsupported_regexp("x")


def test_compiled_regexp_exposes_source_and_flags() -> None:
    regexp = JsRegExp("a(?:b|c)", "gim")
    assert regexp.source == "a(?:b|c)"
    assert regexp.flags == "gim"


def test_supported_escapes_parse_and_match() -> None:
    assert JsRegExp("\\x41").test("A")
    assert JsRegExp("\\u0041").test("A")
    assert JsRegExp("\\0").test("a\x00b")
    assert JsRegExp("[\\b]").test("a\x08b")
    assert JsRegExp("\\n\\r\\t\\f\\v").test("\n\r\t\f\v")
    assert JsRegExp("\\-\\!").test("-!")


def test_lone_surrogate_escapes_match_utf16_code_units() -> None:
    assert JsRegExp("\\ud83d").test("\U0001f600")
    assert JsRegExp("\\ude00").test("\U0001f600")
    assert JsRegExp("^\\ud83d\\ude00$").test("\U0001f600")
    assert not JsRegExp("^\\ud83d$").test("\U0001f600")


def test_empty_and_negated_empty_classes() -> None:
    assert not JsRegExp("[]").test("anything")
    assert JsRegExp("[^]").test("\n")
    assert JsRegExp("^[^]$").test("x")


def test_quantifier_bounds_are_expanded_up_to_the_cap() -> None:
    assert JsRegExp("a{1000}").test("a" * 1000)
    assert not JsRegExp("^a{1000}$").test("a" * 999)


def test_empty_iterations_of_unbounded_repeats_terminate() -> None:
    assert JsRegExp("(?:a*)*b").test("aab")
    assert not JsRegExp("(?:a*)*b").test("aac")
    assert JsRegExp("(?:a|)+").test("")


def test_capture_slots_reset_between_repeat_iterations() -> None:
    assert JsRegExp("(?:(a)|(b))+").replace("ab", "<$1|$2>") == "<|b>"


def test_backtracking_restores_captures_on_failure() -> None:
    assert JsRegExp("(a+)b|(a+)c").replace("aac", "[$1|$2]") == "[|aa]"


def test_replace_tokens_and_missing_groups() -> None:
    regexp = JsRegExp("(x)?(y)")
    assert regexp.replace("y", "<$1|$2>") == "<|y>"
    assert regexp.replace("y", "$$ $& $` $'") == "$ y  "
    assert JsRegExp("y").replace("ay!", "[$`|$&|$']") == "a[a|y|!]!"


def test_search_reports_utf16_code_unit_indexes() -> None:
    assert JsRegExp("b").search("\U0001f600b") == 2
    assert JsRegExp("q").search("abc") == -1


def test_split_limit_matches_js_uint32_semantics() -> None:
    regexp = JsRegExp(",")
    assert regexp.split("a,b,c", 0) == []
    assert regexp.split("a,b,c", 2) == ["a", "b"]
    assert regexp.split("a,b,c", -1) == ["a", "b", "c"]
    assert regexp.split("a,b,c") == ["a", "b", "c"]


def test_multiline_anchors_and_ignore_case_matching() -> None:
    assert JsRegExp("^b$", "m").test("a\nb\nc")
    assert not JsRegExp("^b$").test("a\nb\nc")
    assert JsRegExp("[a-z]+", "i").test("HELLO")
    assert JsRegExp("\u03c3", "i").test("\u03c2")  # sigma folds onto final sigma
    assert not JsRegExp("s", "i").test("\u017f")  # long s is ASCII-guarded in non-u mode
