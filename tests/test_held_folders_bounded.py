"""A folder of held documents is bounded (COR-050 point 1; #1130).

A held folder takes its files out of every place's walk, so an unbounded one
could empty the checks and the measures with nothing reported against it. The
bounds, judged once by friction discovery (`held_folders`) and reported by the
packages pass at the declaration:

- it **names the location it lies within** and is a folder there (the friction
  pass's `malformed-held` otherwise, `test_friction_validate.py`);
- it **never equals or encloses a documentation root** — `.` in a location at
  a root included — **nor another declaration's place**; lying inside
  another's place, a root's say, is what it is for;
- **one holder per file**: it shares no file with another held folder — two
  components', or its own two — nor with its own component's place;
- **rules stay artefacts**: it shares no file with a rule-set folder (COR-051
  point 2).

A folder overstepping a bound holds nothing — the places matching its files
walk them as artefacts — and the error stands at its `friction.held` entry.
"""

from __future__ import annotations

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
        "held folder never equals or encloses a documentation root or another declaration's "
        "place, and shares no file with its own component's place, another held folder or a "
        "rule-set folder (COR-050 point 1)."
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


def test_a_held_folder_sharing_files_with_its_own_place_is_refused(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """A component's own place and held folder never share a file — equal, one
    inside the other, or a glob reaching into the folder — while a glob that
    cannot match beneath the folder is no overlap."""
    repo = _repo(make_adopter_repo)
    _declares(
        repo,
        EVIDENCE,
        "docs:\n"
        "  locations:\n"
        "    runs: {path: evidence}\n"
        "friction:\n"
        "  places:\n"
        "    - {location: runs, path: records}\n"
        "    - {location: runs, path: '**/*.md'}\n"
        "    - {location: runs, path: 'pages/*.md'}\n"
        "  held:\n"
        "    - {location: runs, path: records}\n",
    )
    assert {k: _detail(v) for k, v in _unbounded(repo.root).items()} == {
        (_package(EVIDENCE), "/friction/held/0"): (
            "held folder 'records' (at 'docs/evidence/records') overlaps its own place "
            "'docs/evidence/records'; overlaps its own place 'docs/evidence/**/*.md'"
        )
    }


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
