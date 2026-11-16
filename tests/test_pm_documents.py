"""Each document a project-management command prints for a program holds its contract
(ADR-097 point 7).

Each test runs the command's `main` in the test's own process (`tests/in_process.py`),
from a project its own tests stage, and holds what it prints to the contract pinned here
with `tests/document_contracts.py`. GitHub is never asked: where a command reads it, the
read is stood in for at the command's own seam, as its tests stand in for it, and what the
command prints from what it read is the run held. A key or a value that goes, or comes
back, fails until the same change updates the pin, beside the changeset that declares the
break. `tests/test_capability_documents.py` holds the ratchet over every capability's
commands.

The capability's validator, its fillers and its process predicates, those its process
definitions name and those it registers for one to name, print for the backbone's engines,
whose records set those documents (ADR-097 point 1), so they are not here.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from ruamel.yaml import YAML

from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.document_contracts import Contract, Form, check
from tests.in_process import REPO, load, run_main
from tests.pm_workstream_fakes import stage_project
from tests.test_pm_adopt_existing import (
    _PRIORITY_FIELD,
    _WORKSTREAM_FIELD,
    _board_config,
    _config,
    _serve_auj_reads,
    _serve_board_fields,
)
from tests.test_pm_back_fill import (
    AUJ_BOARD_CONFIG,
    AUJ_HOOKS,
    AUJ_MAP_WS_DEFAULT,
    _cap_root_with_hooks,
    _patch_gate_checks,
    _serve_reads,
)
from tests.test_pm_fixers import CONFIG, CONFIG_REL, PM, _run, _stage_docs

(
    list_workstreams,
    show_workstream,
    check_mesh,
    decline,
    show_issue,
    validate_issue,
    show_pr,
    validate_pr,
    show_tree,
    adopt,
    back_fill,
    pre_check,
    use_case_task,
    fixers,
    agent_verdicts,
    pr_validation,
    containment,
    body_parent_ref,
) = load(
    "project-management",
    "list-workstreams.py",
    "show-workstream.py",
    "check-mesh.py",
    "decline-use-case-task.py",
    "show-issue.py",
    "validate-issue.py",
    "show-pr.py",
    "validate-pr.py",
    "show-tree.py",
    "adopt-existing.py",
    "back-fill.py",
    "pre-check.py",
    "use_case_task",
    "fixers",
    "agent_verdicts",
    "pr_validation",
    "containment",
    "body_parent_ref",
)

#: The capability's own schemas, which a command reads from its installed tree.
SCHEMAS = REPO / ".pkit" / "capabilities" / PM / "schemas"

#: The invoker, in the shape `resolve_invoker_identity` returns, as the verbs' tests give it.
INVOKER = SimpleNamespace(github_login="octocat", email=None, unresolved_cause=None)


def _capability(tmp_path: Path, workstreams: str = "schema_version: 1\nworkstreams: {}\n") -> Path:
    """A bootstrapped project-management tree under a project at `tmp_path`, in open mode."""
    capability = tmp_path / ".pkit" / "capabilities" / PM
    stage_project(capability, workstreams)
    return capability


def _installed(tmp_path: Path) -> Path:
    """`_capability` with the capability's schemas, as a command that reads them needs."""
    capability = _capability(tmp_path)
    shutil.copytree(SCHEMAS, capability / "schemas")
    return capability


def _answering(answer: Callable[[list[str]], Any]) -> Callable[..., Any]:
    """A `gh_run` whose call `args` GitHub answers `answer(args)`, as JSON."""

    def gh_run(args: list[str], config: Any = None, **_kw: Any) -> Any:
        return subprocess.CompletedProcess(args, 0, stdout=json.dumps(answer(args)), stderr="")

    return gh_run


@pytest.fixture(autouse=True)
def invoker(monkeypatch: pytest.MonkeyPatch) -> None:
    """Who runs each command, as the verbs' tests stand them in: GitHub is not asked."""
    for script in (
        list_workstreams,
        show_workstream,
        check_mesh,
        show_issue,
        validate_issue,
        show_pr,
        validate_pr,
        show_tree,
    ):
        monkeypatch.setattr(script, "resolve_invoker_identity", lambda config=None: INVOKER)


def _printed(script: ModuleType, root: Path, *args: str) -> Any:
    """The one JSON document `script` prints with `args`, from `root`."""
    done = run_main(script, *args, cwd=root)
    assert done.stdout, done.stderr
    return json.loads(done.stdout)


# --- `pkit pm list-workstreams --json` and `pkit pm show-workstream --json` ----------------

_WORKSTREAMS = (
    "schema_version: 1\n"
    "workstreams:\n"
    "  cli:\n    name: CLI\n    description: The command line.\n    status: active\n"
    "  old:\n    name: Old\n    status: deprecated\n    deprecated_reason: Folded into cli.\n"
    "  twin:\n    name: CLI\n    status: active\n"
    "  Bad_Slug:\n    name: Bad\n"
)

_WORKSTREAM = {
    "slug": "str",
    "name": "str",
    "description": "str",
    "status": "str",
    "deprecated_reason": "str",
}
_STATUSES = frozenset({"active", "deprecated"})

LIST_WORKSTREAMS = Contract(
    name="pkit pm list-workstreams --json",
    forms={
        "answer": Form(
            keys={
                "form": "str",
                "errors": "list",
                "errors[]": "str",
                "duplicate_names": "list",
                "duplicate_names[]": "str",
                "entries": "list",
                "entries[]": "object",
                **{f"entries[].{key}": kind for key, kind in _WORKSTREAM.items()},
            }
        )
    },
    sets={"form": frozenset({"mapping", "list", "empty"}), "entries[].status": _STATUSES},
)

SHOW_WORKSTREAM = Contract(
    name="pkit pm show-workstream --json",
    forms={"answer": Form(keys=_WORKSTREAM)},
    sets={"status": _STATUSES},
)


def test_the_workstream_documents_hold_their_contracts(tmp_path: Path) -> None:
    mapping = _capability(tmp_path / "mapping", _WORKSTREAMS)
    listed = _capability(tmp_path / "list", "schema_version: 1\nworkstreams: [cli, docs]\n")
    empty = _capability(tmp_path / "empty", "")
    printed = [
        _printed(list_workstreams, capability.parents[2], "--json", "--status", "all")
        for capability in (mapping, listed, empty)
    ]
    check(LIST_WORKSTREAMS, {"answer": printed})
    shown = [
        _printed(show_workstream, mapping.parents[2], slug, "--json") for slug in ("cli", "old")
    ]
    check(SHOW_WORKSTREAM, {"answer": shown})


# --- `pkit pm decline-use-case-task --show --json` -----------------------------------------

DECLINE_USE_CASE_TASK = Contract(
    name="pkit pm decline-use-case-task --show --json",
    forms={
        "answer": Form(
            keys={
                "state": "str",
                "declined_at": "str|null",
                "offered_again_at": "str|null",
                "declined_at_local": "str|null",
                "offered_again_at_local": "str|null",
                "why": "str|null",
            }
        )
    },
    sets={"state": frozenset({"declined", "expired", "none", "unreadable"})},
)


def test_the_declined_use_case_task_document_holds_its_contract(tmp_path: Path) -> None:
    printed = []
    for state in ("declined", "expired", "none", "unreadable"):
        capability = _capability(tmp_path / state)
        if state == "declined":
            use_case_task.record(capability, datetime.now(UTC))
        elif state == "expired":
            use_case_task.record(capability, datetime.now(UTC) - timedelta(days=3))
        elif state == "unreadable":
            use_case_task.path_of(capability).parent.mkdir(parents=True, exist_ok=True)
            use_case_task.path_of(capability).write_text("not json\n", encoding="utf-8")
        printed.append(_printed(decline, capability.parents[2], "--show", "--json"))
    check(
        DECLINE_USE_CASE_TASK,
        {"answer": printed},
        enumerations={
            "state": (
                use_case_task.DECLINED,
                use_case_task.EXPIRED,
                use_case_task.NONE,
                use_case_task.UNREADABLE,
            )
        },
    )


# --- `pkit pm check-mesh --json` -----------------------------------------------------------

CHECK_MESH = Contract(
    name="pkit pm check-mesh --json",
    forms={
        "skipped": Form(keys={"status": "str", "reason": "str"}),
        "answer": Form(
            keys={
                "target": "str",
                "peers": "list",
                "peers[]": "str",
                "drift": "list",
                "drift[]": "object",
                "drift[].kind": "str",
                "drift[].peer": "str",
                "drift[].local": "str",
                "drift[].peer_value": "str",
                "drift[].in_local_only": "list",
                "drift[].in_local_only[]": "str",
                "drift[].in_peer_only": "list",
                "drift[].in_peer_only[]": "str",
                "drift[].severity": "str",
                "summary": "str",
            }
        ),
    },
    sets={
        "status": frozenset({"skipped"}),
        "drift[].kind": frozenset(
            {
                "capability-version",
                "type-labels",
                "priority-labels",
                "workstream-labels",
                "members",
                "milestones",
            }
        ),
        "drift[].severity": frozenset({"warning"}),
    },
)


def _mesh_state(full: str, **fields: Any) -> Any:
    owner, repo = full.split("/")
    return check_mesh.PeerState(
        peer=check_mesh.PeerSpec(owner, repo),
        labels=fields.get("labels", []),
        capability_version=fields.get("version"),
        members=fields.get("members", []),
        milestones=fields.get("milestones", []),
    )


def test_the_mesh_document_holds_its_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    alone = _capability(tmp_path / "alone")
    meshed = _capability(tmp_path / "meshed")
    config = meshed / "project" / "config.yaml"
    config.write_text(
        config.read_text(encoding="utf-8") + "mesh_peers:\n  - github://acme/peer\n",
        encoding="utf-8",
    )
    local = _mesh_state(
        "acme/repo",
        labels=["type:task", "priority:high", "workstream:cli"],
        version="1.0.0",
        members=[{"github_login": "octocat"}],
        milestones=["M1"],
    )
    peer = _mesh_state(
        "acme/peer",
        labels=["type:bug", "priority:low", "workstream:docs"],
        version="1.1.0",
        members=[{"github_login": "hubot"}],
        milestones=["M2"],
    )
    monkeypatch.setattr(check_mesh, "_gather_local_state", lambda root, config: local)
    monkeypatch.setattr(check_mesh, "_gather_peer_state", lambda spec, config: peer)
    printed = {
        "skipped": [_printed(check_mesh, alone.parents[2], "--json")],
        "answer": [_printed(check_mesh, meshed.parents[2], "--json")],
    }
    check(CHECK_MESH, printed)


# --- `pkit pm list-fixers --json` ----------------------------------------------------------

LIST_FIXERS = Contract(
    name="pkit pm list-fixers --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "point": "str",
                "resolved": "bool",
                "why": "str|null",
                "inert": "list",
                "inert[]": "str",
                "fixers": "list",
                "fixers[]": "object",
                "fixers[].agent": "str",
                "fixers[].types": "list",
                "fixers[].types[]": "object",
                "fixers[].types[].type": "str",
                "fixers[].types[].description": "str",
                "fixers[].types[].origin": "str",
                "fixers[].types[].answer": "str|null",
                "fixers[].types[].problems": "list",
                "fixers[].types[].problems[]": "object",
                "fixers[].types[].problems[].severity": "str",
                "fixers[].types[].problems[].text": "str",
                "stale": "list",
                "stale[]": "object",
                "stale[].agent": "str",
                "stale[].type": "str",
                "stale[].revoke": "str",
            }
        )
    },
    sets={
        "fixers[].types[].answer": frozenset({"granted", "refused"}),
        "fixers[].types[].problems[].severity": frozenset({"error", "warning", "report"}),
    },
)


_GRANTS = (
    "fixers:\n"
    "  page-fixer:\n    granted: [docs-test:page]\n    refused: [docs-test:guide]\n"
    "  gone-fixer:\n    granted: [docs-test:guide]\n"
)


def _fixers_project(make_adopter_repo: MakeAdopterRepo, root: Path) -> AdopterRepo:
    """An adopter at `root` whose capability declares three fixers of one agent: one
    granted, one refused and one of a type its registry lacks, and whose grant list grants
    an agent no entry names."""
    repo = make_adopter_repo(capabilities=(PM,), root=root)
    (repo.root / CONFIG_REL).parent.mkdir(parents=True, exist_ok=True)
    (repo.root / CONFIG_REL).write_text(CONFIG + _GRANTS, encoding="utf-8")
    _stage_docs(
        repo,
        [
            {"id": "docs-test:page", "agent": "page-fixer", "description": "your pages"},
            {"id": "docs-test:guide", "agent": "page-fixer", "description": "your guides"},
            {"id": "docs-test:nothing", "agent": "page-fixer", "description": "no such type"},
        ],
    )
    return repo


def test_the_fixers_document_holds_its_contract(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, tmp_path: Path
) -> None:
    resolved = _fixers_project(make_adopter_repo, tmp_path / "resolved")
    inert = _fixers_project(make_adopter_repo, tmp_path / "inert")
    # A contribution of a version the point does not take is inert, and the point fails.
    package = inert.pkit / "capabilities" / "docs-test" / "package.yaml"
    declared = YAML(typ="safe").load(package.read_text(encoding="utf-8"))
    declared["connections"]["extensions"]["contributes"][0]["schema_version"] = 2
    with package.open("w", encoding="utf-8") as handle:
        YAML().dump(declared, handle)
    printed = []
    for repo in (resolved, inert):
        done = _run(repo, "list-fixers", "--json")
        assert done.stdout, done.stderr
        printed.append(json.loads(done.stdout))
    assert [document["resolved"] for document in printed] == [True, False]
    check(
        LIST_FIXERS,
        {"answer": printed},
        enumerations={
            "fixers[].types[].answer": (fixers.GRANTED, fixers.REFUSED),
            "fixers[].types[].problems[].severity": (fixers.ERROR, fixers.WARNING, fixers.REPORT),
        },
    )


# --- `pkit pm show-issue --json` and `pkit pm validate-issue --json` ----------------------

#: A Task as GitHub gives it, with every section its type requires, its criteria, its
#: classification and a label of no axis.
_TASK = {
    "id": "I_1",
    "title": "[Task] Do it",
    "body": (
        "Feature: #3\n\n## What\n\nIt.\n\n## Acceptance criteria\n\n- [ ] one\n- [x] two\n\n"
        "## Doc impact\n\n- [ ] README\n"
    ),
    "labels": [
        {"name": "type:task"},
        {"name": "priority:high"},
        {"name": "workstream:cli"},
        {"name": "extra"},
    ],
    "assignees": [{"login": "octocat"}],
    "state": "OPEN",
    "milestone": {"title": "M1"},
    "url": "https://github.com/acme/repo/issues/1",
}
#: An issue of no type, with no parent line, no section and nothing GitHub left out.
_UNTYPED = {"id": "I_2", "title": "Something", "body": "", "labels": [], "state": "CLOSED"}

SHOW_ISSUE = Contract(
    name="pkit pm show-issue --json",
    forms={
        "answer": Form(
            keys={
                "title": "str",
                "structural_type": "str|null",
                "state": "str",
                "assignees": "list",
                "assignees[]": "str",
                "milestone": "str|null",
                "parent_ref": "str",
                "classification": "object",
                "classification.type": "list",
                "classification.type[]": "str",
                "classification.priority": "list",
                "classification.priority[]": "str",
                "classification.workstream": "list",
                "classification.workstream[]": "str",
                "other_labels": "list",
                "other_labels[]": "str",
                "required_sections": "list",
                "required_sections[]": "object",
                "required_sections[].heading": "str",
                "required_sections[].present": "bool",
                "criteria": "list",
                "criteria[]": "str",
                "doc_impact": "list",
                "doc_impact[]": "str",
                "body": "str",
                "url": "str|null",
            }
        )
    },
)

_FINDINGS = {
    "findings": "list",
    "findings[]": "object",
    "findings[].severity": "str",
    "findings[].label": "str",
    "findings[].detail": "str",
}
_SEVERITIES = frozenset({"hard-reject", "bypassable-with-audit", "warning"})

VALIDATE_ISSUE = Contract(
    name="pkit pm validate-issue --json",
    forms={"answer": Form(keys={"issue_number": "int", "issue_title": "str", **_FINDINGS})},
    sets={"findings[].severity": _SEVERITIES},
)


def _issue_documents(
    script: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> list[Any]:
    """What `script` prints for `_TASK` and for `_UNTYPED`, GitHub answering each."""
    _installed(tmp_path)
    issues = {"1": _TASK, "2": _UNTYPED}
    monkeypatch.setattr(script, "gh_get_issue", lambda number, config, fields: issues[str(number)])
    return [_printed(script, tmp_path, number, "--json") for number in issues]


def test_the_issue_documents_hold_their_contracts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    check(SHOW_ISSUE, {"answer": _issue_documents(show_issue, tmp_path / "show", monkeypatch)})
    validated = _issue_documents(validate_issue, tmp_path / "validate", monkeypatch)
    check(
        VALIDATE_ISSUE,
        {"answer": validated},
        enumerations={
            "findings[].severity": (
                validate_issue.SEVERITY_HARD_REJECT,
                validate_issue.SEVERITY_BYPASSABLE,
                validate_issue.SEVERITY_WARNING,
            )
        },
    )


# --- `pkit pm show-pr --json` and `pkit pm validate-pr --json` -----------------------------


def _verdict(reviewer: str, line: str, at: str) -> dict[str, Any]:
    return {
        "author": {"login": reviewer},
        "body": f"{line}\n\nThe reasons.",
        "createdAt": at,
        "url": f"https://github.com/acme/repo/pull/9#{reviewer}-{at}",
    }


#: A pull request as GitHub gives it: a Conventional Commits title, an issue it closes,
#: a requested reviewer, and verdicts from both paths, one reviewer's in two rounds.
_PR = {
    "number": 9,
    "title": "feat(cli): add the flag",
    "body": "Closes #1\n\n## Doc impact\n\nNone.\n",
    "state": "OPEN",
    "url": "https://github.com/acme/repo/pull/9",
    "isDraft": False,
    "mergeable": "MERGEABLE",
    "headRefName": "feat/1-flag",
    "headRefOid": "a" * 40,
    "baseRefName": "main",
    "mergedAt": None,
    "reviewRequests": [{"login": "alice"}],
    "comments": [
        _verdict(
            "critic", "Reviewer agent (local, critic): CHANGES_REQUESTED", "2026-06-01T00:00:00Z"
        ),
        _verdict("critic", "Reviewer agent (local, critic): APPROVED", "2026-06-02T00:00:00Z"),
        _verdict("review-bot", "Reviewer agent: APPROVED", "2026-06-02T00:00:00Z"),
    ],
}
#: A merged pull request with a title of no convention, closing nothing.
_MERGED = {
    "number": 8,
    "title": "Tidy things",
    "body": "",
    "state": "MERGED",
    "isDraft": True,
    "headRefName": "tidy",
    "baseRefName": "main",
    "mergedAt": "2026-06-03T00:00:00Z",
}

_VERDICTS = frozenset({"APPROVED", "CHANGES_REQUESTED"})
_PATHS = frozenset({"local", "remote"})

SHOW_PR = Contract(
    name="pkit pm show-pr --json",
    forms={
        "answer": Form(
            keys={
                "title": "str",
                "state": "str",
                "is_draft": "bool",
                "mergeable": "str",
                "head": "str",
                "base": "str",
                "merged_at": "str|null",
                "url": "str|null",
                "conventional_commits": "object",
                "conventional_commits.matched": "bool",
                "conventional_commits.type": "str",
                "conventional_commits.scope": "str|null",
                "conventional_commits.summary": "str",
                "closes": "list",
                "closes[]": "int",
                "reviewers": "list",
                "reviewers[]": "str",
                "has_doc_impact_section": "bool",
                "review": "list",
                "review[]": "object",
                "review[].reviewer": "str",
                "review[].verdict": "str",
                "review[].path": "str",
                "review[].body": "str",
                "review[].stale": "bool",
                "review[].freshness": "str",
                "body": "str",
                "review_history": "list",
                "review_history[]": "object",
                "review_history[].reviewer": "str",
                "review_history[].path": "str",
                "review_history[].verdicts": "list",
                "review_history[].verdicts[]": "object",
                "review_history[].verdicts[].verdict": "str",
                "review_history[].verdicts[].timestamp": "str",
                "review_history[].verdicts[].url": "str",
                "review_history[].verdicts[].current": "bool",
                "review_history[].verdicts[].stale": "bool",
                "review_history[].verdicts[].freshness": "str",
                "review_history[].verdicts[].body": "str",
            }
        )
    },
    sets={
        "review[].verdict": _VERDICTS,
        "review[].path": _PATHS,
        "review_history[].path": _PATHS,
        "review_history[].verdicts[].verdict": _VERDICTS,
    },
)

VALIDATE_PR = Contract(
    name="pkit pm validate-pr --json",
    forms={"answer": Form(keys={"pr_number": "int", "pr_title": "str", **_FINDINGS})},
    sets={"findings[].severity": _SEVERITIES},
)


def test_the_pull_request_documents_hold_their_contracts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _installed(tmp_path)
    pulls = {"9": _PR, "8": _MERGED}
    answer = _answering(lambda args: pulls[args[3]])
    monkeypatch.setattr(show_pr, "gh_run", answer)
    # The review the verdicts are judged by, as show-pr's own tests resolve it.
    monkeypatch.setattr(
        show_pr,
        "_resolve_review",
        lambda number, config, root: show_pr.PrReview(
            show_pr.Resolution(),
            author_delta=show_pr.author_delta,
            base_kept=show_pr.base_kept,
            ruled_altered=show_pr.ruled_altered,
        ),
    )
    verdicts = agent_verdicts.APPROVED, agent_verdicts.CHANGES_REQUESTED
    paths = agent_verdicts.PATH_LOCAL, agent_verdicts.PATH_REMOTE
    check(
        SHOW_PR,
        {"answer": [_printed(show_pr, tmp_path, n, "--json") for n in pulls]},
        enumerations={
            "review[].verdict": verdicts,
            "review[].path": paths,
            "review_history[].path": paths,
            "review_history[].verdicts[].verdict": verdicts,
        },
    )
    monkeypatch.setattr(validate_pr, "gh_run", answer)
    monkeypatch.setattr(validate_pr, "gh_get_issue", lambda number, config, fields: _TASK)
    check(
        VALIDATE_PR,
        {"answer": [_printed(validate_pr, tmp_path, n, "--json") for n in pulls]},
        enumerations={
            "findings[].severity": (
                pr_validation.SEVERITY_HARD_REJECT,
                pr_validation.SEVERITY_BYPASSABLE,
                pr_validation.SEVERITY_WARNING,
            )
        },
    )


# --- `pkit pm show-tree --format json` -----------------------------------------------------


def _row(number: int, title: str, body: str, state: str = "OPEN") -> dict[str, Any]:
    return {
        "number": number,
        "title": title,
        "body": body,
        "state": state,
        "labels": [],
        "milestone": {"title": "M1"} if number == 1 else None,
    }


#: A tracker whose issues stand in each relation to their parents the seam compares: an
#: Epic, a Feature its first line and its native link agree on, a Task only its first
#: line places, one only a native link places, one the two disagree on, one under a Task,
#: a closed issue of no type, and a Feature with no parent. One pull request closes an
#: issue, and one closes none.
_ROWS = [
    _row(1, "[EPIC] Platform", "## What"),
    _row(2, "[Feature] Login", "EPIC: #1\n\n## What"),
    _row(3, "[Task] The form", "Feature: #2\n\n## What"),
    _row(4, "[Task] Loose", "## What"),
    _row(5, "[Task] Torn", "Feature: #3\n\n## What"),
    _row(6, "[Task] Beneath", "Task: #3\n\n## What"),
    _row(7, "Something", "", state="CLOSED"),
    _row(8, "[Feature] Alone", "## What"),
]
_PRS = [
    {"number": 10, "title": "feat: the form", "body": "Closes #3", "state": "OPEN"},
    {"number": 11, "title": "fix: stray", "body": "", "state": "OPEN"},
]
#: Each parent's native sub-issues: here, and in another repository.
_NATIVE = {1: {2, 4}, 2: {5}}
_FOREIGN = {1: frozenset({containment.ForeignIssue("acme/other", 7)})}


def _tracker(args: list[str]) -> Any:
    """GitHub's answer to show-tree's lists, each bounded by its `--limit`."""
    limit = int(args[args.index("--limit") + 1])
    return (_PRS if "pr" in args else _ROWS)[:limit]


def _native(_config: Any, *, parent_number: int) -> Any:
    return containment.NativeRead(
        numbers=set(_NATIVE.get(parent_number, set())),
        outcome=containment.NativeReadOutcome.READ,
        foreign=_FOREIGN.get(parent_number, frozenset()),
    )


SHOW_TREE = Contract(
    name="pkit pm show-tree --format json",
    forms={
        "answer": Form(
            keys={
                "issues": "object",
                "issues{}": "object",
                "issues{}.number": "int",
                "issues{}.title": "str",
                "issues{}.state": "str",
                "issues{}.structural_type": "str|null",
                "issues{}.milestone": "str|null",
                "issues{}.parent_number": "int|null",
                "issues{}.children": "list",
                "issues{}.children[]": "int",
                "issues{}.child_substrate": "object",
                "issues{}.child_substrate{}": "str",
                "issues{}.children_in_other_repositories": "list",
                "issues{}.children_in_other_repositories[]": "object",
                "issues{}.children_in_other_repositories[].ref": "str",
                "issues{}.children_in_other_repositories[].repository": "str",
                "issues{}.children_in_other_repositories[].number": "int",
                "issues{}.parent_resolution": "object|null",
                "issues{}.parent_resolution.kind": "str",
                "issues{}.parent_resolution.native_parent": "int|null",
                "issues{}.parent_resolution.native_parent_known": "bool",
                "issues{}.parent_resolution.first_line_parent": "int|null",
                "issues{}.parent_resolution.first_line_form": "str",
                "issues{}.parent_resolution.first_line_names_itself": "bool",
                "prs": "list",
                "prs[]": "object",
                "prs[].number": "int",
                "prs[].title": "str",
                "prs[].state": "str",
                "prs[].closes": "list",
                "prs[].closes[]": "int",
                "orphans": "object",
                "orphans.open_issues_with_no_parent_ref": "list",
                "orphans.open_issues_with_no_parent_ref[]": "int",
                "orphans.tasks_not_under_container": "list",
                "orphans.tasks_not_under_container[]": "int",
                "orphans.prs_without_closing_issue_in_repo": "list",
                "orphans.prs_without_closing_issue_in_repo[]": "int",
                "tree_roots": "list",
                "tree_roots[]": "int",
                "complete": "bool",
                "incomplete_reason": "str|null",
            }
        )
    },
    data=frozenset({"issues", "issues{}.child_substrate"}),
    sets={
        "issues{}.child_substrate{}": frozenset({"native", "textual"}),
        "issues{}.parent_resolution.kind": frozenset(
            {"agreed", "native-only", "textual-only", "disagree", "none"}
        ),
        "issues{}.parent_resolution.first_line_form": frozenset(
            {"conforming", "non-conforming", "milestone", "none"}
        ),
    },
)


def test_the_tree_document_holds_its_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _installed(tmp_path)
    monkeypatch.setattr(show_tree, "gh_run", _answering(_tracker))
    monkeypatch.setattr(containment, "_gh_call", _answering(_tracker))
    monkeypatch.setattr(containment, "read_native_children", _native)
    printed = [
        _printed(show_tree, tmp_path, "--format", "json", "--state", "all", "--limit", limit)
        for limit in ("500", "3")
    ]
    assert [document["complete"] for document in printed] == [True, False]
    check(
        SHOW_TREE,
        {"answer": printed},
        enumerations={
            "issues{}.child_substrate{}": [s.value for s in containment.ChildSubstrate],
            # Each kind but `unread`, which only a read of the issue's own record gives
            # (`resolve_parent`): the tree compares the parents it read (`compare_parents`).
            "issues{}.parent_resolution.kind": [
                k.value for k in containment.ParentKind if k is not containment.ParentKind.UNREAD
            ],
            "issues{}.parent_resolution.first_line_form": [
                f.value for f in body_parent_ref.LineForm
            ],
        },
    )


# --- `pkit pm adopt-existing --json` -------------------------------------------------------

ADOPT_EXISTING = Contract(
    name="pkit pm adopt-existing --json",
    forms={
        "answer": Form(
            keys={
                "posture": "str",
                "inventory": "object",
                "inventory.labels": "list",
                "inventory.labels[]": "object",
                "inventory.labels[].name": "str",
                "inventory.labels[].issue_usage": "int",
                "inventory.title_prefixes": "list",
                "inventory.title_prefixes[]": "object",
                "inventory.title_prefixes[].prefix": "str",
                "inventory.title_prefixes[].count": "int",
                "inventory.open_count": "int",
                "inventory.closed_count": "int",
                "inventory.sampled_issue_count": "int",
                "inventory.sample_truncated": "bool",
                "inventory.labels_truncated": "bool",
                "inventory.has_blocked_label": "bool",
                "inventory.milestones_in_use": "list",
                "inventory.milestones_in_use[]": "str",
                "inventory.has_board": "bool",
                "inventory.board_fields": "list",
                "inventory.board_fields[]": "str",
                "inventory.projects_v2_node_id": "str|null",
                "inferences": "list",
                "inferences[]": "object",
                "inferences[].axis": "str",
                "inferences[].binding": "object|null",
                "inferences[].evidence": "str",
                "inferences[].confidence": "str",
                "hierarchy": "object",
                "hierarchy.mode": "str",
                "hierarchy.evidence": "str",
                "draft_substrate_map": "object",
                "schema_check": "object",
                "schema_check.ran": "bool",
                "schema_check.valid": "bool",
                "schema_check.errors": "list",
                "schema_check.errors[]": "str",
            }
        )
    },
    # The drafted map and each axis's binding in it are the substrate map's, whose
    # schema sets their shape (DEC-036).
    payloads=frozenset({"inferences[].binding", "draft_substrate_map"}),
    sets={
        "inferences[].axis": frozenset({"type", "priority", "workstream", "state"}),
        "inferences[].confidence": frozenset({"high", "low", "none"}),
        "hierarchy.mode": frozenset({"advisory"}),
    },
)


def test_the_adoption_document_holds_its_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A tracker of labels, one with a board and its fields, and one whose installed tree
    lacks the map's schema, so the draft's own check cannot run."""
    labelled = _installed(tmp_path / "labelled")
    boarded = _installed(tmp_path / "boarded")
    unchecked = _capability(tmp_path / "unchecked")
    runs = (
        (labelled, _serve_auj_reads, _config()),
        (boarded, _serve_board_fields([_WORKSTREAM_FIELD, _PRIORITY_FIELD]), _board_config()),
        (unchecked, _serve_auj_reads, _config()),
    )
    printed = []
    for capability, serve, config in runs:
        monkeypatch.setattr(adopt, "gh_run", serve)
        monkeypatch.setattr(adopt, "load_adopter_config", lambda root, config=config: config)
        printed.append(
            _printed(adopt, capability.parents[2], "--json", "--capability-root", str(capability))
        )
    check(ADOPT_EXISTING, {"answer": printed})


# --- `pkit pm back-fill --json` ------------------------------------------------------------

#: The board's hooks, with a field written as text, and an entry that names no milestone,
#: which becomes no intent and says why.
_BOARD_HOOKS = (
    AUJ_HOOKS
    + "    - kind: set-board-field\n"
    + "      field_id: FIELD_NOTE\n"
    + "      text_value: Imported\n"
    + "    - kind: assign-milestone\n"
)
#: A map that binds priority to the project's own labels, with a default its remap
#: covers, and workstream to them too, with a default it does not.
_LABEL_MAP = (
    "schema_version: 1\naxes:\n"
    "  priority:\n    label:\n      remap: {High: P0, Medium: P1, Low: P2}\n    default: Medium\n"
    "  workstream:\n    label:\n      remap: {core: Core}\n    default: elsewhere\n"
)
_INTENT = {
    "kind": "str",
    "citation": "str",
    "field_id": "str|null",
    "single_select_option_id": "str|null",
    "text_value": "str|null",
    "milestone_title": "str|null",
    "axis": "str|null",
    "axis_value": "str|null",
    "label_value": "str|null",
    "carrier_labels": "list",
    "carrier_labels[]": "str",
}
_PROPOSED = {
    "issue_number": "int",
    "issue_title": "str",
    "kind": "str",
    "citation": "str",
    "argv": "list|null",
    "argv[]": "str",
    "observed": "str|null",
    "prediction": "str",
    "blocked_reason": "str",
    "axis": "str|null",
}
_KINDS = frozenset({"set-board-field", "assign-milestone", "set-axis-label"})

BACK_FILL = Contract(
    name="pkit pm back-fill --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "truncated": "bool",
                "residual_pre_check": "object",
                "residual_pre_check.passed": "bool",
                "residual_pre_check.checks": "list",
                "residual_pre_check.checks[]": "object",
                "residual_pre_check.checks[].label": "str",
                "residual_pre_check.checks[].status": "str",
                "residual_pre_check.checks[].detail": "str",
                "intent_errors": "list",
                "intent_errors[]": "str",
                "intents": "list",
                "intents[]": "object",
                **{f"intents[].{key}": kind for key, kind in _INTENT.items()},
                "proposed": "list",
                "proposed[]": "object",
                **{f"proposed[].{key}": kind for key, kind in _PROPOSED.items()},
            }
        )
    },
    sets={
        "intents[].kind": _KINDS,
        "proposed[].kind": _KINDS,
        "proposed[].prediction": frozenset({"already-satisfied", "would-write", "blocked"}),
    },
)


def _tracker_reads(args: list[str], config: Any = None, **_kw: Any) -> Any:
    """back-fill's reads, as its own tests serve them: the repository, the board and its
    one card, and two issues, one already in the milestone."""
    served = _serve_reads(args)
    return served or subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")


def test_the_back_fill_plan_holds_its_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A plan over a board, one over the project's labels, and the empty plan of a project
    that declares nothing. The labels' plan reads as many issues as its `--limit` allows,
    so it may not be whole."""
    monkeypatch.setattr(back_fill, "gh_run", _tracker_reads)
    _patch_gate_checks(back_fill, monkeypatch, auth_ok=True, repo_ok=True, map_ok=True)
    runs = (
        ("board", _BOARD_HOOKS, AUJ_MAP_WS_DEFAULT, AUJ_BOARD_CONFIG, ()),
        ("labels", "schema_version: 1\nhooks: {}\n", _LABEL_MAP, {}, ("--limit", "2")),
        ("nothing", "schema_version: 1\nhooks: {}\n", None, {}, ()),
    )
    printed = []
    for name, hooks, substrate_map, config, extra in runs:
        capability = _cap_root_with_hooks(tmp_path / name, hooks, map_yaml=substrate_map)
        monkeypatch.setattr(
            back_fill, "load_adopter_config", lambda root, config=config: dict(config)
        )
        printed.append(
            _printed(
                back_fill, tmp_path / name, "--capability-root", str(capability), "--json", *extra
            )
        )
    assert [document["truncated"] for document in printed] == [False, True, False]
    kinds = (*back_fill.BACK_FILL_KINDS, back_fill.SET_AXIS_LABEL_KIND)
    check(
        BACK_FILL,
        {"answer": printed},
        enumerations={
            "intents[].kind": kinds,
            "proposed[].kind": kinds,
        },
    )


# --- `pkit pm pre-check --json` ------------------------------------------------------------

#: The document is a list of the checks' outcomes, named from its root (`[]`).
PRE_CHECK = Contract(
    name="pkit pm pre-check --json",
    forms={
        "answer": Form(
            keys={
                "[]": "object",
                "[].label": "str",
                "[].status": "str",
                "[].detail": "str",
                "[].remediation": "str|null",
            }
        )
    },
    sets={"[].status": frozenset({"ok", "fail", "skip", "warn"})},
)


def _unreachable(args: list[str], *_a: Any, **_kw: Any) -> Any:
    """Each program pre-check starts, as one that cannot reach GitHub answers it: its
    version where asked, and a failure for every read."""
    if list(args)[-1:] == ["--version"]:
        return subprocess.CompletedProcess(args, 0, stdout=f"{args[0]} version 1\n", stderr="")
    return subprocess.CompletedProcess(args, 1, stdout="", stderr="unreachable")


def test_the_pre_check_document_holds_its_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A project whose `gh` cannot reach GitHub, one whose stamp an older version wrote,
    and one with no `gh` on its PATH, whose remaining checks are skipped."""
    reached = _installed(tmp_path / "reached")
    stale = _installed(tmp_path / "stale")
    shutil.copy(SCHEMAS.parent / "package.yaml", stale / "package.yaml")
    alone = _installed(tmp_path / "alone")
    monkeypatch.setattr(pre_check.subprocess, "run", _unreachable)
    printed = []
    for capability, on_path in ((reached, {"git", "gh"}), (stale, {"git", "gh"}), (alone, {"git"})):
        monkeypatch.setattr(
            pre_check.shutil,
            "which",
            lambda cmd, on_path=on_path: f"/usr/bin/{cmd}" if cmd in on_path else None,
        )
        printed.append(
            _printed(
                pre_check, capability.parents[2], "--json", "--capability-root", str(capability)
            )
        )
    check(PRE_CHECK, {"answer": printed})


#: The contracts of each project-management command that prints a document for a program,
#: by the command's words.
CONTRACTS: Mapping[str, tuple[Contract, ...]] = {
    "project-management list-workstreams": (LIST_WORKSTREAMS,),
    "project-management show-workstream": (SHOW_WORKSTREAM,),
    "project-management decline-use-case-task": (DECLINE_USE_CASE_TASK,),
    "project-management check-mesh": (CHECK_MESH,),
    "project-management list-fixers": (LIST_FIXERS,),
    "project-management show-issue": (SHOW_ISSUE,),
    "project-management validate-issue": (VALIDATE_ISSUE,),
    "project-management show-pr": (SHOW_PR,),
    "project-management validate-pr": (VALIDATE_PR,),
    "project-management show-tree": (SHOW_TREE,),
    "project-management adopt-existing": (ADOPT_EXISTING,),
    "project-management back-fill": (BACK_FILL,),
    "project-management pre-check": (PRE_CHECK,),
}
