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
import re
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
    assert stamped(project, "use-case", "three", "--actor", "ACT-tester") == "UC-003"
    steps = ("--step", "UC-001", "--step", "UC-003")
    assert stamped(project, "journey", "again", "--actor", "ACT-tester", *steps) == "JRN-002"


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
