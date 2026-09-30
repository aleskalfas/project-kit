"""software-analysis: the analysis location, its places, and stamping artefacts (#887).

Held to software-analysis DEC-001 points 2 to 4:

- the **package metadata** — the analysis location, the `analysis` sub-path of
  the internal root, and one place per kind inside it; the revalidation
  records' folder is not one, and no surface is declared;
- the **stamp**, `pkit analysis new` (the capability's alias) — ids: `UC-NNN`
  and `JRN-NNN` numbered past the working tree and the default branch,
  withdrawn ones included, `ACT-<slug>` and `TERM-<slug>`; the location
  recorded on first use, so a later root change moves nothing; the anchors
  point 4 asks for; an entry added to a collection file with every other byte
  kept; and what it refuses;
- **one home for discovery**: the scripts read the places through the
  backbone, at head and at a commit, and record the location through it;
  they carry no matcher, listing, place reader or location writer of their own.

The check is `test_software_analysis_check.py`'s, the schemas and templates
`test_software_analysis_templates.py`'s.
"""

from __future__ import annotations

import ast
import json
import os
import re
import stat
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import docs_roots as dr
from project_kit import friction_discovery as fd
from project_kit.cli import main
from project_kit.friction_validate import validate_friction
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    ACTORS,
    ANALYSIS,
    CAPABILITY,
    CONFIG,
    GLOSSARY,
    JOURNEYS,
    NEW,
    RECORDED,
    RECORDS,
    USE_CASES,
    VALIDATE,
    front,
    installed,
    load,
    new,
    run_script,
    seed,
    stamped,
)

# The living-docs guard's reading of a script's code: one list of what re-deriving
# discovery would take, shared rather than copied.
from tests.test_living_docs_spaces import (
    _discovery_tokens,  # pyright: ignore[reportPrivateUsage]
)


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch)


# --- the package metadata (DEC-001 point 2) -------------------------------------------------


def test_the_package_declares_the_analysis_location_and_one_place_per_kind(
    project: AdopterRepo,
) -> None:
    location = dr.capability_location(project.root, "software-analysis", "analysis")
    assert location == dr.Location(Path(ANALYSIS), dr.Source.DERIVED)
    settings = fd.read_friction_settings(project.root)
    ours = [p.resolved for p in settings.places if p.source == "capability:software-analysis"]
    assert ours == [GLOSSARY, ACTORS, USE_CASES, JOURNEYS]
    assert not any(RECORDS in place for place in ours)  # an act, not an anchored artefact
    assert [p.resolved for p in settings.surface if p.source.startswith("capability:")] == []


def _kind_of_place_keys() -> list[str]:
    """The places `_lib/model.py` knows, read from its source: the scripts run in
    their own environment, and their `_lib` is not importable beside living-docs'."""
    source = (CAPABILITY / "scripts" / "_lib" / "model.py").read_text(encoding="utf-8")
    for node in ast.parse(source).body:
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "KIND_OF_PLACE"
            and isinstance(node.value, ast.Dict)
        ):
            return [str(ast.literal_eval(key)) for key in node.value.keys if key is not None]
    raise AssertionError("_lib/model.py defines no KIND_OF_PLACE")


def test_the_scripts_know_each_place_by_the_package_s_own_words() -> None:
    package = load((CAPABILITY / "package.yaml").read_text(encoding="utf-8"))
    places: list[dict[str, str]] = package["friction"]["places"]
    assert sorted(place["path"] for place in places) == sorted(_kind_of_place_keys())
    assert {place["location"] for place in places} == {"analysis"}


@pytest.mark.parametrize("namespace", ["analysis", "software-analysis"])
def test_the_stamp_is_reached_under_the_capability_and_its_alias(
    project: AdopterRepo, namespace: str
) -> None:
    result = CliRunner().invoke(main, [namespace, "--help"])
    assert result.exit_code == 0, result.output
    assert "new " in result.output


# --- stamping (DEC-001 points 2 to 4) -------------------------------------------------------


def test_the_first_stamp_records_the_location_and_a_root_change_moves_nothing(
    project: AdopterRepo,
) -> None:
    completed = new(project, "actor", "tester")
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines() == [
        f"recorded software-analysis analysis = {ANALYSIS}  ({RECORDED})",
        f"stamped ACT-tester at {ACTORS}#ACT-tester",
    ]
    assert dr.recorded_capability_locations(project.root, "software-analysis") == {
        "analysis": ANALYSIS
    }
    project.write({CONFIG: "docs:\n  internal: handbook\n"})
    completed = new(project, "term", "sandbox")
    assert completed.stdout.splitlines() == [f"stamped TERM-sandbox at {GLOSSARY}#TERM-sandbox"]


def test_use_cases_and_journeys_are_numbered_in_order_with_their_anchors(
    project: AdopterRepo,
) -> None:
    seed(project)
    run_suite = front(project, f"{USE_CASES}/UC-001-run-suite.md")
    assert run_suite == {
        "id": "UC-001",
        "title": "Run suite",
        "status": "active",
        "actor": "ACT-tester",
        "pkit": {"friction": {"anchors": {"path": ["src/run.py"], "artefact": ["ACT-tester"]}}},
    }
    body = (project.root / USE_CASES / "UC-001-run-suite.md").read_text(encoding="utf-8")
    assert "\n# UC-001 — Run suite\n" in body
    journey = front(project, f"{JOURNEYS}/JRN-001-first-run.md")
    assert journey["title"] == "First run"
    assert journey["steps"] == ["UC-001", "UC-002"]
    assert journey["pkit"] == {"friction": {"anchors": {"artefact": ["UC-001", "UC-002"]}}}
    body = (project.root / JOURNEYS / "JRN-001-first-run.md").read_text(encoding="utf-8")
    assert "# JRN-001 — First run\n" in body
    assert "1. UC-001 — " in body and "2. UC-002 — " in body and "UC-000" not in body
    assert "- **UC-001 → UC-002:** " in body
    title = ("--title", "Export: the report as a file")
    area = stamped(
        project, "use-case", "export", "--actor", "ACT-tester", "--area", "reports", *title
    )
    assert area == "UC-003"
    exported = f"{USE_CASES}/reports/UC-003-export.md"
    assert front(project, exported)["title"] == "Export: the report as a file"
    body = (project.root / exported).read_text(encoding="utf-8")
    assert "\n# UC-003 — Export: the report as a file\n" in body


def test_every_stamped_artefact_passes_the_core_s_friction_pass(project: AdopterRepo) -> None:
    seed(project)
    stamped(project, "term", "sandbox", "--name", "Sandbox", "--record", "ADR-001")
    result = validate_friction(project.root)
    assert result.errors == ()
    discovery = fd.discover_artefacts(project.root)
    ids = [a.id for a in discovery.artefacts]
    assert ids == ["TERM-sandbox", "ACT-tester", "UC-001", "UC-002", "JRN-001"]


def _placeholder_line() -> str:
    template = (CAPABILITY / "templates" / "actors.md").read_text(encoding="utf-8")
    return template.rsplit("\n\n", 1)[1]


_ADMIN_ONLY = (
    "---\n"
    "# The project's own comment, kept.\n"
    "ACT-admin:\n"
    "  name: Admin   # inline, kept\n"
    "  status: active\n"
    "  needs: [Configure the service]\n"
    "  pkit: {friction: {anchors: {path: [src/**]}}}\n"
    "---\n"
    "\n"
    "# Actors\n"
    "\n"
    "## ACT-admin — Admin\n"
    "\n"
    "Runs it.\n"
)


def test_an_entry_is_added_to_a_collection_leaving_every_other_byte(project: AdopterRepo) -> None:
    project.write({ACTORS: _ADMIN_ONLY})
    assert stamped(project, "actor", "tester", "--name", "Test author") == "ACT-tester"
    text = (project.root / ACTORS).read_text(encoding="utf-8")
    closing = _ADMIN_ONLY.index("---\n", 4)
    assert text.startswith(_ADMIN_ONLY[:closing])
    assert text[closing:].startswith("ACT-tester:\n  name: Test author\n")
    assert text.endswith("Runs it.\n\n## ACT-tester — Test author\n\n" + _placeholder_line())
    assert list(front(project, ACTORS)) == ["ACT-admin", "ACT-tester"]


def test_an_entry_is_added_where_its_id_sorts(project: AdopterRepo) -> None:
    """Before the first entry and section whose id sorts after it — in the front matter
    and in the body alike — with every other byte as it was."""
    project.write({ACTORS: _ADMIN_ONLY})
    assert stamped(project, "actor", "able", "--name", "Able") == "ACT-able"
    text = (project.root / ACTORS).read_text(encoding="utf-8")
    comment = "---\n# The project's own comment, kept.\n"
    entry = text[len(comment) : text.index("ACT-admin:\n")]
    assert entry.startswith("ACT-able:\n  name: Able\n")
    section = "## ACT-able — Able\n\n" + _placeholder_line()
    rest = _ADMIN_ONLY[len(comment) :].replace("# Actors\n\n", f"# Actors\n\n{section}\n")
    assert text == comment + entry + rest
    assert list(front(project, ACTORS)) == ["ACT-able", "ACT-admin"]


@pytest.mark.parametrize(
    ("ending", "between"),
    [("", "\n\n"), ("\n", "\n"), ("\n\n\n", "")],
    ids=["none", "one", "three"],
)
def test_an_entry_added_last_keeps_the_file_s_ending(
    project: AdopterRepo, ending: str, between: str
) -> None:
    """The section added after the last one keeps every byte of the file before it —
    no line ending added to its last line, no blank line taken away — and only what
    separates the two is written."""
    original = _ADMIN_ONLY.removesuffix("\n") + ending
    project.write({ACTORS: original})
    stamped(project, "actor", "tester", "--name", "Test author")
    text = (project.root / ACTORS).read_text(encoding="utf-8")
    closing = original.index("---\n", 4)
    assert text.startswith(original[:closing] + "ACT-tester:\n  name: Test author\n")
    section = "## ACT-tester — Test author\n\n" + _placeholder_line()
    assert text.endswith(original[closing:] + between + section)


def test_a_collection_file_is_replaced_whole_keeping_its_mode(project: AdopterRepo) -> None:
    """Written beside itself and moved over, so a failure halfway never leaves it
    half-written: a new file in its place, with its mode, and nothing left beside it."""
    project.write({ACTORS: _ADMIN_ONLY})
    actors = project.root / ACTORS
    actors.chmod(0o640)
    inode = actors.stat().st_ino
    stamped(project, "actor", "tester")
    assert actors.stat().st_ino != inode
    assert stat.S_IMODE(actors.stat().st_mode) == 0o640
    assert sorted(p.name for p in actors.parent.iterdir()) == ["actors.md"]


def test_a_collection_file_with_crlf_line_endings_stays_crlf(project: AdopterRepo) -> None:
    """A checkout with `core.autocrlf` writes every collection file CRLF: the stamp edits
    it as LF and writes it back CRLF, so it is byte for byte the LF result with every
    line ending CRLF — the file's own bytes kept, the entry's and the section's lines
    ending as the file's do."""
    project.write({ACTORS: _ADMIN_ONLY})
    stamped(project, "actor", "able")
    stamped(project, "actor", "tester")
    as_lf = (project.root / ACTORS).read_bytes()
    project.write({ACTORS: _ADMIN_ONLY.replace("\n", "\r\n")})
    stamped(project, "actor", "able")
    stamped(project, "actor", "tester")
    assert (project.root / ACTORS).read_bytes() == as_lf.replace(b"\n", b"\r\n")


def test_a_collection_file_with_mixed_line_endings_is_refused(project: AdopterRepo) -> None:
    mixed = _ADMIN_ONLY.replace("\n", "\r\n", 3)
    project.write({ACTORS: mixed})
    completed = new(project, "actor", "tester")
    assert completed.returncode == 1
    assert completed.stderr.startswith(
        f"refused: {ACTORS} has mixed line endings — some lines end CRLF, others LF or a lone "
        "CR: the stamp writes its lines with the file's own ending, and this file has no one "
        "ending — make them one, then stamp again"
    )
    assert (project.root / ACTORS).read_bytes() == mixed.encode("utf-8")


def test_a_write_that_fails_records_no_location(project: AdopterRepo) -> None:
    """The location is recorded once the artefact is written, never before: a write that
    fails leaves the recorded locations as they were."""
    stamped(project, "actor", "tester")
    (project.root / RECORDED).unlink()  # an analysis whose location was never recorded
    project.write({f"{USE_CASES}/reports": "a file where the area's folder goes\n"})
    completed = new(project, "use-case", "export", "--actor", "ACT-tester", "--area", "reports")
    assert completed.returncode == 1
    assert completed.stderr.startswith(
        f"refused: {USE_CASES}/reports/UC-001-export.md could not be written: "
    )
    assert not (project.root / RECORDED).exists()


#: A `pkit` whose `docs record-location` fails, and every other command as the real one.
_FAILING_RECORD = """#!{python}
import subprocess, sys
if sys.argv[1:3] == ["docs", "record-location"]:
    sys.stderr.write("error: the recorded locations cannot be written\\n")
    sys.exit(1)
sys.exit(subprocess.run([sys.executable, "-m", "project_kit", *sys.argv[1:]]).returncode)
"""


def test_a_recording_that_fails_leaves_nothing_written(
    project: AdopterRepo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The artefact written, the location cannot be recorded: the file is put back as it
    was — a collection's bytes, or no file and no folder made for it."""
    stamped(project, "actor", "tester")
    before = (project.root / ACTORS).read_bytes()
    (project.root / RECORDED).unlink()
    failing = tmp_path / "failing-record"
    failing.mkdir()
    (failing / "pkit").write_text(_FAILING_RECORD.format(python=sys.executable), encoding="utf-8")
    (failing / "pkit").chmod(0o755)
    monkeypatch.setenv("PATH", f"{failing}{os.pathsep}{os.environ['PATH']}")
    for args, gone in (
        (("actor", "admin"), None),
        (("use-case", "export", "--actor", "ACT-tester", "--area", "reports"), USE_CASES),
    ):
        completed = new(project, *args)
        assert completed.returncode == 1, completed.stdout
        assert "the analysis location could not be recorded: " in completed.stderr
        assert (project.root / ACTORS).read_bytes() == before
        assert gone is None or not (project.root / gone).exists()
    assert not (project.root / RECORDED).exists()


@pytest.mark.parametrize(
    ("kind", "rel", "prefix"), [("actor", ACTORS, "ACT"), ("term", GLOSSARY, "TERM")]
)
def test_entries_two_branches_add_merge_cleanly(
    project: AdopterRepo, kind: str, rel: str, prefix: str
) -> None:
    """Two lines of work adding different entries write to different places of the
    collection file, so git merges them without a conflict."""
    stamped(project, kind, "middle")
    project.commit("middle")
    project.checkout("early", create=True)
    stamped(project, kind, "alpha")
    project.commit("alpha, on early")
    project.checkout("main")
    stamped(project, kind, "zulu")
    project.commit("zulu, on main")
    merged = project.git("merge", "--no-edit", "early", check=False)
    assert merged.returncode == 0, merged.stdout + merged.stderr
    ids = [f"{prefix}-alpha", f"{prefix}-middle", f"{prefix}-zulu"]
    assert list(front(project, rel)) == ids
    text = (project.root / rel).read_text(encoding="utf-8")
    assert re.findall(r"^## (\S+)", text, flags=re.MULTILINE) == ids


def test_numbers_count_the_default_branch_and_withdrawn_use_cases(project: AdopterRepo) -> None:
    stamped(project, "actor", "tester")
    stamped(project, "use-case", "one", "--actor", "ACT-tester")
    project.commit("UC-001")
    project.checkout("topic", create=True)
    project.checkout("main")
    stamped(project, "use-case", "two", "--actor", "ACT-tester")
    project.commit("UC-002 on main")
    project.checkout("topic")
    # The working tree holds UC-001 only; main took UC-002 since.
    assert stamped(project, "use-case", "three", "--actor", "ACT-tester") == "UC-003"
    path = project.root / USE_CASES / "UC-003-three.md"
    path.write_text(path.read_text(encoding="utf-8").replace("active", "withdrawn"), "utf-8")
    assert stamped(project, "use-case", "four", "--actor", "ACT-tester") == "UC-004"


def test_a_number_deleted_from_the_default_branch_is_never_used_again(
    project: AdopterRepo,
) -> None:
    """Deleting the highest-numbered use case, against the rule, frees nothing: the
    number is counted over every file the default branch's history held — under
    every name it had, a move into an area included — as well as the tree."""
    stamped(project, "actor", "tester")
    stamped(project, "use-case", "one", "--actor", "ACT-tester")
    stamped(project, "use-case", "two", "--actor", "ACT-tester")
    stamped(
        project, "journey", "trip", "--actor", "ACT-tester", "--step", "UC-001", "--step", "UC-002"
    )
    project.commit("UC-001, UC-002 and JRN-001")
    project.rename(f"{USE_CASES}/UC-002-two.md", f"{USE_CASES}/reports/UC-002-two.md")
    project.commit(
        "UC-002 deleted, and JRN-001",
        {
            f"{USE_CASES}/reports/UC-002-two.md": None,
            f"{JOURNEYS}/JRN-001-trip.md": None,
        },
    )
    assert not list((project.root / USE_CASES).rglob("UC-002-*.md"))
    project.checkout("topic", create=True)
    completed = new(project, "use-case", "three", "--actor", "ACT-tester")
    assert completed.returncode == 0, completed.stderr
    note, done = completed.stdout.splitlines()
    assert done == f"stamped UC-003 at {USE_CASES}/UC-003-three.md"
    # The history's number is the one it follows: the note names the file it was given.
    assert note.startswith(
        f"UC-003 follows UC-002, the number main's history gave {USE_CASES}/reports/UC-002-two.md "
        "(commit "
    )
    assert note.endswith(
        "), which neither main nor the working tree holds now: a number is never used again "
        "(DEC-001 point 3)"
    )
    steps = ("--step", "UC-001", "--step", "UC-003")
    assert stamped(project, "journey", "again", "--actor", "ACT-tester", *steps) == "JRN-002"


def test_the_history_counts_the_files_the_tree_reading_counts(project: AdopterRepo) -> None:
    """A number the history gave is counted only when the backbone's reading at the commit
    that added the file held it as a file of the place — a Markdown file there, not left
    out by `friction.exclude`. A non-Markdown file named after a number, removed since,
    raises nothing; an excluded example raises nothing, present or removed; a Markdown
    note named after a number held its number while it was there, so it still does, and
    the stamp names it."""
    examples = f"{USE_CASES}/examples"
    config = f"docs:\n  internal: tech-docs\nfriction:\n  exclude:\n    - {examples}\n"
    stamped(project, "actor", "tester")
    stamped(project, "use-case", "one", "--actor", "ACT-tester")
    example = (project.root / USE_CASES / "UC-001-one.md").read_text(encoding="utf-8")
    project.write(
        {
            CONFIG: config,
            f"{examples}/UC-900-example.md": example.replace("UC-001", "UC-900"),
            f"{USE_CASES}/UC-800-flow.svg": "<svg/>\n",
        }
    )
    project.commit("UC-001, an excluded example and a diagram")
    # Present: the example is no part of the analysis, and the diagram no file of the place.
    assert stamped(project, "use-case", "two", "--actor", "ACT-tester") == "UC-002"
    checked = json.loads(run_script(project, VALIDATE, "--json").stdout)
    assert not [f for f in checked["findings"] if f["location"].startswith(examples)]
    project.commit(
        "UC-002; the example and the diagram removed",
        {f"{examples}/UC-900-example.md": None, f"{USE_CASES}/UC-800-flow.svg": None},
    )
    # Removed: the history judges each as the reading of its commit did, so neither counts.
    completed = new(project, "use-case", "three", "--actor", "ACT-tester")
    assert completed.stdout.splitlines() == [f"stamped UC-003 at {USE_CASES}/UC-003-three.md"]
    notes = f"{USE_CASES}/UC-2026-notes.md"
    project.commit("notes", {notes: "Some notes.\n"})
    project.commit("notes removed", {notes: None})
    completed = new(project, "use-case", "four", "--actor", "ACT-tester")
    note, done = completed.stdout.splitlines()
    assert done == f"stamped UC-2027 at {USE_CASES}/UC-2027-four.md"
    assert note.startswith(f"UC-2027 follows UC-2026, the number main's history gave {notes} ")


def test_a_shallow_clone_s_stamp_says_its_history_stops_early(
    project: AdopterRepo, tmp_path: Path
) -> None:
    """Git's history stops where a shallow clone does: the stamp says so, as the friction
    report does, rather than number past an unread history in silence."""
    stamped(project, "actor", "tester")
    stamped(project, "use-case", "one", "--actor", "ACT-tester")
    project.commit("UC-001")
    shallow = tmp_path / "shallow"
    project.git("clone", "-q", "--depth", "1", f"file://{project.root}", str(shallow))
    clone = AdopterRepo(shallow, source_kit=project.source_kit)
    completed = new(clone, "use-case", "two", "--actor", "ACT-tester")
    assert completed.returncode == 0, completed.stderr
    note, done = completed.stdout.splitlines()
    assert note == (
        "history: shallow clone — main's history was read back to where the clone stops, so a "
        "number a file was given before it is not counted; fetch the full history (`git fetch "
        "--unshallow`) to count every one"
    )
    assert done == f"stamped UC-002 at {USE_CASES}/UC-002-two.md"
    # An actor's or term's id is a person's choice: no history is read for one.
    completed = new(clone, "actor", "admin")
    assert completed.stdout.splitlines() == [f"stamped ACT-admin at {ACTORS}#ACT-admin"]


def test_a_number_a_file_s_name_carries_is_held_whatever_the_file_holds(
    project: AdopterRepo,
) -> None:
    """A file with no front matter, one whose front matter does not parse, one naming no
    id: the stamp cannot read the id each holds, so it counts the number each name
    carries — in the working tree and on the default branch — and the check reports
    each file (`test_software_analysis_check.py`)."""
    stamped(project, "actor", "tester")
    stamped(project, "use-case", "one", "--actor", "ACT-tester")
    project.commit("UC-001", {f"{USE_CASES}/UC-004-on-main.md": "# No front matter\n"})
    project.checkout("topic", create=True)
    project.write(
        {
            f"{USE_CASES}/UC-005-bare.md": "# No front matter\n",
            f"{USE_CASES}/area/UC-006-broken.md": "---\nid: [unclosed\n---\n",
            f"{USE_CASES}/UC-0007-no-id.md": "---\ntitle: No id\n---\n",
        }
    )
    assert stamped(project, "use-case", "two", "--actor", "ACT-tester") == "UC-008"
    project.write({f"{USE_CASES}/UC-0007-no-id.md": None, f"{USE_CASES}/UC-008-two.md": None})
    assert stamped(project, "use-case", "two", "--actor", "ACT-tester") == "UC-007"


def test_a_number_spelt_with_other_zeros_counts_as_held(project: AdopterRepo) -> None:
    """The stamp reads `UC-0007` as the number 7, as the check's duplicate count does, so
    it never gives a number a file already claims, whatever its spelling — and the ids
    it gives are the one spelling the schema admits."""
    stamped(project, "actor", "tester")
    stamped(project, "use-case", "one", "--actor", "ACT-tester")
    text = (project.root / USE_CASES / "UC-001-one.md").read_text(encoding="utf-8")
    project.write({f"{USE_CASES}/UC-0007-misspelt.md": text.replace("UC-001", "UC-0007")})
    assert stamped(project, "use-case", "two", "--actor", "ACT-tester") == "UC-008"
    project.write({f"{USE_CASES}/UC-999-last.md": text.replace("UC-001", "UC-999")})
    assert stamped(project, "use-case", "three", "--actor", "ACT-tester") == "UC-1000"


def test_without_the_default_branch_ids_come_from_the_working_tree_and_it_says_so(
    project: AdopterRepo,
) -> None:
    stamped(project, "actor", "tester")
    completed = run_script(project, NEW, "use-case", "one", "--actor", "ACT-tester")
    assert completed.returncode == 0, completed.stderr
    assert "origin/main names no commit here, so ids were taken from the working tree" in (
        completed.stdout
    )
    assert completed.stdout.splitlines()[-1] == f"stamped UC-001 at {USE_CASES}/UC-001-one.md"


@pytest.mark.parametrize(
    ("args", "refusal"),
    [
        (("use-case", "one", "--actor", "ACT-nobody"), "no actor ACT-nobody in the analysis"),
        (("journey", "trip", "--actor", "ACT-tester", "--step", "UC-001"), "several use cases"),
        (
            ("journey", "trip", "--actor", "ACT-tester", "--step", "UC-001", "--step", "UC-009"),
            "no use case UC-009 in the analysis",
        ),
        (("actor", "Tester"), "is not a word"),
        (("use-case", "one", "--actor", "ACT-tester", "--area", "Big Area"), "is not a word"),
        (("actor", "tester"), "ACT-tester is held already"),
        (("use-case", "one", "--actor", "ACT-retired"), "actor ACT-retired is withdrawn"),
        (
            ("use-case", "two", "--actor", "ACT-tester", "--title", "<Title>"),
            "--title still holds the placeholder '<Title>'",
        ),
        (("actor", "admin", "--name", "<Display name>"), "--name still holds the placeholder"),
        (
            ("term", "sandbox", "--name", "The <Term>"),
            "--name still holds the placeholder '<Term>'",
        ),
        (
            ("actor", "sponsor", "--unanchored-because", "<why>"),
            "--unanchored-because still holds the placeholder '<why>'",
        ),
    ],
)
def test_a_stamp_refuses_what_it_cannot_ground(
    project: AdopterRepo, args: tuple[str, ...], refusal: str
) -> None:
    stamped(project, "actor", "tester")
    stamped(project, "actor", "retired")
    stamped(project, "use-case", "one", "--actor", "ACT-tester")
    text = (project.root / ACTORS).read_text(encoding="utf-8")
    marker = "ACT-retired:\n  name: Retired\n  status: active"
    (project.root / ACTORS).write_text(text.replace(marker, marker.replace("active", "withdrawn")))
    before = sorted(p.relative_to(project.root) for p in (project.root / ANALYSIS).rglob("*"))
    completed = new(project, *args)
    assert completed.returncode == 1
    assert refusal in completed.stderr
    after = sorted(p.relative_to(project.root) for p in (project.root / ANALYSIS).rglob("*"))
    assert after == before


# --- one home for discovery (ADR-057 point 2) --------------------------------------------


def test_the_capability_s_scripts_carry_no_discovery_of_their_own() -> None:
    """software-analysis reads the places, the files each matches and their
    artefacts through `pkit friction artefacts` — at head and at a commit — and
    records its location through `pkit docs record-location`; no script of it matches,
    lists or reads a place declaration, or writes a recorded location, itself."""
    scripts = sorted((CAPABILITY / "scripts").rglob("*.py"))
    assert scripts
    found = {
        path.relative_to(CAPABILITY).as_posix(): tokens
        for path in scripts
        if (tokens := _discovery_tokens(path.read_text(encoding="utf-8")))
    }
    assert found == {}
