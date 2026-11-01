"""software-analysis: `pkit analysis uses` lists where an analysis uses a term (#1795).

The deterministic half of `RS-SAN-008`: each mention of a term's names, and of the names
it replaces, in the artefacts in force, by artefact and line, in a stable order, so a
rename, a merge or a withdrawal finds each use to mend. Held to `_lib/uses.py`:

- **read as the links read** — a mention is what `pkit analysis link` reads as one, by the
  links' own code, in the same sections: the safeguards hold (whole words, the longest
  first, code, headings, bold labels, links and ids skipped, a phrase in another sense,
  an actor's name and the escape), and every link the command writes to the term lies on
  a use the command lists;
- **each mention** — not only the first, in the term's own entry and in a goal too;
- **the names** — its name and noun forms, then the names it replaces, each use marked;
  a name another term holds is not searched; a withdrawn term is searched alike;
- **every analysis** — whether or not it keeps a domain model, and one analysis of
  several, named by `--analysis`, a term its glossary's head lists read by that name;
- **complete, or no answer** — an id of no term, a term the analysis does not hold, and
  a file that cannot be read as an artefact of its place each exit 1.

The command runs in the test's own process (`tests/in_process.py`). One test keeps a
process: the command's exit code and the lines it prints.
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
    SETTINGS,
    SETTINGS_TEXT,
    USE_CASES,
    fill,
    installed,
    link,
    prepare,
    run_in_process,
    run_script,
    stamped,
)

USES = SA / "scripts" / "uses.py"
VIEW = f"{DOMAIN_MODEL}/010-orders-and-payments.md"
USE_CASE = f"{USE_CASES}/UC-001-take-order.md"

#: Each glossary entry below its heading, as a writer fills it, by its term's id. Each
#: safeguard meets a mention here: a bold label, an id, code, a phrase in another sense
#: and the longest mention first.
ENTRIES = {
    "TERM-order": (
        "**Example:** a customer places an order, and pays for it.\n\n"
        "**Distinctions:**\n\n- **Purchase:** the name it replaces, never another concept.\n"
    ),
    "TERM-payment": (
        "**Example:** a payment settles an order. See TERM-order, or `order` in code.\n\n"
        "**Distinctions:** None.\n"
    ),
    "TERM-customer": (
        "**Example:** customer service answers a customer about a purchase.\n\n"
        "**Distinctions:** None.\n"
    ),
    "TERM-payment-method": (
        "**Example:** a card is a payment method.\n\n**Distinctions:** None.\n"
    ),
}

#: The view's body, below its front matter: an opening, and a section for each term it
#: explains, each opening with its link to its term.
VIEW_BODY = (
    "# VIEW-orders-and-payments — Orders and payments\n\n"
    "How a customer pays for a purchase.\n\n"
    "## Order\n\n"
    "Defined in [TERM-order](../glossary.md#term-order--order).\n\n"
    "**Why:** None.\n\n"
    "An order is what a customer asks for. Orders wait for a payment.\n\n"
    "```\norder\n```\n\n"
    "## Payment\n\n"
    "Defined in [TERM-payment](../glossary.md#term-payment--payment).\n\n"
    "**Why:** None.\n\n"
    "A payment settles an order.\n"
)

#: The use case's parts that name the terms, each in place of what the fill wrote: a goal,
#: which stays plain of links, an actor's name that holds a term's, the escape, code, a
#: link of the writer's own and a phrase in another sense.
GOAL = "**Goal:** Take a purchase for a customer."
TRIGGER = (
    "**Trigger:** The Order desk takes an order by phone, in "
    "<!-- pkit:not-the-term -->order of arrival."
)
MAIN_PATH = (
    "1. The customer service desk checks the purchase and its payment method.\n"
    "2. The system keeps the orders, as `order` in code and "
    "[the docs](https://example.org/order) say."
)


def _part(text: str, label: str, body: str) -> str:
    """`text` with the part `label` opens, up to the next part, written as `body`."""
    pattern = rf"\*\*{re.escape(label)}:\*\*.*?(?=\n\n\*\*[A-Z][^*\n]*:\*\*)"
    written, count = re.subn(pattern, lambda _m: body, text, count=1, flags=re.S)
    assert count == 1, f"no part {label}"
    return written


def _terms(repo: AdopterRepo) -> None:
    """Four terms, `order` with its plural and a name it replaces and `customer` with a
    phrase in another sense, an actor whose name holds `order`, a use case and a view
    explaining two of the terms, filled as `ENTRIES`, `VIEW_BODY` and the use case's parts
    say. Built once per session (`installed`)."""
    prepare(repo)
    for slug, name in (
        ("order", "order"),
        ("payment", "payment"),
        ("customer", "customer"),
        ("payment-method", "payment method"),
    ):
        stamped(repo, "term", slug, "--name", name, "--path", "src/run.py")
    stamped(repo, "actor", "order-desk", "--name", "Order desk", "--path", "src/**")
    stamped(repo, "use-case", "take-order", "--actor", "ACT-order-desk", "--path", "src/run.py")
    explains = ("--explains", "TERM-order", "--explains", "TERM-payment")
    stamped(repo, "view", "orders-and-payments", "--number", "010", *explains)
    fill(repo)
    glossary = (repo.root / GLOSSARY).read_text(encoding="utf-8")
    glossary = glossary.replace(
        "  name: order\n", "  name: order\n  noun-forms: [orders]\n  replaces: [purchase]\n", 1
    )
    glossary = glossary.replace(
        "  name: customer\n", "  name: customer\n  other-senses: [customer service]\n", 1
    )
    for term, body in ENTRIES.items():
        glossary = re.sub(
            rf"(## {term} — [^\n]*\n\n(?:Explained in [^\n]*\n\n)?)\*\*Example:\*\*.*?(?=\n## |\Z)",
            lambda m, b=body: m[1] + b,
            glossary,
            count=1,
            flags=re.S,
        )
    use_case = (repo.root / USE_CASE).read_text(encoding="utf-8")
    use_case = _part(use_case, "Goal", GOAL)
    use_case = _part(use_case, "Trigger", TRIGGER)
    use_case = _part(use_case, "Main path", f"**Main path:**\n\n{MAIN_PATH}")
    view = (repo.root / VIEW).read_text(encoding="utf-8").split("\n---\n", 1)[0]
    repo.write({GLOSSARY: glossary, USE_CASE: use_case, VIEW: f"{view}\n---\n\n{VIEW_BODY}"})


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch, then=_terms)


def _uses(repo: AdopterRepo, *args: str) -> dict[str, Any]:
    """The command's document, `--json`, in the test's own process."""
    completed = run_in_process(repo, USES, *args, "--json")
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def _listed(document: dict[str, Any]) -> list[tuple[str, int, str, bool]]:
    """Each use the document lists: its file, its line, its text and whether it is of a
    name the term replaces."""
    return [(u["path"], u["line"], u["text"], u["replaced"]) for u in document["uses"]]


def _refused(repo: AdopterRepo, *args: str) -> str:
    completed = run_in_process(repo, USES, *args)
    assert completed.returncode == 1, completed.stdout
    assert completed.stdout == ""
    return str(completed.stderr)


def _line(repo: AdopterRepo, rel: str, text: str) -> int:
    """The line, counted from 1, of the one line of `rel` that holds `text`."""
    lines = (repo.root / rel).read_text(encoding="utf-8").split("\n")
    found = [index + 1 for index, line in enumerate(lines) if text in line]
    assert len(found) == 1, (rel, text, found)
    return found[0]


def _order_uses(repo: AdopterRepo) -> list[tuple[str, int, str, bool]]:
    """TERM-order's uses in the fixture, as the command lists them: by file, then line, then
    their place on the line, which the order they are written in here gives."""
    written = [
        (VIEW, _line(repo, VIEW, "How a customer pays"), "purchase", True),
        (VIEW, _line(repo, VIEW, "An order is what"), "order", False),
        (VIEW, _line(repo, VIEW, "An order is what"), "Orders", False),
        (VIEW, _line(repo, VIEW, "A payment settles an order."), "order", False),
        (GLOSSARY, _line(repo, GLOSSARY, "a customer places an order"), "order", False),
        (GLOSSARY, _line(repo, GLOSSARY, "a payment settles an order"), "order", False),
        (GLOSSARY, _line(repo, GLOSSARY, "about a purchase"), "purchase", True),
        (USE_CASE, _line(repo, USE_CASE, GOAL), "purchase", True),
        (USE_CASE, _line(repo, USE_CASE, "takes an order by phone"), "order", False),
        (USE_CASE, _line(repo, USE_CASE, "checks the purchase"), "purchase", True),
        (USE_CASE, _line(repo, USE_CASE, "keeps the orders"), "orders", False),
    ]
    return sorted(written, key=lambda use: (use[0], use[1]))


# --- what it lists ---------------------------------------------------------------------------


def test_each_mention_of_its_names_and_the_names_it_replaces_is_listed(
    project: AdopterRepo,
) -> None:
    """Each mention, by file, line and its place on the line: in a view's opening and its
    sections, in each glossary entry, the term's own among them, and in each part of a use
    case, its goal included. A name the term replaces is marked. Nothing the safeguards
    keep a link off is listed: the title's heading, a bold label, an id, code, a link of
    the writer's own, a phrase in another sense, an actor's name, an escaped mention, and
    `payment method`, which holds `payment`."""
    document = _uses(project, "TERM-order")
    assert _listed(document) == _order_uses(project)
    assert {(u["id"], u["kind"]) for u in document["uses"]} == {
        ("VIEW-orders-and-payments", "domain-model-view"),
        ("TERM-order", "term"),
        ("TERM-payment", "term"),
        ("TERM-customer", "term"),
        ("UC-001", "use-case"),
    }
    by_name = {(u["text"].casefold(), u["name"]) for u in document["uses"]}
    assert by_name == {("order", "order"), ("orders", "orders"), ("purchase", "purchase")}
    assert document["term"] == {
        "id": "TERM-order",
        "name": "order",
        "status": "active",
        "location": f"{GLOSSARY}#TERM-order",
        "analysis": None,
        "listed_from": None,
        "names": ["order", "orders"],
        "replaces": ["purchase"],
        "not_searched": [],
    }
    assert document["schema_version"] == 1
    payment = _uses(project, "TERM-payment")
    assert [(u["id"], u["text"]) for u in payment["uses"]] == [
        ("VIEW-orders-and-payments", "payment"),
        ("VIEW-orders-and-payments", "payment"),
        ("TERM-payment", "payment"),
    ]


def test_every_link_the_command_writes_to_the_term_lies_on_a_use_it_lists(
    project: AdopterRepo,
) -> None:
    """The links and the uses read one way: each first mention `pkit analysis link` links
    to the term's entry is a use, at its line, with its text. A link whose text is the
    term's id is no mention. Linked, the analysis lists the same uses, since a link's text
    is read as the mention it is."""
    before = _listed(_uses(project, "TERM-order"))
    link(project)
    linked: set[tuple[str, int, str]] = set()
    for rel in (GLOSSARY, VIEW, USE_CASE):
        lines = (project.root / rel).read_text(encoding="utf-8").split("\n")
        for index, line in enumerate(lines):
            for m in re.finditer(r"\[([^\]]+)\]\([^)]*#term-order--order\)", line):
                if m[1] != "TERM-order":
                    linked.add((rel, index + 1, m[1]))
    # The term's own section and entry take none, nor does a goal, nor a name it replaces.
    assert linked == {
        (VIEW, _line(project, VIEW, "settles an [order]"), "order"),
        (GLOSSARY, _line(project, GLOSSARY, "settles an [order]"), "order"),
        (USE_CASE, _line(project, USE_CASE, "by phone"), "order"),
        (USE_CASE, _line(project, USE_CASE, "keeps the [orders]"), "orders"),
    }
    after = _listed(_uses(project, "TERM-order"))
    assert linked <= {(path, line, text) for path, line, text, _replaced in after}
    assert [(p, t, r) for p, _l, t, r in after] == [(p, t, r) for p, _l, t, r in before]


def test_a_withdrawn_term_is_searched_by_the_same_names(project: AdopterRepo) -> None:
    """A withdrawal leaves each use to mend, so its names are searched as before. Its own
    entry is history, and read no more."""
    text = (project.root / GLOSSARY).read_text(encoding="utf-8")
    text, count = re.subn(r"(TERM-order:\n(?:  [^\n]*\n)*?  status: )active", r"\1withdrawn", text)
    assert count == 1
    project.write({GLOSSARY: text})
    document = _uses(project, "TERM-order")
    assert document["term"]["status"] == "withdrawn"
    expected = [u for u in _order_uses(project) if "places an order" not in _text(project, u)]
    assert _listed(document) == expected


def _text(repo: AdopterRepo, use: tuple[str, int, str, bool]) -> str:
    return (repo.root / use[0]).read_text(encoding="utf-8").split("\n")[use[1] - 1]


def test_a_name_another_term_holds_is_not_searched(project: AdopterRepo) -> None:
    """A name another term holds is that term's, so it is listed apart and never as a use
    of this one."""
    text = (project.root / GLOSSARY).read_text(encoding="utf-8")
    text = text.replace("  name: payment\n", "  name: payment\n  replaces: [customer]\n", 1)
    project.write({GLOSSARY: text})
    document = _uses(project, "TERM-payment")
    assert document["term"]["replaces"] == []
    assert document["term"]["not_searched"] == [{"name": "customer", "held_by": "TERM-customer"}]
    assert all(u["name"] == "payment" for u in document["uses"])


def test_an_analysis_without_a_domain_model_is_read_too(project: AdopterRepo) -> None:
    """The links to terms are written only where an analysis keeps a domain model, and
    their reading holds in every analysis."""
    expected = [u for u in _order_uses(project) if u[0] != VIEW]
    project.write({VIEW: None})
    assert _listed(_uses(project, "TERM-order")) == expected


# --- complete, or no answer ------------------------------------------------------------------


def test_what_cannot_be_answered_in_full_exits_1(project: AdopterRepo) -> None:
    """An id of no term's shape, a term the analysis does not hold, a file of its places
    that holds no artefact of its place, and an analysis named where the project lists
    none each give no answer."""
    assert "sync is no term's id" in _refused(project, "sync")
    assert "no term TERM-nothing in the analysis" in _refused(project, "TERM-nothing")
    assert "lists no analyses" in _refused(project, "TERM-order", "--analysis", "core")
    broken = f"{USE_CASES}/UC-009-broken.md"
    project.write({broken: "---\nid: [\n---\n\n# UC-009 — Broken\n"})
    message = _refused(project, "TERM-order")
    assert f"{broken} cannot be read as an artefact of its place" in message


# --- one analysis of several -----------------------------------------------------------------

CORE = "  - {component: core, folder: core}\n"
BILLING = "  - component: billing\n    folder: billing\n    builds-on:\n      - {analysis: core}\n"
CORE_GLOSSARY = f"{ANALYSIS}/core/glossary.md"
BILLING_GLOSSARY = f"{ANALYSIS}/billing/glossary.md"
INVOICE = f"{ANALYSIS}/billing/use-case-model/use-cases/UC-001-invoice.md"

#: The billing glossary's head data, listing the core's `suite` by the name `test suite`.
HEAD = (
    "builds-on:\n"
    "  - analysis: core\n"
    "    version: 1.149.0\n"
    "    terms:\n"
    "      - {id: TERM-suite, name: test suite}\n"
)


def _two(repo: AdopterRepo) -> None:
    """Two analyses: the core's, with the term `suite`, which replaces `test set`, and
    billing's, which builds on it and lists the term as `test suite`, with a use case that
    names it. Built once per session."""
    prepare(repo)
    repo.write({SETTINGS: SETTINGS_TEXT + "analyses:\n" + CORE + BILLING})
    stamped(repo, "term", "suite", "--name", "suite", "--analysis", "core", "--path", "src/**")
    stamped(repo, "term", "bill", "--name", "bill", "--analysis", "billing", "--path", "src/**")
    stamped(repo, "actor", "clerk", "--analysis", "billing", "--path", "src/**")
    stamped(repo, "use-case", "invoice", "--actor", "ACT-clerk", "--analysis", "billing")
    fill(repo)
    core = (repo.root / CORE_GLOSSARY).read_text(encoding="utf-8")
    core = core.replace("  name: suite\n", "  name: suite\n  replaces: [test set]\n", 1)
    billing = (repo.root / BILLING_GLOSSARY).read_text(encoding="utf-8")
    invoice = (repo.root / INVOICE).read_text(encoding="utf-8")
    invoice = _part(invoice, "Goal", "**Goal:** Bill each test suite, as each test set was.")
    repo.write(
        {
            CORE_GLOSSARY: core,
            BILLING_GLOSSARY: billing.replace("---\n", f"---\n{HEAD}", 1),
            INVOICE: invoice,
        }
    )


@pytest.fixture
def two(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch, then=_two)


def test_one_analysis_of_several_is_read_and_a_listed_term_by_the_name_listed(
    two: AdopterRepo,
) -> None:
    """Where the project lists several analyses, `--analysis` names the one read. A term
    its glossary's head lists from another is read by the name the head lists, and by the
    names its own entry replaces, and stays listed when withdrawn there."""
    assert "name the one to read, --analysis <component>" in _refused(two, "TERM-suite")
    document = _uses(two, "TERM-suite", "--analysis", "billing")
    line = _line(two, INVOICE, "Bill each test suite")
    assert _listed(document) == [
        (INVOICE, line, "test suite", False),
        (INVOICE, line, "test set", True),
    ]
    assert document["term"]["name"] == "test suite"
    assert document["term"]["analysis"] == "billing"
    assert document["term"]["listed_from"] == "core"
    assert document["term"]["names"] == ["test suite"]
    assert document["term"]["replaces"] == ["test set"]
    assert _listed(_uses(two, "TERM-suite", "--analysis", "core")) == []
    core = (two.root / CORE_GLOSSARY).read_text(encoding="utf-8")
    two.write(
        {
            CORE_GLOSSARY: re.sub(
                r"(  name: suite\n(?:  [^\n]*\n)*?  status: )active", r"\1withdrawn", core, count=1
            )
        }
    )
    assert _listed(_uses(two, "TERM-suite", "--analysis", "billing")) == _listed(document)


# --- the command, as a process ---------------------------------------------------------------


@pytest.mark.process(
    "the uses command's end-to-end test: its exit code and the lines it prints, from a "
    "process of its own, and the pkit it starts"
)
def test_the_command_prints_each_use_by_file_and_line(project: AdopterRepo) -> None:
    """For a person: the term and the names searched, then each use, its file and line
    first, a name the term replaces marked."""
    completed = run_script(project, USES, "TERM-order")
    assert completed.returncode == 0, completed.stderr
    said = completed.stdout.splitlines()
    assert said[:4] == [
        "TERM-order — order, in the analysis",
        "  Its names: order, orders",
        "  The names it replaces: purchase",
        "  Uses:",
    ]
    goal = _line(project, USE_CASE, GOAL)
    assert f"    {USE_CASE}:{goal}  UC-001  purchase  (a name it replaces)" in said
    assert len(said) == 4 + len(_order_uses(project))
