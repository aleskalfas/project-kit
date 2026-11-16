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

import dataclasses
import subprocess
import sys
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import pytest

from project_kit import agent_runs as runs
from project_kit import data_points as dp
from project_kit import decisions_check_diff as check_diff
from project_kit import default_branch as db
from project_kit.agent_confinement import Check
from project_kit.validators import Finding, Severity
from tests import analysis_repo as ar
from tests import document_contracts as contracts
from tests import test_backbone_documents as documents
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.caller_contracts import UNKNOWN_VALUE, Caller, Outcome, check, raises, same
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


# --- software-analysis ----------------------------------------------------------------------

sa_backbone, sa_model, sa_reading, sa_check, sa_evidence = load(
    "software-analysis", "backbone", "model", "reading", "check", "evidence"
)

SOFTWARE_ANALYSIS_SETTLED = Caller(
    name="software-analysis's reading of `pkit repository base --json`",
    contract=documents.REPOSITORY_BASE,
    read=sa_backbone.settled_of,
    untold=raises(sa_model.Unreadable),
    nothing=lambda: sa_backbone.settled(Path("."), run=_no_document),
)


def test_software_analysis_reads_what_is_settled_as_its_contract_says() -> None:
    for document in _repository_bases():
        check(SOFTWARE_ANALYSIS_SETTLED, document)


def _sa_reach(*, preview: bool) -> Caller:
    return Caller(
        name="software-analysis's reading of `pkit rule-sets reach --json`",
        contract=documents.RULE_SETS_REACH,
        read=lambda document: sa_backbone.reach_of(document, preview=preview),
        untold=raises(sa_model.Unreadable),
        nothing=lambda: sa_backbone.reach(Path("."), run=_no_document, preview=preview),
        # `preview` came within version 1: its absence is a backbone too old to preview,
        # whose answer is the one without the preview (the CLI reference).
        readings={} if preview else {"missing:preview": same},
    )


def test_software_analysis_reads_where_rules_bind_as_its_contract_says(
    make_adopter_repo: Any,
) -> None:
    for document in documents._reach_states(make_adopter_repo()):
        check(_sa_reach(preview=document["preview"]), document)


def _sa_records(asked: tuple[str, ...]) -> Caller:
    return Caller(
        name="software-analysis's reading of where records lie, `pkit refs lookup --json`",
        contract=documents.REFS_LOOKUP,
        read=lambda document: sa_backbone.record_files_of(document, asked),
        untold=raises(sa_model.Unreadable),
        nothing=lambda: sa_backbone.RecordFiles(Path("."), run=_no_document).file(asked[0]),
    )


def _sa_citations(asked: tuple[str, ...]) -> Caller:
    return Caller(
        name="software-analysis's reading of where citations lead, `pkit refs lookup --json`",
        contract=documents.REFS_LOOKUP,
        read=lambda document: sa_backbone.found_of(document, asked),
        untold=raises(sa_model.Unreadable),
        nothing=lambda: sa_backbone.lookup(Path("."), asked, run=_no_document),
    )


def test_software_analysis_reads_where_records_and_citations_lie_as_its_contract_says(
    make_adopter_repo: Any,
) -> None:
    make_adopter_repo()
    printed = documents._printed(
        documents._cli("refs", "lookup", documents.JSON_OPTION, *documents.LOOKED_UP)
    )
    check(_sa_records(documents.LOOKED_UP), printed)
    check(_sa_citations(documents.LOOKED_UP), printed)


def _analysis_document(repo: AdopterRepo) -> dict[str, Any]:
    """`pkit friction artefacts --json` over the analysis's places, holding each kind of
    artefact: an actor, terms, use cases in an area and out of one, a journey,
    requirements of each kind, a revalidation record held, and a file in no place."""
    ar.stamped(repo, "term", "suite")
    ar.stamped(repo, "use-case", "export", "--actor", "ACT-tester", "--area", "reports")
    requirement = "---\nid: {id}\ntitle: T\nstatus: active\n---\n\n# {id} · Quality · T\n"
    repo.write(
        {
            f"{ar.RECORDS}/2026-10-12-run-suite.md": "---\nchange: '#1'\n---\n",
            f"{ar.QUALITY}/REQ-004-quick.md": requirement.format(id="REQ-004"),
            f"{ar.FUNCTIONAL}/reports/REQ-002-approved.md": requirement.format(id="REQ-002"),
            f"{ar.CONSTRAINTS}/REQ-001-country.md": requirement.format(id="REQ-001"),
            f"{ar.ANALYSIS}/requirements/REQ-009-loose.md": requirement.format(id="REQ-009"),
        }
    )
    return documents._printed(documents._cli("friction", "artefacts", documents.JSON_OPTION))


def _not_looked(outcome: Outcome, base: Outcome) -> bool:
    """The location's unplaced files read as not looked at: the check says it could not
    look, and never that no such file is there (#1724)."""
    del base
    return getattr(outcome, "unplaced", ()) is None and outcome.outside_kinds is None


#: The keys of the analysis location's unplaced files: one the answer does not give in
#: full leaves that question alone untold, as the check reads it.
_UNPLACED = (
    "unplaced",
    "unplaced{}{}.path",
    "unplaced{}{}.files",
    "unplaced{}{}.files[].path",
    "unplaced{}{}.files[].excluded",
)

SOFTWARE_ANALYSIS_ANALYSIS = Caller(
    name="software-analysis's reading of `pkit friction artefacts --json`",
    contract=documents.FRICTION_ARTEFACTS,
    read=sa_model.analysis_of,
    untold=raises(sa_model.Unreadable),
    nothing=lambda: sa_backbone.read_analysis(Path("."), run=_no_document),
    readings={f"{way}:{name}": _not_looked for name in _UNPLACED for way in ("missing", "null")},
)


def test_software_analysis_reads_the_analysis_as_its_contract_says(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    del pkit_on_path
    repo = ar.installed(make_adopter_repo, monkeypatch, then=ar.prepare_seeded)
    check(SOFTWARE_ANALYSIS_ANALYSIS, _analysis_document(repo))


def _as_read(anchor: Any, *_path: Any) -> Any:
    """A changed path anchor as read against no files: unchanged."""
    return anchor


def _anchor_not_judged(outcome: Outcome, base: Outcome) -> bool:
    """An anchor in a state the reading does not know is kept, and read as not judged."""
    del base
    return any(not anchor.judged for anchor in getattr(outcome, "anchors", ()))


def _sa_evidence_of(artefact: str) -> Caller:
    return Caller(
        name="software-analysis's reading of `pkit friction explain --json` for the evidence",
        contract=documents.FRICTION_EXPLAIN,
        read=lambda document: sa_reading.reading_of(
            sa_backbone.explained_of(document), artefact, _as_read
        ),
        untold=raises(sa_model.Unreadable),
        nothing=lambda: sa_backbone.explain(Path("."), artefact, run=_no_document),
        # The document gained `schema_version` after it first shipped (the CLI reference).
        readings={"missing:schema_version": same, "unknown:anchors[].state": _anchor_not_judged},
    )


SOFTWARE_ANALYSIS_REVALIDATED = Caller(
    name="software-analysis's reading of `pkit friction explain --json` for its revalidations",
    contract=documents.FRICTION_EXPLAIN,
    read=lambda document: sa_check.last_revalidated(sa_backbone.explained_of(document)),
    untold=raises(sa_model.Unreadable),
    nothing=lambda: sa_backbone.explain(Path("."), "guide", run=_no_document),
    # The document gained the key after it first shipped (the CLI reference).
    readings={"missing:schema_version": same},
)


@pytest.fixture
def explained(committed_adopter: AdopterRepo, answers_in_files: None) -> list[dict[str, Any]]:
    """`pkit friction explain --json` as its contract's test builds it: the guide as a
    run gives it, excluded with every part, and with its answers read alone."""
    del answers_in_files
    documents._friction_history(committed_adopter)
    return documents._explain_documents(committed_adopter.root)


def test_software_analysis_reads_an_explanation_as_its_contract_says(
    explained: list[dict[str, Any]],
) -> None:
    for document in explained:
        check(SOFTWARE_ANALYSIS_REVALIDATED, document)
        if document["state"] in sa_reading._READ_STATES:
            check(_sa_evidence_of("guide"), document)


SOFTWARE_ANALYSIS_EVIDENCE = Caller(
    name="software-analysis's reading of the evidence point, `pkit connections resolve --json`",
    contract=documents.DATA_POINT,
    read=sa_evidence.evidence_of,
    untold=lambda outcome: not outcome.resolved,
    nothing=lambda: sa_evidence.read_evidence(Path("."), run=_no_document),
    # The document gained the key after it first shipped (the CLI reference).
    readings={"missing:schema_version": same},
)


def test_software_analysis_reads_the_evidence_point_as_its_contract_says() -> None:
    taken, passed_over = dp.FillerState.TAKEN, dp.FillerState.PASSED_OVER
    for document in (
        _point(("UC-001@c#suite.a",), taken),
        _point(("UC-001@c#suite.a", "UC-002@c#suite.b"), taken, passed_over),
    ):
        check(SOFTWARE_ANALYSIS_EVIDENCE, document)


# --- project-management ---------------------------------------------------------------------

(pm_default_branch, pm_ruled, pm_decision_ids, pm_doc_check, pm_fixers, pm_drift) = load(
    "project-management",
    "default_branch",
    "ruled_artefacts",
    "decision_ids",
    "doc_check",
    "fixers",
    "drift",
)

PROJECT_MANAGEMENT_BASE = Caller(
    name="project-management's reading of `pkit repository base --json`",
    contract=documents.REPOSITORY_BASE,
    read=pm_default_branch.reading_of,
    untold=raises(pm_default_branch.Unanswered),
    nothing=lambda: pm_default_branch._ask(None, _no_document),
)


def test_project_management_reads_the_default_branch_and_base_as_its_contract_says() -> None:
    for document in _repository_bases():
        check(PROJECT_MANAGEMENT_BASE, document)


PROJECT_MANAGEMENT_ALTERED = Caller(
    name="project-management's reading of `pkit rule-sets altered --json`",
    contract=documents.RULE_SETS_ALTERED,
    read=pm_ruled.alteration_of,
    untold=lambda outcome: not outcome.ok,
    nothing=lambda: pm_ruled.ruled_altered("a" * 40, "b" * 40, run=_no_document),
)


def test_project_management_reads_what_a_change_altered_as_its_contract_says(
    make_adopter_repo: Any,
) -> None:
    for document in documents._altered_documents(make_adopter_repo()):
        check(PROJECT_MANAGEMENT_ALTERED, document)


PROJECT_MANAGEMENT_DECISIONS = Caller(
    name="project-management's reading of `pkit refs lookup --json`",
    contract=documents.REFS_LOOKUP,
    read=pm_decision_ids.reading_of,
    untold=lambda outcome: isinstance(outcome, pm_decision_ids.NotChecked),
    nothing=lambda: pm_decision_ids.lookup(list(documents.LOOKED_UP), run=_no_document),
)


def test_project_management_reads_whether_a_record_holds_an_id_as_its_contract_says(
    make_adopter_repo: Any,
) -> None:
    make_adopter_repo()
    printed = documents._printed(
        documents._cli("refs", "lookup", documents.JSON_OPTION, *documents.LOOKED_UP)
    )
    check(PROJECT_MANAGEMENT_DECISIONS, printed)


def _obligations(document: Mapping[str, Any]) -> Any:
    """What pm's documentation check takes from the point: whether it resolved, its
    obligations by how each is met, and its removals."""
    point = pm_doc_check.parse_point(document)
    if not point.resolved:
        return point
    split = pm_doc_check.split(point, "project-management")
    return point.resolved, split, pm_doc_check.removed(point), point.inert


def _obligation_point(*states: dp.FillerState) -> dict[str, Any]:
    """The doc-check point resolved with an obligation from pm's own filler, a
    contributed one and a removal, its fillers in `states`."""
    obligations = (("o1", "project-management"), ("o2", "a-capability"))
    document = _point((), *states)
    document["entries"] = [
        {
            "id": entry,
            "origin": origin,
            "replaces": [],
            "value": {"source": "mapping" if origin == "project-management" else origin},
        }
        for entry, origin in obligations
    ]
    document["removals"] = [{"id": "o3", "reason": "not here", "removed_from": ["a-capability"]}]
    return document


PROJECT_MANAGEMENT_DOC_CHECK = Caller(
    name="project-management's reading of the doc-check point, `pkit connections resolve`",
    contract=documents.DATA_POINT,
    read=_obligations,
    untold=lambda outcome: (
        raises(pm_doc_check.PointUnreadable)(outcome) or getattr(outcome, "resolved", True) is False
    ),
    nothing=lambda: pm_doc_check.read_point(run=_no_document),
    # The document gained the key after it first shipped (the CLI reference).
    readings={"missing:schema_version": same},
)


def test_project_management_reads_the_documentation_obligations_as_their_contract_says() -> None:
    taken, passed_over = dp.FillerState.TAKEN, dp.FillerState.PASSED_OVER
    for document in (_obligation_point(taken), _obligation_point(taken, passed_over)):
        check(PROJECT_MANAGEMENT_DOC_CHECK, document)


def _fixer_point(*states: dp.FillerState) -> dict[str, Any]:
    """The fixers point resolved with a project's entry and a contribution's, its
    fillers in `states`."""
    document = _point((), *states)
    document["entries"] = [
        {"id": kind, "origin": origin, "replaces": [], "value": {"id": kind, "agent": "fixer"}}
        for kind, origin in (("guide", "project filler"), ("page", "a-capability"))
    ]
    return document


PROJECT_MANAGEMENT_FIXERS = Caller(
    name="project-management's reading of the fixers point, `pkit connections resolve`",
    contract=documents.DATA_POINT,
    read=pm_fixers.point_of,
    untold=lambda outcome: (
        raises(pm_fixers.Unreadable)(outcome) or getattr(outcome, "resolved", True) is False
    ),
    nothing=lambda: pm_fixers.read_point(run=_no_document),
    # The document gained the key after it first shipped (the CLI reference).
    readings={"missing:schema_version": same},
)


def test_project_management_reads_the_fixers_point_as_its_contract_says() -> None:
    taken, passed_over = dp.FillerState.TAKEN, dp.FillerState.PASSED_OVER
    for document in (_fixer_point(taken), _fixer_point(taken, passed_over)):
        check(PROJECT_MANAGEMENT_FIXERS, document)


PROJECT_MANAGEMENT_TYPES = Caller(
    name="project-management's reading of the types `pkit friction artefacts --json` lists",
    contract=documents.FRICTION_ARTEFACTS,
    read=pm_fixers.types_of,
    untold=raises(pm_fixers.Unreadable),
    nothing=lambda: pm_fixers.read_types(run=_no_document),
)


def test_project_management_reads_the_declared_types_as_their_contract_says(
    make_adopter_repo: Any,
) -> None:
    repo = documents._evidence_adopter(make_adopter_repo)
    for document in documents._artefacts_states(repo):
        check(PROJECT_MANAGEMENT_TYPES, document)


def _not_judged(outcome: Outcome, base: Outcome) -> bool:
    """A state pm does not know is kept, and the plan lists its artefact as not judged."""
    del base
    return isinstance(outcome, tuple) and (
        any(state == UNKNOWN_VALUE for _location, state in outcome[0])
        or any("could not judge" in why for why in outcome[1].values())
    )


PROJECT_MANAGEMENT_DRIFT_CHECK = Caller(
    name="project-management's drift reading of `pkit friction check --all --json`",
    contract=documents.REPOSITORY_CHECK,
    read=lambda document: pm_drift.judged(pm_drift.checked_of(document)),
    untold=raises(pm_drift.Stop),
    nothing=lambda: pm_drift._json(["pkit", "friction", "check"], Path("."), _no_document),
    # The check gained `schema_version` after it first shipped (the CLI reference).
    readings={
        "missing:schema_version": same,
        "unknown:report:state": _not_judged,
        "unknown:finding:kind": _not_judged,
    },
)


def test_project_management_drift_reads_the_whole_repository_check_as_its_contract_says(
    repository_checks: list[dict[str, Any]],
) -> None:
    for document in repository_checks:
        check(PROJECT_MANAGEMENT_DRIFT_CHECK, document)


def _upstreams(document: Mapping[str, Any]) -> dict[str, tuple[Any, ...]]:
    """What drift reads of each artefact discovery found: its id, type, whether its type
    is tied, and the artefacts it anchors on."""
    by_key = pm_drift._artefact_index(pm_drift.listed_of(document))
    return {
        key: (
            item["id"],
            item["type"],
            bool(item["type_conflict"]),
            tuple(pm_drift._upstreams(item, by_key)),
        )
        for key, item in by_key.items()
    }


PROJECT_MANAGEMENT_DRIFT_ARTEFACTS = Caller(
    name="project-management's drift reading of `pkit friction artefacts --json`",
    contract=documents.FRICTION_ARTEFACTS,
    read=_upstreams,
    untold=raises(pm_drift.Stop),
    nothing=lambda: pm_drift.upstreams_at(Path("."), run=_no_document),
)


def test_project_management_drift_reads_the_artefacts_document_as_its_contract_says(
    make_adopter_repo: Any,
) -> None:
    repo = documents._evidence_adopter(make_adopter_repo)
    for document in documents._artefacts_states(repo):
        check(PROJECT_MANAGEMENT_DRIFT_ARTEFACTS, document)


PROJECT_MANAGEMENT_DRIFT_EXPLAIN = Caller(
    name="project-management's drift reading of `pkit friction explain --json`",
    contract=documents.FRICTION_EXPLAIN,
    read=lambda document: (
        pm_drift.friction_fingerprint(pm_drift.explained_of(document)),
        pm_drift.commits_behind(document),
    ),
    untold=raises(pm_drift.Stop),
    nothing=lambda: pm_drift.explain(Path("."), "guide", run=_no_document),
    # The document gained `schema_version` after it first shipped (the CLI reference).
    readings={"missing:schema_version": same},
)


def test_project_management_drift_reads_an_explanation_as_its_contract_says(
    explained: list[dict[str, Any]],
) -> None:
    for document in explained:
        check(PROJECT_MANAGEMENT_DRIFT_EXPLAIN, document)


PROJECT_MANAGEMENT_DRIFT_RULES = Caller(
    name="project-management's drift reading of `pkit agents rules --json`",
    contract=documents.AGENTS_RULES,
    read=lambda document: pm_drift.forms_of(document, "c" * 40),
    untold=raises(pm_drift.Stop),
    nothing=lambda: pm_drift._json(["pkit", "agents", "rules"], Path("."), _no_document),
)


def test_project_management_drift_reads_the_rules_of_a_fixer_s_run_as_their_contract_says(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    answered, _refused = documents._rules_documents(monkeypatch)
    check(PROJECT_MANAGEMENT_DRIFT_RULES, answered)


(pm_agent_runs,) = load("project-management", "agent_runs")

_RUN = {
    "schema_version": "int",
    "agent": "str",
    "runner": "str|null",
    "ending": "str",
    "exit_code": "int|null",
    "output": "str",
    "diagnostics": "str",
    "reason": "str",
    "refused_calls": "list",
    "confined": "bool",
    "excluded": "list",
}

#: The document `pkit agents run --json` prints, as the CLI reference gives it ("Agent
#: runs"), until the command's documents have their contracts (#3315). An unconfined
#: run prints the confined run's keys too, each null or empty.
AGENTS_RUN = Contract(
    name="pkit agents run --json",
    version=1,
    forms={
        "unconfined": Form(
            keys={**_RUN, "commit": "null", "check": "null", "files": "null"},
        ),
        "confined": Form(
            keys={
                **_RUN,
                "commit": "str",
                "check": "object|null",
                "check.verdict": "str",
                "check.changes": "list",
                "check.changes[]": "str",
                "files": "str|null",
                "excluded[]": "list",
                "excluded[][]": "str",
            }
        ),
    },
    # The calls the harness refused, as the runner reports them: pm prints each as it
    # comes, and reads no key of one as an answer.
    payloads=frozenset({"refused_calls"}),
    sets={
        "ending": frozenset({"finished", "not-started", "timed-out", "refused", "no-answer"}),
        "check.verdict": frozenset({"clean", "breach", "not-run"}),
    },
)


def _breached(outcome: Outcome, base: Outcome) -> bool:
    """A check of the clone pm cannot read is read as a breach, and its files set aside."""
    del base
    return isinstance(outcome, tuple) and outcome[0] is not None and outcome[0].breached


PROJECT_MANAGEMENT_AGENT_RUN = Caller(
    name="project-management's reading of `pkit agents run --json`",
    contract=AGENTS_RUN,
    read=pm_agent_runs._from_document,
    untold=lambda outcome: isinstance(outcome, tuple) and outcome[0] is None,
    nothing=lambda: pm_agent_runs._from_document({}),
    readings={
        f"{way}:{name}": _breached
        for way, name in (
            ("missing", "check"),
            ("missing", "check.verdict"),
            ("null", "check.verdict"),
            ("unknown", "check.verdict"),
            ("missing", "check.changes"),
            ("null", "check.changes"),
        )
    },
)


def _run_documents() -> dict[str, list[dict[str, Any]]]:
    """A run of each ending, and a confined run of each verdict, as the backbone
    prints them."""
    refused = ({"tool": "Bash", "input": "rm -rf /"},)
    finished = runs.AgentRun(
        "reviewer", runs.FINISHED, "claude-code", 0, "done", refused_calls=refused
    )
    unconfined = [finished.as_json()] + [
        runs.AgentRun("reviewer", ending, None, None, reason="why").as_json()
        for ending in sorted(set(runs.ENDINGS) - {runs.FINISHED})
    ]
    confined = [
        dataclasses.replace(
            finished,
            confined=True,
            commit="c" * 40,
            check=check,
            files=None if check is None else Path("/tmp/files"),
            excluded=(("uv", "run", "x"),),
        ).as_json()
        for check in (
            Check("clean", ("a.md",)),
            Check("breach", ("b.md",)),
            Check("not-run"),
            None,
        )
    ]
    return {"unconfined": unconfined, "confined": confined}


def test_project_management_reads_an_agent_s_run_as_its_contract_says() -> None:
    held = _run_documents()
    contracts.check(AGENTS_RUN, held)
    for form in held.values():
        check(PROJECT_MANAGEMENT_AGENT_RUN, form[0])


pm_move_journal, pm_history, pm_move_issue = load(
    "project-management", "move_journal", "history.py", "move-issue.py"
)

#: The keys of `pkit process status --json` pm reads of an issue, as the process
#: engine's page gives them ("The operations"), until the command's documents have
#: their contracts (#3315). The journal's entries are the engine's records, each of a
#: kind of its own, read as the engine writes them.
PROCESS_STATUS = Contract(
    name="pkit process status --json",
    forms={
        "status": Form(
            keys={
                "position": "object",
                "position.state": "str|null",
                "position.indeterminate": "bool",
                "journal_logging": "object",
                "journal_logging.enabled": "bool",
                "journal_logging.committed": "bool",
                "journal": "list",
            }
        )
    },
    payloads=frozenset({"journal"}),
)

#: An engine from before the setting gives no `journal_logging`, and kept a journal.
_BEFORE_THE_SETTING = {"missing:journal_logging": same, "missing:journal_logging.enabled": same}

PROJECT_MANAGEMENT_JOURNAL = Caller(
    name="project-management's reading of an issue's journal, `pkit process status --json`",
    contract=PROCESS_STATUS,
    read=pm_move_journal.Journal.of,
    untold=lambda outcome: outcome is None,
    nothing=lambda: pm_move_journal.Journal.of(None),
    readings=_BEFORE_THE_SETTING,
)

PROJECT_MANAGEMENT_HISTORY = Caller(
    name="project-management's history of an issue, `pkit process status --json`",
    contract=PROCESS_STATUS,
    read=lambda document: pm_history._read_journal_from(document),
    untold=lambda outcome: outcome is None,
    nothing=lambda: pm_history._read_journal_from(None),
    readings=_BEFORE_THE_SETTING,
)

PROJECT_MANAGEMENT_POSITION = Caller(
    name="project-management's reading of where an issue is, `pkit process status --json`",
    contract=PROCESS_STATUS,
    read=lambda document: (
        pm_move_issue._position_from_status(document),
        pm_move_issue._journal_length_from_status(document),
    ),
    # Where the engine cannot tell where the issue is, or how long its journal is, the
    # move falls back to its own inference, and the audit key to none.
    untold=lambda outcome: outcome == (None, None),
    nothing=lambda: (
        pm_move_issue._position_from_status(None),
        pm_move_issue._journal_length_from_status(None),
    ),
    readings={
        **{
            f"{way}:{name}": lambda outcome, base: outcome == (None, base[1])
            for way in ("missing", "null")
            for name in ("position", "position.state", "position.indeterminate")
        },
        **{
            name: lambda outcome, base: outcome == (base[0], None)
            for name in (
                "missing:journal",
                "null:journal",
                "null:journal_logging",
                "null:journal_logging.enabled",
            )
        },
        **_BEFORE_THE_SETTING,
    },
)


def test_project_management_reads_an_issue_s_status_as_its_contract_says() -> None:
    document = {
        "position": {"state": "ready", "indeterminate": False},
        "journal_logging": {"enabled": True, "committed": False},
        "journal": [{"from": "Backlog", "to": "Ready", "actor": "someone"}],
    }
    indeterminate = {**document, "position": {"state": None, "indeterminate": True}}
    contracts.check(PROCESS_STATUS, {"status": [document, indeterminate]})
    for caller in (PROJECT_MANAGEMENT_JOURNAL, PROJECT_MANAGEMENT_HISTORY):
        check(caller, document)
    check(PROJECT_MANAGEMENT_POSITION, document)


(pm_accepted_records,) = load("project-management", "accepted_records")

#: The document `pkit decisions check-diff --json` prints, as the decisions README
#: gives it ("Refining an accepted record"), until the command's documents have their
#: contracts (#3315).
DECISIONS_CHECK_DIFF = Contract(
    name="pkit decisions check-diff --json",
    version=1,
    forms={
        "compared": Form(
            keys={
                "schema_version": "int",
                "base": "object|null",
                "base.ref": "str",
                "base.fork": "str",
                "base.tip": "str",
                "head": "str|null",
                "compared": "int",
                "errors": "int",
                "findings": "list",
                "findings[]": "object",
                "findings[].severity": "str",
                "findings[].location": "str",
                "findings[].message": "str",
                "accepted_changes": "list",
                "accepted_changes[]": "object",
                "accepted_changes[].path": "str",
                "accepted_changes[].record": "str",
                "accepted_changes[].points": "list",
                "accepted_changes[].points[]": "object",
                "accepted_changes[].points[].id": "str",
                "accepted_changes[].points[].change": "str",
                "accepted_changes[].points[].title": "str",
                "accepted_changes[].fields": "list",
                "accepted_changes[].fields[]": "str",
                "accepted_changes[].shared_text": "bool",
                "accepted_changes[].other_text": "bool",
                "accepted_changes[].list_form": "bool",
                "accepted_changes[].removed": "bool",
            }
        )
    },
    sets={
        "findings[].severity": frozenset({"error", "warning"}),
        "accepted_changes[].points[].change": frozenset(
            {check_diff.ADDED, check_diff.ALTERED, check_diff.RETIRED, check_diff.REMOVED}
        ),
    },
)

PROJECT_MANAGEMENT_ACCEPTED_RECORDS = Caller(
    name="project-management's reading of `pkit decisions check-diff --json`",
    contract=DECISIONS_CHECK_DIFF,
    read=lambda document: pm_accepted_records.read(document, "check-diff"),
    untold=lambda outcome: outcome.problem is not None,
    nothing=lambda: pm_accepted_records.read(None, "check-diff"),
)


def test_project_management_reads_the_accepted_records_a_change_alters_as_its_contract_says() -> (
    None
):
    changed = check_diff.ChangedRecord(
        "decisions/project/PRJ-001-x.md",
        "PRJ-001",
        points=tuple(
            check_diff.PointChange(str(n), change, f"Point {n}")
            for n, change in enumerate(
                sorted(DECISIONS_CHECK_DIFF.sets["accepted_changes[].points[].change"]), start=1
            )
        ),
        fields=("title",),
        shared=True,
    )
    report = check_diff.Report(
        "origin/main",
        "f" * 40,
        "t" * 40,
        3,
        (
            Finding("decisions/project/PRJ-002-y.md", "a point taken", Severity.ERROR),
            Finding("decisions/project/PRJ-003-z.md", "a point moved", Severity.WARNING),
        ),
        (
            changed,
            check_diff.ChangedRecord("decisions/project/PRJ-004-w.md", "PRJ-004", removed=True),
        ),
    )
    document = check_diff.as_json(report, None)
    contracts.check(
        DECISIONS_CHECK_DIFF, {"compared": [document, check_diff.as_json(None, "h" * 40)]}
    )
    check(PROJECT_MANAGEMENT_ACCEPTED_RECORDS, document)


(pm_friction_answers,) = load("project-management", "friction_answers")

PROJECT_MANAGEMENT_DISCOVERY = Caller(
    name="project-management's reading of `pkit friction artefacts --json --at`",
    contract=documents.FRICTION_ARTEFACTS,
    read=lambda document: pm_friction_answers.discovery_of(document, "artefacts"),
    untold=lambda outcome: isinstance(outcome, str),
    nothing=lambda: pm_friction_answers.discovery_of(None, "artefacts"),
)


def test_project_management_reads_what_the_change_check_is_asked_about_as_its_contract_says(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = documents._evidence_adopter(make_adopter_repo)
    for document in documents._artefacts_states(repo):
        check(PROJECT_MANAGEMENT_DISCOVERY, document)
