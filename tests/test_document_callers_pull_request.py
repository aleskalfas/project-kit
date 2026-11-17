"""project-management reads each `pkit pull-request` document as ADR-097 point 3 says
(ADR-097 point 7).

`_lib/merge_queue.py` reads seven of the noun's eight documents, each through a reading
of its own: `read`, `squash-defaults`, `merge`, `enqueue`, `dequeue`, `wait` and
`delete-branch`. It reads no `land` document: no project-management command lands
through that subcommand. Each test hands a reading the documents the command prints
them through, as `tests/test_backbone_documents_pull_request.py` builds them, and
`tests/caller_contracts.py` varies each against the contract that module pins. A
document whose `unreadable` says GitHub could not be read gives no answer to vary, so
none is handed here: `tests/test_pm_merge_queue_lib.py` holds that it is unreadable.
`tests/test_document_callers.py` holds the other shipped callers.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Iterator
from typing import Any

import pytest

from project_kit import pull_request_landing as landing
from tests import test_backbone_documents_pull_request as documents
from tests.caller_contracts import UNKNOWN_VALUE, Caller, Outcome, Raised, Reading, check, raises
from tests.in_process import load

(mq,) = load("project-management", "merge_queue")

PR = documents.PR
HEAD = documents.HEAD


def _no_lines(*_args: Any, **_kwargs: Any) -> Iterator[dict[str, Any]]:
    """A run of `pkit pull-request` that wrote no document."""
    yield from ()


def _answering_nothing(read: Callable[[], Any]) -> Any:
    """What `read` answers where the backbone's run writes no document."""
    module: Any = mq
    answers, module._answers = module._answers, _no_lines
    try:
        return read()
    finally:
        module._answers = answers


def _as_reading(outcome: Outcome) -> Any:
    """The reading an outcome holds: a wait's end holds one."""
    return outcome.reading if isinstance(outcome, mq.Wait) else outcome


def _carries(field: str) -> Reading:
    """A word of GitHub's that pm decides nothing on, kept as GitHub gives it: the
    reading is the one it was made from, but for that word."""

    def reading(outcome: Outcome, base: Outcome) -> bool:
        if isinstance(outcome, Raised) or type(outcome) is not type(base):
            return False
        if isinstance(base, mq.Wait) and outcome.ended != base.ended:
            return False
        found, was = _as_reading(outcome), _as_reading(base)
        kept = dataclasses.replace(found, **{field: getattr(was, field)})
        return getattr(found, field) == UNKNOWN_VALUE and kept == was

    return reading


#: GitHub's own words a reading passes on, which pm keeps and decides nothing on.
_GITHUB_WORDS = {
    f"unknown:reading:{field}": _carries(field)
    for field in ("pr_state", "merge_method", "entry_state")
}


def test_project_management_reads_where_a_pr_stands_as_its_contract_says(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caller = Caller(
        name="project-management's reading of `pkit pull-request read --json`",
        contract=documents.READ,
        read=mq.reading_of,
        untold=raises(mq.Unreadable),
        nothing=lambda: _answering_nothing(lambda: mq.read(PR, {})),
        readings=_GITHUB_WORDS,
    )
    for reading in documents._readings():
        check(caller, documents._read_as(monkeypatch, reading))


SQUASH_DEFAULTS = Caller(
    name="project-management's reading of `pkit pull-request squash-defaults --json`",
    contract=documents.SQUASH_DEFAULTS,
    read=mq.squash_defaults_of,
    untold=raises(mq.Unreadable),
    nothing=lambda: _answering_nothing(lambda: mq.squash_commit_defaults({})),
)


def test_project_management_reads_the_squash_commit_defaults_as_their_contract_says() -> None:
    for title in sorted(documents._SQUASH_TITLES):
        for message in sorted(documents._SQUASH_MESSAGES):
            gh = documents._defaults(title, message)
            check(SQUASH_DEFAULTS, landing.squash_defaults_document(gh=gh))


def _carries_the_verdict(outcome: Outcome, base: Outcome) -> bool:
    """The guard's verdict is said as the guard words it: pm decides nothing on it."""
    if not isinstance(outcome, mq.Outcome) or outcome.guard is None or base.guard is None:
        return False
    kept = dataclasses.replace(outcome, guard={**outcome.guard, "verdict": base.guard["verdict"]})
    return outcome.guard["verdict"] == UNKNOWN_VALUE and kept == base


def _request(command: str, contract: Any) -> Caller:
    return Caller(
        name=f"project-management's reading of `pkit pull-request {command} --json`",
        contract=contract,
        read=lambda document: mq.outcome_of(document, command),
        untold=raises(mq.Unreadable),
        nothing=lambda: _answering_nothing(lambda: mq.request([command, str(PR)], {})),
        readings={"unknown:guard:verdict": _carries_the_verdict},
    )


@pytest.mark.parametrize(
    ("command", "contract", "kinds"),
    [
        ("merge", documents.MERGE, documents._REQUEST_KINDS),
        ("enqueue", documents.ENQUEUE, documents._REQUEST_KINDS),
        ("dequeue", documents.DEQUEUE, documents._DEQUEUE_KINDS),
    ],
)
def test_project_management_reads_what_a_request_came_to_as_its_contract_says(
    command: str, contract: Any, kinds: frozenset[str]
) -> None:
    caller = _request(command, contract)
    for document in documents._request_documents(kinds):
        check(caller, document)


DELETE_BRANCH = Caller(
    name="project-management's reading of `pkit pull-request delete-branch --json`",
    contract=documents.DELETE_BRANCH,
    read=mq.deletion_of,
    untold=raises(mq.Unreadable),
    nothing=lambda: _answering_nothing(lambda: mq.deletion([str(PR), "--expect", HEAD], {})),
)


def test_project_management_reads_what_a_branch_s_deletion_came_to_as_its_contract_says() -> None:
    _cleared_all, refusal = documents._guards()
    for index, deletion in enumerate(documents._deletions()):
        built = landing.deletion_document(PR, HEAD, deletion, documents._cleared(index))
        check(DELETE_BRANCH, built)
    check(DELETE_BRANCH, landing.deletion_refusal_document(PR, HEAD, refusal))


WAIT = Caller(
    name="project-management's reading of `pkit pull-request wait --json`",
    contract=documents.WAIT,
    read=mq.wait_line_of,
    untold=raises(mq.Unreadable),
    nothing=lambda: _answering_nothing(
        lambda: mq.wait_for_merge(PR, {}, timeout_seconds=0, on_change=lambda reading: None)
    ),
    readings=_GITHUB_WORDS,
)


def test_project_management_reads_each_line_of_a_wait_as_its_contract_says() -> None:
    readings = documents._readings()
    for reading in readings:
        check(WAIT, landing.wait_reading_document(PR, reading))
    ends = (landing.MERGED, landing.STILL_QUEUED, landing.LEFT, landing.HEAD_MOVED)
    for ended, reading in zip(ends, readings, strict=False):
        check(WAIT, landing.wait_end_document(PR, landing.Wait(ended, reading)))


def test_project_management_knows_each_value_the_contracts_name() -> None:
    """A value of a set the contract names is one pm reads as itself: none of them is
    read as a value it does not know."""
    assert set(mq._SQUASH_TITLES) == documents._SQUASH_TITLES
    assert set(mq._SQUASH_MESSAGES) == documents._SQUASH_MESSAGES
    assert set(mq._REQUEST_KINDS["merge"]) == documents._REQUEST_KINDS
    assert set(mq._REQUEST_KINDS["enqueue"]) == documents._REQUEST_KINDS
    assert set(mq._REQUEST_KINDS["dequeue"]) == documents._DEQUEUE_KINDS
    assert set(mq._DELETION_ENDS) == documents._DELETION_OUTCOMES
    assert set(mq._DELETION_KINDS) == documents._DELETION_KINDS
    assert set(mq._WAIT_ENDS) == documents.WAIT.sets["ended"]
    assert {mq._READING_EVENT, mq._END_EVENT} == documents.WAIT.sets["event"]
