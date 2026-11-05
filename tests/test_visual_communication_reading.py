"""visual-communication's one reading of every file (DEC-006 point 6): YAML 1.2 with
timestamps as text, JSON, and canonical JSON by RFC 8785."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from tests.in_process import load

(reading,) = load("visual-communication", "reading")


# --- YAML ---------------------------------------------------------------------------------------


def test_yaml_is_read_at_1_2_so_yes_and_no_stay_text() -> None:
    assert reading.load_yaml("a: no\nb: yes\nc: on\nd: off\ne: y\n") == {
        "a": "no",
        "b": "yes",
        "c": "on",
        "d": "off",
        "e": "y",
    }


def test_a_timestamp_is_read_as_the_text_it_is_written_as() -> None:
    assert reading.load_yaml("day: 2026-11-01\nmoment: 2026-11-01T10:00:00Z\n") == {
        "day": "2026-11-01",
        "moment": "2026-11-01T10:00:00Z",
    }


def test_a_directive_of_yaml_1_2_is_read_and_one_of_1_1_refused() -> None:
    assert reading.load_yaml("%YAML 1.2\n---\na: no\n") == {"a": "no"}
    with pytest.raises(reading.ReadError, match=r"declares YAML 1\.1"):
        reading.load_yaml("# a comment\n%YAML 1.1\n---\na: no\n", "x.yaml")


@pytest.mark.parametrize(
    ("text", "said"),
    [
        ("a: 1\na: 2\n", "does not parse"),
        ("a: 1\n---\nb: 2\n", "does not parse"),
        ("a: !!binary aGVsbG8=\n", "bytes"),
        ("a: !!set {x}\n", "set"),
        ("1: a\n", "not text"),
        ("a: .inf\n", "JSON cannot hold"),
    ],
)
def test_yaml_that_json_cannot_hold_or_that_is_ambiguous_is_refused(text: str, said: str) -> None:
    with pytest.raises(reading.ReadError, match=said):
        reading.load_yaml(text, "x.yaml")


def test_read_yaml_names_a_file_that_is_not_utf8(tmp_path: Path) -> None:
    path = tmp_path / "x.yaml"
    path.write_bytes(b"a: \xff\n")
    with pytest.raises(reading.ReadError, match="not UTF-8"):
        reading.read_yaml(path)


# --- JSON ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("text", ['{"a": 1, "a": 2}', '{"a": NaN}', '{"a": Infinity}', "{"])
def test_json_with_a_duplicate_key_a_constant_or_a_syntax_error_is_refused(text: str) -> None:
    with pytest.raises(reading.ReadError, match="does not parse as JSON"):
        reading.load_json(text)


# --- canonical text (RFC 8785) ------------------------------------------------------------------


def test_the_rfc_8785_example_gives_its_canonical_text() -> None:
    """RFC 8785 section 3.2.2's example, numbers, a string and literals together."""
    value = reading.load_json(
        '{"numbers": [333333333.33333329, 1E30, 4.50, 2e-3, 0.000000000000000000000000001],'
        ' "string": "\\u20ac$\\u000F\\u000aA\'\\u0042\\u0022\\u005c\\\\\\"\\/",'
        ' "literals": [null, true, false]}'
    )
    assert reading.canonical_json(value) == (
        '{"literals":[null,true,false],'
        '"numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27],'
        '"string":"€$\\u000f\\nA\'B\\"\\\\\\\\\\"/"}'
    )


def test_keys_sort_by_their_utf16_code_units() -> None:
    """RFC 8785 section 3.2.3's example: an astral character sorts by its surrogates."""
    value = {
        "\u20ac": "Euro Sign",
        "\r": "Carriage Return",
        "\ufb33": "Hebrew Letter Dalet With Dagesh",
        "1": "One",
        "\U0001f600": "Emoji: Grinning Face",
        "\u0080": "Control",
        "\u00f6": "Latin Small Letter O With Diaeresis",
    }
    text = reading.canonical_json(value)
    order = [
        "Carriage Return",
        "One",
        "Control",
        "Latin Small Letter O With Diaeresis",
        "Euro Sign",
        "Emoji: Grinning Face",
        "Hebrew Letter Dalet With Dagesh",
    ]
    assert [text.index(name) for name in order] == sorted(text.index(name) for name in order)


@pytest.mark.parametrize(
    ("number", "text"),
    [
        (0, "0"),
        (-0.0, "0"),
        (1.0, "1"),
        (-1.5, "-1.5"),
        (123.456, "123.456"),
        (1e20, "100000000000000000000"),
        (1e21, "1e+21"),
        (1e-6, "0.000001"),
        (1e-7, "1e-7"),
        (5e-324, "5e-324"),
        (1.7976931348623157e308, "1.7976931348623157e+308"),
        (0.1 + 0.2, "0.30000000000000004"),
        (9007199254740991, "9007199254740991"),
        (2.0**53, "9007199254740992"),
    ],
)
def test_numbers_are_written_as_ecmascript_writes_them(number: float, text: str) -> None:
    assert reading.canonical_json(number) == text


@pytest.mark.parametrize("value", [2**53, math.nan, math.inf, b"x", {1: "a"}, {"a": {1, 2}}])
def test_what_json_cannot_hold_exactly_has_no_canonical_text(value: object) -> None:
    with pytest.raises(reading.ReadError):
        reading.canonical_json(value)


def test_a_lone_surrogate_has_no_canonical_bytes() -> None:
    with pytest.raises(reading.ReadError, match="surrogate"):
        reading.canonical_bytes("\ud800")


def test_one_value_written_two_ways_gives_one_canonical_text() -> None:
    from_yaml = reading.load_yaml("b: [1, 2.0]\na: {y: 1, x: true}\n")
    from_json = reading.load_json('{"a": {"x": true, "y": 1.0}, "b": [1.0, 2]}')
    assert reading.canonical_bytes(from_yaml) == reading.canonical_bytes(from_json)
    assert reading.canonical_json(from_yaml) == '{"a":{"x":true,"y":1},"b":[1,2]}'


def test_sha256_is_lower_case_hexadecimal() -> None:
    assert reading.sha256(b"") == (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
