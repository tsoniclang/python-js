import math

from tsonic_python_js import JsDate, date_now, date_parse


def test_date_now_returns_whole_epoch_milliseconds() -> None:
    now = date_now()
    assert now == float(int(now))
    assert now > 1_500_000_000_000.0
    assert abs(JsDate.now().get_time() - now) < 60_000.0


def test_date_parse_accepts_closed_iso_utc_subset() -> None:
    assert date_parse("1970-01-01T00:00:00Z") == 0.0
    assert date_parse("1970-01-01T00:00:00.5Z") == 500.0
    assert date_parse("1969-12-31T23:59:59.999Z") == -1.0
    assert date_parse("2024-02-29T12:34:56.789Z") == 1709210096789.0
    assert date_parse(" 2024-01-01T00:00:00Z ") == 1704067200000.0
    assert date_parse("2024-1-1T0:0:0Z") == 1704067200000.0
    assert date_parse("2024-01-01T00:00:00.123456Z") == 1704067200123.0
    assert date_parse("0000-01-01T00:00:00Z") == -62167219200000.0


def test_date_parse_returns_nan_outside_the_subset() -> None:
    for text in [
        "",
        "2024-01-01",
        "2024-01-01T00:00Z",
        "2024-01-01T00:00:00",
        "2024-01-01T00:00:00+00:00",
        "-0001-01-01T00:00:00Z",
        "+2024-01-01T00:00:00Z",
        "2024-13-01T00:00:00Z",
        "2024-00-10T00:00:00Z",
        "2024-01-32T00:00:00Z",
        "2024-01-00T00:00:00Z",
        "2024-01-01T24:00:00Z",
        "2024-01-01T00:60:00Z",
        "2024-01-01T00:00:60Z",
        "2024-01-01T00:00:0aZ",
        "2024-01-01T00:00:00.12aZ",
        "2024-01-01T00:00:00.5",
        "170000",
        "1700000000000",
    ]:
        assert math.isnan(date_parse(text)), text
