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
