"""A file of the capability's format: its binding, its shape against its schema, the nearest
known key, and writing one whole (DEC-002 points 3 and 4, DEC-003 point 1)."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load
from tests.visual_communication_project import bound, write, yaml_text

files, reading = load("visual-communication", "files", "reading")


# --- binding ------------------------------------------------------------------------------------


def test_a_file_bound_to_its_kind_at_format_1_has_no_binding_problem() -> None:
    assert files.binding_problem(bound("piece"), "piece") is None
    assert files.is_of_format(bound("piece"))
    assert not files.is_of_format({"pkit_schema": "living-docs:doc"})


@pytest.mark.parametrize(
    ("data", "said"),
    [
        (["a"], "is not a mapping"),
        ({"schema_version": 1}, "names no schema"),
        ({"pkit_schema": "visual-communication:content", "schema_version": 1}, "not `visual"),
        ({"pkit_schema": "visual-communication:piece"}, "names no format number"),
        ({"pkit_schema": "visual-communication:piece", "schema_version": 2}, "at format 2"),
        ({"pkit_schema": "visual-communication:piece", "schema_version": "1"}, "at format '1'"),
        ({"pkit_schema": "visual-communication:piece", "schema_version": True}, "at format True"),
    ],
)
def test_a_file_not_bound_to_its_kind_at_format_1_is_named(data: Any, said: str) -> None:
    problem = files.binding_problem(data, "piece")
    assert problem is not None
    assert said in problem


def test_without_binding_leaves_the_content() -> None:
    assert files.without_binding(bound("piece", state="draft")) == {"state": "draft"}


def test_read_bound_reads_a_bound_file_and_refuses_another(tmp_path: Path) -> None:
    good = write(tmp_path / "piece.yaml", yaml_text(bound("piece", state="draft")))
    assert files.read_bound(good, "piece")["state"] == "draft"
    other = write(tmp_path / "content.yaml", yaml_text(bound("content")))
    with pytest.raises(files.FileError, match="names the schema"):
        files.read_bound(other, "piece")
    broken = write(tmp_path / "broken.yaml", "a: [\n")
    with pytest.raises(reading.ReadError):
        files.read_bound(broken, "piece")


# --- the nearest known key ----------------------------------------------------------------------


def test_the_nearest_known_key_is_named_where_one_is_a_likely_slip() -> None:
    assert files.nearest("colour", ["color", "size"]) == "color"
    assert files.nearest("zzz", ["color", "size"]) is None
    assert files.unknown_keys({"color": 1, "sise": 2, "q": 3}, ["color", "size"]) == [
        ("sise", "size"),
        ("q", None),
    ]


# --- shape --------------------------------------------------------------------------------------


def test_what_a_schema_refuses_is_named_with_its_place() -> None:
    problems = files.shape_problems(bound("config", location=".pkit/x", extra=1), "config")
    assert any(problem.startswith("/location: ") for problem in problems), problems
    assert any("extra" in problem for problem in problems), problems


# --- writing ------------------------------------------------------------------------------------


def test_write_whole_writes_a_new_file_and_leaves_no_temporary(tmp_path: Path) -> None:
    target = tmp_path / "a.yaml"
    files.write_whole(target, b"a: 1\n")
    assert target.read_bytes() == b"a: 1\n"
    assert [path.name for path in tmp_path.iterdir()] == ["a.yaml"]


def test_write_whole_keeps_a_files_mode(tmp_path: Path) -> None:
    target = write(tmp_path / "a.yaml", "a: 1\n")
    os.chmod(target, 0o600)
    files.write_whole(target, b"a: 2\n")
    assert target.read_bytes() == b"a: 2\n"
    assert stat.S_IMODE(target.stat().st_mode) == 0o600


def test_write_whole_leaves_the_file_as_it_was_when_the_write_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = write(tmp_path / "a.yaml", "a: 1\n")

    def fail(source: object, destination: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(OSError, match="disk full"):
        files.write_whole(target, b"a: 2\n")
    assert target.read_text(encoding="utf-8") == "a: 1\n"
    assert [path.name for path in tmp_path.iterdir()] == ["a.yaml"]


def test_a_file_reached_through_a_link_is_refused(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    (tmp_path / "linked").symlink_to(real, target_is_directory=True)
    with pytest.raises(files.FileError, match="through the link linked"):
        files.refuse_links(tmp_path, tmp_path / "linked" / "a.yaml")
    target = tmp_path / "file-link.yaml"
    target.symlink_to(real / "a.yaml")
    with pytest.raises(files.FileError, match=r"file-link\.yaml"):
        files.refuse_links(tmp_path, target)
    files.refuse_links(tmp_path, real / "a.yaml")
