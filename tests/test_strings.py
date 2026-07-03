import math

from tsonic_python_js import char_at, char_code_at, js_slice_indices, utf16_code_units, utf16_len


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


def test_js_slice_indices_normalize_like_js_slice() -> None:
    assert js_slice_indices(10, 1, 3) == (1, 3)
    assert js_slice_indices(10, -3, None) == (7, 10)
    assert js_slice_indices(3, 2, 1) == (2, 2)
    assert js_slice_indices(3, -99, 99) == (0, 3)
