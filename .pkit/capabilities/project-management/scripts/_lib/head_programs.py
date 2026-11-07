"""Which pull request heads may start programs (DEC-067).

A checkout of a pull request's head, or of its merge with the base, runs what that
tree holds: each resolver the change check starts, all it loads and any hook. So a
command starts a head's programs only where the head passes a test, or a person at a
terminal named the commit for that run
([project-management:DEC-067-heads-that-start-programs]). This module holds that
rule for the commands that keep to it (`land-work`, `review-work`, `review-pr`):

- `take_test` is the test (point 1). The host must say the head lies in the base's
  own repository, in the reading that names the head, and the head must hold none of
  the commits the Task's build records name (`build_commits`). A reading that does
  not say, and records that cannot be read, fail it. A head that fails is a head
  *from elsewhere*. `Standing` is what the test found, for one head and one run.
- `ask` is the question at a terminal (point 4), and `Standing.named` the word it
  gives. The answer is the commit's short id, typed. A comment on the pull request
  is posted before anything starts, and with no comment nothing starts. No flag
  reaches this: each caller asks only at a terminal and only on a run nobody
  authorised up front.
- `one_open` reads a branch's open pull request, and refuses two of them, since one
  may be a fork's (point 1).
- `repository` names where a head comes from, for the question.

**Build records.** The build command that writes them is not built yet
([project-kit#2287](https://github.com/aleskalfas/project-kit/issues/2287)). So this
module is the reader of the contract: a `build-hand-back` audit event on the Task's
log (`BUILD_EVENT`), whose `commits` field names the build's commits, full ids
separated by commas. The event is read whoever posted it, since a stranger's stamp
can only stop a run. A commit the base already holds no longer counts, since it
landed.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from _lib import audit_log, comment_log, default_branch, friction_answers, topology
from _lib.audit import audit_key, render_audit_comment
from _lib.comment import post_audit_once
from _lib.gh import gh_run
from _lib.membership import resolve_invoker_identity

#: The audit event a Task's log records a build's commits with, and the field that
#: names them.
BUILD_EVENT = "build-hand-back"
BUILD_COMMITS = "commits"
#: The `_lib.audit.audit_key` writer name of the comment a person's word leaves.
NAMED_WRITER = "head-named"


@dataclass(frozen=True)
class Standing:
    """What one run found of a head: `elsewhere` says why it fails the test, and is
    empty where it passes. `named` says a person named it for this run."""

    head: str
    elsewhere: str = ""
    named: bool = False

    @property
    def passes(self) -> bool:
        """Whether the head passed the test, with no person's word."""
        return not self.elsewhere

    @property
    def may_start(self) -> bool:
        """Whether this run may start what the head holds."""
        return self.passes or self.named


#: A head no test was taken on, which starts nothing.
UNTAKEN = Standing("", elsewhere="no test was taken on it")


class TwoOpen(Exception):
    """Two open pull requests share a branch's name: the line that names both."""


def one_open(prs: Iterable[Mapping[str, Any]], branch: str) -> Mapping[str, Any] | None:
    """The open pull request from `branch` among `prs`, or None; `TwoOpen` where
    there are more, since one may be a fork's and a run cannot tell which it was
    asked for. A reading of open pull requests alone need not carry their state."""
    found = [
        pr for pr in prs if pr.get("headRefName") == branch and pr.get("state", "OPEN") == "OPEN"
    ]
    if len(found) > 1:
        named = " and ".join(f"#{pr.get('number')}" for pr in found)
        raise TwoOpen(
            f"open pull requests {named} share the branch name {branch}, and one may be a "
            "fork's, so which this run is for cannot be told. Nothing was done; close the "
            "one this run is not for, or land it apart"
        )
    return found[0] if found else None


def repository(pr: Mapping[str, Any]) -> str:
    """The repository the pull request's head comes from, as the host names it, or ""
    where it names none, as for a fork that was deleted."""
    owner = _mapping(pr.get("headRepositoryOwner")).get("login")
    name = _mapping(pr.get("headRepository")).get("name")
    return f"{owner}/{name}" if owner and name else ""


def take_test(
    head: str,
    placed: object,
    *,
    issue: int,
    base: str,
    source: friction_answers.Source | None,
    capability_root: Path,
    config: dict,
) -> Standing:
    """The test of DEC-067 point 1 on commit `head`. `placed` is the host's word on
    the pull request, `isCrossRepository`, from the reading that named `head`. Only
    False places the head in the base's repository. `issue` is the Task whose build
    records are read, `base` the pull request's base branch and `source` where the
    head is fetched from, should the records name a commit."""
    if placed is True:
        return Standing(head, "it lies in another repository than the base's")
    if placed is not False:
        return Standing(head, "the host did not say it lies in the base's repository")
    named = build_commits(issue, capability_root, config)
    if isinstance(named, str):
        return Standing(head, f"#{issue}'s build records could not be read ({named})")
    if not named:
        return Standing(head)
    held = _held(head, base, named, source)
    if isinstance(held, str):
        return Standing(head, f"which build commits it holds could not be read ({held})")
    if held:
        commits = ", ".join(commit[: friction_answers.SHORT] for commit in held)
        return Standing(head, f"it holds commits of a sandboxed build ({commits})")
    return Standing(head)


def build_commits(issue: int, capability_root: Path, config: dict) -> frozenset[str] | str:
    """Each commit issue `issue`'s build records name, or why they cannot be read. A
    project with no seats has no builds, so nothing is read there."""
    try:
        tree = topology.read(capability_root)
    except topology.Unresolved as exc:
        return str(exc)
    if tree is None:
        return frozenset()
    if tree.not_understood:
        return "this code cannot read the topology of the default branch in full"
    if not tree.seats:
        return frozenset()
    log = comment_log.read_log(issue, lambda argv: gh_run(argv, config, check=False))
    if not log.complete:
        return log.cause or "its comments could not be read in full"
    found: set[str] = set()
    for comment in log.comments:
        event = audit_log.parse(comment.body)
        if event is not None and event.type == BUILD_EVENT:
            found.update(re.findall(r"[0-9a-f]{40,64}", event.get(BUILD_COMMITS) or ""))
    return frozenset(found)


def _held(
    head: str, base: str, named: frozenset[str], source: friction_answers.Source | None
) -> tuple[str, ...] | str:
    """Of the commits `named`, each `head` holds that the base's tip does not, or why
    that could not be read."""
    problem = friction_answers.refresh_base(base)
    if problem is None and source is not None:
        problem = friction_answers.fetch_head(head, source)
    if problem is not None:
        return problem
    try:
        tip = default_branch.branch(base).tip
    except default_branch.Unanswered as exc:
        return str(exc)
    if not tip:
        return f"the base {base} names no commit"
    proc = subprocess.run(
        ["git", "rev-list", head, f"^{tip}"], capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        said = (proc.stderr or "").strip().splitlines()
        return said[-1] if said else f"git rev-list exited {proc.returncode}"
    return tuple(commit for commit in proc.stdout.split() if commit in named)


def ask(
    standing: Standing,
    *,
    command: str,
    number: int,
    source_repository: str,
    capability_root: Path,
    config: dict,
) -> Standing:
    """Ask the person at this terminal whether to name the head for this run of
    `command` (DEC-067 point 4): `standing` with its `named` set, once they typed the
    commit's short id and the comment was posted, else `standing` as it was. The
    caller checks that a person can be there and that no flag authorised the run."""
    head = standing.head
    short = head[: friction_answers.SHORT]
    print(f"{command}: PR #{number}'s head is from elsewhere: {standing.elsewhere}.")
    print(f"  commit:     {head}")
    print(f"  repository: {source_repository or 'one the host does not name'}")
    print(
        f"The change check needs a program this head holds. Naming the head starts its "
        f"programs under your account, for this run of {command} alone: the commit, its "
        "merge with the base and the reviewers the run starts."
    )
    print(f"Reading its diff needs no checkout: `gh pr diff {number}`.")
    try:
        reply = input(f"Type {short} to name this head, anything else to stop: ")
    except EOFError:
        reply = ""
    if reply.strip() != short:
        print(f"{command}: the head was not named, so nothing it holds starts.")
        return standing
    if not _word_left(head, command, number, capability_root, config):
        print(
            f"{command}: the comment naming {short} could not be posted on PR #{number}, so "
            "nothing the head holds starts."
        )
        return standing
    return replace(standing, named=True)


def _word_left(head: str, command: str, number: int, capability_root: Path, config: dict) -> bool:
    """Post the comment a person's word leaves, whatever `audit.projection` says, since
    with no comment nothing starts (DEC-067 point 4): whether it is on the pull
    request. A fresh act's key makes each run's word a comment of its own."""
    key = audit_key(NAMED_WRITER, head, command, audit_log.new_act_id())
    invoker = resolve_invoker_identity(config=config)
    reason = (
        f"named head {head} for one run of `{command}`: the programs it holds start under "
        "their account for that run"
    )
    body = "\n".join([render_audit_comment(capability_root, invoker, reason), "", key])
    return post_audit_once("pr", number, key, body, config, run=gh_run)


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
