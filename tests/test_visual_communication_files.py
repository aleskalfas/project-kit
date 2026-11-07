"""A file of the capability's format: its binding, its shape against its schema, the nearest
known key, writing one whole (DEC-002 points 3 and 4, DEC-003 point 1), and a change of
several files that a failed write leaves as it was."""

from __future__ import annotations

import errno
import os
import stat
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load
from tests.visual_communication_project import bound, write, yaml_text
from tests.visual_communication_writes import FULL, failing

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


def test_load_bound_reads_bytes_as_read_bound_reads_a_file() -> None:
    good = yaml_text(bound("piece", state="draft")).encode("utf-8")
    assert files.load_bound(good, "at/a/commit", "piece")["state"] == "draft"
    with pytest.raises(files.FileError, match=r"^at/a/commit: names the schema"):
        files.load_bound(good, "at/a/commit", "exports")
    with pytest.raises(reading.ReadError, match=r"^at/a/commit: does not parse as YAML"):
        files.load_bound(b"not: [yaml\n", "at/a/commit", "piece")
    with pytest.raises(reading.ReadError, match=r"^at/a/commit: is not UTF-8"):
        files.load_bound(b"\xff", "at/a/commit", "piece")


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


# --- a change of several files ------------------------------------------------------------------


def tree(folder: Path) -> dict[str, bytes]:
    """Every file under `folder`, relative to it, with its bytes."""
    return {
        path.relative_to(folder).as_posix(): path.read_bytes()
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    }


def change_of(root: Path) -> Any:
    """A change that replaces `kept.yaml`, writes `new/deep/made.yaml` in folders it makes,
    adds the folder `added/` holding a copy of `source.txt`, removes `gone.yaml`, and
    writes `record.yaml` last."""
    write(root / "kept.yaml", "a: 1\n")
    write(root / "gone.yaml", "b: 1\n")
    write(root / "record.yaml", "c: 1\n")
    write(root / "source.txt", "copied\n")
    change = files.Change(root)
    change.write(root / "kept.yaml", b"a: 2\n")
    change.write(root / "new" / "deep" / "made.yaml", b"d: 1\n")
    change.add_folder(root / "added", {"sub/copy.txt": root / "source.txt"})
    change.remove(root / "gone.yaml")
    change.write(root / "record.yaml", b"c: 2\n")
    return change


def test_a_change_takes_every_step_and_leaves_no_temporary(tmp_path: Path) -> None:
    change = change_of(tmp_path)
    change.commit()
    assert tree(tmp_path) == {
        "added/sub/copy.txt": b"copied\n",
        "kept.yaml": b"a: 2\n",
        "new/deep/made.yaml": b"d: 1\n",
        "record.yaml": b"c: 2\n",
        "source.txt": b"copied\n",
    }


def test_a_write_that_fails_while_staged_changes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    change = change_of(tmp_path)
    before = tree(tmp_path)
    mkstemp = files.tempfile.mkstemp

    def full(*args: Any, prefix: str = "", **kwargs: Any) -> Any:
        if prefix.startswith(".record.yaml."):
            raise OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))
        return mkstemp(*args, prefix=prefix, **kwargs)

    monkeypatch.setattr(files.tempfile, "mkstemp", full)
    with pytest.raises(files.WriteFailed) as failed:
        change.commit()
    assert str(failed.value) == f"record.yaml could not be written: {FULL}"
    assert tree(tmp_path) == before
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted(before)


def test_a_write_that_fails_in_its_place_takes_back_every_step_before_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    change = change_of(tmp_path)
    before = tree(tmp_path)
    failing(monkeypatch, write={"record.yaml"})
    with pytest.raises(files.WriteFailed) as failed:
        change.commit()
    assert str(failed.value) == f"record.yaml could not be written: {FULL}"
    assert failed.value.left == ()
    assert tree(tmp_path) == before
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted(before)


def test_an_interrupt_between_two_steps_takes_back_every_step_before_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    change = change_of(tmp_path)
    before = tree(tmp_path)
    replace = files.os.replace

    def interrupted(source: Any, target: Any) -> None:
        if Path(target).name == "record.yaml":
            raise KeyboardInterrupt
        replace(source, target)

    monkeypatch.setattr(files.os, "replace", interrupted)
    with pytest.raises(KeyboardInterrupt):
        change.commit()
    assert tree(tmp_path) == before
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted(before)


def test_a_step_that_cannot_be_taken_back_is_named(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    change = change_of(tmp_path)
    failing(monkeypatch, write={"record.yaml"}, remove={"made.yaml"})
    with pytest.raises(files.WriteFailed) as failed:
        change.commit()
    assert str(failed.value) == (
        f"record.yaml could not be written: {FULL}; these could not be put back as they were "
        f"before the run: new/deep/made.yaml"
    )
    assert (tmp_path / "new/deep/made.yaml").read_bytes() == b"d: 1\n"
    assert (tmp_path / "kept.yaml").read_bytes() == b"a: 1\n"
    assert (tmp_path / "gone.yaml").read_bytes() == b"b: 1\n"
    assert not (tmp_path / "added").exists()


def test_a_file_that_cannot_be_removed_is_named_and_nothing_else_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    change = change_of(tmp_path)
    before = tree(tmp_path)
    failing(monkeypatch, remove={"gone.yaml"})
    with pytest.raises(files.WriteFailed) as failed:
        change.commit()
    assert str(failed.value).startswith("gone.yaml could not be removed: ")
    assert tree(tmp_path) == before


def replaced_in(root: Path) -> Any:
    """A change that replaces the folder `kept/`, holding `old.txt`, by one holding a copy of
    `source.txt`, then writes `record.yaml`."""
    write(root / "kept" / "old.txt", "old\n")
    write(root / "record.yaml", "c: 1\n")
    write(root / "source.txt", "copied\n")
    change = files.Change(root)
    change.replace_folder(root / "kept", {"sub/new.txt": root / "source.txt"})
    change.write(root / "record.yaml", b"c: 2\n")
    return change


def test_a_folder_replaced_holds_its_copy_alone_and_leaves_nothing_beside_it(
    tmp_path: Path,
) -> None:
    replaced_in(tmp_path).commit()
    assert tree(tmp_path) == {
        "kept/sub/new.txt": b"copied\n",
        "record.yaml": b"c: 2\n",
        "source.txt": b"copied\n",
    }
    assert sorted(path.name for path in tmp_path.iterdir()) == ["kept", "record.yaml", "source.txt"]


def test_a_write_that_fails_after_a_folder_is_replaced_moves_the_folder_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    change = replaced_in(tmp_path)
    before = tree(tmp_path)
    failing(monkeypatch, write={"record.yaml"})
    with pytest.raises(files.WriteFailed) as failed:
        change.commit()
    assert str(failed.value) == f"record.yaml could not be written: {FULL}"
    assert tree(tmp_path) == before
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted(
        {name.split("/")[0] for name in before}
    )


def test_a_folder_whose_copy_cannot_be_moved_in_is_named_where_it_cannot_be_moved_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    change = replaced_in(tmp_path)
    failing(monkeypatch, write={"kept"})
    with pytest.raises(files.WriteFailed) as failed:
        change.commit()
    assert str(failed.value) == (
        f"kept could not be replaced: {FULL}; these could not be put back as they were before "
        f"the run: kept"
    )
    assert (tmp_path / "record.yaml").read_bytes() == b"c: 1\n"
    [aside] = [path for path in tmp_path.iterdir() if path.name.startswith(".kept.")]
    assert tree(aside) == {"old.txt": b"old\n"}


def removed_in(root: Path) -> Any:
    """A change that removes the folder `gone/`, holding `old.txt` and `sub/deep.txt`, then
    writes `record.yaml`."""
    write(root / "gone" / "old.txt", "old\n")
    write(root / "gone" / "sub" / "deep.txt", "deep\n")
    write(root / "record.yaml", "c: 1\n")
    change = files.Change(root)
    change.remove_folder(root / "gone")
    change.write(root / "record.yaml", b"c: 2\n")
    return change


def test_a_folder_removed_goes_whole_and_leaves_nothing_beside_it(tmp_path: Path) -> None:
    removed_in(tmp_path).commit()
    assert tree(tmp_path) == {"record.yaml": b"c: 2\n"}
    assert [path.name for path in tmp_path.iterdir()] == ["record.yaml"]


def test_a_write_that_fails_after_a_folder_is_removed_moves_the_folder_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    change = removed_in(tmp_path)
    before = tree(tmp_path)
    failing(monkeypatch, write={"record.yaml"})
    with pytest.raises(files.WriteFailed) as failed:
        change.commit()
    assert str(failed.value) == f"record.yaml could not be written: {FULL}"
    assert tree(tmp_path) == before
    assert sorted(path.name for path in tmp_path.iterdir()) == ["gone", "record.yaml"]


def test_a_folder_that_cannot_be_moved_aside_is_named_and_nothing_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    change = removed_in(tmp_path)
    before = tree(tmp_path)
    rename = os.rename

    def held(source: Any, target: Any) -> None:
        if Path(source).name == "gone":
            raise OSError(errno.EBUSY, os.strerror(errno.EBUSY), str(source))
        rename(source, target)

    monkeypatch.setattr(os, "rename", held)
    with pytest.raises(files.WriteFailed) as failed:
        change.commit()
    assert str(failed.value) == f"gone could not be removed: {os.strerror(errno.EBUSY)}"
    assert tree(tmp_path) == before
    assert sorted(path.name for path in tmp_path.iterdir()) == ["gone", "record.yaml"]


def test_a_folder_removed_that_cannot_be_moved_back_is_named(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    change = removed_in(tmp_path)
    failing(monkeypatch, write={"record.yaml", "gone"})
    with pytest.raises(files.WriteFailed) as failed:
        change.commit()
    assert str(failed.value) == (
        f"record.yaml could not be written: {FULL}; these could not be put back as they were "
        f"before the run: gone"
    )
    assert (tmp_path / "record.yaml").read_bytes() == b"c: 1\n"
    [aside] = [path for path in tmp_path.iterdir() if path.name.startswith(".gone.")]
    assert tree(aside) == {"old.txt": b"old\n", "sub/deep.txt": b"deep\n"}
