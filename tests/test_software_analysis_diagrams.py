"""software-analysis: the analysis's diagrams, drawn from its front matter (#1804).

Held to software-analysis DEC-003:

- **what it draws** (point 4) — the use-case diagram, each journey's flow and the
  requirement map, of the artefacts in force alone, from the front matter alone
  (point 3);
- **how it prints them** (point 7) — Mermaid, each diagram opening with its
  `accTitle` and `accDescr`, with no styling and the same bytes for the same
  analysis; complete, or no answer;
- **the chain** (point 5) — drawn from each use case's `after`, grouped by area,
  dotted from a later area and with implied arrows left out (#1816);
- **the query** — `pkit analysis diagram [<subject>] [--json]`, registered as a
  query, run on an adopter's analysis, writing nothing.

The fixture analysis below is built in memory, as the backbone's reading gives
it, so each diagram is compared whole, byte for byte.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    ANALYSIS,
    CAPABILITY,
    SA,
    installed,
    load,
    load_lib,
    prepare_seeded,
    run_script,
)

diagrams: Any
model: Any
met_by: Any
diagrams, model, met_by = load_lib("diagrams", "model", "met_by")

DIAGRAM = SA / "scripts" / "diagram.py"

SHOWN_AS = {
    "quality-requirement": "Quality",
    "functional-requirement": "Functional",
    "constraint": "Constraint",
}

PLACE = {
    "actor": "use-case-model/actors",
    "use-case": "use-case-model/use-cases",
    "journey": "use-case-model/journeys",
    "quality-requirement": "requirements/quality",
    "constraint": "requirements/constraints",
}


def _artefact(kind: str, artefact_id: str, **fields: Any) -> Any:
    path = f"{ANALYSIS}/{PLACE[kind]}/{artefact_id}.md"
    fields.setdefault("status", "active")
    return model.Artefact(
        kind=kind,
        id=artefact_id,
        path=path,
        location=path,
        entry=False,
        fields={"id": artefact_id, **fields},
        anchors={},
    )


#: The fixture analysis: two actors in force and one withdrawn, four use cases, one
#: withdrawn, a journey that relies on a use case outside it, and three requirements,
#: one withdrawn.
FIXTURE = (
    _artefact("actor", "ACT-tester", name="Tester"),
    _artefact("actor", "ACT-lead", name="Test lead"),
    _artefact("actor", "ACT-gone", name="Gone", status="withdrawn"),
    _artefact(
        "use-case",
        "UC-001",
        title="Run suite",
        actor="ACT-tester",
        **{"other-actors": ["ACT-lead", "ACT-gone"], "requirements": ["REQ-004", "REQ-001"]},
    ),
    _artefact(
        "use-case", "UC-002", title="Read report", actor="ACT-tester", requirements=["REQ-004"]
    ),
    _artefact("use-case", "UC-003", title="Old path", actor="ACT-tester", status="withdrawn"),
    _artefact("use-case", "UC-005", title="Set up a sandbox", actor="ACT-lead"),
    _artefact(
        "journey",
        "JRN-001",
        title="First run",
        actor="ACT-tester",
        steps=["UC-001", "UC-002"],
        requirements=["REQ-004"],
        **{"relies-on": ["UC-005"]},
    ),
    _artefact(
        "constraint", "REQ-001", title="Run suites on the client's machines", actors=["ACT-lead"]
    ),
    _artefact(
        "quality-requirement",
        "REQ-004",
        title="Show a run's result quickly",
        refines=["REQ-001", "REQ-006"],
        actors=["ACT-tester"],
    ),
    _artefact(
        "quality-requirement", "REQ-006", title="Withdrawn one", status="withdrawn", actors=[]
    ),
)


def _analysis(
    artefacts: tuple[Any, ...] = FIXTURE,
    *,
    strays: tuple[Any, ...] = (),
    unreadable: dict[str, str] | None = None,
    files: dict[str, str] | None = None,
    places: dict[str, str] | None = None,
) -> Any:
    return model.Analysis(
        location=ANALYSIS,
        places=places or {},
        artefacts=artefacts,
        strays=strays,
        unreadable=unreadable or {},
        files=files or {a.path: a.kind for a in artefacts},
        records=(),
    )


def _draw(subject: str | None = None, analysis: Any = None) -> list[Any]:
    return diagrams.diagrams(analysis or _analysis(), subject, SHOWN_AS)


def _one(subject: str) -> str:
    (found,) = _draw(subject)
    return str(found.mermaid)


# --- what it draws ----------------------------------------------------------------------------


def test_the_use_case_diagram_draws_the_boundary_and_the_actors_around_it() -> None:
    """The use cases in force inside the boundary, the actors in force around it, an
    arrow from each use case's actor and a line from each other actor. The withdrawn
    actor and use case draw nothing (DEC-003 point 4)."""
    assert _one("use-cases") == (
        "flowchart LR\n"
        "  accTitle: The use cases and their actors\n"
        "  accDescr: The system's boundary holds 3 use cases, and 2 actors stand around it. "
        "An arrow joins each use case to the actor whose goal it is, and a line joins it to "
        "each other actor who takes part.\n"
        '  ACT_lead["ACT-lead — Test lead"]\n'
        '  ACT_tester["ACT-tester — Tester"]\n'
        '  subgraph boundary["The system"]\n'
        '    UC_001(["UC-001 — Run suite"])\n'
        '    UC_002(["UC-002 — Read report"])\n'
        '    UC_005(["UC-005 — Set up a sandbox"])\n'
        "  end\n"
        "  ACT_lead --- UC_001\n"
        "  ACT_lead --> UC_005\n"
        "  ACT_tester --> UC_001\n"
        "  ACT_tester --> UC_002\n"
    )


def test_a_journeys_flow_draws_its_steps_in_order_and_what_it_relies_on_apart() -> None:
    """Its actor, then its steps in order, and the use cases it relies on in a group of
    their own with no arrow (DEC-003 point 4)."""
    assert _one("JRN-001") == (
        "flowchart LR\n"
        "  accTitle: JRN-001 — First run\n"
        "  accDescr: The flow of JRN-001: ACT-tester takes 2 steps in order, UC-001, UC-002. "
        "It relies on 1 use case outside the journey, drawn apart with no arrow.\n"
        '  ACT_tester["ACT-tester — Tester"]\n'
        '  step_1(["1. UC-001 — Run suite"])\n'
        '  step_2(["2. UC-002 — Read report"])\n'
        '  subgraph relies_on["Relied on, outside the journey"]\n'
        '    UC_005(["UC-005 — Set up a sandbox"])\n'
        "  end\n"
        "  ACT_tester --> step_1\n"
        "  step_1 --> step_2\n"
    )
    assert [d.id for d in _draw("journeys")] == ["journey-JRN-001"]


def test_a_step_not_in_force_keeps_its_place_by_its_id_alone() -> None:
    journey = _artefact(
        "journey",
        "JRN-002",
        title="Again",
        actor="ACT-tester",
        steps=["UC-001", "UC-003", "UC-001"],
    )
    (found,) = _draw("JRN-002", _analysis((*FIXTURE, journey)))
    assert found.mermaid.splitlines()[4:7] == [
        '  step_1(["1. UC-001 — Run suite"])',
        '  step_2(["2. UC-003"])',
        '  step_3(["3. UC-001 — Run suite"])',
    ]


def test_the_requirement_map_draws_what_must_meet_each_requirement() -> None:
    """Each requirement in force, what lists it, what it refines and its actors. The
    withdrawn requirement draws nothing, though REQ-004 still names it (DEC-003 point 4)."""
    assert _one("requirements") == (
        "flowchart LR\n"
        "  accTitle: The requirements and what must meet them\n"
        "  accDescr: 2 requirements in force. An arrow runs to each requirement from each use "
        "case or journey that must meet it, from each requirement to each requirement it "
        "refines, and from each requirement to each actor whose need it meets.\n"
        '  ACT_lead["ACT-lead — Test lead"]\n'
        '  ACT_tester["ACT-tester — Tester"]\n'
        '  REQ_001{{"REQ-001 · Constraint · Run suites on the client\'s machines"}}\n'
        '  REQ_004{{"REQ-004 · Quality · Show a run\'s result quickly"}}\n'
        '  UC_001(["UC-001 — Run suite"])\n'
        '  UC_002(["UC-002 — Read report"])\n'
        '  JRN_001[["JRN-001 — First run"]]\n'
        "  JRN_001 -->|must meet| REQ_004\n"
        "  REQ_001 -->|meets a need of| ACT_lead\n"
        "  REQ_004 -->|meets a need of| ACT_tester\n"
        "  REQ_004 -->|refines| REQ_001\n"
        "  UC_001 -->|must meet| REQ_001\n"
        "  UC_001 -->|must meet| REQ_004\n"
        "  UC_002 -->|must meet| REQ_004\n"
    )


def test_the_map_and_met_by_agree_on_what_meets_each_requirement() -> None:
    """The map's arrows of what must meet a requirement are `met-by`'s answer, for each
    requirement in force: one computation of it (DEC-002 point 7)."""
    (found,) = _draw("requirements")
    drawn = sorted(
        (m.group(2).replace("_", "-"), m.group(1).replace("_", "-"))
        for m in re.finditer(r"^  (\S+) -->\|must meet\| (\S+)$", found.mermaid, flags=re.M)
    )
    computed = sorted(
        (str(met.requirement.id), str(lister.id))
        for met in met_by.met_by(_analysis())
        if not met.requirement.withdrawn
        for lister in met.by
    )
    assert (
        drawn
        == computed
        == [
            ("REQ-001", "UC-001"),
            ("REQ-004", "JRN-001"),
            ("REQ-004", "UC-001"),
            ("REQ-004", "UC-002"),
        ]
    )


def test_one_requirements_map_draws_what_it_names_and_what_lists_it() -> None:
    (found,) = _draw("REQ-001")
    assert found.id == "requirement-REQ-001"
    assert found.title == "REQ-001 · Constraint · Run suites on the client's machines"
    assert found.mermaid.splitlines()[3:] == [
        '  ACT_lead["ACT-lead — Test lead"]',
        '  REQ_001{{"REQ-001 · Constraint · Run suites on the client\'s machines"}}',
        '  UC_001(["UC-001 — Run suite"])',
        "  REQ_001 -->|meets a need of| ACT_lead",
        "  UC_001 -->|must meet| REQ_001",
    ]


def test_with_no_subject_every_diagram_the_analysis_has_something_for() -> None:
    """Every diagram, in the order of point 4. Actors with no use case in force draw no
    use-case diagram, which would be the system as one box among its actors: a context
    view (DEC-003 point 4)."""
    assert [d.id for d in _draw()] == ["use-cases", "journey-JRN-001", "requirements"]
    assert _draw("chain") == []  # no use case writes `after`
    chained = _analysis(CHAIN_FIXTURE, places={"use-case": AREAS})
    assert [d.id for d in _draw(None, chained)] == ["use-cases", "chain"]
    only_actors = tuple(a for a in FIXTURE if a.kind == "actor")
    assert _draw(None, _analysis(only_actors)) == []
    assert _draw("use-cases", _analysis(only_actors)) == []
    assert _draw(None, _analysis(())) == []
    assert _draw("requirements", _analysis(only_actors)) == []


# --- the chain of use cases ------------------------------------------------------------------

#: The use cases' place, the folder whose folders are the areas.
AREAS = f"{ANALYSIS}/{PLACE['use-case']}"


def _in_area(area: str | None, use_case_id: str, title: str, **fields: Any) -> Any:
    """A use case of ACT-tester, in force unless `fields` say otherwise, in `area` of the
    use cases' place, or in none."""
    path = f"{AREAS}/{area}/{use_case_id}.md" if area else f"{AREAS}/{use_case_id}.md"
    own = {"id": use_case_id, "title": title, "status": "active", "actor": "ACT-tester"}
    return model.Artefact("use-case", use_case_id, path, path, False, {**own, **fields}, {})


#: A chain across three numbered areas, one area without a number and none: a loop of
#: two use cases, a release that follows from itself, an install in a later area beside
#: the source repository, and a withdrawn producer and one the analysis does not hold,
#: which draw nothing.
CHAIN_FIXTURE = (
    _artefact("actor", "ACT-tester", name="Tester"),
    _in_area("010-develop", "UC-001", "Develop the system"),
    _in_area("010-develop", "UC-002", "Check a change", after=[["UC-001"]]),
    _in_area(
        "020-release",
        "UC-003",
        "Cut a release",
        after=[["UC-002", "UC-001", "UC-009"], ["UC-003", "environment"]],
    ),
    _in_area("030-adopt", "UC-004", "Install", after=[["UC-003"]]),
    _in_area("020-release", "UC-005", "Upgrade", after=[["UC-001", "UC-004"]]),
    _in_area("loose", "UC-006", "Loop A", after=[["UC-007"]]),
    _in_area("loose", "UC-007", "Loop B", after=[["UC-006"], ["UC-002", "UC-008"]]),
    _in_area("loose", "UC-008", "Old", status="withdrawn"),
    _in_area(None, "UC-010", "Read the docs"),
)


def test_the_chain_draws_each_producer_grouped_by_area() -> None:
    """The use cases in force, grouped by area in the order of the areas' numbers, those
    in no area first. An arrow runs from each producer, the environment one node, dotted
    from a producer in a later area. UC-001's arrow to UC-003 is left out, implied through
    UC-002. A self arrow and a loop's arrows stay, and a withdrawn producer, or one the
    analysis does not hold, draws nothing (DEC-003 point 5)."""
    (found,) = _draw("chain", _analysis(CHAIN_FIXTURE, places={"use-case": AREAS}))
    assert found.id == "chain"
    assert found.mermaid == (
        "flowchart LR\n"
        "  accTitle: The chain of use cases\n"
        "  accDescr: The chain of 8 use cases in force, grouped by area in the order of the "
        "areas' numbers. An arrow runs from each producer a use case names in `after` to that "
        "use case, the environment among them. A dotted arrow comes from a producer in a later "
        "area, an alternative its use case's area does not build on. 1 solid arrow that other "
        "solid arrows imply is left out.\n"
        '  environment(("The environment"))\n'
        '  UC_010(["UC-010 — Read the docs"])\n'
        '  subgraph area_010_develop["010-develop"]\n'
        '    UC_001(["UC-001 — Develop the system"])\n'
        '    UC_002(["UC-002 — Check a change"])\n'
        "  end\n"
        '  subgraph area_020_release["020-release"]\n'
        '    UC_003(["UC-003 — Cut a release"])\n'
        '    UC_005(["UC-005 — Upgrade"])\n'
        "  end\n"
        '  subgraph area_030_adopt["030-adopt"]\n'
        '    UC_004(["UC-004 — Install"])\n'
        "  end\n"
        '  subgraph area_loose["loose"]\n'
        '    UC_006(["UC-006 — Loop A"])\n'
        '    UC_007(["UC-007 — Loop B"])\n'
        "  end\n"
        "  UC_001 --> UC_002\n"
        "  UC_001 --> UC_005\n"
        "  UC_002 --> UC_003\n"
        "  UC_002 --> UC_007\n"
        "  UC_003 --> UC_003\n"
        "  UC_003 --> UC_004\n"
        "  UC_004 -.-> UC_005\n"
        "  UC_006 --> UC_007\n"
        "  UC_007 --> UC_006\n"
        "  environment --> UC_003\n"
    )


def test_the_chain_is_drawn_where_a_use_case_in_force_writes_after() -> None:
    """With no `after` in force there is no chain, since a withdrawn use case's is
    history. A use case that names itself draws its arrow to itself."""
    withdrawn = _in_area("010-a", "UC-001", "Gone", status="withdrawn", after=[["UC-001"]])
    assert _draw("chain", _analysis((withdrawn,), places={"use-case": AREAS})) == []
    alone = _in_area("010-a", "UC-001", "Again", after=[["UC-001"]])
    (found,) = _draw("chain", _analysis((alone,), places={"use-case": AREAS}))
    assert found.mermaid.splitlines()[-1] == "  UC_001 --> UC_001"
    assert "No solid arrow is implied by others." in found.description


# --- how it prints them -----------------------------------------------------------------------

#: What sets a colour, a font, a theme or a class in Mermaid: styling, which no
#: diagram holds (DEC-003 point 2).
STYLING = re.compile(r"%%\{|^\s*(classDef|class|style|linkStyle)\b|:::", re.M)


def test_every_diagram_carries_its_text_alternative_and_no_styling() -> None:
    """Each opens with an `accTitle` and an `accDescr` that are not blank, holds no
    styling, and prints the same bytes for the same analysis in any order of its files
    (DEC-003 point 7)."""
    drawn = _draw()
    chained = _draw("chain", _analysis(CHAIN_FIXTURE, places={"use-case": AREAS}))
    for found in (*drawn, *chained):
        lines = found.mermaid.splitlines()
        assert lines[0] == "flowchart LR"
        assert lines[1] == f"  accTitle: {found.title}" and found.title.strip()
        assert lines[2] == f"  accDescr: {found.description}" and found.description.strip()
        assert not STYLING.search(found.mermaid), found.id
    shuffled = _analysis(tuple(reversed(FIXTURE)))
    assert [d.mermaid for d in _draw(None, shuffled)] == [d.mermaid for d in drawn]
    reversed_chain = _analysis(tuple(reversed(CHAIN_FIXTURE)), places={"use-case": AREAS})
    assert [d.mermaid for d in _draw("chain", reversed_chain)] == [d.mermaid for d in chained]


def test_a_label_shows_what_mermaid_would_read_as_markup_as_text() -> None:
    """A quote, a hash and angle brackets in a title become entities, a line break
    folds, and a comment marker breaks, so no title ends its node or its line."""
    tricky = _artefact(
        "use-case", "UC-001", title='Run "all" #1 <fast>\nnow %% here', actor="ACT-tester"
    )
    actor = _artefact("actor", "ACT-tester", name="Tester")
    (found,) = _draw("use-cases", _analysis((actor, tricky)))
    assert '    UC_001(["UC-001 — Run #quot;all#quot; #35;1 #lt;fast#gt; now % % here"])' in (
        found.mermaid.splitlines()
    )


def test_it_gives_no_answer_it_cannot_give_in_full() -> None:
    """A file it cannot read, an id of no shape, a list that is no list of ids, a subject
    that names no diagram, and a journey or a requirement not in force are no answer."""

    def refused(subject: str | None, analysis: Any, said: str) -> None:
        with pytest.raises(diagrams.NoAnswer, match=re.escape(said)):
            _draw(subject, analysis)

    broken = f"{ANALYSIS}/use-case-model/use-cases/UC-009-broken.md"
    files = {**{a.path: a.kind for a in FIXTURE}, broken: "use-case"}
    refused(None, _analysis(unreadable={broken: "bad"}, files=files), f"{broken} cannot be read")
    stray = model.Stray(kind="actor", path=f"{ANALYSIS}/x.md", why="no front matter")
    refused("use-cases", _analysis(strays=(stray,)), "x.md cannot be read")
    # A stray of a kind the diagram does not read is no matter to it.
    assert _draw("use-cases", _analysis(strays=(model.Stray("journey", "j.md", "no"),)))
    no_id = _artefact("use-case", "UC-1", title="No id", actor="ACT-tester")
    refused("use-cases", _analysis((*FIXTURE, no_id)), "gives no use case id")
    no_list = _artefact("use-case", "UC-008", actor="ACT-tester", **{"other-actors": "ACT-lead"})
    refused("use-cases", _analysis((*FIXTURE, no_list)), "gives a `other-actors` that is no list")
    refused("UC-001", _analysis(), "no diagram for 'UC-001'")
    no_lists = _artefact("use-case", "UC-008", actor="ACT-tester", after=["UC-001"])
    refused("chain", _analysis((*FIXTURE, no_lists)), "gives an `after` that is no list of lists")
    # The use-case diagram reads no `after`, so it draws all the same.
    assert _draw("use-cases", _analysis((*FIXTURE, no_lists)))
    refused("JRN-009", _analysis(), "no journey JRN-009 in the analysis")
    refused("REQ-006", _analysis(), "requirement REQ-006 is withdrawn")


# --- the query --------------------------------------------------------------------------------


@pytest.fixture
def seeded(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    """The seed: an actor, two use cases and a journey through them."""
    return installed(make_adopter_repo, monkeypatch, then=prepare_seeded)


def _tree(repo: AdopterRepo) -> dict[str, bytes]:
    return {
        p.relative_to(repo.root).as_posix(): p.read_bytes()
        for p in sorted((repo.root / ANALYSIS).rglob("*"))
        if p.is_file()
    }


def test_the_query_prints_each_diagram_in_a_fence_and_writes_nothing(seeded: AdopterRepo) -> None:
    before = _tree(seeded)
    completed = run_script(seeded, DIAGRAM)
    assert completed.returncode == 0, completed.stderr
    fences = re.findall(r"^```mermaid\n(.*?)^```$", completed.stdout, flags=re.M | re.S)
    assert [f.splitlines()[1] for f in fences] == [
        "  accTitle: The use cases and their actors",
        "  accTitle: JRN-001 — First run",
    ]
    document = json.loads(run_script(seeded, DIAGRAM, "JRN-001", "--json").stdout)
    assert document["schema_version"] == 1
    (journey,) = document["diagrams"]
    assert (journey["id"], journey["title"]) == ("journey-JRN-001", "JRN-001 — First run")
    assert journey["mermaid"] == fences[1]
    nothing = run_script(seeded, DIAGRAM, "requirements")
    assert (nothing.returncode, nothing.stdout) == (
        0,
        "The analysis holds no requirement in force.\n",
    )
    no_chain = run_script(seeded, DIAGRAM, "chain")
    assert (no_chain.returncode, no_chain.stdout) == (
        0,
        "The analysis holds no use case in force that writes `after`.\n",
    )
    assert _tree(seeded) == before


def test_the_query_is_registered_as_a_query_command() -> None:
    package: dict[str, Any] = load((CAPABILITY / "package.yaml").read_text(encoding="utf-8"))
    leaf = package["commands"]["diagram"]
    assert (leaf["script"], leaf["query-contract"]) == ("scripts/diagram.py", True)
    result = CliRunner().invoke(main, ["analysis", "--help"])
    assert result.exit_code == 0, result.output
    assert "diagram " in result.output
