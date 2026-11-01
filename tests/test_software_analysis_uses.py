"""software-analysis: `pkit analysis uses` prints what to search for when a term changes
(#1795).

When a term is renamed, merged or withdrawn, whoever changes it finds its uses and mends
them (DEC-001 point 12). The command gives the names to search for, from front matter
alone, since a tool reads no body's other text (DEC-001 point 1; DEC-006 point 3). Held to
`_lib/uses.py`:

- **the names** — its name and noun forms, then the names it replaces;
- **a name another term holds** — listed apart, never as one of its names;
- **a withdrawn term** — gives its names alike;
- **no body** — a mention written in a body changes nothing, and a file whose front matter
  does not parse stops the answer only where it is a glossary;
- **one analysis of several** — named by `--analysis`, a term its glossary's head lists
  read by the name listed, and each analysis whose head lists the term named;
- **no answer** — an id of no term, a term the analysis does not hold, and a glossary
  that cannot be read each exit 1.

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
    GLOSSARY,
    SA,
    SETTINGS,
    SETTINGS_TEXT,
    USE_CASES,
    installed,
    prepare,
    run_in_process,
    run_script,
    stamped,
)

USES = SA / "scripts" / "uses.py"
USE_CASE = f"{USE_CASES}/UC-001-take-order.md"


def _terms(repo: AdopterRepo) -> None:
    """Three terms, `order` with its plural and a name it replaces, an actor and a use
    case. Built once per session (`installed`)."""
    prepare(repo)
    for slug in ("order", "payment", "customer"):
        stamped(repo, "term", slug, "--name", slug, "--path", "src/run.py")
    stamped(repo, "actor", "clerk", "--name", "clerk", "--path", "src/**")
    stamped(repo, "use-case", "take-order", "--actor", "ACT-clerk", "--path", "src/run.py")
    glossary = (repo.root / GLOSSARY).read_text(encoding="utf-8")
    glossary = glossary.replace(
        "  name: order\n", "  name: order\n  noun-forms: [orders]\n  replaces: [purchase]\n", 1
    )
    repo.write({GLOSSARY: glossary})


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


def _said(repo: AdopterRepo, *args: str) -> list[str]:
    """The lines the command prints for a person, in the test's own process."""
    completed = run_in_process(repo, USES, *args)
    assert completed.returncode == 0, completed.stderr
    return str(completed.stdout).splitlines()


def _refused(repo: AdopterRepo, *args: str) -> str:
    completed = run_in_process(repo, USES, *args)
    assert completed.returncode == 1, completed.stdout
    assert completed.stdout == ""
    return str(completed.stderr)


def _withdrawn(text: str, name: str) -> str:
    """A glossary's `text` with the term named `name` withdrawn."""
    written, count = re.subn(
        rf"(  name: {name}\n(?:  [^\n]*\n)*?  status: )active", r"\1withdrawn", text, count=1
    )
    assert count == 1
    return written


# --- what it prints --------------------------------------------------------------------------


def test_its_names_and_the_names_it_replaces_are_printed(project: AdopterRepo) -> None:
    """The term's name and noun forms, then the names its `replaces` lists, and the term
    itself: its id, name, status and entry, and the analysis read."""
    assert _uses(project, "TERM-order") == {
        "schema_version": 1,
        "term": {
            "id": "TERM-order",
            "name": "order",
            "status": "active",
            "location": f"{GLOSSARY}#TERM-order",
            "analysis": None,
            "listed_from": None,
        },
        "names": ["order", "orders"],
        "replaces": ["purchase"],
        "not_searched": [],
        "listed_in": [],
    }
    payment = _uses(project, "TERM-payment")
    assert (payment["names"], payment["replaces"]) == (["payment"], [])


def test_a_name_another_term_holds_is_listed_apart(project: AdopterRepo) -> None:
    """A name another term holds is that term's, so it is listed apart and never as one of
    the names to search for this one."""
    text = (project.root / GLOSSARY).read_text(encoding="utf-8")
    text = text.replace("  name: payment\n", "  name: payment\n  replaces: [customer]\n", 1)
    project.write({GLOSSARY: text})
    document = _uses(project, "TERM-payment")
    assert document["replaces"] == []
    assert document["not_searched"] == [{"name": "customer", "held_by": "TERM-customer"}]
    assert "  Not searched for it: customer, a name of TERM-customer" in _said(
        project, "TERM-payment"
    )


def test_a_withdrawn_term_gives_its_names_alike(project: AdopterRepo) -> None:
    """A withdrawal leaves each use to mend, so the term's names are printed as before."""
    before = _uses(project, "TERM-order")
    text = (project.root / GLOSSARY).read_text(encoding="utf-8")
    project.write({GLOSSARY: _withdrawn(text, "order")})
    document = _uses(project, "TERM-order")
    assert document["term"]["status"] == "withdrawn"
    assert {k: v for k, v in document.items() if k != "term"} == {
        k: v for k, v in before.items() if k != "term"
    }
    assert _said(project, "TERM-order")[0] == "TERM-order — order (withdrawn), in the analysis"


def test_no_body_text_is_read(project: AdopterRepo) -> None:
    """The command reads front matter alone: a mention written in a body, of a name the term
    replaces or of another word, changes nothing. A use case whose front matter does not
    parse changes nothing either, since only a glossary's names are read."""
    before = _uses(project, "TERM-order")
    glossary = (project.root / GLOSSARY).read_text(encoding="utf-8")
    use_case = (project.root / USE_CASE).read_text(encoding="utf-8")
    mentions = "\nEach purchase is an order of a client; the orders and the buyings wait.\n"
    broken = f"{USE_CASES}/UC-009-broken.md"
    project.write(
        {
            GLOSSARY: glossary + mentions,
            USE_CASE: use_case + mentions,
            broken: "---\nid: [\n---\n\n# UC-009 — Broken\n",
        }
    )
    assert _uses(project, "TERM-order") == before


# --- no answer -------------------------------------------------------------------------------


def test_what_cannot_be_answered_exits_1(project: AdopterRepo) -> None:
    """An id of no term's shape, a term the analysis does not hold, an analysis named where
    the project lists none, and a glossary whose front matter does not parse each give no
    answer."""
    assert "sync is no term's id" in _refused(project, "sync")
    assert "no term TERM-nothing in the analysis" in _refused(project, "TERM-nothing")
    assert "lists no analyses" in _refused(project, "TERM-order", "--analysis", "core")
    text = (project.root / GLOSSARY).read_text(encoding="utf-8")
    project.write({GLOSSARY: text.replace("  name: order\n", "  name: [order\n", 1)})
    assert f"{GLOSSARY} cannot be read as a glossary" in _refused(project, "TERM-order")


# --- one analysis of several -----------------------------------------------------------------

CORE = "  - {component: core, folder: core}\n"
BILLING = "  - component: billing\n    folder: billing\n    builds-on:\n      - {analysis: core}\n"
CORE_GLOSSARY = f"{ANALYSIS}/core/glossary.md"
BILLING_GLOSSARY = f"{ANALYSIS}/billing/glossary.md"

#: The billing glossary's head data, listing the core's `suite` by the name `test suite`.
HEAD = (
    "builds-on:\n"
    "  - analysis: core\n"
    "    version: 1.149.0\n"
    "    terms:\n"
    "      - {id: TERM-suite, name: test suite}\n"
)


def _two(repo: AdopterRepo) -> None:
    """Two analyses: the core's, with the term `suite`, its plural and a name it replaces,
    and billing's, which builds on it and lists the term as `test suite`. Built once per
    session."""
    prepare(repo)
    repo.write({SETTINGS: SETTINGS_TEXT + "analyses:\n" + CORE + BILLING})
    stamped(repo, "term", "suite", "--name", "suite", "--analysis", "core", "--path", "src/**")
    stamped(repo, "term", "bill", "--name", "bill", "--analysis", "billing", "--path", "src/**")
    core = (repo.root / CORE_GLOSSARY).read_text(encoding="utf-8")
    core = core.replace(
        "  name: suite\n", "  name: suite\n  noun-forms: [suites]\n  replaces: [test set]\n", 1
    )
    billing = (repo.root / BILLING_GLOSSARY).read_text(encoding="utf-8")
    repo.write({CORE_GLOSSARY: core, BILLING_GLOSSARY: billing.replace("---\n", f"---\n{HEAD}", 1)})


@pytest.fixture
def two(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch, then=_two)


def test_one_analysis_of_several_and_where_else_the_term_is_listed(two: AdopterRepo) -> None:
    """Where the project lists several analyses, `--analysis` names the one read. A term its
    glossary's head lists from another is read by the name the head lists, with the noun
    forms and the names its own entry gives, and stays readable when withdrawn there. Each
    analysis whose head lists the term is named, whichever analysis is read."""
    assert "name the one to read, --analysis <component>" in _refused(two, "TERM-suite")
    listed_in = [{"analysis": "billing", "name": "test suite"}]
    billing = _uses(two, "TERM-suite", "--analysis", "billing")
    assert billing["term"]["name"] == "test suite"
    assert billing["term"]["analysis"] == "billing"
    assert billing["term"]["listed_from"] == "core"
    assert billing["term"]["location"] == f"{CORE_GLOSSARY}#TERM-suite"
    assert (billing["names"], billing["replaces"]) == (["test suite", "suites"], ["test set"])
    assert billing["listed_in"] == listed_in
    core = _uses(two, "TERM-suite", "--analysis", "core")
    assert (core["term"]["name"], core["term"]["listed_from"]) == ("suite", None)
    assert (core["names"], core["replaces"]) == (["suite", "suites"], ["test set"])
    assert core["listed_in"] == listed_in
    assert _said(two, "TERM-suite", "--analysis", "core")[-1] == (
        "  Listed in the glossary's head of billing, as test suite"
    )
    assert "no term TERM-bill in the analysis of core" in _refused(
        two, "TERM-bill", "--analysis", "core"
    )
    text = (two.root / CORE_GLOSSARY).read_text(encoding="utf-8")
    two.write({CORE_GLOSSARY: _withdrawn(text, "suite")})
    withdrawn = _uses(two, "TERM-suite", "--analysis", "billing")
    assert withdrawn["term"]["status"] == "withdrawn"
    assert (withdrawn["names"], withdrawn["replaces"]) == (billing["names"], billing["replaces"])


# --- the command, as a process ---------------------------------------------------------------


@pytest.mark.process(
    "the uses command's end-to-end test: its exit code and the lines it prints, from a "
    "process of its own, and the pkit it starts"
)
def test_the_command_prints_the_names_to_search_for(project: AdopterRepo) -> None:
    """For a person: the term and the analysis read, then its names and the names it
    replaces, one line each."""
    completed = run_script(project, USES, "TERM-order")
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines() == [
        "TERM-order — order, in the analysis",
        "  Its names: order, orders",
        "  The names it replaces: purchase",
    ]
