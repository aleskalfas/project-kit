"""software-analysis: each mention of an artefact by its id links to it (#2109).

Held to software-analysis DEC-001 point 14:

- **the links** — in every analysis, a domain model or none, `pkit analysis link` links
  the first mention of each artefact by its id in each section to that artefact: a use
  case, a journey, a requirement, an actor or a view to its file, a term to its glossary
  entry, by a path from the file; a journey's step lines and seams, and a precondition's
  producers, inside the bold, included;
- **what a mention is** — an id whole, any spelling of its number, alone for an artefact
  of its own analysis, or written with an analysis it builds on (`core:UC-021`); never in
  code, a heading, a link, a goal or an actor's first sentence, nor the artefact's own;
- **the check** — `pkit analysis validate` reports a link missing, extra or stale, whatever
  any rule's status, and names the command; a link to a web address, or to a heading
  other than a term's entry, is the writer's own;
- **what a form reads** — a journey's step lines and seams, a precondition's producers and
  the append-only comparison read an id's link as the id, so the format rule still holds;
- **an id is no mention of a term** — `core` in `core:UC-021` takes no term's link, and a
  term's id counts as no use of it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    ACTORS,
    JOURNEYS,
    QUALITY,
    USE_CASES,
    VALIDATE,
    accepting_san,
    fill,
    installed,
    link,
    load_lib,
    prepare,
    run_script,
    stamped,
)

links, id_links, forms, model, append_only, structure = load_lib(
    "links", "id_links", "forms", "model", "append_only", "structure"
)

RUN = f"{USE_CASES}/UC-001-run-suite.md"
READ = f"{USE_CASES}/UC-002-read-report.md"
SHARE = f"{USE_CASES}/UC-003-share-report.md"
JOURNEY = f"{JOURNEYS}/JRN-001-first-run.md"
TESTER = f"{ACTORS}/ACT-tester.md"
FAST = f"{QUALITY}/REQ-001-run-fast.md"

#: Where each link leads from a journey, and from a use case.
FROM_JOURNEY = {
    "UC-001": "../use-cases/UC-001-run-suite.md",
    "UC-002": "../use-cases/UC-002-read-report.md",
    "UC-003": "../use-cases/UC-003-share-report.md",
    "ACT-tester": "../actors/ACT-tester.md",
    "REQ-001": "../../requirements/quality/REQ-001-run-fast.md",
}
FROM_USE_CASE = {
    "UC-001": "UC-001-run-suite.md",
    "JRN-001": "../journeys/JRN-001-first-run.md",
    "REQ-001": "../../requirements/quality/REQ-001-run-fast.md",
}


def _bodies(linked: bool) -> dict[str, str]:
    """The journey's and the second use case's bodies below their front matter, as a
    writer fills them or, `linked`, as `pkit analysis link` writes them. The analysis keeps
    no view, so no term is linked: only the ids are."""

    def j(text: str, artefact: str | None = None) -> str:
        target = FROM_JOURNEY[artefact or text]
        return f"[{text}]({target})" if linked else text

    def u(text: str, artefact: str | None = None) -> str:
        target = FROM_USE_CASE[artefact or text]
        return f"[{text}]({target})" if linked else text

    return {
        JOURNEY: "\n".join(
            [
                "# JRN-001 — Run the suite and read its report",
                "",
                "**Goal:** Run the suite and read its report, as UC-001 begins it.",
                "",
                "**Steps:**",
                "",
                f"1. {j('UC-001')} — Run the suite",
                f"   - **Needs from {j('UC-003')} (outside this journey):** the shared suite. A "
                "suite not shared runs nothing.",
                f"2. {j('UC-002')} — Read the report",
                "   - **Needs from step 1 (UC-001):** the run's result. UC-001 variant 1a leaves "
                "none.",
                "",
                "**Variants:**",
                "",
                f"- **2a.** The report is gone, and {j('UC-002')} ends. The `UC-002` code, "
                "UC-099 and core:UC-001 stay plain, as does "
                f"[UC-002](https://example.org/UC-002). {j('ACT-tester')} sees it.",
                "",
                f"**Postconditions:** JRN-001 ends with the report read, as {j('REQ-001')} asks.",
                "",
                "**Minimal guarantees:** None.",
                "",
            ]
        ),
        READ: "\n".join(
            [
                "# UC-002 — Read the report",
                "",
                "**Goal:** Read the report of my run.",
                "",
                "**Other actors:** None.",
                "",
                f"**Preconditions:** **From {u('UC-1', 'UC-001')}:** a run has finished. Its "
                "report waits where UC-001 left it.",
                "",
                "**Assumptions:** None.",
                "",
                "**Trigger:** The tester opens the report UC-002 names.",
                "",
                "**Main path:**",
                "",
                f"1. The system shows the report of the run {u('UC-001')} made.",
                f"2. The tester reads it, as {u('REQ-001')} asks.",
                "",
                "**Variants:** None.",
                "",
                f"**Postconditions:** The tester has read the report, and {u('JRN-001')} goes on.",
                "",
                "**Minimal guarantees:** None.",
                "",
            ]
        ),
    }


BODIES = _bodies(linked=False)
BODIES_LINKED = _bodies(linked=True)


def _ids(repo: AdopterRepo) -> None:
    """An actor, three use cases, a journey through two of them that relies on the third,
    and a quality requirement, filled, with `BODIES` written over the journey and the
    second use case. No view, so the analysis keeps no domain model. Built once per
    session (`installed`)."""
    prepare(repo)
    stamped(repo, "actor", "tester", "--path", "src/run.py")
    actor = ("--actor", "ACT-tester")
    for slug, title in (
        ("run-suite", "Run the suite"),
        ("read-report", "Read the report"),
        ("share-report", "Share the report"),
    ):
        stamped(repo, "use-case", slug, "--title", title, *actor)
    stamped(
        repo,
        "journey",
        "first-run",
        "--title",
        "Run the suite and read its report",
        *actor,
        *("--step", "UC-001", "--step", "UC-002", "--relies-on", "UC-003"),
    )
    stamped(repo, "quality-requirement", "run-fast", "--title", "Run fast", *actor)
    fill(repo)
    for rel, body in BODIES.items():
        front = _read(repo, rel).split("\n---\n", 1)[0]
        repo.write({rel: f"{front}\n---\n\n{body}"})


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch, then=_ids)


def _read(repo: AdopterRepo, rel: str) -> str:
    return (repo.root / rel).read_text(encoding="utf-8")


def _body(repo: AdopterRepo, rel: str) -> str:
    return _read(repo, rel).split("\n---\n", 1)[1].lstrip("\n")


def _errors(repo: AdopterRepo) -> list[tuple[str, str]]:
    completed = run_script(repo, VALIDATE, "--json")
    assert completed.returncode in (0, 1), completed.stderr
    return [
        (f["location"], f["message"])
        for f in json.loads(completed.stdout)["findings"]
        if f["severity"] == "error"
    ]


MEND = "run `pkit analysis link`, which writes the links (DEC-001 point 14)"


def _line(text: str, needle: str) -> int:
    """The number of the line of `text` that holds `needle`, counted from 1."""
    (number,) = [n for n, line in enumerate(text.split("\n"), start=1) if needle in line]
    return number


# --- the command writes them, the check holds them -----------------------------------------


def test_the_command_links_each_first_mention_of_an_id_with_no_domain_model(
    project: AdopterRepo,
) -> None:
    """With no view in the analysis, the command links ids alone: each step line's use
    case, a seam's and a precondition's ids inside the bold, an actor and a requirement,
    each first in its part. A goal, code, a web link, an id naming nothing and the
    artefact's own stay plain. The analysis then passes the check, the format rule
    accepted included, and a second run writes nothing (DEC-001 point 14)."""
    fronts = {rel: _read(project, rel).split("\n---\n", 1)[0] for rel in BODIES}
    link(project)
    for rel, body in BODIES_LINKED.items():
        assert _body(project, rel) == body, rel
        assert _read(project, rel).split("\n---\n", 1)[0] == fronts[rel], rel
    assert _errors(project) == []
    # The format rule accepted, the journey's steps and seams and the use case's parts
    # still match their forms, the ids linked (the other use cases hold their examples).
    project.write(accepting_san(project))
    assert [f for f in _errors(project) if f[0] in BODIES] == []
    assert link(project).stdout.strip() == "Every link is as it should be; nothing written."


def test_the_check_reports_an_id_s_link_missing_extra_or_stale(project: AdopterRepo) -> None:
    """Whatever any rule's status, the check reports each first mention of an id left
    unlinked, a link where none belongs, and one whose target is stale, and names the
    command, which mends each (DEC-001 point 14)."""
    found = _errors(project)
    first = _line(_read(project, JOURNEY), "1. UC-001 — Run the suite")
    assert (
        JOURNEY,
        f"line {first}: `UC-001` is the first mention of UC-001 in its section, and takes a "
        f"link to it, `{FROM_JOURNEY['UC-001']}` — {MEND}",
    ) in found, found
    assert {where for where, _m in found} == {JOURNEY, READ}, found
    assert all(m.endswith(MEND) for _w, m in found), found
    link(project)
    linked = _read(project, JOURNEY)
    stale = linked.replace(FROM_JOURNEY["UC-003"], "../use-cases/UC-003-old.md", 1)
    hand = f"([UC-001]({FROM_JOURNEY['UC-001']})):** the run's"
    project.write({JOURNEY: stale.replace("(UC-001):** the run's", hand, 1)})
    seam, step = _line(stale, "**Needs from [UC-003]"), _line(stale, "(UC-001):** the run's")
    messages = sorted(m.split(" — ")[0] for where, m in _errors(project) if where == JOURNEY)
    assert messages == [
        f"line {seam}: `UC-003` links to `../use-cases/UC-003-old.md`, and UC-003 is "
        f"`{FROM_JOURNEY['UC-003']}`",
        f"line {step}: `UC-001` links to `{FROM_JOURNEY['UC-001']}`, where no link belongs: "
        "only the first mention of an artefact of the analysis, or of one it builds on, by its "
        "id in each section takes one, never in the artefact itself, a goal or an actor's "
        "first sentence",
    ], messages
    link(project)
    assert _body(project, JOURNEY) == BODIES_LINKED[JOURNEY]
    assert _errors(project) == []


def test_a_renamed_file_moves_each_link_to_it(project: AdopterRepo) -> None:
    """A use case's file renamed, its id kept, leaves each link to it stale until the
    command runs (DEC-001 point 14)."""
    link(project)
    moved = f"{USE_CASES}/UC-003-share-the-suite.md"
    project.write({moved: _read(project, SHARE)})
    (project.root / SHARE).unlink()
    found = [m for where, m in _errors(project) if where == JOURNEY]
    assert len(found) == 1 and "`../use-cases/UC-003-share-the-suite.md`" in found[0], found
    link(project)
    assert "](../use-cases/UC-003-share-the-suite.md) (outside this journey)" in _read(
        project, JOURNEY
    )
    assert _errors(project) == []


# --- the matching, read alone ----------------------------------------------------------------

HERE = "tech-docs/analysis/use-case-model/use-cases/010-run/UC-007-run.md"


def _named(**built_on: dict[str, Any]) -> Any:
    own = {
        "UC-007": id_links.Target("UC-007", HERE),
        "UC-008": id_links.Target(
            "UC-008", "tech-docs/analysis/use-case-model/use-cases/020-read/UC-008-read.md"
        ),
        "TERM-change": id_links.Target(
            "TERM-change", "tech-docs/analysis/glossary.md", "term-change--change"
        ),
        "TERM-change-check": id_links.Target(
            "TERM-change-check", "tech-docs/analysis/glossary.md", "term-change-check--change-check"
        ),
    }
    return id_links.Named(own, built_on)


def _linked(text: str, named: Any = None, *terms: Any, own: str | None = "UC-007") -> str:
    vocabulary = links.Vocabulary(tuple(terms), {t.id: links._forms(t) for t in terms})
    ids = links.Ids(named or _named(), own)
    return links.section(text, None, vocabulary, HERE, 1, ids=ids)[0]


READ_TO = "../020-read/UC-008-read.md"


@pytest.mark.parametrize(
    ("text", "linked"),
    [
        # The first mention in a section, in any spelling of its number; never its own.
        (
            "UC-007 needs UC-8, then UC-008 again.",
            f"UC-007 needs [UC-8]({READ_TO}), then UC-008 again.",
        ),
        # Whole only: a file's name, a longer slug, a hyphen or an anchor hold none.
        (
            "UC-008-read.md, TERM-change-check, x-UC-008, #UC-008 and UC-0080.",
            "UC-008-read.md, [TERM-change-check](../../../glossary.md#term-change-check--"
            "change-check), x-UC-008, #UC-008 and UC-0080.",
        ),
        # A full stop ends a sentence, and joins a file's extension.
        ("It ends at UC-008.", f"It ends at [UC-008]({READ_TO})."),
        # A bold label is read; code, a heading, a comment and a link are not.
        (
            "**From UC-008:** a report.",
            f"**From [UC-008]({READ_TO}):** a report.",
        ),
        (
            "## UC-008\n`UC-008` <!-- UC-008 --> [UC-008](https://x.org/UC-008)",
            "## UC-008\n`UC-008` <!-- UC-008 --> [UC-008](https://x.org/UC-008)",
        ),
        # A term's id links to its entry; an id that names nothing takes no link.
        (
            "TERM-change and UC-999.",
            "[TERM-change](../../../glossary.md#term-change--change) and UC-999.",
        ),
    ],
)
def test_a_mention_of_an_id_is_read_whole_and_first(text: str, linked: str) -> None:
    assert _linked(text) == linked


def test_an_id_names_the_artefact_that_spells_it_so_first() -> None:
    """Of two artefacts whose numbers are one, which validation refuses, a mention names
    the one whose id it spells as written, and another spelling the one that writes its
    number in its one spelling (DEC-001 points 3 and 14)."""
    alias = "tech-docs/analysis/use-case-model/use-cases/020-read/UC-0008-alias.md"
    path = "tech-docs/analysis/model.md"
    analysis = model.Analysis(
        location="tech-docs/analysis",
        places={},
        artefacts=(
            model.Artefact("use-case", "UC-0008", alias, alias, False, {}, {}),
            model.Artefact("use-case", "UC-008", path, path, False, {}, {}),
        ),
        strays=(),
        unreadable={},
        files={},
        records=(),
    )
    named = id_links.named(analysis, links.analyses.Listing(), None)
    assert named.of(None, "UC-008").path == path
    assert named.of(None, "UC-0008").path == alias
    assert named.of(None, "UC-8").path == path


def test_an_id_written_with_an_analysis_names_one_it_builds_on() -> None:
    """`core:UC-021` names the core's use case where the text's analysis builds on the
    core; an id of another analysis written alone, or of one it does not build on, takes no
    link (DEC-001 points 2 and 14)."""
    core = {
        "UC-021": id_links.Target(
            "UC-021", "tech-docs/analysis/core/use-case-model/use-cases/UC-021-x.md"
        )
    }
    named = _named(core=core)
    text = "core:UC-021, UC-021 alone, and shipping:UC-021."
    assert _linked(text, named) == (
        "[core:UC-021](../../../core/use-case-model/use-cases/UC-021-x.md), UC-021 alone, "
        "and shipping:UC-021."
    )


def test_an_id_holds_no_mention_of_a_term() -> None:
    """A term named `core` takes no link inside `core:UC-021`, linked or not, and its own
    mention elsewhere still takes one (DEC-001 point 14, DEC-004 point 7)."""
    core_term = links.Term("TERM-core", "core", "tech-docs/analysis/glossary.md")
    core = {
        "UC-021": id_links.Target(
            "UC-021", "tech-docs/analysis/core/use-case-model/use-cases/UC-021-x.md"
        )
    }
    out = _linked("See core:UC-021 in the core.", _named(core=core), core_term)
    assert out == (
        "See [core:UC-021](../../../core/use-case-model/use-cases/UC-021-x.md) in the "
        "[core](../../../glossary.md#term-core--core)."
    )


def test_a_link_of_an_id_written_by_hand_is_held_unless_it_leads_to_a_heading() -> None:
    """A link whose words are an id and whose target is a file's path is the command's:
    on a later mention it is extra, and taken out. One to a web address, or to a heading
    other than a term's entry, is the writer's own (DEC-001 point 14)."""
    text = (
        f"[UC-008]({READ_TO}) then [UC-008]({READ_TO}) and "
        "[UC-008](../020-read/UC-008-read.md#steps)."
    )
    out, found = links.section(
        text, None, links.Vocabulary((), {}), HERE, 1, ids=links.Ids(_named(), "UC-007")
    )
    assert out == (
        f"[UC-008]({READ_TO}) then UC-008 and [UC-008](../020-read/UC-008-read.md#steps)."
    )
    assert [(d.how, d.of_id) for d in found] == [(links.EXTRA, True)]
    assert id_links.is_held("TERM-x", "../glossary.md#term-x--x")
    assert not id_links.is_held("VIEW-x", "domain-model/010-x.md#order")
    assert not id_links.is_held("UC-008", "https://example.org/UC-008.md")
    assert not id_links.is_held("the read", READ_TO)


def test_each_step_line_links_its_use_case_and_counts_first(tmp_path: Path) -> None:
    """Each step line links its use case's id, a use case taken twice at both its steps,
    whatever a hand-over before names; a later mention of that use case in the steps takes
    none (DEC-001 point 14)."""
    journey = links.parted(tmp_path)["journey"]
    path = "tech-docs/analysis/use-case-model/journeys/JRN-001-x.md"
    named = id_links.Named(
        {
            f"UC-00{n}": id_links.Target(
                f"UC-00{n}", f"tech-docs/analysis/use-case-model/use-cases/UC-00{n}-x.md"
            )
            for n in (1, 2, 3)
        },
        {},
    )
    text = (
        "# JRN-001 — T\n\n**Steps:**\n\n1. UC-001 — Run\n"
        "   - **Needs from UC-002 (outside this journey):** a suite.\n"
        "2. UC-002 — Read\n3. UC-001 — Run\n   - **Needs from step 2 (UC-002):** UC-003 too.\n"
    )
    artefact = model.Artefact("journey", "JRN-001", path, path, False, {}, {})
    out = links.document(artefact, text, links.Vocabulary((), {}), journey, named).linked

    def to(n: int) -> str:
        return f"[UC-00{n}](../use-cases/UC-00{n}-x.md)"

    assert out == (
        f"# JRN-001 — T\n\n**Steps:**\n\n1. {to(1)} — Run\n"
        "   - **Needs from UC-002 (outside this journey):** a suite.\n"
        f"2. {to(2)} — Read\n3. {to(1)} — Run\n"
        f"   - **Needs from step 2 (UC-002):** {to(3)} too.\n"
    )


def test_a_goal_and_an_actor_s_first_sentence_stay_plain_of_ids(tmp_path: Path) -> None:
    """A goal and an actor's first sentence, where it gives its summary, say a need and a
    datum again, so an id there takes no link, and the next mention counts as the first."""
    kinds = links.parted(tmp_path)
    named = _named()
    case = "# UC-007 — T\n\n**Goal:** Read UC-008.\n\n**Trigger:** UC-008 ends.\n"
    artefact = model.Artefact("use-case", "UC-007", HERE, HERE, False, {}, {})
    out = links.document(artefact, case, links.Vocabulary((), {}), kinds["use-case"], named)
    assert out.linked == case.replace("**Trigger:** UC-008", f"**Trigger:** [UC-008]({READ_TO})")
    actor_path = "tech-docs/analysis/use-case-model/actors/ACT-x.md"
    actor = model.Artefact(
        "actor", "ACT-x", actor_path, actor_path, False, {"summary": "Reads UC-008."}, {}
    )
    text = "# ACT-x — X\n\nReads UC-008. Then UC-008 again.\n"
    written = links.document(actor, text, links.Vocabulary((), {}), kinds["actor"], named).linked
    assert written == text.replace(
        "Then UC-008", "Then [UC-008](../use-cases/020-read/UC-008-read.md)"
    )


def test_a_term_s_id_is_no_use_of_the_term() -> None:
    """The terms an artefact uses are read from the links of its mentions: a link of a
    term's id counts none (DEC-001 point 14, DEC-004 point 7)."""
    order = links.Term("TERM-order", "order", "tech-docs/analysis/glossary.md")
    vocabulary = links.Vocabulary((order,), {order.id: ("order",)})
    path = "tech-docs/analysis/use-case-model/use-cases/UC-1.md"
    text = "---\nid: UC-1\n---\n\n[TERM-order](../../glossary.md#term-order--order) is named.\n"
    assert links.terms_linked(text, path, vocabulary) == frozenset()
    text = text.replace("is named", "and an [order](../../glossary.md#term-order--order)")
    assert links.terms_linked(text, path, vocabulary) == frozenset({"TERM-order"})


# --- what a form reads -----------------------------------------------------------------------


def test_the_forms_read_an_id_s_link_as_the_id() -> None:
    """A step line, a seam's label and a precondition's producers read an id's link as the
    id alone, so a linked id matches its data (DEC-001 point 14)."""
    assert forms.ids_read_plain("[UC-001](../x/UC-001-a.md) — Run") == "UC-001 — Run"
    assert forms.ids_read_plain("[core:ACT-ai](../../core/a/ACT-ai.md)") == "core:ACT-ai"
    assert forms.ids_read_plain("[a run](UC-001-a.md)") == "[a run](UC-001-a.md)"
    assert forms.named_producers("From [UC-003](UC-003-x.md), or Environment:") == (
        "UC-003",
        "environment",
    )


def test_the_append_only_comparison_reads_an_id_s_link_as_the_id() -> None:
    """A step whose id only gained a link keeps its text, so linking ids renumbers nothing
    and hides no renumbering (DEC-001 point 14)."""
    (kind,) = [k for name, k in structure.read_kinds().items() if name == "use-case"]
    body = (
        "---\nid: UC-007\n---\n\n# UC-007 — T\n\n**Main path:**\n\n1. The tester runs UC-008.\n\n"
        "**Variants:**\n\n- **1a.** UC-008 fails.\n"
    )
    linked = body.replace("runs UC-008", f"runs [UC-008]({READ_TO})").replace(
        "1a.** UC-008", f"1a.** [UC-008]({READ_TO})"
    )
    assert append_only.read(body, kind) == append_only.read(linked, kind)


def test_each_place_declares_the_form_of_the_links_of_ids() -> None:
    """Each target the command writes on an id matches the declared form whole, and no
    link to a heading, a web address or a revalidation record does (COR-050 point 5)."""
    written = [
        "UC-001-run.md",
        "../020-read/UC-008-read.md",
        "../use-cases/UC-001-run-suite.md",
        "../../requirements/quality/REQ-001-run-fast.md",
        "../actors/ACT-tester.md",
        "../../../core/use-case-model/actors/ACT-developer.md",
        "../domain-model/010-orders.md",
        "020-payments.md",
        "../journeys/JRN-001-first-run.md",
    ]
    for target in written:
        assert re.fullmatch(id_links.TARGET, target), target
    for target in (
        "domain-model/010-orders.md#order",
        "https://example.org/UC-001-run.md",
        "../../revalidations/2026-10-26-run.md",
        "../overview/README.md",
    ):
        assert not re.fullmatch(id_links.TARGET, target), target
