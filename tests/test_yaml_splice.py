"""Tests for the in-place YAML edit behind the configuration writer (#1198): a
change edits the lines of the keys it sets, and every other byte of the
document stays as written."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from project_kit import project_config
from project_kit import yaml_splice as ys

# Comments, blank lines, nested lists in two layouts, flow collections and
# quoted strings: what a hand-kept configuration holds.
RICH = """\
# A header comment.
name: "project"  # quoted, with a comment

# A block between keys.
docs:
  user: 'docs/'
  internal: tech-docs/
friction:
  mode: enforcing
  # Places, commented.
  places:
    # first
    - CONTRIBUTING.md
    - "README.md"

  exclude: [a/, 'b/', "c d/"]
  surface:
  - src/**
  - tests/**
  # A comment after the list.
process:
  journal: {enabled: true, committed: false}
"""


def _spliced(text: str, mutate: Callable[[Any], None]) -> str:
    data = YAML().load(text)
    if data is None:
        data = CommentedMap()
    mutate(data)
    return ys.splice(text, data)


def _set(*path_and_value: Any) -> Callable[[Any], None]:
    """The writers' mutation: the key path set to the value, mappings made on the way."""
    *path, value = path_and_value
    return lambda data: project_config.set_path(data, tuple(path), value)


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_a_scalar_changes_its_value_and_nothing_else(newline: str) -> None:
    text = RICH.replace("\n", newline)
    after = _spliced(text, _set("friction", "mode", "warning"))
    assert after == text.replace("  mode: enforcing", "  mode: warning")


def test_a_quoted_value_keeps_its_quotes_and_its_comment() -> None:
    after = _spliced(RICH, _set("name", "renamed"))
    assert after == RICH.replace('name: "project"', 'name: "renamed"')


def test_a_flow_list_stays_a_flow_list() -> None:
    after = _spliced(RICH, _set("friction", "exclude", ["x/", "y, z/"]))
    assert after == RICH.replace("""[a/, 'b/', "c d/"]""", "[x/, 'y, z/']")


def test_a_flow_mapping_gets_a_new_key_inside_its_braces() -> None:
    after = _spliced(RICH, _set("process", "journal", "logs", "here"))
    assert after == RICH.replace("committed: false}", "committed: false, logs: here}")


def test_a_list_replaces_the_lines_of_its_key_in_that_list_s_own_layout() -> None:
    places = _spliced(RICH, _set("friction", "places", ["one.md", "two.md"]))
    old_places = '  places:\n    # first\n    - CONTRIBUTING.md\n    - "README.md"\n'
    assert places == RICH.replace(old_places, "  places:\n    - one.md\n    - two.md\n")

    # The dashes of `surface` sit at its key's column; the comment after it stays.
    surface = _spliced(RICH, _set("friction", "surface", ["lib/**"]))
    assert surface == RICH.replace("  - src/**\n  - tests/**\n", "  - lib/**\n")


def test_a_new_key_comes_after_its_last_sibling() -> None:
    after = _spliced(RICH, _set("docs", "extra", "x/"))
    assert after == RICH.replace(
        "  internal: tech-docs/\n", "  internal: tech-docs/\n  extra: x/\n"
    )


def test_a_new_key_after_a_list_comes_before_the_comment_that_follows_it() -> None:
    after = _spliced(RICH, _set("friction", "added", True))
    assert after == RICH.replace("  - tests/**\n", "  - tests/**\n  added: true\n")


def test_a_key_whose_mappings_are_missing_brings_them_in_the_document_s_layout() -> None:
    after = _spliced(RICH, _set("connections", "providers", "pkit::work-tracking", "pm"))
    assert after == RICH + "connections:\n  providers:\n    pkit::work-tracking: pm\n"

    # A new list takes the layout of the document's first list.
    listed = _spliced(RICH, _set("extra", ["a", "b"]))
    assert listed == RICH + "extra:\n  - a\n  - b\n"


def test_an_empty_value_becomes_the_mapping_set_under_it() -> None:
    text = "friction:\nname: x\n"
    assert _spliced(text, _set("friction", "mode", "warning")) == (
        "friction:\n  mode: warning\nname: x\n"
    )


def test_a_text_of_comments_only_keeps_them() -> None:
    text = "# nothing yet\n\n# still nothing\n"
    assert _spliced(text, _set("name", "alpha")) == text + "name: alpha\n"


def test_a_last_line_without_a_line_break_gets_one_before_the_new_key() -> None:
    assert _spliced("name: alpha", _set("docs", "user", "d/")) == "name: alpha\ndocs:\n  user: d/\n"


def test_setting_what_is_already_set_changes_nothing() -> None:
    assert _spliced(RICH, _set("friction", "mode", "enforcing")) == RICH
    assert _spliced(RICH, lambda data: None) == RICH


def test_several_keys_are_each_edited_in_place() -> None:
    def mutate(data: Any) -> None:
        data["friction"]["mode"] = "warning"
        data["docs"]["user"] = "guide/"
        data["repository"] = {"default-branch": "main"}

    after = _spliced(RICH, mutate)
    expected = (
        RICH.replace("  mode: enforcing", "  mode: warning").replace("'docs/'", "'guide/'")
        + "repository:\n  default-branch: main\n"
    )
    assert after == expected


def test_removing_a_key_is_refused() -> None:
    with pytest.raises(ys.SpliceRefused, match=r"removes `friction\.mode`"):
        _spliced(RICH, lambda data: data["friction"].pop("mode"))


def test_mixed_line_endings_are_refused() -> None:
    with pytest.raises(ys.SpliceRefused, match="mixes line endings"):
        _spliced("a: 1\r\nb: 2\n", _set("a", 3))


def test_a_change_that_would_reach_past_its_key_is_refused() -> None:
    # `other` is `base` through an alias: editing it in the text edits `base` too.
    text = "base: &b {x: 1}\nother: *b\n"

    def mutate(data: Any) -> None:
        data["other"] = {"x": 2}

    with pytest.raises(ys.SpliceRefused, match="change more than those keys"):
        _spliced(text, mutate)


def test_a_key_set_through_a_merge_is_written_as_its_own() -> None:
    text = "base: &b {x: 1}\nchild:\n  <<: *b\n  y: 2\n"
    assert _spliced(text, _set("child", "x", 3)) == text + "  x: 3\n"
