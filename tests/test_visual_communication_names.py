"""The shapes of names, ids, token paths and language tags (DEC-002 point 4, DEC-004 points 4
and 7), and that the schemas hold the same shapes as the code."""

from __future__ import annotations

import json
import re

import pytest

from tests.in_process import load
from tests.visual_communication_project import SCHEMAS

(names,) = load("visual-communication", "names")

DEFS = json.loads((SCHEMAS / "defs.schema.json").read_text(encoding="utf-8"))["$defs"]


@pytest.mark.parametrize("name", ["a", "figure", "text-primary", "h2", "a-1-b", "x9"])
def test_a_name_is_lower_case_words_joined_by_single_hyphens(name: str) -> None:
    assert names.is_name(name)


@pytest.mark.parametrize(
    "name", ["", "1a", "-a", "a-", "a--b", "A", "a_b", "a.b", "a/b", "a#b", "a b", 1, None]
)
def test_what_is_not_a_name(name: object) -> None:
    assert not names.is_name(name)


@pytest.mark.parametrize("word", ["y", "n", "yes", "no", "on", "off", "true", "false", "null"])
def test_a_name_is_never_a_word_yaml_reads_as_a_yes_or_no_or_nothing(word: str) -> None:
    assert not names.is_name(word)
    assert names.is_name(f"{word}-1")


@pytest.mark.parametrize("path", ["space.3", "text-primary", "grey.900", "type.body", "a.1-b"])
def test_a_token_path_is_segments_joined_by_dots(path: str) -> None:
    assert names.is_token_path(path)


@pytest.mark.parametrize("path", ["", "a.", ".a", "a..b", "A.b", "a.b_c", "a/b", "{a.b}"])
def test_what_is_not_a_token_path(path: str) -> None:
    assert not names.is_token_path(path)


@pytest.mark.parametrize("value", ["a", "Fig_1", "x-y", "nope", "On1", "yesno", "nullish"])
def test_an_id_takes_letters_digits_hyphens_and_underscores(value: str) -> None:
    assert names.is_id(value)


@pytest.mark.parametrize(
    "value",
    ["", "1a", "_a", "a.b", "y", "N", "Yes", "no", "TRUE", "off", "null", "Null", "NULL"],
)
def test_an_id_is_never_a_word_yaml_reads_as_a_yes_or_no_or_nothing(value: str) -> None:
    assert not names.is_id(value)


@pytest.mark.parametrize("tag", ["en", "cs", "deu", "en-gb", "zh-hant-tw", "sl-rozaj-biske"])
def test_a_language_is_a_lower_case_tag(tag: str) -> None:
    assert names.is_language(tag)


@pytest.mark.parametrize("tag", ["", "e", "EN", "en-GB", "en_gb", "english", "en-x"])
def test_what_is_not_a_language(tag: str) -> None:
    assert not names.is_language(tag)


def test_a_use_is_a_library_and_a_component() -> None:
    assert names.split_use("foundations/figure") == ("foundations", "figure")
    assert names.split_use("piece/legend") == ("piece", "legend")


@pytest.mark.parametrize("use", ["figure", "foundations/", "/figure", "a/b/c", "a/B", "a@1/b"])
def test_a_use_of_another_shape_is_refused(use: str) -> None:
    with pytest.raises(ValueError, match="is not `<library>/<component>`"):
        names.split_use(use)


def test_a_library_name_is_neither_reserved_nor_a_shared_top_group() -> None:
    assert names.library_name_problem("test-brand", ("space", "type")) is None
    assert "reserved" in (names.library_name_problem("piece") or "")
    assert "reserved" in (names.library_name_problem("component") or "")
    assert "top group" in (names.library_name_problem("space", ("space", "type")) or "")
    assert "not a name" in (names.library_name_problem("Brand") or "")


# --- the schemas hold the code's shapes ---------------------------------------------------------


@pytest.mark.parametrize(
    ("definition", "pattern"),
    [("name", "NAME"), ("id", "ID"), ("language", "LANGUAGE")],
)
def test_the_schemas_hold_the_pattern_the_code_holds(definition: str, pattern: str) -> None:
    assert DEFS[definition]["pattern"] == getattr(names, pattern)


def test_the_schemas_token_path_is_the_codes_segment_joined_by_dots() -> None:
    segment = names.SEGMENT.strip("^$")
    assert DEFS["token-path"]["pattern"] == f"^{segment}(\\.{segment})*$"


def test_the_schemas_refuse_the_ids_the_code_refuses() -> None:
    refused = re.compile(DEFS["id"]["not"]["pattern"])
    for word in names.YAML_WORDS:
        for written in (word, word.upper(), word.capitalize()):
            assert refused.match(written), written
    assert not refused.match("nope")


def test_the_schemas_refuse_the_names_the_code_refuses() -> None:
    assert DEFS["name"]["not"]["enum"] == list(names.YAML_WORDS)


def test_the_schemas_reserve_the_library_names_the_code_reserves() -> None:
    (reserved,) = [part["not"]["enum"] for part in DEFS["library-name"]["allOf"] if "not" in part]
    assert sorted(reserved) == sorted(names.RESERVED_LIBRARY_NAMES)
