"""software-analysis: the overview of each analysis, the reader's entry point (#1805).

Held to software-analysis DEC-003 point 8:

- **what it shows** — the concepts, each view by its number and title, the actors,
  each with the use cases it is the main actor of and those it takes part in, an
  actor of another analysis as the glossary's head names it, the requirements, the
  areas with their goals and use cases, the chain and the use-case diagram, and the
  journeys, each artefact in force linked, each diagram the query's own output;
- **front matter only** — a view's body is never read (DEC-001 point 1);
- **who writes it** — the stamp, after each artefact, and `pkit analysis
  overview`, each only where its bytes change;
- **fresh by fingerprint** — the check fails a stale overview, never one only
  printed differently, and warns of a missing one;
- **keeping none** — `overview: false` in the settings;
- **each area's goal** — data in the settings: an area without one is a warning,
  and a goal no area takes an error.
"""

from __future__ import annotations

import dataclasses
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    ANALYSIS,
    CAPABILITY,
    DOMAIN_MODEL,
    OVERVIEW_FILE,
    SA,
    SETTINGS,
    USE_CASES,
    VALIDATE,
    actor_at,
    fill,
    installed,
    load,
    load_lib,
    new,
    prepare,
    run_script,
    seed,
    stamped,
)

overview: Any
model: Any
analyses: Any
diagrams: Any
overview, model, analyses, diagrams = load_lib("overview", "model", "analyses", "diagrams")

OVERVIEW = SA / "scripts" / "overview.py"
DIAGRAM = SA / "scripts" / "diagram.py"
#: The settings file's head, with no setting: the overview kept.
HEAD = "pkit_schema: software-analysis:config\nschema_version: 1\n"


def _kept(repo: AdopterRepo) -> None:
    """`prepare`, with the settings keeping the overview, as a project's do unless it
    sets `overview: false` (DEC-003 point 8): `prepare` keeps none for other modules."""
    prepare(repo)
    repo.write({SETTINGS: HEAD})
    repo.commit("keep the overview")


# Slow: four stamps, built once per session.
def _seeded(repo: AdopterRepo) -> None:
    """`_kept`, then the seed, stamped and filled."""
    _kept(repo)
    seed(repo)


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch, then=_kept)


@pytest.fixture
def seeded(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    """The seed, stamped and filled: an actor, two use cases and a journey through them."""
    return installed(make_adopter_repo, monkeypatch, then=_seeded)


def _check(repo: AdopterRepo) -> dict[str, Any]:
    completed = run_script(repo, VALIDATE, "--json")
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def _about(document: Mapping[str, Any], severity: str, where: str) -> list[str]:
    """The messages of `severity` at a location that opens with `where`."""
    return [
        f["message"]
        for f in document["findings"]
        if f["severity"] == severity and f["location"].startswith(where)
    ]


def _read(repo: AdopterRepo, rel: str = OVERVIEW_FILE) -> str:
    return (repo.root / rel).read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    """The lines under `heading` up to the next heading of its level or above."""
    level = heading.split(" ", 1)[0]
    lines = text.split("\n")
    start = lines.index(heading) + 1
    stop = next(
        (i for i in range(start, len(lines)) if re.match(rf"^#{{1,{len(level)}}} ", lines[i])),
        len(lines),
    )
    return "\n".join(lines[start:stop]).strip("\n")


def _fence(repo: AdopterRepo, subject: str) -> str:
    """The query's own output for `subject`, as a fence."""
    completed = run_script(repo, DIAGRAM, subject)
    assert completed.returncode == 0, completed.stderr
    return completed.stdout.strip("\n")


# --- what it shows, and who writes it ----------------------------------------------------------


def test_the_stamp_writes_the_overview_and_the_check_holds_it_fresh(seeded: AdopterRepo) -> None:
    """The seed's stamps wrote the overview: each artefact linked, each diagram the query's
    own output, and its fingerprint fresh. A change of its text alone fails nothing, a
    drawn field changed by hand makes it stale, and the command writes it anew."""
    text = _read(seeded)
    assert text.startswith(
        "# Overview of the analysis\n\n<!-- pkit:overview reads=2 fingerprint=sha256:"
    )
    assert _section(text, "## Actors") == (
        "### [ACT-tester — Tester](../use-case-model/actors/ACT-tester.md)\n\n"
        "The use cases it is the main actor of:\n\n"
        "- [UC-001 — Run suite](../use-case-model/use-cases/UC-001-run-suite.md)\n"
        "- [UC-002 — Read report](../use-case-model/use-cases/UC-002-read-report.md)"
    )
    assert _section(text, "## Use cases") == (
        "- [UC-001 — Run suite](../use-case-model/use-cases/UC-001-run-suite.md)\n"
        "- [UC-002 — Read report](../use-case-model/use-cases/UC-002-read-report.md)"
    )
    assert _section(text, "## Use cases and their actors") == _fence(seeded, "use-cases")
    journey = "### [JRN-001 — First run](../use-case-model/journeys/JRN-001-first-run.md)"
    assert _section(text, journey) == _fence(seeded, "JRN-001")
    for absent in ("## Concepts", "## Requirements", "## Areas", "## Chain of use cases"):
        assert absent not in text
    assert _about(_check(seeded), "error", OVERVIEW_FILE) == []

    (seeded.root / OVERVIEW_FILE).write_text(text + "\nPrinted otherwise.\n", encoding="utf-8")
    assert _about(_check(seeded), "error", OVERVIEW_FILE) == []

    # An actor's needs are not drawn, so they leave it fresh; its name is.
    actor = actor_at("ACT-tester")
    before = _read(seeded, actor)
    seeded.write(
        {actor: re.sub(r"(?m)^needs:\n(  - .*\n)+", "needs:\n  - Run it again.\n", before)}
    )
    assert _about(_check(seeded), "error", OVERVIEW_FILE) == []
    seeded.write({actor: _read(seeded, actor).replace("Tester", "Test author")})
    (stale,) = _about(_check(seeded), "error", OVERVIEW_FILE)
    assert stale.startswith("it is stale: what it draws changed since it was written")
    assert "`pkit analysis overview`" in stale

    written = run_script(seeded, OVERVIEW)
    assert (written.returncode, written.stdout) == (0, f"wrote {OVERVIEW_FILE}\n")
    assert "[ACT-tester — Test author]" in _read(seeded)
    assert "Printed otherwise." not in _read(seeded)
    assert _about(_check(seeded), "error", OVERVIEW_FILE) == []
    again = run_script(seeded, OVERVIEW)
    assert (again.returncode, again.stdout) == (0, f"fresh already: {OVERVIEW_FILE}\n")


def test_a_missing_overview_warns_and_one_it_cannot_judge_is_said(seeded: AdopterRepo) -> None:
    """No overview is a warning naming the command and the setting; a page with no
    fingerprint fails; and where what it draws cannot be read in full, the check does
    not judge it and the command writes none."""
    text = _read(seeded)
    (seeded.root / OVERVIEW_FILE).unlink()
    document = _check(seeded)
    assert _about(document, "error", OVERVIEW_FILE) == []
    (missing,) = _about(document, "warning", OVERVIEW_FILE)
    assert missing.startswith("the analysis has no overview, the reader's entry point")
    assert "`pkit analysis overview`" in missing and "`overview: false`" in missing

    seeded.write({OVERVIEW_FILE: "# Overview, by hand\n"})
    (unmarked,) = _about(_check(seeded), "error", OVERVIEW_FILE)
    assert unmarked.startswith("it carries no fingerprint of what it draws")

    # Written by a release that read other data: a warning until it is written anew.
    older = re.sub(r"reads=[0-9]+ fingerprint=\S+", "reads=1 fingerprint=sha256:00", text)
    seeded.write({OVERVIEW_FILE: older})
    document = _check(seeded)
    assert _about(document, "error", OVERVIEW_FILE) == []
    (version,) = _about(document, "warning", OVERVIEW_FILE)
    assert version.startswith("it was written by a release that reads other data")

    seeded.write({OVERVIEW_FILE: text, f"{USE_CASES}/UC-009-broken.md": "---\nid: [\n---\n"})
    (said,) = _about(_check(seeded), "report", OVERVIEW_FILE)
    assert said.startswith("whether it is fresh is not checked")
    refused = run_script(seeded, OVERVIEW)
    assert refused.returncode == 1
    assert "the overview of the analysis is not written" in refused.stderr
    assert _read(seeded) == text


def test_keeping_none(project: AdopterRepo) -> None:
    """`overview: false`: the stamp writes none, the check asks for none and for no goal,
    the command refuses, and an overview left in place is a warning, since nothing keeps
    it fresh."""
    project.write({SETTINGS: HEAD + "overview: false\n"})
    completed = new(project, "actor", "tester", "--path", "src/**")
    assert completed.returncode == 0, completed.stderr
    assert "overview" not in completed.stdout
    assert not (project.root / OVERVIEW_FILE).exists()
    stamped(project, "use-case", "run-suite", "--actor", "ACT-tester", "--area", "010-run")
    document = _check(project)
    assert _about(document, "warning", OVERVIEW_FILE) == []
    # Nothing shows a goal, so none is asked for.
    assert _about(document, "warning", f"{USE_CASES}/010-run") == []
    refused = run_script(project, OVERVIEW)
    assert refused.returncode == 1
    assert "`overview: false`" in refused.stderr and "keeps no overview" in refused.stderr
    project.write({OVERVIEW_FILE: "# Overview of the analysis\n"})
    (left,) = _about(_check(project), "warning", OVERVIEW_FILE)
    assert "nothing keeps this one fresh" in left


# --- each area's goal -----------------------------------------------------------------------


def test_each_area_shows_its_goal_and_the_check_holds_the_goals(project: AdopterRepo) -> None:
    """The areas in the order of their numbers, each with its goal, or a line saying it
    has none, and its use cases, then those outside any area; the chain where a use case
    writes `after`. An area without a goal is a warning, a goal no area takes an error,
    and a changed goal makes the overview stale."""
    project.write(
        {
            SETTINGS: HEAD + "areas:\n  010-run: A suite runs, and its result can be read.\n"
            "  030-gone: Nothing lies here.\n"
        }
    )
    stamped(project, "actor", "tester", "--path", "src/**")
    stamped(project, "use-case", "read-report", "--actor", "ACT-tester", "--area", "020-report")
    stamped(project, "use-case", "run-suite", "--actor", "ACT-tester", "--area", "010-run")
    stamped(project, "use-case", "set-up", "--actor", "ACT-tester")
    fill(project)
    text = _read(project)
    assert _section(text, "## Areas") == (
        "### 010-run\n\nA suite runs, and its result can be read.\n\n"
        "- [UC-002 — Run suite](../use-case-model/use-cases/010-run/UC-002-run-suite.md)\n\n"
        "### 020-report\n\nNo goal is written for this area yet.\n\n"
        "- [UC-001 — Read report](../use-case-model/use-cases/020-report/UC-001-read-report.md)"
        "\n\n### Outside any area\n\n"
        "- [UC-003 — Set up](../use-case-model/use-cases/UC-003-set-up.md)"
    )
    assert "## Chain of use cases" not in text
    document = _check(project)
    (no_goal,) = _about(document, "warning", f"{USE_CASES}/020-report")
    assert no_goal.startswith("the area 020-report of the analysis has no goal")
    assert "the `areas` at the file's top" in no_goal
    (orphan,) = _about(document, "error", f"{SETTINGS}:/areas/030-gone")
    assert orphan.startswith("the goal of 030-gone names no area of the analysis")
    assert _about(document, "error", OVERVIEW_FILE) == []

    project.write({SETTINGS: HEAD + "areas:\n  010-run: Suites run.\n"})
    (stale,) = _about(_check(project), "error", OVERVIEW_FILE)
    assert stale.startswith("it is stale")
    assert run_script(project, OVERVIEW).returncode == 0
    assert "### 010-run\n\nSuites run.\n" in _read(project)


def test_several_analyses_each_keep_their_own(project: AdopterRepo) -> None:
    """Each listed analysis keeps its overview in its folder, named by its component, and
    its goals in its entry; the file's own `areas` beside a list belongs to none."""
    project.write(
        {
            SETTINGS: HEAD + "areas:\n  010-run: Belongs to none.\nanalyses:\n"
            "  - {component: core, folder: core}\n"
            "  - component: billing\n    folder: billing\n    builds-on:\n"
            "      - {analysis: core}\n    areas:\n      010-pay: Invoices are paid.\n"
        }
    )
    stamped(project, "actor", "tester", "--analysis", "core", "--path", "src/**")
    stamped(project, "actor", "clerk", "--analysis", "billing", "--path", "src/**")
    stamped(
        project,
        "use-case",
        "pay",
        "--actor",
        "ACT-clerk",
        "--analysis",
        "billing",
        "--area",
        "010-pay",
    )
    core = f"{ANALYSIS}/core/overview/README.md"
    billing = f"{ANALYSIS}/billing/overview/README.md"
    assert _read(project, core).startswith("# Overview of the analysis of core\n")
    assert "[ACT-clerk" not in _read(project, core)
    assert "### 010-pay\n\nInvoices are paid.\n" in _read(project, billing)
    document = _check(project)
    (misplaced,) = _about(document, "error", f"{SETTINGS}:/areas")
    assert "belongs to no analysis" in misplaced
    assert _about(document, "error", core) == _about(document, "error", billing) == []
    assert not (project.root / OVERVIEW_FILE).exists()


def test_each_view_is_listed_by_its_number_and_title(project: AdopterRepo) -> None:
    """The concepts: the glossary, then each view by its number, as its file's name spells
    it, and its title, in the order of its number. The overview reads no body, so writing
    a view's opening leaves it fresh."""
    for slug in ("order", "payment"):
        stamped(project, "term", slug, "--name", slug, "--path", "src/run.py")
    stamped(project, "view", "payments", "--number", "020", "--explains", "TERM-payment")
    stamped(project, "view", "orders", "--number", "010", "--explains", "TERM-order")
    assert _section(_read(project), "## Concepts") == (
        "The [glossary](../glossary.md) defines each term.\n\n"
        "Each view of the domain model explains a group of related concepts:\n\n"
        "- [010 — Orders](../domain-model/010-orders.md)\n"
        "- [020 — Payments](../domain-model/020-payments.md)"
    )
    view = f"{DOMAIN_MODEL}/010-orders.md"
    text = _read(project, view)
    hint = re.search(r"(?m)^<!-- pkit:hint The problem.*-->\n", text)
    assert hint is not None
    project.write({view: text.replace(hint.group(0), "A shop must know what each order asks.\n")})
    assert _about(_check(project), "error", OVERVIEW_FILE) == []
    again = run_script(project, OVERVIEW)
    assert (again.returncode, again.stdout) == (0, f"fresh already: {OVERVIEW_FILE}\n")


# --- each actor's use cases -------------------------------------------------------------------


def test_each_actor_lists_the_use_cases_it_is_main_actor_of_and_takes_part_in(
    project: AdopterRepo,
) -> None:
    """Under each actor, the use cases in force whose `actor` it is, then those whose
    `other-actors` name it, each linked, in the order of their numbers; an actor no use
    case names says so. A withdrawn use case is not listed, and a changed `other-actors`
    makes the overview stale."""
    for slug in ("auditor", "reviewer", "tester"):
        stamped(project, "actor", slug, "--path", "src/**")
    stamped(project, "use-case", "run-suite", "--actor", "ACT-tester")
    stamped(
        project, "use-case", "review-run", "--actor", "ACT-reviewer", "--other-actor", "ACT-tester"
    )
    stamped(project, "use-case", "read-report", "--actor", "ACT-tester")
    fill(project)
    uc = "../use-case-model/use-cases"
    assert _section(_read(project), "## Actors") == (
        "### [ACT-auditor — Auditor](../use-case-model/actors/ACT-auditor.md)\n\n"
        "No use case names it yet.\n\n"
        "### [ACT-reviewer — Reviewer](../use-case-model/actors/ACT-reviewer.md)\n\n"
        "The use cases it is the main actor of:\n\n"
        f"- [UC-002 — Review run]({uc}/UC-002-review-run.md)\n\n"
        "### [ACT-tester — Tester](../use-case-model/actors/ACT-tester.md)\n\n"
        "The use cases it is the main actor of:\n\n"
        f"- [UC-001 — Run suite]({uc}/UC-001-run-suite.md)\n"
        f"- [UC-003 — Read report]({uc}/UC-003-read-report.md)\n\n"
        "The use cases it takes part in:\n\n"
        f"- [UC-002 — Review run]({uc}/UC-002-review-run.md)"
    )
    assert _about(_check(project), "error", OVERVIEW_FILE) == []

    review = f"{USE_CASES}/UC-002-review-run.md"
    project.write(
        {review: _read(project, review).replace("  - ACT-tester\n", "  - ACT-auditor\n", 1)}
    )
    (stale,) = _about(_check(project), "error", OVERVIEW_FILE)
    assert stale.startswith("it is stale")
    read = f"{USE_CASES}/UC-003-read-report.md"
    project.write({read: _read(project, read).replace("status: active", "status: withdrawn", 1)})
    assert run_script(project, OVERVIEW).returncode == 0
    actors = _section(_read(project), "## Actors")
    assert "UC-003" not in actors
    assert (
        "### [ACT-auditor — Auditor](../use-case-model/actors/ACT-auditor.md)\n\n"
        "The use cases it takes part in:\n\n"
        f"- [UC-002 — Review run]({uc}/UC-002-review-run.md)\n"
    ) in actors + "\n"


#: The head of billing's glossary: what it takes from the core's analysis, ACT-tester among
#: it (DEC-001 point 2).
_HEAD = (
    "builds-on:\n"
    "  - analysis: core\n"
    "    version: 1.0.0\n"
    "    actors:\n"
    "      - id: ACT-tester\n"
    "        name: Tester\n"
    "        needs: [Never lose a bill.]\n"
)


def test_an_actor_of_another_analysis_is_listed_as_the_glossarys_head_names_it(
    project: AdopterRepo,
) -> None:
    """In an analysis that builds on another, each actor the glossary's head lists from
    it follows the analysis's own actors, by its id with that analysis and the name the
    head gives it, with its use cases. One a use case names that the head lists not is
    shown by that id alone. The head's names are data the overview reads, and its needs
    are not; the other analysis's overview lists none of this one's use cases."""
    project.write(
        {
            SETTINGS: HEAD + "analyses:\n  - {component: core, folder: core}\n"
            "  - component: billing\n    folder: billing\n    builds-on:\n"
            "      - {analysis: core}\n"
        }
    )
    stamped(project, "actor", "tester", "--analysis", "core", "--path", "src/**")
    stamped(project, "actor", "clerk", "--analysis", "billing", "--path", "src/**")
    stamped(project, "term", "bill", "--analysis", "billing", "--path", "src/**")
    glossary = f"{ANALYSIS}/billing/glossary.md"
    project.write({glossary: _read(project, glossary).replace("---\n", f"---\n{_HEAD}", 1)})
    audit = stamped(
        project,
        "use-case",
        "audit",
        "--analysis",
        "billing",
        "--actor",
        "core:ACT-tester",
        "--other-actor",
        "ACT-clerk",
        "--record",
        "COR-001",
    )
    assert audit == "UC-001"
    billing = f"{ANALYSIS}/billing/overview/README.md"
    link = "- [UC-001 — Audit](../use-case-model/use-cases/UC-001-audit.md)"
    assert _section(_read(project, billing), "## Actors") == (
        "### [ACT-clerk — Clerk](../use-case-model/actors/ACT-clerk.md)\n\n"
        f"The use cases it takes part in:\n\n{link}\n\n"
        "### core:ACT-tester — Tester\n\n"
        "An actor of the analysis of core, which the head of the [glossary](../glossary.md) "
        f"lists.\n\nThe use cases it is the main actor of:\n\n{link}"
    )
    core = f"{ANALYSIS}/core/overview/README.md"
    assert _section(_read(project, core), "## Actors") == (
        "### [ACT-tester — Tester](../use-case-model/actors/ACT-tester.md)\n\n"
        "No use case names it yet."
    )

    head = _read(project, glossary)
    project.write({glossary: head.replace("Never lose a bill.", "Never pay twice.")})
    assert _about(_check(project), "error", billing) == []
    project.write({glossary: head.replace("name: Tester", "name: Test author")})
    (stale,) = _about(_check(project), "error", billing)
    assert stale.startswith("it is stale")

    use_case = f"{ANALYSIS}/billing/use-case-model/use-cases/UC-001-audit.md"
    project.write(
        {use_case: _read(project, use_case).replace("  - ACT-clerk\n", "  - core:ACT-pilot\n", 1)}
    )
    assert run_script(project, OVERVIEW).returncode == 0
    actors = _section(_read(project, billing), "## Actors")
    assert (
        "### core:ACT-pilot\n\nAn actor of the analysis of core.\n\n"
        f"The use cases it takes part in:\n\n{link}\n\n### core:ACT-tester — Test author\n"
    ) in actors


# --- the fingerprint, read alone ---------------------------------------------------------------


def _artefact(kind: str, artefact_id: str, place: str, **fields: Any) -> Any:
    path = f"{ANALYSIS}/{place}/{artefact_id}.md"
    return model.Artefact(
        kind, artefact_id, path, path, False, {"id": artefact_id, "status": "active", **fields}, {}
    )


def _analysis(*artefacts: Any) -> Any:
    return model.Analysis(
        location=ANALYSIS,
        places={"use-case": f"{ANALYSIS}/use-case-model/use-cases"},
        artefacts=artefacts,
        strays=(),
        unreadable={},
        files={a.path: a.kind for a in artefacts},
        records=(),
    )


def _fingerprint(analysis: Any, goals: str = "") -> str:
    listing = analyses.Listing(areas=(("010-run", goals),) if goals else ())
    return str(overview.fingerprint(analysis, overview.read(analysis, listing, None), None))


def _headed(*artefacts: Any, name: str = "Developer", needs: str = "A") -> Any:
    """`_analysis`, its glossary's head listing core's ACT-developer as `name`."""
    glossary = f"{ANALYSIS}/glossary.md"
    taken = {"analysis": "core", "version": "1.0.0"}
    actor = {"id": "ACT-developer", "name": name, "needs": [needs]}
    return dataclasses.replace(
        _analysis(*artefacts),
        files={**{a.path: a.kind for a in artefacts}, glossary: "term"},
        glossaries={glossary: {"builds-on": [{**taken, "actors": [actor]}]}},
    )


def test_the_fingerprint_reads_what_it_draws_and_nothing_else() -> None:
    """The same data gives the same fingerprint in any order of its files; a drawn field,
    a status or a goal changes it, and a field it does not read changes nothing."""
    actor = _artefact("actor", "ACT-tester", "use-case-model/actors", name="Tester", needs=["A"])
    use_case = _artefact(
        "use-case", "UC-001", "use-case-model/use-cases/010-run", title="Run", actor="ACT-tester"
    )
    first = _fingerprint(_analysis(actor, use_case))
    assert first.startswith("sha256:") and len(first) == len("sha256:") + 64
    assert _fingerprint(_analysis(use_case, actor)) == first
    needs = _artefact("actor", "ACT-tester", "use-case-model/actors", name="Tester", needs=["B"])
    assert _fingerprint(_analysis(needs, use_case)) == first
    named = _artefact("actor", "ACT-tester", "use-case-model/actors", name="Test author")
    assert _fingerprint(_analysis(named, use_case)) != first
    gone = _artefact(
        "actor", "ACT-tester", "use-case-model/actors", name="Tester", status="withdrawn"
    )
    assert _fingerprint(_analysis(gone, use_case)) != first
    assert _fingerprint(_analysis(actor, use_case), "Runs.") != first
    # An actor of another analysis: the name the head gives it is read, its needs are not.
    headed = _fingerprint(_headed(actor, use_case))
    assert headed not in (first, _fingerprint(_headed(actor, use_case, name="Dev")))
    assert _fingerprint(_headed(actor, use_case, needs="B")) == headed
    marked = overview.mark(first)
    assert overview.written_fingerprint(f"# Overview\n\n{marked}\n") == (overview.VERSION, first)
    assert overview.written_fingerprint("# Overview\n") is None


# --- the command -----------------------------------------------------------------------------


def test_the_command_is_registered_and_its_folders_are_held() -> None:
    """`overview` writes, so it is no query; its folder is held at the location's top and
    one folder down, as the records' is (COR-050 point 1)."""
    package: dict[str, Any] = load((CAPABILITY / "package.yaml").read_text(encoding="utf-8"))
    leaf = package["commands"]["overview"]
    assert leaf["script"] == "scripts/overview.py" and "query-contract" not in leaf
    held = {entry["path"] for entry in package["friction"]["held"]}
    assert {overview.FOLDER, f"*/{overview.FOLDER}"} <= held
    result = CliRunner().invoke(main, ["analysis", "--help"])
    assert result.exit_code == 0, result.output
    assert "overview " in result.output
