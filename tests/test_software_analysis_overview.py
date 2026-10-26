"""software-analysis: the overview of each analysis, the reader's entry point (#1805, #1887).

Held to software-analysis DEC-003 point 8:

- **what it shows** — for a newcomer first, in two parts. The story: the opening, with
  what the component is for from its purpose record and what the analysis is, then
  the areas, each with its goal, what it builds on, its concepts read from the links to
  the terms, its requirements and its use cases, or "Not written yet", or the use cases
  where there are no areas. Then reference: one
  table of who takes part, an actor of another analysis as the glossary's head names
  it; the concepts, each view by its number and title; the requirements in no area; the
  journeys, each with its flow; what is not built yet; then the line that names the query
  of the diagrams, on every page. Each artefact in force is linked, and each journey's
  flow is the query's own output. No other diagram is on the page;
- **its purpose** — `purpose` names an accepted record, whose title it shows; a pointer
  to no record, or to one not accepted, fails the check and is said on the page;
- **front matter, and the links to the terms** — a view's body is never read, and of a
  use case's or a requirement's body only its links to the terms (DEC-001 point 1);
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
    QUALITY,
    SA,
    SETTINGS,
    USE_CASES,
    VALIDATE,
    actor_at,
    fill,
    installed,
    link,
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
    """The lines under `heading` up to the next heading of its level or above, or the
    break above the page's closing line."""
    level = heading.split(" ", 1)[0]
    lines = text.split("\n")
    start = lines.index(heading) + 1
    stop = next(
        (
            i
            for i in range(start, len(lines))
            if re.match(rf"^#{{1,{len(level)}}} ", lines[i]) or lines[i] == "---"
        ),
        len(lines),
    )
    return "\n".join(lines[start:stop]).strip("\n")


def _opening(text: str) -> str:
    """The page's opening: below its fingerprint's line, up to its first section."""
    lines = text.split("\n")
    start = next(i for i, line in enumerate(lines) if line.startswith("<!-- pkit:overview")) + 1
    stop = next(i for i in range(start, len(lines)) if lines[i].startswith("## "))
    return "\n".join(lines[start:stop]).strip("\n")


#: Who the seed's actor is, its summary and the first sentence of its opening, as `fill`
#: writes the hints' example (DEC-001 point 1).
WHO = "Someone who builds reports from their team's figures."


def _headings(text: str) -> list[str]:
    """The page's headings, in their order."""
    return re.findall(r"(?m)^#{1,6} .*$", text)


def _fence(repo: AdopterRepo, subject: str) -> str:
    """The query's own output for `subject`, as a fence."""
    completed = run_script(repo, DIAGRAM, subject)
    assert completed.returncode == 0, completed.stderr
    return completed.stdout.strip("\n")


def _shows_no_other_diagram(repo: AdopterRepo, text: str, *drawn: str) -> None:
    """The page holds no Mermaid fence but a journey's flow. The query draws each diagram
    of `drawn`, such as the use-case diagram, the requirement map or the chain of use
    cases, and the page shows none of them."""
    printed = run_script(repo, DIAGRAM, "--json")
    assert printed.returncode == 0, printed.stderr
    others = {d["id"]: d for d in json.loads(printed.stdout)["diagrams"]}
    assert set(drawn) <= set(others), sorted(others)
    for diagram in drawn:
        assert f"accTitle: {others[diagram]['title']}" not in text
    fences = re.findall(r"(?ms)^```mermaid\n(.*?)^```$", text)
    assert all(re.search(r"(?m)^  accTitle: JRN-", f) for f in fences), fences
    for heading in ("### Requirement map", "### Chain of use cases", "### Use cases and their"):
        assert heading not in text


def _ends_reference(text: str, command: str = "pkit analysis diagram") -> None:
    """Reference ends with its section on the diagrams: one line that names the query, as
    it is run for the analysis, and its subjects."""
    assert _section(text, "### Diagrams") == (
        f"`{command}` prints this analysis's diagrams from the working tree. Its subjects are "
        "`use-cases`, `journeys`, `requirements` and `chain`, or a journey's or a requirement's "
        "id."
    )
    assert _headings(text)[-1] == "### Diagrams"


# --- what it shows, and who writes it ----------------------------------------------------------


def test_the_stamp_writes_the_overview_and_the_check_holds_it_fresh(seeded: AdopterRepo) -> None:
    """The seed's stamps wrote the overview: each artefact linked, a journey's flow the
    query's own output, the other diagrams left to the query, and its fingerprint fresh.
    A change of its text alone fails nothing, a drawn field changed by hand makes it
    stale, and the command writes it anew."""
    text = _read(seeded)
    assert text.startswith(
        "# Overview of the analysis\n\n<!-- pkit:overview reads=5 fingerprint=sha256:"
    )
    assert _section(text, "### Who takes part") == (
        "| Actor | Who they are | Areas they act in |\n| --- | --- | --- |\n"
        f"| [ACT-tester — Tester](../use-case-model/actors/ACT-tester.md) | {WHO} | "
        "[the use cases](#use-cases) |"
    )
    assert _section(text, "## Use cases") == (
        "- [UC-001 — Run suite](../use-case-model/use-cases/UC-001-run-suite.md)\n"
        "- [UC-002 — Read report](../use-case-model/use-cases/UC-002-read-report.md)"
    )
    journey = "#### [JRN-001 — First run](../use-case-model/journeys/JRN-001-first-run.md)"
    assert _section(text, journey) == _fence(seeded, "JRN-001")
    _shows_no_other_diagram(seeded, text, "use-cases")
    _ends_reference(text)
    for absent in ("### Concepts", "Requirement", "## Areas"):
        assert absent not in text
    assert text.endswith(
        "\n\n---\n\nThe command `pkit analysis overview` writes this page from the "
        "analysis. Change the analysis, never this page (software-analysis DEC-003 point 8).\n"
    )
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


# --- its two parts: the story, then reference --------------------------------------------------


def _links_resolve(text: str) -> None:
    """Each link inside the page leads to one of its headings, as a repository host makes
    their anchors."""
    anchors = {overview._anchor(h.lstrip("#").strip()) for h in _headings(text)}
    targets = set(re.findall(r"\]\(#([^)]+)\)", text))
    assert targets and targets <= anchors, targets - anchors


def test_an_analysis_with_areas_reads_as_its_story_then_reference(project: AdopterRepo) -> None:
    """The story: the opening, then the areas. Then reference, under a heading of its own:
    who takes part, the concepts, the requirements in no area, the journeys, what is not
    built yet, then the line that names the query of the diagrams, each a section below
    it. No line says where to start, no diagram but a journey's flow is on the page, and
    each link inside the page leads to a heading."""
    project.write({SETTINGS: HEAD + "areas:\n  010-run: Run the suites.\n"})
    stamped(project, "term", "suite", "--name", "suite", "--path", "src/run.py")
    stamped(project, "view", "runs", "--number", "010", "--explains", "TERM-suite")
    stamped(project, "actor", "tester", "--path", "src/**")
    stamped(project, "use-case", "run-suite", "--actor", "ACT-tester", "--area", "010-run")
    stamped(project, "use-case", "read-report", "--actor", "ACT-tester", "--area", "010-run")
    stamped(project, "constraint", "local", "--actor", "ACT-tester")
    steps = ("--step", "UC-001", "--step", "UC-002")
    stamped(project, "journey", "first-run", "--actor", "ACT-tester", *steps)
    fill(project)
    _after(project, f"{USE_CASES}/010-run/UC-002-read-report.md", "[UC-001]")
    run = f"{USE_CASES}/010-run/UC-001-run-suite.md"
    shortfall = "shortfalls:\n  - {at: 2, issue: '#12', record: PRJ-001}\n"
    project.write(
        {run: _read(project, run).replace("status: active\n", f"status: active\n{shortfall}", 1)}
    )
    assert run_script(project, OVERVIEW).returncode == 0
    text = _read(project)
    assert _headings(text) == [
        "# Overview of the analysis",
        "## Areas",
        "### 010-run",
        "## Reference",
        "### Who takes part",
        "### Concepts",
        "### Requirements in no area",
        "### Journeys",
        "#### [JRN-001 — First run](../use-case-model/journeys/JRN-001-first-run.md)",
        "### Not built yet",
        "### Diagrams",
    ]
    assert "Start with" not in text
    _shows_no_other_diagram(project, text, "use-cases", "requirements", "chain")
    _ends_reference(text)
    _links_resolve(text)


def test_an_analysis_without_areas_reads_as_its_use_cases_then_reference(
    seeded: AdopterRepo,
) -> None:
    """Where no use case lies in an area, the use cases tell the story after the opening,
    and reference follows them."""
    text = _read(seeded)
    assert _headings(text) == [
        "# Overview of the analysis",
        "## Use cases",
        "## Reference",
        "### Who takes part",
        "### Journeys",
        "#### [JRN-001 — First run](../use-case-model/journeys/JRN-001-first-run.md)",
        "### Diagrams",
    ]
    assert "Start with" not in text
    _links_resolve(text)


def test_reference_ends_with_the_query_of_the_diagrams_on_every_page(
    project: AdopterRepo,
) -> None:
    """Where the analysis holds no part of reference, such as one requirement in an area,
    reference holds the line that names the query alone, under its heading."""
    stamped(project, "constraint", "local", "--area", "010-run", "--path", "src/**")
    text = _read(project)
    assert _headings(text) == [
        "# Overview of the analysis",
        "## Areas",
        "### 010-run",
        "## Reference",
        "### Diagrams",
    ]
    _ends_reference(text)
    assert "```mermaid" not in text


# --- the opening, and what the component is for ------------------------------------------------

#: A project record that states what the component is for, as the purpose names it.
PURPOSE_REL = ".pkit/decisions/project/PRJ-001-what-the-runner-is-for.md"
PURPOSE_TITLE = "The runner exists so a team's suites run the same way on every machine"


def _record(status: str = "accepted", title: str = PURPOSE_TITLE) -> str:
    return (
        f"---\nid: PRJ-001\ntitle: {title}\nstatus: {status}\ndate: 2026-10-22\n"
        "author: A Person <person@example.com>\n---\n\n## Context\n\nA team's suites ran "
        "differently on each machine.\n\n## Decision\n\n**The runner exists for it.**\n\n"
        "## Rationale\n\nNone.\n\n## Implications\n\nNone.\n"
    )


def test_the_opening_shows_what_the_component_is_for_and_what_the_analysis_is(
    project: AdopterRepo,
) -> None:
    """Without a purpose, the opening says no record states what the system is for, and
    names the command and the setting; nothing fails. With one, it shows the accepted
    record's title as a sentence, linked, then what the analysis is, and nothing
    more: the story goes on with the areas. The record's title is drawn, so a changed one
    makes the overview stale."""
    project.write({SETTINGS: HEAD + "areas:\n  010-run: Run the suites.\n"})
    stamped(project, "term", "suite", "--name", "suite", "--path", "src/run.py")
    stamped(project, "actor", "tester", "--path", "src/**")
    stamped(project, "use-case", "run-suite", "--actor", "ACT-tester", "--area", "010-run")
    fill(project)
    what_it_is = (
        "This analysis describes what the system does: who uses it, what they do with it, "
        "and what it must meet. It builds on no other analysis."
    )
    assert _opening(_read(project)) == (
        "No record states what the system is for yet. Write one with `pkit new decision`, "
        "and name it as `purpose` at the top of "
        f"`{SETTINGS}`.\n\n{what_it_is}"
    )
    assert _about(_check(project), "error", SETTINGS) == []

    project.write(
        {
            SETTINGS: HEAD + "purpose: PRJ-001\nareas:\n  010-run: Run the suites.\n",
            PURPOSE_REL: _record(),
        }
    )
    (stale,) = _about(_check(project), "error", OVERVIEW_FILE)
    assert stale.startswith("it is stale")
    assert run_script(project, OVERVIEW).returncode == 0
    assert _opening(_read(project)) == f"[{PURPOSE_TITLE}](../../../{PURPOSE_REL}).\n\n{what_it_is}"
    document = _check(project)
    assert _about(document, "error", SETTINGS) == _about(document, "error", OVERVIEW_FILE) == []

    project.write({PURPOSE_REL: _record(title="The runner is for teams.")})
    (stale,) = _about(_check(project), "error", OVERVIEW_FILE)
    assert stale.startswith("it is stale")
    assert run_script(project, OVERVIEW).returncode == 0
    assert _opening(_read(project)).startswith(
        f"[The runner is for teams.](../../../{PURPOSE_REL})\n"
    )


def test_a_purpose_naming_no_accepted_record_fails_and_the_page_says_so(
    project: AdopterRepo,
) -> None:
    """A purpose that names a record not accepted, or no record, fails the check, whatever
    the setting `overview`. The page shows no title of such a record: it says what is
    wrong, and the rest of it is written as usual."""
    project.write(
        {
            SETTINGS: HEAD + "purpose: PRJ-001\n",
            PURPOSE_REL: _record(status="proposed"),
        }
    )
    stamped(project, "actor", "tester", "--path", "src/**")
    fill(project)
    (proposed,) = _about(_check(project), "error", f"{SETTINGS}:/purpose")
    assert proposed.startswith("PRJ-001 is proposed, not accepted: only an accepted record")
    assert _opening(_read(project)).startswith(
        "`PRJ-001` is named as the record of what the system is for, and it is proposed, not "
        "accepted. Only an accepted record states it (software-analysis DEC-003 point 8).\n"
    )
    assert PURPOSE_TITLE not in _read(project)
    assert "### Who takes part" in _read(project)
    assert _about(_check(project), "error", OVERVIEW_FILE) == []

    project.write({SETTINGS: HEAD + "purpose: PRJ-009\noverview: false\n"})
    (missing,) = _about(_check(project), "error", f"{SETTINGS}:/purpose")
    assert missing.startswith("`PRJ-009` names no record the repository holds")
    project.write({SETTINGS: HEAD + "purpose: PRJ-009\n"})
    assert run_script(project, OVERVIEW).returncode == 0
    assert _opening(_read(project)).startswith(
        "`PRJ-009` is named as the record of what the system is for, and the repository holds "
        "no record of that id."
    )


# --- the areas ---------------------------------------------------------------------------------


def test_each_area_shows_its_goal_and_the_check_holds_the_goals(project: AdopterRepo) -> None:
    """The areas in the order of their numbers, each with its goal, or a line saying it
    has none, its requirements and its use cases, then those outside any area. An area
    whose goal is given and that holds no use case reads "Not written yet.", and fails
    nothing. An area of use cases without a goal is a warning, and a changed goal makes
    the overview stale."""
    project.write(
        {
            SETTINGS: HEAD + "areas:\n  010-run: Run a suite, and read its result.\n"
            "  030-share: Share a failure's cause.\n"
        }
    )
    stamped(project, "actor", "tester", "--path", "src/**")
    stamped(project, "use-case", "read-report", "--actor", "ACT-tester", "--area", "020-report")
    stamped(project, "use-case", "run-suite", "--actor", "ACT-tester", "--area", "010-run")
    stamped(project, "use-case", "set-up", "--actor", "ACT-tester")
    fill(project)
    uc = "../use-case-model/use-cases"
    text = _read(project)
    assert _section(text, "## Areas") == (
        "### 010-run\n\nRun a suite, and read its result.\n\n"
        "**Its requirements:** none.\n\n**Its use cases:**\n\n"
        f"- [UC-002 — Run suite]({uc}/010-run/UC-002-run-suite.md)\n\n"
        "### 020-report\n\nNo goal is written for this area yet.\n\n"
        "**Its requirements:** none.\n\n**Its use cases:**\n\n"
        f"- [UC-001 — Read report]({uc}/020-report/UC-001-read-report.md)\n\n"
        "### 030-share\n\nShare a failure's cause.\n\nNot written yet.\n\n"
        f"### Outside any area\n\n- [UC-003 — Set up]({uc}/UC-003-set-up.md)"
    )
    assert "Builds on" not in text
    document = _check(project)
    (no_goal,) = _about(document, "warning", f"{USE_CASES}/020-report")
    assert no_goal.startswith("the area 020-report of the analysis has no goal")
    assert "the `areas` at the file's top" in no_goal
    assert _about(document, "error", SETTINGS) == []
    assert _about(document, "error", OVERVIEW_FILE) == []

    project.write({SETTINGS: HEAD + "areas:\n  010-run: Run the suites.\n"})
    (stale,) = _about(_check(project), "error", OVERVIEW_FILE)
    assert stale.startswith("it is stale")
    assert run_script(project, OVERVIEW).returncode == 0
    assert "### 010-run\n\nRun the suites.\n" in _read(project)
    assert "030-share" not in _read(project)


#: The trigger and the check of a requirement as `fill` writes them, the shipped examples.
TRIGGER = "**Trigger:** The analyst asks to export the report on screen."
VERIFIED = (
    "**Verified by:** A timing test opens a report of a year's figures, and fails if it takes "
    "over two seconds to show."
)


def test_each_area_shows_its_concepts_from_the_links_to_the_terms(project: AdopterRepo) -> None:
    """Where the analysis holds a view in force, each area shows its concepts: each view
    that explains a term one of its use cases links, in the order of the views' numbers, or
    none. A requirement's links lead its area nowhere. They are read from the links `pkit
    analysis link` writes, so a link that leads an area to another view makes the overview
    stale, and a reworded sentence that moves no link leaves it fresh (DEC-003 point 8,
    DEC-005 point 3). The use cases in no area show none."""
    project.write(
        {SETTINGS: HEAD + "areas:\n  010-run: Run the suites.\n  020-read: Read the results.\n"}
    )
    for slug in ("suite", "result"):
        stamped(project, "term", slug, "--name", slug, "--path", "src/run.py")
    stamped(project, "view", "results", "--number", "020", "--explains", "TERM-result")
    stamped(project, "view", "suites", "--number", "010", "--explains", "TERM-suite")
    stamped(project, "actor", "tester", "--path", "src/**")
    stamped(project, "use-case", "run", "--actor", "ACT-tester", "--area", "010-run")
    stamped(project, "use-case", "read", "--actor", "ACT-tester", "--area", "020-read")
    stamped(project, "use-case", "share", "--actor", "ACT-tester", "--area", "030-share")
    stamped(project, "use-case", "set-up", "--actor", "ACT-tester")
    stamped(project, "quality-requirement", "quick", "--area", "010-run", "--actor", "ACT-tester")
    fill(project)
    run = f"{USE_CASES}/010-run/UC-001-run.md"
    read = f"{USE_CASES}/020-read/UC-002-read.md"
    quick = f"{QUALITY}/010-run/REQ-001-quick.md"
    set_up = f"{USE_CASES}/UC-004-set-up.md"
    project.write(
        {
            run: _read(project, run).replace(TRIGGER, "**Trigger:** The tester starts a suite."),
            read: _read(project, read).replace(TRIGGER, "**Trigger:** The tester reads a result."),
            quick: _read(project, quick).replace(VERIFIED, "**Verified by:** A result shows."),
            set_up: _read(project, set_up).replace(TRIGGER, "**Trigger:** A suite is set up."),
        }
    )
    link(project)
    assert run_script(project, OVERVIEW).returncode == 0
    views = {"010": "- [010 — Suites](../domain-model/010-suites.md)"}
    views["020"] = "- [020 — Results](../domain-model/020-results.md)"
    text = _read(project)
    assert _section(text, "### 010-run").startswith(
        f"Run the suites.\n\n**Its concepts:**\n\n{views['010']}\n\n**Its requirements:**\n\n"
    )
    assert f"Read the results.\n\n**Its concepts:**\n\n{views['020']}\n\n" in text
    assert (
        "### 030-share\n\nNo goal is written for this area yet.\n\n**Its concepts:** none.\n"
        in (text)
    )
    assert "Its concepts" not in _section(text, "### Outside any area")
    assert _about(_check(project), "error", OVERVIEW_FILE) == []

    # A reworded sentence moves no link; a mention linked leads the area to another view.
    reworded = _read(project, read).replace("tester reads a", "tester reads the")
    project.write({read: reworded})
    link(project)
    assert _about(_check(project), "error", OVERVIEW_FILE) == []
    project.write({read: _read(project, read).replace("result).", "result) of a suite.")})
    link(project)
    (stale,) = _about(_check(project), "error", OVERVIEW_FILE)
    assert stale.startswith("it is stale")
    assert run_script(project, OVERVIEW).returncode == 0
    assert f"Read the results.\n\n**Its concepts:**\n\n{views['010']}\n{views['020']}\n\n" in _read(
        project
    )


def _after(repo: AdopterRepo, rel: str, *entries: str) -> None:
    """Write `after` into a stamped use case's front matter, one entry for each of
    `entries`, as written: `[UC-001]` or `[UC-002, environment]`."""
    text = _read(repo, rel)
    after = "after:\n" + "".join(f"  - {entry}\n" for entry in entries)
    repo.write({rel: text.replace("status: active\n", f"status: active\n{after}", 1)})


def test_an_area_builds_on_the_areas_its_use_cases_producers_lie_in(project: AdopterRepo) -> None:
    """What an area builds on is computed from its use cases' `after`: each other area that
    holds a producer in force, in the order of their numbers. A producer of its own area,
    one in a later area and the environment are no area it builds on. An area none of
    whose use cases writes `after` shows no line, and a changed `after` makes the overview
    stale."""
    stamped(project, "actor", "tester", "--path", "src/**")
    for slug, area in (("run", "010-run"), ("read", "020-read"), ("share", "030-share")):
        stamped(project, "use-case", slug, "--actor", "ACT-tester", "--area", area)
    stamped(project, "use-case", "keep", "--actor", "ACT-tester", "--area", "040-keep")
    stamped(project, "use-case", "reread", "--actor", "ACT-tester", "--area", "020-read")
    fill(project)
    _after(project, f"{USE_CASES}/020-read/UC-002-read.md", "[UC-001]")
    _after(project, f"{USE_CASES}/020-read/UC-005-reread.md", "[UC-002, environment]")
    _after(project, f"{USE_CASES}/030-share/UC-003-share.md", "[UC-005, UC-004]", "[UC-001]")
    assert run_script(project, OVERVIEW).returncode == 0
    areas = _section(_read(project), "## Areas")
    builds = re.findall(r"(?m)^### (\S+)$|^\*\*Builds on:\*\* (.*)$", areas)
    assert [(a or b) for a, b in builds] == [
        "010-run",
        "020-read",
        "[010-run](#010-run).",
        "030-share",
        "[010-run](#010-run) and [020-read](#020-read).",
        "040-keep",
    ]
    _after(project, f"{USE_CASES}/040-keep/UC-004-keep.md", "[UC-004]")
    (stale,) = _about(_check(project), "error", OVERVIEW_FILE)
    assert stale.startswith("it is stale")
    assert run_script(project, OVERVIEW).returncode == 0
    assert (
        "### 040-keep\n\nNo goal is written for this area yet.\n\n**Builds on:** no other area."
        in (_read(project))
    )


def test_an_area_s_requirements_are_read_from_their_folder(project: AdopterRepo) -> None:
    """A requirement whose file lies in an area's folder of its kind's folder is that
    area's, an area that holds only requirements is shown, not written yet, and the
    requirements in no area's folder are listed apart."""
    stamped(project, "actor", "tester", "--path", "src/**")
    stamped(project, "use-case", "run", "--actor", "ACT-tester", "--area", "010-run")
    for slug, area in (("quick", "010-run"), ("kept", "060-audit")):
        stamped(project, "quality-requirement", slug, "--area", area, "--actor", "ACT-tester")
    stamped(project, "constraint", "local", "--actor", "ACT-tester")
    fill(project)
    assert run_script(project, OVERVIEW).returncode == 0
    text = _read(project)
    req = "../requirements"
    assert _section(text, "### 010-run") == (
        "No goal is written for this area yet.\n\n**Its requirements:**\n\n"
        f"- [REQ-001 · Quality · Quick]({req}/quality/010-run/REQ-001-quick.md)\n\n"
        "**Its use cases:**\n\n"
        "- [UC-001 — Run](../use-case-model/use-cases/010-run/UC-001-run.md)"
    )
    assert _section(text, "### 060-audit") == (
        "No goal is written for this area yet.\n\n**Its requirements:**\n\n"
        f"- [REQ-002 · Quality · Kept]({req}/quality/060-audit/REQ-002-kept.md)\n\n"
        "Not written yet."
    )
    assert _section(text, "### Requirements in no area") == (
        f"- [REQ-003 · Constraint · Local]({req}/constraints/REQ-003-local.md)"
    )
    (no_goal,) = _about(_check(project), "warning", f"{QUALITY}/060-audit")
    assert no_goal.startswith("the area 060-audit of the analysis has no goal")


# --- who takes part ---------------------------------------------------------------------------


def test_one_table_shows_who_takes_part_and_the_areas_each_acts_in(
    project: AdopterRepo,
) -> None:
    """One row for each actor in force: the actor, linked, its summary, and the areas of
    the use cases in force it is the main actor of or takes part in, in the order of their
    numbers. An actor that gives no summary has an empty cell, and one no use case names
    says so. A withdrawn use case is not read, and a changed `other-actors` or summary
    makes the overview stale."""
    for slug in ("auditor", "reviewer", "tester"):
        stamped(project, "actor", slug, "--path", "src/**")
    stamped(project, "use-case", "run-suite", "--actor", "ACT-tester", "--area", "020-run")
    stamped(
        project,
        "use-case",
        "review-run",
        "--actor",
        "ACT-reviewer",
        "--other-actor",
        "ACT-tester",
        "--area",
        "010-review",
    )
    stamped(project, "use-case", "read-report", "--actor", "ACT-tester")
    fill(project)
    auditor = actor_at("ACT-auditor")
    project.write({auditor: re.sub(r"(?m)^summary: .*\n", "", _read(project, auditor), count=1)})
    assert run_script(project, OVERVIEW).returncode == 0
    actors = "../use-case-model/actors"
    assert _section(_read(project), "### Who takes part") == (
        "| Actor | Who they are | Areas they act in |\n| --- | --- | --- |\n"
        f"| [ACT-auditor — Auditor]({actors}/ACT-auditor.md) |  | No use case names it yet. |\n"
        f"| [ACT-reviewer — Reviewer]({actors}/ACT-reviewer.md) | {WHO} | "
        "[010-review](#010-review) |\n"
        f"| [ACT-tester — Tester]({actors}/ACT-tester.md) | {WHO} | [010-review](#010-review), "
        "[020-run](#020-run), [outside any area](#outside-any-area) |"
    )
    assert "## Actors" not in _read(project)
    assert _about(_check(project), "error", OVERVIEW_FILE) == []

    review = f"{USE_CASES}/010-review/UC-002-review-run.md"
    project.write(
        {review: _read(project, review).replace("  - ACT-tester\n", "  - ACT-auditor\n", 1)}
    )
    (stale,) = _about(_check(project), "error", OVERVIEW_FILE)
    assert stale.startswith("it is stale")
    read = f"{USE_CASES}/UC-003-read-report.md"
    project.write({read: _read(project, read).replace("status: active", "status: withdrawn", 1)})
    tester = actor_at("ACT-tester")
    project.write(
        {
            tester: re.sub(
                r"(?m)^summary: .*$", "summary: A tester.", _read(project, tester), count=1
            )
        }
    )
    assert run_script(project, OVERVIEW).returncode == 0
    rows = _section(_read(project), "### Who takes part").split("\n")
    assert rows[2].endswith("|  | [010-review](#010-review) |")
    assert (
        rows[4]
        == f"| [ACT-tester — Tester]({actors}/ACT-tester.md) | A tester. | [020-run](#020-run) |"
    )


def test_several_analyses_each_keep_their_own(project: AdopterRepo) -> None:
    """Each listed analysis keeps its overview in its folder, named by its component, and
    its goals and its purpose in its entry; the file's own `areas` and `purpose` beside a
    list belong to none. The opening says what each analysis builds on."""
    project.write(
        {
            SETTINGS: HEAD + "areas:\n  010-run: Belongs to none.\npurpose: PRJ-001\nanalyses:\n"
            "  - {component: core, folder: core}\n"
            "  - component: billing\n    folder: billing\n    builds-on:\n"
            "      - {analysis: core}\n    purpose: ledger:DEC-001\n    areas:\n"
            "      010-pay: Pay the invoices.\n"
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
    assert "### 010-pay\n\nPay the invoices.\n" in _read(project, billing)
    assert _opening(_read(project, core)) == (
        "No record states what core is for yet. Write one with `pkit new decision`, and "
        f"name it as `purpose` in the entry of core under `analyses` in `{SETTINGS}`.\n\n"
        "This analysis describes what core does: who uses it, what they do with it, and "
        "what it must meet. It builds on no other analysis."
    )
    assert (
        "This analysis describes what billing does: who uses it, what they do with it, and "
        "what it must meet. It builds on the analysis of core.\n"
    ) in _read(project, billing)
    document = _check(project)
    (misplaced,) = _about(document, "error", f"{SETTINGS}:/areas")
    assert "belongs to no analysis" in misplaced
    (also,) = _about(document, "error", f"{SETTINGS}:/purpose")
    assert "belongs to no analysis" in also
    (other,) = _about(document, "error", f"{SETTINGS}:/analyses/1/purpose")
    assert other.startswith(
        "ledger:DEC-001 is a decision of ledger, and the component of the analysis of billing "
        "is billing"
    )
    assert _about(document, "error", core) == _about(document, "error", billing) == []
    assert not (project.root / OVERVIEW_FILE).exists()
    # The line names the query as it is run for each analysis, and it runs.
    for component, page in (("core", core), ("billing", billing)):
        _ends_reference(_read(project, page), f"pkit analysis diagram --analysis {component}")
        drawn = run_script(project, DIAGRAM, "--analysis", component)
        assert drawn.returncode == 0, drawn.stderr


def test_each_view_is_listed_by_its_number_and_title(project: AdopterRepo) -> None:
    """The concepts: the glossary, then each view by its number, as its file's name spells
    it, and its title, in the order of its number. The overview reads no body, so writing
    a view's opening leaves it fresh."""
    for slug in ("order", "payment"):
        stamped(project, "term", slug, "--name", slug, "--path", "src/run.py")
    stamped(project, "view", "payments", "--number", "020", "--explains", "TERM-payment")
    stamped(project, "view", "orders", "--number", "010", "--explains", "TERM-order")
    assert _section(_read(project), "### Concepts") == (
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
    it follows the analysis's own actors in the table, by its id with that analysis and
    the name the head gives it, with the areas it acts in. One a use case names that the
    head lists not is shown by that id alone. The head's names are data the overview
    reads, and its needs are not; the other analysis's overview reads none of this one's
    use cases."""
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
    fill(project)
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
    listed = "which the head of the [glossary](../glossary.md) lists."
    assert _section(_read(project, billing), "### Who takes part").split("\n")[2:] == [
        f"| [ACT-clerk — Clerk](../use-case-model/actors/ACT-clerk.md) | {WHO} | "
        "[the use cases](#use-cases) |",
        f"| core:ACT-tester — Tester | An actor of the analysis of core, {listed} | "
        "[the use cases](#use-cases) |",
    ]
    core = f"{ANALYSIS}/core/overview/README.md"
    assert _section(_read(project, core), "### Who takes part").split("\n")[2:] == [
        f"| [ACT-tester — Tester](../use-case-model/actors/ACT-tester.md) | {WHO} | "
        "No use case names it yet. |"
    ]

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
    rows = _section(_read(project, billing), "### Who takes part").split("\n")[2:]
    assert rows[1:] == [
        "| core:ACT-pilot | An actor of the analysis of core. | [the use cases](#use-cases) |",
        f"| core:ACT-tester — Test author | An actor of the analysis of core, {listed} | "
        "[the use cases](#use-cases) |",
    ]


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
    # What only the query's diagrams draw is not read: a use case's `requirements`, and a
    # requirement's `refines` and `actors`.
    listing = _artefact(
        "use-case",
        "UC-001",
        "use-case-model/use-cases/010-run",
        title="Run",
        actor="ACT-tester",
        requirements=["REQ-001"],
    )
    assert _fingerprint(_analysis(actor, listing)) == first
    bare = _artefact("constraint", "REQ-001", "requirements/constraints", title="Local")
    tied = _artefact(
        "constraint",
        "REQ-001",
        "requirements/constraints",
        title="Local",
        refines=["REQ-002"],
        actors=["ACT-tester"],
    )
    assert _fingerprint(_analysis(actor, use_case, bare)) == _fingerprint(
        _analysis(actor, use_case, tied)
    )
    # An actor of another analysis: the name the head gives it is read, its needs are not.
    headed = _fingerprint(_headed(actor, use_case))
    assert headed not in (first, _fingerprint(_headed(actor, use_case, name="Dev")))
    assert _fingerprint(_headed(actor, use_case, needs="B")) == headed
    # The views each use case leads to, through the links to the terms, are read.
    analysis = _analysis(actor, use_case)
    read_ = overview.read(analysis, analyses.Listing(), None)
    led = dataclasses.replace(read_, concepts={"UC-001": ("VIEW-orders",)})
    assert overview.fingerprint(analysis, led, None) != overview.fingerprint(analysis, read_, None)
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
