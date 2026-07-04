import math

from tsonic_python_js import (
    at,
    char_at,
    char_code_at,
    code_point_at,
    concat,
    js_slice_indices,
    replace,
    to_lower_case,
    to_upper_case,
    undefined,
    utf16_code_units,
    utf16_len,
)


def test_utf16_len_and_code_units_count_surrogates() -> None:
    assert utf16_len("abc") == 3
    assert utf16_len("😀") == 2
    assert utf16_code_units("😀") == (0xD83D, 0xDE00)


def test_char_at_uses_utf16_code_units() -> None:
    assert char_at("abc", 1) == "b"
    assert char_at("abc", 5) == ""
    assert char_at("abc", -1) == ""
    assert char_at("😀", 0) == "\ud83d"
    assert char_at("😀", 1) == "\ude00"


def test_char_code_at_returns_nan_out_of_range() -> None:
    assert char_code_at("hello", 1) == 101.0
    assert char_code_at("😀", 0) == float(0xD83D)
    assert char_code_at("😀", 1) == float(0xDE00)
    assert math.isnan(char_code_at("hello", -1))
    assert math.isnan(char_code_at("hello", 99))


def test_at_supports_negative_indexes_and_returns_undefined_out_of_range() -> None:
    assert at("abc", 0) == "a"
    assert at("abc", -1) == "c"
    assert at("abc", 3) is undefined
    assert at("abc", -4) is undefined
    assert at("", 0) is undefined
    assert at("😀", -1) == "\ude00"


def test_code_point_at_combines_surrogate_pairs() -> None:
    assert code_point_at("a😀b", 0) == 97.0
    assert code_point_at("a😀b", 1) == float(0x1F600)
    assert code_point_at("a😀b", 2) == float(0xDE00)
    assert code_point_at("a😀b", 3) == float(ord("b"))
    assert code_point_at("a😀b", 4) is undefined
    assert code_point_at("abc", -1) is undefined


def test_concat_joins_string_parts() -> None:
    assert concat("a") == "a"
    assert concat("a", "b", "c") == "abc"
    assert concat("", "😀", "") == "😀"


def test_replace_rewrites_first_occurrence_only() -> None:
    assert replace("aa", "a", "b") == "ba"
    assert replace("abc", "z", "y") == "abc"
    assert replace("abc", "", "X") == "Xabc"
    assert replace("😀😀", "\ude00", "!") == "\ud83d!😀"


def test_replace_honors_js_replacement_tokens() -> None:
    assert replace("price", "ri", "$$") == "p$ce"
    assert replace("price", "ri", "$$&") == "p$&ce"
    assert replace("abcd", "bc", "[$&]") == "a[bc]d"
    assert replace("abcd", "bc", "<$`>") == "a<a>d"
    assert replace("abcd", "bc", "<$'>") == "a<d>d"
    assert replace("abc", "b", "$1$x$") == "a$1$x$c"


def test_case_conversion_uses_unicode_default_full_mappings() -> None:
    assert to_upper_case("straße") == "STRASSE"
    assert to_upper_case("abc😀") == "ABC😀"
    assert to_lower_case("İ") == "i̇"
    assert to_lower_case("ΟΣ") == "ος"
    assert to_lower_case("\ud83d") == "\ud83d"
    assert to_upper_case("já") == "JÁ"


def test_js_slice_indices_normalize_like_js_slice() -> None:
    assert js_slice_indices(10, 1, 3) == (1, 3)
    assert js_slice_indices(10, -3, None) == (7, 10)
    assert js_slice_indices(3, 2, 1) == (2, 2)
    assert js_slice_indices(3, -99, 99) == (0, 3)
