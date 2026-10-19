"""A folder of held documents is bounded (COR-050 point 1; #1130).

A held folder takes its files out of every place's walk, so an unbounded one
could empty the checks and the measures with nothing reported against it. The
bounds, judged once by friction discovery (`held_folders`) and reported by the
packages pass at the declaration:

- it **names the location it lies within** and is a folder there, or a glob of
  folders at one depth (#1821; the friction pass's `malformed-held` otherwise,
  `test_friction_validate.py`);
- it **never equals or encloses a documentation root** — `.` in a location at
  a root included — **nor any declaration's place**, its own component's
  included; lying inside a place, a root's say, or sharing some of its files,
  as its own component's place glob may, is what it is for: the held folder
  wins (#1821);
- **one holder per file**: it shares no file with another component's held
  folder, and is not nested in or around another of its own; two of its own
  that share only some files hold them for it, the first declared each;
- **rules stay artefacts**: it shares no file with a rule-set folder (COR-051
  point 2).

A folder overstepping a bound holds nothing — the places matching its files
walk them as artefacts — and the error stands at its `friction.held` entry.
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from project_kit import friction_discovery as fd
from project_kit import package_validate as pv
from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

CONFIG = ".pkit/project/config.yaml"
EVIDENCE = "evidence"
DEMO = "demo-recording"


def _package(name: str) -> str:
    return f".pkit/capabilities/{name}/package.yaml"


def _declares(repo: AdopterRepo, name: str, blocks: str) -> None:
    """Append `docs` / `friction` blocks to an installed capability's package."""
    package = repo.root / _package(name)
    package.write_text(package.read_text(encoding="utf-8") + blocks, encoding="utf-8")


def _repo(make_adopter_repo: MakeAdopterRepo, config: str = "name: adopter\n") -> AdopterRepo:
    repo = make_adopter_repo(capabilities=(EVIDENCE, DEMO))
    repo.write({CONFIG: config})
    return repo


def _unbounded(root: Path) -> dict[tuple[str, str], str]:
    """The packages pass's findings on held folders: `(package, pointer) -> message`."""
    return {
        (report.file.relative_to(root).as_posix(), finding.path): finding.message
        for report in pv.validate_installed_packages(root).reports
        for finding in report.findings
        if finding.path.startswith("/friction/held/")
    }


def _detail(message: str) -> str:
    """What a finding says the folder oversteps: the clauses before the rule."""
    return message.split(", so it holds nothing")[0]


def test_held_dot_in_a_location_at_the_root_equals_the_roots_and_holds_nothing(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """`.` in a location at a root is the root itself — both roots, by default — so it
    is refused at its entry and holds nothing: the page under it stays an
    artefact of the place that walks it. Without a location, `.` is not even a
    held folder (the friction pass's `malformed-held`)."""
    repo = _repo(make_adopter_repo, "name: adopter\nfriction:\n  places: [docs]\n")
    _declares(
        repo,
        EVIDENCE,
        "docs:\n"
        "  locations:\n"
        "    whole: {path: .}\n"
        "friction:\n"
        "  held:\n"
        "    - {path: .}\n"
        "    - {location: whole, path: .}\n",
    )
    repo.write({"docs/page.md": "---\ntitle: A page\n---\n"})

    found = _unbounded(repo.root)
    message = found[(_package(EVIDENCE), "/friction/held/1")]
    assert _detail(message) == (
        "held folder '.' (at 'docs') equals or encloses the internal documentation root "
        "'docs'; equals or encloses the user documentation root 'docs'; equals or encloses "
        "the project's place 'docs'"
    )
    assert message.endswith(
        ", so it holds nothing and the places matching its files read them as artefacts: a "
        "held folder never equals or encloses a documentation root or any declaration's place, "
        "its own component's included, shares no file with another component's held folder or "
        "a rule-set folder, and is not nested with another of its own held folders (COR-050 "
        "point 1)."
    )
    assert (_package(EVIDENCE), "/friction/held/0") in found  # the shape pass: no location

    discovery = fd.discover_artefacts(repo.root)
    (folder,) = discovery.held_folders
    assert folder.skipped is not None and folder.skipped.reason == fd.SKIP_OVERLAP
    assert discovery.held == ()
    assert [a.path for a in discovery.artefacts] == ["docs/page.md"]

    cli = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert cli.exit_code == 1, cli.output
    packages = cli.output.split("\n  packages\n")[1].split("\n  friction\n")[0]
    assert f"error    {_package(EVIDENCE)}:/friction/held/1" in packages


def test_a_held_folder_enclosing_a_root_is_refused(make_adopter_repo: MakeAdopterRepo) -> None:
    """A root nested in the folder is reached whole by it: refused, though the folder
    is not the root it lies in."""
    repo = _repo(
        make_adopter_repo, "name: adopter\ndocs:\n  internal: docs\n  user: docs/guide/users\n"
    )
    _declares(
        repo,
        EVIDENCE,
        "docs:\n"
        "  locations:\n"
        "    notes: {path: .}\n"
        "friction:\n"
        "  held:\n"
        "    - {location: notes, path: guide}\n",
    )
    assert {k: _detail(v) for k, v in _unbounded(repo.root).items()} == {
        (_package(EVIDENCE), "/friction/held/0"): (
            "held folder 'guide' (at 'docs/guide') equals or encloses the user documentation "
            "root 'docs/guide/users'"
        )
    }


def test_a_held_folder_enclosing_another_component_s_place_is_refused_and_one_inside_it_is_not(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """A held folder reaching every file of another component's place would empty
    it: refused. The other way round — the held folder inside the other's place,
    as revalidation records lie under a root — is what a held folder is for: that
    place leaves its files out."""
    repo = _repo(make_adopter_repo)
    _declares(
        repo,
        DEMO,
        "docs:\n"
        "  locations:\n"
        "    demos: {path: evidence/demos}\n"
        "friction:\n"
        "  places:\n"
        "    - {location: demos, path: .}\n",
    )
    _declares(
        repo,
        EVIDENCE,
        "docs:\n"
        "  locations:\n"
        "    runs: {path: evidence}\n"
        "friction:\n"
        "  held:\n"
        "    - {location: runs, path: .}\n",
    )
    assert {k: _detail(v) for k, v in _unbounded(repo.root).items()} == {
        (_package(EVIDENCE), "/friction/held/0"): (
            "held folder '.' (at 'docs/evidence') equals or encloses demo-recording's place "
            "'docs/evidence/demos'"
        )
    }

    # The other component's place encloses the held folder: no finding, and the
    # record is held, not walked by that place.
    package = repo.root / _package(DEMO)
    package.write_text(
        package.read_text(encoding="utf-8").replace(
            "demos: {path: evidence/demos}", "demos: {path: .}"
        ),
        encoding="utf-8",
    )
    package = repo.root / _package(EVIDENCE)
    package.write_text(
        package.read_text(encoding="utf-8").replace(
            "{location: runs, path: .}", "{location: runs, path: records}"
        ),
        encoding="utf-8",
    )
    repo.write({"docs/evidence/records/run.md": "---\ndate: '2026-10-01'\n---\n"})
    assert _unbounded(repo.root) == {}
    discovery = fd.discover_artefacts(repo.root)
    (held,) = discovery.held
    assert (held.path, held.component) == ("docs/evidence/records/run.md", EVIDENCE)
    assert [(p.source, p.pattern) for p in held.places] == [("capability:demo-recording", "docs/.")]
    assert discovery.artefacts == ()


def test_a_held_folder_wins_over_its_own_place_and_one_it_would_empty_is_refused(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """A component's own place that only shares files with its held folder — a glob
    reaching into it — leaves them to the folder: no finding, and the record is
    held, with that place among those that left it out (#1821). A place of its own
    the folder equals or encloses would be emptied: refused, as another
    declaration's place is, and the folder holds nothing."""
    repo = _repo(make_adopter_repo)
    _declares(
        repo,
        EVIDENCE,
        "docs:\n"
        "  locations:\n"
        "    runs: {path: evidence}\n"
        "friction:\n"
        "  places:\n"
        "    - {location: runs, path: '**/*.md'}\n"
        "    - {location: runs, path: 'pages/*.md'}\n"
        "  held:\n"
        "    - {location: runs, path: records}\n",
    )
    repo.write(
        {
            "docs/evidence/records/run.md": "---\ndate: '2026-10-01'\n---\n",
            "docs/evidence/pages/page.md": "---\ntitle: A page\n---\n",
        }
    )
    assert _unbounded(repo.root) == {}
    discovery = fd.discover_artefacts(repo.root)
    (held,) = discovery.held
    assert (held.path, held.component) == ("docs/evidence/records/run.md", EVIDENCE)
    assert [p.pattern for p in held.places] == ["docs/evidence/**/*.md"]
    assert [a.path for a in discovery.artefacts] == ["docs/evidence/pages/page.md"]

    package = repo.root / _package(EVIDENCE)
    package.write_text(
        package.read_text(encoding="utf-8").replace(
            "    - {location: runs, path: 'pages/*.md'}\n",
            "    - {location: runs, path: 'pages/*.md'}\n    - {location: runs, path: records}\n",
        ),
        encoding="utf-8",
    )
    assert {k: _detail(v) for k, v in _unbounded(repo.root).items()} == {
        (_package(EVIDENCE), "/friction/held/0"): (
            "held folder 'records' (at 'docs/evidence/records') equals or encloses its own "
            "place 'docs/evidence/records'"
        )
    }
    discovery = fd.discover_artefacts(repo.root)
    assert discovery.held == ()
    assert "docs/evidence/records/run.md" in [a.path for a in discovery.artefacts]


def test_two_held_folders_sharing_files_are_refused_at_both(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """One holder per file: two components' held folders that share a file are
    both refused, and hold nothing — the file goes back to the place walking it,
    rather than to whichever component sorts first."""
    repo = _repo(make_adopter_repo, "name: adopter\nfriction:\n  places: [docs]\n")
    _declares(
        repo,
        EVIDENCE,
        "docs:\n"
        "  locations:\n"
        "    runs: {path: evidence}\n"
        "friction:\n"
        "  held:\n"
        "    - {location: runs, path: records}\n",
    )
    _declares(
        repo,
        DEMO,
        "docs:\n"
        "  locations:\n"
        "    old: {path: evidence/records/old}\n"
        "friction:\n"
        "  held:\n"
        "    - {location: old, path: .}\n",
    )
    repo.write({"docs/evidence/records/old/run.md": "---\ndate: '2026-10-01'\n---\n"})
    assert {k: _detail(v) for k, v in _unbounded(repo.root).items()} == {
        (_package(DEMO), "/friction/held/0"): (
            "held folder '.' (at 'docs/evidence/records/old') overlaps evidence's held folder "
            "'docs/evidence/records'"
        ),
        (_package(EVIDENCE), "/friction/held/0"): (
            "held folder 'records' (at 'docs/evidence/records') overlaps demo-recording's held "
            "folder 'docs/evidence/records/old'"
        ),
    }
    discovery = fd.discover_artefacts(repo.root)
    assert discovery.held == ()
    assert [a.path for a in discovery.artefacts] == ["docs/evidence/records/old/run.md"]


def test_one_component_s_two_held_folders_sharing_files_are_refused_at_both(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """No held folder is emptied, even within one component: a folder nested in
    another of the same component's is refused, and so is the enclosing one."""
    repo = _repo(make_adopter_repo)
    _declares(
        repo,
        EVIDENCE,
        "docs:\n"
        "  locations:\n"
        "    runs: {path: evidence}\n"
        "friction:\n"
        "  held:\n"
        "    - {location: runs, path: records}\n"
        "    - {location: runs, path: records/old}\n",
    )
    assert {k: _detail(v) for k, v in _unbounded(repo.root).items()} == {
        (_package(EVIDENCE), "/friction/held/0"): (
            "held folder 'records' (at 'docs/evidence/records') overlaps its own held folder "
            "'docs/evidence/records/old'"
        ),
        (_package(EVIDENCE), "/friction/held/1"): (
            "held folder 'records/old' (at 'docs/evidence/records/old') overlaps its own held "
            "folder 'docs/evidence/records'"
        ),
    }


def test_a_held_folder_sharing_files_with_a_rule_set_folder_is_refused_and_rules_stay(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """The location rule reads every file of a rule-set folder as rules (COR-051
    point 2): a held folder there is refused, and the file stays a rule set."""
    repo = _repo(make_adopter_repo)
    _declares(
        repo,
        EVIDENCE,
        "docs:\n"
        "  locations:\n"
        "    sets: {path: rule-sets}\n"
        "friction:\n"
        "  held:\n"
        "    - {location: sets, path: drafts}\n",
    )
    rules = "docs/rule-sets/drafts/runs.md"
    repo.write(
        {
            rules: (
                "---\nrule-set: RUNS\nrules:\n  RS-RUNS-001:\n    status: accepted\n"
                "    pkit:\n      friction:\n        anchors: {path: [src/**]}\n---\n\n"
                "## RS-RUNS-001 — A rule\n\nA statement.\n"
            )
        }
    )
    assert {k: _detail(v) for k, v in _unbounded(repo.root).items()} == {
        (_package(EVIDENCE), "/friction/held/0"): (
            "held folder 'drafts' (at 'docs/rule-sets/drafts') overlaps the rule-set folder "
            "'docs/rule-sets', whose files are rules (COR-051 point 2)"
        )
    }
    discovery = fd.discover_artefacts(repo.root)
    assert discovery.held == ()
    (read,) = [f for f in discovery.files if f.path == rules]
    assert read.rule_set is not None
    assert [a.location for a in discovery.artefacts] == [f"{rules}#RS-RUNS-001"]


# --- a glob of folders (#1821) ---------------------------------------------------------

#: One analysis per component beside the root's (software-analysis DEC-001 point 2):
#: a glossary and a folder of records at the location's top and in each component's
#: folder, and a place of the component's own reaching into both folders of records.
ANALYSIS = (
    "docs:\n"
    "  locations:\n"
    "    analysis: {path: analysis}\n"
    "friction:\n"
    "  places:\n"
    "    - {location: analysis, path: glossary.md}\n"
    "    - {location: analysis, path: '*/glossary.md'}\n"
    "    - {location: analysis, path: '**/*.md'}\n"
    "  held:\n"
    "    - {location: analysis, path: revalidations}\n"
    "    - {location: analysis, path: '*/revalidations'}\n"
)


def test_a_glob_held_folder_holds_each_component_s_records_and_wins_over_its_own_places(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """A held folder may be a glob of folders, `*/revalidations`, and holds every
    Markdown file beneath each folder it names. Its own component's place that
    reaches into it — `**/*.md` here — leaves those files to it, as the project's
    place does, so no bound is overstepped. Its two folders share a file only at
    `revalidations/revalidations/`, and neither lies within the other: the first
    declared holds that file for the component."""
    repo = _repo(make_adopter_repo, "name: adopter\nfriction:\n  places: [docs]\n")
    _declares(repo, EVIDENCE, ANALYSIS)
    record = "---\ndate: '2026-10-01'\n---\n"
    repo.write(
        {
            "docs/analysis/glossary.md": "---\ntitle: Glossary\n---\n",
            "docs/analysis/billing/glossary.md": "---\ntitle: Billing glossary\n---\n",
            "docs/analysis/revalidations/r1.md": record,
            "docs/analysis/billing/revalidations/r2.md": record,
            "docs/analysis/revalidations/revalidations/r3.md": record,
        }
    )

    assert _unbounded(repo.root) == {}
    discovery = fd.discover_artefacts(repo.root)
    assert [(h.path, h.folder.declaration.pointer) for h in discovery.held] == [
        ("docs/analysis/billing/revalidations/r2.md", "/friction/held/1"),
        ("docs/analysis/revalidations/r1.md", "/friction/held/0"),
        ("docs/analysis/revalidations/revalidations/r3.md", "/friction/held/0"),
    ]
    assert {h.component for h in discovery.held} == {EVIDENCE}
    assert [p.pattern for p in discovery.held[0].places] == ["docs", "docs/analysis/**/*.md"]
    assert [a.path for a in discovery.artefacts] == [
        "docs/analysis/billing/glossary.md",
        "docs/analysis/glossary.md",
    ]

    cli = CliRunner().invoke(main, ["friction", "artefacts", "--json"])
    assert cli.exit_code == 0, cli.output
    document = json.loads(cli.output)
    assert [(h["written"], h["path"], h["files"], h["skipped"]) for h in document["held"]] == [
        (
            "revalidations",
            "docs/analysis/revalidations",
            [
                "docs/analysis/revalidations/r1.md",
                "docs/analysis/revalidations/revalidations/r3.md",
            ],
            None,
        ),
        (
            "*/revalidations",
            "docs/analysis/*/revalidations",
            ["docs/analysis/billing/revalidations/r2.md"],
            None,
        ),
    ]


def test_a_glob_held_folder_never_empties_a_place_its_own_component_s_included(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """A glob held folder is bounded as a folder is: a place every file of which lies
    beneath a folder it names — another component's, or its own — would be emptied,
    so it is refused and holds nothing, and its files stay artefacts."""
    repo = _repo(make_adopter_repo)
    _declares(
        repo,
        DEMO,
        "docs:\n"
        "  locations:\n"
        "    demos: {path: analysis/billing/revalidations/demos}\n"
        "friction:\n"
        "  places:\n"
        "    - {location: demos, path: .}\n",
    )
    _declares(
        repo,
        EVIDENCE,
        ANALYSIS.replace(
            "    - {location: analysis, path: '**/*.md'}\n",
            "    - {location: analysis, path: '*/revalidations/*.md'}\n",
        ),
    )
    assert {k: _detail(v) for k, v in _unbounded(repo.root).items()} == {
        (_package(EVIDENCE), "/friction/held/1"): (
            "held folder '*/revalidations' (at 'docs/analysis/*/revalidations') equals or "
            "encloses demo-recording's place 'docs/analysis/billing/revalidations/demos'; "
            "equals or encloses its own place 'docs/analysis/*/revalidations/*.md'"
        )
    }
    repo.write({"docs/analysis/billing/revalidations/r2.md": "---\ndate: '2026-10-01'\n---\n"})
    discovery = fd.discover_artefacts(repo.root)
    assert discovery.held == ()
    assert [a.path for a in discovery.artefacts] == ["docs/analysis/billing/revalidations/r2.md"]


def test_a_glob_held_folder_shares_no_file_with_another_component_s_or_a_rule_set_folder(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """One component holds each held file, and rules stay artefacts, whichever of
    two folders is a glob: a glob that could name a folder beneath another
    component's held folder, or beneath a rule-set folder, is refused, and so is
    the other component's folder."""
    repo = _repo(make_adopter_repo)
    _declares(
        repo,
        EVIDENCE,
        "docs:\n"
        "  locations:\n"
        "    whole: {path: .}\n"
        "friction:\n"
        "  held:\n"
        "    - {location: whole, path: '*/drafts'}\n",
    )
    _declares(
        repo,
        DEMO,
        "docs:\n"
        "  locations:\n"
        "    notes: {path: notes}\n"
        "friction:\n"
        "  held:\n"
        "    - {location: notes, path: drafts}\n",
    )
    rules = "docs/rule-sets/drafts/runs.md"
    repo.write(
        {
            rules: (
                "---\nrule-set: RUNS\nrules:\n  RS-RUNS-001:\n    status: accepted\n"
                "    pkit:\n      friction:\n        anchors: {path: [src/**]}\n---\n\n"
                "## RS-RUNS-001 — A rule\n\nA statement.\n"
            )
        }
    )
    assert {k: _detail(v) for k, v in _unbounded(repo.root).items()} == {
        (_package(EVIDENCE), "/friction/held/0"): (
            "held folder '*/drafts' (at 'docs/*/drafts') overlaps the rule-set folder "
            "'docs/rule-sets', whose files are rules (COR-051 point 2); overlaps "
            "demo-recording's held folder 'docs/notes/drafts'"
        ),
        (_package(DEMO), "/friction/held/0"): (
            "held folder 'drafts' (at 'docs/notes/drafts') overlaps evidence's held folder "
            "'docs/*/drafts'"
        ),
    }
    discovery = fd.discover_artefacts(repo.root)
    assert discovery.held == ()
    assert [a.location for a in discovery.artefacts] == [f"{rules}#RS-RUNS-001"]
