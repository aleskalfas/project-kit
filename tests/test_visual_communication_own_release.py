"""No release hides a failure a piece's scene shows (visual-communication DEC-079 point 4).

A release reads a version alone and computes no scene (DEC-014 point 1), so it passes a
component whose fault only some piece's content triggers. Inside a released version of the
project's own library, that failure lies at the lock of the piece whose scene shows it, and
fails there, in validation and in the viewing step's report:

- **Two faults only content triggers,** each in a component of the project's own library
  `tests`: a division by zero over an empty list, and a stand-in for an export's fact too
  long for its box (DEC-016 point 5). Each fails at a draft that triggers it, in the version
  not yet released, and at no draft that does not.
- **The release passes the version,** `pkit visual release tests` refusing nothing, and each
  failure still fails for the piece that shows it, now at that piece's lock, naming the
  version and the component, whether the check computes the scenes or reads them from a
  findings record written before the release.
- **What it leaves as it stands:** a finding on what a released version declares asks its
  owner for attention, one of a label a scene shows too where reading the component finds
  it; the same faults inside a released copy of a library the capability ships, or a
  released version from another repository, ask that library's owner; and a released version
  whose folder no longer matches its release keeps them in the version, where they fail.

The components are written in `tmp_path`, in the `tests` library: the repository's
validation reads every bound file under `tests/`, and a file a test refuses must not be
one of them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, NamedTuple

import pytest

from tests.in_process import load, run_main
from tests.test_visual_communication_checks import local
from tests.test_visual_communication_look import (  # noqa: F401
    plugins,
    report_of,
    reports_hold_their_schema,
    run_look,
)
from tests.test_visual_communication_meant_overlaps import ELSEWHERE, release
from tests.test_visual_communication_pipeline import PIECE, PIECE_FOLDER, drawing_project
from tests.visual_communication_project import bound, write, yaml_text

checks, findings, rendering, release_script = load(
    "visual-communication", "checks", "findings", "rendering", "release.py"
)

#: The version the tests release, and the folder of its components.
VERSION = "tests@1.0.0"
COMPONENTS = "visual/libraries/tests/1.0.0/components"

#: Where a failure the scene shows lies once the version is released.
LOCK = f"{PIECE_FOLDER}/piece.yaml#lock"

#: A second draft, beside `flow`, that draws the same component and does not trigger its fault.
OTHER = "calm"

#: A list of steps, and a bar under them whose width divides by the list's height: an empty
#: list is no height, so the bar divides by zero, and a list of steps is some.
SHARE = local(
    about="The steps of a flow in a column, and a bar under them as wide as they are few.",
    fields={
        "type": "object",
        "required": ["steps"],
        "properties": {"steps": {"type": "array", "items": {"type": "object"}}},
    },
    parts={
        "steps": {
            "repeat": "steps",
            "draw": "tests/card",
            "width": "=:width",
            "column": {"gap": "=@space.1"},
        },
        "bar": {
            "box": {"fill": "accent"},
            "y": "=steps.bottom",
            "width": "=:width * @space.1 / steps.height",
            "height": "=@space.1",
        },
    },
    preferred={"height": "=steps.height + @space.1"},
)


class Fault(NamedTuple):
    """A fault only a piece's content triggers: its label, the body of the figure that
    triggers it and one that does not, the component it lies in, where in the scene, and the
    mend its finding names."""

    label: str
    triggers: dict[str, Any]
    calm: dict[str, Any]
    component: str
    where: str
    mend: str

    @property
    def file(self) -> str:
        return f"{COMPONENTS}/{self.component.partition('/')[2]}.yaml"


FAULTS = {
    "division-by-zero": Fault(
        "division-by-zero",
        {"use": "tests/share", "steps": []},
        {"use": "tests/share", "steps": [{"id": "plan", "head": "Plan."}]},
        "tests/share",
        "figure/body",
        "mend it",
    ),
    "a-stand-in-too-long": Fault(
        "text-overflow",
        {"use": "tests/stamp", "shows": "narrow"},
        {"use": "tests/stamp", "shows": "number"},
        "tests/stamp",
        "figure/body/narrow",
        "give the text `narrow` of `tests/stamp` more width",
    ),
}

each_fault = pytest.mark.parametrize("fault", list(FAULTS.values()), ids=list(FAULTS))


def two_drafts(tmp_path: Path, fault: Fault) -> Path:
    """The drawing project, its `tests` library not yet released and holding `share`, with
    two drafts of one lock: `flow`, whose content triggers `fault`, and `calm`, whose content
    does not."""
    root = drawing_project(tmp_path, picture=False)
    write(root / COMPONENTS / "share.yaml", SHARE)
    flow = root / PIECE_FOLDER
    write(flow / "content.en.yaml", yaml_text(bound("content", body=fault.triggers)))
    other = root / "visual" / "pieces" / OTHER
    write(other / "piece.yaml", (flow / "piece.yaml").read_text(encoding="utf-8"))
    write(other / "content.en.yaml", yaml_text(bound("content", body=fault.calm)))
    return root


def found(root: Path, label: str) -> list[tuple[str, str, str, str, str]]:
    """Each finding `label` names in validation: where it lies, its level, its message, who
    it names and its fix."""
    report = checks.check(root)
    return sorted(
        (checks.place(finding), level, finding.message, finding.who, finding.fix)
        for finding, level in report.judged
        if finding.code == label
    )


def drawn_of(root: Path) -> Any:
    """The piece `flow` as this module's own `checks` reads it, whose `_lib` this module's
    `rendering` shares: two loads share no class, so a version that one reads under the lock
    the other would not find (`tests/in_process.py`, `load`)."""
    piece = checks.pl.read_piece(root, "visual", PIECE)
    return checks.pl.Project(piece, piece.lock, checks.Held(root, "visual"))


def release_tests(root: Path) -> None:
    """`pkit visual release tests`, which refuses nothing."""
    done = run_main(release_script, "tests", cwd=root)
    assert done.returncode == 0, done.stderr
    assert f"checked {VERSION}" in done.stdout


def at_the_lock(fault: Fault, message: str) -> str:
    """The message of `fault`'s failure at the piece's lock, whose message in the version
    was `message`."""
    return (
        f"under this lock, {VERSION}, released, fails in this piece's scene, in its component "
        f"`{fault.component}` ({fault.file}, `{fault.where}`): {message}"
    )


# --- before the release, and after it ----------------------------------------------------------


@each_fault
def test_a_fault_content_triggers_fails_at_the_draft_that_triggers_it_and_at_no_other(
    tmp_path: Path, fault: Fault
) -> None:
    [(place, level, _, _, _)] = found(two_drafts(tmp_path, fault), fault.label)
    assert (place, level) == (f"{fault.file}#{fault.where}", findings.FAILS)


@each_fault
def test_the_release_passes_the_version_and_the_failure_still_fails_at_the_pieces_lock(
    tmp_path: Path, fault: Fault
) -> None:
    root = two_drafts(tmp_path, fault)
    [(_, _, before, _, _)] = found(root, fault.label)
    release_tests(root)
    assert found(root, fault.label) == [
        (
            LOCK,
            findings.FAILS,
            at_the_lock(fault, before),
            "",
            f"in a new version of `tests`, {fault.mend}, and run `pkit visual render {PIECE}`, "
            f"which moves a draft's lock to it; or change the content",
        )
    ]


def test_a_release_moves_a_recorded_failure_to_the_lock_at_once(tmp_path: Path) -> None:
    """The findings record keeps the failure in the version, and its key covers no list, so a
    release that leaves the version's folder as it was moves it to the lock at once, from the
    record that still verifies."""
    fault = FAULTS["division-by-zero"]
    root = two_drafts(tmp_path, fault)
    drawn = drawn_of(root)
    record = rendering.record(drawn, checks.computed(drawn), None)
    (root / PIECE_FOLDER / "findings.yaml").write_bytes(rendering.record_text(record))
    [(place, _, before, _, _)] = found(root, fault.label)
    assert place == f"{fault.file}#{fault.where}"
    release(root, "tests")
    assert "of 1 read from their findings record" in checks.check(root, only=PIECE).summary[0]
    [(place, level, message, _, _)] = found(root, fault.label)
    assert (place, level, message) == (LOCK, findings.FAILS, at_the_lock(fault, before))


@each_fault
def test_the_viewing_steps_report_gives_the_failure_at_the_pieces_lock(
    tmp_path: Path, fault: Fault
) -> None:
    root = two_drafts(tmp_path, fault)
    [(_, _, before, _, _)] = found(root, fault.label)
    release_tests(root)
    done = run_look(root, PIECE)
    assert done.returncode == 0, done.stderr
    report = report_of(root)
    given = [
        each
        for entry in [*report["images"], {"findings": report["on-no-image"]}]
        for each in entry["findings"]
        if each["label"] == fault.label
    ]
    assert given
    for each in given:
        assert (each["location"], each["level"]) == (LOCK, findings.FAILS)
        # The step fills a fact's stand-in as its images are, so its width may differ.
        said = before if fault.label == "division-by-zero" else ""
        assert each["message"].startswith(at_the_lock(fault, said))


# --- what it leaves as it stands ----------------------------------------------------------------


#: A component of the `tests` library with two faults in what it declares, which the release
#: refuses, and one its scene shows: the width of `place` reads `:place`, which only a
#: `cross-size` reads, a `formula-reach` found as the component is read; the text `title` gives
#: a height, which its measured text sets, `two-owners`; and the width of `index` reads
#: `:index` where the piece places the component as no item, a `formula-reach` found as the
#: scene is computed.
ODD = local(
    about="A block whose parts read what they may not, and a text with two owners of its height.",
    fields={"type": "object", "properties": {"title": {"type": "string"}}},
    parts={
        "place": {"box": {"fill": "accent"}, "width": "=:place * @space.1", "height": "=@space.1"},
        "index": {"box": {"fill": "accent"}, "width": "=:index * @space.1", "height": "=@space.1"},
        "title": {
            "text": {"content": "title", "style": "type.body", "fill": "text-primary"},
            "width": "=:width",
            "height": "=@space.4",
        },
    },
    preferred={"height": "=@space.4"},
)


def test_what_a_released_version_declares_asks_its_owner_and_what_the_scene_shows_fails(
    tmp_path: Path,
) -> None:
    """The version is listed released as it stands, as a later capability's tightened check
    would find it: the release refuses what it declares."""
    root = two_drafts(tmp_path, FAULTS["division-by-zero"])
    write(root / COMPONENTS / "odd.yaml", ODD)
    write(
        root / PIECE_FOLDER / "content.en.yaml",
        yaml_text(bound("content", body={"use": "tests/odd", "title": "Odd."})),
    )
    release(root, "tests")
    owner = "the owner of `tests`, who corrects it in a new release"
    file = f"{COMPONENTS}/odd.yaml"
    assert [each[:2] + each[3:4] for each in found(root, "two-owners")] == [
        (f"{file}#parts.title.height", findings.ATTENTION, owner)
    ]
    reach = {each[0]: each[1:4] for each in found(root, "formula-reach")}
    assert set(reach) == {f"{file}#parts.place.width", LOCK}
    assert reach[f"{file}#parts.place.width"][0::2] == (findings.ATTENTION, owner)
    level, message, _ = reach[LOCK]
    assert level == findings.FAILS
    assert message.startswith(f"under this lock, {VERSION}, released, fails in this piece's scene")
    assert message.endswith("figure/body: tests/odd reads :index but is no item")


@each_fault
@pytest.mark.parametrize(
    ("source", "who"),
    [
        (
            {"kind": "shipped"},
            "whoever maintains the capability, who corrects `tests` where it is authored",
        ),
        (ELSEWHERE, "the owner of `tests`, who corrects it in a new release"),
    ],
    ids=["a-shipped-copy", "another-repositorys-version"],
)
def test_the_same_fault_in_a_library_the_project_does_not_own_asks_its_owner(
    tmp_path: Path, fault: Fault, source: dict[str, str], who: str
) -> None:
    root = two_drafts(tmp_path, fault)
    release(root, "tests", **source)
    [(place, level, _, named, _)] = found(root, fault.label)
    assert (place, level, named) == (f"{fault.file}#{fault.where}", findings.ATTENTION, who)


def test_a_released_version_whose_folder_changed_keeps_the_failure_where_it_fails(
    tmp_path: Path,
) -> None:
    fault = FAULTS["a-stand-in-too-long"]
    root = two_drafts(tmp_path, fault)
    release_tests(root)
    write(root / COMPONENTS / "notes.txt", "Added after the release.\n")
    [(place, level, _, _, _)] = found(root, fault.label)
    assert (place, level) == (f"{fault.file}#{fault.where}", findings.FAILS)
    assert [each[1] for each in found(root, "library-changed")] == [findings.FAILS]
