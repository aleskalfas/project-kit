"""The records the commands keep, each read and written one way (`_lib/records.py`): a
record's value, read with one error; a record written whole under its comment, its time
quoted; and one key written into a file, every other byte kept."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.in_process import load
from tests.visual_communication_project import bound, write, yaml_text

records, reading = load("visual-communication", "records", "reading")


def test_a_record_is_read_as_its_kind(tmp_path: Path) -> None:
    path = write(tmp_path / "exports.yaml", yaml_text(bound("exports", versions=[])))
    assert records.read(path, "exports") == bound("exports", versions=[])


def test_a_record_of_another_kind_or_one_that_does_not_parse_is_one_error(
    tmp_path: Path,
) -> None:
    other = write(tmp_path / "findings.yaml", yaml_text(bound("findings", findings=[])))
    with pytest.raises(records.RecordError, match="names the schema `visual-communication:find"):
        records.read(other, "exports")
    broken = write(tmp_path / "exports.yaml", "versions: [\n")
    with pytest.raises(records.RecordError, match="does not parse as YAML"):
        records.read(broken, "exports")


def test_a_record_written_whole_opens_with_its_comment_set_apart() -> None:
    assert records.text({"a": [1]}, ["One.", "", "Two."]) == "# One.\n#\n# Two.\n\na:\n  - 1\n"


def test_a_comment_of_one_line_may_sit_right_above_the_record() -> None:
    text = records.text({"a": 1}, ["Written by a command."], apart=False)
    assert text == "# Written by a command.\na: 1\n"


def test_a_time_is_written_quoted_and_reads_back_as_the_same_text() -> None:
    entry = {"version": 1, "recorded": {"time": "2026-11-03T10:00:00Z", "state": "draft"}}
    text = records.text(records.quoted_time(entry), [])
    assert "  time: '2026-11-03T10:00:00Z'\n" in text
    assert reading.load_yaml(text) == entry


def test_a_key_is_written_in_its_place_and_every_other_byte_is_kept() -> None:
    original = records.BOM + "# Kept.\r\nnames:\r\n  a: x  # moved\r\nrest: 1\r\n"
    assert records.with_mapping(original, "names", {"b": "y", "a": "x"}, each="name") == (
        records.BOM + "# Kept.\r\nnames:\r\n  b: y\r\n  a: x\r\nrest: 1\r\n"
    )


def test_a_key_the_file_lacks_is_added_at_its_end() -> None:
    assert records.with_mapping("rest: 1", "names", {}, each="name") == "rest: 1\nnames: {}\n"


def test_a_key_that_would_not_read_back_is_refused_naming_what_a_line_holds() -> None:
    original = "names:\n  a: x\n# A comment at the left edge.\n  b: y\nrest: 1\n"
    with pytest.raises(records.RecordError, match="`names:` as a block mapping, one name a line"):
        records.with_mapping(original, "names", {"a": "x"}, each="name")


def test_an_entry_of_the_files_top_ends_the_file_every_other_byte_kept() -> None:
    original = records.BOM + "a: 1\r\n# The end.\r\n"
    assert records.with_entry(original, [], "b", 2, each="field") == original + "b: 2\r\n"
    assert records.with_entry("a: 1", [], "b", 2, each="field") == "a: 1\nb: 2\n"


def test_an_entry_the_files_top_holds_or_cannot_take_is_refused() -> None:
    with pytest.raises(records.RecordError, match="the file holds `a` already"):
        records.with_entry("a: 1\n", [], "a", 2, each="field")
    with pytest.raises(records.RecordError, match="write the file as a block mapping"):
        records.with_entry("{a: 1}\n", [], "b", 2, each="field")


def test_an_entry_is_added_last_to_a_block_mapping_at_its_indent() -> None:
    original = records.BOM + "a:\r\n    b:  # kept\r\n        c: 1\r\n\r\n# The end.\r\n"
    assert records.with_entry(original, ["a"], "d", {"e": [1]}, each="item") == (
        records.BOM
        + "a:\r\n    b:  # kept\r\n        c: 1\r\n    d:\r\n      e:\r\n        - 1\r\n"
        + "\r\n# The end.\r\n"
    )


def test_an_entry_is_added_to_a_nested_mapping_the_path_leads_to() -> None:
    original = "a:\n  b:\n    c:\n      x: 1\n  d:\n    c:\n      y: 2\n"
    assert records.with_entry(original, ["a", "d", "c"], "z", 3, each="item") == (
        "a:\n  b:\n    c:\n      x: 1\n  d:\n    c:\n      y: 2\n      z: 3\n"
    )


def test_an_entry_is_added_after_the_last_past_comments_at_any_indent() -> None:
    original = "a:\n  x: 1\n# At the left edge.\n  y: 2\n# Of b.\nb: 1\n"
    assert records.with_entry(original, ["a"], "z", 3, each="item") == (
        "a:\n  x: 1\n# At the left edge.\n  y: 2\n  z: 3\n# Of b.\nb: 1\n"
    )


def test_an_entry_is_added_in_flow_to_a_mapping_written_on_its_key_line() -> None:
    assert records.with_entry("a: {}  # none\n", ["a"], "b", {"c": 1}, each="item") == (
        "a: {b: {c: 1}}  # none\n"
    )
    assert records.with_entry("a: {x: 1}", ["a"], "b", 2, each="item") == "a: {x: 1, b: 2}"


def test_an_entry_the_mapping_holds_already_is_refused() -> None:
    with pytest.raises(records.RecordError, match="`a` holds `b` already"):
        records.with_entry("a:\n  b: 1\n", ["a"], "b", 2, each="item")


def test_an_entry_where_the_text_does_not_show_the_mapping_is_refused() -> None:
    refusal = "write `a` as a block mapping, one item an entry"
    with pytest.raises(records.RecordError, match=f"`a` is not a mapping: {refusal}"):
        records.with_entry("a: [1]\n", ["a"], "b", 2, each="item")
    with pytest.raises(records.RecordError, match=f"^{refusal}$"):
        records.with_entry("a: {\n  x: 1}\n", ["a"], "b", 2, each="item")
    with pytest.raises(records.RecordError, match=f"^{refusal}$"):
        records.with_entry("a:\n  {x: 1}\n", ["a"], "b", 2, each="item")


@pytest.mark.parametrize(
    ("original", "path", "said"),
    [
        pytest.param("'a':\n  x: 1\n", ["a"], "write the key `a` without quotes", id="single"),
        pytest.param(
            'a:\n  "c":\n    x: 1\n', ["a", "c"], "write the key `c` without quotes", id="double"
        ),
        pytest.param(
            "'a':\n  c:\n    'd': {}\n",
            ["a", "c", "d"],
            "write the keys `a`, `d` without quotes",
            id="several",
        ),
    ],
)
def test_a_key_on_the_way_written_in_quotes_is_refused_naming_it(
    original: str, path: list[str], said: str
) -> None:
    with pytest.raises(records.RecordError, match=f"^{said}$"):
        records.with_entry(original, path, "b", 2, each="item")
    unquoted = original.replace("'", "").replace('"', "")
    mapping = reading.load_yaml(records.with_entry(unquoted, path, "b", 2, each="item"))
    for key in path:
        mapping = mapping[key]
    assert mapping["b"] == 2


# --- one entry's value replaced -----------------------------------------------------------------

RELEASED = {"released": True, "hash": {"form": 1, "inputs": [{"path": "a.yaml", "sha256": "ab"}]}}


def test_an_entry_written_in_block_is_written_again_at_its_indent() -> None:
    original = (
        records.BOM
        + "# Kept.\r\nv:\r\n    1.0.0:  # ours\r\n        released: false\r\n"
        + "    2.0.0:\r\n        released: false\r\n# The end.\r\n"
    )
    assert records.with_value(original, ["v"], "1.0.0", RELEASED, each="version") == (
        records.BOM
        + "# Kept.\r\nv:\r\n    1.0.0:  # ours\r\n      released: true\r\n      hash:\r\n"
        + "        form: 1\r\n        inputs:\r\n          - path: a.yaml\r\n"
        + "            sha256: ab\r\n"
        + "    2.0.0:\r\n        released: false\r\n# The end.\r\n"
    )


def test_an_entry_written_in_flow_on_its_line_is_written_again_there() -> None:
    original = "a:\n  v:\n    1.0.0: {released: false}  # ours\n    2.0.0: {released: false}"
    assert records.with_value(original, ["a", "v"], "2.0.0", RELEASED, each="version") == (
        "a:\n  v:\n    1.0.0: {released: false}  # ours\n"
        "    2.0.0: {released: true, hash: {form: 1, inputs: [{path: a.yaml, sha256: ab}]}}"
    )


def test_an_entry_of_a_mapping_written_in_flow_is_written_again_in_its_place() -> None:
    original = (
        "libraries: {a: {v: {1.0.0: {released: false}}}, "
        "b: {v: {2.0.0: {released: false}, 1.0.0: {released: false}}}}  # all\n"
    )
    assert records.with_value(original, ["libraries", "b", "v"], "1.0.0", RELEASED, each="v") == (
        "libraries: {a: {v: {1.0.0: {released: false}}}, "
        "b: {v: {2.0.0: {released: false}, 1.0.0: {released: true, hash: {form: 1, inputs: "
        "[{path: a.yaml, sha256: ab}]}}}}}  # all\n"
    )
    flow = "a:\n  v: {1.0.0: {released: false}}\n"
    assert reading.load_yaml(records.with_value(flow, ["a", "v"], "1.0.0", RELEASED, each="v")) == {
        "a": {"v": {"1.0.0": RELEASED}}
    }


def test_an_entry_the_mapping_does_not_hold_or_the_text_does_not_show_is_refused() -> None:
    with pytest.raises(records.RecordError, match=r"^`v` holds no `1\.0\.0`$"):
        records.with_value("v: {}\n", ["v"], "1.0.0", RELEASED, each="version")
    with pytest.raises(records.RecordError, match=r"^write `v` as a block mapping, one version"):
        records.with_value(
            "v: {\n  1.0.0: {released: false}}\n", ["v"], "1.0.0", RELEASED, each="version"
        )
    with pytest.raises(records.RecordError, match=r"^write the key `1\.0\.0` without quotes$"):
        records.with_value(
            "v:\n  '1.0.0': {released: false}\n", ["v"], "1.0.0", RELEASED, each="version"
        )
