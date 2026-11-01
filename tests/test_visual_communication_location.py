"""The capability's location and its configuration (DEC-002 points 1 and 2, COR-049 point 5):
the paths refused, where reading and writing commands take the work, recording it with every
other byte of the configuration kept, and the files of a folder as git sees them."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.in_process import load
from tests.visual_communication_project import CONFIG, bound, project, write, yaml_text

location, config_text = load("visual-communication", "location", "config_text")

BINDING = "pkit_schema: visual-communication:config\nschema_version: 1\n"


def config(root: Path, text: str) -> Path:
    return write(root / CONFIG, text)


def marked(root: Path, folder: str = "visual") -> Path:
    """`folder` holding the capability's marker, the list of libraries."""
    return write(root / folder / "libraries" / "libraries.yaml", yaml_text(bound("libraries")))


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


# --- the paths refused --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rel", "said"),
    [
        ("", "repository's top"),
        (".", "repository's top"),
        ("a\\b", "holds a `\\`"),
        ("/abs", "is absolute"),
        ("a//b", "empty segment"),
        ("a/", "empty segment"),
        ("../out", "outside the repository"),
        ("a/../../out", "outside the repository"),
        (".pkit/visual", "under `.pkit/`"),
        ("docs/.hidden/visual", "hidden folder"),
    ],
)
def test_a_path_the_rules_refuse_is_named(rel: str, said: str) -> None:
    assert said in (location.shape_problem(rel) or "")


@pytest.mark.parametrize("rel", ["visual", "docs/figures", "a-b/c_d"])
def test_a_folder_within_the_repository_is_taken(rel: str) -> None:
    assert location.shape_problem(rel) is None


def test_a_location_reached_through_a_link_or_that_is_a_file_is_refused(tmp_path: Path) -> None:
    root = project(tmp_path)
    (root / "real").mkdir()
    (root / "linked").symlink_to(root / "real", target_is_directory=True)
    write(root / "file", "")
    assert "through the link linked" in (location.problem(root, "linked/visual") or "")
    assert "not a folder" in (location.problem(root, "file") or "")
    assert location.problem(root, "not-there-yet") is None


def test_a_given_location_is_taken_relative_to_the_working_directory(tmp_path: Path) -> None:
    root = project(tmp_path)
    (root / "docs").mkdir()
    assert location.normalise(root, "figures", root / "docs") == "docs/figures"
    assert location.normalise(root, str(root / "art"), root / "docs") == "art"
    assert location.normalise(root, "../visual", root / "docs") == "visual"
    with pytest.raises(location.LocationRefused, match="outside the repository"):
        location.normalise(root, "../../elsewhere", root / "docs")
    with pytest.raises(location.LocationRefused, match=r"under `\.pkit/`"):
        location.normalise(root, ".pkit/x", root)


# --- reading ------------------------------------------------------------------------------------


def test_with_nothing_recorded_and_no_marker_there_is_no_visual_work(tmp_path: Path) -> None:
    root = project(tmp_path)
    assert location.for_reading(root) is None
    write(root / "visual" / "notes.md", "not the capability's\n")
    assert location.for_reading(root) is None


def test_the_default_holding_the_marker_is_read_unrecorded(tmp_path: Path) -> None:
    root = project(tmp_path)
    marked(root)
    assert location.for_reading(root) == location.Location("visual", recorded=False)


def test_any_bound_yaml_file_is_the_marker(tmp_path: Path) -> None:
    root = project(tmp_path)
    write(root / "visual" / "pieces" / "a" / "piece.yaml", yaml_text(bound("piece")))
    write(root / "visual" / "other.yaml", "a: [\n")
    assert location.holds_marker(root, "visual")
    assert location.for_reading(root) == location.Location("visual", recorded=False)


def test_the_recorded_location_is_read(tmp_path: Path) -> None:
    root = project(tmp_path)
    config(root, f"{BINDING}location: docs/figures\n")
    (root / "docs" / "figures").mkdir(parents=True)
    marked(root)
    assert location.for_reading(root) == location.Location("docs/figures", recorded=True)


@pytest.mark.parametrize(
    ("text", "said"),
    [
        (f"{BINDING}location: docs/figures\n", "does not exist"),
        (f"{BINDING}location: .pkit/x\n", r"under `\.pkit/`"),
        (f"{BINDING}location: [a]\n", "not a path"),
        ("location: [\n", "cannot be read"),
        ("- a\n", "not a mapping"),
    ],
)
def test_a_recorded_location_that_cannot_be_used_is_refused(
    tmp_path: Path, text: str, said: str
) -> None:
    root = project(tmp_path)
    config(root, text)
    with pytest.raises(location.LocationRefused, match=said):
        location.for_reading(root)


# --- writing ------------------------------------------------------------------------------------


def test_a_writing_command_takes_the_default_where_it_is_absent_empty_or_marked(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    assert location.for_writing(root) == location.ForWriting("visual", record=True)
    (root / "visual").mkdir()
    assert location.for_writing(root) == location.ForWriting("visual", record=True)
    marked(root)
    assert location.for_writing(root) == location.ForWriting("visual", record=True)


def test_a_writing_command_refuses_a_default_holding_other_work(tmp_path: Path) -> None:
    root = project(tmp_path)
    write(root / "visual" / "notes.md", "not the capability's\n")
    with pytest.raises(location.LocationRefused, match="--location visual"):
        location.for_writing(root)
    assert location.for_writing(root, "visual", root) == location.ForWriting("visual", True)
    assert location.for_writing(root, "art", root) == location.ForWriting("art", True)


def test_a_default_that_is_a_file_asks_for_a_location(tmp_path: Path) -> None:
    root = project(tmp_path)
    write(root / "visual", "")
    with pytest.raises(location.LocationRefused, match="--location <path>"):
        location.for_writing(root)


def test_a_writing_command_never_moves_the_recorded_location(tmp_path: Path) -> None:
    root = project(tmp_path)
    config(root, f"{BINDING}location: art\n")
    (root / "art").mkdir()
    assert location.for_writing(root) == location.ForWriting("art", record=False)
    assert location.for_writing(root, "art", root) == location.ForWriting("art", record=False)
    with pytest.raises(location.LocationRefused, match="never moves it"):
        location.for_writing(root, "visual", root)
    (root / "art").rmdir()
    with pytest.raises(location.LocationRefused, match="does not exist"):
        location.for_writing(root)


def test_recording_creates_the_configuration_and_says_where_to_change_it(tmp_path: Path) -> None:
    root = project(tmp_path)
    said = location.record(root, "visual")
    assert "recorded the location `visual` (the default" in said
    assert CONFIG in said
    assert (root / CONFIG).read_text(encoding="utf-8") == f"{BINDING}\nlocation: visual\n"
    assert location.configured(root) == "visual"


# --- the configuration's text -------------------------------------------------------------------


def test_a_key_is_added_at_the_end_with_comments_and_order_kept() -> None:
    existing = f"# the project's own words\n{BINDING}\n# later\nother: 1 # kept\n"
    assert config_text.with_key(existing, "location", "art") == existing + "location: art\n"


def test_a_last_line_without_its_ending_gets_one() -> None:
    existing = f"{BINDING}other: 1"
    assert config_text.with_key(existing, "location", "art") == f"{existing}\nlocation: art\n"


def test_an_empty_file_takes_the_binding_with_the_key() -> None:
    assert config_text.with_key("", "location", "art") == f"{BINDING}location: art\n"
    assert config_text.with_key("# empty\n", "location", "art") == (
        f"# empty\n{BINDING}location: art\n"
    )


def test_a_byte_order_mark_and_crlf_endings_are_kept() -> None:
    existing = "﻿" + BINDING.replace("\n", "\r\n")
    assert config_text.with_key(existing, "location", "art") == (existing + "location: art\r\n")


def test_mixed_line_endings_are_refused() -> None:
    with pytest.raises(config_text.ConfigRefused, match="mixed line endings"):
        config_text.with_key("a: 1\r\nb: 2\n", "location", "art")


@pytest.mark.parametrize(
    ("value", "written"),
    [
        ("docs/figures", "docs/figures"),
        ("no", '"no"'),
        ("On", '"On"'),
        ("null", '"null"'),
        ("1.0", '"1.0"'),
        ("2026-11-01", '"2026-11-01"'),
        ("my art", '"my art"'),
        ("a: b", '"a: b"'),
    ],
)
def test_a_value_any_yaml_would_read_otherwise_is_quoted(value: str, written: str) -> None:
    text = config_text.with_key(None, "location", value)
    assert text.endswith(f"location: {written}\n")
    assert config_text.with_key(text, "location", value) == text


def test_the_same_value_leaves_the_file_and_another_is_refused() -> None:
    existing = f"{BINDING}location: art\n"
    assert config_text.with_key(existing, "location", "art") == existing
    with pytest.raises(config_text.ConfigRefused, match="never moves it"):
        config_text.with_key(existing, "location", "visual")


def test_a_flow_mapping_at_the_top_is_left_for_a_person() -> None:
    with pytest.raises(config_text.ConfigRefused, match="by hand"):
        config_text.with_key(
            "{pkit_schema: visual-communication:config, schema_version: 1}\n", "location", "art"
        )


def test_a_configuration_that_does_not_parse_is_refused() -> None:
    with pytest.raises(config_text.ConfigRefused, match="fix it first"):
        config_text.with_key("a: [\n", "location", "art")


def test_record_writes_once_and_reads_back(tmp_path: Path) -> None:
    root = project(tmp_path)
    assert config_text.record(root, "location", "art")
    assert not config_text.record(root, "location", "art")
    assert (root / CONFIG).read_text(encoding="utf-8") == f"{BINDING}\nlocation: art\n"


def test_a_configuration_reached_through_a_link_is_refused(tmp_path: Path) -> None:
    root = project(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (root / ".pkit" / "capabilities" / "visual-communication" / "project").symlink_to(
        elsewhere, target_is_directory=True
    )
    with pytest.raises(config_text.ConfigRefused, match="through the link"):
        config_text.record(root, "location", "art")


# --- the files of a folder ----------------------------------------------------------------------


def test_outside_a_repository_the_folder_is_walked_without_links(tmp_path: Path) -> None:
    root = project(tmp_path)
    write(root / "visual" / "b.yaml", "")
    write(root / "visual" / "a" / "c.yaml", "")
    (root / "visual" / "link.yaml").symlink_to(root / "visual" / "b.yaml")
    (root / "visual" / "dir-link").symlink_to(root / "visual" / "a", target_is_directory=True)
    assert location.files(root, "visual") == ["visual/a/c.yaml", "visual/b.yaml"]
    assert location.files(root, "missing") == []


def test_in_a_repository_the_files_are_listed_as_git_sees_them(tmp_path: Path) -> None:
    root = project(tmp_path)
    git(root, "init", "-q")
    write(root / ".gitignore", "*.png\n")
    write(root / "visual" / "tracked.yaml", "")
    write(root / "visual" / "gone.yaml", "")
    git(root, "add", "visual")
    (root / "visual" / "gone.yaml").unlink()
    write(root / "visual" / "untracked.yaml", "")
    write(root / "visual" / "ignored.png", "")
    write(root / "visual" / "[x].yaml", "")
    (root / "visual" / "link.yaml").symlink_to(root / "visual" / "tracked.yaml")
    write(root / "visualise" / "other.yaml", "")
    assert location.files(root, "visual") == [
        "visual/[x].yaml",
        "visual/tracked.yaml",
        "visual/untracked.yaml",
    ]
