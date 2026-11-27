"""Each document a backbone command prints for a program holds its contract (ADR-097
point 7).

Each test prints its document through the command, in the test's own process, and
builds the forms and keys a short state does not reach through the function the command
prints, from a result holding each of them. `tests/document_contracts.py` holds them to
the contract pinned here: a key or a value that goes, or comes back, fails until the
same change updates the pin, beside the changeset that declares the break.

Every backbone command that prints a document for a program has its contracts here, or in
a module this one gathers: `tests/test_backbone_documents_account.py`,
`tests/test_backbone_documents_pull_request.py`,
`tests/test_backbone_documents_process.py`, `tests/test_backbone_documents_components.py`
and `tests/test_backbone_documents_session.py`.
`tests/backbone_documents_baseline.txt` names the commands no contract pins yet, and is
empty; nothing is ever added to it. Each way a command prints for a program other than
`--json` is named here, with why no contract pins it (`OTHER_OUTPUT`).
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

import click
import pytest

from project_kit import answer_files as af
from project_kit import data_points as dp
from project_kit import decisions_check_diff as numbering
from project_kit import decisions_landing as landing
from project_kit import default_branch as db
from project_kit import docs_roots, path_records
from project_kit import friction_check as fc
from project_kit import friction_discovery as fd
from project_kit import friction_move as fmove
from project_kit import friction_prune as fprune
from project_kit import friction_report as frep
from project_kit import friction_repository as fr
from project_kit import friction_since as fs
from project_kit import loaded_rule_sets as lr
from project_kit import refs as refs_mod
from project_kit import rule_set_reading as reading
from project_kit.cli import main
from project_kit.config_at_commit import KeyAtCommit
from project_kit.validators import Finding, Severity
from tests import test_answer_files as answer_tests
from tests import test_backbone_documents_account as account_documents
from tests import test_backbone_documents_components as component_documents
from tests import test_backbone_documents_process as process_documents
from tests import test_backbone_documents_pull_request as pull_request_documents
from tests import test_backbone_documents_session as session_documents
from tests import test_friction_artefacts as artefacts_tests
from tests import test_friction_revisit as revisit_tests
from tests import test_rule_reach as reach
from tests.adopter_repo import AdopterRepo, GitRepo
from tests.backbone_documents import JSON_OPTION, document_of, invoke
from tests.document_contracts import ANY, Contract, Form, check
from tests.friction_documents import CONFIG as FRICTION_CONFIG
from tests.friction_documents import SOURCE, Timeline, commit_install, friction_config, guide
from tests.test_rule_sets import anchored_to, rule_set_text, rules

BASELINE = Path(__file__).with_name("backbone_documents_baseline.txt")


@pytest.fixture(autouse=True)
def no_check_base_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """A developer's own `$PKIT_CHECK_BASE` must not decide what a document holds."""
    monkeypatch.delenv(db.CHECK_BASE_ENV, raising=False)


# --- `pkit repository base --json` -------------------------------------------------------

_BASE_SOURCES = frozenset({"option", "environment", "default-branch"})
_RESOLVED = frozenset({"remote", "local"})

REPOSITORY_BASE = Contract(
    name="pkit repository base --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "default_branch": "object",
                "default_branch.name": "str",
                "default_branch.source": "str",
                "default_branch.ref": "str|null",
                "default_branch.commit": "str|null",
                "default_branch.resolved": "str|null",
                "default_branch.problem": "str|null",
                "default_branch.unborn": "bool",
                "base": "object",
                "base.ref": "str",
                "base.source": "str",
                "base.tip": "str|null",
                "base.fork": "str|null",
                "base.outdated": "bool|null",
                "base.resolved": "str|null",
                "base.problem": "str|null",
                "head": "object",
                "head.commit": "str|null",
                "head.unborn": "bool",
                "head.problem": "str|null",
            }
        )
    },
    sets={
        "default_branch.source": frozenset({"configuration", "default"}),
        "default_branch.resolved": _RESOLVED,
        "base.source": _BASE_SOURCES,
        "base.resolved": _RESOLVED,
    },
)


def _settled(source: str, resolved: str | None, *, found: bool = True) -> dict[str, Any]:
    commit = "c" * 40 if found else None
    problem = None if found else "it names no commit here"
    return db.Settled(
        db.DefaultBranch(
            "main",
            db.DECLARED if found else db.DEFAULTED,
            "origin/main" if found else None,
            commit,
            resolved,
            problem,
            unborn=not found,
        ),
        db.Base("main", source, commit, commit, False if found else None, resolved, problem),
        db.Head(commit, unborn=not found, problem=problem),
    ).as_json()


def test_the_repository_base_document_holds_its_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = GitRepo.init(tmp_path / "work")
    repo.commit("first", {"README.md": "one\n"})
    monkeypatch.chdir(repo.root)
    printed = document_of(invoke("repository", "base", JSON_OPTION))
    built = [
        _settled(db.OPTION, db.RESOLVED_REMOTE),
        _settled(db.ENVIRONMENT, db.RESOLVED_LOCAL),
        _settled(db.DEFAULT_BRANCH, None, found=False),
    ]
    check(REPOSITORY_BASE, {"answer": [printed, *built]})


# --- `pkit decisions check-landing --json` ------------------------------------------------

_LANDING_KINDS = frozenset({"record", "rule", "rule-set-file"})
_POINT_CHANGES = frozenset({"added", "altered", "retired", "removed"})


def _proposal_keys(prefix: str) -> dict[str, str]:
    return {
        f"{prefix}": "list",
        f"{prefix}[]": "object",
        f"{prefix}[].kind": "str",
        f"{prefix}[].name": "str",
        f"{prefix}[].path": "str",
        f"{prefix}[].was": "str|null",
        f"{prefix}[].why": "str|null",
    }


def _work_keys(prefix: str) -> dict[str, str]:
    return {
        f"{prefix}.commit": "str",
        f"{prefix}.subject": "str",
        f"{prefix}.paths": "list",
        f"{prefix}.paths[]": "str",
        f"{prefix}.nothing_lands": "bool",
    }


def _edits_keys(prefix: str, *, null: bool) -> dict[str, str]:
    """A rule's edits, or a record's as the numbering check gives them."""
    return {
        prefix: "object|null" if null else "object",
        f"{prefix}.fields": "list",
        f"{prefix}.fields[]": "str",
        f"{prefix}.text": "bool",
        f"{prefix}.removed": "bool",
        f"{prefix}.path": "str",
        f"{prefix}.record": "str",
        f"{prefix}.points": "list",
        f"{prefix}.points[]": "object",
        f"{prefix}.points[].id": "str",
        f"{prefix}.points[].change": "str",
        f"{prefix}.points[].title": "str",
        f"{prefix}.shared_text": "bool",
        f"{prefix}.other_text": "bool",
        f"{prefix}.list_form": "bool",
    }


CHECK_LANDING = Contract(
    name="pkit decisions check-landing --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "problem": "null",
                "base": "object",
                "base.named": "str",
                "base.source": "str",
                "base.ref": "str",
                "base.tip": "str|null",
                "base.fork": "str|null",
                "head": "str",
                "landing_tree": "str",
                "default_branch": "object",
                "default_branch.declared": "str",
                "default_branch.is_base": "bool",
                "default_branch.warning": "str|null",
                "key": "object",
                "key.name": "str",
                "key.value": "bool",
                "key.read_at": "str",
                "key.warning": "str|null",
                "key.refusal_on": "bool",
                "key.change": "object|null",
                "key.change.tip": "bool",
                "key.change.landing": "bool",
                **_proposal_keys("proposals"),
                "refuses": "bool",
                "accepted": "list",
                "accepted[]": "object",
                "accepted[].kind": "str",
                "accepted[].name": "str",
                "accepted[].path": "str",
                "accepted[].was": "str|null",
                "accepted[].commits": "list",
                "accepted[].commits[]": "object",
                **_work_keys("accepted[].commits[]"),
                "accepted[].commits[].before": "list",
                "accepted[].commits[].before[]": "object",
                **_work_keys("accepted[].commits[].before[]"),
                **_edits_keys("accepted[].commits[].edits_since", null=True),
                "accepted_on_base": "list",
                "accepted_on_base[]": "object",
                "accepted_on_base[].kind": "str",
                "accepted_on_base[].name": "str",
                "accepted_on_base[].path": "str",
                **_edits_keys("accepted_on_base[].edits", null=False),
                "received_disagreements": "list",
                "received_disagreements[]": "str",
                "cannot_tell": "list",
                "cannot_tell[]": "str",
                **_proposal_keys("default_branch_proposals"),
            }
        ),
        "no answer": Form(keys={"schema_version": "int", "problem": "str"}),
    },
    sets={
        "base.source": _BASE_SOURCES,
        "proposals[].kind": _LANDING_KINDS,
        "accepted[].kind": _LANDING_KINDS,
        "accepted_on_base[].kind": _LANDING_KINDS,
        "default_branch_proposals[].kind": _LANDING_KINDS,
        "accepted[].commits[].edits_since.points[].change": _POINT_CHANGES,
        "accepted_on_base[].edits.points[].change": _POINT_CHANGES,
    },
)

_RECORD = ".pkit/decisions/project/PRJ-001-a.md"


def _record(status: str) -> str:
    return (
        f"---\nid: PRJ-001\ntitle: A record\nstatus: {status}\ndate: 2026-10-13\n"
        f"author: t\n---\n\n## Context\n\nWhy.\n\n## Decision\n\nWhat.\n\n"
        f"### 1. Point 1\n\nText of 1.\n\n## Rationale\n\nBecause.\n"
    )


def _key(value: bool, *, warning: str | None = None) -> KeyAtCommit:
    return KeyAtCommit("decisions.refuse-proposals", "c" * 40, value, warning=warning)


def _landing(source: str) -> dict[str, Any]:
    """A landing that holds every key: each kind of record and rule proposed, accepted,
    accepted on the base and standing, a record's edits and a rule's, and the key
    changing at the landing."""
    record_edits = numbering.ChangedRecord(
        _RECORD,
        "PRJ-001",
        points=tuple(
            numbering.PointChange(f"{i}", change, "A title")
            for i, change in enumerate(sorted(_POINT_CHANGES), start=1)
        ),
        fields=("status",),
        shared=True,
    )
    rule_edits = landing.RuleEdits(fields=("status",), text=True)
    work = landing.Work("w" * 40, "a commit", ("docs/a.md",))
    before = landing.Work("b" * 40, "before", ("docs/b.md",))
    kinds = sorted(_LANDING_KINDS)
    found = landing.Landing(
        named="main",
        base=db.Base("origin/main", source, "t" * 40, "f" * 40, False, db.RESOLVED_REMOTE, None),
        head="h" * 40,
        landing_tree="l" * 40,
        declared_branch=KeyAtCommit("repository.default-branch", "t" * 40, "main", warning="why"),
        is_default=True,
        key=_key(True, warning="read as the default"),
        key_at_landing=_key(False),
        proposals=tuple(
            landing.Proposal(kind, "PRJ-002", _RECORD, was, why)
            for kind, was, why in zip(
                kinds, (None, "accepted", "proposed"), (None, None, "a link"), strict=True
            )
        ),
        accepted=tuple(
            landing.Accepted(
                kind,
                "PRJ-001",
                _RECORD,
                "proposed",
                (
                    landing.Acceptance(work, (before,), edits),
                    landing.Acceptance(work),
                ),
            )
            for kind, edits in zip(kinds, (record_edits, rule_edits, None), strict=True)
        ),
        accepted_on_base=tuple(
            landing.AcceptedOnBase(kind, "PRJ-001", _RECORD, edits)
            for kind, edits in zip(kinds, (record_edits, rule_edits, rule_edits), strict=True)
        ),
        disagreements=("docs/a.md",),
        cannot_tell=("the state could not tell",),
        standing=tuple(landing.Proposal(kind, "PRJ-003", _RECORD) for kind in kinds),
    )
    return landing.document(found)


def test_the_landing_check_document_holds_its_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = GitRepo.init(tmp_path / "work")
    monkeypatch.chdir(repo.root)
    repo.commit("start", {_RECORD: _record("proposed")})
    repo.checkout("change", create=True)
    repo.commit("accept it", {_RECORD: _record("accepted")})
    printed = document_of(invoke("decisions", "check-landing", "--base", "main", JSON_OPTION))
    no_answer = document_of(invoke("decisions", "check-landing", "--base", "nowhere", JSON_OPTION))
    check(
        CHECK_LANDING,
        {
            "answer": [printed, *(_landing(source) for source in sorted(_BASE_SOURCES))],
            "no answer": [no_answer, landing.no_answer_document("why")],
        },
    )


# --- `pkit decisions check-diff --json` ---------------------------------------------------

CHECK_DIFF = Contract(
    name="pkit decisions check-diff --json",
    version=1,
    forms={
        "answer": Form(
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
        "accepted_changes[].points[].change": _POINT_CHANGES,
    },
)


def _numbering_report() -> dict[str, Any]:
    """A numbering check holding every key: an error and a warning, and an accepted
    record changed in each way the check tells."""
    changed = numbering.ChangedRecord(
        _RECORD,
        "PRJ-001",
        points=tuple(
            numbering.PointChange(f"{i}", change, "A title")
            for i, change in enumerate(sorted(_POINT_CHANGES), start=1)
        ),
        fields=("status",),
        shared=True,
        other=True,
        list_form=True,
    )
    report = numbering.Report(
        "main",
        "f" * 40,
        "t" * 40,
        2,
        (
            Finding(_RECORD, "point 1 was dropped", Severity.ERROR),
            Finding(_RECORD, "a title moved", Severity.WARNING),
        ),
        (changed, numbering.ChangedRecord(_RECORD, "PRJ-002", removed=True)),
    )
    return numbering.as_json(report, "h" * 40)


def test_the_numbering_check_document_holds_its_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = GitRepo.init(tmp_path / "work")
    monkeypatch.chdir(repo.root)
    repo.commit("start", {"README.md": "A project.\n"})
    no_record = document_of(invoke("decisions", "check-diff", "--base", "main", JSON_OPTION))
    repo.commit("accept it", {_RECORD: _record("accepted")})
    repo.checkout("change", create=True)
    repo.commit("refine it", {_RECORD: _record("accepted").replace("Text of 1.", "Text.")})
    printed = document_of(invoke("decisions", "check-diff", "--base", "main", JSON_OPTION))
    at_head = document_of(
        invoke("decisions", "check-diff", "--base", "main", "--head", "HEAD", JSON_OPTION)
    )
    check(CHECK_DIFF, {"answer": [no_record, printed, at_head, _numbering_report()]})


# --- `pkit connections resolve --json` ----------------------------------------------------

DATA_POINT = Contract(
    name="pkit connections resolve --json",
    version=1,
    forms={
        "defined": Form(
            keys={
                "schema_version": "int",
                "address": "str",
                "defined": "bool",
                "from": "str",
                "provider": "str",
                "policy": "str",
                "inert_policy": "str",
                "participation": "str|null",
                "resolved": "bool",
                "outcome": "str",
                "why": "str",
                "value": ANY,
                "origin": "str",
                "entries": "list",
                "entries[]": "object",
                "entries[].id": "str",
                "entries[].origin": "str",
                "entries[].replaces": "list",
                "entries[].replaces[]": "str",
                "entries[].value": ANY,
                "removals": "list",
                "removals[]": "object",
                "removals[].id": "str",
                "removals[].reason": "str",
                "removals[].removed_from": "list",
                "removals[].removed_from[]": "str",
                "fillers": "list",
                "fillers[]": "object",
                "fillers[].source": "str",
                "fillers[].name": "str",
                "fillers[].supplies": "str",
                "fillers[].state": "str",
                "fillers[].reason": "str",
                "fillers[].query_contract": "bool|null",
                "fillers[].reads": "list",
                "fillers[].reads[]": "object",
                "fillers[].reads[].state": "str",
                "fillers[].reads[].ref": "str|null",
                "fillers[].reads[].commit": "str|null",
                "fillers[].reads[].shallow": "bool",
            }
        ),
        "undefined": Form(
            keys={
                "schema_version": "int",
                "address": "str",
                "defined": "bool",
                "from": "str",
                "resolved": "bool",
                "outcome": "str",
                "why": "str",
                "value": "null",
            }
        ),
    },
    sets={
        "from": frozenset({"resolution", "run-cache"}),
        "outcome": frozenset(
            {
                "resolved",
                "undefined",
                "unfilled",
                "no-answer",
                "inert-fail",
                "collision",
                "selection-needed",
                "selection-unmatched",
                "definer-defect",
            }
        ),
        "fillers[].source": frozenset({"project filler", "contribution", "default"}),
        "fillers[].state": frozenset({"taken", "inert", "passed over"}),
        "fillers[].reads[].state": frozenset({"history", "settled"}),
    },
    payloads=frozenset({"value", "entries[].value"}),
)

_ADDRESS = "pkit::work-tracking:doc-check"


def _point(outcome: dp.Outcome, value: Any) -> dp.ResolvedPoint:
    reads = (
        dp.FillerRead("history", "HEAD", "c" * 40, shallow=False),
        dp.FillerRead("settled", None, None),
    )
    return dp.ResolvedPoint(
        address=_ADDRESS,
        provider="project-management",
        policy="union",
        inert_policy="fallback",
        participation=None if value is None else "always",
        fillers=tuple(
            dp.Filler(source, "a filler", "a supply", state, "why", query, reads)
            for source, state, query in zip(
                dp.FillerSource, dp.FillerState, (True, False, None), strict=True
            )
        ),
        outcome=outcome,
        value=value,
        origin="living-docs",
        entries=(dp.Entry("one", {"any": ["payload"]}, "living-docs", ("project filler",)),),
        removals=(dp.Removal("two", "not wanted", ("living-docs",)),),
        why="why",
    )


def test_the_data_point_document_holds_its_contract(make_adopter_repo: Any) -> None:
    make_adopter_repo()
    undefined = document_of(invoke("connections", "resolve", _ADDRESS, JSON_OPTION))
    defined = [
        dp.point_document(_point(dp.Outcome.RESOLVED, [{"id": "one"}])),
        dp.point_document(_point(dp.Outcome.NO_ANSWER, None), source=dp.FROM_RUN_CACHE),
    ]
    check(
        DATA_POINT,
        {"defined": defined, "undefined": [undefined, dp.undefined_document(_ADDRESS, "why")]},
        enumerations={
            "outcome": (outcome.value for outcome in dp.Outcome),
            "fillers[].source": (source.value for source in dp.FillerSource),
            "fillers[].state": (state.value for state in dp.FillerState),
            "fillers[].reads[].state": ("history", "settled"),
        },
    )


# --- `pkit friction since --json` ----------------------------------------------------------

FRICTION_SINCE = Contract(
    name="pkit friction since --json",
    version=2,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "report": "str",
                "since": "str",
                "head": "str",
                "base": "object",
                "base.ref": "str",
                "base.tip": "str",
                "all_inside": "bool",
                "reason": "str|null",
                "commits": "list",
                "commits[]": "object",
                "commits[].commit": "str",
                "commits[].merges_base": "bool",
                "inside": "list",
                "inside[]": "str",
                "outside": "list",
                "outside[]": "object",
                "outside[].path": "str|null",
                "outside[].commit": "str",
                "outside[].why": "str",
            }
        )
    },
    sets={"report": frozenset({"since"})},
    raised_before={
        2: "what `all_inside` counts: answer files the change adds, where version 1 counted "
        "the artefacts' `revalidated` blocks and `revisited` lists (ADR-068 point 5)"
    },
)


def test_the_friction_since_document_holds_its_contract(committed_adopter: AdopterRepo) -> None:
    repo = committed_adopter
    since = repo.head()
    repo.commit("an edit", {"docs/a.md": "A page.\n"})
    printed = document_of(invoke("friction", "since", since, "--base", "main", JSON_OPTION))
    built = json.loads(
        fs.render_json(
            fs.Since(
                since="s" * 40,
                head="h" * 40,
                base_ref="main",
                base_tip="t" * 40,
                steps=(fs.Step("h" * 40, merges_base=True),),
                inside=("answers/one.yaml",),
                outside=(fs.Outside(None, "h" * 40, "a merge conflict"),),
                reason="the head does not descend from it",
            )
        )
    )
    check(FRICTION_SINCE, {"answer": [printed, built]})


# --- `pkit friction move-plan --json` and `pkit friction prune --json` ------------------------

FRICTION_MOVE_PLAN = Contract(
    name="pkit friction move-plan --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "report": "str",
                "folder": "str",
                "files": "list",
                "files[]": "object",
                "files[].path": "str",
                "files[].sha256": "str",
                "files[].text": "str",
                "files[].answers": "list",
                "files[].answers[]": "object",
                "files[].answers[].artefact": "str",
                "files[].answers[].path": "str",
                "files[].answers[].text": "str",
                "left": "list",
                "left[]": "object",
                "left[].artefact": "str",
                "left[].path": "str",
                "left[].reason": "str",
            }
        )
    },
    sets={"report": frozenset({"move-plan"})},
)

FRICTION_PRUNE = Contract(
    name="pkit friction prune --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "report": "str",
                "dry_run": "bool",
                "head": "str",
                "folder": "str",
                "files": "int",
                "live": "int",
                "remove": "list",
                "remove[]": "str",
                "removed": "list",
                "removed[]": "str",
                "kept": "list",
                "kept[]": "object",
                "kept[].path": "str",
                "kept[].why": "str",
            }
        )
    },
    sets={"report": frozenset({"prune"})},
)


def test_the_answer_move_and_prune_documents_hold_their_contracts(
    committed_adopter: AdopterRepo,
) -> None:
    moved = fmove.MovePlan(
        files=(
            fmove.MovedFile(
                "docs/guide.md",
                "s" * 64,
                "A page.\n",
                (fmove.MovedAnswers("guide", "answers/one.yaml", "answers: []\n"),),
            ),
        ),
        left=(fmove.LeftAnswers("other", "docs/other.md", "its block is an alias"),),
    )
    check(
        FRICTION_MOVE_PLAN,
        {
            "answer": [
                document_of(invoke("friction", "move-plan", JSON_OPTION)),
                json.loads(fmove.render_json(moved)),
            ]
        },
    )
    pruned = fprune.PrunePlan(
        "h" * 40, 3, 1, ("one.yaml",), (fprune.KeptFile("two.yaml", "a live deferral keeps it"),)
    )
    check(
        FRICTION_PRUNE,
        {
            "answer": [
                document_of(invoke("friction", "prune", "--dry-run", JSON_OPTION)),
                json.loads(fprune.render_json(pruned, dry_run=False, removed=("one.yaml",))),
            ]
        },
    )


# --- `pkit rule-sets reach --json` and `pkit rule-sets altered --json` ---------------------


_RULE = {
    "rule": "str",
    "id": "str",
    "status": "str",
    "rule_set": "str",
    "rule_set_path": "str",
    "previewed": "bool",
    "text": "str",
}
_PINS = {
    "pins": "list",
    "pins[]": "object",
    "pins[].by": "str",
    "pins[].by_rule_set": "str",
    "pins[].pin": "str",
}

#: One artefact with the walk's answer for it, as `rule_set_reading.artefact_entry`
#: builds it wherever a document holds it.
RULED = Form(
    keys={
        "location": "str",
        "path": "str",
        "id": "str",
        "kind": "str",
        "span": "object|null",
        "span.first_line": "int",
        "span.last_line": "int",
        "rules": "list",
        "rules[]": "object",
        **{f"rules[].{key}": kind for key, kind in _RULE.items()},
        "rules[].covering": "list",
        "rules[].covering[]": "str",
        "rules[].fills": "list",
        "rules[].fills[]": "str",
        "rules[].checks": "list",
        "rules[].checks[]": "object",
        "rules[].checks[].check": "str",
        "rules[].checks[].part": "str",
        "rules[].checks[].there": "bool",
        "rules[].checks[].problem": "str|null",
        "conflicts": "list",
        "conflicts[]": "object",
        "conflicts[].kind": "str",
        "conflicts[].previewed": "bool",
        "conflicts[].rule_set": "str",
        "conflicts[].rule_set_path": "str",
        "conflicts[].version": "str",
        **{f"conflicts[].{key}": kind for key, kind in _PINS.items()},
        "conflicts[].point": "str",
        "conflicts[].brought": "list",
        "conflicts[].brought[]": "object",
        "conflicts[].brought[].by": "str",
        "conflicts[].brought[].by_rule_set": "str",
        "conflicts[].brought[].fills": "list",
        "conflicts[].brought[].fills[]": "str",
        "held": "list",
        "held[]": "object",
        **{f"held[].{key}": kind for key, kind in _RULE.items()},
        **{f"held[].{key}": kind for key, kind in _PINS.items()},
    }
)

_RULED_SETS = {
    "ruled:kind": frozenset({"document", "entry"}),
    "ruled:conflicts[].kind": frozenset({"pin", "fill"}),
}

_PATH_ANSWERS = frozenset({"artefact", "not-artefact", "unreadable", "folder", "absent", "outside"})

RULE_SETS_REACH = Contract(
    name="pkit rule-sets reach --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "commit": "str|null",
                "preview": "bool",
                "paths": "list|null",
                "paths[]": "object",
                "paths[].given": "str",
                "paths[].path": "str|null",
                "paths[].answer": "str",
                "paths[].artefacts": "list",
                "paths[].artefacts[]": "str",
                "artefacts": "list",
                "artefacts[]": "object",
            }
        )
    },
    shapes={"ruled": RULED},
    refs={"artefacts[]": "ruled"},
    sets={"paths[].answer": _PATH_ANSWERS, **_RULED_SETS},
)

_ALTERATIONS = frozenset({"added", "removed", "changed"})
_BUDGET_CHANGES = frozenset({"raised", "lowered", "added", "removed"})

RULE_SETS_ALTERED = Contract(
    name="pkit rule-sets altered --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "base": "object",
                "base.ref": "str",
                "base.tip": "str",
                "base.commit": "str",
                "base.outdated": "bool",
                "head": "object",
                "head.commit": "str",
                "head.uncommitted_paths": "int",
                "head.working_tree": "bool",
                "artefacts": "list",
                "artefacts[]": "object",
                "artefacts[].change": "str",
                "artefacts[].base": "object|null",
                "artefacts[].head": "object|null",
                "artefacts[].brought_under": "list",
                "artefacts[].brought_under[]": "str",
                "brought_unaltered": "list",
                "brought_unaltered[]": "object",
                "brought_unaltered[].change": "str",
                "brought_unaltered[].base": "object",
                "brought_unaltered[].head": "object",
                "brought_unaltered[].brought_under": "list",
                "brought_unaltered[].brought_under[]": "str",
                "budgets": "list",
                "budgets[]": "object",
                "budgets[].set_by": "str",
                "budgets[].path": "str",
                "budgets[].file": "str|null",
                "budgets[].base": "int|null",
                "budgets[].head": "int|null",
                "budgets[].change": "str",
            }
        )
    },
    shapes={"ruled": RULED},
    refs={
        "artefacts[].base": "ruled",
        "artefacts[].head": "ruled",
        "brought_unaltered[].base": "ruled",
        "brought_unaltered[].head": "ruled",
    },
    sets={
        "artefacts[].change": _ALTERATIONS,
        "brought_unaltered[].change": frozenset({"unaltered"}),
        "budgets[].change": _BUDGET_CHANGES,
        **_RULED_SETS,
    },
)

_ENTRIES = f"{reach.SETS}/two.md"
_CHECKS = {
    "RS-CMN-001": [
        {"check": "backbone:validate", "part": "The field resolves."},
        {"check": "backbone:no-such-check", "part": "Nothing."},
    ]
}


def _reach_states(repo: AdopterRepo) -> Iterator[dict[str, Any]]:
    """The walk's document at each state that prints a part of it: rules with checks
    and fills, entries with their spans, a rule held back, and each kind of conflict,
    under the preview too."""
    reach.lay_out(
        repo,
        {
            "cmn": reach.rule_set(
                "CMN",
                entries={**rules("RS-CMN-001", offers=["where"]), **rules("RS-CMN-002")},
                checks=_CHECKS,
            ),
            "doc": reach.rule_set(
                "DOC",
                inherits=["CMN@1"],
                scope=reach.scoped(f"{reach.GUIDES}/**", _ENTRIES),
                entries=rules(
                    "RS-DOC-001", fills=["RS-CMN-001#where"], **anchored_to("RS-CMN-001")
                ),
            ),
            "two": reach.rule_set("TWO", entries=rules("RS-TWO-001", "RS-TWO-002")),
        },
        a=reach.page(),
    )
    yield reading.reach_document(repo.root)
    yield reading.reach_document(repo.root, preview=True)
    reach.lay_out(
        repo,
        {
            "cmn": reach.rule_set("CMN", "2.0.0"),
            "doc": reach.rule_set(
                "DOC", inherits=["CMN@1"], scope=reach.scoped(f"{reach.GUIDES}/**")
            ),
        },
        a=reach.page(),
    )
    yield reading.reach_document(repo.root)
    reach.lay_out(
        repo,
        {
            "cmn": reach.rule_set("CMN", "2.0.0"),
            "tech": reach.rule_set(
                "TECH", inherits=["CMN@1"], scope=reach.scoped(f"{reach.GUIDES}/**")
            ),
            "user": reach.rule_set(
                "USER", inherits=["CMN@2"], scope=reach.scoped(f"{reach.GUIDES}/a.md")
            ),
        },
        a=reach.page(),
    )
    yield reading.reach_document(repo.root)
    reach.lay_out(
        repo,
        {
            "cmn": reach._offering(),
            "tech": reach.rule_set(
                "TECH",
                inherits=["CMN@1"],
                scope=reach.scoped(f"{reach.GUIDES}/**"),
                entries=rules("RS-TECH-001", **reach._filling()),
            ),
            "user": reach.rule_set(
                "USER", inherits=["CMN@1"], scope=reach.scoped(f"{reach.GUIDES}/a.md")
            ),
        },
        a=reach.page(),
    )
    yield reading.reach_document(repo.root)


def test_the_rule_sets_reach_document_holds_its_contract(
    make_adopter_repo: Any, tmp_path: Path
) -> None:
    repo = make_adopter_repo()
    built = list(_reach_states(repo))
    repo.write(
        {
            f"{reach.GUIDES}/broken.md": "---\ntitle: [unclosed\n---\n\nBody.\n",
            "notes/plain.txt": "Not an artefact.\n",
        }
    )
    repo.commit("the last state", files=None)
    given = (
        f"{reach.GUIDES}/a.md",
        f"{reach.GUIDES}/broken.md",
        "notes/plain.txt",
        "notes",
        "nowhere.md",
        str(tmp_path.parent),
    )
    printed = document_of(invoke("rule-sets", "reach", *given, JSON_OPTION))
    at_commit = document_of(invoke("rule-sets", "reach", "--at", repo.head(), JSON_OPTION))
    check(RULE_SETS_REACH, {"answer": [printed, at_commit, *built]})


def _ruled_states(repo: AdopterRepo) -> list[dict[str, Any]]:
    """`rule-sets altered` at each of the reach states: the ruled guide changed in the
    working tree against the state committed, so both sides carry every part of the
    walk's answer."""
    found = []
    for count, _document in enumerate(_reach_states(repo)):
        repo.git("add", "-A")
        repo.git("commit", "-q", "--allow-empty", "-m", f"state {count}")
        repo.write({reach.A: reach.page(body=f"Changed {count}.")})
        found.append(reading.altered_document(repo.root, "HEAD"))
    return found


def test_the_rule_sets_altered_document_holds_its_contract(make_adopter_repo: Any) -> None:
    check(RULE_SETS_ALTERED, {"answer": _altered_documents(make_adopter_repo())})


def _altered_documents(repo: AdopterRepo) -> list[dict[str, Any]]:
    """The walk's documents of a change that alters, adds, renames and brings artefacts
    under a rule, between named commits too, with every kind of budget change, and at
    each ruled state."""
    reach._start(repo)
    repo.commit(
        "change",
        {
            f"{reach.GUIDES}/c.md": reach.page("C", body="A new body."),
            f"{reach.GUIDES}/old.md": None,
            f"{reach.GUIDES}/new.md": reach.page(
                "New", body="A new guide on another subject: nothing in it is the old one."
            ),
        },
    )
    repo.write(
        {
            f"{reach.SETS}/doc.md": rule_set_text(
                reach.rule_set(
                    "DOC",
                    inherits=["CMN@1"],
                    scope=reach.scoped(f"{reach.GUIDES}/**"),
                    entries=rules("RS-DOC-001", "RS-DOC-002"),
                )
            )
        }
    )
    printed = document_of(invoke("rule-sets", "altered", "--base", "main", JSON_OPTION))
    named = document_of(
        invoke("rule-sets", "altered", "--base", "main", "--head", "feature", JSON_OPTION)
    )
    budgets = [
        reading.budget_entry(lr.BudgetChange("OWN", "docs/rule-sets/own.md", file, base, head))
        for file, base, head in (
            ("CLAUDE.md", 40, 50),
            (None, 50, 40),
            (None, None, 40),
            ("CLAUDE.md", 40, None),
        )
    ]
    return [printed, named, {**printed, "budgets": budgets}, *_ruled_states(repo)]


# --- `pkit rule-sets loaded --json` ---------------------------------------------------------

RULE_SETS_LOADED = Contract(
    name="pkit rule-sets loaded --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "loaded": "list",
                "loaded[]": "object",
                "loaded[].layer": "str",
                "loaded[].owner": "str",
                "loaded[].path": "str",
                "loaded[].rule_set": "str|null",
                "loaded[].set_path": "str|null",
                "loaded[].present": "bool",
                "index": "object",
                "index.path": "str",
                "index.present": "bool",
            }
        )
    },
    sets={"loaded[].layer": frozenset({"backbone", "capability", "project"})},
)


def test_the_loaded_rules_document_holds_its_contract(make_adopter_repo: Any) -> None:
    make_adopter_repo(capabilities=("project-management",))
    check(
        RULE_SETS_LOADED,
        {"answer": [document_of(invoke("rule-sets", "loaded", JSON_OPTION))]},
    )


# --- `pkit friction artefacts --json` ------------------------------------------------------

_PLACE_SKIPS = frozenset({"malformed", "outside-repository"})
_HELD_SKIPS = frozenset({"malformed", "outside-repository", "overlap"})

_LOCATION = {
    "location": "object|null",
    "location.name": "str",
    "location.path": "str",
    "location.root": "str",
}
_SPAN = {"span": "object|null", "span.first_line": "int", "span.last_line": "int"}

FRICTION_ARTEFACTS = Contract(
    name="pkit friction artefacts --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "roots": "object",
                "roots.internal": "str",
                "roots.user": "str",
                "places": "list",
                "places[]": "object",
                "places[].source": "str",
                "places[].declared": "bool",
                "places[].file": "str",
                "places[].pointer": "str",
                "places[].written": "str|null",
                **{f"places[].{key}": kind for key, kind in _LOCATION.items()},
                "places[].path": "str|null",
                "places[].rule_sets": "object|null",
                "places[].rule_sets.component": "str|null",
                "places[].encloses": "list",
                "places[].encloses[]": "str",
                "places[].files": "list",
                "places[].files[]": "str",
                "places[].synced": "list",
                "places[].synced[]": "str",
                "places[].skipped": "object|null",
                "places[].skipped.reason": "str",
                "places[].skipped.detail": "str",
                "places[].type": "str|null",
                "files": "list",
                "files[]": "object",
                "files[].path": "str",
                "files[].places": "list",
                "files[].places[]": "int",
                "files[].rule_set": "int|null",
                "files[].excluded": "bool",
                "files[].fields": "object|null",
                "files[].unreadable": "str|null",
                "artefacts": "list",
                "artefacts[]": "object",
                "artefacts[].path": "str",
                "artefacts[].id": "str",
                "artefacts[].kind": "str",
                "artefacts[].location": "str",
                "artefacts[].place": "int",
                "artefacts[].rule_set": "int|null",
                "artefacts[].container": "bool",
                "artefacts[].friction": "bool",
                "artefacts[].anchors": "object",
                "artefacts[].anchors{}": "list",
                "artefacts[].anchors{}[]": "str",
                "artefacts[].unanchored_because": "str|null",
                "artefacts[].fields": "object",
                **{f"artefacts[].{key}": kind for key, kind in _SPAN.items()},
                "artefacts[].part_anchors": "list",
                "artefacts[].part_anchors[]": "object",
                "artefacts[].part_anchors[].kind": "str",
                "artefacts[].part_anchors[].value": "str",
                "artefacts[].part_anchors[].path": "str",
                **{f"artefacts[].part_anchors[].{key}": kind for key, kind in _SPAN.items()},
                "artefacts[].path_anchors": "list",
                "artefacts[].path_anchors[]": "object",
                "artefacts[].path_anchors[].value": "str",
                "artefacts[].path_anchors[].files": "list",
                "artefacts[].path_anchors[].files[]": "str",
                "artefacts[].in_scope_of": "list",
                "artefacts[].in_scope_of[]": "str",
                "artefacts[].type": "str|null",
                "artefacts[].type_place": "int|null",
                "artefacts[].type_conflict": "list",
                "artefacts[].type_conflict[]": "object",
                "artefacts[].type_conflict[].type": "str",
                "artefacts[].type_conflict[].place": "int",
                "artefacts[].ranked_places": "list",
                "artefacts[].ranked_places[]": "object",
                "artefacts[].ranked_places[].place": "int",
                "artefacts[].ranked_places[].rank": "int",
                "types": "object",
                "types{}": "object",
                "types{}.component": "str",
                "types{}.name": "str",
                "types{}.description": "str",
                "types{}.kind_field": "str|null",
                "types{}.project_places": "bool",
                "held": "list",
                "held[]": "object",
                "held[].source": "str",
                "held[].file": "str",
                "held[].pointer": "str",
                "held[].written": "str|null",
                **{f"held[].{key}": kind for key, kind in _LOCATION.items()},
                "held[].path": "str|null",
                "held[].files": "list",
                "held[].files[]": "str",
                "held[].skipped": "object|null",
                "held[].skipped.reason": "str",
                "held[].skipped.detail": "str",
                "held_files": "list",
                "held_files[]": "object",
                "held_files[].path": "str",
                "held_files[].held": "int",
                "held_files[].places": "list",
                "held_files[].places[]": "int",
                "held_files[].excluded": "bool",
                "held_files[].fields": "object|null",
                "held_files[].unreadable": "str|null",
                "unplaced": "object",
                "unplaced{}": "object",
                "unplaced{}{}": "object",
                "unplaced{}{}.path": "str",
                "unplaced{}{}.files": "list",
                "unplaced{}{}.files[]": "object",
                "unplaced{}{}.files[].path": "str",
                "unplaced{}{}.files[].excluded": "bool",
            }
        )
    },
    sets={
        "places[].encloses[]": frozenset({"user", "internal"}),
        "places[].skipped.reason": _PLACE_SKIPS,
        "artefacts[].kind": frozenset({"document", "entry"}),
        "held[].skipped.reason": _HELD_SKIPS,
    },
    data=frozenset({"types", "unplaced", "unplaced{}", "artefacts[].anchors"}),
    payloads=frozenset({"files[].fields", "artefacts[].fields", "held_files[].fields"}),
)

_LOGS = artefacts_tests.LOGS
_ROOTS = "docs:\n  user: handbook\n  internal: tech-docs\n"


def _evidence_adopter(make_adopter_repo: Any) -> AdopterRepo:
    """The artefacts tests' adopter: project places and the evidence capability's, with
    their locations and a type that asks for a kind, a document, a collection, a plain
    file and an excluded one."""
    repo = make_adopter_repo(capabilities=("evidence",), prepare=commit_install)
    artefacts_tests._evidence_declares(
        repo,
        "docs:\n"
        "  locations:\n"
        "    runs: {path: evidence}\n"
        "    guides: {path: guides, root: user}\n"
        "friction:\n"
        "  types:\n"
        "    page: {description: A page., kind-field: kind}\n"
        "  places:\n"
        "    - {location: runs, path: '**/*.md'}\n"
        "    - {location: guides, path: '*.md'}\n",
    )
    repo.write(
        {
            FRICTION_CONFIG: (
                f"{_ROOTS}friction:\n  places: [notes, notes/rules.md, handbook]\n"
                "  exclude: [notes/old.md]\n"
            ),
            "notes/guide.md": artefacts_tests.ANCHORED.format(id="guide"),
            "notes/rules.md": artefacts_tests.COLLECTION,
            "notes/plain.md": "# No front matter\n",
            "notes/old.md": "# Excluded\n",
            "tech-docs/evidence/run.md": artefacts_tests.ANCHORED.format(id="run"),
            "handbook/guides/start.md": artefacts_tests.ANCHORED.format(id="start"),
            "src/cli.py": "print('the CLI')\n",
        }
    )
    return repo


def _configure(repo: AdopterRepo, places: str, exclude: str = "notes/old.md") -> None:
    repo.write(
        {FRICTION_CONFIG: f"{_ROOTS}friction:\n  places: [{places}]\n  exclude: [{exclude}]\n"}
    )


def _artefacts_states(repo: AdopterRepo) -> Iterator[dict[str, Any]]:
    """The artefacts document at each state that prints a part of it: part and path
    anchors, a rule set's scope and an unreadable file; a malformed place, one outside
    the repository and a synced copy; held folders, held files and unplaced ones; and
    places that type a file, and tie on another."""
    repo.write(
        {
            artefacts_tests.TERMS: artefacts_tests.SECTIONED,
            "notes/page.md": artefacts_tests.PAGE,
            "tech-docs/rule-sets/doc.md": artefacts_tests.DOC_RULES.replace(
                "version: 1.0.0\n", "version: 1.0.0\nscope: [notes/**]\n"
            ),
            "notes/broken.md": "---\ntitle: [unclosed\n---\n\n# Broken\n",
        }
    )
    yield fd.artefacts_document(repo.root)
    artefacts_tests._evidence_declares(repo, "    - {location: runs}\n")
    _configure(repo, f"notes, ../elsewhere, {artefacts_tests.EVIDENCE_README}")
    yield fd.artefacts_document(repo.root)
    artefacts_tests._logs_declared(
        repo,
        "    - {location: logs, path: records}\n"
        "    - {location: logs, path: shared}\n"
        "    - {location: logs, path: shared/x}\n"
        "    - {location: logs, path: linked}\n"
        "    - {path: stray}\n",
    )
    outside = repo.root.parent / f"{repo.root.name}-outside"
    outside.mkdir()
    (repo.root / _LOGS).mkdir(parents=True, exist_ok=True)
    (repo.root / _LOGS / "linked").symlink_to(outside, target_is_directory=True)
    _configure(repo, f"notes, {_LOGS}", exclude=f"notes/old.md, {_LOGS}/old.md")
    repo.write(
        {
            f"{_LOGS}/records/2026-10-01.md": "---\ndate: '2026-10-01'\n---\n\n# A run\n",
            f"{_LOGS}/records/broken.md": "---\ndate: [unclosed\n---\n",
            f"{_LOGS}/loose.md": "# Loose\n",
            f"{_LOGS}/old.md": "# Old\n",
        }
    )
    yield fd.artefacts_document(repo.root)
    _configure(
        repo,
        "{path: notes, type: plain}, {path: 'notes/**', type: starred}, "
        "{path: notes/rules.md, type: ruled}",
    )
    yield fd.artefacts_document(repo.root)


def test_the_friction_artefacts_document_holds_its_contract(make_adopter_repo: Any) -> None:
    repo = _evidence_adopter(make_adopter_repo)
    printed = document_of(invoke("friction", "artefacts", JSON_OPTION))
    at_commit = document_of(invoke("friction", "artefacts", "--at", "HEAD", JSON_OPTION))
    check(
        FRICTION_ARTEFACTS,
        {"answer": [printed, at_commit, *_artefacts_states(repo)]},
        enumerations={"places[].encloses[]": docs_roots.AUDIENCES},
    )


# --- `pkit friction check --json` ----------------------------------------------------------

_MODES = frozenset({"warning", "enforcing"})
_ANCHOR = {"anchor": "object|null", "anchor.kind": "str", "anchor.value": "str"}
_CHANGE_KINDS = frozenset(
    {
        "friction",
        "answered",
        "revalidated",
        "bump",
        "dead-anchor",
        "dead-unattributed",
        "unresolved-kind",
        "no-answer",
        "left-out",
        "outdated-base",
        "unreadable",
        "revisited",
        "unrevisited",
        "shared-id",
        "answer-file-rewritten",
        "prune-mixed",
        "read-incomplete",
        "answers-nothing",
        "answer-on-what-is-gone",
        "answered-apart",
    }
)

#: An answer the change wrote, as `friction_check.WrittenAnswer.as_json` builds it in
#: `answers` and `moved`.
WRITTEN = Form(
    keys={
        "artefact": "str",
        "location": "str",
        "answer": "str|null",
        **_ANCHOR,
        "reason": "str|null",
        "kept": "list",
        "kept[]": "object",
        **{f"kept[].{key}": kind for key, kind in _ANCHOR.items()},
        "kept[].reason": "str|null",
        "asked": "bool",
        "status": "str",
        "new": "bool",
        "put_back": "bool",
        "changed": "list",
        "changed[]": "object|null",
        "changed[].kind": "str",
        "changed[].value": "str",
        "file": "str|null",
        "replaces_apart": "list",
        "replaces_apart[]": "str",
        "moved": "bool",
        "outcome": "str|null",
        "target": "object|null",
        "target.kind": "str",
        "target.value": "str",
        "links": "list",
        "links[]": "str",
        "fields": "list",
        "fields[]": "str",
    }
)

FRICTION_CHECK = Contract(
    name="pkit friction check --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "check": "str",
                "mode": "str",
                "dormant": "bool",
                "failed": "bool",
                "base": "object|null",
                "base.ref": "str",
                "base.tip": "str",
                "base.commit": "str",
                "base.outdated": "bool",
                "head": "object|null",
                "head.commit": "str",
                "head.uncommitted_paths": "int",
                "head.own": "str",
                "counts": "object",
                "counts.places": "int",
                "counts.artefacts": "int",
                "counts.carrying": "int",
                **{f"counts.{kind}": "int" for kind in sorted(_CHANGE_KINDS)},
                "findings": "list",
                "findings[]": "object",
                "findings[].artefact": "str|null",
                "findings[].location": "str|null",
                "findings[].kind": "str",
                **{f"findings[].{key}": kind for key, kind in _ANCHOR.items()},
                "findings[].answer": "str|null",
                "findings[].message": "str",
                "answers": "list",
                "answers[]": "object",
                "moved": "list",
                "moved[]": "object",
                "answered_apart_at_tip": "list",
                "answered_apart_at_tip[]": "object",
                "answered_apart_at_tip[].artefact": "str",
                "answered_apart_at_tip[].location": "str",
                "answered_apart_at_tip[].revalidations": "list",
                "answered_apart_at_tip[].revalidations[]": "object",
                "answered_apart_at_tip[].revalidations[].file": "str|null",
                "answered_apart_at_tip[].revalidations[].at": "str|null",
                "answered_apart_at_tip[].revalidations[].outcome": "str|null",
                "answered_apart_at_tip[].revalidations[].unchanged_because": "str|null",
                "unreadable": "list",
                "unreadable[]": "str",
                "history": "object|null",
                "history.shallow": "bool",
                "history.cut": "list",
                "history.cut[]": "str",
            }
        ),
        "refusal": Form(
            keys={
                "schema_version": "int",
                "check": "str",
                "failed": "bool",
                "refused": "object",
                "refused.kind": "str",
                "refused.head": "str",
                "refused.anchor": "object",
                "refused.anchor.kind": "str",
                "refused.anchor.value": "str",
                "refused.working_tree": "str",
                "refused.message": "str",
            }
        ),
    },
    shapes={"written": WRITTEN},
    refs={"answers[]": "written", "moved[]": "written"},
    sets={
        "check": frozenset({"change"}),
        "mode": _MODES,
        "findings[].kind": _CHANGE_KINDS,
        "findings[].answer": frozenset({"updated", "unchanged", "deferred", "new"}),
        "written:answer": frozenset(
            {"updated", "unchanged", "deferred", "unanchored", "revisited"}
        ),
        "written:status": frozenset({"stands", "bump", "edited", "written-back"}),
        "written:outcome": frozenset({"updated", "unchanged", "deferred"}),
        "refused.kind": frozenset({"resolver-elsewhere"}),
    },
)


def _written(answer: str, status: fc.AnswerStatus, **revisit: Any) -> fc.WrittenAnswer:
    anchor = fd.Anchor("path", "src/**")
    return fc.WrittenAnswer(
        "guide",
        "docs/guide.md",
        answer,
        anchor if answer == "deferred" else None,
        "a reason",
        (fc.KeptDeferral(anchor, "kept"),),
        True,
        status,
        False,
        changed=(anchor,),
        file="answers/one.yaml",
        replaces_apart=("answers/two.yaml",),
        **revisit,
    )


def _change_check() -> dict[str, Any]:
    """A change check holding every key: a finding of each kind, each kind of answer the
    change writes in each status, an answer moved, revalidations answered apart at the
    base's tip, and a history cut."""
    anchor = fd.Anchor("path", "src/**")
    written = [
        _written(answer, status)
        for answer, status in zip(
            ("updated", "unchanged", "deferred", "unanchored"), fc.AnswerStatus, strict=True
        )
    ]
    written += [
        _written(
            "revisited",
            fc.AnswerStatus.STANDS,
            outcome=outcome,
            target=anchor,
            links=("triggers",),
            fields=("status",),
        )
        for outcome in ("unchanged", "deferred")
    ]
    answers = [*fc.Answer]
    result = fc.ChangeCheck(
        mode="enforcing",
        mode_as_written="enforcing",
        dormant=False,
        places=1,
        artefacts=1,
        carrying=1,
        base=fc.BaseState("main", "t" * 40, "f" * 40, outdated=True),
        head=fc.HeadState("h" * 40, 2),
        findings=tuple(
            fc.Finding(
                kind,
                "why",
                "guide",
                "docs/guide.md",
                anchor,
                answers[index] if index < len(answers) else None,
            )
            for index, kind in enumerate(fc.FindingKind)
        ),
        answers=tuple(written),
        unreadable=("docs/broken.md",),
        shallow=True,
        cut=("docs/guide.md",),
        moved=(_written("updated", fc.AnswerStatus.STANDS),),
        apart_at_tip=(
            fc.ApartAtTip(
                "guide",
                "docs/guide.md",
                (
                    af.LiveRevalidation(
                        "answers/one.yaml",
                        None,
                        "2026-10-01T09:00:00Z",
                        "unchanged",
                        "the CLI is as described",
                    ),
                    af.LiveRevalidation(None, None, None, None, None),
                ),
            ),
        ),
    )
    return json.loads(fc.render_json(result))


def _refusal() -> dict[str, Any]:
    refused = fc.ResolverElsewhere(
        "the resolver runs only from the head",
        head="h" * 40,
        anchor=fd.Anchor("artefact", "guide"),
        working_tree="w" * 40,
    )
    return json.loads(fc.render_refusal_json(refused))


@pytest.mark.usefixtures("answers_in_files")
def test_the_friction_check_document_holds_its_contract(committed_adopter: AdopterRepo) -> None:
    """The run changes the CLI under the guide, and the requirement's threshold with its
    test, a target the change revisits by changing it: outcome `updated`."""
    repo = committed_adopter
    revisit_tests.declare_linker(repo.root)
    repo.write(
        {
            FRICTION_CONFIG: friction_config(mode="enforcing"),
            **SOURCE,
            "docs/guide.md": guide(),
            revisit_tests.TEST_FILE: "def test_latency():\n    assert answer_time() < 2\n",
            revisit_tests.DECISION: "Cache the status.\n",
            revisit_tests.SOURCE_DOC: revisit_tests.requirement(),
        }
    )
    repo.commit("base", files=None)
    repo.checkout("feature", create=True)
    repo.commit(
        "change the CLI, and relax the threshold with its test",
        {
            "src/cli/main.py": "print('j')\n",
            revisit_tests.SOURCE_DOC: revisit_tests.requirement(threshold="10 s"),
            revisit_tests.TEST_FILE: "def test_latency():\n    assert answer_time() < 10\n",
        },
    )
    printed = document_of(invoke("friction", "check", "--base", "main", JSON_OPTION))
    outcomes = {answer.get("outcome") for answer in printed["answers"]}
    assert fc.Answer.UPDATED.value in outcomes, printed["answers"]
    check(
        FRICTION_CHECK,
        {"answer": [printed, _change_check()], "refusal": [_refusal()]},
        enumerations={
            "mode": fd.FRICTION_MODES,
            "findings[].kind": (kind.value for kind in fc.FindingKind),
            "findings[].answer": (answer.value for answer in fc.Answer),
            "written:status": (status.value for status in fc.AnswerStatus),
        },
    )


# --- `pkit friction check --all --json`, `pkit friction debt --json`, `pkit friction explain`

_REPOSITORY_KINDS = frozenset(
    {
        "stale",
        "deferred",
        "left-out",
        "dead-anchor",
        "unresolved-kind",
        "no-answer",
        "over-broad",
        "shared-id",
        "whole-and-parts",
        "unreachable",
        "unreadable",
        "answered-apart",
    }
)
_ARTEFACT_STATES = frozenset({"current", "stale", "deferred", "unreachable", "unresolved"})
_BARS = frozenset({"flags", "asks"})
_PLAIN_ANCHOR = {"kind": "str", "value": "str"}
_POINTS = {"points": "list", "points[]": "object"}

#: The shapes the three documents share: a commit, an artefact's live answers with the
#: points each keeps, a finding of the whole-repository check, and a checked artefact.
COMMIT = Form(keys={"commit": "str", "author": "str", "date": "str", "change": "str"})
ANSWERS = Form(
    keys={
        "home": "str",
        "folder": "str",
        "revalidations": "list",
        "revalidations[]": "object",
        "revalidations[].file": "str|null",
        "revalidations[].at": "str|null",
        "revalidations[].outcome": "str|null",
        "revalidations[].unchanged_because": "str|null",
        **{f"revalidations[].{key}": kind for key, kind in _POINTS.items()},
        "deferrals": "list",
        "deferrals[]": "object",
        "deferrals[].file": "str|null",
        "deferrals[].anchor": "object",
        **{f"deferrals[].anchor.{key}": kind for key, kind in _PLAIN_ANCHOR.items()},
        "deferrals[].reason": "str|null",
        "deferrals[].kept": "bool",
        **{f"deferrals[].{key}": kind for key, kind in _POINTS.items()},
        "revisits": "list",
        "revisits[]": "object",
        "revisits[].file": "str|null",
        "revisits[].anchor": "object",
        **{f"revisits[].anchor.{key}": kind for key, kind in _PLAIN_ANCHOR.items()},
        "revisits[].outcome": "str|null",
        "revisits[].reason": "str|null",
        "answered_apart": "list",
        "answered_apart[]": "list",
        "answered_apart[][]": "str",
    }
)
_FINDING_KEYS = {
    "kind": "str",
    **_ANCHOR,
    "origin": "object|null",
    "message": "str",
    "bar": "str|null",
    "share": "int|null",
    "parts": "list|null",
    "parts[]": "object",
    **{f"parts[].{key}": kind for key, kind in _PLAIN_ANCHOR.items()},
}
FINDING = Form(keys={"artefact": "str|null", "location": "str|null", **_FINDING_KEYS})
_POINTED = {
    "revalidation_point": "object|null",
    "revalidation_points": "list",
    "revalidation_points[]": "object",
    "deferral_points": "list",
    "deferral_points[]": "object",
    "deferral_points[].anchor": "object",
    **{f"deferral_points[].anchor.{key}": kind for key, kind in _PLAIN_ANCHOR.items()},
    "deferral_points[].point": "object|null",
}
REPORT = Form(
    keys={
        "artefact": "str",
        "location": "str",
        "answers": "object|null",
        "cut": "bool",
        "state": "str",
        **_POINTED,
    }
)
_REPORT_SHAPES = {"commit": COMMIT, "answers": ANSWERS, "finding": FINDING, "report": REPORT}
_COMMIT_REFS = (
    "revalidation_point",
    "revalidation_points[]",
    "deferral_points[].point",
)
_REPORT_REFS = {
    "answers:revalidations[].points[]": "commit",
    "answers:deferrals[].points[]": "commit",
    "finding:origin": "commit",
    "report:answers": "answers",
    **{f"report:{path}": "commit" for path in _COMMIT_REFS},
}
_HEAD = {"head": "object|null", "head.commit": "str", "head.uncommitted_paths": "int"}
_HISTORY = {"history": "object|null", "history.shallow": "bool"}
_ACCEPTED_UNANCHORED = {
    "accepted_unanchored": "list",
    "accepted_unanchored[]": "object",
    "accepted_unanchored[].artefact": "str",
    "accepted_unanchored[].location": "str",
    "accepted_unanchored[].reason": "str",
}

#: The keys the whole-repository check's document holds in each of its forms.
_REPOSITORY_KEYS = {
    "schema_version": "int",
    "check": "str",
    "mode": "str",
    "dormant": "bool",
    "failed": "bool",
    **_HEAD,
    **_HISTORY,
    "counts": "object",
    **{
        f"counts.{key}": "int"
        for key in (
            "places",
            "artefacts",
            "carrying",
            "checked",
            "excluded",
            "surface",
            *sorted(_REPOSITORY_KINDS),
        )
    },
    "states": "object",
    **{f"states.{state}": "int" for state in sorted(_ARTEFACT_STATES)},
    "artefacts": "list",
    "artefacts[]": "object",
    "findings": "list",
    "findings[]": "object",
    "measures": "object",
    "measures.unanchored": "list",
    "measures.unanchored[]": "str",
    **{f"measures.{key}": kind for key, kind in _ACCEPTED_UNANCHORED.items()},
    "measures.uncovered_surface": "list",
    "measures.uncovered_surface[]": "str",
    "answers": "object",
    "answers.folder": "str",
    "answers.files": "int",
}

REPOSITORY_CHECK = Contract(
    name="pkit friction check --all --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                **_REPOSITORY_KEYS,
                "answers.prunable": "list",
                "answers.prunable[]": "str",
                "selection": "null",
            }
        ),
        # Under a selection, which answer files a prune would remove is not read
        # (ADR-079 point 2).
        "selection": Form(
            keys={
                **_REPOSITORY_KEYS,
                "answers.prunable": "null",
                "selection": "object",
                "selection.named": "list",
                "selection.named[]": "str",
                "selection.absent": "list",
                "selection.absent[]": "str",
            }
        ),
    },
    shapes=_REPORT_SHAPES,
    refs={"artefacts[]": "report", "findings[]": "finding", **_REPORT_REFS},
    sets={
        "check": frozenset({"repository"}),
        "mode": _MODES,
        "finding:kind": _REPOSITORY_KINDS,
        "finding:bar": _BARS,
        "report:state": _ARTEFACT_STATES,
        "answers:home": frozenset({"block", "files"}),
    },
)

_ARTEFACT_ENTRY = {"artefact": "str", "location": "str"}

FRICTION_DEBT = Contract(
    name="pkit friction debt --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "report": "str",
                "dormant": "bool",
                **_HEAD,
                **_HISTORY,
                "counts": "object",
                **{
                    f"counts.{key}": "int"
                    for key in (
                        "stale",
                        "deferred",
                        "answered-apart",
                        "unreachable",
                        "unresolved",
                        "unanchored",
                    )
                },
                "debt": "list",
                "debt[]": "object",
                "debt[].kind": "str",
                "debt[].artefact": "str|null",
                "debt[].location": "str|null",
                **{f"debt[].{key}": kind for key, kind in _ANCHOR.items()},
                "debt[].origin": "object",
                "debt[].reason": "str|null",
                "debt[].message": "str",
                "debt[].files": "list",
                "debt[].files[]": "str",
                **{
                    f"{listed}{key}": kind
                    for listed in ("unreachable", "unresolved")
                    for key, kind in {
                        "": "list",
                        "[]": "object",
                        **{f"[].{name}": "str" for name in _ARTEFACT_ENTRY},
                    }.items()
                },
                "unanchored": "list",
                "unanchored[]": "str",
                **_ACCEPTED_UNANCHORED,
            }
        )
    },
    shapes={"commit": COMMIT},
    refs={"debt[].origin": "commit"},
    sets={
        "report": frozenset({"debt"}),
        "debt[].kind": frozenset({"stale", "deferred", "answered-apart"}),
    },
)

_EXPLAINED_STATES = _ARTEFACT_STATES | {"unanchored", "excluded", "received"}

#: What an explained anchor's state may be: the kind of its first finding among those
#: that judge an anchor, else what the artefact shows when it is not judged, else
#: `current` (`friction_report._anchor_state`).
_ANCHOR_STATES = (
    *(
        kind.value
        for kind in (
            fr.RepositoryFindingKind.DEAD_ANCHOR,
            fr.RepositoryFindingKind.UNRESOLVED_KIND,
            fr.RepositoryFindingKind.NO_ANSWER,
            fr.RepositoryFindingKind.STALE,
            fr.RepositoryFindingKind.DEFERRED,
        )
    ),
    "current",
    fr.ArtefactState.UNREACHABLE.value,
    frep.EXCLUDED,
    frep.RECEIVED,
)

FRICTION_EXPLAIN = Contract(
    name="pkit friction explain --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "report": "str",
                **_HEAD,
                **_HISTORY,
                "artefact": "str",
                "location": "str",
                "body": "str",
                "state": "str",
                "unanchored_because": "str|null",
                "excluded_by": "object|null",
                "excluded_by.value": "str",
                "excluded_by.file": "str",
                "excluded_by.pointer": "str",
                **_POINTED,
                "anchors": "list",
                "anchors[]": "object",
                **{f"anchors[].{key}": kind for key, kind in _PLAIN_ANCHOR.items()},
                "anchors[].state": "str",
                "anchors[].changes": "int",
                "anchors[].over_broad": "bool",
                "anchors[].files": "object|null",
                "anchors[].files.point": "list|null",
                "anchors[].files.point[]": "str",
                "anchors[].files.head": "list",
                "anchors[].files.head[]": "str",
                "anchors[].files.excluded": "list",
                "anchors[].files.excluded[]": "str",
                "anchors[].diff": "list|null",
                "anchors[].diff[]": "str",
                "findings": "list",
                "findings[]": "object",
                **{f"findings[].{key}": kind for key, kind in _FINDING_KEYS.items()},
                "findings[].commits": "list",
                "findings[].commits[]": "object",
                **{f"findings[].commits[].{key}": kind for key, kind in COMMIT.keys.items()},
                "findings[].commits[].paths": "list",
                "findings[].commits[].paths[]": "str",
                "findings[].clears": "str",
                "findings[].answers": "list",
                "findings[].answers[]": "object",
                "findings[].answers[].answer": "str",
                "findings[].answers[].command": "str",
                "answers": "object|null",
                "answers_folder": "str",
            }
        )
    },
    shapes={"commit": COMMIT, "answers": ANSWERS},
    refs={
        "answers": "answers",
        "findings[].origin": "commit",
        **{path: "commit" for path in _COMMIT_REFS},
        **{key: value for key, value in _REPORT_REFS.items() if key.startswith("answers:")},
    },
    sets={
        "report": frozenset({"explain"}),
        "state": _EXPLAINED_STATES,
        "anchors[].state": frozenset(
            {"dead-anchor", "unresolved-kind", "no-answer", "stale", "deferred", "current"}
            | {"unreachable", "excluded", "received"}
        ),
        "findings[].kind": _REPOSITORY_KINDS,
        "findings[].bar": _BARS,
        "findings[].answers[].answer": frozenset({"updated", "unchanged", "deferred"}),
        "answers:home": frozenset({"block", "files"}),
    },
)


def _friction_history(repo: AdopterRepo) -> None:
    """The guide answered on two lines of work apart, then deferred on the engine, then
    both changed: stale, deferred and answered-apart debt. Beside it the requirement of a
    capability's place that links to its tests, revisited on one: live answers of each
    kind, with their points."""
    revisit_tests.declare_linker(repo.root)
    timeline = Timeline(repo)
    answer_tests._apart(timeline)
    timeline.commit(
        "defer the engine; revisit the requirement's test",
        {
            answer_tests.answer_path("three"): answer_tests.answers(
                answer_tests.entry(deferred=[(answer_tests.CORE, "until the engine settles, #1")])
            ),
            revisit_tests.TEST_FILE: "def test_latency():\n    assert answer_time() < 2\n",
            revisit_tests.DECISION: "Cache the status.\n",
            revisit_tests.SOURCE_DOC: revisit_tests.requirement(
                revisited=[revisit_tests.entry("unchanged", "the test still asserts under 2 s")]
            ),
        },
    )
    timeline.commit(
        "change both", {"src/cli/main.py": "print('s')\n", "src/core/engine.py": "ENGINE = 2\n"}
    )


def _every_finding(origin: fr.Commit) -> tuple[fr.RepositoryFinding, ...]:
    """A finding of each kind, each with an origin, a second bar's count and parts."""
    anchor = fd.Anchor("path", "src/**")
    counted = fr.OverBroad(fr.OverBroadBar.ASKS, "the last 100 commits", 5, 80, "src/cli/**")
    return tuple(
        fr.RepositoryFinding(
            kind,
            "why",
            "guide",
            answer_tests.GUIDE,
            anchor,
            origin,
            over_broad=counted,
            parts=(fd.Anchor("record", "PRJ-001#1"),),
        )
        for kind in fr.RepositoryFindingKind
    )


def _repository_documents(root: Path) -> list[dict[str, Any]]:
    """The check's document as a run prints it, with every finding and state, and
    dormant."""
    found = fr.run_repository_check(root)
    report = found.artefact_reports[0]
    assert report.revalidation_point is not None
    every = replace(
        found,
        findings=_every_finding(report.revalidation_point),
        artefact_reports=(
            report,
            replace(report, state=fr.ArtefactState.UNREACHABLE, revalidation_point=None, cut=True),
        ),
        unanchored=("docs/bare.md",),
        accepted_unanchored=(fr.AcceptedUnanchored("bare", "docs/bare.md", "nothing to stand on"),),
        uncovered=("src/stray.py",),
        prunable=("one.yaml",),
    )
    dormant = replace(found, dormant=True, head=None, shallow=None)
    return [json.loads(fr.render_json(result)) for result in (found, every, dormant)]


def _selection_documents(root: Path) -> list[dict[str, Any]]:
    """The check's document under a selection, as a run prints it, then with every finding
    and state and a location HEAD holds no artefact at."""
    named = fr.run_repository_check(root, judging=["docs/guide.md"])
    (report,) = named.artefact_reports
    assert report.revalidation_point is not None
    every = replace(
        named,
        findings=_every_finding(report.revalidation_point),
        unanchored=("docs/bare.md",),
        accepted_unanchored=(fr.AcceptedUnanchored("bare", "docs/bare.md", "nothing to stand on"),),
        uncovered=("src/stray.py",),
        selection=fr.Selection(("docs/gone.md", "docs/guide.md"), ("docs/gone.md",)),
    )
    return [json.loads(fr.render_json(result)) for result in (named, every)]


def _debt_documents(root: Path) -> list[dict[str, Any]]:
    listing = frep.run_debt(root)
    report = fr.run_repository_check(root).artefact_reports[0]
    every = replace(
        listing,
        unreachable=(report,),
        unresolved=(report,),
        unanchored=("docs/bare.md",),
        accepted_unanchored=(fr.AcceptedUnanchored("bare", "docs/bare.md", "nothing to stand on"),),
    )
    dormant = replace(listing, dormant=True, head=None, shallow=None)
    return [json.loads(frep.render_debt_json(found)) for found in (listing, every, dormant)]


def _explain_documents(root: Path) -> list[dict[str, Any]]:
    """The guide explained as a run gives it; then excluded, with an anchor's files read
    at no point and a part's diff, a finding of a second bar with parts; and with no
    report, its answers read alone."""
    explained = frep.run_explain(root, "guide")
    (anchor, *_rest) = explained.anchors
    (finding, *_others) = explained.findings
    assert finding.finding.origin is not None
    every = replace(
        explained,
        artefact=replace(
            explained.artefact,
            excluded_by=fd.SettingsPath(
                "docs/**", "docs/**", FRICTION_CONFIG, "/exclude/0", "project"
            ),
            friction={fd.UNANCHORED_BECAUSE_KEY: "nothing to stand on"},
        ),
        anchors=(replace(anchor, files=fr.AnchorFiles(None, (), ("src/x",)), diff=("-a", "+b")),),
        findings=(replace(finding, finding=_every_finding(finding.finding.origin)[0]),),
    )
    alone = replace(explained, report=None)
    return [json.loads(frep.render_explain_json(found)) for found in (explained, every, alone)]


@pytest.mark.usefixtures("answers_in_files")
def test_the_friction_report_documents_hold_their_contracts(
    committed_adopter: AdopterRepo,
) -> None:
    root = committed_adopter.root
    _friction_history(committed_adopter)
    kinds = tuple(kind.value for kind in fr.RepositoryFindingKind)
    bars = tuple(bar.value for bar in fr.OverBroadBar)
    homes = (af.BLOCK_HOME, af.FILES_HOME)
    check(
        REPOSITORY_CHECK,
        {
            "answer": [
                document_of(invoke("friction", "check", "--all", JSON_OPTION)),
                *_repository_documents(root),
            ],
            "selection": [
                document_of(
                    invoke("friction", "check", "--all", "--artefact", "docs/guide.md", JSON_OPTION)
                ),
                *_selection_documents(root),
            ],
        },
        enumerations={
            "finding:kind": kinds,
            "finding:bar": bars,
            "mode": fd.FRICTION_MODES,
            "report:state": (state.value for state in fr.ArtefactState),
            "answers:home": homes,
        },
    )
    check(
        FRICTION_DEBT,
        {"answer": [document_of(invoke("friction", "debt", JSON_OPTION)), *_debt_documents(root)]},
        enumerations={"debt[].kind": (kind.value for kind in frep.DEBT_KINDS)},
    )
    check(
        FRICTION_EXPLAIN,
        {
            "answer": [
                document_of(invoke("friction", "explain", "guide", JSON_OPTION)),
                document_of(invoke("friction", "explain", "REQ-1", JSON_OPTION)),
                *_explain_documents(root),
            ]
        },
        enumerations={
            "findings[].kind": kinds,
            "findings[].bar": bars,
            "anchors[].state": _ANCHOR_STATES,
            "state": (
                *(state.value for state in fr.ArtefactState),
                frep.UNANCHORED,
                frep.EXCLUDED,
                frep.RECEIVED,
            ),
            "answers:home": homes,
        },
    )


# --- `pkit refs lookup --json` and `pkit refs records-for --json` ---------------------------

REFS_LOOKUP = Contract(
    name="pkit refs lookup --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "lookups": "list",
                "lookups[]": "object",
                "lookups[].id": "str",
                "lookups[].resolved": "bool",
                "lookups[].paths": "list",
                "lookups[].paths[]": "str",
                "lookups[].problem": "str|null",
                "lookups[].path": "str|null",
                "lookups[].anchor": "str|null",
                "lookups[].received": "bool",
                "lookups[].partial_supersession": "str|null",
            }
        )
    },
)

_TIED = {
    "id": "str",
    "title": "str|null",
    "path": "str",
    "received": "bool",
    "points": "list",
    "points[]": "str",
    "in_place_of": "str|null",
}

RECORDS_FOR = Contract(
    name="pkit refs records-for --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "anchored": "int",
                "unreadable": "list",
                "unreadable[]": "str",
                "paths": "list",
                "paths[]": "object",
                "paths[].path": "str",
                "paths[].excluded_by": "str|null",
                "paths[].direct": "list",
                "paths[].direct[]": "object",
                **{f"paths[].direct[].{key}": _TIED[key] for key in ("id", "title", "path")},
                "paths[].direct[].received": "bool",
                "paths[].direct[].ties": "list",
                "paths[].direct[].ties[]": "object",
                "paths[].direct[].ties[].how": "str",
                "paths[].direct[].ties[].artefact": "str",
                "paths[].direct[].ties[].anchor": "str|null",
                "paths[].direct[].ties[].points": "list",
                "paths[].direct[].ties[].points[]": "str",
                "paths[].direct[].ties[].in_place_of": "str|null",
                "paths[].through": "list",
                "paths[].through[]": "object",
                "paths[].through[].artefact": "str",
                "paths[].through[].anchor": "str",
                "paths[].through[].records": "list",
                "paths[].through[].records[]": "object",
                **{f"paths[].through[].records[].{key}": kind for key, kind in _TIED.items()},
            }
        )
    },
    sets={
        "paths[].direct[].ties[].how": frozenset({"record", "artefact"}),
    },
)

_LOOKED_UP = ".pkit/decisions/project/PRJ-001-a.md"


def _records_for() -> dict[str, Any]:
    """An answer holding every key: a path excluded, tied directly by a record and by an
    artefact, a record in place of one it supersedes, and an artefact it is reached
    through."""
    record = path_records.Record("PRJ-001", "A record", _LOOKED_UP, received=False)
    received = path_records.Record("COR-001", None, ".pkit/decisions/core/COR-001-a.md", True)
    ties = (
        path_records.Tie(record, "record", "PRJ-001", "src/**", in_place_of="PRJ-000"),
        path_records.Tie(received, "artefact", "guide", None, points=("1",)),
        path_records.Tie(record, "through", "guide", "src/**", points=("2",)),
    )
    answer = path_records.Answer(
        (path_records.PathRecords("src/a.py", "src/old/**", ties),), 2, ("docs/broken.md",)
    )
    return answer.as_json()


def test_the_lookup_and_records_for_documents_hold_their_contracts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = GitRepo.init(tmp_path / "work")
    monkeypatch.chdir(repo.root)
    repo.commit("start", {_LOOKED_UP: _record("accepted")})
    looked_up = document_of(
        invoke("refs", "lookup", "PRJ-001", "PRJ-001#1", "PRJ-404", JSON_OPTION)
    )
    built = {
        "schema_version": 1,
        "lookups": [
            refs_mod.Lookup(
                "PRJ-001#1",
                (f"{_LOOKED_UP}#1-point-1",),
                path=_LOOKED_UP,
                anchor="1-point-1",
                received=True,
                partial_supersession="*Partially superseded by PRJ-002.*",
            ).as_json()
        ],
    }
    check(REFS_LOOKUP, {"answer": [looked_up, built]})
    records = document_of(invoke("refs", "records-for", "src/a.py", JSON_OPTION))
    check(RECORDS_FOR, {"answer": [records, _records_for()]})


# --- every command that prints a document has its contracts ---------------------------------

#: The contracts of the commands this module pins, by the command's words.
PINNED_HERE: Mapping[str, tuple[Contract, ...]] = {
    "repository base": (REPOSITORY_BASE,),
    "decisions check-landing": (CHECK_LANDING,),
    "decisions check-diff": (CHECK_DIFF,),
    "connections resolve": (DATA_POINT,),
    "friction since": (FRICTION_SINCE,),
    "friction move-plan": (FRICTION_MOVE_PLAN,),
    "friction prune": (FRICTION_PRUNE,),
    "rule-sets reach": (RULE_SETS_REACH,),
    "rule-sets altered": (RULE_SETS_ALTERED,),
    "rule-sets loaded": (RULE_SETS_LOADED,),
    "friction artefacts": (FRICTION_ARTEFACTS,),
    "friction check": (FRICTION_CHECK, REPOSITORY_CHECK),
    "friction debt": (FRICTION_DEBT,),
    "friction explain": (FRICTION_EXPLAIN,),
    "refs lookup": (REFS_LOOKUP,),
    "refs records-for": (RECORDS_FOR,),
}

#: The contracts of each command, by the module that pins them.
_MODULES: tuple[Mapping[str, tuple[Contract, ...]], ...] = (
    PINNED_HERE,
    account_documents.CONTRACTS,
    pull_request_documents.CONTRACTS,
    process_documents.CONTRACTS,
    component_documents.CONTRACTS,
    session_documents.CONTRACTS,
)

#: The contracts of each backbone command that prints a document for a program, by the
#: command's words.
CONTRACTS: Mapping[str, tuple[Contract, ...]] = {
    words: contracts for module in _MODULES for words, contracts in module.items()
}

#: Each way a backbone command prints for a program other than `--json`, by the command's
#: words and the option, with why no contract pins it (ADR-097 point 1).
OTHER_OUTPUT: Mapping[str, str] = {
    "refs graph --format": (
        "its `dot` form is a drawing in Graphviz's DOT language, which a renderer reads and "
        "whose shape that language sets, a protocol outside project-kit; `ascii` and `text` "
        "are for people"
    ),
    "connections graph --mermaid": (
        "a flowchart in Mermaid's language, which a renderer reads and whose shape that "
        "language sets, a protocol outside project-kit"
    ),
    "process graph --mermaid": (
        "a flowchart in Mermaid's language, which a renderer reads and whose shape that "
        "language sets, a protocol outside project-kit"
    ),
    "--version": "one line for people naming pkit's version, no request for machine output",
}

#: The options by which a backbone command chooses a form of its output other than
#: `--json`, and the one by which `pkit` itself prints its version: what `OTHER_OUTPUT`
#: is held to. A command's own `--version` names a version it is given.
_OUTPUT_OPTIONS = frozenset({"--format", "--mermaid"})
_VERSION_OPTION = "--version"


def _commands(
    group: click.Group, words: tuple[str, ...] = ()
) -> Iterator[tuple[str, click.Command]]:
    for name, command in sorted(group.commands.items()):
        if isinstance(command, click.Group):
            yield from _commands(command, (*words, name))
        else:
            yield " ".join((*words, name)), command


def _printing_documents() -> set[str]:
    """Each backbone command that takes `--json`, by its words."""
    return {
        words
        for words, command in _commands(main)
        if any(JSON_OPTION in param.opts for param in command.params)
    }


def baseline() -> set[str]:
    """The commands whose documents no contract pins yet."""
    lines = BASELINE.read_text(encoding="utf-8").splitlines()
    return {line.strip() for line in lines if line.strip() and not line.startswith("#")}


def test_every_command_that_prints_a_document_has_its_contracts() -> None:
    missing = _printing_documents() - set(CONTRACTS) - baseline()
    assert not missing, (
        f"{sorted(missing)} print a document for a program, and no contract here pins it: "
        f"pin each document's contract (ADR-097 point 7)"
    )


def test_the_baseline_names_only_commands_no_contract_pins() -> None:
    commands = _printing_documents()
    assert not baseline() & set(CONTRACTS), "a command with its contracts leaves the baseline"
    assert baseline() <= commands, "the baseline names a command that prints no document"


def test_each_command_has_its_contracts_in_one_module() -> None:
    pinned = [words for module in _MODULES for words in module]
    twice = sorted({words for words in pinned if pinned.count(words) > 1})
    assert not twice, f"{twice} have their contracts in two modules: keep them in one"


def _other_output() -> set[str]:
    """Each option of a backbone command, or of `pkit` itself, that chooses a form of its
    output other than `--json`, as the command's words and the option."""
    found = {
        f"{words} {option}"
        for words, command in _commands(main)
        for param in command.params
        for option in param.opts
        if option in _OUTPUT_OPTIONS
    }
    if any(_VERSION_OPTION in param.opts for param in main.params):
        found.add(_VERSION_OPTION)
    return found


def test_each_other_output_is_named_with_why_no_contract_pins_it() -> None:
    found = _other_output()
    assert found <= set(OTHER_OUTPUT), (
        f"{sorted(found - set(OTHER_OUTPUT))} print for a program other than through `--json`: "
        f"pin the document's contract here, or name in `OTHER_OUTPUT` why none pins it "
        f"(ADR-097 point 1)"
    )
    assert set(OTHER_OUTPUT) <= found, (
        f"`OTHER_OUTPUT` names {sorted(set(OTHER_OUTPUT) - found)}, which no command takes"
    )
