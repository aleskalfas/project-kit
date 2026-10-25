"""software-analysis: the analysis links its citations of records, points and rules (#1865).

Held to software-analysis DEC-001 point 13:

- **the forms** — a record (`COR-050`, `PRJ-002`), a capability's decision with its name
  before it, possessive or not, with a colon or in brackets, a point (`point 14`,
  `point D1`), several (`points 6 and 9`), labels alone (`PRJ-002 D1 and D4`), and a
  rule (`RS-WRITE-005`, `software-analysis:RS-SAN-001`); a `DEC-NNN` names the
  capability a word before it names, else the one a list carries, else the analysis's
  own, else none, and is then warned of;
- **the targets** — through `pkit refs lookup` alone: a record's file, a point's
  heading by GitHub's anchor, a list-form record's file once, the record of a point it
  does not hold, with a warning; one link around a citation of one point, one around
  each id of several;
- **the safeguards** — the first citation of each target in each section (each part of
  an artefact of a kind with labels), never in code, headings, labels or other links,
  never after `<!-- pkit:not-a-citation -->`, and a term never linked inside a citation;
- **the check** — a link missing, extra or stale fails into a file the project writes,
  and is warned of into one it receives; a reworded point heading stales its links,
  and the command mends them;
- **no folder walked** — the capability's scripts find no record or rule set
  themselves.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

import pytest

from project_kit import refs
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    ACTORS,
    CAPABILITY,
    VALIDATE,
    fill,
    installed,
    link,
    load_lib,
    prepare,
    run_script,
    stamped,
)

links: Any
citations: Any
links, citations = load_lib("links", "citations")


# --- the forms and the links, read alone --------------------------------------------------

#: What the lookup answers, by what it is asked, for the tests read alone: a record whose
#: points are headings, a labelled one, one whose points are a list, a received one,
#: capability decisions, and a rule.
P1 = ".pkit/decisions/project/PRJ-001-exports.md"
P2 = ".pkit/decisions/project/PRJ-002-versions.md"
C7 = ".pkit/decisions/core/COR-007-pattern-extraction.md"
C50 = ".pkit/decisions/core/COR-050-anchors-and-friction.md"
SA1 = ".pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md"
PM8 = ".pkit/capabilities/project-management/decisions/DEC-008-roles.md"
PM29 = ".pkit/capabilities/project-management/decisions/DEC-029-project-manager-agent.md"
SE1 = ".pkit/capabilities/software-engineering/decisions/DEC-001-conventions.md"
WRITE = "tech-docs/rule-sets/writing.md"

F = citations.Found
LOOKUPS = {
    "PRJ-001": F(P1),
    "PRJ-001#1": F(P1, "1-sign-each-export"),
    "PRJ-001#2": F(P1, "2-keep-a-run_log"),
    "PRJ-001#9": F(P1, None, "PRJ-001 holds no point 9"),
    "PRJ-002": F(P2),
    "PRJ-002#D1": F(P2, "d1--declared-per-change"),
    "PRJ-002#D4": F(P2, "d4--floors-raised-on-release"),
    "PRJ-002#H2": F(P2, None, "PRJ-002 holds no point H2"),
    "COR-007": F(C7, received=True),
    "COR-007#3": F(C7, None, received=True),
    "COR-007#5": F(C7, None, received=True),
    "COR-050": F(C50, received=True),
    "COR-050#2": F(C50, "2-anchors", received=True),
    "software-analysis:DEC-001": F(SA1),
    "software-analysis:DEC-001#2": F(SA1, "2-where-it-keeps-them"),
    "software-analysis:DEC-001-software-analysis-discipline": F(SA1),
    "software-analysis:DEC-001-software-analysis-discipline#2": F(SA1, "2-where-it-keeps-them"),
    "project-management:DEC-008": F(PM8),
    "project-management:DEC-029": F(PM29),
    "software-engineering:DEC-001": F(SE1),
    "software-engineering:DEC-001#4": F(SE1, "4-the-corpus"),
    "RS-WRITE-005": F(WRITE, "rs-write-005--sentences-of-25-words-at-most"),
    "software-analysis:RS-SAN-001": F(
        ".pkit/capabilities/software-analysis/rule-sets/san.md", "rs-san-001--format"
    ),
}

#: The file the links of these tests lead from, two folders below the root.
FROM = "tech-docs/analysis/glossary.md"
UP = "../../"


def _linked(text: str, component: str | None = None, vocabulary: Any = None) -> str:
    cites = links.Cites(LOOKUPS, component)
    return links.section(text, None, vocabulary, FROM, 1, cites=cites)[0]


def _found(text: str, component: str | None = None) -> list[Any]:
    cites = links.Cites(LOOKUPS, component)
    return links.section(text, None, None, FROM, 1, cites=cites)[1]


@pytest.mark.parametrize(
    ("text", "linked"),
    [
        # A record cited whole links to its file; a possessive's 's stays outside.
        ("PRJ-001's rule", f"[PRJ-001]({UP}{P1})'s rule"),
        # One point, numbered or labelled, is one link around the whole citation.
        (
            "per PRJ-001 point 1 and PRJ-002 D1.",
            f"per [PRJ-001 point 1]({UP}{P1}#1-sign-each-export) and "
            f"[PRJ-002 D1]({UP}{P2}#d1--declared-per-change).",
        ),
        # Several points: each id is a link of its own.
        (
            "PRJ-001 points 1 and 2; PRJ-002 D1 and D4",
            f"PRJ-001 points [1]({UP}{P1}#1-sign-each-export) and "
            f"[2]({UP}{P1}#2-keep-a-run_log); PRJ-002 [D1]({UP}{P2}#d1--declared-per-change) "
            f"and [D4]({UP}{P2}#d4--floors-raised-on-release)",
        ),
        # A capability's decision: its name before it, possessive, with a colon, in
        # brackets with its slug.
        (
            "software-analysis DEC-001 point 2",
            f"[software-analysis DEC-001 point 2]({UP}{SA1}#2-where-it-keeps-them)",
        ),
        (
            "software-analysis:DEC-001 point 2",
            f"[software-analysis:DEC-001 point 2]({UP}{SA1}#2-where-it-keeps-them)",
        ),
        (
            "software-analysis's DEC-001",
            f"[software-analysis's DEC-001]({UP}{SA1})",
        ),
        (
            "[software-analysis:DEC-001-software-analysis-discipline] point 2",
            f"[[software-analysis:DEC-001-software-analysis-discipline] point 2]"
            f"({UP}{SA1}#2-where-it-keeps-them)",
        ),
        # A list carries its capability to a `DEC-NNN` after it.
        (
            "project-management DEC-008 and DEC-029",
            f"[project-management DEC-008]({UP}{PM8}) and [DEC-029]({UP}{PM29})",
        ),
        # A rule, bare or with its component.
        (
            "RS-WRITE-005 and software-analysis:RS-SAN-001",
            "[RS-WRITE-005](../rule-sets/writing.md#rs-write-005--sentences-of-25-words-at-most)"
            " and "
            f"[software-analysis:RS-SAN-001]({UP}.pkit/capabilities/software-analysis/rule-sets/"
            "san.md#rs-san-001--format)",
        ),
        # A record whose points are a list: one link to its file, whatever it cites.
        ("COR-007 points 3 and 5", f"[COR-007 points 3 and 5]({UP}{C7})"),
        # A label that is no point of its record: the record is cited whole.
        ("PRJ-002 H2 headings", f"[PRJ-002]({UP}{P2}) H2 headings"),
        # A point its record does not hold links to the record.
        ("PRJ-001 point 9", f"[PRJ-001 point 9]({UP}{P1})"),
    ],
)
def test_each_form_links_to_what_it_cites(text: str, linked: str) -> None:
    assert _linked(text) == linked


def test_only_the_first_citation_of_each_target_in_a_section_is_linked() -> None:
    """The record whole, each point and each rule count apart; a point linked already is
    plain in a later list, and the escape takes one citation out, the next counting as
    the first."""
    text = (
        "PRJ-001 point 1, then PRJ-001, PRJ-001 point 1 and PRJ-001 points 1 and 2. "
        "<!-- pkit:not-a-citation --> PRJ-002 D1, then PRJ-002 D1."
    )
    assert _linked(text) == (
        f"[PRJ-001 point 1]({UP}{P1}#1-sign-each-export), then [PRJ-001]({UP}{P1}), "
        f"PRJ-001 point 1 and PRJ-001 points 1 and [2]({UP}{P1}#2-keep-a-run_log). "
        f"<!-- pkit:not-a-citation --> PRJ-002 D1, then "
        f"[PRJ-002 D1]({UP}{P2}#d1--declared-per-change)."
    )


def test_code_headings_labels_and_other_links_hold_no_citation() -> None:
    text = (
        "### PRJ-001 point 1\n\n**PRJ-001:** `PRJ-001 point 1` and "
        "[PRJ-001](https://example.org/PRJ-001), decisions/PRJ-001, PRJ-001-exports.\n"
    )
    assert _linked(text) == text


def test_which_capability_a_decision_names() -> None:
    """In software-engineering's analysis, a `DEC-NNN` with no word before it is its
    own; after a word, it is that word's capability's or none, never the analysis's;
    after a list, the list's."""
    own = f"([DEC-001 point 4]({UP}{SE1}#4-the-corpus))"
    assert _linked("(DEC-001 point 4)", "software-engineering") == own
    assert _linked("project-management DEC-008 and DEC-029", "software-engineering") == (
        f"[project-management DEC-008]({UP}{PM8}) and [DEC-029]({UP}{PM29})"
    )
    found = _found("per DEC-001, and (DEC-008)", "software-engineering")
    assert [(d.how, d.text) for d in found] == [
        (links.UNRESOLVED, "DEC-001"),
        (links.UNRESOLVED, "DEC-008"),
    ]
    assert found[0].wanted == citations.NO_CAPABILITY


def test_a_point_its_record_lacks_is_warned_of_and_a_link_into_a_received_file_marked() -> None:
    found = _found("PRJ-001 point 9 and COR-050 point 2")
    assert sorted((d.how, d.text, d.received) for d in found) == [
        (links.MISSING, "COR-050 point 2", True),
        (links.MISSING, "PRJ-001 point 9", False),
        (links.UNRESOLVED, "PRJ-001 point 9", False),
    ]
    (note,) = [d for d in found if d.how == links.UNRESOLVED]
    assert note.wanted == "PRJ-001 holds no point 9"


def test_a_term_is_never_linked_inside_a_citation_and_its_old_link_is_taken_out() -> None:
    """The analysis held term links on `point` inside citations; the command takes them
    out and links the citation, and `point` outside one still links its term."""
    term = links.Term("TERM-point", "point", "tech-docs/analysis/glossary.md")
    vocabulary = links.Vocabulary((term,), {term.id: ("point",)})
    text = "PRJ-001 [point](#term-point--point) 2, a point."
    assert _linked(text, None, vocabulary) == (
        f"[PRJ-001 point 2]({UP}{P1}#2-keep-a-run_log), a [point](#term-point--point)."
    )


def test_a_link_written_by_hand_is_held_as_the_command_s() -> None:
    """A link whose text is a citation, or a point's id in one, and whose target is a path
    to a Markdown file, is the command's: rewritten where stale, taken out where extra. A
    link to a web address is the writer's."""
    stale = f"[PRJ-001 point 1]({UP}{P1}#1-sign-every-export) and [PRJ-001 point 1](x.md)"
    found = _found(stale)
    assert [(d.how, d.written) for d in found] == [
        (links.STALE, f"{UP}{P1}#1-sign-every-export"),
        (links.EXTRA, "x.md"),
    ]
    assert _linked(stale) == f"[PRJ-001 point 1]({UP}{P1}#1-sign-each-export) and PRJ-001 point 1"
    assert citations.is_cited_link("2", f"{UP}{P1}#2-keep") is True
    assert citations.is_cited_link("2", "notes.md") is False
    assert citations.is_cited_link("PRJ-001", "https://example.org/PRJ-001.md") is False


def test_each_part_of_an_artefact_with_labels_is_a_section() -> None:
    lines = ["# UC-001 — Run", "", "**Goal:** a.", "", "- **1a.** b.", "  - **x:** c.", "d."]
    assert links.part_sections(lines, 0) == [(0, 0), (0, 2), (2, 4), (4, 7)]


def test_a_use_case_takes_both_kinds_of_link_each_in_its_own_sections(tmp_path: Path) -> None:
    """Where the analysis keeps a domain model, a use case takes the links of its terms
    part by part, as its kind declares its parts (DEC-004 point 7), and the links of its
    citations in each section a heading or a bold label opens, such as each variant
    (DEC-001 point 13). A citation in its goal takes its link while a term there stays
    plain, and the word `point` inside a citation links no term."""
    (model,) = load_lib("model")
    kind = links.parted(tmp_path)["use-case"]
    term = links.Term("TERM-point", "point", "tech-docs/analysis/glossary.md")
    vocabulary = links.Vocabulary((term,), {term.id: ("point",)})
    path = "tech-docs/analysis/use-case-model/use-cases/UC-001-run.md"
    artefact = model.Artefact("use-case", "UC-001", path, path, False, {}, {})
    text = (
        "# UC-001 — Run\n\n"
        "**Goal:** Sign at a point, per PRJ-001 point 1.\n\n"
        "**Variants:**\n\n"
        "- **1a.** A point fails, per PRJ-001 point 1.\n"
        "- **1b.** Another point fails, per PRJ-001 point 1.\n"
    )
    found = links.document(artefact, text, vocabulary, kind, links.Cites(LOOKUPS, None))
    cited = f"[PRJ-001 point 1](../../../../{P1}#1-sign-each-export)"
    assert found.linked == (
        "# UC-001 — Run\n\n"
        f"**Goal:** Sign at a point, per {cited}.\n\n"
        "**Variants:**\n\n"
        f"- **1a.** A [point](../../glossary.md#term-point--point) fails, per {cited}.\n"
        f"- **1b.** Another point fails, per {cited}.\n"
    )


def test_one_run_asks_the_point_a_term_link_inside_its_citation_hid(tmp_path: Path) -> None:
    """What the lookup is asked is read as the links are written, so a term link on
    `point` inside a citation, which the pass takes out, hides none of its points: one run
    links the citation, and a second has nothing left to write."""
    model, analyses = load_lib("model", "analyses")
    kinds = links.parted(tmp_path)
    path = "tech-docs/analysis/use-case-model/use-cases/UC-001-run.md"
    analysis = model.Analysis(
        location="tech-docs/analysis",
        places={},
        artefacts=(
            model.Artefact(
                model.TERM, "TERM-point", FROM, f"{FROM}#TERM-point", True, {"name": "point"}, {}
            ),
            model.Artefact(model.VIEW, "VIEW-run", "v.md", "v.md", False, {}, {}),
            model.Artefact(model.USE_CASE, "UC-001", path, path, False, {}, {}),
        ),
        strays=(),
        unreadable={},
        files={},
        records=(),
    )
    listing = analyses.Listing()
    term_link = "[point](../../glossary.md#term-point--point)"
    read = {path: f"# UC-001 — Run\n\nSign, per PRJ-001 {term_link} 2.\n"}
    asked = links.asked(analysis, listing, read, kinds)
    assert "PRJ-001#2" in asked
    lookups = {key: LOOKUPS[key] for key in asked if key in LOOKUPS}
    (linked,) = links.plan(analysis, listing, read, kinds, lookups)
    assert linked.linked == (
        f"# UC-001 — Run\n\nSign, per [PRJ-001 point 2](../../../../{P1}#2-keep-a-run_log).\n"
    )
    assert [d for d in linked.departures if d.how == links.UNRESOLVED] == []


# --- the command and the check, in an adopter ------------------------------------------------

ACTOR = f"{ACTORS}/ACT-tester.md"
REL = "../../../../"


def _record(record_id: str, decision: str) -> str:
    return (
        f"---\nid: {record_id}\ntitle: A record\nstatus: accepted\ndate: 2026-10-21\n"
        f"author: t\n---\n\n# {record_id}\n\n## Context\n\nWhy.\n\n## Decision\n\n"
        f"**The choice.**\n\n{decision}\n## Rationale\n\nBecause.\n"
    )


PRJ_001 = _record(
    "PRJ-001",
    "### 1. Sign each export\n\nText.\n\n### 2. Keep a `run_log`\n\nText.\n",
)
PRJ_002 = _record(
    "PRJ-002",
    "### D1 — Declared per change\n\nText.\n\n### D2 — Applied on release\n\nText.\n",
)

#: The actor's body as a writer fills it, citing the records.
BODY = (
    "# ACT-tester — Tester\n\n"
    "Someone who runs the suite (PRJ-001 point 1). They read PRJ-001 point 1 again, and "
    "PRJ-001 points 1 and 2, then PRJ-002 D1 and D2.\n\n"
    "**Occasions:** Each release, as PRJ-001 says, and `PRJ-001 point 2` in code. "
    "<!-- pkit:not-a-citation --> PRJ-002 D1 is quoted.\n\n"
    "**Context:** None, as COR-050 point 2 and [the record](https://example.org/PRJ-001) "
    "say.\n"
)


def _linked_body(cor_050_2: str) -> str:
    p1 = f"{REL}.pkit/decisions/project/PRJ-001-exports.md"
    p2 = f"{REL}.pkit/decisions/project/PRJ-002-versions.md"
    return (
        "# ACT-tester — Tester\n\n"
        f"Someone who runs the suite ([PRJ-001 point 1]({p1}#1-sign-each-export)). They read "
        f"PRJ-001 point 1 again, and PRJ-001 points 1 and [2]({p1}#2-keep-a-run_log), then "
        f"PRJ-002 [D1]({p2}#d1--declared-per-change) and [D2]({p2}#d2--applied-on-release).\n\n"
        f"**Occasions:** Each release, as [PRJ-001]({p1}) says, and `PRJ-001 point 2` in code. "
        "<!-- pkit:not-a-citation --> PRJ-002 D1 is quoted.\n\n"
        f"**Context:** None, as [COR-050 point 2]({REL}{cor_050_2}) and "
        "[the record](https://example.org/PRJ-001) say.\n"
    )


def _cited(repo: AdopterRepo) -> None:
    """Two project records, and an actor whose body cites them and a core record. Built
    once per session (`installed`)."""
    prepare(repo)
    repo.write(
        {
            ".pkit/decisions/project/PRJ-001-exports.md": PRJ_001,
            ".pkit/decisions/project/PRJ-002-versions.md": PRJ_002,
        }
    )
    stamped(repo, "actor", "tester", "--name", "Tester", "--path", "src/run.py")
    fill(repo)
    text = (repo.root / ACTOR).read_text(encoding="utf-8")
    front = text.split("\n---\n", 1)[0]
    repo.write({ACTOR: f"{front}\n---\n\n{BODY}"})
    repo.commit("cite records")


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch, then=_cited)


def _validate(repo: AdopterRepo) -> list[tuple[str, str, str]]:
    completed = run_script(repo, VALIDATE, "--json")
    assert completed.returncode == 0, completed.stderr
    return [
        (f["severity"], f["location"], f["message"])
        for f in json.loads(completed.stdout)["findings"]
        if "DEC-001 point 13" in f["message"]
    ]


def _body(repo: AdopterRepo) -> str:
    return (repo.root / ACTOR).read_text(encoding="utf-8").split("\n---\n", 1)[1].lstrip("\n")


def _cor_050_2(repo: AdopterRepo) -> str:
    (found,) = refs.lookup_citations(repo.root, ["COR-050#2"])
    assert found.path is not None and found.anchor is not None and found.received
    return f"{found.path}#{found.anchor}"


def test_the_command_links_each_citation_and_the_check_holds_them(project: AdopterRepo) -> None:
    """Unlinked, each first citation of a project record fails and one of a received core
    record is warned of; the command writes them as `_linked_body` shows, after which the
    check finds nothing and a second run writes nothing."""
    found = _validate(project)
    assert [s for s, _l, _m in found].count("error") == 5, found
    assert [s for s, _l, _m in found].count("warning") == 1, found
    assert (
        "error",
        ACTOR,
        "line 17: `PRJ-001 point 1` is the first citation of what it cites in its section, "
        "and takes a link to it, `../../../../.pkit/decisions/project/PRJ-001-exports.md"
        "#1-sign-each-export` — run `pkit analysis link`, which writes the links (DEC-001 "
        "point 13)",
    ) in found, found
    completed = link(project)
    assert completed.stdout.splitlines() == [f"linked {ACTOR} (6 link(s) written or mended)"]
    assert _body(project) == _linked_body(_cor_050_2(project))
    assert _validate(project) == []
    assert link(project).stdout.strip() == "Every link is as it should be; nothing written."


def test_a_reworded_point_heading_stales_its_link_and_the_command_mends_it(
    project: AdopterRepo,
) -> None:
    """A point keeps its id, and its title may change: the anchor moves, the check reports
    the link as stale, and the command rewrites it (DEC-001 point 13; COR-058 point 3)."""
    link(project)
    record = ".pkit/decisions/project/PRJ-001-exports.md"
    project.write({record: PRJ_001.replace("### 1. Sign each export", "### 1. Sign every export")})
    ((severity, where, message),) = _validate(project)
    assert (severity, where) == ("error", ACTOR)
    assert message.startswith(
        "line 17: `PRJ-001 point 1` links to `../../../../.pkit/decisions/project/"
        "PRJ-001-exports.md#1-sign-each-export`, and what it cites lies at "
        "`../../../../.pkit/decisions/project/PRJ-001-exports.md#1-sign-every-export`"
    ), message
    link(project)
    assert "#1-sign-every-export)" in _body(project)
    assert _validate(project) == []


def test_a_stale_link_into_a_received_record_is_warned_of(project: AdopterRepo) -> None:
    """A core record is the project's to receive, not to write: a stale link into it is a
    warning, which names why, and the command mends it."""
    link(project)
    text = (project.root / ACTOR).read_text(encoding="utf-8")
    project.write({ACTOR: re.sub(r"(\[COR-050 point 2\]\([^)#]*)#[^)]*\)", r"\1#2-old)", text)})
    ((severity, _where, message),) = _validate(project)
    assert severity == "warning"
    assert "since the project receives that file as a synced copy" in message
    link(project)
    assert _validate(project) == []


def test_a_decision_that_names_no_capability_is_warned_of(project: AdopterRepo) -> None:
    """The one analysis at the location's top names no component, so a `DEC-NNN` with no
    capability's name takes no link."""
    text = (project.root / ACTOR).read_text(encoding="utf-8")
    project.write({ACTOR: text.replace("Each release,", "Each release (DEC-003),")})
    link(project)
    assert "(DEC-003)" in _body(project)
    warned = [m for s, _l, m in _validate(project) if s == "warning"]
    assert warned == [
        "line 19: `DEC-003` takes no link, since it names no capability whose decision the "
        "lookup finds: write its capability's name before it, as in `<capability> DEC-NNN` — "
        "mend the citation, or mark one that is no citation with `<!-- pkit:not-a-citation "
        "-->` (DEC-001 point 13)"
    ]


# --- no folder walked --------------------------------------------------------------------------

#: What would walk a folder, and the folders of records and rule sets named in a string.
_WALKS = {"glob", "rglob", "iterdir", "walk", "listdir", "scandir"}
_FOLDERS = re.compile(r"(?:^|/)(?:decisions|rule-sets)/|/(?:decisions|rule-sets)$")


def test_the_capability_s_scripts_find_no_record_or_rule_set_themselves() -> None:
    """Every target of a link comes from `pkit refs lookup` (DEC-001 point 13): no script
    of the capability calls what walks a folder, or names a folder of records or rule
    sets in a string it could open."""
    offences: list[str] = []
    for script in sorted((CAPABILITY / "scripts").rglob("*.py")):
        tree = ast.parse(script.read_text(encoding="utf-8"))
        docstrings = {
            id(node.body[0].value)
            for node in ast.walk(tree)
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef))
            and node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in _WALKS:
                offences.append(f"{script.name}:{node.lineno} calls {node.attr}")
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in docstrings
                and " " not in node.value
                and _FOLDERS.search(node.value)
            ):
                offences.append(f"{script.name}:{node.lineno} names {node.value!r}")
    assert offences == []
