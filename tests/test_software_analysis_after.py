"""software-analysis: what makes each precondition true, and its chain (#1816).

A use case's optional `after` held to software-analysis DEC-001 points 1, 2 and 12,
and RS-SAN-009 with its declared check:

- **the field** — its schema reads `after`, one list of producers per precondition,
  each a use case's id or `environment`, never `environment` alone, and holds that
  shape whatever any rule's status;
- **the check** — each producer resolves to a use case in force of its own analysis,
  the field and the words of *Preconditions* agree, and in a numbered area each
  precondition has a producer in no later area. It binds where RS-SAN-009 binds and
  at its status: proposed as shipped, so it reports nothing unless a preview asks;
- **the areas** — the stamp takes a numbered area, such as `010-develop`, whose
  number is no part of the id (RS-ANA-003);
- **the words** — a precondition's opening, `**From UC-003:**`, is no label a
  closed list of labels reports.

The chain diagram, drawn from `after`, is `test_software_analysis_diagrams.py`'s.
"""

from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path
from typing import Any

import pytest

from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    ANALYSIS,
    ANALYSIS_SET,
    ANALYSIS_SET_TEXT,
    SA,
    SAN_REL,
    USE_CASES,
    VALIDATE,
    fill,
    installed,
    load_lib,
    new,
    prepare,
    run_script,
    stamped,
    with_status,
)

chain: Any
check: Any
forms: Any
model: Any
structure: Any
chain, check, forms, model, structure = load_lib("chain", "check", "forms", "model", "structure")

DIAGRAM = SA / "scripts" / "diagram.py"

#: The fixture's use cases, each in its area: two in the first, one in each later one.
DEVELOP = f"{USE_CASES}/010-develop/UC-001-develop.md"
CHANGE = f"{USE_CASES}/010-develop/UC-002-check-a-change.md"
RELEASE = f"{USE_CASES}/020-release/UC-003-release.md"
INSTALL = f"{USE_CASES}/030-adopt/UC-004-install.md"


def _chain(repo: AdopterRepo) -> None:
    """`prepare`, then an actor and four use cases in three numbered areas, stamped and
    filled, none writing `after` yet."""
    prepare(repo)
    stamped(repo, "actor", "developer", "--path", "src/**")
    for slug, area in (
        ("develop", "010-develop"),
        ("check-a-change", "010-develop"),
        ("release", "020-release"),
        ("install", "030-adopt"),
    ):
        stamped(repo, "use-case", slug, "--actor", "ACT-developer", "--area", area)
    fill(repo)


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch, then=_chain)


_PRECONDITIONS = re.compile(r"(\*\*Preconditions:\*\*).*?(?=\n\*\*Assumptions:\*\*)", re.DOTALL)


def _write(repo: AdopterRepo, rel: str, after: Any, lines: list[str] | None) -> None:
    """A use case's `after` written as given — left out when `None` — and its
    *Preconditions* as one item for each of `lines`, or `None.` when there are none."""
    text = (repo.root / rel).read_text(encoding="utf-8")
    text = re.sub(r"\nafter: .*\n", "\n", text)
    if after is not None:
        text = text.replace("\npkit:\n", f"\nafter: {json.dumps(after)}\npkit:\n", 1)
    written = "\n".join(f"- {line}" for line in lines) if lines else "None."
    text, count = _PRECONDITIONS.subn(lambda m: f"{m.group(1)}\n\n{written}\n", text)
    assert count == 1, text
    repo.write({rel: text})


def _accepted(repo: AdopterRepo) -> None:
    """RS-SAN-009 accepted in the adopter's copy of `SAN`, a fixture and not the
    acceptance, and a set of the project's own through which `SAN` binds."""
    text = (repo.root / SAN_REL).read_text(encoding="utf-8")
    repo.write({SAN_REL: with_status(text, "RS-SAN-009", "accepted")})
    repo.write({ANALYSIS_SET: ANALYSIS_SET_TEXT})


def _validate(repo: AdopterRepo, *args: str) -> dict[str, Any]:
    completed = run_script(repo, VALIDATE, "--json", *args)
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def _of_after(document: dict[str, Any]) -> list[tuple[str, str, str]]:
    """The findings at a use case's `after`, or citing RS-SAN-009: severity, location and
    message."""
    return [
        (f["severity"], f["location"], f["message"])
        for f in document["findings"]
        if ":/after" in f["location"] or "RS-SAN-009" in f["message"]
    ]


def _summary(document: dict[str, Any]) -> list[str]:
    return [line for line in document["summary"] if line.startswith("after")]


# --- the field ------------------------------------------------------------------------------


def test_a_use_case_that_writes_no_after_fails_nothing(project: AdopterRepo) -> None:
    """`after` is optional: a use case without it is not read, and with none written the
    summary says nothing of it, previewed or not, accepted or not."""
    _accepted(project)
    for args in ((), ("--preview",)):
        document = _validate(project, *args)
        assert _of_after(document) == []
        assert _summary(document) == []


def test_the_schema_holds_after_s_shape_whatever_the_rule_s_status(project: AdopterRepo) -> None:
    """One list of producers per precondition, each a use case's id or `environment`, and
    never `environment` alone: the schema's, so an error with RS-SAN-009 proposed."""
    for after in ([["environment"]], [], [["UC-1"]], "UC-001", [[]]):
        _write(project, RELEASE, after, ["**From UC-002:** a change is checked."])
        document = _validate(project)
        located = [f for f in document["findings"] if f["location"].startswith(f"{RELEASE}:/after")]
        assert located and {f["severity"] for f in located} == {"error"}, after
    _write(project, RELEASE, [["UC-002", "environment"]], ["**From UC-002, or Environment:** x."])
    assert _of_after(_validate(project)) == []


# --- the check, at RS-SAN-009's status --------------------------------------------------------


def test_proposed_the_check_reports_only_in_a_preview(project: AdopterRepo) -> None:
    """As `SAN` ships it, RS-SAN-009 is proposed: the normal check reports nothing of
    `after` and says so, and a preview, where the rule would bind, reports each departure
    with `preview:`, never failing (DEC-001 point 1; COR-051 point 4)."""
    _write(project, CHANGE, [["UC-009"]], ["**From UC-009:** the system is developed."])
    document = _validate(project)
    assert _of_after(document) == []
    assert _summary(document) == [
        "after (RS-SAN-009, proposed): not checked — the rule binds nothing until it is "
        "accepted (COR-051 point 4); `pkit analysis validate --preview` shows what it would "
        "report."
    ]
    # No set of the project's own inherits `SAN`, so the rule would bind on nothing.
    previewed = _validate(project, "--preview")
    assert _of_after(previewed) == []
    assert _summary(previewed) == [
        "after (RS-SAN-009, proposed, previewed as accepted): nothing checked. The rule would "
        "not bind on 1 of the 1 use case(s) that write `after`, so they are not checked."
    ]
    project.write({ANALYSIS_SET: ANALYSIS_SET_TEXT})
    previewed = _validate(project, "--preview")
    assert _of_after(previewed) == [
        (
            "report",
            f"{CHANGE}:/after/0/0",
            "preview: no use case UC-009 in the analysis: each producer is a use case in force "
            "of its own analysis, the use case itself among them, or `environment` (RS-SAN-009)",
        )
    ]
    assert _summary(previewed) == [
        "after (RS-SAN-009, proposed, previewed as accepted): 1 use case(s) that write `after` "
        "checked, where the rule would bind, as `pkit rule-sets reach --preview` reads it; 1 of "
        "them departing from it, reported and never failing."
    ]


def test_accepted_a_chain_that_keeps_the_rule_passes(project: AdopterRepo) -> None:
    """Producers in their own area or an earlier one, the use case itself, the environment
    beside a producer, and a later producer beside an earlier one, each with words that
    name the same producers (DEC-001 points 1 and 12)."""
    _accepted(project)
    _write(project, CHANGE, [["UC-001"]], ["**From UC-001:** the system is developed."])
    _write(
        project,
        RELEASE,
        [["UC-002", "UC-004"], ["UC-003", "environment"]],
        [
            "**From UC-002 or UC-004:** the project holds the system.",
            "**From UC-003, or Environment:** the last release, or the first version (ADR-059).",
        ],
    )
    _write(project, INSTALL, [["UC-003"]], ["**From UC-003:** a release is published."])
    document = _validate(project)
    assert _of_after(document) == []
    assert _summary(document) == [
        "after (RS-SAN-009, accepted): 3 use case(s) that write `after` checked, where the rule "
        "binds; 0 of them departing from it."
    ]


def test_accepted_each_producer_is_a_use_case_in_force_of_its_analysis(
    project: AdopterRepo,
) -> None:
    _accepted(project)
    text = (project.root / DEVELOP).read_text(encoding="utf-8")
    project.write({DEVELOP: text.replace("status: active", "status: withdrawn", 1)})
    _write(
        project,
        RELEASE,
        [["UC-002", "UC-009"], ["UC-001", "environment"]],
        ["**From UC-002 or UC-009:** a change is checked.", "**From UC-001, or Environment:** x."],
    )
    found = [(loc, msg) for sev, loc, msg in _of_after(_validate(project)) if sev == "error"]
    assert found == [
        (
            f"{RELEASE}:/after/0/1",
            "no use case UC-009 in the analysis: each producer is a use case in force of its own "
            "analysis, the use case itself among them, or `environment` (RS-SAN-009)",
        ),
        (
            f"{RELEASE}:/after/1/0",
            f"use case UC-001 is withdrawn ({DEVELOP}): each producer is a use case in force of "
            f"its own analysis, the use case itself among them, or `environment` (RS-SAN-009)",
        ),
    ]


def test_accepted_after_names_the_producers_the_words_name(project: AdopterRepo) -> None:
    """One entry for each precondition, in order, each naming what its line opens with;
    a line that opens with no producers, and `None.` beside an `after`, break it."""
    _accepted(project)
    _write(
        project,
        RELEASE,
        [["UC-002"], ["UC-001", "environment"]],
        [
            "**From UC-001:** a change is checked.",
            "The last release, or the first version.",
        ],
    )
    _write(project, INSTALL, [["UC-003"]], ["**From UC-003:** one.", "**From UC-003:** two."])
    _write(project, CHANGE, [["UC-001"]], None)
    found = [(loc, msg) for sev, loc, msg in _of_after(_validate(project)) if sev == "error"]
    assert found == [
        (
            f"{CHANGE}",
            "`after` lists 1 precondition, and `**Preconditions:**` holds no precondition, and "
            "a use case with none writes no `after`: `after` holds one entry for each "
            "precondition the words write, in their order (RS-SAN-009)",
        ),
        (
            f"{RELEASE}:/after/0",
            "precondition 1 of `**Preconditions:**`, at line 24, names UC-001, and entry 0 of "
            "`after` names UC-002: `after` names the producers the words name (RS-SAN-009)",
        ),
        (
            f"{RELEASE}:/after/1",
            "precondition 2 of `**Preconditions:**`, at line 25, opens with no producers, such "
            "as `**From UC-003:**`, though `after` lists them: each line of the part opens "
            "with its producers (RS-SAN-009)",
        ),
        (
            f"{INSTALL}",
            "`after` lists 1 precondition, and `**Preconditions:**` holds 2 preconditions: "
            "`after` holds one entry for each precondition the words write, in their order "
            "(RS-SAN-009)",
        ),
    ]


def test_accepted_each_precondition_has_a_producer_in_no_later_area(
    project: AdopterRepo,
) -> None:
    """A precondition whose producers all lie in later areas breaks the rule. A later one
    beside an earlier one, or beside the environment, is an alternative (DEC-001 point
    12)."""
    _accepted(project)
    _write(
        project,
        CHANGE,
        [["UC-003", "UC-004"], ["UC-004", "environment"]],
        ["**From UC-003 or UC-004:** one.", "**From UC-004, or Environment:** two."],
    )
    found = [(loc, msg) for sev, loc, msg in _of_after(_validate(project)) if sev == "error"]
    assert found == [
        (
            f"{CHANGE}:/after/0",
            "each producer of precondition 1 lies in a later area than 010-develop: UC-003 in "
            "020-release, UC-004 in 030-adopt. At least one producer of each precondition lies "
            "in its own area or a lower-numbered one, the environment before every area: name "
            "one there, or move a use case to another area (RS-SAN-009; DEC-001 point 12)",
        )
    ]


def test_the_chain_query_draws_the_analysis_s_after(project: AdopterRepo) -> None:
    """`pkit analysis diagram chain` draws the use cases by area, the areas in their
    numbers' order, an arrow from each producer, dotted from a later area. The arrows
    from UC-001 and from the environment to UC-003 are implied through UC-002, and left
    out (DEC-003 point 5)."""
    _write(project, CHANGE, [["UC-001"]], ["**From UC-001:** the system is developed."])
    _write(
        project,
        RELEASE,
        [["UC-002", "UC-001"], ["UC-003", "environment"]],
        ["**From UC-002 or UC-001:** one.", "**From UC-003, or Environment:** two."],
    )
    _write(project, INSTALL, [["UC-003"]], ["**From UC-003:** a release is published."])
    _write(project, DEVELOP, [["UC-004", "environment"]], ["**From UC-004, or Environment:** x."])
    completed = run_script(project, DIAGRAM, "chain")
    assert completed.returncode == 0, completed.stderr
    lines = completed.stdout.splitlines()
    assert lines[0] == "```mermaid" and lines[-1] == "```"
    assert lines[2] == "  accTitle: The chain of use cases"
    assert lines[4:] == [
        '  environment(("The environment"))',
        '  subgraph area_010_develop["010-develop"]',
        '    UC_001(["UC-001 — Develop"])',
        '    UC_002(["UC-002 — Check a change"])',
        "  end",
        '  subgraph area_020_release["020-release"]',
        '    UC_003(["UC-003 — Release"])',
        "  end",
        '  subgraph area_030_adopt["030-adopt"]',
        '    UC_004(["UC-004 — Install"])',
        "  end",
        "  UC_001 --> UC_002",
        "  UC_002 --> UC_003",
        "  UC_003 --> UC_003",
        "  UC_003 --> UC_004",
        "  UC_004 -.-> UC_001",
        "  environment --> UC_001",
        "```",
    ]


# --- the areas ------------------------------------------------------------------------------


def test_the_stamp_takes_a_numbered_area_whose_number_is_no_part_of_the_id(
    project: AdopterRepo,
) -> None:
    """The fixture stamped each use case into `010-develop` and the like, numbering them
    one numbering whatever their area (DEC-001 points 2 and 3; RS-ANA-003). A number with
    no word after it, or a word that is no slug, is refused."""
    assert (project.root / DEVELOP).is_file() and (project.root / INSTALL).is_file()
    for area in ("010-", "010-Develop", "010_develop", "10-2"):
        refused = new(project, "use-case", "more", "--actor", "ACT-developer", "--area", area)
        assert refused.returncode != 0, area
        assert "such as `010-develop`" in refused.stderr, refused.stderr
    assert stamped(project, "use-case", "more", "--actor", "ACT-developer", "--area", "2-x") == (
        "UC-005"
    )
    assert (project.root / USE_CASES / "2-x" / "UC-005-more.md").is_file()


def test_an_area_is_the_folder_below_the_use_cases_and_its_number_opens_its_name() -> None:
    top = f"{ANALYSIS}/use-case-model/use-cases"
    nested = f"{ANALYSIS}/*/use-case-model/use-cases/**"
    analysis = model.Analysis(
        location=ANALYSIS,
        places={"use-case": top},
        nested={"use-case": nested},
        artefacts=(),
        strays=(),
        unreadable={},
        files={},
        records=(),
    )

    def area(path: str) -> str | None:
        return analysis.area(model.Artefact("use-case", "UC-001", path, path, False, {}, {}))

    assert area(f"{top}/010-develop/UC-001-x.md") == "010-develop"
    assert area(f"{top}/010-develop/deeper/UC-001-x.md") == "010-develop"
    assert area(f"{top}/UC-001-x.md") is None
    assert area(f"{ANALYSIS}/core/use-case-model/use-cases/020-set-up/UC-001-x.md") == "020-set-up"
    assert area(f"{ANALYSIS}/core/use-case-model/use-cases/UC-001-x.md") is None
    assert [model.area_number(a) for a in ("010-develop", "7-x", "develop", None, "010")] == [
        10,
        7,
        None,
        None,
        None,
    ]
    assert chain.later("020-release", "010-develop")
    assert not chain.later("010-develop", "010-develop")
    assert not chain.later("loose", "010-develop") and not chain.later("020-a", None)
    assert chain.ordered_areas(["loose", "100-z", "020-b", "010-a"]) == [
        "010-a",
        "020-b",
        "100-z",
        "loose",
    ]


def test_a_producer_of_an_area_without_a_number_is_left_to_a_reviewer() -> None:
    """The check refuses a precondition only where each producer lies in a later numbered
    area: one in an area without a number, or in none, is no later, nor is the use case
    itself, nor the environment. A use case in an area without a number is not compared."""
    top = f"{ANALYSIS}/use-case-model/use-cases"

    def use_case(uc: str, area: str | None) -> Any:
        path = f"{top}/{area}/{uc}-x.md" if area else f"{top}/{uc}-x.md"
        fields = {"id": uc, "status": "active"}
        return model.Artefact("use-case", uc, path, path, False, fields, {})

    held = (
        use_case("UC-001", "010-a"),
        use_case("UC-002", "020-b"),
        use_case("UC-003", "loose"),
        use_case("UC-004", None),
        use_case("UC-005", "loose"),
    )
    analysis = model.Analysis(
        location=ANALYSIS,
        places={"use-case": top},
        artefacts=held,
        strays=(),
        unreadable={},
        files={a.path: a.kind for a in held},
        records=(),
    )
    first = held[0]
    assert check._all_later(analysis, first, [["UC-003"], ["UC-004"], ["UC-001"]]) == []
    assert check._all_later(analysis, first, [["UC-002", "environment"], ["UC-009"]]) == []
    ((where, message),) = check._all_later(analysis, first, [["UC-002"]])
    assert where == f"{first.path}:/after/0"
    assert message.startswith("each producer of precondition 1 lies in a later area than 010-a")
    assert check._all_later(analysis, held[4], [["UC-002"]]) == []


# --- the words ------------------------------------------------------------------------------


def _part(text: str) -> Any:
    found = chain.words(text, structure.read_kinds()["use-case"])
    assert found is not None
    return found


def test_each_precondition_opens_with_its_producers() -> None:
    """Each item of *Preconditions*, or its text where it holds no item, opens with its
    producers: use cases by id, and the environment, separated by commas and `or`, the
    colon inside the bold run or right after it (DEC-001 point 1)."""
    element, written = _part(
        "**Preconditions:**\n\n"
        "- **From UC-003:** one.\n"
        "- **From UC-001 or UC-064:** two.\n"
        "- **From UC-059, or Environment:** three.\n"
        "- **From UC-001, UC-002, or UC-003**: four.\n"
        "- The fifth, with none.\n"
        "- **From the build:** six.\n"
        "- **From UC-007** seven.\n\n"
        "**Assumptions:** None.\n"
    )
    assert element.id == "preconditions"
    assert [(p.line, p.named) for p in written] == [
        (3, ("UC-003",)),
        (4, ("UC-001", "UC-064")),
        (5, ("UC-059", "environment")),
        (6, ("UC-001", "UC-002", "UC-003")),
        (7, None),
        (8, None),
        (9, None),
    ]
    assert _part("**Preconditions:** None.\n\n**Assumptions:** None.\n")[1] == []
    (alone,) = _part("**Preconditions:** **From UC-002:** one.\n\n**Assumptions:** None.\n")[1]
    assert (alone.line, alone.named) == (1, ("UC-002",))


def test_a_closed_list_of_labels_reads_no_precondition_s_opening_as_a_label() -> None:
    """A project rule that closes the use case's labels reports a bold run of its own,
    but never a precondition's producers in *Preconditions*, which DEC-001 point 1 asks
    each line to open with."""
    kind = dataclasses.replace(structure.read_kinds()["use-case"], closed=("RS-LOC-001",))
    body = (
        "**Preconditions:**\n\n- **From UC-003:** one.\n- **From UC-059, or Environment:** two.\n"
        "- **Odd:** three.\n\n**Assumptions:** None.\n\n**From UC-004:** outside.\n"
    )
    lines = [(i + 1, line) for i, line in enumerate(body.split("\n"))]
    undeclared = [d for d in structure.departures(lines, kind) if d.how == "undeclared-label"]
    assert [(d.element.text, d.line) for d in undeclared] == [("Odd", 5), ("From UC-004", 9)]


# --- the chain's arrows ---------------------------------------------------------------------


def test_the_chain_leaves_out_only_a_solid_arrow_others_imply() -> None:
    """Through a third node, a solid arrow is implied and left out. A loop counts as one
    node, so the arrows within it stay, and so does an arrow from a node to itself
    (DEC-003 point 5)."""
    solid = {
        ("A", "B"),
        ("B", "C"),
        ("A", "C"),  # implied through B
        ("C", "D"),
        ("D", "C"),  # C and D: one loop, whose arrows stay
        ("B", "D"),  # into the loop, one node with C: no third node, so it stays
        ("D", "E"),
        ("C", "E"),  # from the loop to E: no third node either
        ("E", "E"),
        ("A", "E"),  # implied through B
    }
    assert chain.left_out(solid) == {("A", "C"), ("A", "E")}
    assert chain.left_out({("A", "A")}) == set()
    assert chain.left_out(set()) == set()
