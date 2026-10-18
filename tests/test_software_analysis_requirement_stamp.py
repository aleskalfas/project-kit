"""software-analysis: the stamp of each of the three kinds of requirement (#1692).

Held to software-analysis DEC-002:

- **each kind in its place** (points 1 to 4) — `pkit analysis new
  quality-requirement`, `functional-requirement` and `constraint` write
  `REQ-NNN-<slug>.md` in the kind's folder, or an area's folder in it, rendered
  from the kind's structure: its heading the id, the kind and the title, and each
  field and part a writer fills holding its hint;
- **one numbering** (point 2) — the next free `REQ-NNN` across the three kinds,
  past every number the working tree and the default branch hold in any of the
  three places and every number the default branch's history gave, a file moved
  to another kind included; the numbering setting frees a requirement's id as it
  frees a use case's;
- **its actors and what it refines** (point 6) — written in `actors` and
  `refines`, each an artefact anchor; a requirement with no anchor at all gives
  the reason instead;
- **what it refuses** (points 6 and 7) — an actor or a requirement the analysis
  does not hold or has withdrawn, a requirement that refines itself,
  `--unanchored-because` beside an anchor, and a placeholder left in a value —
  writing nothing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from project_kit.friction_validate import validate_friction
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    ANALYSIS,
    CAPABILITY,
    CONSTRAINTS,
    FUNCTIONAL,
    MAIN,
    QUALITY,
    SA,
    actor_at,
    below_floor,
    field_hint,
    fill,
    front,
    installed,
    new,
    prepare,
    stamped,
)
from tests.test_software_analysis_check import check, errors

#: Each kind of requirement, its place, and the name its heading shows beside its id.
KINDS = {
    "quality-requirement": (QUALITY, "Quality"),
    "functional-requirement": (FUNCTIONAL, "Functional"),
    "constraint": (CONSTRAINTS, "Constraint"),
}

#: The capability's settings file, where the numbering setting lies.
SETTING = f"{SA.as_posix()}/project/config.yaml"

#: How many characters of a commit a message shows.
SHORT = 12


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch)


def _template_body(kind: str) -> str:
    """The body of a kind's template, which the stamp renders the same way."""
    text = (CAPABILITY / "templates" / f"{kind}.md").read_text(encoding="utf-8")
    return text.split("\n---\n\n", 1)[1]


# --- each kind in its place ------------------------------------------------------------------


# Slow by design: two stamps for each kind, each a script that starts several `pkit` processes.
@pytest.mark.parametrize("kind", sorted(KINDS))
def test_each_kind_is_stamped_in_its_place_rendered_from_its_structure(
    project: AdopterRepo, kind: str
) -> None:
    """The file lies in its kind's folder, named `REQ-NNN-<slug>.md`. Its front matter is
    its template's, with its id, its title, its actors and what it refines, and its
    statement, its measure and where it holds each holding the field's declared hint. Its
    body is its template's, the heading reading the id, the kind and the title. In an
    area, it lies in the area's folder of its kind's place."""
    place, shown = KINDS[kind]
    stamped(project, "actor", "tester")
    args = ("--actor", "ACT-tester", "--path", "tests/test_run.py", "--title", "Show it fast")
    assert stamped(project, kind, "show-fast", *args) == "REQ-001"
    rel = f"{place}/REQ-001-show-fast.md"
    assert front(project, rel) == {
        "id": "REQ-001",
        "title": "Show it fast",
        "status": "active",
        "statement": field_hint(kind, "statement"),
        "measure": field_hint(kind, "measure"),
        "applies-to": field_hint(kind, "applies-to"),
        "actors": ["ACT-tester"],
        "refines": [],
        "pkit": {
            "friction": {"anchors": {"path": ["tests/test_run.py"], "artefact": ["ACT-tester"]}}
        },
    }
    body = (project.root / rel).read_text(encoding="utf-8").split("\n---\n\n", 1)[1]
    heading = f"# REQ-001 · {shown} · Show it fast\n"
    assert body == _template_body(kind).replace(f"# REQ-000 · {shown} · <Title>\n", heading)
    assert body.startswith(heading)
    # What the stamp writes is plain enough for any project's writing rules (#1351).
    assert below_floor((project.root / rel).read_text(encoding="utf-8")) == []
    # In an area's folder of its kind's place, numbered on.
    assert stamped(project, kind, "later", "--area", "reports") == "REQ-002"
    assert (project.root / place / "reports" / "REQ-002-later.md").is_file()
    # The title is the slug, capitalised, by default.
    assert front(project, f"{place}/reports/REQ-002-later.md")["title"] == "Later"


# --- one numbering ---------------------------------------------------------------------------


# Slow by design: eight stamps, each a script that starts several `pkit` processes.
def test_requirements_share_one_numbering_with_the_default_branch_and_its_history(
    project: AdopterRepo,
) -> None:
    """A requirement takes one past the highest `REQ-NNN` the three kinds' places hold, in
    the working tree and on the default branch, and past every number the default
    branch's history gave a file of any of them, one moved to another kind and deleted
    since included. A file's number is read from its name too. Use cases number apart."""
    stamped(project, "actor", "tester")
    assert stamped(project, "quality-requirement", "fast") == "REQ-001"
    assert stamped(project, "constraint", "country") == "REQ-002"
    assert stamped(project, "functional-requirement", "approved", "--area", "reports") == "REQ-003"
    assert stamped(project, "use-case", "run", "--actor", "ACT-tester") == "UC-001"
    project.commit("REQ-001 to REQ-003, and UC-001")
    project.checkout("topic", create=True)
    project.checkout(MAIN)
    assert stamped(project, "functional-requirement", "drafts") == "REQ-004"
    project.commit("REQ-004 on main")
    # Moved to another kind, it keeps its id (DEC-002 point 2), then is deleted.
    moved = f"{CONSTRAINTS}/REQ-004-drafts.md"
    project.rename(f"{FUNCTIONAL}/REQ-004-drafts.md", moved)
    project.commit("REQ-004 deleted", {moved: None})
    project.checkout("topic")
    completed = new(project, "quality-requirement", "reliable")
    assert completed.returncode == 0, completed.stderr
    note, done = completed.stdout.splitlines()
    assert done == f"stamped REQ-005 at {QUALITY}/REQ-005-reliable.md"
    # The history's number is the one it follows: the note names the last file it was given.
    assert note.startswith(f"REQ-005 follows REQ-004, the number main's history gave {moved} ")
    # A file whose front matter cannot be read still holds the number its name carries.
    project.write({f"{CONSTRAINTS}/REQ-0009-broken.md": "---\nid: [unclosed\n---\n"})
    assert stamped(project, "constraint", "after-broken") == "REQ-010"
    # Use cases number apart from requirements.
    assert stamped(project, "use-case", "export", "--actor", "ACT-tester") == "UC-002"


def _freed_by(repo: AdopterRepo, commit: str, ids: tuple[str, ...]) -> None:
    """The numbering setting, one entry freeing `ids` by `commit`."""
    written = f'    - commit: "{commit}"\n      ids: [{", ".join(ids)}]\n'
    repo.write({SETTING: f"schema_version: 1\nnumbering:\n  freed-by:\n{written}"})


# Slow by design: four stamps, each a script that starts several `pkit` processes.
def test_the_numbering_setting_frees_a_requirement_s_id(project: AdopterRepo) -> None:
    """A pilot's requirements deleted from the default branch, their ids listed in the
    setting under the commit that removed them: the stamp gives the ids again, and says
    so, naming the commit. Without the entry, the numbers stay taken."""
    stamped(project, "quality-requirement", "pilot-one")
    stamped(project, "constraint", "pilot-two")
    added = project.commit("the pilot")
    one, two = f"{QUALITY}/REQ-001-pilot-one.md", f"{CONSTRAINTS}/REQ-002-pilot-two.md"
    removed = project.commit("the pilot removed", {one: None, two: None})
    assert stamped(project, "functional-requirement", "taken") == "REQ-003"
    project.write({f"{FUNCTIONAL}/REQ-003-taken.md": None})
    _freed_by(project, removed, ("REQ-001", "REQ-002"))
    completed = new(project, "functional-requirement", "again")
    assert completed.returncode == 0, completed.stderr
    note, done = completed.stdout.splitlines()
    assert done == f"stamped REQ-001 at {FUNCTIONAL}/REQ-001-again.md"
    assert note == (
        f"REQ-002 is free again, freed by {removed[:SHORT]}, as the project's numbering "
        f"setting names: main's history gave it {two} (commit {added[:SHORT]}), which "
        f"{removed[:SHORT]} removed (DEC-001 point 3)"
    )


# Slow by design: two stamps, each a script that starts several `pkit` processes.
def test_a_requirement_moved_to_another_kind_then_deleted_is_not_freed(
    project: AdopterRepo,
) -> None:
    """The name a requirement had in its first kind's folder still counts, as a use
    case's name before a move between areas does. So an entry that lists its id under
    the commit that deleted it is refused, and the stamp numbers past it."""
    stamped(project, "functional-requirement", "drafts")
    project.commit("REQ-001")
    first, moved = f"{FUNCTIONAL}/REQ-001-drafts.md", f"{CONSTRAINTS}/REQ-001-drafts.md"
    project.rename(first, moved)
    removed = project.commit("REQ-001 deleted", {moved: None})
    _freed_by(project, removed, ("REQ-001",))
    completed = new(project, "quality-requirement", "again")
    assert completed.returncode == 1, completed.stdout
    assert f"REQ-001 is not freed by {removed[:SHORT]}: the history before it gave REQ-001 to " in (
        completed.stderr
    )
    assert f"to {first} too (commit " in completed.stderr
    project.write({SETTING: None})
    assert stamped(project, "quality-requirement", "again") == "REQ-002"


# --- its actors and what it refines ----------------------------------------------------------


# Slow by design: five stamps and the check, each a script that starts `pkit` processes.
def test_its_actors_and_what_it_refines_are_written_and_anchored(project: AdopterRepo) -> None:
    """`--actor` and `--refines`, each repeatable and each once, are written in `actors`
    and `refines`, and each is an artefact anchor, beside the records and paths given
    (DEC-002 point 6). A requirement of another kind may be refined. What it writes,
    filled, passes the check and the core's friction pass."""
    stamped(project, "actor", "tester", "--path", "src/run.py")
    stamped(project, "actor", "admin", "--path", "src/run.py")
    stamped(project, "quality-requirement", "fast", "--path", "src/run.py")
    args = (
        *("--actor", "ACT-tester", "--actor", "ACT-admin", "--actor", "ACT-tester"),
        *("--refines", "REQ-001", "--record", "ADR-001"),
    )
    assert stamped(project, "constraint", "on-site", *args) == "REQ-002"
    written = front(project, f"{CONSTRAINTS}/REQ-002-on-site.md")
    assert written["actors"] == ["ACT-tester", "ACT-admin"]
    assert written["refines"] == ["REQ-001"]
    assert written["pkit"] == {
        "friction": {
            "anchors": {"record": ["ADR-001"], "artefact": ["ACT-tester", "ACT-admin", "REQ-001"]}
        }
    }
    reason = ("--unanchored-because", "A stakeholder states it, and nothing embodies it yet.")
    assert stamped(project, "functional-requirement", "stated", *reason) == "REQ-003"
    stated = front(project, f"{FUNCTIONAL}/REQ-003-stated.md")
    assert (stated["actors"], stated["refines"]) == ([], [])
    assert stated["pkit"] == {"friction": {"unanchored-because": reason[1]}}
    fill(project)
    assert errors(check(project)) == []
    assert validate_friction(project.root).errors == ()


# --- what it refuses -------------------------------------------------------------------------


# Slow: five stamps, built once per session; the first test to ask pays it in its setup.
def _ground(repo: AdopterRepo) -> None:
    """`prepare`, then the actor ACT-tester, the actor ACT-retired withdrawn, the use case
    UC-001, the quality requirement REQ-001, and the constraint REQ-002 withdrawn."""
    prepare(repo)
    stamped(repo, "actor", "tester")
    stamped(repo, "actor", "retired")
    stamped(repo, "use-case", "one", "--actor", "ACT-tester")
    stamped(repo, "quality-requirement", "fast")
    stamped(repo, "constraint", "gone")
    for rel in (actor_at("ACT-retired"), f"{CONSTRAINTS}/REQ-002-gone.md"):
        path = repo.root / rel
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("status: active", "status: withdrawn", 1), encoding="utf-8")


@pytest.fixture
def grounded(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    """What the refusals below are judged against (`_ground`)."""
    return installed(make_adopter_repo, monkeypatch, then=_ground)


REASON = ("--unanchored-because", "A stakeholder states it.")


@pytest.mark.parametrize(
    ("args", "refusal"),
    [
        (("--actor", "ACT-nobody"), "no actor ACT-nobody in the analysis"),
        (("--actor", "ACT-retired"), "actor ACT-retired is withdrawn"),
        (("--refines", "REQ-009"), "no requirement REQ-009 in the analysis"),
        (("--refines", "UC-001"), "no requirement UC-001 in the analysis"),
        (
            ("--refines", "REQ-002"),
            "constraint REQ-002 is withdrawn (",
        ),
        (
            ("--refines", "REQ-003"),
            "--refines REQ-003 is the id this requirement takes: a requirement never refines "
            "itself (DEC-002 point 6)",
        ),
        (
            (*REASON, "--actor", "ACT-tester"),
            "a quality requirement with anchors is not unanchored: give its anchors (--path, "
            "--record, --actor, --refines) or the reason it has none (--unanchored-because), "
            "not both",
        ),
        ((*REASON, "--refines", "REQ-001"), "with anchors is not unanchored"),
        ((*REASON, "--path", "src/run.py"), "with anchors is not unanchored"),
        (("--title", "<Title>"), "--title still holds the placeholder '<Title>'"),
        (
            ("--unanchored-because", "<why>"),
            "--unanchored-because still holds the placeholder '<why>'",
        ),
        (("--area", "Big Area"), "is not a word"),
    ],
    ids=[
        "no-actor",
        "withdrawn-actor",
        "no-requirement",
        "a-use-case",
        "withdrawn-requirement",
        "itself",
        "unanchored-with-an-actor",
        "unanchored-refining",
        "unanchored-with-a-path",
        "placeholder-title",
        "placeholder-reason",
        "area-no-word",
    ],
)
def test_a_requirement_stamp_refuses_what_it_cannot_ground(
    grounded: AdopterRepo, args: tuple[str, ...], refusal: str
) -> None:
    """Each refusal says why and writes nothing (DEC-002 points 6 and 7)."""
    before = sorted(p.relative_to(grounded.root) for p in (grounded.root / ANALYSIS).rglob("*"))
    completed = new(grounded, "quality-requirement", "next", *args)
    assert completed.returncode == 1, completed.stdout
    assert refusal in completed.stderr
    after = sorted(p.relative_to(grounded.root) for p in (grounded.root / ANALYSIS).rglob("*"))
    assert after == before


def test_a_withdrawn_requirement_may_not_be_refined_but_keeps_its_number(
    grounded: AdopterRepo,
) -> None:
    """The withdrawn constraint holds its number: the next requirement, of any kind, is
    numbered past it."""
    assert stamped(grounded, "functional-requirement", "next", "--refines", "REQ-001") == "REQ-003"
    written: dict[str, Any] = front(grounded, f"{FUNCTIONAL}/REQ-003-next.md")
    assert written["refines"] == ["REQ-001"]
