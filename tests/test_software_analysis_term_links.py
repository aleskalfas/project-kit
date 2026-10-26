"""software-analysis: an analysis's terms cross-linked, and one name for one concept (#1841).

Held to software-analysis DEC-004 point 7 and DEC-001 points 1 and 2:

- **the links** — in an analysis that keeps a domain model, `pkit analysis link` opens
  each view section with its link to its term, and links the first mention of each term
  in each section to the term's glossary entry: in a view's opening and its sections,
  and in each glossary entry below its heading, never in a term's own section or entry,
  and never in front matter or the glossary's head;
- **the safeguards** — noun forms only, a plural only where a term declares one; whole
  words; the longest mention first; code, fences, headings, bold labels, comments and
  links skipped; a phrase a term lists in `other-senses` never links it; and an escape
  for one mention;
- **the check** — `pkit analysis validate` reports a link missing, extra or stale, and
  names the command, whatever any rule's status; an analysis with no domain model is
  never read for them;
- **across analyses** — a term the head lists from an analysis the repository holds
  links to its entry there, by a path from the file;
- **the four kinds** — each part of an actor's, a use case's, a journey's and a
  requirement's body takes the links once, as the project's own structures label its
  parts; a goal, a journey's step lines and an actor's first sentence, which say a datum
  again, stay plain, and a link written there is extra;
- **a view's closing section** — each view ends with what is built on its concepts: the
  use cases, journeys and requirements whose bodies link a term it explains, written by
  the command and the stamp, held by the check, and no part of the view's structure
  (#2104);
- **one name, one concept** — validation refuses two terms in force of one name, a
  plural among the names, and a name another term replaces, within an analysis and
  across the analyses it builds on, two of those included, whatever any rule's status.
"""

from __future__ import annotations

import dataclasses
import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    ACTORS,
    ANALYSIS,
    CONSTRAINTS,
    DOMAIN_MODEL,
    FUNCTIONAL,
    GLOSSARY,
    JOURNEYS,
    QUALITY,
    SA,
    SETTINGS_TEXT,
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

VIEW = f"{DOMAIN_MODEL}/010-orders-and-payments.md"


def _view(linked: bool) -> str:
    """The view's body below its front matter, as a writer fills it or, `linked`, as `pkit
    analysis link` writes it: an opening, and one section for each term it explains, each
    opening with the link the stamp writes, then its *Why*, which no record gives here.
    Each safeguard meets a mention here."""

    def k(text: str, slug: str) -> str:
        return f"[{text}](../glossary.md#term-{slug}--{slug})" if linked else text

    return "\n".join(
        [
            "# VIEW-orders-and-payments — Orders and payments",
            "",
            "The concepts of ordering goods and paying for them. <!-- pkit:not-the-term -->"
            f"Order in the sense of a sequence is no {k('order', 'order')} here: an order is "
            f"what a {k('customer', 'customer')} places, and a {k('payment', 'payment')} "
            "settles it.",
            "",
            "```mermaid",
            "classDiagram",
            "  accTitle: Orders and payments",
            "  accDescr: A payment settles an order.",
            "  Order --> Payment",
            "```",
            "",
            "## Order",
            "",
            "Defined in [TERM-order](../glossary.md#term-order--order).",
            "",
            "**Why:** None.",
            "",
            f"An order is what a {k('customer', 'customer')} asks the shop to send. Orders "
            f"wait for a {k('payment method', 'payment-method')}, and a "
            f"{k('payment', 'payment')} settles them.",
            "",
            "**Attributes:** Its lines, and the customer's address.",
            "",
            "**Relations:** One payment or more settle it.",
            "",
            "**States:** None.",
            "",
            "**Always true:** None.",
            "",
            "## Payment",
            "",
            "Defined in [TERM-payment](../glossary.md#term-payment--payment).",
            "",
            "**Why:** None.",
            "",
            f"A payment settles {k('orders', 'order')}. Customer service answers for a "
            f"{k('customer', 'customer')}, and a pre-order or an order-form holds no order. "
            "`customer` in code, and [the docs](https://example.org/customer), link elsewhere.",
            "",
            "**Attributes:** Its amount.",
            "",
            "**Relations:** None.",
            "",
            "**States:** None.",
            "",
            "**Always true:** None.",
            "",
        ]
    )


#: The sentence that opens a view's closing section, as the command writes it.
CLOSING_OPENING = (
    "Each concept below lists the use cases, journeys and requirements whose text links its term."
)

#: The view's closing section where nothing in the analysis links a term it explains, as
#: the command writes it (DEC-004 point 7).
CLOSING_NONE = (
    f"\n## What is built on these concepts\n\n{CLOSING_OPENING}\n\n"
    "**Order:** None.\n\n**Payment:** None.\n"
)

VIEW_BODY = _view(linked=False)
VIEW_LINKED = _view(linked=True) + CLOSING_NONE

#: Each term's entry below its heading, as a writer fills it, by its id: the example and
#: the distinctions, the term's link to its section left as the stamp wrote it.
ENTRIES = {
    "TERM-order": (
        "a customer places an order, and pays for it with a payment method.",
        "\n\n- **Payment:** what settles an order, never the order itself.",
    ),
    "TERM-customer": ("the customer's orders wait for a payment.", " None."),
    "TERM-payment": ("None.", " None."),
    "TERM-payment-method": ("a card is a payment method that makes a payment.", " None."),
}

#: The same, as `pkit analysis link` writes them.
ENTRIES_LINKED = {
    "TERM-order": (
        "a [customer](#term-customer--customer) places an order, and pays for it with a "
        "[payment method](#term-payment-method--payment-method).",
        "\n\n- **Payment:** what settles an order, never the order itself.",
    ),
    "TERM-customer": (
        "the customer's [orders](#term-order--order) wait for a [payment](#term-payment--payment).",
        " None.",
    ),
    "TERM-payment": ("None.", " None."),
    "TERM-payment-method": (
        "a card is a payment method that makes a [payment](#term-payment--payment).",
        " None.",
    ),
}


def _set_entries(repo: AdopterRepo, entries: dict[str, tuple[str, str]]) -> None:
    text = (repo.root / GLOSSARY).read_text(encoding="utf-8")
    for term, (example, distinctions) in entries.items():
        text = re.sub(
            rf"(## {term} — [^\n]*\n(?:\n[^*\n][^\n]*\n)?\n\*\*Example:\*\*) [^\n]*\n\n"
            rf"\*\*Distinctions:\*\*(?:[^\n]*|(?:\n\n- [^\n]*)+)",
            lambda m, e=example, d=distinctions: f"{m[1]} {e}\n\n**Distinctions:**{d}",
            text,
            count=1,
        )
    repo.write({GLOSSARY: text})


def _domain(repo: AdopterRepo) -> None:
    """Four terms, `order` with its plural and `customer` with a phrase in another sense,
    and a view explaining two of them, filled as `VIEW_BODY` and `ENTRIES` say, and not
    linked. Built once per session (`installed`)."""
    prepare(repo)
    for slug, name in (
        ("order", "order"),
        ("payment", "payment"),
        ("customer", "customer"),
        ("payment-method", "payment method"),
    ):
        stamped(repo, "term", slug, "--name", name, "--path", "src/run.py")
    explains = ("--explains", "TERM-order", "--explains", "TERM-payment")
    stamped(repo, "view", "orders-and-payments", "--number", "010", *explains)
    fill(repo)
    text = (repo.root / GLOSSARY).read_text(encoding="utf-8")
    text = text.replace("  name: order\n", "  name: order\n  noun-forms: [orders]\n", 1)
    text = text.replace(
        "  name: customer\n", "  name: customer\n  other-senses: [customer service]\n", 1
    )
    text = re.sub(
        r"(  name: payment\n  status: active\n  definition: )[^\n]*",
        r"\1sum a customer pays to settle an order",
        text,
    )
    repo.write({GLOSSARY: text})
    _set_entries(repo, ENTRIES)
    view = (repo.root / VIEW).read_text(encoding="utf-8")
    front = view.split("\n---\n", 1)[0]
    repo.write({VIEW: f"{front}\n---\n\n{VIEW_BODY}"})


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


def _validate(repo: AdopterRepo) -> list[tuple[str, str]]:
    completed = run_script(repo, VALIDATE, "--json")
    assert completed.returncode == 0, completed.stderr
    return [
        (f["location"], f["message"])
        for f in json.loads(completed.stdout)["findings"]
        if f["severity"] == "error"
    ]


def _read(repo: AdopterRepo, rel: str) -> str:
    return (repo.root / rel).read_text(encoding="utf-8")


def _body(repo: AdopterRepo, rel: str) -> str:
    return _read(repo, rel).split("\n---\n", 1)[1].lstrip("\n")


def _entry(repo: AdopterRepo, term: str) -> tuple[str, str]:
    """A term's example and distinctions, as the glossary holds them."""
    section = _read(repo, GLOSSARY).split(f"## {term} — ", 1)[1].split("\n## ", 1)[0]
    example = section.split("**Example:** ", 1)[1].split("\n\n**Distinctions:**", 1)[0]
    distinctions = section.split("**Distinctions:**", 1)[1].rstrip("\n")
    return example, distinctions


# --- the stamp writes each section's link to its term --------------------------------------


def test_the_stamp_opens_each_section_with_its_link_to_its_term(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Right below its heading, each section links to its term's entry, by the slug of the
    entry's heading, `<id> — <name>` (DEC-004 point 7)."""
    repo = installed(make_adopter_repo, monkeypatch)
    stamped(repo, "term", "line-item", "--name", "line item", "--path", "src/run.py")
    stamped(repo, "view", "lines", "--number", "020", "--explains", "TERM-line-item")
    body = _body(repo, f"{DOMAIN_MODEL}/020-lines.md")
    assert (
        "## Line item\n\nDefined in [TERM-line-item](../glossary.md#term-line-item--line-item)."
        "\n\n**Why:** <!-- pkit:hint " in body
    )


# --- the command writes the links ------------------------------------------------------------


def test_the_command_links_each_first_mention_with_every_safeguard(project: AdopterRepo) -> None:
    """Each first mention in a section links to its term's entry; the safeguards keep a
    link off the rest (DEC-004 point 7). The view and the glossary's entries come out
    exactly as `VIEW_LINKED` and `ENTRIES_LINKED` show them, and a term's definition, in
    front matter, stays plain."""
    before = _read(project, GLOSSARY).split("\n---\n", 1)[0]
    completed = link(project)
    assert completed.stdout.splitlines() == [
        f"linked {GLOSSARY} (5 link(s) written or mended)",
        f"linked {VIEW} (9 link(s) written or mended)",
    ]
    assert _body(project, VIEW) == VIEW_LINKED
    for term, (example, distinctions) in ENTRIES_LINKED.items():
        assert _entry(project, term) == (example, distinctions), term
    assert _read(project, GLOSSARY).split("\n---\n", 1)[0] == before
    # Linked, the analysis passes the check, and a second run writes nothing.
    assert _validate(project) == []
    assert link(project).stdout.strip() == "Every link is as it should be; nothing written."


def test_the_check_reports_each_link_missing_extra_or_stale_and_names_the_command(
    project: AdopterRepo,
) -> None:
    """Whatever any rule's status, a link the command would write and the text lacks, one
    it would not write, and one whose target is stale are each reported, with the line,
    and mended by the command (DEC-004 point 7)."""
    found = _validate(project)
    assert len(found) == 14, "\n".join(f"{where} | {m}" for where, m in found)
    assert all(
        m.endswith("run `pkit analysis link`, which writes the links (DEC-004 point 7)")
        for _l, m in found
    )
    assert (
        VIEW,
        "the view ends with no section `## What is built on these concepts`: the view's one "
        "closing section, at its end, lists under each concept it explains each use case, "
        "journey and requirement in force of its analysis that links the concept's term — run "
        "`pkit analysis link`, which writes the links (DEC-004 point 7)",
    ) in found
    assert (
        VIEW,
        "line 33: `customer` is the first mention of TERM-customer in its section, and takes "
        "a link to its entry, `../glossary.md#term-customer--customer` — run `pkit analysis "
        "link`, which writes the links (DEC-004 point 7)",
    ) in found
    link(project)
    view = _read(project, VIEW)
    stale = view.replace(
        "[orders](../glossary.md#term-order--order)", "[orders](../glossary.md#term-old--old)"
    )
    extra = stale.replace(
        "One payment or more", "One [payment](../glossary.md#term-payment--payment) or more"
    )
    defined = extra.replace(
        "Defined in [TERM-payment](../glossary.md#term-payment--payment).\n\n", ""
    )
    project.write({VIEW: defined})
    messages = sorted(m.split(" — ")[0] for _l, m in _validate(project))
    assert messages == [
        "line 37: `payment` links to a glossary entry, `../glossary.md#term-payment--payment`, "
        "where no link belongs: only the first mention of a term in force in each section "
        "takes one, never in its own section, nor after `<!-- pkit:not-the-term -->`",
        "line 43 heads a section with no link to its term: each section opens with "
        "`Defined in [TERM-payment](../glossary.md#term-payment--payment).`",
        "line 47: `orders` links to `../glossary.md#term-old--old`, and its term's entry is "
        "`../glossary.md#term-order--order`",
    ], messages
    link(project)
    assert _body(project, VIEW) == VIEW_LINKED
    assert _validate(project) == []


def test_a_link_to_a_withdrawn_term_or_written_by_hand_is_held_as_the_command_s(
    project: AdopterRepo,
) -> None:
    """A link to a glossary entry is the command's, whoever wrote it: on a second mention,
    or to a term withdrawn since, it is extra, and the command takes it out."""
    link(project)
    glossary = _read(project, GLOSSARY)
    withdrawn = glossary.replace(
        "  name: payment method\n  status: active", "  name: payment method\n  status: withdrawn"
    )
    project.write({GLOSSARY: withdrawn})
    found = [(where, m) for where, m in _validate(project) if "where no link belongs" in m]
    assert {where for where, _m in found} == {VIEW, f"{GLOSSARY}#TERM-order"}, found
    link(project)
    assert "#term-payment-method--payment-method" not in _read(project, VIEW)
    assert _validate(project) == []


def test_a_section_s_link_to_its_term_is_no_content_of_its_explanation(
    project: AdopterRepo,
) -> None:
    """Where the format rule binds, a section whose explanation holds only its link to its
    term lacks its explanation (DEC-004 point 7)."""
    link(project)
    project.write(accepting_san(project))
    assert _validate(project) == []
    view = _read(project, VIEW).replace(
        "An order is what a [customer](../glossary.md#term-customer--customer) asks the shop "
        "to send. Orders wait for a [payment method](../glossary.md#term-payment-method--"
        "payment-method), and a [payment](../glossary.md#term-payment--payment) settles "
        "them.\n\n",
        "",
    )
    project.write({VIEW: view})
    found = [m for where, m in _validate(project) if where == VIEW and "is missing" in m]
    assert any("in the section `## Order` is missing" in m for m in found), found


def test_a_writer_s_line_that_opens_with_defined_in_is_left_as_written(
    project: AdopterRepo,
) -> None:
    """Only a section's first line, in the form the command writes, leading from the
    section's own term, is its link to its term. A sentence that opens with `Defined in [`
    and such a line in fenced code are the writer's: the check reports neither, and the
    command writes the section's link above the sentence and leaves both as written."""
    link(project)
    own = "Defined in [TERM-order](../glossary.md#term-order--order)."
    prose = "Defined in [ISO 4217](https://www.iso.org/iso-4217), an order's currency is a code."
    fenced = f"```markdown\n{own}\n```\n\n"
    attributes = "**Attributes:** Its amount."
    view = _read(project, VIEW).replace(own, prose, 1).replace(attributes, fenced + attributes, 1)
    project.write({VIEW: view})
    found = [m.split(" — ")[0] for _l, m in _validate(project)]
    assert len(found) == 1 and "heads a section with no link to its term" in found[0], found
    link(project)
    expected = VIEW_LINKED.replace(own, f"{own}\n\n{prose}", 1)
    assert _body(project, VIEW) == expected.replace(attributes, fenced + attributes, 1)
    assert _validate(project) == []
    assert link(project).stdout.strip() == "Every link is as it should be; nothing written."


#: Each section's link to its term, as the command writes it, and what the check says of
#: one in that form where none belongs.
OWN_ORDER = "Defined in [TERM-order](../glossary.md#term-order--order)."
OWN_PAYMENT = "Defined in [TERM-payment](../glossary.md#term-payment--payment)."
NOT_BELONGING = "links the section to a term where no such link belongs"


def test_a_later_line_in_the_form_of_a_section_s_link_is_extra(project: AdopterRepo) -> None:
    """A line in the command's form below a section's own link, naming another term, is a
    link to a glossary entry written by hand where the command writes none: the check
    reports it as extra, and the command takes it out (DEC-004 point 7)."""
    link(project)
    amount = "**Attributes:** Its amount."
    project.write({VIEW: _read(project, VIEW).replace(amount, f"{OWN_ORDER}\n\n{amount}", 1)})
    found = [m.split(" — ")[0] for _l, m in _validate(project)]
    assert len(found) == 1 and f"{NOT_BELONGING}, `{OWN_ORDER}`" in found[0], found
    link(project)
    assert _body(project, VIEW) == VIEW_LINKED
    assert _validate(project) == []


def test_two_sections_naming_each_other_s_terms_are_each_mended(project: AdopterRepo) -> None:
    """Two sections whose lines in the command's form name each other's terms hold no link
    to their own: the check reports each missing, and each line naming the other term
    extra, and the command writes each section's own and takes the other out."""
    link(project)
    swapped = _read(project, VIEW).replace(OWN_ORDER, "\0").replace(OWN_PAYMENT, OWN_ORDER)
    project.write({VIEW: swapped.replace("\0", OWN_PAYMENT)})
    found = sorted(m.split(" — ")[0].split(" ", 2)[2] for _l, m in _validate(project))
    assert len(found) == 4, found
    assert [m for m in found if m.startswith("heads a section with no link")] == [
        f"heads a section with no link to its term: each section opens with `{own}`"
        for own in (OWN_ORDER, OWN_PAYMENT)
    ], found
    assert sorted(m for m in found if m.startswith(NOT_BELONGING)) == sorted(
        f"{NOT_BELONGING}, `{own}`: a section's one link to its term is its first line below "
        "its heading, to its own term while that term is in force"
        for own in (OWN_ORDER, OWN_PAYMENT)
    ), found
    link(project)
    assert _body(project, VIEW) == VIEW_LINKED
    assert _validate(project) == []
    assert link(project).stdout.strip() == "Every link is as it should be; nothing written."


def test_an_analysis_with_no_domain_model_takes_no_link(bare: AdopterRepo) -> None:
    """A glossary with no view beside it is never linked to its terms nor held, a link
    written in it by hand included (DEC-004 point 7). It names no artefact by its id, so
    the links of ids write nothing either (DEC-001 point 14)."""
    stamped(bare, "term", "order", "--name", "order", "--path", "src/run.py")
    stamped(bare, "term", "payment", "--name", "payment", "--path", "src/run.py")
    fill(bare)
    hand = "a [payment](#term-payment--payment) settles an order."
    _set_entries(bare, {"TERM-order": (hand, " None.")})
    before = _read(bare, GLOSSARY)
    completed = link(bare)
    assert completed.stdout.strip() == "Every link is as it should be; nothing written."
    assert _read(bare, GLOSSARY) == before
    assert _validate(bare) == []


# --- the matching, read alone -----------------------------------------------------------------


links: Any
(links,) = load_lib("links")


def _vocabulary(*terms: Any) -> Any:
    return links.Vocabulary(tuple(terms), {t.id: links._forms(t) for t in terms})


def _linked(text: str, own: str | None = None, *terms: Any) -> str:
    vocabulary = _vocabulary(*terms)
    return links.section(text, own, vocabulary, "glossary.md", 1)[0]


#: The typographer's apostrophe, U+2019.
TYPOGRAPHERS = chr(0x2019)

CHANGE = links.Term("TERM-change", "change", "glossary.md")
CHANGE_CHECK = links.Term("TERM-change-check", "change check", "glossary.md")
RECORD = links.Term("TERM-record", "record", "glossary.md")
DECISION_RECORD = links.Term(
    "TERM-decision-record", "decision record", "glossary.md", ("decision records",)
)
HEAD = links.Term("TERM-head", "head", "glossary.md", (), ("glossary's head",))
GLOSSARY_TERM = links.Term("TERM-glossary", "glossary", "glossary.md")


@pytest.mark.parametrize(
    ("text", "linked"),
    [
        # The longest first: a longer name wins where both start together.
        (
            "A change check reads a change.",
            "A [change check](#term-change-check--change-check) reads a "
            "[change](#term-change--change).",
        ),
        # A plural only where declared, and never a verb form.
        (
            "It changes the decision records.",
            "It changes the [decision records](#term-decision-record--decision-record).",
        ),
        # A name across a line break is one mention.
        ("A decision\nrecord.", "A [decision\nrecord](#term-decision-record--decision-record)."),
        # A phrase in another sense never links its term; another term inside it may.
        (
            "The glossary's head moves the head.",
            "The [glossary](#term-glossary--glossary)'s head moves the [head](#term-head--head).",
        ),
        # A phrase is matched as a mention is: its first letter in either case, and an
        # apostrophe of either kind.
        (
            f"Glossary{TYPOGRAPHERS}s head, then the head.",
            f"[Glossary](#term-glossary--glossary){TYPOGRAPHERS}s head, then the "
            "[head](#term-head--head).",
        ),
        # Headings, bold labels, code, fences, comments and links are skipped.
        ("### A change\n\n**Change:** `change`", "### A change\n\n**Change:** `change`"),
        ("```\nchange\n```\n<!-- change -->", "```\nchange\n```\n<!-- change -->"),
        (
            "[a change](https://x.org) and <https://x.org/change>",
            "[a change](https://x.org) and <https://x.org/change>",
        ),
        # The escape takes one mention out; the next counts as the first.
        (
            "<!-- pkit:not-the-term --> change, then a change.",
            "<!-- pkit:not-the-term --> change, then a [change](#term-change--change).",
        ),
        # Whole words only, and an apostrophe joins nothing.
        (
            "re-change, change/check, change_x; the change's",
            "re-change, change/check, change_x; the [change](#term-change--change)'s",
        ),
    ],
)
def test_a_mention_is_read_with_its_safeguards(text: str, linked: str) -> None:
    terms = (CHANGE, CHANGE_CHECK, RECORD, DECISION_RECORD, HEAD, GLOSSARY_TERM)
    assert _linked(text, None, *terms) == linked


@pytest.mark.parametrize(
    "phrase",
    [
        "change",
        "Change check",
        "glossary's head",
        f"n{TYPOGRAPHERS}s",
        "a",
        "x y",
        "über",
        "co-author",
        "decision\trecords",
    ],
)
def test_a_text_without_a_phrase_s_needle_is_not_searched_and_nothing_else_changes(
    phrase: str,
) -> None:
    """A text is searched for a phrase only where it holds the phrase's needle: the longest
    run of it matched as written, past its first letter, within one word and with no
    apostrophe. The mentions found are the ones the phrase's pattern finds in any text:
    the first letter in either case, an apostrophe of either kind, any white space
    between the words, whole words only (#2025)."""
    texts = [
        "",
        "A change; the Change check, change-checks and changes.",
        f"The Glossary{TYPOGRAPHERS}s head and the glossary's\nhead, not glossarys head.",
        f"N's, n{TYPOGRAPHERS}s and an's.",
        "a x  y, X\ny and xy.",
        "Über and über, Uber.",
        "A co-author, Co-author and coauthor.",
        "Decision records, decision\nrecords and decision-records.",
    ]
    needle = links._needle(phrase)
    for text in texts:
        found = [m.span() for m in links._found(phrase, text)]
        assert found == [m.span() for m in links._pattern(phrase).finditer(text)], text
        if needle not in text:
            assert found == []
    assert links._needle("glossary's head") == "lossary"
    assert links._needle("a") == ""


def test_a_term_is_never_linked_in_its_own_section_and_its_name_consumes_its_words() -> None:
    """The section's own term takes no link, and a shorter term inside it takes none
    either: `record` is never linked inside `decision record`."""
    assert _linked(
        "A decision record is a record.", "TERM-decision-record", DECISION_RECORD, RECORD
    ) == ("A decision record is a [record](#term-record--record).")


def test_an_actor_s_name_holds_no_mention_of_a_term_only_part_of_it() -> None:
    """An actor named by its name uses no concept: a term whose name is only part of an
    actor's name takes no link inside it, and its next mention counts as the first. A term
    whose name is an actor's whole name is still mentioned by it (DEC-004 point 7)."""
    component = links.Term("TERM-component", "component", "glossary.md")
    vocabulary = links.Vocabulary(
        (component, RECORD),
        {component.id: ("component",), RECORD.id: ("record",)},
        ("Component author", "Record"),
    )
    text = "The component author writes a component, and a record."
    assert links.section(text, None, vocabulary, "glossary.md", 1)[0] == (
        "The component author writes a [component](#term-component--component), and a "
        "[record](#term-record--record)."
    )


def test_a_name_two_terms_share_links_neither() -> None:
    """Validation refuses the pair; until it is mended, neither term is linked by the name
    they share, ignoring case, and each keeps the names it holds alone."""
    twin = links.Term("TERM-change-2", "Change", "other/glossary.md", ("change sets",))
    assert links.matched((CHANGE, twin)) == {CHANGE.id: (), twin.id: ("change sets",)}
    vocabulary = links.Vocabulary((CHANGE, twin), links.matched((CHANGE, twin)))
    assert links.section("a change", None, vocabulary, "glossary.md", 1)[0] == "a change"


def _definitions(lines: list[str], owners: list[str], wanted: Sequence[str | None]) -> Any:
    return links.with_definitions(lines, links.view_sections(lines, 0)[1:], owners, wanted)


def _defined(term: str, anchor: str | None = None) -> str:
    return f"Defined in [{term}](../glossary.md#{anchor or term.lower() + '--' + term[5:]})."


def test_the_command_writes_mends_and_takes_out_a_section_s_link_to_its_term() -> None:
    """A section with no link to its term gets one right below its heading; a stale one is
    rewritten in its place; one to a term no longer wanted is taken out, with a blank line
    beside it. A second pass finds nothing (DEC-004 point 7)."""
    stale = _defined("TERM-payment", "term-payment--old")
    lines = ["# V", "", "## Order", "", "An order.", "", "## Payment", "", stale, "", "Paid."]
    lines += ["", "## Gone", "", _defined("TERM-gone"), "", "Gone."]
    owners = ["TERM-order", "TERM-payment", "TERM-gone"]
    wanted = [_defined("TERM-order"), _defined("TERM-payment"), None]
    out, found = _definitions(lines, owners, wanted)
    assert out == [
        *("# V", "", "## Order", "", _defined("TERM-order"), "", "An order.", ""),
        *("## Payment", "", _defined("TERM-payment"), "", "Paid.", ""),
        *("## Gone", "", "Gone."),
    ]
    assert found == [
        (links.MISSING, 3, None, _defined("TERM-order")),
        (links.STALE, 9, stale, _defined("TERM-payment")),
        (links.EXTRA, 15, _defined("TERM-gone"), None),
    ]
    assert _definitions(out, owners, wanted) == (out, [])


def test_a_line_that_opens_with_defined_in_is_the_section_s_link_only_at_its_top() -> None:
    """Only the section's first line that is not blank, in the command's form, leading
    from its own term, is its link to its term. A sentence that opens with `Defined in [`
    and the line in fenced code are the writer's, left as written; a line in the
    command's form leading from another term is extra, and taken out; and a section that
    holds no link of its own gets one right below its heading."""
    prose = "Defined in [ISO 4217](https://www.iso.org/iso-4217), a currency is a code."
    fence = ["```markdown", _defined("TERM-payment"), "```"]
    lines = ["# V", "", "## Currency", "", prose, "", "## Order", "", _defined("TERM-order")]
    lines += ["", prose, "", "```", _defined("TERM-order"), "```", ""]
    lines += ["## Payment", "", *fence, "", "## Refund", "", _defined("TERM-payment"), ""]
    owners = ["TERM-currency", "TERM-order", "TERM-payment", "TERM-refund"]
    wanted = [_defined(term) for term in owners]
    out, found = _definitions(lines, owners, wanted)
    assert [(how, number) for how, number, *_rest in found] == [
        (links.MISSING, 3),
        (links.MISSING, 17),
        (links.MISSING, 23),
        (links.EXTRA, 25),
    ]
    assert out == [
        *("# V", "", "## Currency", "", wanted[0], "", prose, ""),
        *("## Order", "", _defined("TERM-order"), "", prose, "", "```", _defined("TERM-order")),
        *("```", "", "## Payment", "", wanted[2], "", *fence, ""),
        *("## Refund", "", wanted[3], ""),
    ]
    assert _definitions(out, owners, wanted) == (out, [])


def _front(repo: AdopterRepo, old: str, new_text: str) -> None:
    text = _read(repo, GLOSSARY)
    assert old in text, old
    repo.write({GLOSSARY: text.replace(old, new_text, 1)})


def _cut(message: str) -> str:
    """A finding's message up to its reason."""
    for reason in (": one name means", ": a replaced name", ": each phrase"):
        message = message.split(reason)[0]
    return message


def test_no_two_terms_of_an_analysis_share_a_name(project: AdopterRepo) -> None:
    """Whatever any rule's status, two terms in force of one name are refused, ignoring
    case and counting a noun form as a name, and so is a name another term replaces. Each
    `other-senses` phrase holds one of its term's names, and more (DEC-001 point 1)."""
    link(project)
    assert _validate(project) == []
    _front(project, "  name: payment method\n", "  name: Order\n")
    _front(
        project,
        "  name: customer\n",
        "  name: customer\n  noun-forms: [orders]\n  replaces: [buyer]\n",
    )
    _front(
        project,
        "  other-senses: [customer service]\n",
        "  other-senses: [customer service, help desk, customer]\n",
    )
    _front(project, "  name: payment\n", "  name: buyer\n")
    found = [(where, _cut(m)) for where, m in _validate(project) if "DEC-001 point 1" in m]
    assert sorted(found) == sorted(
        [
            (
                f"{GLOSSARY}#TERM-payment-method:/name",
                "its name, Order, is the name of TERM-order too",
            ),
            (
                f"{GLOSSARY}#TERM-order:/noun-forms/0",
                "its noun form, orders, is the noun form of TERM-customer too",
            ),
            (f"{GLOSSARY}#TERM-payment:/name", "its name, buyer, is a name TERM-customer replaces"),
            (
                f"{GLOSSARY}#TERM-customer:/other-senses/1",
                "the phrase help desk holds none of its names, its name or a noun form",
            ),
            (
                f"{GLOSSARY}#TERM-customer:/other-senses/2",
                "the phrase customer is one of its names alone, so no such mention of it would "
                "be linked",
            ),
        ]
    ), found
    # A withdrawn term holds no name.
    _front(project, "  name: Order\n  status: active", "  name: Order\n  status: withdrawn")
    assert not any("TERM-payment-method:/name" in where for where, _m in _validate(project))


# --- across analyses (DEC-001 point 2; DEC-004 point 7) ---------------------------------------

SETTINGS = f"{SA.as_posix()}/project/config.yaml"
CORE_GLOSSARY = f"{ANALYSIS}/core/glossary.md"
BILLING_GLOSSARY = f"{ANALYSIS}/billing/glossary.md"
BILLING_VIEW = f"{ANALYSIS}/billing/domain-model/010-bills.md"


def _example(repo: AdopterRepo, rel: str, term: str, example: str) -> None:
    text = (repo.root / rel).read_text(encoding="utf-8")
    changed = re.sub(
        rf"(## {term} — [^\n]*\n(?:\n[^*\n][^\n]*\n)?\n\*\*Example:\*\*) [^\n]*",
        lambda m: f"{m[1]} {example}",
        text,
        count=1,
    )
    assert changed != text
    repo.write({rel: changed})


def _three(repo: AdopterRepo) -> None:
    """Three analyses: the core's, shipping's, and billing's, which builds on both. The
    core holds `order` and `ledger`, shipping `parcel`, and billing `bill`, which a view
    explains. Billing's glossary's head lists the core's `order`. Built once per session."""
    prepare(repo)
    repo.write(
        {
            SETTINGS: (
                SETTINGS_TEXT + "analyses:\n"
                "  - {component: core, folder: core}\n"
                "  - {component: shipping, folder: shipping}\n"
                "  - component: billing\n    folder: billing\n    builds-on:\n"
                "      - {analysis: core}\n      - {analysis: shipping}\n"
            )
        }
    )
    for analysis, slug in (
        ("core", "order"),
        ("core", "ledger"),
        ("shipping", "parcel"),
        ("billing", "bill"),
    ):
        stamped(repo, "term", slug, "--name", slug, "--analysis", analysis, "--path", "src/run.py")
    explains = ("--explains", "TERM-bill", "--analysis", "billing")
    stamped(repo, "view", "bills", "--number", "010", *explains)
    fill(repo)
    head = (
        "builds-on:\n  - analysis: core\n    version: 1.0.0\n"
        "    terms:\n      - {id: TERM-order, name: order}\n"
    )
    text = (repo.root / BILLING_GLOSSARY).read_text(encoding="utf-8")
    repo.write({BILLING_GLOSSARY: text.replace("---\n", f"---\n{head}", 1)})
    _example(
        repo,
        BILLING_GLOSSARY,
        "TERM-bill",
        "a bill asks for the order's price, and the ledger records it.",
    )
    view = (repo.root / BILLING_VIEW).read_text(encoding="utf-8")
    view = re.sub(
        r"(# VIEW-bills — [^\n]*\n\n)[^\n]*", r"\1A bill asks a customer to pay for an order.", view
    )
    repo.write({BILLING_VIEW: view})


@pytest.fixture
def three(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch, then=_three)


def test_a_listed_term_links_to_its_entry_in_the_analysis_the_repository_holds(
    three: AdopterRepo,
) -> None:
    """A term the head lists from an analysis the configuration lists links to its entry
    there, by a path from the file; a term the head does not list takes no link, and an
    analysis with no domain model, the core's, takes none (DEC-004 point 7)."""
    core_before = _read(three, CORE_GLOSSARY)
    link(three)
    assert (
        "a bill asks for the [order](../core/glossary.md#term-order--order)'s price, and the "
        "ledger records it." in _read(three, BILLING_GLOSSARY)
    )
    assert (
        "A [bill](../glossary.md#term-bill--bill) asks a customer to pay for an "
        "[order](../../core/glossary.md#term-order--order)." in _read(three, BILLING_VIEW)
    )
    assert _read(three, CORE_GLOSSARY) == core_before
    assert [f for f in _validate(three) if "DEC-004 point 7" in f[1]] == []


def test_no_term_takes_a_name_of_an_analysis_it_builds_on(three: AdopterRepo) -> None:
    """A term never takes the name of a term of an analysis it builds on, whether its head
    lists that term or not; and no two analyses it builds on share a name, which is
    reported at its glossary's head (DEC-001 point 2)."""
    link(three)
    text = _read(three, BILLING_GLOSSARY).replace("  name: bill\n", "  name: Ledger\n", 1)
    three.write({BILLING_GLOSSARY: text})
    found = dict(_validate(three))
    assert found[f"{BILLING_GLOSSARY}#TERM-bill:/name"].startswith(
        "its name, Ledger, is the name of core:TERM-ledger: a term never takes the name of a "
        "term of an analysis it builds on, whether its head lists that term or not"
    )
    shipping = f"{ANALYSIS}/shipping/glossary.md"
    three.write({BILLING_GLOSSARY: text.replace("  name: Ledger\n", "  name: bill\n", 1)})
    renamed = _read(three, shipping).replace("  name: parcel\n", "  name: order\n", 1)
    three.write({shipping: renamed})
    found = dict(_validate(three))
    assert found[f"{BILLING_GLOSSARY}:/builds-on"].startswith(
        "two analyses it builds on hold one name: the name of core:TERM-order, and the name "
        "of shipping:TERM-parcel"
    )


def test_a_link_leads_by_a_path_from_the_file_that_holds_it() -> None:
    term = links.Term("TERM-adapter", "adapter", "tech-docs/analysis/core/glossary.md")
    assert term.target("tech-docs/analysis/core/glossary.md") == "#term-adapter--adapter"
    assert term.target("tech-docs/analysis/core/domain-model/010-x.md") == (
        "../glossary.md#term-adapter--adapter"
    )
    assert term.target("tech-docs/analysis/billing/glossary.md") == (
        "../core/glossary.md#term-adapter--adapter"
    )


# --- an actor, a use case, a journey and a requirement (DEC-004 point 7) ----------------------

ACTOR_FILE = f"{ACTORS}/ACT-shopper.md"
PLACE = f"{USE_CASES}/UC-001-place-order.md"
PAY = f"{USE_CASES}/UC-002-pay-order.md"
JOURNEY = f"{JOURNEYS}/JRN-001-first-order.md"
QUICK = f"{QUALITY}/REQ-001-settle-quickly.md"
ONCE = f"{FUNCTIONAL}/REQ-002-settle-once.md"
NETWORK = f"{CONSTRAINTS}/REQ-003-card-network.md"

#: The actor's summary, the first sentence of its opening.
SHOPPER_SUMMARY = "A customer who places an order and pays for it."


def _bodies(linked: bool) -> dict[str, str]:
    """Each of the four kinds' artefacts' body below its front matter, as a writer fills it
    or, `linked`, as `pkit analysis link` writes it. Every one lies two folders below the
    glossary. A goal, a journey's step lines and the actor's first sentence say a datum
    again, and stay plain. Every other part links each term's first mention in it."""

    def k(text: str, slug: str) -> str:
        return f"[{text}](../../glossary.md#term-{slug}--{slug})" if linked else text

    def case(case_id: str, slug: str) -> str:
        """A use case's id in a journey, linked to its file (DEC-001 point 14)."""
        return f"[{case_id}](../use-cases/{case_id}-{slug}.md)" if linked else case_id

    order, customer = k("order", "order"), k("customer", "customer")
    payment, method = k("payment", "payment"), k("payment method", "payment-method")
    return {
        ACTOR_FILE: "\n".join(
            [
                "# ACT-shopper — Shopper",
                "",
                f"{SHOPPER_SUMMARY} Each {order} waits for a {payment}.",
                "",
                f"**Occasions:** Whenever the {customer} wants goods, once a {method} is chosen.",
                "",
                "**Context:** None.",
                "",
            ]
        ),
        PLACE: "\n".join(
            [
                "# UC-001 — Place an order",
                "",
                "**Goal:** Place an order and pay for it with my payment method.",
                "",
                "**Other actors:** None.",
                "",
                f"**Preconditions:** The {customer} holds a {method}.",
                "",
                "**Assumptions:** None.",
                "",
                f"**Trigger:** The {customer} asks to place an {order}.",
                "",
                "**Main path:**",
                "",
                f"1. The {customer} chooses goods, and the system opens an {order}.",
                f"2. The system asks for a {payment}, and the customer's payment settles the "
                "order.",
                "",
                "**Variants:**",
                "",
                f"- **2a.** No {payment} arrives. The system keeps the {order} open, and the use "
                "case ends.",
                "",
                f"**Postconditions:** A {payment} settles the {order}.",
                "",
                "**Minimal guarantees:** None.",
                "",
            ]
        ),
        PAY: "\n".join(
            [
                "# UC-002 — Pay for an order",
                "",
                "**Goal:** Pay for my order.",
                "",
                "**Other actors:** None.",
                "",
                "**Preconditions:** None.",
                "",
                "**Assumptions:** None.",
                "",
                f"**Trigger:** The {customer} opens the {order}.",
                "",
                "**Main path:**",
                "",
                f"1. The system takes the {payment}.",
                "",
                "**Variants:** None.",
                "",
                f"**Postconditions:** The {order} is paid.",
                "",
                "**Minimal guarantees:** None.",
                "",
            ]
        ),
        JOURNEY: "\n".join(
            [
                "# JRN-001 — Place and pay for a first order",
                "",
                "**Goal:** Place my first order and pay for it.",
                "",
                "**Steps:**",
                "",
                f"1. {case('UC-001', 'place-order')} — Place an order",
                f"2. {case('UC-002', 'pay-order')} — Pay for an order",
                f"   - **Needs from step 1 (UC-001):** the {order} the {customer} placed. An "
                f"order left unplaced takes no {payment}.",
                "",
                "**Variants:** None.",
                "",
                f"**Postconditions:** The {customer}'s first {order} is settled, and no other "
                "orders wait.",
                "",
                "**Minimal guarantees:** None.",
                "",
            ]
        ),
        QUICK: "\n".join(
            [
                "# REQ-001 · Quality · Settle a payment quickly",
                "",
                f"**Verified by:** A timing test pays for an {order}, and fails if the {payment} "
                "takes over a second.",
                "",
                "**Rationale:** None.",
                "",
            ]
        ),
        ONCE: "\n".join(
            [
                "# REQ-002 · Functional · Settle each order once",
                "",
                "**Verified by:** None.",
                "",
                f"**Rationale:** A {customer} charged twice for one {order} asks for a refund.",
                "",
            ]
        ),
        NETWORK: "\n".join(
            [
                "# REQ-003 · Constraint · Keep each payment method on the card network",
                "",
                "**Verified by:** None.",
                "",
                f"**Imposed by:** The card network holds each {method}, and no design may copy it.",
                "",
            ]
        ),
    }


BODIES = _bodies(linked=False)
BODIES_LINKED = _bodies(linked=True)


def _kinds(repo: AdopterRepo) -> None:
    """`_domain`, then an actor, two use cases, a journey through them and a requirement of
    each kind, their bodies as `BODIES` gives them, and not linked. Built once per session
    (`installed`)."""
    _domain(repo)
    stamped(repo, "actor", "shopper", "--name", "Shopper", "--path", "src/run.py")
    actor = ("--actor", "ACT-shopper")
    stamped(repo, "use-case", "place-order", "--title", "Place an order", *actor)
    stamped(repo, "use-case", "pay-order", "--title", "Pay for an order", *actor)
    steps = ("--step", "UC-001", "--step", "UC-002")
    title = ("--title", "Place and pay for a first order")
    stamped(repo, "journey", "first-order", *title, *actor, *steps)
    for kind, slug, named in (
        ("quality-requirement", "settle-quickly", "Settle a payment quickly"),
        ("functional-requirement", "settle-once", "Settle each order once"),
        ("constraint", "card-network", "Keep each payment method on the card network"),
    ):
        stamped(repo, kind, slug, "--title", named, *actor)
    fill(repo)
    for rel, body in BODIES.items():
        front = _read(repo, rel).split("\n---\n", 1)[0]
        if rel == ACTOR_FILE:
            front = re.sub(r"\nsummary: [^\n]*", f'\nsummary: "{SHOPPER_SUMMARY}"', front)
        repo.write({rel: f"{front}\n---\n\n{body}"})


@pytest.fixture
def kinds(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch, then=_kinds)


def test_the_command_links_each_part_of_an_actor_a_use_case_a_journey_and_a_requirement(
    kinds: AdopterRepo,
) -> None:
    """Each part of the four kinds' bodies is a section: the first mention of each term in
    it links to the term's entry, by a path from the file. A goal, a journey's step lines
    and an actor's first sentence, which gives its summary, stay plain, and so does front
    matter (DEC-004 point 7). The analysis then passes the check, the format rule accepted
    included, and a second run writes nothing."""
    fronts = {rel: _read(kinds, rel).split("\n---\n", 1)[0] for rel in BODIES}
    link(kinds)
    for rel, body in BODIES_LINKED.items():
        assert _body(kinds, rel) == body, rel
        assert _read(kinds, rel).split("\n---\n", 1)[0] == fronts[rel], rel
    assert _validate(kinds) == []
    kinds.write(accepting_san(kinds))
    assert _validate(kinds) == []
    assert link(kinds).stdout.strip() == "Every link is as it should be; nothing written."


def test_the_check_holds_the_links_of_the_four_kinds_and_a_link_on_a_datum_is_extra(
    kinds: AdopterRepo,
) -> None:
    """Whatever any rule's status, the check reports each first mention left unlinked in
    the four kinds' parts, and a link written by hand on a goal, a step line or an actor's
    first sentence is extra. The command takes each such link out (DEC-004 point 7)."""
    missing = {where for where, m in _validate(kinds) if "is the first mention of" in m}
    assert missing >= set(BODIES), missing
    link(kinds)
    hand = "[order](../../glossary.md#term-order--order)"
    by_hand = {
        PLACE: ("**Goal:** Place an order", f"**Goal:** Place an {hand}"),
        JOURNEY: (
            "UC-001-place-order.md) — Place an order",
            f"UC-001-place-order.md) — Place an {hand}",
        ),
        ACTOR_FILE: ("an order and pays for it. Each", f"an {hand} and pays for it. Each"),
    }
    for rel, (old, new_text) in by_hand.items():
        kinds.write({rel: _read(kinds, rel).replace(old, new_text, 1)})
    found = sorted((where, m.split(" — ")[0]) for where, m in _validate(kinds))
    assert [where for where, _m in found] == sorted(by_hand), found
    assert all("where no link belongs" in m for _w, m in found), found
    link(kinds)
    for rel, body in BODIES_LINKED.items():
        assert _body(kinds, rel) == body, rel
    assert _validate(kinds) == []


# --- a view's closing section: what is built on its concepts (DEC-004 point 7) -----------------

#: Each artefact of `kinds` the closing sections list, by its id: its line there.
_ITEM = {
    "UC-001": "- [UC-001 — Place an order](../use-case-model/use-cases/UC-001-place-order.md)",
    "UC-002": "- [UC-002 — Pay for an order](../use-case-model/use-cases/UC-002-pay-order.md)",
    "JRN-001": (
        "- [JRN-001 — Place and pay for a first order]"
        "(../use-case-model/journeys/JRN-001-first-order.md)"
    ),
    "REQ-001": (
        "- [REQ-001 · Quality · Settle a payment quickly]"
        "(../requirements/quality/REQ-001-settle-quickly.md)"
    ),
    "REQ-002": (
        "- [REQ-002 · Functional · Settle each order once]"
        "(../requirements/functional/REQ-002-settle-once.md)"
    ),
}


def _under(label: str, *ids: str) -> str:
    """One concept's part of a closing section: its label, then each artefact's line."""
    return f"**{label}:**\n\n" + "".join(f"{_ITEM[i]}\n" for i in ids)


#: The view's closing section in `kinds`, as the command writes it: under each concept the
#: view explains, each use case, journey and requirement whose body links its term. The
#: second requirement links `order` and no `payment`, and the constraint links `payment
#: method` alone, so it is under neither.
KINDS_CLOSING = (
    f"## What is built on these concepts\n\n{CLOSING_OPENING}\n\n"
    + _under("Order", "UC-001", "UC-002", "JRN-001", "REQ-001", "REQ-002")
    + "\n"
    + _under("Payment", "UC-001", "UC-002", "JRN-001", "REQ-001")
)

#: The heading of a view's closing section, as the command writes it.
CLOSING_HEADING = "## What is built on these concepts"


def _closing_of(repo: AdopterRepo, rel: str = VIEW) -> str:
    """A view's closing section, from its heading to the file's end."""
    return CLOSING_HEADING + _read(repo, rel).split(f"\n{CLOSING_HEADING}", 1)[1]


def test_a_view_ends_with_where_its_concepts_are_used(kinds: AdopterRepo) -> None:
    """The command ends the view with its closing section: under each concept it explains,
    each use case, journey and requirement in force whose body, as the command links it,
    links the concept's term, the use cases first, each by its id and title, linked by a
    path from the view's folder in the form the views' places declare. The section is no
    part of the view's structure, so the check passes with the format rule binding (DEC-004
    points 2 and 7)."""
    link(kinds)
    assert _closing_of(kinds) == KINDS_CLOSING
    assert _body(kinds, VIEW).endswith("**Always true:** None.\n\n" + KINDS_CLOSING)
    targets = re.findall(r"\]\(([^)]+)\)", KINDS_CLOSING)
    assert targets and all(re.fullmatch(links.CLOSING_TARGET, t) for t in targets), targets
    kinds.write(accepting_san(kinds))
    assert _validate(kinds) == []


def test_the_check_holds_the_closing_section_and_the_command_mends_it(kinds: AdopterRepo) -> None:
    """Whatever any rule's status, the check reports a closing section missing, or stale: a
    use case retitled or withdrawn, a section moved off the view's end, or held twice. The
    command writes it anew, last, and a second run writes nothing (DEC-004 point 7)."""
    link(kinds)
    linked = _read(kinds, VIEW)
    kinds.write({VIEW: linked.split(f"\n{CLOSING_HEADING}", 1)[0] + "\n"})
    (missing,) = [m for where, m in _validate(kinds) if where == VIEW]
    assert missing.startswith(f"the view ends with no section `{CLOSING_HEADING}`")
    link(kinds)
    assert _read(kinds, VIEW) == linked

    retitled = _read(kinds, PAY).replace("title: Pay for an order", "title: Pay for it", 1)
    withdrawn = _read(kinds, ONCE).replace("status: active", "status: withdrawn", 1)
    kinds.write({PAY: retitled, ONCE: withdrawn})
    (stale,) = [m for where, m in _validate(kinds) if where == VIEW]
    heading = linked.split("\n").index(CLOSING_HEADING) + 1
    assert stale.startswith(
        f"line {heading} heads the view's section `{CLOSING_HEADING}`, which is stale: "
    )
    link(kinds)
    closing = _closing_of(kinds)
    assert "[UC-002 — Pay for it]" in closing and "REQ-002" not in closing
    kinds.write({PAY: retitled.replace("title: Pay for it", "title: Pay for an order", 1)})
    kinds.write({ONCE: withdrawn.replace("status: withdrawn", "status: active", 1)})
    link(kinds)
    assert _read(kinds, VIEW) == linked

    # Off the view's end, or held twice: stale, and written once, last.
    head, tail = linked.split(f"\n{CLOSING_HEADING}", 1)
    order, payment = head.split("\n## Payment\n", 1)
    moved = f"{order}\n{CLOSING_HEADING}{tail}\n## Payment\n{payment}\n"
    for text in (moved, f"{linked}\n{CLOSING_HEADING}{tail}"):
        kinds.write({VIEW: text})
        assert any("which is stale" in m for where, m in _validate(kinds) if where == VIEW)
        link(kinds)
        assert _read(kinds, VIEW) == linked
    assert link(kinds).stdout.strip() == "Every link is as it should be; nothing written."


def test_the_stamp_ends_a_new_view_with_where_its_concepts_are_used(
    kinds: AdopterRepo,
) -> None:
    """A new view's closing section lists what links its terms already, as the command
    would write it, so the command leaves the new view as the stamp wrote it."""
    link(kinds)
    stamped(kinds, "view", "customers", "--number", "020", "--explains", "TERM-customer")
    view = f"{DOMAIN_MODEL}/020-customers.md"
    assert _closing_of(kinds, view) == (
        f"{CLOSING_HEADING}\n\n{CLOSING_OPENING}\n\n"
        + _under("Customer", "UC-001", "UC-002", "JRN-001", "REQ-002")
    )
    assert view not in link(kinds).stdout


def test_where_a_closing_section_lies_and_what_the_command_makes_of_it() -> None:
    """A closing section runs from its heading, outside fenced code, to the next heading of
    its level or the end. A new view ends with one after its last line that is not blank."""
    lines = ["# V", "", "## Order", "", "x", "", CLOSING_HEADING, "", "y", ""]
    assert links.closing_spans(lines, 0) == [(6, 10)]
    fenced = ["# V", "```", CLOSING_HEADING, "```", "## Order", ""]
    assert links.closing_spans(fenced, 0) == []
    middle = [CLOSING_HEADING, "", "y", "", "## Order", "", "x", ""]
    assert links.closing_spans(middle, 0) == [(0, 4)]
    assert links.closing_lines(middle) == {0, 1, 2, 3}
    closing = [CLOSING_HEADING, "", "**Order:** None."]
    assert links.ending_with("# V\n\nx\n\n\n", closing) == (
        f"# V\n\nx\n\n{CLOSING_HEADING}\n\n**Order:** None.\n"
    )


def test_the_terms_a_body_links_are_read_below_its_front_matter_outside_code() -> None:
    """An artefact uses a term where its body links the term's entry, by the target the
    command writes from the artefact's folder; front matter, code and other links are no
    use."""
    path = "tech-docs/analysis/use-case-model/use-cases/UC-1.md"
    text = (
        "---\nnote: '[payment](../../glossary.md#term-payment--payment)'\n---\n\n"
        f"An [order]({_to(ORDER)}). `[payment]({_to(PAYMENT)})` and [a payment](#elsewhere).\n"
    )
    vocabulary = _vocabulary(ORDER, PAYMENT)
    assert links.terms_linked(text, path, vocabulary) == frozenset({"TERM-order"})


def test_each_concept_lists_its_uses_by_a_path_in_the_declared_form() -> None:
    """Under each concept, in the order the view explains them, each use listed is linked
    by a path from the view's folder, an area's folder or a component's included, which
    the views' places declare: the use cases first, then the requirements. A concept
    nothing links reads `None.`, and a title's brackets are escaped."""
    view = "tech-docs/analysis/core/domain-model/010-orders.md"
    path = "tech-docs/analysis/core/use-case-model/use-cases/010-run/UC-007-run.md"
    case = model.Artefact(
        "use-case", "UC-007", path, path, False, {"title": "Run [fast]"}, {}, folder="core"
    )
    req = dataclasses.replace(
        case,
        kind="constraint",
        id="REQ-003",
        path="tech-docs/analysis/core/requirements/constraints/REQ-003-local.md",
        fields={"title": "Local"},
    )
    used = {"UC-007": {"TERM-order"}, "REQ-003": {"TERM-order"}}
    headings = {"TERM-order": "Order", "TERM-line": "Line"}
    written = links.closing(
        view, ["TERM-order", "TERM-line"], headings, [case, req], used, {"constraint": "Constraint"}
    )
    assert written == [
        CLOSING_HEADING,
        "",
        CLOSING_OPENING,
        "",
        "**Order:**",
        "",
        "- [UC-007 — Run \\[fast\\]](../use-case-model/use-cases/010-run/UC-007-run.md)",
        "- [REQ-003 · Constraint · Local](../requirements/constraints/REQ-003-local.md)",
        "",
        "**Line:** None.",
    ]
    for target in re.findall(r"\]\(([^)]+)\)", "\n".join(written)):
        assert re.fullmatch(links.CLOSING_TARGET, target), target


model, structure = load_lib("model", "structure")

ORDER = links.Term("TERM-order", "order", "tech-docs/analysis/glossary.md")
PAYMENT = links.Term("TERM-payment", "payment", "tech-docs/analysis/glossary.md")


def _document(kind: Any, text: str, *terms: Any, **fields: Any) -> str:
    path = "tech-docs/analysis/use-case-model/x/X-1.md"
    artefact = model.Artefact(kind.name, "X-1", path, path, False, fields, {})
    return links.document(artefact, text, _vocabulary(*terms), kind).linked


def _to(term: Any) -> str:
    return f"../../glossary.md#{term.anchor}"


def test_a_part_opens_at_each_label_the_project_adds_and_a_relabelled_goal_stays_plain(
    tmp_path: Path,
) -> None:
    """The kinds are read as the project's own structures relabel them and add to them,
    whatever any rule's status: a label a group adds opens a part of its own, and the goal
    stays plain under the label it is relabelled to, and under its shipped one."""
    own = tmp_path / SA / "project" / "structures.yaml"
    own.parent.mkdir(parents=True)
    own.write_text(
        "schema_version: 1\nkinds:\n  use-case:\n    relabel: {goal: {label: Aim}}\n"
        "  actor:\n    tighten:\n      - rule: RS-LOC-001\n        add:\n"
        "          - {id: setup, label: Setup, after: opening, hint: Its setup.,\n"
        "             example: A lab.}\n",
        encoding="utf-8",
    )
    kinds = links.parted(tmp_path)
    assert set(kinds) == set(links.PARTED)
    case = "# UC-1 — T\n\n**Aim:** An order.\n\n**Goal:** An order.\n\n**Trigger:** An order."
    assert _document(kinds["use-case"], case, ORDER) == case.replace(
        "Trigger:** An order", f"Trigger:** An [order]({_to(ORDER)})"
    )
    actor = "# ACT-x — X\n\nA payment. An order.\n\n- **Setup:** an order.\n"
    assert _document(kinds["actor"], actor, ORDER, PAYMENT) == (
        f"# ACT-x — X\n\nA [payment]({_to(PAYMENT)}). An [order]({_to(ORDER)}).\n\n"
        f"- **Setup:** an [order]({_to(ORDER)}).\n"
    )
    # Its first sentence stays plain only where the actor gives a summary.
    assert _document(kinds["actor"], actor, ORDER, PAYMENT, summary="A payment.") == (
        f"# ACT-x — X\n\nA payment. An [order]({_to(ORDER)}).\n\n"
        f"- **Setup:** an [order]({_to(ORDER)}).\n"
    )


def test_a_journey_s_step_line_stays_plain_to_its_end_and_its_hand_overs_link(
    tmp_path: Path,
) -> None:
    """A step's line runs to a blank line, a nested item or a hand-over. Its title stays
    plain, and the first mention in a hand-over or a nested item takes the link."""
    journey = links.parted(tmp_path)["journey"]
    text = (
        "# JRN-1 — T\n\n**Steps:**\n\n1. UC-1 — Place an\n   order\n"
        "   **Needs from step 1 (UC-1):** a payment.\n2. UC-2 — Pay\n   - an order paid\n"
    )
    assert _document(journey, text, ORDER, PAYMENT) == text.replace(
        "a payment.", f"a [payment]({_to(PAYMENT)})."
    ).replace("an order paid", f"an [order]({_to(ORDER)}) paid")


@pytest.mark.parametrize(
    ("text", "end"),
    [
        ("One. Two.", 4),
        ("  One `a. B` two. Three.", 17),
        ("One e.g. two.\n\nThree.", 13),
        ("One\nline. Two.", 9),
        ("One only", 8),
    ],
)
def test_the_first_sentence_ends_where_the_summary_s_form_ends_it(text: str, end: int) -> None:
    (forms,) = load_lib("forms")
    assert forms.first_sentence_end(text) == end
    assert " ".join(text[:end].split()) == forms.first_sentence(text)
