"""Each caller project-kit ships reads a document a command prints as ADR-097 point 3 says
(ADR-097 point 7).

Each test hands a caller the documents a command prints, from a real run or from the
function the command prints them through, and `tests/caller_contracts.py` varies each:
a key the caller does not know, each key it reads left out or null, a value of a set it
does not know, a version it does not know, and no document at all. The contracts are the
ones the command's own tests pin, `tests/test_backbone_documents.py`'s, a module it
gathers, or the capability's, so a caller is held to the same contract its command is.
Where those tests build a document holding every key, the caller is handed it too. The
deploy's pick, which no command prints, is the one document whose contract is pinned here.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import json
import subprocess
import sys
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import pytest

from project_kit import agent_runs as runs
from project_kit import data_points as dp
from project_kit import default_branch as db
from project_kit.agent_confinement import CLEAN, Check
from tests import analysis_repo as ar
from tests import document_contracts as contracts
from tests import test_backbone_documents as documents
from tests import test_backbone_documents_components as component_documents
from tests import test_backbone_documents_process as process_documents
from tests import test_backbone_documents_session as session_documents
from tests import test_doc_examples_documents as doc_examples_documents
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.backbone_documents import JSON_OPTION, document_of, invoke
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


#: Ids whose lookup prints each part of one: a record, a point of a record partly
#: superseded, a rule, and an id that resolves nowhere.
LOOKED_UP = ("COR-005", "COR-050#14", "RS-OPS-001", "NOPE-999")


def _lookups() -> dict[str, Any]:
    """`pkit refs lookup --json` of `LOOKED_UP`, in the project the test runs in."""
    return document_of(invoke("refs", "lookup", JSON_OPTION, *LOOKED_UP))


def _point(
    entries: tuple[str, ...], *states: dp.FillerState, inert_policy: str = "fail"
) -> dict[str, Any]:
    """A `union` point's document, resolved with `entries`, its fillers in `states`, under
    `inert_policy`: only `fallback` resolves with a filler `inert`."""
    sources = (dp.FillerSource.DEFAULT, dp.FillerSource.CONTRIBUTION, dp.FillerSource.PROJECT)
    return dp.point_document(
        dp.ResolvedPoint(
            address="pkit::a-role:a-point",
            provider="a-provider",
            policy="union",
            inert_policy=inert_policy,
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
    check(_ld_lookup(LOOKED_UP), _lookups())


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


DOC_EXAMPLES_RUN = Caller(
    name="doc-examples's run, reading `pkit doc-examples pages --json`",
    contract=doc_examples_documents.DOC_EXAMPLES_PAGES,
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
    check(DOC_EXAMPLES_RUN, de_selection.document(tmp_path, config, pages))


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
    printed = _lookups()
    check(_sa_records(LOOKED_UP), printed)
    check(_sa_citations(LOOKED_UP), printed)


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
    return document_of(invoke("friction", "artefacts", JSON_OPTION))


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
        # The point's policy is `fallback`: a filler that cannot answer leaves the rest.
        _point(("UC-001@c#suite.a",), taken, dp.FillerState.INERT, inert_policy="fallback"),
    ):
        check(SOFTWARE_ANALYSIS_EVIDENCE, document)


def test_software_analysis_keeps_the_evidence_of_the_fillers_beside_an_inert_one() -> None:
    document = _point(
        ("UC-001@c#suite.a",), dp.FillerState.TAKEN, dp.FillerState.INERT, inert_policy="fallback"
    )
    point = sa_evidence.evidence_of(document)
    assert point.resolved and list(point.entries) == ["UC-001@c#suite.a"]


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
    nothing=lambda: pm_decision_ids.lookup(list(LOOKED_UP), run=_no_document),
)


def test_project_management_reads_whether_a_record_holds_an_id_as_its_contract_says(
    make_adopter_repo: Any,
) -> None:
    make_adopter_repo()
    check(PROJECT_MANAGEMENT_DECISIONS, _lookups())


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


def _with_an_unlocated_finding(document: Mapping[str, Any]) -> dict[str, Any]:
    """`document` with a finding that names no artefact after its others, its `artefact`
    and `location` null, as the contract allows."""
    findings = document["findings"]
    unlocated = {**findings[0], "artefact": None, "location": None}
    return {**document, "findings": [*findings, unlocated]}


def test_project_management_drift_reads_the_whole_repository_check_as_its_contract_says(
    repository_checks: list[dict[str, Any]],
) -> None:
    for document in repository_checks:
        check(PROJECT_MANAGEMENT_DRIFT_CHECK, document)
    found = [document for document in repository_checks if document["findings"]]
    assert found, "no check the contract's test prints holds a finding"
    for document in found:
        check(PROJECT_MANAGEMENT_DRIFT_CHECK, _with_an_unlocated_finding(document))


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
    contract=component_documents.AGENTS_RULES,
    read=lambda document: pm_drift.forms_of(document, "c" * 40),
    untold=raises(pm_drift.Stop),
    nothing=lambda: pm_drift._json(["pkit", "agents", "rules"], Path("."), _no_document),
)


def test_project_management_drift_reads_the_rules_of_a_fixer_s_run_as_their_contract_says(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    make_adopter_repo(capabilities=("project-management",))
    projected = document_of(invoke("agents", "rules", component_documents._FIX_DRIFT, JSON_OPTION))
    check(PROJECT_MANAGEMENT_DRIFT_RULES, projected)


(pm_agent_runs,) = load("project-management", "agent_runs")


def _breached(outcome: Outcome, base: Outcome) -> bool:
    """A check of the clone pm cannot read is read as a breach, and its files set aside."""
    del base
    return isinstance(outcome, tuple) and outcome[0] is not None and outcome[0].breached


PROJECT_MANAGEMENT_AGENT_RUN = Caller(
    name="project-management's reading of `pkit agents run --json`",
    contract=component_documents.AGENTS_RUN,
    read=pm_agent_runs._from_document,
    untold=lambda outcome: isinstance(outcome, tuple) and outcome[0] is None,
    nothing=lambda: pm_agent_runs._from_document({}),
    readings={
        **{
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
        # A backbone older than the key prints none, and a cause pm does not know is
        # none it can name a way out for: the contract reads both as no cause.
        "missing:refusal_cause": same,
        "unknown:refusal_cause": same,
    },
)


def _run_documents() -> list[dict[str, Any]]:
    """A finished run, unconfined, and confined with all its parts as the run's contract
    test builds it, as the backbone prints them."""
    confined = component_documents._ended(runs.FINISHED, Check(CLEAN, ("a.md",)))
    unconfined = dataclasses.replace(
        confined, confined=False, commit=None, check=None, files=None, excluded=()
    )
    return [unconfined.as_json(), confined.as_json()]


def test_project_management_reads_an_agent_s_run_as_its_contract_says() -> None:
    for document in _run_documents():
        check(PROJECT_MANAGEMENT_AGENT_RUN, document)


pm_move_journal, pm_history, pm_move_issue = load(
    "project-management", "move_journal", "history.py", "move-issue.py"
)

#: An engine from before the setting gives no `journal_logging`, and kept a journal.
_BEFORE_THE_SETTING = {"missing:journal_logging": same, "missing:journal_logging.enabled": same}

PROJECT_MANAGEMENT_JOURNAL = Caller(
    name="project-management's reading of an issue's journal, `pkit process status --json`",
    contract=process_documents.PROCESS_STATUS,
    read=pm_move_journal.Journal.of,
    untold=lambda outcome: outcome is None,
    nothing=lambda: pm_move_journal.Journal.of(None),
    readings=_BEFORE_THE_SETTING,
)

PROJECT_MANAGEMENT_HISTORY = Caller(
    name="project-management's history of an issue, `pkit process status --json`",
    contract=process_documents.PROCESS_STATUS,
    read=lambda document: pm_history._read_journal_from(document),
    untold=lambda outcome: outcome is None,
    nothing=lambda: pm_history._read_journal_from(None),
    readings=_BEFORE_THE_SETTING,
)

PROJECT_MANAGEMENT_POSITION = Caller(
    name="project-management's reading of where an issue is, `pkit process status --json`",
    contract=process_documents.PROCESS_STATUS,
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
    # The status as the command prints it, less the keys pm does not read: a key a
    # caller ignores leaves its reading as it is, as each check here holds.
    document = {
        "position": {"state": "ready", "indeterminate": False},
        "journal_logging": {"enabled": True, "committed": False},
        "journal": [{"from": "Backlog", "to": "Ready", "actor": "someone"}],
    }
    for caller in (PROJECT_MANAGEMENT_JOURNAL, PROJECT_MANAGEMENT_HISTORY):
        check(caller, document)
    check(PROJECT_MANAGEMENT_POSITION, document)


(pm_accepted_records,) = load("project-management", "accepted_records")

PROJECT_MANAGEMENT_ACCEPTED_RECORDS = Caller(
    name="project-management's reading of `pkit decisions check-diff --json`",
    contract=documents.CHECK_DIFF,
    read=lambda document: pm_accepted_records.read(document, "check-diff"),
    untold=lambda outcome: outcome.problem is not None,
    nothing=lambda: pm_accepted_records.read(None, "check-diff"),
)


def test_project_management_reads_the_accepted_records_a_change_alters_as_its_contract_says() -> (
    None
):
    check(PROJECT_MANAGEMENT_ACCEPTED_RECORDS, documents._numbering_report())


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


#: The head a reading of the change check is for, as the module names it.
_PM_HEAD = "h" * 40


def _change_checked(document: Mapping[str, Any]) -> Any:
    """What project-management reads in the change check's document: what the person
    who authorises the merge is told, the counts and the paths the answers are on, the
    base the check compared against, and whether it fails and on which findings. A
    refusal to run a resolver away from the head is its own reading."""
    fa = pm_friction_answers
    found = fa.check_of(document, "`pkit friction check`", "it exited 1")
    if isinstance(found, fa._NoDocument):
        return found
    derived = fa.Derivation(_PM_HEAD, document=found, answers=tuple(fa._entries(found)))
    merged = fa.Merged(_PM_HEAD, document=found)
    return (
        tuple(fa.told(found)),
        fa.counted_told(found),
        tuple(fa.updated_in(found)),
        tuple(sorted(fa.listed_paths(found))),
        fa.documents(derived.answers),
        (derived.merge_base, derived.tip, derived.outdated, derived.unreadable),
        (merged.failed, tuple(finding["kind"] for finding in merged.failing)),
    )


def _not_named(outcome: Outcome, base: Outcome) -> bool:
    """A finding of a kind project-management does not know is not among those it names
    a refused merge by, and the check's `failed` still decides: nothing else changes."""
    if not isinstance(outcome, tuple):
        return False
    (failed, kinds), (was_failed, was_kinds) = outcome[-1], base[-1]
    return (
        outcome[:-1] == base[:-1]
        and failed == was_failed
        and UNKNOWN_VALUE not in kinds
        and set(kinds) <= set(was_kinds)
    )


PROJECT_MANAGEMENT_CHANGE_CHECK = Caller(
    name="project-management's reading of `pkit friction check --json`",
    contract=documents.FRICTION_CHECK,
    read=_change_checked,
    untold=lambda outcome: (
        isinstance(outcome, pm_friction_answers._NoDocument) and not outcome.elsewhere
    ),
    nothing=lambda: _without_pkit(
        pm_friction_answers.backbone,
        lambda: pm_friction_answers._run_check(None, "main", cwd=None),
    ),
    # The check gained `schema_version` after it first shipped (the CLI reference).
    readings={"missing:schema_version": same, "unknown:findings[].kind": _not_named},
)


def test_project_management_reads_the_change_check_as_its_contract_says() -> None:
    every = documents._change_check()
    for document in (every, {**every, "base": None}, documents._refusal()):
        check(PROJECT_MANAGEMENT_CHANGE_CHECK, document)


def test_project_management_knows_each_answer_and_refusal_the_change_check_names() -> None:
    """A value of a set the contract names is one project-management reads as itself."""
    fa, sets = pm_friction_answers, documents.FRICTION_CHECK.sets
    assert set(fa._WRITTEN_ANSWERS) == sets["written:answer"]
    assert set(fa._REVISIT_OUTCOMES) == sets["written:outcome"]
    assert set(fa._REFUSALS) == sets["refused.kind"]


def _covers_with_no_document() -> Any:
    """What `covers` answers where the base needs no fetch and `pkit friction since`
    exits without a document."""
    fa: Any = pm_friction_answers
    refresh, fa._refresh_base = fa._refresh_base, lambda _base: None
    try:
        return _without_pkit(fa.backbone, lambda: fa.covers(_PM_HEAD, _PM_HEAD, "main"))
    finally:
        fa._refresh_base = refresh


PROJECT_MANAGEMENT_SINCE = Caller(
    name="project-management's reading of `pkit friction since --json`",
    contract=documents.FRICTION_SINCE,
    read=lambda document: pm_friction_answers.coverage_of(document, "`pkit friction since`"),
    untold=lambda outcome: outcome.problem is not None,
    nothing=_covers_with_no_document,
)


def test_project_management_reads_what_changed_since_an_authorisation_as_its_contract_says(
    committed_adopter: AdopterRepo,
) -> None:
    repo = committed_adopter
    since = repo.head()
    repo.commit("an edit", {"docs/a.md": "A page.\n"})
    printed = document_of(invoke("friction", "since", since, "--base", "main", JSON_OPTION))
    fs = documents.fs
    commits = (fs.Step("h" * 40, merges_base=True),)
    outside = fs.Since(
        "s" * 40,
        "h" * 40,
        "main",
        "t" * 40,
        commits,
        ("answers/one.yaml",),
        (fs.Outside(None, "h" * 40, "a merge conflict"), fs.Outside("docs/a.md", "a" * 40, "why")),
        "the head does not descend from it",
    )
    inside = fs.Since("s" * 40, "h" * 40, "main", "t" * 40, commits, ("answers/one.yaml",))
    for since_ in (outside, inside):
        check(PROJECT_MANAGEMENT_SINCE, json.loads(fs.render_json(since_)))
    check(PROJECT_MANAGEMENT_SINCE, printed)


PROJECT_MANAGEMENT_ANSWERS_FOLDER = Caller(
    name="project-management's reading of the answers' folder in `pkit friction check --all "
    "--json`",
    contract=documents.REPOSITORY_CHECK,
    read=pm_friction_answers.folder_of,
    untold=lambda outcome: outcome is None,
    nothing=lambda: pm_friction_answers._folder_at(Path("."), _no_document),
    # The check gained `schema_version` after it first shipped (the CLI reference).
    readings={"missing:schema_version": same},
)


def test_project_management_reads_where_the_answers_are_kept_as_its_contract_says(
    repository_checks: list[dict[str, Any]],
) -> None:
    for document in repository_checks:
        check(PROJECT_MANAGEMENT_ANSWERS_FOLDER, document)


# --- the Claude Code adapter ----------------------------------------------------------------


def _runner() -> Any:
    """The agent runner, `run-agent.py`, loaded as its tests load it."""
    path = Path(__file__).resolve().parent.parent / ".pkit/adapters/claude-code/run-agent.py"
    spec = importlib.util.spec_from_file_location("claude_code_run_agent_for_callers", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


#: The pick the deploy's resolver writes for the runner (`_resolve_agent.pick_answer`),
#: a document of one component, the adapter, with no version of its own. The resolver is
#: the deploy's script, no command the adapter registers, so no command's tests pin it
#: and this one does.
RESOLVER_PICK = Contract(
    name="the deploy's resolver, `--pick <name>`",
    forms={
        "agent": Form(keys={"name": "str", "shipped": "bool", "agent": "str", "place": "str"}),
        "not shipped": Form(keys={"name": "str", "shipped": "bool"}),
        "no agent": Form(
            keys={
                "name": "str",
                "shipped": "bool",
                "untold": "str",
                "none": "str",
                "refused": "str",
            }
        ),
    },
)

cc_runner = _runner()

CLAUDE_CODE_PICK = Caller(
    name="the Claude Code runner's reading of the deploy's pick",
    contract=RESOLVER_PICK,
    read=lambda document: cc_runner.pick_of(document, "fixer"),
    untold=raises(cc_runner.Refused),
    nothing=lambda: cc_runner.picked_source(
        Path(sys.executable), Path("."), "fixer", {}, timeout=5
    ),
)


def test_the_claude_code_runner_reads_the_deploy_s_pick_as_its_resolver_writes_it() -> None:
    picked = {"name": "fixer", "shipped": True, "agent": ".pkit/agents/core/fixer.md"}
    agent, not_shipped = {**picked, "place": "core"}, {"name": "fixer", "shipped": False}
    no_agent = [
        {"name": "fixer", "shipped": True, key: "why"} for key in ("untold", "none", "refused")
    ]
    contracts.check(
        RESOLVER_PICK, {"agent": [agent], "not shipped": [not_shipped], "no agent": no_agent}
    )
    for document in (agent, not_shipped):
        check(CLAUDE_CODE_PICK, document)


(pm_processes, pm_document_keys) = load("project-management", "processes", "document_keys")

#: Process names as the backbone gives them, which the capability passes whole.
_P41 = "p1:aaaaaaaaaaaaaaaa:bbbbbbbbbbbbbbbb:-:41:100.0"
_P42 = "p1:aaaaaaaaaaaaaaaa:bbbbbbbbbbbbbbbb:-:42:200.0"

PROJECT_MANAGEMENT_SESSION = Caller(
    name="project-management's reading of `pkit harness session --json`",
    contract=session_documents.SESSION,
    read=pm_processes.session_of,
    untold=lambda outcome: (
        raises(pm_document_keys.Untold)(outcome) or getattr(outcome, "found", True) is False
    ),
    nothing=lambda: pm_processes.session(run=_no_document),
)


def test_project_management_reads_the_harness_session_as_its_contract_says() -> None:
    document = {
        "schema_version": 1,
        "adapter": "claude-code",
        "found": True,
        "why": None,
        "messaging": True,
        "process": _P41,
        "process_why": None,
        "address": "/tmp/cc-socks/41.sock",
        "address_why": None,
        "replies": [
            {"given": "uds:/tmp/cc-socks/42.sock", "address": "/tmp/cc-socks/42.sock", "why": None}
        ],
    }
    check(PROJECT_MANAGEMENT_SESSION, document)


PROJECT_MANAGEMENT_PROCESS_READ = Caller(
    name="project-management's reading of `pkit recorded-process read --json`",
    contract=session_documents.READ,
    read=lambda document: pm_processes.readings_of(document, 2),
    untold=lambda outcome: (
        raises(pm_document_keys.Untold)(outcome)
        or any(reading.state == pm_processes.CANNOT_TELL for reading in outcome)
    ),
    nothing=lambda: pm_processes.read([_P41], run=_no_document),
)


def test_project_management_reads_whether_a_recorded_process_runs_as_its_contract_says() -> None:
    document = {
        "schema_version": 1,
        "answers": [
            {"name": _P41, "state": "running", "by": "start-time", "why": "it runs"},
            {"name": _P42, "state": "ended", "by": "start-time", "why": "no process holds it"},
        ],
    }
    check(PROJECT_MANAGEMENT_PROCESS_READ, document)


PROJECT_MANAGEMENT_PROCESS_COMPARE = Caller(
    name="project-management's reading of `pkit recorded-process compare --json`",
    contract=session_documents.COMPARE,
    read=pm_processes.answer_of,
    untold=lambda outcome: (
        raises(pm_document_keys.Untold)(outcome) or outcome == pm_processes.CANNOT_TELL
    ),
    nothing=lambda: pm_processes.compare(_P41, _P42, run=_no_document),
)


def test_project_management_reads_whether_two_names_name_one_process_as_its_contract_says() -> None:
    document = {
        "schema_version": 1,
        "pairs": [{"names": [_P41, _P42], "answer": "two", "why": "they hold two ids"}],
    }
    check(PROJECT_MANAGEMENT_PROCESS_COMPARE, document)
