"""Tests for the reader of ruled artefacts a change altered (`_lib/ruled_artefacts.py`, #1386).

The `touches-ruled-artefact` floor (project-management DEC-032 D1) and its
freshness (DEC-028) read the backbone's one answer, `pkit rule-sets altered
--json`. These run the real command in fixture repositories: a change inside
and outside every scope, a set whose rules are all proposed, a change that only
writes a revalidation, an artefact ruled only at the base and removed, and a
change to the declared places alone, which alters the pages it brings in. The
failures that fail the resolution — a commit origin cannot provide, a shallow
checkout, a failing command, an unreadable answer, a backbone without the
command — are each named with their reason.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.friction_documents import CONFIG, SOURCE, T2, friction_config, guide
from tests.test_rule_sets import rule_set_text, rules

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"

SETS = "docs/rule-sets"
GUIDES = "docs/guides"
NOTES = "docs/notes"
A = f"{GUIDES}/a.md"
B = f"{GUIDES}/b.md"
N = f"{NOTES}/n.md"


@pytest.fixture(scope="module")
def ra() -> Iterator[ModuleType]:
    """The module, imported as the pm scripts import it."""
    inserted = str(SCRIPTS_DIR) not in sys.path
    if inserted:
        sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        yield importlib.import_module("_lib.ruled_artefacts")
    finally:
        if inserted:
            sys.path.remove(str(SCRIPTS_DIR))


def page(title: str, body: str = "Body.") -> str:
    return f"---\ntitle: {title}\n---\n\n{body}\n"


def _rule_set(status: str = "accepted") -> str:
    """`DOC`, scoped to the guides, with one rule of `status`."""
    return rule_set_text(
        {
            "rule-set": "DOC",
            "version": "1.0.0",
            "scope": {"paths": [f"{GUIDES}/**"]},
            "rules": rules("RS-DOC-001", status=status),
        }
    )


def _start(repo: AdopterRepo, *, status: str = "accepted") -> str:
    """The base on `main`: guides inside DOC's scope, a note outside every scope;
    then branch `feature`. Returns the base commit."""
    repo.write(
        {
            CONFIG: friction_config(places=(GUIDES, NOTES)),
            f"{SETS}/doc.md": _rule_set(status),
            A: guide(),
            B: page("B"),
            N: page("N"),
            **SOURCE,
        }
    )
    base = repo.commit("base", files=None)
    repo.checkout("feature", create=True)
    return base


@pytest.fixture
def repo(make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path) -> AdopterRepo:
    return make_adopter_repo()


# --- the answer ---------------------------------------------------------------


def test_a_change_inside_a_scope_alters_a_ruled_artefact(ra: ModuleType, repo: AdopterRepo) -> None:
    base = _start(repo)
    head = repo.commit("change b", {B: page("B", "A new body.")})
    found = ra.ruled_altered(base, head)
    assert found.ok, found.error
    assert found.locations == (B,) and found.altered == (B,)


def test_a_change_outside_every_scope_alters_no_ruled_artefact(
    ra: ModuleType, repo: AdopterRepo
) -> None:
    base = _start(repo)
    head = repo.commit("change the note", {N: page("N", "A new body.")})
    found = ra.ruled_altered(base, head)
    assert found.ok and found.locations == () and found.altered == (N,)


def test_a_set_whose_rules_are_all_proposed_rules_nothing(
    ra: ModuleType, repo: AdopterRepo
) -> None:
    base = _start(repo, status="proposed")
    head = repo.commit("change b", {B: page("B", "A new body.")})
    found = ra.ruled_altered(base, head)
    assert found.ok and found.locations == () and found.altered == (B,)


def test_a_change_that_only_writes_a_revalidation_alters_nothing(
    ra: ModuleType, repo: AdopterRepo
) -> None:
    base = _start(repo)
    head = repo.commit("revalidate a", {A: guide(at=T2, because="nothing it rests on changed")})
    assert ra.ruled_altered(base, head) == ra.RuledAlteration()


def test_an_artefact_ruled_at_the_base_and_removed_is_altered(
    ra: ModuleType, repo: AdopterRepo
) -> None:
    base = _start(repo)
    head = repo.commit("remove b", {B: None})
    assert ra.ruled_altered(base, head).locations == (B,)


def test_each_altered_artefact_carries_its_change_and_its_files(
    ra: ModuleType, repo: AdopterRepo
) -> None:
    base = _start(repo)
    head = repo.commit(
        "change a and the note, remove b",
        {A: guide(body="Changed."), N: page("N", "Changed."), B: None},
    )
    found = ra.ruled_altered(base, head)
    assert found.ok, found.error
    assert found.artefacts == (
        ra.AlteredArtefact(location=A, change="changed", paths=(A,), ruled=True),
        ra.AlteredArtefact(location=N, change="changed", paths=(N,), ruled=False),
        ra.AlteredArtefact(location=B, change="removed", paths=(B,), ruled=True),
    )


def test_a_change_to_the_places_alone_alters_the_pages_it_brings_in(
    ra: ModuleType, repo: AdopterRepo
) -> None:
    """A configuration change that brings a ruled page into the places makes it
    an artefact at the head only. The command lists it as added, though the
    change touches no file of it, and the floor counts it (DEC-032 D1)."""
    repo.write(
        {
            CONFIG: friction_config(places=(NOTES,)),
            f"{SETS}/doc.md": _rule_set(),
            B: page("B"),
            N: page("N"),
        }
    )
    base = repo.commit("base", files=None)
    repo.checkout("feature", create=True)
    head = repo.commit("add the guides", {CONFIG: friction_config(places=(GUIDES, NOTES))})
    found = ra.ruled_altered(base, head)
    assert found.ok, found.error
    assert found.artefacts == (
        ra.AlteredArtefact(location=B, change="added", paths=(B,), ruled=True),
    )


def test_the_base_is_where_the_head_left_it(ra: ModuleType, repo: AdopterRepo) -> None:
    """Named by the base branch's head, the change is the head's own: what the base
    branch changed after the head left it is not the change's."""
    _start(repo)
    head = repo.commit("change the note", {N: page("N", "Changed.")})
    repo.checkout("main")
    tip = repo.commit("main changes b", {B: page("B", "Main's body.")})
    found = ra.ruled_altered(tip, head)
    assert found.ok and found.locations == () and found.altered == (N,)


# --- what it needs locally ----------------------------------------------------------------


def test_a_commit_origin_cannot_provide_names_the_fetch(ra: ModuleType, repo: AdopterRepo) -> None:
    base = _start(repo)
    found = ra.ruled_altered(base, "f" * 40)
    assert not found.ok and found.locations == ()
    assert "the head, fffffff, is not in this checkout and could not be fetched" in found.error


def test_a_shallow_checkout_fails_with_its_reason(
    ra: ModuleType, repo: AdopterRepo, tmp_path: Path
) -> None:
    base = _start(repo)
    head = repo.commit("change b", {B: page("B", "A new body.")})
    clone = tmp_path / "shallow"
    subprocess.run(
        [
            "git",
            "clone",
            "-q",
            "--depth",
            "1",
            "--branch",
            "feature",
            repo.root.as_uri(),
            str(clone),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(clone), "fetch", "-q", "--depth", "1", "origin", base],
        check=True,
        capture_output=True,
    )
    found = ra.ruled_altered(base, head, cwd=clone)
    assert not found.ok and "this checkout is shallow" in found.error


def _answering(returncode: int, stdout: str = "", stderr: str = "") -> tuple[list[list[str]], Any]:
    """A runner that has every commit, a full history, and answers the command
    with `returncode`, `stdout` and `stderr`; and the argv of each run."""
    seen: list[list[str]] = []

    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.append(list(argv))
        if argv[:2] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(argv, 0, "false\n", "")
        if argv[0] == "git":
            return subprocess.CompletedProcess(argv, 0, "", "")
        assert kwargs["env"]["PKIT_NO_ROUTE"] == "1"
        return subprocess.CompletedProcess(argv, returncode, stdout, stderr)

    return seen, run


BASE, HEAD = "b" * 40, "c" * 40


def _side(location: str, *, rules: list | None = None, held: list | None = None) -> dict:
    """One state of an artefact as the command lists it."""
    return {"location": location, "path": location, "rules": rules or [], "held": held or []}


def test_the_command_runs_unrouted_with_both_commits_named(ra: ModuleType) -> None:
    document = {"schema_version": 1, "artefacts": []}
    seen, run = _answering(0, json.dumps(document))
    assert ra.ruled_altered(BASE, HEAD, run=run) == ra.RuledAlteration()
    assert seen[-1] == ["pkit", "rule-sets", "altered", "--json", "--base", BASE, "--head", HEAD]


def test_a_backbone_without_the_command_names_the_backbone_needed(ra: ModuleType) -> None:
    _seen, run = _answering(
        2, stderr="Usage: pkit [OPTIONS]\nError: No such command 'rule-sets'.\n"
    )
    found = ra.ruled_altered(BASE, HEAD, run=run)
    assert not found.ok
    assert "has no `pkit rule-sets altered` command" in found.error
    assert "project-management's `requires_backbone`" in found.error
    assert "upgrade pkit" in found.error


@pytest.mark.parametrize(
    ("returncode", "stdout", "why"),
    [
        (1, "", "it exited 1: Error: the base cannot be compared"),
        (0, "not json", "its answer is not JSON"),
        (0, "[]", "its answer is not a document"),
        (0, json.dumps({"schema_version": 2, "artefacts": []}), "schema_version 2"),
        (0, json.dumps({"schema_version": 1}), "lists no artefacts"),
        (
            0,
            json.dumps(
                {
                    "schema_version": 1,
                    "artefacts": [{"change": "added", "base": None, "head": None}],
                }
            ),
            "without a readable location",
        ),
        (
            0,
            json.dumps(
                {
                    "schema_version": 1,
                    "artefacts": [{"change": "added", "base": None, "head": {"location": A}}],
                }
            ),
            "without a readable location",
        ),
        (
            0,
            json.dumps(
                {
                    "schema_version": 1,
                    "artefacts": [
                        {"change": "moved", "base": None, "head": _side(A, rules=[])},
                    ],
                }
            ),
            "altered as 'moved', which this does not read",
        ),
    ],
)
def test_an_answer_that_cannot_be_read_fails_with_its_reason(
    ra: ModuleType, returncode: int, stdout: str, why: str
) -> None:
    _seen, run = _answering(returncode, stdout, "Error: the base cannot be compared\n")
    found = ra.ruled_altered(BASE, HEAD, run=run)
    assert not found.ok and found.locations == () and why in found.error


def test_an_artefact_whose_rules_are_all_held_back_is_not_ruled(ra: ModuleType) -> None:
    """A rule a pin behind its set holds back binds nothing (COR-051 point 7):
    the answer lists it under `held`, and the floor counts only `rules`."""
    held = [{"rule": "RS-DOC-002", "id": "RS-DOC-002", "status": "accepted"}]
    document = {
        "schema_version": 1,
        "artefacts": [
            {"change": "changed", "base": _side(A, held=held), "head": _side(A, held=held)},
            {"change": "added", "base": None, "head": _side(B, rules=[{"rule": "RS-DOC-001"}])},
        ],
    }
    _seen, run = _answering(0, json.dumps(document))
    found = ra.ruled_altered(BASE, HEAD, run=run)
    assert found.ok, found.error
    assert found.altered == (A, B) and found.locations == (B,)


def test_pkit_missing_from_path_fails(ra: ModuleType) -> None:
    def run(argv: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        if argv[0] == "git":
            return subprocess.CompletedProcess(argv, 0, "false\n", "")
        raise FileNotFoundError("pkit")

    found = ra.ruled_altered(BASE, HEAD, run=run)
    assert not found.ok and "`pkit` is not on PATH" in found.error


def test_an_unknown_commit_fails_before_reading_anything(ra: ModuleType) -> None:
    seen, run = _answering(0)
    assert not ra.ruled_altered("", HEAD, run=run).ok
    assert seen == []


# --- the gate and the freshness rule, through the real backbone ------------------------------
#
# `resolve_pr_review` — the one wiring `done-work`, `review-pr`, `show-pr` and
# `land-work` share — with `gh` stood in and the backbone real: the gate
# requires the floor's reviewer exactly when the change alters a ruled
# artefact, and the reviewer's approval survives what alters none.

RULES = "rule-set-reviewer"


@pytest.fixture(scope="module")
def pm() -> Iterator[tuple[ModuleType, ModuleType, ModuleType, ModuleType]]:
    inserted = str(SCRIPTS_DIR) not in sys.path
    if inserted:
        sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        yield (
            importlib.import_module("_lib.pr_review"),
            importlib.import_module("_lib.review_contributions"),
            importlib.import_module("_lib.author_delta"),
            importlib.import_module("_lib.agent_verdicts"),
        )
    finally:
        if inserted:
            sys.path.remove(str(SCRIPTS_DIR))


def _gh(changed: list[str], base: str, head: str) -> Any:
    """`gh` for PR 7: it closes nothing, changes `changed`, and runs from
    `base`'s branch head to `head`."""

    def run(argv: list[str], _config: Any, **_: Any) -> subprocess.CompletedProcess[str]:
        if "closingIssuesReferences" in argv:
            out = json.dumps({"closingIssuesReferences": []})
        elif "baseRefOid,headRefOid" in argv:
            out = json.dumps({"baseRefOid": base, "headRefOid": head})
        elif argv[:2] == ["gh", "api"]:
            out = "\n".join(json.dumps([path, None]) for path in changed)
        else:
            raise AssertionError(f"unexpected gh call: {argv}")
        return subprocess.CompletedProcess(argv, 0, out, "")

    return run


def _resolve(pm: tuple, repo: AdopterRepo, changed: list[str], base: str, head: str) -> Any:
    pr_review, rc, ad, _av = pm
    rule = rc.ContributionRule(
        capability="living-docs",
        predicate={},
        reviewer=RULES,
        floor=rc.FLOOR_TOUCHES_RULED_ARTEFACT,
    )
    return pr_review.resolve_pr_review(
        7,
        {"review": {"agents": {"local_registered": [{"name": "pm-reviewer"}]}}},
        repo.root,
        gh_run=_gh(changed, base, head),
        gh_get_issue=lambda *_a, **_k: None,
        collect_contributions=lambda _root: rc.ContributionCollection(rules=(rule,)),
        author_delta=ad.author_delta,
        base_kept=ad.base_kept,
    )


def test_the_gate_requires_the_reviewer_exactly_when_a_ruled_artefact_is_altered(
    pm: tuple, repo: AdopterRepo
) -> None:
    base = _start(repo)
    head = repo.commit("change the note", {N: page("N", "A new body.")})
    review = _resolve(pm, repo, [N], base, head)
    assert review.resolution.ok, review.resolution.error
    assert review.resolution.required_local == ("pm-reviewer",)

    head = repo.commit("change b", {B: page("B", "A new body.")})
    review = _resolve(pm, repo, [N, B], base, head)
    assert review.resolution.ok, review.resolution.error
    assert review.resolution.required_local == ("pm-reviewer", RULES)
    assert review.resolution.floors_by_reviewer == {RULES: frozenset({"touches-ruled-artefact"})}


def test_a_commit_the_checkout_lacks_fails_the_resolution_with_its_reason(
    pm: tuple, repo: AdopterRepo
) -> None:
    base = _start(repo)
    review = _resolve(pm, repo, [B], base, "e" * 40)
    assert not review.resolution.ok
    assert review.resolution.error.kind == "ruled-artefacts-unresolvable"
    assert "could not be fetched" in review.resolution.error.message


def _approval(av: ModuleType, sha: str) -> Any:
    return av.Verdict(
        reviewer=RULES,
        token=av.APPROVED,
        path=av.PATH_LOCAL,
        body="",
        timestamp="2026-10-13T00:00:00Z",
        sha=sha,
        base="",
    )


def test_the_approval_survives_a_revalidation_and_a_clean_merge_of_the_base(
    pm: tuple, repo: AdopterRepo
) -> None:
    base = _start(repo)
    reviewed = repo.commit("change b", {B: page("B", "A new body.")})
    repo.commit("revalidate a", {A: guide(at=T2, because="nothing it rests on changed")})
    repo.checkout("main")
    tip = repo.commit("main changes the note", {N: page("N", "Main's body.")})
    repo.checkout("feature")
    head = repo.merge("main")
    _pr_review, _rc, _ad, av = pm
    review = _resolve(pm, repo, [A, B, N], tip, head)
    assert review.resolution.ok, review.resolution.error
    rule = review.freshness_rule({"headRefOid": head, "baseRefOid": tip, "commits": []})
    assessed = rule.assess(_approval(av, reviewed))
    assert assessed.fresh, assessed.reason
    assert assessed.reason.endswith("reaches none of its floors (touches-ruled-artefact)")
    assert base != tip


def test_a_push_altering_a_ruled_artefact_stales_the_approval(pm: tuple, repo: AdopterRepo) -> None:
    _start(repo)
    reviewed = repo.commit("change the note", {N: page("N", "A new body.")})
    head = repo.commit("change b", {B: page("B", "A new body.")})
    tip = repo.git("rev-parse", "main").stdout.strip()
    _pr_review, _rc, _ad, av = pm
    review = _resolve(pm, repo, [N, B], tip, head)
    rule = review.freshness_rule({"headRefOid": head, "baseRefOid": tip, "commits": []})
    assessed = rule.assess(_approval(av, reviewed))
    assert not assessed.fresh
    assert assessed.reason.endswith("reaches its touches-ruled-artefact floor")


def _start_without_the_guides(repo: AdopterRepo) -> str:
    """The base on `main`: only the notes are a place, so the guides inside
    DOC's scope are no artefacts yet; then branch `feature`."""
    repo.write(
        {
            CONFIG: friction_config(places=(NOTES,)),
            f"{SETS}/doc.md": _rule_set(),
            B: page("B"),
            N: page("N"),
            **SOURCE,
        }
    )
    base = repo.commit("base", files=None)
    repo.checkout("feature", create=True)
    return base


def test_a_change_to_the_declared_places_alone_requires_the_reviewer(
    pm: tuple, repo: AdopterRepo
) -> None:
    """The PR changes only the configuration, bringing a ruled page into the
    declared places. It touches no Markdown file, and the gate still requires
    the reviewer of the rules (DEC-032 D1)."""
    base = _start_without_the_guides(repo)
    head = repo.commit("add the guides", {CONFIG: friction_config(places=(GUIDES, NOTES))})
    review = _resolve(pm, repo, [CONFIG], base, head)
    assert review.resolution.ok, review.resolution.error
    assert review.resolution.required_local == ("pm-reviewer", RULES)


def test_a_push_to_the_declared_places_alone_stales_the_approval(
    pm: tuple, repo: AdopterRepo
) -> None:
    """Approved on a page edit; the author then brings the guides into the
    places. The page it brings in was never judged, so the approval goes
    stale (DEC-028)."""
    base = _start_without_the_guides(repo)
    reviewed = repo.commit("change the note", {N: page("N", "A new body.")})
    head = repo.commit("add the guides", {CONFIG: friction_config(places=(GUIDES, NOTES))})
    _pr_review, _rc, _ad, av = pm
    review = _resolve(pm, repo, [N, CONFIG], base, head)
    assert review.resolution.ok, review.resolution.error
    rule = review.freshness_rule({"headRefOid": head, "baseRefOid": base, "commits": []})
    assessed = rule.assess(_approval(av, reviewed))
    assert not assessed.fresh
    assert assessed.reason.endswith("reaches its touches-ruled-artefact floor")


def test_a_place_the_base_brings_in_keeps_the_approval(pm: tuple, repo: AdopterRepo) -> None:
    """The PR adds a page outside the places and is approved. The base then
    declares the place, and the author merges it cleanly and pushes a code fix.
    The page is now a ruled artefact the PR adds, so the gate requires the
    reviewer. But the place came with the base: only the author's own run
    since the review is asked about, and it alters no artefact, so the
    approval stands, as it would without the code fix (DEC-028)."""
    _start_without_the_guides(repo)
    new = f"{GUIDES}/new.md"
    reviewed = repo.commit("add a page", {new: page("New")})
    repo.checkout("main")
    tip = repo.commit("add the guides", {CONFIG: friction_config(places=(GUIDES, NOTES))})
    repo.checkout("feature")
    repo.merge("main")
    head = repo.commit("code fix", {"src/core/engine.py": "ENGINE = 2\n"})
    _pr_review, _rc, _ad, av = pm
    review = _resolve(pm, repo, [new, "src/core/engine.py"], tip, head)
    assert review.resolution.ok, review.resolution.error
    assert review.resolution.required_local == ("pm-reviewer", RULES)
    rule = review.freshness_rule({"headRefOid": head, "baseRefOid": tip, "commits": []})
    assessed = rule.assess(_approval(av, reviewed))
    assert assessed.fresh, assessed.reason
    assert assessed.reason.endswith("reaches none of its floors (touches-ruled-artefact)")
