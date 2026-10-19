"""software-analysis: a requirement's changed obligation revisits its anchors (#1659).

Held to software-analysis DEC-002 point 4 and COR-050 point 16. Each kind of
requirement's place declares the core's link: a change to `statement`,
`measure` or `applies-to` asks for a revisit of every anchor of the
requirement but those its `actors` and `refines` list, which are its anchors
within the analysis (point 6). Each test stands up an adopter with the
capability installed, commits a base on `main`, branches `feature` off it and
runs the core's change check against `main`, for each of the three kinds:

- **the declaration** — the capability's package declares the link on the
  three places, and validation accepts it;
- **a changed obligation** — a change to any of the three fields that changes
  none of the targets and records no reason is a finding on each target,
  which enforcing mode fails on; one that changes each target, or records
  why it still stands or which follow-up revisits it, passes;
- **what triggers nothing** — a change to `actors` or `refines` alone, or to
  a body part alone.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from project_kit import friction_check as fc
from project_kit import friction_discovery as fd
from project_kit import package_validate as pv
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import CONFIG, MAIN, REQUIREMENT_PLACES, actor_at, installed

#: The trigger fields (DEC-002 point 4).
TRIGGERS = ("statement", "measure", "applies-to")

#: What the requirement anchors outside the analysis: the test that verifies it, the
#: narrow code that holds it, and the record it rests on.
TEST_FILE = "tests/test_timing.py"
CODE = "src/run.py"
RECORD_ID = "PRJ-101"
RECORD = ".pkit/decisions/project/PRJ-101-fast-runs.md"

#: Its anchors within the analysis: its actor, and the requirement it refines.
ACTOR = "ACT-tester"
REFINED = "REQ-001"

#: The targets a triggered link asks after, in the requirement's anchors' order.
TARGETS = [f"path:{TEST_FILE}", f"path:{CODE}", f"record:{RECORD_ID}"]

ENFORCING = "docs:\n  internal: tech-docs\nfriction:\n  mode: enforcing\n"


def _actor() -> str:
    return (
        f"---\nid: {ACTOR}\nname: Tester\nstatus: active\nneeds:\n  - Know a run's result.\n"
        f"pkit:\n  friction:\n    unanchored-because: A person.\n---\n\n# {ACTOR} — Tester\n"
    )


def _record() -> str:
    return (
        f"---\nid: {RECORD_ID}\ntitle: Runs show their result fast\nstatus: accepted\n"
        "date: 2026-10-01\n---\n\n## Context\n\nWhy.\n\n## Decision\n\n"
        "Show a run's result within two seconds.\n\n## Rationale\n\nWhy this way.\n\n"
        "## Implications\n\nNone.\n"
    )


def requirement(
    kind: str,
    *,
    req_id: str = "REQ-004",
    actors: list[str] | None = None,
    refines: list[str] | None = None,
    anchors: dict[str, list[str]] | None = None,
    revisited: list[dict[str, Any]] | None = None,
    verified_by: str = "A timing test runs the suite and measures when its result shows.",
    **fields: Any,
) -> str:
    """A requirement of `kind`, filled, anchored to the test, the code and the record, and
    to its actor and the requirement it refines; its own `fields` changed as given, and
    its `revisited` list written where given."""
    _place, shown, last = REQUIREMENT_PLACES[kind]
    actors = [ACTOR] if actors is None else actors
    refines = [REFINED] if refines is None else refines
    front: dict[str, Any] = {
        "id": req_id,
        "title": "Show a run's result quickly",
        "status": "active",
        "statement": "The system shows a suite's result within two seconds of the run's end.",
        "measure": "95 of every 100 runs show their result within two seconds.",
        "applies-to": "Every run of a suite.",
        "actors": actors,
        "refines": refines,
        **fields,
    }
    block: dict[str, Any] = {
        "anchors": anchors
        if anchors is not None
        else {
            "path": [TEST_FILE, CODE],
            "record": [RECORD_ID],
            "artefact": [*actors, *refines],
        },
        "revalidated": {
            "at": "2026-10-01T09:00:00Z",
            "outcome": "unchanged",
            "unchanged-because": "The test, the code and the record say what it says.",
        },
    }
    if revisited is not None:
        block["revisited"] = revisited
    front["pkit"] = {"friction": block}
    return (
        f"---\n{json.dumps(front, indent=2)}\n---\n\n# {req_id} · {shown} · Show a run's result "
        f"quickly\n\n**Verified by:** {verified_by}\n\n**{last}:** None.\n"
    )


def refined(kind: str) -> str:
    """`REQ-001`, the requirement `REQ-004` refines, anchored to its actor only."""
    return requirement(
        kind,
        req_id=REFINED,
        refines=[],
        anchors={"artefact": [ACTOR]},
    )


def _at(kind: str, req_id: str = "REQ-004") -> str:
    place, _shown, _last = REQUIREMENT_PLACES[kind]
    slug = "fast-result" if req_id == "REQ-004" else "fast-runs"
    return f"{place}/{req_id}-{slug}.md"


def revisit(target: str, outcome: str, reason: str) -> dict[str, Any]:
    kind, value = target.split(":", 1)
    return {"anchor": {"kind": kind, "value": value}, "outcome": outcome, "reason": reason}


@pytest.fixture
def project(make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch)


def _start(project: AdopterRepo, kind: str) -> None:
    """The base on `main`, friction enforcing, and `feature` branched off it."""
    project.write(
        {
            CONFIG: ENFORCING,
            TEST_FILE: "def test_timing():\n    assert result_time() < 2\n",
            RECORD: _record(),
            actor_at(ACTOR): _actor(),
            _at(kind, REFINED): refined(kind),
            _at(kind): requirement(kind),
        }
    )
    project.commit("base", files=None)
    project.checkout("feature", create=True)


def _revisits(result: fc.ChangeCheck) -> list[tuple[str, str, str | None]]:
    """(kind, target, answer) for each finding about a target, in report order."""
    kinds = {fc.FindingKind.REVISITED, fc.FindingKind.UNREVISITED}
    return [
        (
            f.kind.value,
            "" if f.anchor is None else f"{f.anchor.kind}:{f.anchor.value}",
            None if f.answer is None else f.answer.value,
        )
        for f in result.findings
        if f.kind in kinds
    ]


# --- the declaration ---------------------------------------------------------------------


@pytest.mark.parametrize("kind", sorted(REQUIREMENT_PLACES))
def test_each_kind_declares_the_link(project: AdopterRepo, kind: str) -> None:
    project.write({actor_at(ACTOR): _actor(), RECORD: _record(), _at(kind): requirement(kind)})
    discovery = fd.discover_artefacts(project.root)
    (source,) = [a for a in discovery.artefacts if a.path == _at(kind)]
    (link,) = discovery.links(source)
    assert (link.targets, link.all_but, link.when) == (None, ("actors", "refines"), TRIGGERS)
    assert [f"{a.kind}:{a.value}" for a in fd.link_targets(source, link)] == TARGETS


def test_validation_accepts_the_declaration(project: AdopterRepo) -> None:
    package = project.root / ".pkit/capabilities/software-analysis/package.yaml"
    findings = [
        finding
        for report in pv.validate_installed_packages(project.root).reports
        if report.file == package
        for finding in report.findings
        if finding.severity is pv.Severity.ERROR
    ]
    assert findings == []


# --- a changed obligation ----------------------------------------------------------------


@pytest.mark.parametrize("field", TRIGGERS)
@pytest.mark.parametrize("kind", sorted(REQUIREMENT_PLACES))
def test_a_changed_obligation_with_no_revisit_fails(
    project: AdopterRepo, kind: str, field: str
) -> None:
    _start(project, kind)
    changed: dict[str, Any] = {field: "Within one second."}
    project.commit("tighten it", {_at(kind): requirement(kind, **changed)})
    result = fc.run_change_check(project.root, MAIN)
    assert _revisits(result) == [("unrevisited", target, None) for target in TARGETS]
    assert result.failed


@pytest.mark.parametrize("kind", sorted(REQUIREMENT_PLACES))
def test_a_changed_obligation_whose_targets_record_why_passes(
    project: AdopterRepo, kind: str
) -> None:
    _start(project, kind)
    entries = [
        revisit(f"path:{CODE}", "unchanged", "The code shows the result as it ends the run."),
        revisit(TARGETS[2], "deferred", "The record states two seconds until #9999 revisits it."),
        revisit(f"path:{TEST_FILE}", "unchanged", "The test asserts under two seconds, still."),
    ]
    project.commit(
        "tighten the measure, and say why each target stands",
        {_at(kind): requirement(kind, measure="99 of every 100 runs.", revisited=entries)},
    )
    result = fc.run_change_check(project.root, MAIN)
    assert sorted(_revisits(result)) == sorted(
        [
            ("revisited", f"path:{TEST_FILE}", "unchanged"),
            ("revisited", f"path:{CODE}", "unchanged"),
            ("revisited", TARGETS[2], "deferred"),
        ]
    )
    assert not result.failed


@pytest.mark.parametrize("kind", sorted(REQUIREMENT_PLACES))
def test_a_changed_obligation_whose_targets_change_answers_them(
    project: AdopterRepo, kind: str
) -> None:
    _start(project, kind)
    project.commit(
        "tighten the statement, and the test, the code and the record with it",
        {
            _at(kind): requirement(kind, statement="The system shows it within one second."),
            TEST_FILE: "def test_timing():\n    assert result_time() < 1\n",
            CODE: "print('run, and show the result at once')\n",
            RECORD: _record().replace("two seconds", "one second"),
        },
    )
    result = fc.run_change_check(project.root, MAIN)
    assert _revisits(result) == [("revisited", target, "updated") for target in TARGETS]


# --- what triggers nothing ---------------------------------------------------------------


@pytest.mark.parametrize("kind", sorted(REQUIREMENT_PLACES))
def test_a_change_to_actors_or_refines_alone_triggers_nothing(
    project: AdopterRepo, kind: str
) -> None:
    _start(project, kind)
    project.commit(
        "it serves no actor and refines nothing",
        {_at(kind): requirement(kind, actors=[], refines=[])},
    )
    assert _revisits(fc.run_change_check(project.root, MAIN)) == []


@pytest.mark.parametrize("kind", sorted(REQUIREMENT_PLACES))
def test_a_change_to_a_body_part_alone_triggers_nothing(project: AdopterRepo, kind: str) -> None:
    _start(project, kind)
    project.commit(
        "reword what verifies it",
        {_at(kind): requirement(kind, verified_by="A timing test measures each run's result.")},
    )
    assert _revisits(fc.run_change_check(project.root, MAIN)) == []


def test_the_shipped_places_declare_one_link_each() -> None:
    """The source repository's own package, read as the backbone reads it."""
    root = Path(__file__).resolve().parent.parent
    places = [
        place
        for place in fd.read_friction_settings(root).places
        if place.source == "capability:software-analysis" and place.revisits
    ]
    # Each kind of requirement's place, at the location's top and one folder down, one
    # analysis per component (DEC-001 point 2).
    assert sorted(place.type or "" for place in places) == [
        "software-analysis:constraint",
        "software-analysis:constraint",
        "software-analysis:functional-requirement",
        "software-analysis:functional-requirement",
        "software-analysis:quality-requirement",
        "software-analysis:quality-requirement",
    ]
