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
- **one name, one concept** — validation refuses two terms in force of one name, a
  plural among the names, and a name another term replaces, within an analysis and
  across the analyses it builds on, two of those included, whatever any rule's status.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    ANALYSIS,
    DOMAIN_MODEL,
    GLOSSARY,
    SA,
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
    opening with the link the stamp writes. Each safeguard meets a mention here."""

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


VIEW_BODY = _view(linked=False)
VIEW_LINKED = _view(linked=True)

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
        "\n\n<!-- pkit:hint " in body
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
        f"linked {VIEW} (8 link(s) written or mended)",
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
    assert len(found) == 13, "\n".join(f"{where} | {m}" for where, m in found)
    assert all(
        m.endswith("run `pkit analysis link`, which writes the links (DEC-004 point 7)")
        for _l, m in found
    )
    assert (
        VIEW,
        "line 31: `customer` is the first mention of TERM-customer in its section, and takes "
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
        "line 35: `payment` links to a glossary entry, `../glossary.md#term-payment--payment`, "
        "where no link belongs: only the first mention of a term in force in each section "
        "takes one, never in its own section, nor after `<!-- pkit:not-the-term -->`",
        "line 41 heads a section with no link to its term: each section opens with "
        "`Defined in [TERM-payment](../glossary.md#term-payment--payment).`",
        "line 43: `orders` links to `../glossary.md#term-old--old`, and its term's entry is "
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


def test_an_analysis_with_no_domain_model_takes_no_link(bare: AdopterRepo) -> None:
    """A glossary with no view beside it is never linked nor held, a link written in it by
    hand included (DEC-004 point 7)."""
    stamped(bare, "term", "order", "--name", "order", "--path", "src/run.py")
    stamped(bare, "term", "payment", "--name", "payment", "--path", "src/run.py")
    fill(bare)
    _set_entries(bare, {"TERM-order": ("a payment settles an order.", " None.")})
    before = _read(bare, GLOSSARY)
    completed = link(bare)
    assert "No analysis keeps a domain model" in completed.stdout
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


def test_a_term_is_never_linked_in_its_own_section_and_its_name_consumes_its_words() -> None:
    """The section's own term takes no link, and a shorter term inside it takes none
    either: `record` is never linked inside `decision record`."""
    assert _linked(
        "A decision record is a record.", "TERM-decision-record", DECISION_RECORD, RECORD
    ) == ("A decision record is a [record](#term-record--record).")


def test_a_name_two_terms_share_links_neither() -> None:
    """Validation refuses the pair; until it is mended, neither term is linked by the name
    they share, ignoring case, and each keeps the names it holds alone."""
    twin = links.Term("TERM-change-2", "Change", "other/glossary.md", ("change sets",))
    assert links.matched((CHANGE, twin)) == {CHANGE.id: (), twin.id: ("change sets",)}
    vocabulary = links.Vocabulary((CHANGE, twin), links.matched((CHANGE, twin)))
    assert links.section("a change", None, vocabulary, "glossary.md", 1)[0] == "a change"


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
                "pkit_schema: software-analysis:config\nschema_version: 1\nanalyses:\n"
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
