"""The designer's grant against the location (visual-communication DEC-030 point 5): the
check reads the category `visual-communication.work` from the agents overlay as the deploy
reads it, the designer's override included, and fails a value that does not cover the
recorded location or that lies inside the methodology's folder; a value that names no path
fails nothing. Moving the location names the overlay line to change, and the capability
writes nothing in the agents' area. Run in this process; it starts no `pkit`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_kit import agents_overlay, write_categories
from tests.in_process import load, run_main
from tests.visual_communication_project import (
    CAPABILITY,
    CONFIG,
    OVERLAY,
    bound,
    project,
    write,
    yaml_text,
)

grant, checks, location, files, add = load(
    "visual-communication", "grant", "checks", "location", "files", "add.py"
)

BINDING = "pkit_schema: visual-communication:config\nschema_version: 1\n"
CATEGORY = "visual-communication.work"
DESIGNER = "graphic-designer"
OVERRIDE = f"overrides.{DESIGNER}.{CATEGORY}"
#: The top-level line in words, as the messages name it.
TOP_LINE = f"the `{CATEGORY}:` line of {OVERLAY}"
#: The designer's own line in words, as the messages name it.
OWN_LINE = f"`{CATEGORY}` under `overrides.{DESIGNER}` in {OVERLAY}"
RECONCILE = "`pkit agents reconcile --write`"


def overlay(root: Path, text: str) -> Path:
    return write(root / OVERLAY, text)


def recorded(root: Path, folder: str = "visual") -> Path:
    """`folder` recorded as the location, holding the capability's marker."""
    write(root / CONFIG, f"{BINDING}location: {folder}\n")
    return write(root / folder / "libraries" / "libraries.yaml", yaml_text(bound("libraries")))


def grant_found(root: Path) -> list[tuple[str, str, str]]:
    """Each finding on the designer's grant: where it points, what it says, its fix."""
    return [
        (checks.place(finding), finding.message, finding.fix)
        for finding in checks.grant_findings(root)
    ]


def agents_area(root: Path) -> dict[str, bytes]:
    """Every file under `.pkit/agents/`, with its bytes."""
    folder = root / ".pkit" / "agents"
    return {
        path.relative_to(folder).as_posix(): path.read_bytes()
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    }


# --- read as the deploy reads it ----------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        None,
        "",
        f'{CATEGORY}: ["visual/"]\n',
        f"{CATEGORY}: visual\n",
        f"{CATEGORY}:\n",
        f"{CATEGORY}: []\n",
        f'{CATEGORY}: ["visual/", null, "helpers/"]\n',
        f'{CATEGORY}: ["visual/"]\noverrides:\n  {DESIGNER}:\n    {CATEGORY}: ["art/"]\n',
        f'{CATEGORY}: ["visual/"]\noverrides:\n  {DESIGNER}:\n    {CATEGORY}:\n',
        f'{CATEGORY}: ["visual/"]\noverrides:\n  critic:\n    {CATEGORY}: ["art/"]\n',
        f'{CATEGORY}: ["visual/"]\noverrides:\n  {DESIGNER}:\n    model: opus\n',
        f'{CATEGORY}: ["visual/"]\noverrides:\n  {DESIGNER}: ["art/"]\n',
        f'{CATEGORY}: ["visual/"]\noverrides: ["art/"]\n',
        f'overrides:\n  {DESIGNER}:\n    {CATEGORY}: ["art/"]\n',
        "- visual/\n",
    ],
)
def test_the_grant_is_what_the_backbone_resolves_for_the_designer(
    tmp_path: Path, text: str | None
) -> None:
    root = project(tmp_path)
    if text is not None:
        overlay(root, text)
    entries, undefined = agents_overlay.expand_placeholders(
        [f"<{CATEGORY}>"], agent_name=DESIGNER, overlay=agents_overlay.load_overlay_values(root)
    )
    given = grant.granted(root)
    if undefined:
        assert given is None or given.paths is None
    else:
        assert given is not None
        assert given.paths == tuple(entry.value for entry in entries)


def test_the_category_and_its_owner_are_the_capabilitys_declaration() -> None:
    (category,) = write_categories.declared_in("visual-communication", CAPABILITY)
    assert (category.name, category.owner) == (grant.CATEGORY, grant.OWNER)
    assert agents_overlay.OVERLAY_PATH.as_posix() == grant.OVERLAY == OVERLAY


# --- the check ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("folder", "paths"),
    [
        ("visual", ["visual/"]),
        ("visual", ["./visual"]),
        ("visual", ["helpers/", "visual"]),
        ("docs/figures", ["docs/"]),
    ],
)
def test_a_grant_that_covers_the_recorded_location_fails_nothing(
    tmp_path: Path, folder: str, paths: list[str]
) -> None:
    root = project(tmp_path)
    recorded(root, folder)
    overlay(root, f"{CATEGORY}: {json.dumps(paths)}\n")
    assert grant_found(root) == []


def test_an_absolute_path_within_the_repository_is_read_from_its_top(tmp_path: Path) -> None:
    root = project(tmp_path)
    recorded(root)
    overlay(root, f"{CATEGORY}: {json.dumps([str(root / 'visual')])}\n")
    assert grant_found(root) == []


@pytest.mark.parametrize("paths", [["art/"], ["visual/pieces/"], ["visual/**"], ["vis"]])
def test_a_grant_that_does_not_cover_the_recorded_location_fails(
    tmp_path: Path, paths: list[str]
) -> None:
    root = project(tmp_path)
    recorded(root)
    overlay(root, f"{CATEGORY}: {json.dumps(paths)}\n")
    ((where, said, fix),) = grant_found(root)
    assert where == f"{OVERLAY}#{CATEGORY}"
    assert said == (
        f"the designer's grant names `{paths[0]}`, which does not cover the location `visual` "
        f"the configuration records, so the designer cannot write the visual work"
    )
    assert fix == (
        f"run {RECONCILE}, which moves {TOP_LINE} to `visual/` while it stays as pkit wrote "
        f"it; otherwise name `visual/` there, or `[]` to switch the designer off"
    )


def test_the_designers_override_is_judged_in_place_of_the_top_level_line(tmp_path: Path) -> None:
    root = project(tmp_path)
    recorded(root)
    overlay(root, f'{CATEGORY}: ["visual/"]\noverrides:\n  {DESIGNER}:\n    {CATEGORY}: [art/]\n')
    ((where, said, fix),) = grant_found(root)
    assert where == f"{OVERLAY}#{OVERRIDE}"
    assert "names `art/`, which does not cover the location `visual`" in said
    assert fix == f"in {OWN_LINE}, name `visual/` there, or `[]` to switch the designer off"
    overlay(root, f'{CATEGORY}: ["art/"]\noverrides:\n  {DESIGNER}:\n    {CATEGORY}: [visual]\n')
    assert grant_found(root) == []


@pytest.mark.parametrize(
    "paths", [[".pkit/capabilities/visual-communication/project/art/"], [".pkit"], ["x/../.pkit/y"]]
)
def test_a_path_inside_the_methodologys_folder_fails(tmp_path: Path, paths: list[str]) -> None:
    root = project(tmp_path)
    recorded(root)
    overlay(root, f"{CATEGORY}: {json.dumps(['visual/', *paths])}\n")
    ((where, said, fix),) = grant_found(root)
    assert where == f"{OVERLAY}#{CATEGORY}"
    assert said == (
        f"the designer's grant names `{paths[0]}`, inside the methodology's folder `.pkit/`, "
        f"where the visual work never lies"
    )
    assert fix == f"take `{paths[0]}` out of {TOP_LINE}"


def test_a_grant_inside_the_methodologys_folder_alone_fails_twice(tmp_path: Path) -> None:
    root = project(tmp_path)
    recorded(root)
    overlay(root, f'{CATEGORY}: [".pkit/visual/"]\n')
    found = grant_found(root)
    assert [said.split(", ")[1] for _, said, _ in found] == [
        "inside the methodology's folder `.pkit/`",
        "which does not cover the location `visual` the configuration records",
    ]


@pytest.mark.parametrize(
    "text",
    [
        f"{CATEGORY}: []\n",
        f"{CATEGORY}:\n",
        "process-authoring-targets: []\n",
        f'{CATEGORY}: ["art/"]\noverrides:\n  {DESIGNER}:\n    {CATEGORY}: []\n',
    ],
)
def test_a_grant_that_names_no_path_fails_nothing(tmp_path: Path, text: str) -> None:
    root = project(tmp_path)
    recorded(root)
    overlay(root, text)
    assert grant_found(root) == []


def test_with_no_location_recorded_only_the_methodologys_folder_is_judged(tmp_path: Path) -> None:
    root = project(tmp_path)
    overlay(root, f'{CATEGORY}: ["art/"]\n')
    assert grant_found(root) == []
    overlay(root, f'{CATEGORY}: ["art/", ".pkit/art/"]\n')
    assert [said for _, said, _ in grant_found(root)] == [
        "the designer's grant names `.pkit/art/`, inside the methodology's folder `.pkit/`, "
        "where the visual work never lies"
    ]
    write(root / CONFIG, f"{BINDING}location: .pkit/x\n")
    assert len(grant_found(root)) == 1  # the refused location is `location`'s to report


def test_an_overlay_that_cannot_be_read_fails(tmp_path: Path) -> None:
    root = project(tmp_path)
    recorded(root)
    overlay(root, f"{CATEGORY}: [\n")
    ((where, said, fix),) = grant_found(root)
    assert where == OVERLAY
    assert said.startswith(
        "the agents overlay cannot be read, so the designer's grant is not checked: "
    )
    assert fix == "mend the file"


def test_the_check_judges_the_grant_in_every_run_but_one_of_a_piece(tmp_path: Path) -> None:
    root = project(tmp_path)
    recorded(root)
    overlay(root, f'{CATEGORY}: ["art/"]\n')
    report = checks.check(root)
    assert [checks.place(f) for f, level in report.judged if f.code == "grant"] == [
        f"{OVERLAY}#{CATEGORY}"
    ]
    assert all(level == "fails" for f, level in report.judged if f.code == "grant")
    assert report.failed()
    assert [f.code for f, _ in checks.check(root, only="talk").judged] == ["piece-missing"]
    (root / "visual" / "libraries" / "libraries.yaml").unlink()
    assert [f.code for f, _ in checks.check(root).judged] == ["grant"]
    write(root / CONFIG, f"{BINDING}location: art\n")
    assert [f.code for f, _ in checks.check(root).judged] == ["location"]


# --- moving the location ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "named"),
    [
        (
            None,
            f"move the designer's grant, {TOP_LINE}, which {RECONCILE} moves while it stays "
            "as pkit wrote it",
        ),
        (
            f'{CATEGORY}: ["visual/"]\n',
            f"move the designer's grant, {TOP_LINE}, which "
            f"{RECONCILE} moves while it stays as pkit wrote it",
        ),
        (
            f'overrides:\n  {DESIGNER}:\n    {CATEGORY}: ["visual/"]\n',
            f"move the designer's grant, {OWN_LINE}",
        ),
        (f"{CATEGORY}: [\n", f"move the designer's grant, {TOP_LINE}, which {RECONCILE} moves"),
    ],
)
def test_each_way_to_move_the_location_names_the_overlay_line(
    tmp_path: Path, text: str | None, named: str
) -> None:
    root = project(tmp_path)
    recorded(root)
    if text is not None:
        overlay(root, text)
    with pytest.raises(location.LocationRefused) as moved:
        location.for_writing(root, "art", root)
    assert "To move the work, move the folder, change the `location:` line, and " in str(
        moved.value
    )
    assert named in str(moved.value)
    write(root / CONFIG, f"{BINDING}location: art\n")
    for find in (location.for_reading, location.for_writing):
        with pytest.raises(location.LocationRefused) as missing:
            find(root)
        assert "change the `location:` line to where the work lies, and " in str(missing.value)
        assert named in str(missing.value)


def test_recording_the_location_names_the_line_and_writes_nothing_in_the_agents_area(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    overlay(root, f'overrides:\n  {DESIGNER}:\n    {CATEGORY}: ["visual/"]\n')
    before = agents_area(root)
    added = run_main(add, "foundations", "--location", "art", cwd=root)
    assert added.returncode == 0, added.stderr
    assert (
        f"recorded the location `art` in {CONFIG}; to move the work, move the folder, change "
        f"the `location:` line there, and move the designer's grant, {OWN_LINE}"
    ) in added.stdout.splitlines()
    assert agents_area(root) == before
    refused = run_main(add, "foundations", "--location", "visual", cwd=root)
    assert refused.returncode == 1
    assert f"move the designer's grant, {OWN_LINE}" in refused.stderr
    assert agents_area(root) == before
