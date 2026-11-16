"""Each caller project-kit ships reads a document a command prints as ADR-097 point 3 says
(ADR-097 point 7).

Each test hands a caller the documents a command prints, from a real run or from the
function the command prints them through, and `tests/caller_contracts.py` varies each:
a key the caller does not know, each key it reads left out or null, a value of a set it
does not know, a version it does not know, and no document at all. The documents and
their contracts are `tests/test_backbone_documents.py`'s, so a caller is held to the
same contract its command is.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from project_kit import data_points as dp
from project_kit import default_branch as db
from tests import document_contracts as contracts
from tests import test_backbone_documents as documents
from tests.adopter_repo import AdopterRepo
from tests.caller_contracts import Caller, Outcome, check, raises, same
from tests.document_contracts import Contract, Form
from tests.in_process import load


def _no_document(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
    """A run of a command that gave no document: it exited 1 and printed nothing."""
    return subprocess.CompletedProcess([], 1, "", "the command failed\n")


def _repository_bases() -> list[dict[str, Any]]:
    """`pkit repository base --json` as its contract's test builds it: a base named by the
    option and read from the remote, one from the environment read locally, and a
    default branch that names no commit."""
    return [
        documents._settled(db.OPTION, db.RESOLVED_REMOTE),
        documents._settled(db.ENVIRONMENT, db.RESOLVED_LOCAL),
        documents._settled(db.DEFAULT_BRANCH, None, found=False),
    ]


@pytest.fixture
def repository_checks(
    committed_adopter: AdopterRepo, answers_in_files: None
) -> list[dict[str, Any]]:
    """`pkit friction check --all --json` as its contract's test prints it: a run, one
    with every finding and state, and a dormant check."""
    del answers_in_files
    documents._friction_history(committed_adopter)
    return documents._repository_documents(committed_adopter.root)


def _point(entries: tuple[str, ...], *states: dp.FillerState) -> dict[str, Any]:
    """A `union` point's document, resolved with `entries`, its fillers in `states`."""
    sources = (dp.FillerSource.DEFAULT, dp.FillerSource.CONTRIBUTION, dp.FillerSource.PROJECT)
    return dp.point_document(
        dp.ResolvedPoint(
            address="pkit::a-role:a-point",
            provider="a-provider",
            policy="union",
            inert_policy="fail",
            participation="always",
            fillers=tuple(
                dp.Filler(source, f"filler {i}", "value", state, "why")
                for i, (source, state) in enumerate(zip(sources, states, strict=False))
            ),
            outcome=dp.Outcome.RESOLVED,
            value=[{"id": entry} for entry in entries],
            entries=tuple(dp.Entry(entry, {"id": entry}, "a-provider") for entry in entries),
        )
    )


# --- living-docs ----------------------------------------------------------------------------

ld_artefacts, ld_binding, ld_doc_check, ld_readers, ld_mentions = load(
    "living-docs", "artefacts", "binding", "doc_check", "readers", "mentions"
)


def _parts(outcome: Outcome) -> int:
    return sum(len(artefact.parts) for artefact in outcome.artefacts)


def _skips_the_part(outcome: Outcome, base: Outcome) -> bool:
    """A part anchor of a kind no mention stands on is skipped, as the CLI reference has
    a reader skip a kind it does not read."""
    return isinstance(outcome, ld_artefacts.Reading) and _parts(outcome) == _parts(base) - 1


LIVING_DOCS_ARTEFACTS = Caller(
    name="living-docs's reading of `pkit friction artefacts --json`",
    contract=documents.FRICTION_ARTEFACTS,
    read=ld_artefacts.reading_of,
    untold=raises(ld_artefacts.Unreadable),
    nothing=lambda: ld_artefacts.read_artefacts(Path("."), run=_no_document),
    sets={"artefacts[].part_anchors[].kind": ld_artefacts.PART_KINDS},
    readings={
        # A root of an audience the capability serves no space in decides nothing here.
        "unknown:places[].encloses[]": same,
        "unknown:artefacts[].part_anchors[].kind": _skips_the_part,
    },
)

LIVING_DOCS_BINDING = Caller(
    name="living-docs's reading of `pkit rule-sets reach --json`",
    contract=documents.RULE_SETS_REACH,
    read=ld_binding.binding_of,
    untold=raises(ld_binding.Unreadable),
    nothing=lambda: ld_binding.read_binding(Path("."), run=_no_document),
)


def test_living_docs_reads_the_artefacts_document_as_its_contract_says(
    make_adopter_repo: Any,
) -> None:
    repo = documents._evidence_adopter(make_adopter_repo)
    for document in documents._artefacts_states(repo):
        check(LIVING_DOCS_ARTEFACTS, document)


def test_living_docs_reads_where_rules_bind_as_its_contract_says(make_adopter_repo: Any) -> None:
    for document in documents._reach_states(make_adopter_repo()):
        check(LIVING_DOCS_BINDING, document)


def _ld_obligations(pages: list[str], *, dormant: bool) -> Caller:
    readings = {"missing:schema_version": same}
    if dormant:
        # A dormant check owes nothing, so no state or kind it reports decides anything.
        readings |= {"unknown:report:state": same, "unknown:finding:kind": same}
    return Caller(
        name="living-docs's reading of `pkit friction check --all --json`",
        contract=documents.REPOSITORY_CHECK,
        read=lambda document: ld_doc_check.obligations(ld_doc_check.friction_of(document), pages),
        untold=raises(ld_doc_check.NoAnswer),
        nothing=lambda: ld_doc_check.read_friction(".", run=_no_document),
        # The check gained `schema_version` after it first shipped (the CLI reference).
        readings=readings,
    )


def _judged(document: dict[str, Any]) -> Iterator[tuple[dict[str, Any], list[str]]]:
    """`document` with only the artefacts the check judged, and their locations: what
    an artefact the check did not judge owes cannot be told, so such a document gives
    living-docs no answer to vary."""
    judged = [a for a in document["artefacts"] if a["state"] in ld_doc_check.JUDGED]
    yield {**document, "artefacts": judged}, [a["location"] for a in judged]


def test_living_docs_reads_the_whole_repository_check_as_its_contract_says(
    repository_checks: list[dict[str, Any]],
) -> None:
    for document in repository_checks:
        for judged, pages in _judged(document):
            check(_ld_obligations(pages, dormant=judged["dormant"]), judged)


LIVING_DOCS_HEAD = Caller(
    name="living-docs's reading of `pkit repository base --json`",
    contract=documents.REPOSITORY_BASE,
    read=ld_doc_check.commit_named,
    untold=raises(ld_doc_check.NoAnswer),
    nothing=lambda: ld_doc_check.has_commit(".", run=_no_document),
)


def test_living_docs_reads_whether_head_names_a_commit_as_its_contract_says() -> None:
    for document in _repository_bases():
        check(LIVING_DOCS_HEAD, document)


LIVING_DOCS_READERS = Caller(
    name="living-docs's reading of the readers point, `pkit connections resolve --json`",
    contract=documents.DATA_POINT,
    read=ld_readers.readers_of,
    untold=lambda outcome: not outcome.resolved,
    nothing=lambda: ld_readers.read_readers(run=_no_document),
    # The document gained the key after it first shipped (the CLI reference).
    readings={"missing:schema_version": same},
)


def test_living_docs_reads_the_readers_point_as_its_contract_says() -> None:
    taken, passed_over = dp.FillerState.TAKEN, dp.FillerState.PASSED_OVER
    for document in (
        _point(("user", "maintainer"), taken),
        _point(("user", "maintainer", "operator"), taken, taken, passed_over),
    ):
        check(LIVING_DOCS_READERS, document)


def _ld_lookup(ids: tuple[str, ...]) -> Caller:
    return Caller(
        name="living-docs's reading of `pkit refs lookup --json`",
        contract=documents.REFS_LOOKUP,
        read=lambda document: ld_mentions.lookups_of(document, ids),
        untold=raises(ld_mentions.Unreadable),
        nothing=lambda: ld_mentions.look_up(Path("."), run=_no_document)(ids),
    )


def test_living_docs_reads_where_records_lie_as_its_contract_says(
    make_adopter_repo: Any,
) -> None:
    make_adopter_repo()
    printed = documents._printed(
        documents._cli("refs", "lookup", documents.JSON_OPTION, *documents.LOOKED_UP)
    )
    check(_ld_lookup(documents.LOOKED_UP), printed)


# --- doc-examples ---------------------------------------------------------------------------

de_selection, de_run = load("doc-examples", "selection", "run-examples.py")

#: The types of the project's own the last of the artefacts states gives its places.
_PAGE_TYPES = ("plain", "starred", "ruled")

DOC_EXAMPLES_PAGES = Caller(
    name="doc-examples's reading of `pkit friction artefacts --json`",
    contract=documents.FRICTION_ARTEFACTS,
    read=lambda document: de_selection.select(
        de_selection.Config(types=_PAGE_TYPES), de_selection.artefacts_of(document)
    ),
    untold=raises(de_selection.Unreadable),
    nothing=lambda: de_selection.read_artefacts(Path("."), run=_no_document),
)


def test_doc_examples_reads_the_artefacts_document_as_its_contract_says(
    make_adopter_repo: Any,
) -> None:
    repo = documents._evidence_adopter(make_adopter_repo)
    for document in documents._artefacts_states(repo):
        check(DOC_EXAMPLES_PAGES, document)


#: The pages document `pkit doc-examples pages --json` prints, as the run reads it, until
#: the capability's documents have their contracts (#3315).
DOC_EXAMPLES_SELECTION = Contract(
    name="pkit doc-examples pages --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "root": "str",
                "types": "list",
                "types[]": "str",
                "pages": "list",
                "pages[]": "str",
                "setup": "list",
                "setup[]": "str",
                "path": "list",
                "path[]": "str",
                "environment": "object",
                "environment{}": "str|null",
                "placeholders": "object",
                "placeholders{}": "str",
            }
        )
    },
    data=frozenset({"environment", "placeholders"}),
)

DOC_EXAMPLES_RUN = Caller(
    name="doc-examples's run, reading `pkit doc-examples pages --json`",
    contract=DOC_EXAMPLES_SELECTION,
    read=de_run.selection_of,
    untold=raises(de_run.CannotRun),
    nothing=lambda: de_run.read_selection(Path("."), (sys.executable, "-c", "raise SystemExit(1)")),
)


def test_the_doc_examples_run_reads_its_pages_document_as_its_contract_says(
    tmp_path: Path,
) -> None:
    config = de_selection.Config(
        types=("living-docs:page",),
        setup=("make setup",),
        path=("bin",),
        environment={"LANG": "C", "HOME": None},
        placeholders={"VERSION": "cat VERSION"},
    )
    pages = de_selection.Pages(types=("living-docs:page",), paths=("README.md", "docs/a.md"))
    document = de_selection.document(tmp_path, config, pages)
    contracts.check(DOC_EXAMPLES_SELECTION, {"answer": [document]})
    check(DOC_EXAMPLES_RUN, document)


def _without_pkit(backbone: Any, read: Any) -> Any:
    """What `read` answers where every `pkit` call through `backbone` exits without a
    document."""
    run, backbone._run = backbone._run, _no_document
    try:
        return read()
    finally:
        backbone._run = run


# --- visual-communication -------------------------------------------------------------------

vc_looks, vc_backbone = load("visual-communication", "looks", "backbone")

VISUAL_COMMUNICATION_BASE = Caller(
    name="visual-communication's reading of `pkit repository base --json`",
    contract=documents.REPOSITORY_BASE,
    read=vc_looks.fork_of,
    untold=raises(vc_looks.pl.Refused),
    nothing=lambda: _without_pkit(vc_backbone, lambda: vc_looks.base_commit(Path("."), None)),
)


def test_visual_communication_reads_where_the_branch_left_its_base_as_its_contract_says() -> None:
    # A base that resolves to no commit gives no fork to vary: the look back refuses it.
    for document in _repository_bases()[:2]:
        check(VISUAL_COMMUNICATION_BASE, document)
