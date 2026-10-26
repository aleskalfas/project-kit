"""Derived links set aside wherever friction compares a body (#1844, COR-050 point 5).

A fixture capability, `deriver`, declares on its place `notes` the form of the links
a command of its own would write there: a link to a glossary entry. Each test stands
up a real adopter repository, commits a base on `main`, branches `feature` off it and
makes real commits before running a check. They cover:

- **the reading** — `document_parts.links_set_aside` reads a link of the form in
  running text as its words alone, and leaves code, comments, headings, images and
  links of any other form as written;
- **the declaration** — read from a capability place, a target that does not compile
  declaring nothing and failing the package check, and each form matched on its own, so
  forms that would clash when joined pass the check and set their links aside (#1912);
- **the change check** — a change that only adds, removes or retargets such links
  asks nothing of what rests on the document, through an anchor on it whole, on a
  section, on its file or on a record; a word beside a link, or a link of another
  form, still asks; a capability that declares nothing sees links as content; the
  declaration is read at head; and an `updated` answer on links alone is a bump, in
  a block and in an answer file;
- **the whole-repository check** — the same, measured from a revalidation point, and
  the cost the record states: a declaration withdrawn sets nothing aside;
- **what is not friction's** — `pkit rule-sets altered` still lists an artefact
  changed only in such links, and `pkit friction resolve` advises the outcome the
  change check bears out;
- **software-analysis** — the forms its places declare are the link command's own,
  and what `pkit analysis link` writes, in the glossary, the views, the actors, the use
  cases, the journeys and the requirements, asks nothing of what rests on the linked
  documents.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from project_kit import friction_check as fc
from project_kit import friction_discovery as fd
from project_kit import friction_repository as fr
from project_kit import friction_resolve as fres
from project_kit import package_validate as pv
from project_kit.document_parts import links_set_aside
from project_kit.manifest import (
    ORIGIN_KIT_SHIPPED,
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
)
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import CAPABILITY, GLOSSARY, installed, link, load_lib
from tests.friction_documents import (
    CONFIG,
    POINTS,
    SOURCE,
    T1,
    T2,
    Timeline,
    document,
    friction_config,
    pointed_record,
)
from tests.test_answer_files import answer_path, answers, entry
from tests.test_software_analysis_term_links import (
    BODIES,
    JOURNEY,
    PLACE,
    VIEW,
    _domain,
    _kinds,
)

#: The documents here say each artefact's answers beside its anchors, and each write
#: takes them into answer files, as a change writes them (COR-062 point 1).
pytestmark = pytest.mark.usefixtures("answers_in_files")

DERIVER = "deriver"
NOTE = "notes/source.md"
RECORD = ".pkit/decisions/project/PRJ-900-pointed.md"
WHOLE, PART, FILE, ON_RECORD = "docs/whole.md", "docs/part.md", "docs/file.md", "docs/record.md"

#: The form of the links the fixture capability's command would write: a link to a
#: glossary entry, by a path to a glossary or by its anchor alone.
TARGET = r"(?:[^()\s:#]*/)?glossary\.md#term-[^()\s]*|#term-[^()\s]*"


def _form(target: str = TARGET) -> str:
    return f"      derived-links:\n        - target: '{target}'\n"


def declare_deriver(root: Path, forms: str | None = None) -> None:
    """The fixture capability `deriver`, registered once in the backbone manifest: its
    places `notes` and the project's records, each declaring `forms` — by default the one
    form `TARGET`; `""` declares none."""
    forms = _form() if forms is None else forms
    cap_dir = root / ".pkit" / "capabilities" / DERIVER
    cap_dir.mkdir(parents=True, exist_ok=True)
    (cap_dir / "package.yaml").write_text(
        f"schema_version: 2\ncomponent:\n  kind: capability\n  name: {DERIVER}\n"
        f"  version: 0.1.0\ndescription: Fixture capability declaring derived links.\n"
        f'requires_backbone: ">=0.1.0"\nfriction:\n  places:\n'
        f"    - path: notes\n{forms}    - path: .pkit/decisions/project\n{forms}",
        encoding="utf-8",
    )
    backbone = read_backbone_manifest(root)
    assert backbone is not None
    if any(c.name == DERIVER for c in backbone.components):
        return
    backbone.components.append(
        ComponentRegistryEntry(
            kind="capability",
            name=DERIVER,
            manifest=f".pkit/capabilities/{DERIVER}/manifest.yaml",
            origin=ORIGIN_KIT_SHIPPED,
        )
    )
    write_backbone_manifest(root, backbone)


def k(words: str, slug: str, *, form: str = "glossary.md#term-") -> str:
    """A link on `words` to the glossary entry `slug`, in the declared form by default."""
    return f"[{words}]({form}{slug})"


def note_body(
    lead: str = f"An {k('order', 'order--order')} waits for a payment.",
    why: str = f"A shop sends what a {k('customer', 'customer--customer')} asks for.",
) -> str:
    return f"# Notes\n\n{lead}\n\n## Why\n\n{why}\n"


def note(**overrides: Any) -> str:
    """`NOTE`, in the capability's place: anchored to the engine, revalidated at T1."""
    values: dict[str, Any] = {
        "anchors": {"path": ["src/core/**"]},
        "at": T1,
        "outcome": "updated",
        "body": note_body(),
    }
    values.update(overrides)
    return document("NOTE", **values)


def dependant(artefact_id: str, kind: str, value: str) -> str:
    """An artefact in the project's place `docs`, resting on `value`, revalidated at T1."""
    return document(
        artefact_id,
        anchors={kind: [value]},
        at=T1,
        outcome="unchanged",
        because="it says what the notes say",
    )


#: The record's points, point 1 holding a link of the declared form.
LINKED_POINTS = (
    ("1", "First", f"The first {k('order', 'order--order')} point."),
    *POINTS[1:],
)

BASE = {
    NOTE: note(),
    RECORD: pointed_record(LINKED_POINTS),
    WHOLE: dependant("whole", "artefact", "NOTE"),
    PART: dependant("part", "artefact", "NOTE#why"),
    FILE: dependant("file", "path", NOTE),
    ON_RECORD: document(
        "on-record",
        anchors={"record": ["PRJ-900", "PRJ-900#1"]},
        at=T1,
        outcome="unchanged",
        because="it says what the record says",
    ),
}

DEPENDANTS = (WHOLE, PART, FILE, ON_RECORD)

#: Only the links moved: one retargeted, one added and one taken out, in the notes and
#: in the record's point.
LINKS_MOVED = {
    NOTE: note(
        body=note_body(
            lead=(
                f"An {k('order', 'order--orders')} waits for a {k('payment', 'payment--payment')}."
            ),
            why="A shop sends what a customer asks for.",
        )
    ),
    RECORD: pointed_record(
        (("1", "First", f"The first {k('order', 'order--orders')} point."), *POINTS[1:])
    ),
}


@pytest.fixture
def repo(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    adopter = make_adopter_repo()
    declare_deriver(adopter.root)
    return adopter


def _start(adopter: AdopterRepo, files: dict[str, str] | None = None) -> None:
    """Commit the base state on `main` and branch `feature` off it."""
    adopter.write({CONFIG: friction_config(places=("docs",)), **SOURCE, **BASE, **(files or {})})
    adopter.commit("base", files=None)
    adopter.checkout("feature", create=True)


def _friction(result: fc.ChangeCheck) -> list[str]:
    """The locations the change check asks an answer of, each once, sorted."""
    asked = (f.location for f in result.findings if f.kind is fc.FindingKind.FRICTION)
    return sorted({location for location in asked if location is not None})


def _run(adopter: AdopterRepo) -> fc.ChangeCheck:
    return fc.run_change_check(adopter.root, "main")


# --- the reading --------------------------------------------------------------------------


def _glossary(target: str) -> bool:
    return re.fullmatch(TARGET, target) is not None


def test_a_link_of_the_form_in_running_text_reads_as_its_words() -> None:
    payment = k("payment", "payment--payment", form="#term-")
    text = f"An {k('order', 'order--order')} and a {payment}."
    assert links_set_aside(text, _glossary) == "An order and a payment."


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("A [source](https://example.org/order) says so.", id="another target"),
        pytest.param("An ![order](glossary.md#term-order--order) drawn.", id="an image"),
        pytest.param("Write `[order](glossary.md#term-order--order)` so.", id="a code span"),
        pytest.param("<!-- [order](glossary.md#term-order--order) -->", id="a comment"),
        pytest.param("## The [order](glossary.md#term-order--order)", id="a heading"),
        pytest.param("```\n[order](glossary.md#term-order--order)\n```", id="fenced code"),
        pytest.param("An [order][1] by reference.", id="a reference link"),
    ],
)
def test_a_link_outside_running_text_or_of_another_form_is_left_as_written(text: str) -> None:
    assert links_set_aside(text, _glossary) == text


def test_the_lines_and_the_headings_of_a_body_stay_where_they_were() -> None:
    body = note_body()
    read = links_set_aside(body, _glossary)
    lead, why = "An order waits for a payment.", "A shop sends what a customer asks for."
    assert read == f"# Notes\n\n{lead}\n\n## Why\n\n{why}\n"
    assert read.count("\n") == body.count("\n")


# --- the declaration ----------------------------------------------------------------------


def test_a_capability_place_declares_its_derived_links(repo: AdopterRepo) -> None:
    repo.write({CONFIG: friction_config(places=("docs",)), NOTE: note()})
    discovery = fd.discover_artefacts(repo.root)
    (artefact,) = [a for a in discovery.artefacts if a.path == NOTE]
    assert artefact.aside == fd.SetAside((TARGET,))
    assert discovery.aside_of(NOTE) == artefact.aside
    (place,) = [p for p in discovery.settings.places if p.value == "notes"]
    (form,) = place.derived_links
    assert form.pointer == "/friction/places/0/derived-links/0"


def test_a_project_place_declares_no_derived_links(repo: AdopterRepo) -> None:
    repo.write({CONFIG: friction_config(places=("docs",)), WHOLE: BASE[WHOLE]})
    discovery = fd.discover_artefacts(repo.root)
    (artefact,) = [a for a in discovery.artefacts if a.path == WHOLE]
    assert not artefact.aside


def test_a_target_that_does_not_compile_fails_the_package_check_and_declares_nothing(
    repo: AdopterRepo,
) -> None:
    declare_deriver(repo.root, _form("glossary[.md") + "        - target: 'kept'\n")
    repo.write({CONFIG: friction_config(places=("docs",))})
    errors = [
        (finding.path, finding.message)
        for report in pv.validate_installed_packages(repo.root).reports
        if report.file == repo.root / f".pkit/capabilities/{DERIVER}/package.yaml"
        for finding in report.findings
        if finding.severity is pv.Severity.ERROR
    ]
    assert [path for path, _message in errors] == [
        "/friction/places/0/derived-links/0/target",
        "/friction/places/1/derived-links/0/target",
    ]
    assert "is no regular expression" in errors[0][1]
    (place, _records) = [p for p in fd.read_friction_settings(repo.root).places if p.is_capability]
    assert [form.target for form in place.derived_links] == ["kept"]


@pytest.mark.parametrize(
    ("forms", "aside", "kept"),
    [
        pytest.param(
            (r"glossary\.md#(?P<slug>term-[a-z-]+)", r"#(?P<slug>term-[a-z-]+)"),
            ("glossary.md#term-order", "#term-payment"),
            "notes.md#term-order",
            id="one group name in two forms",
        ),
        pytest.param(
            (r"(a+)-\1", r"(b+)-\1"),
            ("aa-aa", "b-b"),
            "a-b",
            id="a numbered back-reference in each form",
        ),
        pytest.param(
            (r"(?i)glossary\.md#term-[a-z-]+", r"#term-[a-z-]+"),
            ("GLOSSARY.md#term-order", "#term-payment"),
            "#TERM-payment",
            id="a flag set for one whole form",
        ),
    ],
)
def test_each_form_is_matched_on_its_own(
    forms: tuple[str, str], aside: tuple[str, str], kept: str
) -> None:
    """Forms that each compile may clash when joined into one pattern (#1912): each is
    matched on its own, so a group, a back-reference or a flag means what it means alone."""
    assert all(fd.compiles(form) is None for form in forms)
    text = f"[one]({aside[0]}), [two]({aside[1]}) and [three]({kept})."
    assert fd.SetAside(forms).body(text) == f"one, two and [three]({kept})."


def test_forms_that_clash_when_joined_pass_the_package_check_and_set_links_aside(
    repo: AdopterRepo,
) -> None:
    """Two forms on one place that name the same group: the package check passes them, and
    the change check reads a links-only edit as before, asking nothing."""
    clashing = (
        "      derived-links:\n"
        r"        - target: '(?:[^()\s:#]*/)?glossary\.md#(?P<slug>term-[^()\s]*)'" + "\n"
        r"        - target: '#(?P<slug>term-[^()\s]*)'" + "\n"
    )
    declare_deriver(repo.root, clashing)
    _start(repo)
    assert [
        finding.path
        for report in pv.validate_installed_packages(repo.root).reports
        for finding in report.findings
        if finding.severity is pv.Severity.ERROR
    ] == []
    repo.commit("move the links", LINKS_MOVED)
    assert _friction(_run(repo)) == []


# --- the change check ---------------------------------------------------------------------


def test_a_links_only_edit_asks_nothing_of_what_rests_on_the_document(repo: AdopterRepo) -> None:
    """Whole, on a section, on the file and on a record whole or on its point."""
    _start(repo)
    repo.commit("move the links", LINKS_MOVED)
    assert _friction(_run(repo)) == []


def test_without_the_derived_links_the_same_edit_asks_each_dependant(repo: AdopterRepo) -> None:
    """A component that declares no form sees no change of behaviour: links are content."""
    declare_deriver(repo.root, "")
    _start(repo)
    repo.commit("move the links", LINKS_MOVED)
    assert _friction(_run(repo)) == sorted(DEPENDANTS)


def test_a_word_changed_beside_a_link_still_asks(repo: AdopterRepo) -> None:
    _start(repo)
    lead = f"An {k('order', 'order--order')} awaits a payment."
    repo.commit("reword the lead", {NOTE: note(body=note_body(lead=lead))})
    # The section `Why` is as it was, and so is the record.
    assert _friction(_run(repo)) == [FILE, WHOLE]


@pytest.mark.parametrize(
    "why",
    [
        pytest.param(
            f"A shop sends what a {k('customer', 'customer', form='https://example.org/')} asks "
            "for.",
            id="another target",
        ),
        pytest.param(
            "A shop sends what a `[customer](glossary.md#term-customer--customers)` asks for.",
            id="in a code span",
        ),
        pytest.param(
            "A shop sends what a ![customer](glossary.md#term-customer--customer) asks for.",
            id="an image",
        ),
    ],
)
def test_a_link_the_command_would_not_write_still_asks(repo: AdopterRepo, why: str) -> None:
    _start(repo)
    repo.commit("a hand-written link", {NOTE: note(body=note_body(why=why))})
    assert _friction(_run(repo)) == [FILE, PART, WHOLE]


def test_the_declaration_is_read_at_head(repo: AdopterRepo) -> None:
    """The change that brings the declaration, with links moved, asks nothing: the base is
    read under head's forms, though it declared none."""
    declare_deriver(repo.root, "")
    _start(repo)
    declare_deriver(repo.root)
    repo.commit("declare the links, and move them", LINKS_MOVED)
    assert _friction(_run(repo)) == []


def test_an_updated_revalidation_on_links_alone_is_a_bump(repo: AdopterRepo) -> None:
    _start(repo)
    moved = note(body=LINKS_MOVED[NOTE].split("\n---\n", 1)[1].strip() + "\n", at=T2)
    repo.commit("move the links, stamp the notes", {NOTE: moved})
    bumps = [f for f in _run(repo).findings if f.kind is fc.FindingKind.BUMP]
    assert [f.location for f in bumps] == [NOTE]
    assert "the content did not change" in bumps[0].message


def test_an_updated_answer_file_on_links_alone_is_a_bump_too(repo: AdopterRepo) -> None:
    """The comparison holds in both homes of an answer (COR-062)."""
    bare = document("NOTE", anchors={"path": ["src/core/**"]}, body=note_body())
    _start(repo, {NOTE: bare, answer_path("a0"): answers(entry(NOTE, at=T1))})
    moved_body = LINKS_MOVED[NOTE].split("\n---\n", 1)[1].strip() + "\n"
    repo.commit(
        "move the links, answer the notes",
        {
            NOTE: document("NOTE", anchors={"path": ["src/core/**"]}, body=moved_body),
            answer_path("x"): answers(entry(NOTE, at=T2, outcome="updated", read=("a0",))),
        },
    )
    result = _run(repo)
    assert [(f.kind, f.location) for f in result.findings] == [(fc.FindingKind.BUMP, NOTE)]
    (answer,) = result.answers
    assert answer.status is fc.AnswerStatus.BUMP


# --- the whole-repository check -----------------------------------------------------------


@pytest.fixture
def timeline(make_adopter_repo: MakeAdopterRepo) -> Timeline:
    adopter = make_adopter_repo()
    declare_deriver(adopter.root)
    return Timeline(adopter)


def _states(result: fr.RepositoryCheck) -> dict[str, str]:
    return {
        report.location: report.state.value
        for report in result.artefact_reports
        if report.location in DEPENDANTS
    }


def test_links_moved_since_a_revalidation_point_are_no_debt(timeline: Timeline) -> None:
    timeline.start(BASE, friction_config(places=("docs",)))
    timeline.commit("move the links", LINKS_MOVED)
    result = fr.run_repository_check(timeline.adopter.root)
    assert set(_states(result).values()) == {"current"}
    timeline.commit("reword the lead", {NOTE: note(body=note_body(lead="An order awaits."))})
    states = _states(fr.run_repository_check(timeline.adopter.root))
    assert (states[WHOLE], states[FILE], states[PART]) == ("stale", "stale", "current")


def test_a_declaration_withdrawn_leaves_the_links_moved_while_it_stood_as_debt(
    timeline: Timeline,
) -> None:
    """The cost COR-050 point 5 states: the latest commit's declaration is read, and a
    withdrawn one sets nothing aside."""
    timeline.start(BASE, friction_config(places=("docs",)))
    timeline.commit("move the links", LINKS_MOVED)
    declare_deriver(timeline.adopter.root, "")
    timeline.commit("withdraw the declaration", None)
    states = _states(fr.run_repository_check(timeline.adopter.root))
    assert states == {WHOLE: "stale", PART: "stale", FILE: "stale", ON_RECORD: "stale"}


# --- what is not friction's: the alteration, and the resolver's advice --------------------


def test_a_links_only_edit_still_alters_the_artefact_for_its_rules(repo: AdopterRepo) -> None:
    """`pkit rule-sets altered` pairs as before: COR-050's content, nothing set aside, so the
    rule-set reviewer still judges a change to derived links alone (COR-057 point 1)."""
    _start(repo)
    base_commit = repo.head()
    repo.commit("move the links", LINKS_MOVED)
    pairing = fc.pair_artefacts(
        fd.discover_artefacts(repo.root, tree=fc.CommitTree(repo.root, base_commit)),
        fd.discover_artefacts(repo.root),
        fc.read_diff(repo.root, base_commit),
    )
    altered = {a.after.location for a in pairing.altered if a.after is not None}
    assert {NOTE, RECORD} <= altered


def test_the_resolver_advises_unchanged_where_only_links_differ(repo: AdopterRepo) -> None:
    """`pkit friction resolve` names the outcome the change check bears out (COR-050 point
    5): links moved alone change no content, so it advises `unchanged`."""
    repo.write({CONFIG: friction_config(places=("docs",)), NOTE: note()})
    (found,) = [f for f in fd.discover_artefacts(repo.root).files if f.path == NOTE]
    parse = fres._parsed  # pyright: ignore[reportPrivateUsage] -- the reading under test
    owe = fres._owed  # pyright: ignore[reportPrivateUsage] -- the advice under test
    (base,), _ = parse(NOTE, found, note())
    (resolved,), _ = parse(NOTE, found, LINKS_MOVED[NOTE])
    assert owe(resolved, base).outcome == fres.UNCHANGED
    (reworded,), _ = parse(NOTE, found, note(body=note_body(lead="An order awaits.")))
    assert owe(reworded, base).outcome == fres.UPDATED


# --- software-analysis --------------------------------------------------------------------


def _declared(place: str) -> list[str]:
    from ruamel.yaml import YAML

    package = YAML(typ="safe").load((CAPABILITY / "package.yaml").read_text(encoding="utf-8"))
    (found,) = [p for p in package["friction"]["places"] if p["path"] == place]
    return [form["target"] for form in found.get("derived-links", ())]


def test_software_analysis_declares_the_link_commands_own_form() -> None:
    """The glossary's form is the command's target; every other place's, its branch by a
    path, since only the glossary links an entry by its anchor alone: the views, the actors,
    the use cases, the journeys and the three kinds of requirement. The views' places also
    declare the form of their closing section's links (#2104). Every place declares the
    form of the links of ids last (#2109)."""
    links, id_links = load_lib("links", "id_links")
    entry_form: str = links._ENTRY
    ids: str = id_links.TARGET
    for place in ("glossary.md", "*/glossary.md"):
        assert _declared(place) == [entry_form, ids]
    by_path = entry_form.split("|", 1)[0]
    for place in ("domain-model", "*/domain-model/**"):
        assert _declared(place) == [by_path, links.CLOSING_TARGET, ids]
    for folder in (
        "use-case-model/actors",
        "use-case-model/use-cases",
        "use-case-model/journeys",
        "requirements/quality",
        "requirements/functional",
        "requirements/constraints",
    ):
        assert _declared(folder) == [by_path, ids], folder
        assert _declared(f"*/{folder}/**") == [by_path, ids], folder


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    repo = installed(make_adopter_repo, monkeypatch, then=_domain)
    repo.commit("the analysis, unlinked")
    repo.checkout("feature", create=True)
    return repo


def test_what_the_link_command_writes_asks_nothing_of_what_rests_on_it(
    project: AdopterRepo,
) -> None:
    """`pkit analysis link` adds links in the glossary's entries and in the view: the view
    rests on the terms it explains, and nothing asks it an answer."""
    before = {rel: (project.root / rel).read_text(encoding="utf-8") for rel in (GLOSSARY, VIEW)}
    link(project)
    assert all((project.root / rel).read_text(encoding="utf-8") != before[rel] for rel in before)
    assert _friction(fc.run_change_check(project.root, "main")) == []


@pytest.fixture
def parted(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    repo = installed(make_adopter_repo, monkeypatch, then=_kinds)
    repo.commit("the analysis, unlinked")
    repo.checkout("feature", create=True)
    return repo


def test_links_written_in_the_four_kinds_ask_nothing_of_what_rests_on_them(
    parted: AdopterRepo,
) -> None:
    """`pkit analysis link` adds links in an actor, the use cases, a journey and the
    requirements, which rest on one another: nothing asks an answer, the links of the
    journey's steps to its use cases included (#2109). A word changed beside a link in a
    use case still asks the journey through it."""
    before = {rel: (parted.root / rel).read_text(encoding="utf-8") for rel in BODIES}
    link(parted)
    assert all((parted.root / rel).read_text(encoding="utf-8") != before[rel] for rel in before)
    journey = (parted.root / JOURNEY).read_text(encoding="utf-8")
    assert "1. [UC-001](../use-cases/UC-001-place-order.md) — Place an order" in journey
    assert _friction(fc.run_change_check(parted.root, "main")) == []
    text = (parted.root / PLACE).read_text(encoding="utf-8")
    reworded = text.replace("chooses goods", "picks goods", 1)
    assert reworded != text
    parted.write({PLACE: reworded})
    assert _friction(fc.run_change_check(parted.root, "main")) == [JOURNEY]


def test_a_word_changed_in_a_linked_entry_still_asks_the_view(project: AdopterRepo) -> None:
    link(project)
    text = (project.root / GLOSSARY).read_text(encoding="utf-8")
    reworded = text.replace("places an order, and pays", "places an order, then pays", 1)
    assert reworded != text
    project.write({GLOSSARY: reworded})
    assert _friction(fc.run_change_check(project.root, "main")) == [VIEW]
