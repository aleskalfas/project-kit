"""software-analysis: the domain model's views, and each term's link to its section (#1817).

Held to software-analysis DEC-004:

- **the stamp** — `pkit analysis new view <slug> --number <digits> --explains <TERM-id>…`
  writes `domain-model/<number>-<slug>.md`, its id `VIEW-<slug>`, with `explains`, an
  anchor to each term it lists and one section for each, headed by the term's name. It
  writes each term's link to its section under the term's heading in the glossary, and
  refuses what a view may not explain (points 2, 4, 5 and 7);
- **the check, whatever any rule's status** — a view's file's name against its id, the
  terms it explains against its analysis, one view in force for each term, its term
  anchors equal to `explains`, no path anchor, and each term's link held equal to the
  view that explains it (points 4, 5 and 7);
- **the structure, where the format rule binds** — one section for each term `explains`
  lists, in its order, headed by its name, no two headings giving one slug, and each
  section's parts (point 2), with a project's own labels in the opening or each section
  and never a heading;
- **optional** — a project with no domain model fails nothing.
"""

from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path
from typing import Any

import pytest

from project_kit import document_parts
from project_kit.friction_validate import validate_friction
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    ANALYSIS_SET,
    DOMAIN_MODEL,
    GLOSSARY,
    STRUCTURES,
    VALIDATE,
    accepting_san,
    fill,
    front,
    installed,
    link,
    load_lib,
    new,
    prepare,
    run_script,
    stamped,
)

forms: Any
structure: Any
forms, structure = load_lib("forms", "structure")

#: The fixture's view, as the stamp names it.
VIEW = f"{DOMAIN_MODEL}/010-orders-and-payments.md"
VIEW_ID = "VIEW-orders-and-payments"

#: The link each term the fixture's view explains carries under its heading.
ORDER_LINK = (
    "Explained in [VIEW-orders-and-payments](domain-model/010-orders-and-payments.md#order)."
)
PAYMENT_LINK = (
    "Explained in [VIEW-orders-and-payments](domain-model/010-orders-and-payments.md#payment)."
)


def _domain(repo: AdopterRepo) -> None:
    """`prepare`, then three terms, and a view explaining two of them, stamped, filled and
    linked. Built once per session (`installed`)."""
    prepare(repo)
    for slug in ("order", "payment", "customer"):
        stamped(repo, "term", slug, "--name", slug, "--path", "src/run.py")
    explains = ("--explains", "TERM-order", "--explains", "TERM-payment")
    stamped(repo, "view", "orders-and-payments", "--number", "010", *explains)
    fill(repo)
    link(repo)


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch, then=_domain)


@pytest.fixture
def bare(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch)


def _validate(repo: AdopterRepo, *args: str) -> dict[str, Any]:
    completed = run_script(repo, VALIDATE, "--json", *args)
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def _found(document: dict[str, Any], severity: str = "error") -> list[tuple[str, str]]:
    return [
        (f["location"], f["message"]) for f in document["findings"] if f["severity"] == severity
    ]


def _read(repo: AdopterRepo, rel: str) -> str:
    return (repo.root / rel).read_text(encoding="utf-8")


def _edit(repo: AdopterRepo, rel: str, old: str, new_text: str) -> None:
    text = _read(repo, rel)
    assert old in text, (old, text)
    repo.write({rel: text.replace(old, new_text, 1)})


# --- the stamp (DEC-004 points 2, 4, 5 and 7) ------------------------------------------------


def test_a_view_is_stamped_with_its_terms_their_sections_and_their_links(
    project: AdopterRepo,
) -> None:
    """The view's file is named by its number and its slug, its id the slug alone. It lists
    the terms it explains, anchors each and no code, and holds one section for each,
    headed by the term's name. Each term links to its section, right below its heading."""
    assert front(project, VIEW) == {
        "id": VIEW_ID,
        "title": "Orders and payments",
        "status": "active",
        "explains": ["TERM-order", "TERM-payment"],
        "pkit": {"friction": {"anchors": {"artefact": ["TERM-order", "TERM-payment"]}}},
    }
    body = _read(project, VIEW).split("\n---\n", 1)[1]
    headings = [line for line in body.splitlines() if line.startswith("#")]
    assert headings == [f"# {VIEW_ID} — Orders and payments", "## Order", "## Payment"]
    # Each section opens with its link to its term, then its *Why*, then its explanation.
    order = body.split("## Order\n", 1)[1].split("\n## ", 1)[0].strip("\n").split("\n\n")
    assert order[0] == "Defined in [TERM-order](../glossary.md#term-order--order)."
    assert order[1].startswith("**Why:** A shop must know")
    assert order[2].startswith("An order is")
    glossary = _read(project, GLOSSARY)
    assert f"## TERM-order — order\n\n{ORDER_LINK}\n\n**Example:** " in glossary
    assert f"## TERM-payment — payment\n\n{PAYMENT_LINK}\n\n**Example:** " in glossary
    section = glossary.split("## TERM-customer — customer\n", 1)[1].split("\n## ", 1)[0]
    assert "Explained in" not in section  # a term no view explains carries no link
    # Filled, it passes the check with the format rule binding, and the core's friction pass.
    project.write(accepting_san(project))
    assert _found(_validate(project)) == []
    assert validate_friction(project.root).errors == ()


def test_the_stamp_heads_each_section_in_sentence_case(project: AdopterRepo) -> None:
    """A section's heading is its term's name with its first letter capitalized, the rest
    as the name writes it. The heading's slug is the name's, so the term's link names it,
    and the view passes the check where the format rule binds (DEC-004 points 2 and 7)."""
    stamped(project, "term", "line-item", "--name", "line item", "--path", "src/run.py")
    stamped(project, "term", "github-issue", "--name", "GitHub issue", "--path", "src/run.py")
    explains = ("--explains", "TERM-line-item", "--explains", "TERM-github-issue")
    stamped(project, "view", "lines", "--number", "020", *explains)
    view = f"{DOMAIN_MODEL}/020-lines.md"
    headings = [line for line in _read(project, view).splitlines() if line.startswith("## ")]
    assert headings == ["## Line item", "## GitHub issue"]
    glossary = _read(project, GLOSSARY)
    assert "Explained in [VIEW-lines](domain-model/020-lines.md#line-item)." in glossary
    assert "Explained in [VIEW-lines](domain-model/020-lines.md#github-issue)." in glossary
    assert "## TERM-line-item — line item\n" in glossary  # the name itself keeps its case
    fill(project)
    link(project)
    project.write(accepting_san(project))
    assert _found(_validate(project)) == []


def test_the_stamp_says_what_it_linked(project: AdopterRepo) -> None:
    completed = new(project, "view", "customers", "--number", "020", "--explains", "TERM-customer")
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines()[-2:] == [
        f"linked TERM-customer in {GLOSSARY} to its section (DEC-004 point 7)",
        f"stamped VIEW-customers at {DOMAIN_MODEL}/020-customers.md",
    ]
    link = "Explained in [VIEW-customers](domain-model/020-customers.md#customer)."
    assert f"## TERM-customer — customer\n\n{link}\n\n" in _read(project, GLOSSARY)


@pytest.mark.parametrize(
    ("args", "said"),
    [
        (("--number", "030"), "explains one term at least"),
        (("--number", "03a", "--explains", "TERM-customer"), "is not a number"),
        (("--number", "030", "--explains", "TERM-nothing"), "no term TERM-nothing"),
        (("--number", "030", "--explains", "TERM-order"), "VIEW-orders-and-payments explains it"),
        (
            ("--number", "030", "--explains", "TERM-customer", "--explains", "TERM-customer"),
            "is named twice",
        ),
        (("--number", "030", "--explains", "core:TERM-change"), "of its own analysis alone"),
        (("--number", "030", "--explains", "TERM-customer", "--title", "<Title>"), "<Title>"),
    ],
)
def test_the_stamp_refuses_what_a_view_may_not_explain(
    project: AdopterRepo, args: tuple[str, ...], said: str
) -> None:
    """One term at least, each once, each a term in force of its own analysis that no view
    in force explains yet (DEC-004 point 5); a number of digits (point 4). Refused, it
    writes nothing."""
    before = _read(project, GLOSSARY)
    completed = new(project, "view", "customers", *args)
    assert completed.returncode == 1, completed.stdout
    assert said in completed.stderr
    assert not (project.root / DOMAIN_MODEL / "030-customers.md").exists()
    assert _read(project, GLOSSARY) == before


def test_the_stamp_refuses_a_held_id_a_withdrawn_term_and_code(project: AdopterRepo) -> None:
    """A view's id is never used again, whatever its number. A view in force explains
    terms in force, and anchors no code: `new view` takes no `--path` (DEC-004 points 4
    and 5)."""
    completed = new(
        project, "view", "orders-and-payments", "--number", "090", "--explains", "TERM-customer"
    )
    assert (
        completed.returncode == 1 and "VIEW-orders-and-payments is held already" in completed.stderr
    )
    _edit(project, GLOSSARY, "  status: active\n  definition", "  status: withdrawn\n  definition")
    withdrawn = front(project, GLOSSARY)
    first = next(term for term, entry in withdrawn.items() if entry["status"] == "withdrawn")
    completed = new(project, "view", "lone", "--number", "030", "--explains", first)
    assert completed.returncode == 1 and "is withdrawn" in completed.stderr
    completed = new(project, "view", "lone", "--number", "030", "--path", "src/run.py")
    assert completed.returncode == 2 and "--path" in completed.stderr


# --- the check, whatever any rule's status (DEC-004 points 4, 5 and 7) ----------------------


def test_a_view_s_file_name_opens_with_its_number_and_gives_its_id(project: AdopterRepo) -> None:
    text = _read(project, VIEW)
    project.write({VIEW: None, f"{DOMAIN_MODEL}/orders-and-payments.md": text})
    (found,) = [f for f in _found(_validate(project)) if "opens with no number" in f[1]]
    assert found[0] == f"{DOMAIN_MODEL}/orders-and-payments.md"
    project.write(
        {f"{DOMAIN_MODEL}/orders-and-payments.md": None, f"{DOMAIN_MODEL}/020-orders.md": text}
    )
    messages = [m for _l, m in _found(_validate(project))]
    assert any(
        "its name is 020-orders.md, its front matter's id VIEW-orders-and-payments" in m
        for m in messages
    ), messages


def test_a_view_s_term_anchors_match_explains_and_it_anchors_no_code(project: AdopterRepo) -> None:
    _edit(
        project,
        VIEW,
        "      artefact:\n        - TERM-order\n        - TERM-payment\n",
        "      path:\n        - src/run.py\n      artefact:\n        - TERM-order\n",
    )
    messages = [m for location, m in _found(_validate(project)) if location.startswith(VIEW)]
    assert any("it anchors code (src/run.py)" in m for m in messages), messages
    assert any(
        "its term anchors (TERM-order) do not match its `explains` (TERM-order, TERM-payment)" in m
        and "anchor exactly [TERM-order, TERM-payment]" in m
        for m in messages
    ), messages


def test_each_term_is_explained_by_one_view_in_force(project: AdopterRepo) -> None:
    """A second view in force explaining a term is refused at its `explains`; withdrawn,
    it explains nothing, and the term links to the view in force (DEC-004 point 5)."""
    second = _read(project, VIEW).replace(VIEW_ID, "VIEW-payments")
    project.write({f"{DOMAIN_MODEL}/020-payments.md": second})
    found = [(location, m) for location, m in _found(_validate(project)) if "is explained by" in m]
    assert found == [
        (
            f"{DOMAIN_MODEL}/020-payments.md:/explains/0",
            f"TERM-order is explained by {VIEW_ID} too ({VIEW}): no two views in force explain "
            f"one term, so each explanation has one home — explain it in one of them, and take "
            f"it off the other's `explains`, anchors and sections (DEC-004 point 5)",
        ),
        (
            f"{DOMAIN_MODEL}/020-payments.md:/explains/1",
            f"TERM-payment is explained by {VIEW_ID} too ({VIEW}): no two views in force "
            f"explain one term, so each explanation has one home — explain it in one of them, "
            f"and take it off the other's `explains`, anchors and sections (DEC-004 point 5)",
        ),
    ]
    project.write(
        {f"{DOMAIN_MODEL}/020-payments.md": second.replace("status: active", "status: withdrawn")}
    )
    assert _found(_validate(project)) == []


def test_a_view_in_force_explains_terms_in_force_of_its_own_analysis(
    project: AdopterRepo,
) -> None:
    """The change that withdraws a term takes its section out of the view in force that
    explains it (DEC-004 point 5). A withdrawn view may still list it: it is history."""
    text = _read(project, GLOSSARY)
    withdrawn = re.sub(r"(TERM-payment:\n  name: payment\n  status: )active", r"\1withdrawn", text)
    assert withdrawn != text
    project.write({GLOSSARY: withdrawn})
    found = [(location, m) for location, m in _found(_validate(project))]
    assert (
        f"{VIEW}:/explains/1",
        f"term TERM-payment is withdrawn ({GLOSSARY}#TERM-payment): a view in force explains "
        f"only terms in force — take it off `explains`, its anchors and its section, or "
        f"withdraw the view too (DEC-004 point 5)",
    ) in found
    _edit(project, VIEW, "status: active", "status: withdrawn")
    # A withdrawn view explains nothing, so no term links to it.
    found = _found(_validate(project))
    assert [location for location, _m in found] == [
        f"{GLOSSARY}#TERM-order",
        f"{GLOSSARY}#TERM-payment",
    ], found
    assert all("and no view in force explains it" in m for _l, m in found), found


def test_a_term_s_link_is_held_to_the_view_that_explains_it(project: AdopterRepo) -> None:
    """The link names the view's file and the term's section, exactly as the stamp writes
    it: missing, written otherwise, twice, or left by a view renumbered, it is reported
    with the line to write (DEC-004 point 7)."""
    _edit(project, GLOSSARY, f"{ORDER_LINK}\n\n", "")
    (found,) = _found(_validate(project))
    assert found[0] == f"{GLOSSARY}#TERM-order"
    assert (
        "its section holds no link to it: a term links to the section of the view that "
        f"explains it, `{ORDER_LINK}`" in found[1]
    )
    _edit(
        project,
        "tech-docs/analysis/glossary.md",
        "## TERM-order — order\n",
        "## TERM-order — order\n\nSee [the view](domain-model/010-orders-and-payments.md).\n",
    )
    (found,) = _found(_validate(project))
    assert "as `See [the view](domain-model/010-orders-and-payments.md).`" in found[1]
    assert f"write `{ORDER_LINK}` in its place" in found[1]
    # A view renumbered is a moved file: each term's link names its new file.
    text = _read(project, VIEW)
    _edit(project, GLOSSARY, "See [the view](domain-model/010-orders-and-payments.md).", ORDER_LINK)
    project.write({VIEW: None, f"{DOMAIN_MODEL}/015-orders-and-payments.md": text})
    found = _found(_validate(project))
    assert [location for location, _m in found] == [
        f"{GLOSSARY}#TERM-order",
        f"{GLOSSARY}#TERM-payment",
    ], found
    assert "domain-model/015-orders-and-payments.md#order" in found[0][1]


# --- the structure, where the format rule binds (DEC-004 point 2) ----------------------------


def test_a_view_s_sections_match_explains_where_the_format_rule_binds(
    project: AdopterRepo,
) -> None:
    """Each section is headed by the name of the term `explains` lists in its place. The
    format rule is accepted as `SAN` ships it, so this binds where a set of the project's
    own selects the view, as the set install creates does."""
    _edit(project, VIEW, "## Payment\n", "## settlement\n")
    assert _found(_validate(project)) == []  # no set of the project's own selects it yet
    project.write(accepting_san(project))
    (found,) = _found(_validate(project))
    assert found[0] == VIEW
    assert (
        "the 2nd section is headed `settlement`, and `explains` lists TERM-payment in its "
        "place, whose name is `payment`" in found[1]
    )
    assert "head it `Payment`" in found[1]
    assert "(RS-SAN-001)" in found[1]
    # The term's name as running text writes it, in lower case, is no heading either.
    _edit(project, VIEW, "## settlement\n", "## payment\n")
    (found,) = _found(_validate(project))
    assert "the 2nd section is headed `payment`" in found[1]
    assert "in sentence case, its first letter capitalized" in found[1]
    assert "head it `Payment`" in found[1]


def test_a_view_s_parts_are_held_in_each_section(project: AdopterRepo) -> None:
    project.write(accepting_san(project))
    _edit(project, VIEW, "**Relations:**", "**Links:**")
    messages = [m for location, m in _found(_validate(project)) if location == VIEW]
    assert any(
        m.startswith("`**Relations:**` in the section `## Order` is missing") for m in messages
    ), messages
    assert len(messages) == 1, messages


def test_a_section_s_why_is_held_where_the_format_rule_binds(project: AdopterRepo) -> None:
    """A section with no *Why*, or whose *Why* runs into its explanation, is reported, and
    the message says where the part goes (DEC-004 point 2)."""
    text = _read(project, VIEW)
    why = next(line for line in text.splitlines() if line.startswith("**Why:**"))
    _edit(project, VIEW, f"{why}\n\n", "")
    link(project)  # the first mention of a term the *Why* held moves to the explanation
    assert _found(_validate(project)) == []  # no set of the project's own selects it yet
    project.write(accepting_san(project))
    messages = [m for location, m in _found(_validate(project)) if location == VIEW]
    assert len(messages) == 1, messages
    assert messages[0].startswith("`**Why:**` in the section `## Order` is missing"), messages
    assert "(RS-SAN-001)" in messages[0]
    project.write({VIEW: text.replace(f"{why}\n\n", f"{why}\n", 1)})
    messages = [m for location, m in _found(_validate(project)) if location == VIEW]
    assert len(messages) == 1, messages
    assert messages[0].startswith("the text before `**Attributes:**` in the section `## Order`")
    assert (
        "is missing, and it comes after the paragraph of `**Why:**`, a blank line" in (messages[0])
    )


def test_a_project_s_own_label_goes_in_the_opening_or_each_section_never_a_heading(
    project: AdopterRepo,
) -> None:
    """A project adds labels to a view's opening, or to each concept's section, and never a
    heading (DEC-004 point 2)."""
    rule = "RS-ANALYSIS-001"
    sets = accepting_san(project)
    set_text = (
        sets[ANALYSIS_SET].replace(
            "rules: {}\n",
            f'rules:\n  {rule}:\n    status: accepted\n    origin: {{why: "A reader asks."}}\n',
        )
        + f"\n## {rule} — A view says more\n\nA view says more.\n"
    )
    project.write({**sets, ANALYSIS_SET: set_text})
    added = (
        "pkit_schema: software-analysis:structures\nschema_version: 1\nkinds:\n"
        "  domain-model-view:\n    tighten:\n      - rule: RS-ANALYSIS-001\n        add:\n"
        "          - {id: examples, label: Examples, after: attributes, hint: An instance., "
        "example: Order 7., required: true}\n"
    )
    project.write({STRUCTURES: added})
    messages = [m for location, m in _found(_validate(project)) if location == VIEW]
    assert [m.split(" is missing")[0] for m in messages] == [
        "`**Examples:**` in the section `## Order`",
        "`**Examples:**` in the section `## Payment`",
    ], messages
    headed = added.replace("{id: examples,", "{id: examples, type: heading, level: 2,")
    project.write({STRUCTURES: headed})
    found = _found(_validate(project))
    assert any(
        location.startswith(STRUCTURES) and "'label' was expected" in m for location, m in found
    ), found


def test_a_project_with_no_domain_model_fails_nothing(bare: AdopterRepo) -> None:
    """The view kind is optional: terms with no view carry no link, and nothing asks for
    one (DEC-004 point 1)."""
    stamped(bare, "term", "order", "--name", "order", "--path", "src/run.py")
    fill(bare)
    bare.write(accepting_san(bare))
    document = _validate(bare)
    assert _found(document) == []
    assert "0 domain-model view(s)" in document["summary"][0]


# --- the pure parts --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "title",
    ["order", "Order line", "order-line", "Ordnung & Zahlung", "état payé", "1st step", "#!?", ""],
)
def test_a_heading_s_slug_is_the_backbone_s(title: str) -> None:
    """A term's link names its section by the slug the backbone makes of its heading
    (COR-050 point 2): the capability's copy of the rule says the same."""
    assert forms.heading_slug(title) == document_parts.heading_slug(title)


KINDS: dict[str, Any] = structure.read_kinds()

#: A view's body, filled: two sections, `Order` and `Payment`, each its term's name in
#: sentence case.
BODY = """# VIEW-orders-and-payments — Orders and payments

What ordering and paying cover.

## Order

**Why:** A shop must know what a customer asked for.

An order is what a customer asks for.

**Attributes:** Its lines.

**Relations:** One payment settles it.

**States:** None.

**Always true:** None.

## Payment

**Why:** A shop must know which orders are paid.

A payment settles an order.

**Attributes:** Its amount.

**Relations:** None.

**States:** None.

**Always true:** None.
"""

FIELDS = {"explains": ["TERM-order", "TERM-payment"]}
TITLES = {"TERM-order": "order", "TERM-payment": "payment"}


def _departures(
    body: str, fields: dict[str, Any] = FIELDS
) -> list[tuple[str, str, int | None, str | None]]:
    lines = list(enumerate(body.splitlines(), 1))
    return [
        (d.element.id, d.how, d.line, d.within)
        for d in structure.departures(
            lines, KINDS["domain-model-view"], fields=fields, titles=TITLES
        )
    ]


def test_a_filled_view_departs_from_nothing() -> None:
    assert _departures(BODY) == []


def test_the_headings_follow_explains_and_give_one_slug_each() -> None:
    """One section per term, in order, each headed by its name; and no two headings with
    one slug (DEC-004 point 2)."""
    swapped = {"explains": ["TERM-payment", "TERM-order"]}
    assert _departures(BODY, swapped) == [
        ("concept", "breaks-its-form", 5, None),
        ("concept", "breaks-its-form", 19, None),
    ]
    one = {"explains": ["TERM-order"]}
    assert _departures(BODY, one) == [("concept", "breaks-its-form", 19, None)]
    three = {"explains": ["TERM-order", "TERM-payment", "TERM-customer"]}
    assert _departures(BODY, three) == [("concept", "breaks-its-form", 19, None)]
    twice = BODY.replace("## Payment", "## order")
    assert ("concept", "breaks-its-form", 19, None) in _departures(
        twice, {"explains": ["TERM-order", "TERM-x"]}
    )


def test_each_heading_is_its_term_s_name_in_sentence_case() -> None:
    """The name as running text writes it, in lower case, breaks the form, as does a name
    in title case. A name whose first word holds a capital already stands as it is
    (DEC-004 point 2)."""
    assert _departures(BODY.replace("## Payment", "## payment")) == [
        ("concept", "breaks-its-form", 19, None)
    ]
    assert _departures(BODY.replace("## Order", "## ORDER")) == [
        ("concept", "breaks-its-form", 5, None)
    ]
    assert _departures(BODY.replace("## Payment", "##   Payment  ")) == []  # white space aside
    titles = {"TERM-order": "iPhone order", "TERM-payment": "payment"}
    proper = BODY.replace("## Order", "## iPhone order")
    lines = list(enumerate(proper.splitlines(), 1))
    kind = KINDS["domain-model-view"]
    assert structure.departures(lines, kind, fields=FIELDS, titles=titles) == []
    capitalized = list(enumerate(BODY.replace("## Order", "## IPhone order").splitlines(), 1))
    assert [
        (d.element.id, d.line)
        for d in structure.departures(capitalized, kind, fields=FIELDS, titles=titles)
    ] == [("concept", 5)]


@pytest.mark.parametrize(
    ("name", "heading"),
    [
        ("order", "Order"),
        ("decision record", "Decision record"),
        ("pull request on GitHub", "Pull request on GitHub"),
        ("GitHub issue", "GitHub issue"),
        ("iPhone app", "iPhone app"),
        ("état payé", "État payé"),
        ("3d model", "3d model"),
        ("ßx", "ßx"),
        ("", ""),
    ],
)
def test_sentence_case_capitalizes_the_first_letter_alone(name: str, heading: str) -> None:
    """The first letter capitalized, the rest as the name writes it, a name whose first
    word holds a capital standing as it is. The slug is always the name's, so a term's
    link names its section whatever the capital (DEC-004 points 2 and 7)."""
    assert forms.sentence_case(name) == heading
    assert forms.heading_slug(heading) == forms.heading_slug(name)


def test_a_section_is_held_to_its_parts_and_names_its_heading() -> None:
    empty = BODY.replace("**Attributes:** Its amount.", "**Attributes:**")
    assert _departures(empty) == [("attributes", "empty", 25, "Payment")]
    unexplained = BODY.replace("An order is what a customer asks for.\n", "")
    assert _departures(unexplained) == [("explanation", "missing", None, "Order")]
    assert _departures(BODY.split("## Order", 1)[0]) == [("concept", "missing", None, None)]
    no_opening = BODY.replace("What ordering and paying cover.\n", "")
    assert _departures(no_opening) == [("opening", "missing", None, None)]


WHY = "**Why:** A shop must know what a customer asked for.\n"


def test_each_section_opens_with_its_why_present_and_filled() -> None:
    """Each section's first part is its *Why*, what the concept is for, before its
    explanation: missing or empty, it departs, naming its section. It reads `None.` where
    no record gives the concept's reason (DEC-004 points 2 and 3)."""
    assert _departures(BODY.replace(WHY, "")) == [("why", "missing", None, "Order")]
    assert _departures(BODY.replace(WHY, "**Why:**\n")) == [("why", "empty", 7, "Order")]
    assert _departures(BODY.replace(WHY, "**Why:** None.\n")) == []
    after = BODY.replace(WHY, "").replace(
        "An order is what a customer asks for.\n", f"An order is what a customer asks for.\n\n{WHY}"
    )
    assert _departures(after) == [("explanation", "missing", None, "Order")]


def test_the_why_holds_its_paragraph_and_the_explanation_follows_it() -> None:
    """*Why* is a label listed right before an opening, so it holds its paragraph alone, up
    to the first blank line, and the explanation is the text below it. A *Why* written
    over two lines, or holding a fence or a comment with a blank line, is still one
    paragraph. One that runs into the explanation leaves the explanation missing, and one
    written below its label, after a blank line, leaves the *Why* empty (DEC-004 point 2)."""
    wrapped = BODY.replace(WHY, "**Why:** A shop must know\nwhat a customer asked for.\n")
    assert _departures(wrapped) == []
    fenced = BODY.replace(WHY, f"{WHY}```text\nan order\n\nits lines\n```\n")
    assert _departures(fenced) == []
    commented = BODY.replace(WHY, f"{WHY}<!-- a note\n\nof two paragraphs -->\n")
    assert _departures(commented) == []
    below = BODY.replace(WHY, "**Why:**\n\nA shop must know what a customer asked for.\n")
    assert _departures(below) == [("why", "empty", 7, "Order")]
    joined = BODY.replace(
        f"{WHY}\nAn order is", "**Why:** A shop must know what a customer asked for.\nAn order is"
    )
    assert _departures(joined) == [("explanation", "missing", None, "Order")]
    lines = list(enumerate(BODY.splitlines(), 1))
    kind = KINDS["domain-model-view"]
    section = dataclasses.replace(kind, sections=structure.section_elements(kind.sections[2]))
    held = {
        element.id: [row.text for row in part.rows if row.text.strip()]
        for element, part in structure.parts(lines[4:18], section)
    }
    assert held["why"] == []  # its text is on the label's line
    assert held["explanation"] == ["An order is what a customer asks for."]


project_structure: Any
(project_structure,) = load_lib("project_structure")

#: A project's own structures for the view kind, as `project/structures.yaml` holds them.
OWN = (
    "pkit_schema: software-analysis:structures\nschema_version: 1\nkinds:\n"
    "  domain-model-view:\n    relabel:\n      attributes: {label: Holds}\n"
    "    tighten:\n      - rule: RS-X-001\n        add:\n"
    "          - {id: examples, label: Examples, after: AFTER, hint: An instance., "
    "example: Order 7.}\n"
)


def _own(tmp_path: Path, after: str) -> Any:
    path = tmp_path / STRUCTURES
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(OWN.replace("AFTER", after), encoding="utf-8")
    return project_structure.read(tmp_path, KINDS)


def test_a_project_relabels_and_adds_to_each_section_of_a_view(tmp_path: Path) -> None:
    """A relabel and an addition after a part of a concept's section apply in each section
    (DEC-004 point 2). Each section opens with its *Why* and its explanation, so an
    addition placed after its heading or its *Why* is refused, naming the part to place it
    after."""
    own = _own(tmp_path, "attributes")
    assert own.problems == ()
    groups = own.of("domain-model-view")
    view = project_structure.tightened(
        project_structure.relabelled(KINDS["domain-model-view"], own), groups, groups
    )
    (concept,) = [e for e in view.sections if e.type == "repeated"]
    assert [(p.id, p.text) for p in concept.parts] == [
        ("why", "Why"),
        ("explanation", None),
        ("attributes", "Holds"),
        ("examples", "Examples"),
        ("relations", "Relations"),
        ("states", "States"),
        ("always-true", "Always true"),
    ]
    assert {"holds", "examples"} <= view.labels
    for after in ("concept", "why"):
        (problem,) = _own(tmp_path, after).problems
        assert "`why` and the opening text below its paragraph" in problem.message
        assert "name `explanation`" in problem.message
        assert problem.location.endswith("/tighten/0/add/0/after")
